from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.agents.incident import format_incident_comment, triage_incident
from backend.agents.pr_reviewer import format_review_comment, review_pr
from backend.config import settings
from backend.db.database import (
    get_incident_job,
    get_incident_jobs,
    get_review_job,
    get_review_jobs,
    init_db,
    save_incident_job,
    save_review_job,
    update_incident_job,
    update_review_job,
)
from backend.tools.github import GitHubTools
from backend.tools.hedera import record_pr_review, record_incident

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("DevPilot started")
    yield
    logger.info("DevPilot shutting down")


app = FastAPI(title="DevPilot", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

github = GitHubTools(token=settings.github_token)


def _verify_webhook_signature(payload: bytes, sig_header: str | None) -> None:
    if not settings.github_webhook_secret:
        # No secret configured; skip validation (dev mode only)
        logger.warning("Webhook secret not configured; skipping signature check")
        return
    if not sig_header:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256 header")
    if not sig_header.startswith("sha256="):
        raise HTTPException(status_code=400, detail="Unexpected signature format")
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        payload,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, sig_header):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


async def _handle_pr_review(repo: str, pr_number: int, job_id: int) -> None:
    try:
        await update_review_job(job_id, "running")
        diff = await github.get_pr_diff(repo, pr_number)
        files = await github.get_pr_files(repo, pr_number)
        review = await review_pr(repo, pr_number, diff, files)

        verdict_map = {
            "approve": "APPROVE",
            "request_changes": "REQUEST_CHANGES",
            "comment": "COMMENT",
        }
        github_event = verdict_map.get(review.overall, "COMMENT")

        # Record verdict on Hedera HCS (immutable audit trail — no-op if not configured)
        hcs_url = await record_pr_review(
            repo=repo,
            pr_number=pr_number,
            verdict=review.overall,
            summary=review.summary,
            issues_count=len(review.issues),
        )

        comment_body = format_review_comment(review, hcs_url=hcs_url)
        await github.post_review(repo, pr_number, body=comment_body, event=github_event)

        result = review.model_dump()
        result_json = json.dumps(result, sort_keys=True)
        result_hash = hashlib.sha256(result_json.encode()).hexdigest()
        await update_review_job(job_id, "done", result, hcs_url=hcs_url, hcs_result_hash=result_hash)
        logger.info("Review complete for %s#%d (job %d)", repo, pr_number, job_id)
    except Exception as exc:
        logger.error("Review job %d failed: %s", job_id, exc, exc_info=True)
        await update_review_job(job_id, "error", {"error": str(exc)})


async def _handle_incident_triage(repo: str, run_id: int, pr_number: int | None, job_id: int) -> None:
    try:
        await update_incident_job(job_id, "running")
        logs = await github.get_workflow_run_logs(repo, run_id)
        report = await triage_incident(repo, run_id, logs)

        # Record incident on Hedera HCS (no-op if not configured)
        hcs_url = await record_incident(
            repo=repo,
            run_id=run_id,
            severity=report.severity,
            root_cause=report.root_cause,
        )

        comment_body = format_incident_comment(report, run_id, hcs_url=hcs_url)
        if pr_number:
            await github.post_pr_comment(repo, pr_number, comment_body)
        else:
            logger.info("No PR associated with run %d; skipping comment", run_id)

        result = report.model_dump()
        result_json = json.dumps(result, sort_keys=True)
        result_hash = hashlib.sha256(result_json.encode()).hexdigest()
        await update_incident_job(job_id, "done", result, hcs_url=hcs_url, hcs_result_hash=result_hash)
        logger.info("Incident triage complete for %s run %d (job %d)", repo, run_id, job_id)
    except Exception as exc:
        logger.error("Incident job %d failed: %s", job_id, exc, exc_info=True)
        await update_incident_job(job_id, "error", {"error": str(exc)})


@app.post("/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
) -> dict[str, str]:
    payload_bytes = await request.body()
    _verify_webhook_signature(payload_bytes, x_hub_signature_256)

    try:
        payload: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    action = payload.get("action")
    repo_data = payload.get("repository", {})
    repo = repo_data.get("full_name", "unknown/unknown")

    logger.info("Received GitHub event=%s action=%s repo=%s", x_github_event, action, repo)

    if x_github_event == "pull_request" and action in ("opened", "synchronize"):
        pr_data = payload.get("pull_request", {})
        pr_number = pr_data.get("number")
        if not pr_number:
            raise HTTPException(status_code=400, detail="Missing pull_request.number")
        job_id = await save_review_job(repo, pr_number, status="pending")
        background_tasks.add_task(_handle_pr_review, repo, pr_number, job_id)
        return {"status": "queued", "job_id": str(job_id), "type": "pr_review"}

    if x_github_event == "workflow_run" and action == "completed":
        run_data = payload.get("workflow_run", {})
        conclusion = run_data.get("conclusion")
        if conclusion != "failure":
            return {"status": "ignored", "reason": f"conclusion={conclusion}"}
        run_id = run_data.get("id")
        if not run_id:
            raise HTTPException(status_code=400, detail="Missing workflow_run.id")
        pr_number: int | None = None
        prs = run_data.get("pull_requests", [])
        if prs:
            pr_number = prs[0].get("number")
        job_id = await save_incident_job(repo, run_id, status="pending")
        background_tasks.add_task(_handle_incident_triage, repo, run_id, pr_number, job_id)
        return {"status": "queued", "job_id": str(job_id), "type": "incident_triage"}

    return {"status": "ignored", "event": x_github_event, "action": action}


@app.get("/api/reviews")
async def list_reviews(limit: int = 20) -> list[dict]:
    return await get_review_jobs(limit=min(limit, 100))


@app.get("/api/incidents")
async def list_incidents(limit: int = 20) -> list[dict]:
    return await get_incident_jobs(limit=min(limit, 100))


@app.get("/api/reviews/{job_id}/audit")
async def audit_review(job_id: int) -> dict:
    job = await get_review_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Review job not found")
    stored_hash = job.get("hcs_result_hash")
    result_json = job.get("result_json")
    if not result_json:
        return {"job_id": job_id, "status": "no_result", "verified": False}
    # Re-hash current result_json using same sort_keys=True convention
    try:
        current_data = json.loads(result_json)
        current_json = json.dumps(current_data, sort_keys=True)
        current_hash = hashlib.sha256(current_json.encode()).hexdigest()
    except Exception:
        current_hash = None
    verified = stored_hash is not None and current_hash == stored_hash
    tampered = stored_hash is not None and current_hash != stored_hash
    return {
        "job_id": job_id,
        "repo": job.get("repo"),
        "pr_number": job.get("pr_number"),
        "hcs_url": job.get("hcs_url"),
        "stored_hash": stored_hash,
        "current_hash": current_hash,
        "verified": verified,
        "tampered": tampered,
        "anchored": job.get("hcs_url") is not None,
    }


@app.get("/api/incidents/{job_id}/audit")
async def audit_incident(job_id: int) -> dict:
    job = await get_incident_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Incident job not found")
    stored_hash = job.get("hcs_result_hash")
    result_json = job.get("result_json")
    if not result_json:
        return {"job_id": job_id, "status": "no_result", "verified": False}
    try:
        current_data = json.loads(result_json)
        current_json = json.dumps(current_data, sort_keys=True)
        current_hash = hashlib.sha256(current_json.encode()).hexdigest()
    except Exception:
        current_hash = None
    verified = stored_hash is not None and current_hash == stored_hash
    tampered = stored_hash is not None and current_hash != stored_hash
    return {
        "job_id": job_id,
        "repo": job.get("repo"),
        "run_id": job.get("run_id"),
        "hcs_url": job.get("hcs_url"),
        "stored_hash": stored_hash,
        "current_hash": current_hash,
        "verified": verified,
        "tampered": tampered,
        "anchored": job.get("hcs_url") is not None,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "devpilot"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=settings.port, reload=True)

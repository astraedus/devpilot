from __future__ import annotations

import base64
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
ACCEPT_DIFF = "application/vnd.github.v3.diff"
ACCEPT_JSON = "application/vnd.github+json"
LOG_CONTENT_MAX = 5_000_000  # 5MB cap on log downloads


class GitHubTools:
    def __init__(self, token: str) -> None:
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def _client(self, accept: str = ACCEPT_JSON) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={**self._headers, "Accept": accept},
            timeout=30.0,
        )

    async def get_pr_diff(self, repo: str, pr_number: int) -> str:
        url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}"
        async with self._client(accept=ACCEPT_DIFF) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.text

    async def get_pr_files(self, repo: str, pr_number: int) -> list[dict[str, Any]]:
        url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}/files"
        results: list[dict[str, Any]] = []
        page = 1
        async with self._client() as client:
            while True:
                resp = await client.get(url, params={"per_page": 100, "page": page})
                resp.raise_for_status()
                batch = resp.json()
                if not batch:
                    break
                results.extend(batch)
                if len(batch) < 100:
                    break
                page += 1
        return results

    async def get_file_content(self, repo: str, path: str, ref: str) -> str:
        url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{path}"
        async with self._client() as client:
            resp = await client.get(url, params={"ref": ref})
            resp.raise_for_status()
            data = resp.json()
            if data.get("encoding") == "base64":
                return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
            return data.get("content", "")

    async def post_review(
        self,
        repo: str,
        pr_number: int,
        body: str,
        comments: list[dict[str, Any]] | None = None,
        event: str = "COMMENT",
    ) -> None:
        url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}/reviews"
        payload: dict[str, Any] = {"body": body, "event": event}
        if comments:
            payload["comments"] = comments
        async with self._client() as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Posted review to %s#%d", repo, pr_number)

    async def get_workflow_run_logs(self, repo: str, run_id: int) -> str:
        url = f"{GITHUB_API_BASE}/repos/{repo}/actions/runs/{run_id}/logs"
        async with self._client() as client:
            # GitHub returns a 302 redirect to the actual ZIP download
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/zip"):
                # Return raw bytes interpreted as text; for ZIP, extract inline text
                import io
                import zipfile

                try:
                    zf = zipfile.ZipFile(io.BytesIO(resp.content))
                    parts: list[str] = []
                    total = 0
                    for name in zf.namelist():
                        chunk = zf.read(name).decode("utf-8", errors="replace")
                        parts.append(f"=== {name} ===\n{chunk}")
                        total += len(chunk)
                        if total >= LOG_CONTENT_MAX:
                            parts.append("\n[logs truncated]")
                            break
                    return "\n".join(parts)
                except zipfile.BadZipFile:
                    return resp.text[:LOG_CONTENT_MAX]
            resp.raise_for_status()
            return resp.text[:LOG_CONTENT_MAX]

    async def post_pr_comment(self, repo: str, pr_number: int, body: str) -> None:
        url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
        async with self._client() as client:
            resp = await client.post(url, json={"body": body})
            resp.raise_for_status()
        logger.info("Posted comment to %s#%d", repo, pr_number)

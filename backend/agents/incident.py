from __future__ import annotations

import json
import logging
import os
import textwrap
from typing import Any

from backend.config import settings
from backend.models.schemas import IncidentReport

logger = logging.getLogger(__name__)

TRIAGE_INSTRUCTIONS = textwrap.dedent("""
    You are a CI/CD incident triage specialist. Analyze the provided GitHub Actions workflow logs.

    Identify:
    1. The root cause of the failure (be specific: test name, error message, file)
    2. Which files are most likely responsible
    3. A concrete suggested fix

    Respond ONLY with valid JSON matching this exact schema:
    {
      "root_cause": "<specific description of what failed and why>",
      "affected_files": ["<file1>", "<file2>"],
      "suggested_fix": "<actionable steps to fix the issue>",
      "severity": "<critical|high|medium>"
    }

    severity guide:
    - critical: build broken, deploy blocked
    - high: test suite failing, significant regression
    - medium: flaky test, non-blocking warning
""").strip()


async def _run_with_foundry(prompt: str) -> str:
    from azure.ai.projects import AIProjectClient
    from azure.identity import DefaultAzureCredential

    client = AIProjectClient.from_connection_string(
        conn_str=settings.azure_project_connection_string,
        credential=DefaultAzureCredential(),
    )
    agent = client.agents.create_agent(
        model=settings.azure_model_deployment,
        name="devpilot-incident-triager",
        instructions=TRIAGE_INSTRUCTIONS,
    )
    thread = client.agents.create_thread()
    client.agents.create_message(
        thread_id=thread.id,
        role="user",
        content=prompt,
    )
    run = client.agents.create_and_process_run(
        thread_id=thread.id,
        agent_id=agent.id,
    )
    messages = client.agents.list_messages(thread_id=thread.id)
    for msg in messages.data:
        if msg.role == "assistant":
            for content_block in msg.content:
                if hasattr(content_block, "text"):
                    return content_block.text.value
    client.agents.delete_agent(agent.id)
    raise RuntimeError("No assistant response from Azure AI Foundry")


async def _run_with_openai(prompt: str) -> str:
    from openai import AsyncOpenAI

    client = AsyncOpenAI()
    response = await client.chat.completions.create(
        model=settings.azure_model_deployment,
        messages=[
            {"role": "system", "content": TRIAGE_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


def _parse_report(raw: str) -> IncidentReport:
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse JSON from agent response: {raw[:200]}")
        data = json.loads(match.group())

    return IncidentReport(
        root_cause=data.get("root_cause", "Unknown failure"),
        affected_files=data.get("affected_files", []),
        suggested_fix=data.get("suggested_fix", ""),
        severity=data.get("severity", "high"),
    )


async def triage_incident(repo: str, run_id: int, logs: str) -> IncidentReport:
    prompt = (
        f"Repository: {repo}\n"
        f"Workflow Run ID: {run_id}\n\n"
        f"CI Logs:\n```\n{logs[:40000]}\n```"
    )

    use_foundry = bool(settings.azure_project_connection_string)
    use_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    use_openai = bool(os.environ.get("OPENAI_API_KEY"))

    try:
        if use_foundry:
            logger.info("Running incident triage via Azure AI Foundry for %s run %d", repo, run_id)
            raw = await _run_with_foundry(prompt)
        elif use_anthropic:
            logger.info("Running incident triage via Anthropic Claude for %s run %d", repo, run_id)
            from backend.agents.pr_reviewer import _run_with_anthropic as _anthropic
            raw = await _anthropic(f"{TRIAGE_INSTRUCTIONS}\n\n{prompt}")
        elif use_openai:
            logger.info("Running incident triage via OpenAI fallback for %s run %d", repo, run_id)
            raw = await _run_with_openai(prompt)
        else:
            logger.warning("No AI backend configured — returning mock incident report")
            raw = json.dumps({
                "root_cause": "Mock incident: AI backend not configured. Set AZURE_PROJECT_CONNECTION_STRING, ANTHROPIC_API_KEY, or OPENAI_API_KEY.",
                "affected_files": [],
                "suggested_fix": "Configure an AI backend to enable real incident triage.",
                "severity": "medium"
            })
        return _parse_report(raw)
    except Exception as exc:
        logger.error("Incident triage agent failed: %s", exc, exc_info=True)
        raise


def format_incident_comment(report: IncidentReport, run_id: int) -> str:
    severity_icons = {"critical": "CRITICAL", "high": "HIGH", "medium": "MEDIUM"}
    icon = severity_icons.get(report.severity, report.severity.upper())

    lines = [
        f"## DevPilot CI Incident Report (Run #{run_id})\n",
        f"**Severity:** {icon}\n",
        f"### Root Cause\n{report.root_cause}\n",
    ]
    if report.affected_files:
        lines.append("### Affected Files\n")
        for f in report.affected_files:
            lines.append(f"- `{f}`")
        lines.append("")
    lines.append(f"### Suggested Fix\n{report.suggested_fix}")
    lines.append("\n---\n_Posted by DevPilot_")
    return "\n".join(lines)

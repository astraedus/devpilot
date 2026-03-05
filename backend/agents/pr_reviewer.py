from __future__ import annotations

import json
import logging
import os
import textwrap
from typing import Any

from backend.config import settings
from backend.models.schemas import PRReview, ReviewIssue

logger = logging.getLogger(__name__)

REVIEW_INSTRUCTIONS = textwrap.dedent("""
    You are an expert code reviewer. Analyze the provided PR diff and file list.

    Evaluate the code for:
    1. Bugs and logic errors
    2. Security vulnerabilities (injection, auth, data exposure)
    3. Performance issues
    4. Style and readability violations
    5. Missing error handling

    Respond ONLY with valid JSON matching this exact schema:
    {
      "summary": "<1-3 sentence overall summary>",
      "issues": [
        {
          "file": "<filename>",
          "line": <line number, use 1 if unknown>,
          "severity": "<error|warning|info>",
          "comment": "<specific actionable feedback>"
        }
      ],
      "overall": "<approve|request_changes|comment>"
    }

    Be precise and actionable. If no issues exist, return an empty issues array and overall=approve.
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
        name="devpilot-pr-reviewer",
        instructions=REVIEW_INSTRUCTIONS,
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
    # Last assistant message contains the result
    for msg in messages.data:
        if msg.role == "assistant":
            for content_block in msg.content:
                if hasattr(content_block, "text"):
                    return content_block.text.value
    client.agents.delete_agent(agent.id)
    raise RuntimeError("No assistant response from Azure AI Foundry")


async def _run_with_anthropic(prompt: str) -> str:
    import anthropic
    client = anthropic.AsyncAnthropic()  # uses ANTHROPIC_API_KEY env var
    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=REVIEW_INSTRUCTIONS,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


async def _run_with_openai(prompt: str) -> str:
    from openai import AsyncOpenAI
    client = AsyncOpenAI()  # uses OPENAI_API_KEY env var
    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": REVIEW_INSTRUCTIONS},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or ""


def _mock_review(diff: str) -> str:
    """Return a realistic mock review for local testing without API keys."""
    import re
    files_mentioned = re.findall(r"^\+\+\+ b/(.+)$", diff, re.MULTILINE)
    file_str = files_mentioned[0] if files_mentioned else "unknown.py"
    return json.dumps({
        "summary": "Mock review: AI backend not configured. Set AZURE_PROJECT_CONNECTION_STRING, ANTHROPIC_API_KEY, or OPENAI_API_KEY to enable real reviews.",
        "issues": [
            {
                "file": file_str,
                "line": 1,
                "severity": "info",
                "comment": "This is a mock review. Configure an AI backend to get real code analysis."
            }
        ],
        "overall": "comment"
    })


def _parse_review(raw: str) -> PRReview:
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError:
        # Extract JSON block if wrapped in markdown
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise ValueError(f"Could not parse JSON from agent response: {raw[:200]}")
        data = json.loads(match.group())

    issues = [
        ReviewIssue(
            file=i.get("file", "unknown"),
            line=int(i.get("line", 1)),
            severity=i.get("severity", "info"),
            comment=i.get("comment", ""),
        )
        for i in data.get("issues", [])
    ]
    return PRReview(
        summary=data.get("summary", ""),
        issues=issues,
        overall=data.get("overall", "comment"),
    )


async def review_pr(repo: str, pr_number: int, diff: str, files: list[dict[str, Any]]) -> PRReview:
    file_names = [f.get("filename", "") for f in files]
    prompt = (
        f"Repository: {repo}\n"
        f"PR: #{pr_number}\n"
        f"Changed files: {', '.join(file_names)}\n\n"
        f"Diff:\n```\n{diff[:30000]}\n```"
    )

    use_foundry = bool(settings.azure_project_connection_string)
    use_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    use_openai = bool(os.environ.get("OPENAI_API_KEY"))

    try:
        if use_foundry:
            logger.info("Running PR review via Azure AI Foundry for %s#%d", repo, pr_number)
            raw = await _run_with_foundry(prompt)
        elif use_anthropic:
            logger.info("Running PR review via Anthropic Claude for %s#%d", repo, pr_number)
            raw = await _run_with_anthropic(prompt)
        elif use_openai:
            logger.info("Running PR review via OpenAI fallback for %s#%d", repo, pr_number)
            raw = await _run_with_openai(prompt)
        else:
            logger.warning("No AI backend configured — returning mock review for %s#%d", repo, pr_number)
            raw = _mock_review(diff)
        return _parse_review(raw)
    except Exception as exc:
        logger.error("PR review agent failed: %s", exc, exc_info=True)
        raise


def format_review_comment(review: PRReview) -> str:
    lines = ["## DevPilot PR Review\n", review.summary, ""]
    if review.issues:
        lines.append("### Issues Found\n")
        for issue in review.issues:
            badge = {"error": "ERROR", "warning": "WARN", "info": "INFO"}.get(issue.severity, issue.severity.upper())
            lines.append(f"- **[{badge}]** `{issue.file}` line {issue.line}: {issue.comment}")
        lines.append("")
    verdict_map = {
        "approve": "Verdict: Approved",
        "request_changes": "Verdict: Changes Requested",
        "comment": "Verdict: Comment Only",
    }
    lines.append(f"_{verdict_map.get(review.overall, review.overall)}_")
    lines.append("\n---\n_Posted by DevPilot_")
    return "\n".join(lines)

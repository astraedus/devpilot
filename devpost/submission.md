# DevPost Submission — DevPilot

## Title
DevPilot

## Tagline
AI agent that reviews your PRs and triages CI failures, powered by Azure AI Foundry.

## Inspiration
Every engineering team wastes hours on two recurring problems: writing thorough code reviews (which are often too short because reviewers are busy), and debugging CI failures (which involve manually reading cryptic logs). These problems happen dozens of times per week on any active codebase.

DevPilot automates both using Azure AI Foundry agents. It connects to GitHub via webhooks and runs autonomously in the background.

## What It Does

**PR Review Agent**
When a pull request is opened, DevPilot fetches the diff and file list via GitHub API, runs an Azure AI Foundry agent that analyzes the code for bugs, security vulnerabilities, performance issues, and style violations, then posts a structured review comment directly on GitHub. The review includes a summary, inline issue comments with severity levels, and a verdict (approve / request changes / comment).

**CI Incident Triage Agent**
When a GitHub Actions workflow fails, DevPilot fetches the failure logs, runs an Azure AI Foundry agent to identify the root cause, and posts an incident card on the PR. The card includes: root cause description, affected files, suggested fix, and severity level.

**Dashboard**
A Next.js dashboard shows all recent PR reviews and CI incidents in real time, backed by SQLite history.

## How We Built It

**Azure AI Foundry** is the core AI layer. We use the `azure-ai-projects` SDK to create agent runs against GPT-4o. The agent receives structured prompts (diff content, file list, or CI logs) and returns structured JSON responses that we parse into typed Python models.

**FastAPI** handles the webhook receiver. GitHub events arrive via POST /webhooks/github with HMAC-SHA256 signature validation. The webhook handler dispatches to the appropriate agent (PR review or incident triage) as a background task.

**GitHub API** provides the raw data: PR diffs, file lists, and workflow run logs via httpx async requests.

**Next.js 15** dashboard provides the review history UI, polling the FastAPI backend every 30 seconds.

**SQLite** stores job history (review jobs and incident jobs) with status tracking.

## Challenges

Getting Azure AI Foundry agent responses to reliably produce structured JSON required careful prompt engineering and a robust JSON parser that handles both clean JSON and JSON embedded in markdown code blocks.

The GitHub webhook flow requires running agent jobs as FastAPI background tasks to return a 200 response immediately while processing continues asynchronously.

## Accomplishments

- End-to-end agentic workflow: webhook in, GitHub comment out, no human in the loop
- Works with any GitHub repository via webhook configuration
- Graceful multi-tier fallback: Azure AI Foundry -> Gemini -> OpenAI -> mock
- Production-ready: HMAC webhook validation, async background tasks, error logging

## What We Learned

Azure AI Foundry's agent SDK is well-suited for stateful, multi-turn analysis tasks. The agent create/thread/run pattern adds overhead compared to direct completion calls, but the structured agent framework pays off for complex analysis workflows.

## What's Next

- Support for GitHub Pull Request review comments at specific lines (inline comments via the GitHub Reviews API)
- Slack notification integration for incident alerts
- Custom ruleset configuration per repository (.devpilot.yml)
- GitHub App packaging for one-click installation

## Built With

- azure-ai-projects
- azure-identity
- python
- fastapi
- github-api
- next.js
- tailwindcss
- sqlite
- httpx
- hiero-sdk-python (Hedera HCS audit trail)

## Links

- GitHub: https://github.com/astraedus/devpilot
- Demo video: [coming]

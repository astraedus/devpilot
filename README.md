# DevPilot

AI-powered GitHub PR review and CI incident triage agent.
Built for AI Dev Days (Microsoft Azure AI Foundry + GitHub).

## What it does

1. Receives GitHub webhooks (PR opened/updated, workflow_run failed)
2. PR Review agent: reads diff, generates structured review comments posted to GitHub
3. Incident agent: when CI fails, reads logs, identifies root cause, posts a root cause card as PR comment

## Architecture

- FastAPI backend (webhook receiver + REST API)
- Azure AI Foundry for agent orchestration (azure-ai-projects SDK)
- Falls back to OpenAI-compatible client if Foundry not configured
- GitHub API (httpx) for repo access and posting comments
- SQLite (aiosqlite) for job history
- Next.js 14 frontend (placeholder, see frontend/README.md)

## Quick start

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp ../.env.example ../.env
# Fill in .env with your credentials

python -m backend.main
```

## Webhook setup

Point your GitHub repo webhook to:
```
POST https://<your-host>/webhooks/github
Content-Type: application/json
Secret: <GITHUB_WEBHOOK_SECRET>
Events: Pull requests, Workflow runs
```

## API

| Endpoint | Description |
|---|---|
| POST /webhooks/github | GitHub webhook receiver |
| GET /api/reviews | List recent PR reviews |
| GET /api/incidents | List recent CI incidents |
| GET /health | Health check |

## Environment variables

See `.env.example` for all required variables.

| Variable | Description |
|---|---|
| AZURE_PROJECT_CONNECTION_STRING | From Azure AI Foundry project |
| AZURE_MODEL_DEPLOYMENT | Model to use (default: gpt-4o) |
| GITHUB_TOKEN | PAT with repo + workflow scope |
| GITHUB_WEBHOOK_SECRET | Webhook HMAC secret |

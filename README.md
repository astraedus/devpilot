# DevPilot

> AI agent that reviews your PRs and triages CI failures.

DevPilot is an agentic GitHub companion built on Azure AI Foundry. When a pull request is opened, DevPilot analyzes the diff, identifies bugs and security issues, and posts a structured code review as a GitHub review comment. When a CI workflow fails, DevPilot reads the failure logs, identifies the root cause, and posts an incident card on the PR.

Originally built for the Microsoft AI Dev Days Hackathon 2026 (cancelled -- registration closed Feb 22).

## Hackathon Submissions

| Hackathon | Platform | Track | Status |
|-----------|----------|-------|--------|
| ~~Microsoft AI Dev Days 2026~~ | ~~DevPost~~ | ~~AI Agents~~ | CANCELLED (registration closed Feb 22) |

**Note**: The Hedera HCS integration originally added to DevPilot was expanded into a standalone project, [ProofMint](https://github.com/astraedus/proofmint), which adds HTS NFT minting + Mirror Node verification on top of HCS. ProofMint is being submitted to the Hedera Hello Future Apex hackathon instead.

## What It Does

**PR Review**
- Triggered automatically when a PR is opened or updated via GitHub webhook
- Azure AI Foundry agent reads the diff and changed files
- Posts a structured review: summary, inline issue comments, verdict (approve / request changes / comment)
- Categorizes issues: bugs, security vulnerabilities, performance problems, style violations

**CI Incident Triage**
- Triggered when a GitHub Actions workflow run fails
- Agent reads failure logs and identifies root cause
- Posts an incident card: root cause, affected files, suggested fix, severity level

## Architecture

```
GitHub PR opened / CI failure
  |
  v
FastAPI webhook receiver (HMAC validated)
  |
  +-- PR Review Agent (Azure AI Foundry)
  |     +-- GitHub API: get diff + files
  |     +-- Azure AI Foundry: analyze code
  |     +-- GitHub API: post review comment
  |
  +-- Incident Agent (Azure AI Foundry)
        +-- GitHub API: get workflow logs
        +-- Azure AI Foundry: identify root cause
        +-- GitHub API: post incident card

Next.js Dashboard: live review + incident history
```

## Tech Stack

- **AI**: Azure AI Foundry (Agent Service) + GPT-4o
- **Backend**: Python 3.12, FastAPI, aiosqlite
- **Frontend**: Next.js 15, Tailwind CSS
- **Integrations**: GitHub API (webhooks, PR reviews, workflow logs)

## Setup

### Prerequisites

- Azure AI Foundry project (get connection string from Azure AI Studio)
- GitHub personal access token (repo, pull_requests scope)
- Python 3.12+, Node.js 18+

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp ../.env.example .env
# Edit .env with your credentials

uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # runs on port 3001
```

### GitHub Webhook

1. Go to your repository Settings > Webhooks > Add webhook
2. Payload URL: https://your-domain.com/webhooks/github
3. Content type: application/json
4. Secret: your GITHUB_WEBHOOK_SECRET value
5. Events: Select "Pull requests" and "Workflow runs"

## Environment Variables

```
AZURE_PROJECT_CONNECTION_STRING=  # From Azure AI Foundry project settings
AZURE_MODEL_DEPLOYMENT=gpt-4o     # Model deployment name
GITHUB_TOKEN=                     # PAT with repo + pull_requests scope
GITHUB_WEBHOOK_SECRET=            # Random secret for webhook HMAC
PORT=8000
```

## License

MIT

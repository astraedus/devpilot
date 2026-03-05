# DevPilot Demo Narration Script
# Voice: en-US-JennyNeural (female)
# Target: 90-120 seconds
# Recording: edge-tts + screen capture of DevPilot dashboard

---

## SECTION 1: Hook (0-10s)
Every engineering team reviews dozens of pull requests per week.
Most reviews are too short — reviewers are busy.
And when CI breaks, someone spends an hour reading cryptic logs.
DevPilot fixes both — automatically.

## SECTION 2: What It Is (10-25s)
DevPilot is an AI agent that sits in your GitHub repo.
When a pull request opens, it reviews the diff for bugs, security issues, and performance problems — then posts a structured comment in seconds.
When CI fails, it reads the logs, identifies the root cause, and posts an incident card with a suggested fix.

## SECTION 3: Live Demo — PR Review (25-60s)
Here's DevPilot in action.
I'm opening a pull request with some intentional issues — an unvalidated input, a raw SQL query, and missing error handling.
Within seconds, DevPilot's Azure AI Foundry agent analyzes the diff.
[pause for review to appear]
The review is structured: a summary, severity-tagged issues with file names and line numbers, and a final verdict.
This is better than most human reviews, and it happened automatically.

## SECTION 4: Live Demo — CI Triage (60-90s)
Now when CI fails —
[trigger a failed run]
DevPilot fetches the workflow logs, sends them to the AI agent, and posts an incident card.
Root cause, affected files, and a concrete fix suggestion.
No more staring at cryptic stack traces.

## SECTION 5: Dashboard (90-110s)
Everything shows up in the dashboard — a real-time view of all PR reviews and CI incidents across your repo.
Full history, verdict badges, severity levels.

## SECTION 6: Close (110-120s)
DevPilot is open source, works with any GitHub repo via a webhook, and uses Azure AI Foundry as its core AI engine.
Built in 48 hours. Ready for your team today.

---
# Technical notes for recording:
# - Start server: source venv/bin/activate && uvicorn backend.main:app --port 8000
# - Start frontend: cd frontend && npm run dev -- --port 3001
# - Start ngrok: ngrok http 8000 → register webhook at github.com/astraedus/devpilot/settings/hooks
# - Open PR on astraedus/devpilot (test_feature.py branch)
# - Show review posting in real time
# - Trigger CI failure → show incident card

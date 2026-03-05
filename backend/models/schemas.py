from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


# GitHub webhook payload (generic envelope)
class WebhookPayload(BaseModel):
    action: Optional[str] = None
    repository: Optional[dict[str, Any]] = None
    pull_request: Optional[dict[str, Any]] = None
    workflow_run: Optional[dict[str, Any]] = None
    sender: Optional[dict[str, Any]] = None


# PR review structures
class ReviewIssue(BaseModel):
    file: str
    line: int
    severity: str  # "error" | "warning" | "info"
    comment: str


class PRReview(BaseModel):
    summary: str
    issues: list[ReviewIssue]
    overall: str  # "approve" | "request_changes" | "comment"


# Incident triage structures
class IncidentReport(BaseModel):
    root_cause: str
    affected_files: list[str]
    suggested_fix: str
    severity: str  # "critical" | "high" | "medium"


# Database job records
class ReviewJob(BaseModel):
    id: Optional[int] = None
    repo: str
    pr_number: int
    status: str  # "pending" | "running" | "done" | "error"
    created_at: Optional[datetime] = None
    result_json: Optional[str] = None


class IncidentJob(BaseModel):
    id: Optional[int] = None
    repo: str
    run_id: int
    status: str  # "pending" | "running" | "done" | "error"
    created_at: Optional[datetime] = None
    result_json: Optional[str] = None

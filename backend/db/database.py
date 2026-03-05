from __future__ import annotations

import json
import logging
from datetime import datetime

import aiosqlite

logger = logging.getLogger(__name__)

DB_PATH = "devpilot.db"

CREATE_REVIEW_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS review_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo TEXT NOT NULL,
    pr_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    result_json TEXT
)
"""

CREATE_INCIDENT_JOBS_TABLE = """
CREATE TABLE IF NOT EXISTS incident_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    repo TEXT NOT NULL,
    run_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    result_json TEXT
)
"""


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_REVIEW_JOBS_TABLE)
        await db.execute(CREATE_INCIDENT_JOBS_TABLE)
        await db.commit()
    logger.info("Database initialized at %s", DB_PATH)


async def save_review_job(repo: str, pr_number: int, status: str = "pending", result: dict | None = None) -> int:
    now = datetime.utcnow().isoformat()
    result_json = json.dumps(result) if result else None
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO review_jobs (repo, pr_number, status, created_at, result_json) VALUES (?, ?, ?, ?, ?)",
            (repo, pr_number, status, now, result_json),
        )
        await db.commit()
        return cursor.lastrowid


async def update_review_job(job_id: int, status: str, result: dict | None = None) -> None:
    result_json = json.dumps(result) if result else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE review_jobs SET status = ?, result_json = ? WHERE id = ?",
            (status, result_json, job_id),
        )
        await db.commit()


async def get_review_jobs(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM review_jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def save_incident_job(repo: str, run_id: int, status: str = "pending", result: dict | None = None) -> int:
    now = datetime.utcnow().isoformat()
    result_json = json.dumps(result) if result else None
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO incident_jobs (repo, run_id, status, created_at, result_json) VALUES (?, ?, ?, ?, ?)",
            (repo, run_id, status, now, result_json),
        )
        await db.commit()
        return cursor.lastrowid


async def update_incident_job(job_id: int, status: str, result: dict | None = None) -> None:
    result_json = json.dumps(result) if result else None
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE incident_jobs SET status = ?, result_json = ? WHERE id = ?",
            (status, result_json, job_id),
        )
        await db.commit()


async def get_incident_jobs(limit: int = 20) -> list[dict]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM incident_jobs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

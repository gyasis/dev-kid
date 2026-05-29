#!/usr/bin/env python3
"""SQLite observability for sentinel / ma-loop runs.

Why this exists: the per-run ma-loop log (`.claude/sentinel/ma-loop-*.log`) is
the verbose drill-down, but loading it into an agent's context for every run is
expensive and noisy. This DB is the queryable INDEX — one row per ma-loop tier
run with the headline facts (tier, model, iterations, cost, status, the files it
changed, the test errors that drove it) plus a `log_path` pointer to the full
log. An agent SELECTs what it needs and only opens the log when it wants detail.
Keeps the context window quiet; every run stays searchable.

    sqlite3 .dk/observability.db \\
      "SELECT ts,tier,status,iterations,cost_usd,files_changed,errors,log_path
         FROM sentinel_runs ORDER BY id DESC LIMIT 10;"

Best-effort: any failure here is swallowed — observability must never break a run.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

DB_REL = ".dk/observability.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sentinel_runs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ts            TEXT NOT NULL,
    objective     TEXT,
    tier          TEXT,
    model         TEXT,
    iterations    INTEGER,
    cost_usd      REAL,
    duration_sec  REAL,
    status        TEXT,
    returncode    INTEGER,
    files_changed TEXT,   -- JSON array of paths the artisan wrote
    errors        TEXT,   -- JSON array of test/compile errors
    log_path      TEXT    -- pointer to the verbose ma-loop log (drill-down)
);
CREATE INDEX IF NOT EXISTS idx_runs_ts ON sentinel_runs(ts);
CREATE INDEX IF NOT EXISTS idx_runs_status ON sentinel_runs(status);
"""


def record_run(
    project_root,
    ts: str,
    objective: str,
    tier: str,
    model: str,
    iterations: int,
    cost_usd: float,
    duration_sec: float,
    status: str,
    returncode: Optional[int],
    files_changed: Optional[List[str]],
    errors: Optional[List[str]],
    log_path,
) -> None:
    """Insert one ma-loop tier run. Best-effort — never raises into the caller."""
    try:
        db = Path(project_root) / DB_REL
        db.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(db))
        try:
            con.executescript(_SCHEMA)
            con.execute(
                "INSERT INTO sentinel_runs (ts, objective, tier, model, iterations, "
                "cost_usd, duration_sec, status, returncode, files_changed, errors, log_path) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    ts,
                    objective,
                    tier,
                    model,
                    int(iterations or 0),
                    float(cost_usd or 0.0),
                    float(duration_sec or 0.0),
                    status,
                    int(returncode) if returncode is not None else -1,
                    json.dumps(files_changed or []),
                    json.dumps(errors or []),
                    str(log_path) if log_path else None,
                ),
            )
            con.commit()
        finally:
            con.close()
    except Exception:
        pass  # observability must never break the sentinel run

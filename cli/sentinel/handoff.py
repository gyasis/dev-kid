"""Claude Code handoff tier — alternative to expensive API tier escalation.

When a sentinel run can't pass on the cheap local tiers (Ollama, free Gemini),
the operator may prefer to leverage their existing Claude Code subscription
(flat-fee, no per-token cost) instead of burning per-token API credits on
OpenAI/Anthropic.

This module implements the file-based IPC between dev-kid (which writes a
"handoff request") and the active Claude Code session (which reads the request,
processes the task, writes back a "handoff complete" marker).

State directory: .claude/sentinel/SENTINEL-<TASK_ID>/handoff/
  request.json    — written by dev-kid when handoff tier is reached
  complete.json   — written by Claude Code after the operator handles the task

The wave executor polls for `complete.json` (with a configurable timeout) before
proceeding to the next task.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional


def _handoff_dir(task_id: str, project_root: Path) -> Path:
    return project_root / ".claude" / "sentinel" / f"SENTINEL-{task_id}" / "handoff"


def write_handoff_request(
    task_id: str,
    project_root: Path,
    task_description: str,
    test_command: str,
    file_locks: list[str],
    tier_history: list[Dict[str, Any]],
    cumulative_cost_so_far: float,
    cumulative_budget: float,
    reason: str = "cheap_tiers_exhausted",
) -> Path:
    """Write the handoff request file. Returns the path written.

    Claude Code (the operator) reads this file, performs the work the task
    requires (apply the fix that the lower tiers couldn't), then writes a
    `complete.json` companion to signal completion.
    """
    d = _handoff_dir(task_id, project_root)
    d.mkdir(parents=True, exist_ok=True)
    # Cleanup: stale complete.json from a prior aborted handoff would otherwise
    # be auto-applied to this fresh request — wave executor would silently mark
    # the task PASS with stale operator response. Always remove it first.
    stale_complete = d / "complete.json"
    if stale_complete.exists():
        try:
            stale_complete.unlink()
        except Exception:
            pass
    payload = {
        "task_id": task_id,
        "task_description": task_description,
        "test_command": test_command,
        "file_locks": file_locks,
        "reason": reason,
        "tier_history": tier_history,
        "cumulative_cost_so_far": cumulative_cost_so_far,
        "cumulative_budget": cumulative_budget,
        "requested_at": time.time(),
        "instructions_for_claude": (
            "The local sentinel tiers exhausted their iterations or budget. "
            "Please: (1) read the file_locks listed above, (2) apply the fix "
            "implied by task_description, (3) ensure the test_command passes, "
            "(4) write a `complete.json` next to this file with keys "
            "`succeeded`, `notes`, `files_modified`, `completed_at`."
        ),
    }
    request_path = d / "request.json"
    request_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return request_path


def write_handoff_complete(
    task_id: str,
    project_root: Path,
    succeeded: bool,
    notes: str = "",
    files_modified: Optional[list[str]] = None,
) -> Path:
    """Operator-side helper: write the complete marker. Used by the
    `dev-kid handoff-complete <task_id>` CLI command.
    """
    d = _handoff_dir(task_id, project_root)
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_id": task_id,
        "succeeded": bool(succeeded),
        "notes": notes,
        "files_modified": files_modified or [],
        "completed_at": time.time(),
    }
    complete_path = d / "complete.json"
    complete_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return complete_path


def read_handoff_complete(task_id: str, project_root: Path) -> Optional[Dict[str, Any]]:
    d = _handoff_dir(task_id, project_root)
    complete_path = d / "complete.json"
    if not complete_path.exists():
        return None
    try:
        return json.loads(complete_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_handoff_pending(task_id: str, project_root: Path) -> bool:
    """True if request exists but complete does not."""
    d = _handoff_dir(task_id, project_root)
    return (d / "request.json").exists() and not (d / "complete.json").exists()


def list_pending_handoffs(project_root: Path) -> list[Dict[str, Any]]:
    """Return all pending handoff requests across the project."""
    sentinel_root = project_root / ".claude" / "sentinel"
    if not sentinel_root.exists():
        return []
    pending = []
    for sentinel_dir in sentinel_root.iterdir():
        if not sentinel_dir.is_dir():
            continue
        if not sentinel_dir.name.startswith("SENTINEL-"):
            continue
        task_id = sentinel_dir.name.replace("SENTINEL-", "", 1)
        if is_handoff_pending(task_id, project_root):
            request_path = sentinel_dir / "handoff" / "request.json"
            try:
                pending.append(json.loads(request_path.read_text(encoding="utf-8")))
            except Exception:
                pending.append({"task_id": task_id, "error": "request.json unreadable"})
    return pending


def sweep_stale_handoffs(
    project_root: Path,
    older_than_hours: int = 24,
) -> list[Dict[str, str]]:
    """Move handoff dirs whose request.json is older than N hours into .attic/.

    Called by `dev-kid execute` startup so a crashed-mid-handoff invocation
    doesn't leave permanent stale state that confuses later runs.

    Returns list of {task_id, original_path, archived_path} for any swept dirs.
    """
    import uuid as _uuid

    sentinel_root = project_root / ".claude" / "sentinel"
    if not sentinel_root.exists():
        return []
    attic = sentinel_root / ".attic"
    cutoff = time.time() - (older_than_hours * 3600)
    swept: list[Dict[str, str]] = []
    attic_created = False
    for sentinel_dir in sentinel_root.iterdir():
        if not sentinel_dir.is_dir() or not sentinel_dir.name.startswith("SENTINEL-"):
            continue
        handoff_dir = sentinel_dir / "handoff"
        request_path = handoff_dir / "request.json"
        complete_path = handoff_dir / "complete.json"
        if not request_path.exists():
            continue
        # Stale if request older than cutoff AND no complete written
        if complete_path.exists():
            continue  # operator handled it; leave alone
        try:
            mtime = request_path.stat().st_mtime
        except Exception:
            continue
        if mtime >= cutoff:
            continue  # still fresh
        # Lazy attic creation (avoid wasted syscalls when nothing to sweep)
        if not attic_created:
            attic.mkdir(parents=True, exist_ok=True)
            attic_created = True
        # Use uuid suffix to defeat collision when two stale handoffs share the
        # same int(mtime) and the same task_id (e.g. CI re-runs hitting the
        # same second). Without this, rename() would silently replace or raise
        # on the existing target, both swallowed by the bare except below.
        archive_name = f"{int(mtime)}-{sentinel_dir.name}-{_uuid.uuid4().hex[:6]}"
        archived = attic / archive_name
        try:
            handoff_dir.rename(archived)
            swept.append(
                {
                    "task_id": sentinel_dir.name.replace("SENTINEL-", "", 1),
                    "original_path": str(handoff_dir),
                    "archived_path": str(archived),
                }
            )
        except Exception:
            pass
    return swept


def wait_for_handoff_complete(
    task_id: str,
    project_root: Path,
    timeout_sec: int = 1800,  # 30 min default
    poll_interval_sec: float = 2.0,
) -> Optional[Dict[str, Any]]:
    """Block until the operator writes complete.json or timeout elapses.

    Returns the parsed complete payload, or None on timeout.

    Note: this is intentionally synchronous and blocking. The wave executor
    uses it inline so the operator's response becomes the wave's pacing.
    For a fully async wave executor, this should be called from a thread.
    """
    start = time.time()
    while time.time() - start < timeout_sec:
        result = read_handoff_complete(task_id, project_root)
        if result is not None:
            return result
        time.sleep(poll_interval_sec)
    return None

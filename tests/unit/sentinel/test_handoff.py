"""Regression tests for cli/sentinel/handoff.py — Claude Code handoff IPC."""
import json
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "cli"))

from sentinel.handoff import (
    write_handoff_request,
    write_handoff_complete,
    read_handoff_complete,
    is_handoff_pending,
    list_pending_handoffs,
    wait_for_handoff_complete,
    sweep_stale_handoffs,
)


def _tmp_project():
    return Path(tempfile.mkdtemp(prefix="devkid-handoff-test-"))


def test_write_request_creates_file_with_required_keys():
    proj = _tmp_project()
    p = write_handoff_request(
        task_id="T001",
        project_root=proj,
        task_description="Fix the auth bug",
        test_command="pytest tests/test_auth.py",
        file_locks=["src/auth.py"],
        tier_history=[{"tier": "all-local", "result": "FAIL"}],
        cumulative_cost_so_far=2.5,
        cumulative_budget=25.0,
        reason="cheap_tiers_exhausted",
    )
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    for required in (
        "task_id", "task_description", "test_command", "file_locks",
        "reason", "tier_history", "cumulative_cost_so_far",
        "cumulative_budget", "requested_at", "instructions_for_claude",
    ):
        assert required in data, f"missing key: {required}"
    assert data["task_id"] == "T001"
    assert data["cumulative_cost_so_far"] == 2.5


def test_is_handoff_pending_true_when_request_no_complete():
    proj = _tmp_project()
    write_handoff_request("T002", proj, "x", "x", [], [], 0, 25, "x")
    assert is_handoff_pending("T002", proj)


def test_is_handoff_pending_false_when_complete_exists():
    proj = _tmp_project()
    write_handoff_request("T003", proj, "x", "x", [], [], 0, 25, "x")
    write_handoff_complete("T003", proj, succeeded=True)
    assert not is_handoff_pending("T003", proj)


def test_read_handoff_complete_returns_payload():
    proj = _tmp_project()
    write_handoff_complete("T004", proj, succeeded=True, notes="all good", files_modified=["src/a.py"])
    payload = read_handoff_complete("T004", proj)
    assert payload is not None
    assert payload["succeeded"] is True
    assert payload["notes"] == "all good"
    assert payload["files_modified"] == ["src/a.py"]


def test_read_handoff_complete_returns_none_when_missing():
    proj = _tmp_project()
    assert read_handoff_complete("T999-no-such", proj) is None


def test_list_pending_handoffs_collects_all_open():
    proj = _tmp_project()
    write_handoff_request("T010", proj, "first", "x", [], [], 0, 25, "x")
    write_handoff_request("T011", proj, "second", "x", [], [], 0, 25, "x")
    write_handoff_request("T012", proj, "third (already done)", "x", [], [], 0, 25, "x")
    write_handoff_complete("T012", proj, succeeded=True)

    pending = list_pending_handoffs(proj)
    task_ids = sorted(p.get("task_id") for p in pending)
    assert task_ids == ["T010", "T011"]


def test_wait_for_handoff_complete_short_timeout():
    proj = _tmp_project()
    write_handoff_request("T020", proj, "x", "x", [], [], 0, 25, "x")
    # No complete written → should time out quickly
    start = time.time()
    result = wait_for_handoff_complete("T020", proj, timeout_sec=2, poll_interval_sec=0.1)
    elapsed = time.time() - start
    assert result is None
    assert 1.5 <= elapsed <= 3.5  # roughly 2s


def test_wait_for_handoff_complete_returns_payload_when_ready():
    proj = _tmp_project()
    write_handoff_request("T021", proj, "x", "x", [], [], 0, 25, "x")
    # Pre-write complete so wait returns immediately
    write_handoff_complete("T021", proj, succeeded=True, notes="done")
    result = wait_for_handoff_complete("T021", proj, timeout_sec=5, poll_interval_sec=0.1)
    assert result is not None
    assert result["succeeded"] is True
    assert result["notes"] == "done"


def test_write_request_clears_stale_complete():
    """Writing a fresh request must remove any pre-existing complete.json so the
    next handoff doesn't auto-pass on stale operator response."""
    proj = _tmp_project()
    # Simulate prior aborted handoff: complete exists from previous attempt
    write_handoff_complete("T040", proj, succeeded=True, notes="stale prior response")
    assert read_handoff_complete("T040", proj) is not None
    # Now write a NEW request — stale complete must be cleared
    write_handoff_request("T040", proj, "new task", "x", [], [], 0, 25, "x")
    assert read_handoff_complete("T040", proj) is None
    assert is_handoff_pending("T040", proj)


def test_sweep_stale_handoffs_archives_old_requests():
    """sweep_stale_handoffs moves request.json older than N hours into .attic/
    if no complete.json was written."""
    import os
    proj = _tmp_project()
    # Create a stale handoff (24h+ old)
    write_handoff_request("T050", proj, "stale", "x", [], [], 0, 25, "x")
    request_path = proj / ".claude" / "sentinel" / "SENTINEL-T050" / "handoff" / "request.json"
    old_time = time.time() - (48 * 3600)  # 48 hours ago
    os.utime(request_path, (old_time, old_time))

    # Create a fresh handoff (recent)
    write_handoff_request("T051", proj, "fresh", "x", [], [], 0, 25, "x")

    # Create a stale-but-completed handoff (should NOT be archived)
    write_handoff_request("T052", proj, "stale-but-done", "x", [], [], 0, 25, "x")
    write_handoff_complete("T052", proj, succeeded=True)
    request_path_52 = proj / ".claude" / "sentinel" / "SENTINEL-T052" / "handoff" / "request.json"
    os.utime(request_path_52, (old_time, old_time))

    swept = sweep_stale_handoffs(proj, older_than_hours=24)

    swept_ids = [s["task_id"] for s in swept]
    assert "T050" in swept_ids  # archived: stale + no complete
    assert "T051" not in swept_ids  # not stale
    assert "T052" not in swept_ids  # has complete, leave alone


def test_request_is_self_describing_for_claude():
    """The request payload should contain enough info for Claude Code to act on it
    without consulting external state."""
    proj = _tmp_project()
    write_handoff_request(
        task_id="T030",
        project_root=proj,
        task_description="Refactor the parser",
        test_command="pytest tests/test_parser.py -v",
        file_locks=["src/parser.py", "tests/test_parser.py"],
        tier_history=[
            {"tier": "all-local", "iterations": 5, "result": "FAIL", "cost_usd": 0.0},
            {"tier": "groq-fast-free", "iterations": 5, "result": "FAIL", "cost_usd": 0.0},
        ],
        cumulative_cost_so_far=12.34,
        cumulative_budget=25.0,
        reason="cheap_tiers_exhausted",
    )
    request_path = proj / ".claude" / "sentinel" / "SENTINEL-T030" / "handoff" / "request.json"
    data = json.loads(request_path.read_text(encoding="utf-8"))
    assert "instructions_for_claude" in data
    assert "complete.json" in data["instructions_for_claude"]  # tells Claude how to respond
    assert data["test_command"] == "pytest tests/test_parser.py -v"
    assert len(data["tier_history"]) == 2

"""Regression tests for cli/sentinel/budget_tracker.py — global cumulative budget guard."""
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "cli"))

from sentinel.budget_tracker import BudgetTracker, get_tracker, reset_tracker


def _tmp_state() -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    f.close()
    Path(f.name).unlink()  # remove so tracker starts fresh
    return Path(f.name)


def test_starts_at_zero():
    state = _tmp_state()
    t = BudgetTracker(budget_usd=10.0, state_file=state)
    assert t.cumulative_cost == 0.0
    assert t.task_count == 0
    assert not t.is_exhausted()
    assert t.remaining_budget == 10.0


def test_record_increments_cumulatively():
    state = _tmp_state()
    t = BudgetTracker(budget_usd=10.0, state_file=state)
    t.record(2.5, 30.0, "T001")
    t.record(1.5, 15.0, "T002")
    assert t.cumulative_cost == 4.0
    assert t.task_count == 2
    assert t.remaining_budget == 6.0


def test_would_exceed_predicts_correctly():
    state = _tmp_state()
    t = BudgetTracker(budget_usd=10.0, state_file=state)
    t.record(8.0, 0, "T001")
    assert not t.would_exceed(1.0)
    assert not t.would_exceed(2.0)
    assert t.would_exceed(3.0)


def test_is_exhausted_triggers_at_cap():
    state = _tmp_state()
    t = BudgetTracker(budget_usd=10.0, state_file=state)
    assert not t.is_exhausted()
    t.record(10.0, 0, "T001")
    assert t.is_exhausted()


def test_should_handoff_per_task():
    state = _tmp_state()
    t = BudgetTracker(budget_usd=100.0, handoff_per_task_usd=2.0, state_file=state)
    assert not t.should_handoff_per_task(1.5)
    assert t.should_handoff_per_task(2.0)
    assert t.should_handoff_per_task(2.5)


def test_warn_if_approaching_idempotent():
    state = _tmp_state()
    t = BudgetTracker(budget_usd=10.0, warn_pct=0.8, state_file=state)
    t.record(7.5, 0, "T001")  # 75% — no warning yet
    assert t.warn_if_approaching() is None
    t.record(0.5, 0, "T002")  # 80% — warning fires
    msg = t.warn_if_approaching()
    assert msg is not None
    assert "80%" in msg
    # Second call: idempotent, no repeat
    assert t.warn_if_approaching() is None


def test_persists_across_instances():
    state = _tmp_state()
    t1 = BudgetTracker(budget_usd=10.0, state_file=state)
    t1.record(3.0, 30.0, "T001")
    t2 = BudgetTracker(budget_usd=10.0, state_file=state)
    assert t2.cumulative_cost == 3.0
    assert t2.task_count == 1


def test_corrupt_state_file_starts_fresh():
    state = _tmp_state()
    state.write_text("not valid json {{{", encoding="utf-8")
    t = BudgetTracker(budget_usd=10.0, state_file=state)
    assert t.cumulative_cost == 0.0
    # And it can still record + persist normally
    t.record(1.0, 0, "T001")
    assert t.cumulative_cost == 1.0


def test_reset_clears_state_and_file():
    state = _tmp_state()
    t = BudgetTracker(budget_usd=10.0, state_file=state)
    t.record(5.0, 30.0, "T001")
    assert state.exists()
    t.reset()
    assert t.cumulative_cost == 0.0
    assert t.task_count == 0
    assert not state.exists()


def test_get_tracker_singleton():
    reset_tracker()
    t1 = get_tracker(budget_usd=20.0)
    t2 = get_tracker(budget_usd=999.0)  # ignored — singleton already initialized
    assert t1 is t2
    assert t1.budget_usd == 20.0
    reset_tracker()


def test_summary_includes_key_numbers():
    state = _tmp_state()
    t = BudgetTracker(budget_usd=25.0, state_file=state)
    t.record(7.5, 120.0, "T001")
    s = t.summary()
    assert "$7.50" in s
    assert "$25.00" in s
    assert "1 sentinel" in s
    assert "$17.50 remaining" in s
    assert "2.0 cumulative minutes" in s

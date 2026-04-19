"""Cumulative cost & duration tracker shared across all sentinel runs in one wave-executor invocation.

Without this, the per-task `max_total_cost_usd` cap in tier_runner.py applies independently to
each sentinel — meaning a 65-task wave plan can theoretically burn 65 × $5 = $325 even though
each individual run is bounded.

The BudgetTracker enforces a GLOBAL ceiling across the whole `dev-kid execute` invocation. It
also surfaces approaching-limit warnings so the operator gets advance notice instead of a
sudden hard stop.

State persistence: the tracker writes to .claude/sentinel/.budget-state.json so that a
resumed `dev-kid execute` (after a crash or interruption) picks up the cumulative spend
already incurred — preventing budget reset abuse.

Usage from tier_runner.py:

    from sentinel.budget_tracker import get_tracker

    tracker = get_tracker()
    if tracker.would_exceed(estimated_cost):
        # Trigger handoff or halt
        return TierResult(skipped=True, reason="cumulative_budget_exhausted", ...)

    tracker.record(actual_cost, duration_sec, task_id)
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional


_STATE_FILE = Path(".claude/sentinel/.budget-state.json")
_DEFAULT_BUDGET_USD = 25.0  # global cap across all sentinels in one execute run
_DEFAULT_WARN_THRESHOLD_PCT = 0.80  # warn at 80% spent
_DEFAULT_HANDOFF_THRESHOLD_USD = 1.0  # per-task threshold that triggers handoff escalation


class BudgetTracker:
    """Tracks cumulative sentinel cost across one dev-kid execute invocation.

    Loaded once per process (singleton via get_tracker()), persists state to disk
    after each `record()` so that a re-launched dev-kid execute picks up where
    the previous one left off (within the same logical session).
    """

    def __init__(
        self,
        budget_usd: float = _DEFAULT_BUDGET_USD,
        warn_pct: float = _DEFAULT_WARN_THRESHOLD_PCT,
        handoff_per_task_usd: float = _DEFAULT_HANDOFF_THRESHOLD_USD,
        state_file: Optional[Path] = None,
    ) -> None:
        self.budget_usd = float(budget_usd)
        self.warn_pct = float(warn_pct)
        self.handoff_per_task_usd = float(handoff_per_task_usd)
        self.state_file = state_file if state_file is not None else _STATE_FILE
        self._cumulative_cost = 0.0
        self._cumulative_duration_sec = 0.0
        self._task_count = 0
        self._warned = False
        self._load()

    def _load(self) -> None:
        try:
            if self.state_file.exists():
                data = json.loads(self.state_file.read_text(encoding="utf-8"))
                self._cumulative_cost = float(data.get("cumulative_cost_usd", 0.0))
                self._cumulative_duration_sec = float(data.get("cumulative_duration_sec", 0.0))
                self._task_count = int(data.get("task_count", 0))
                self._warned = bool(data.get("warned", False))
        except Exception:
            # Corrupt state file? Start fresh — better to over-spend slightly
            # than to fail-stop on persistence corruption.
            pass

    def _persist(self) -> None:
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "cumulative_cost_usd": self._cumulative_cost,
                "cumulative_duration_sec": self._cumulative_duration_sec,
                "task_count": self._task_count,
                "budget_usd": self.budget_usd,
                "warned": self._warned,
                "updated_at": time.time(),
            }
            self.state_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            # Persistence failure is non-fatal for the run itself
            pass

    @property
    def cumulative_cost(self) -> float:
        return self._cumulative_cost

    @property
    def cumulative_duration_sec(self) -> float:
        return self._cumulative_duration_sec

    @property
    def remaining_budget(self) -> float:
        return max(0.0, self.budget_usd - self._cumulative_cost)

    @property
    def task_count(self) -> int:
        return self._task_count

    def would_exceed(self, projected_cost: float) -> bool:
        """Return True if recording `projected_cost` would push cumulative past the global cap."""
        return (self._cumulative_cost + projected_cost) > self.budget_usd

    def is_exhausted(self) -> bool:
        """Already at or past the global cap."""
        return self._cumulative_cost >= self.budget_usd

    def should_handoff_per_task(self, projected_cost: float) -> bool:
        """Return True if a single task's projected cost exceeds the per-task handoff threshold.

        Used by tier_runner to trigger Claude Code handoff (Phase B) instead of
        burning the budget on an expensive API tier.
        """
        return projected_cost >= self.handoff_per_task_usd

    def record(self, cost_usd: float, duration_sec: float, task_id: Optional[str] = None) -> None:
        self._cumulative_cost += float(cost_usd)
        self._cumulative_duration_sec += float(duration_sec)
        self._task_count += 1
        self._persist()

    def reset(self) -> None:
        """Reset cumulative state. Called explicitly by `dev-kid execute --fresh-budget`."""
        self._cumulative_cost = 0.0
        self._cumulative_duration_sec = 0.0
        self._task_count = 0
        self._warned = False
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception:
            pass

    def warn_if_approaching(self) -> Optional[str]:
        """Return a warning message if cumulative spend has crossed warn_pct of budget. Returns None otherwise.

        Idempotent — only warns once per process / state-file lifetime.
        """
        if self._warned:
            return None
        if self.budget_usd <= 0:
            return None
        pct_spent = self._cumulative_cost / self.budget_usd
        if pct_spent >= self.warn_pct:
            self._warned = True
            self._persist()
            return (
                f"⚠️  CUMULATIVE BUDGET WARNING: ${self._cumulative_cost:.2f} of "
                f"${self.budget_usd:.2f} spent across {self._task_count} sentinel(s) "
                f"({pct_spent * 100:.0f}% — threshold {self.warn_pct * 100:.0f}%). "
                f"Remaining budget: ${self.remaining_budget:.2f}."
            )
        return None

    def summary(self) -> str:
        return (
            f"BudgetTracker: ${self._cumulative_cost:.2f} of ${self.budget_usd:.2f} spent "
            f"across {self._task_count} sentinel(s), "
            f"${self.remaining_budget:.2f} remaining "
            f"({self._cumulative_duration_sec / 60:.1f} cumulative minutes)"
        )


_singleton: Optional[BudgetTracker] = None


def get_tracker(
    budget_usd: Optional[float] = None,
    warn_pct: Optional[float] = None,
    handoff_per_task_usd: Optional[float] = None,
) -> BudgetTracker:
    """Return the process-level singleton tracker.

    First call initializes from env vars or defaults:
      DEVKID_SENTINEL_BUDGET_USD          (default 25.0)
      DEVKID_SENTINEL_WARN_PCT            (default 0.80)
      DEVKID_SENTINEL_HANDOFF_THRESHOLD   (default 1.0 per task)

    Explicit args override env vars. Subsequent calls return the same instance
    regardless of args (use reset_tracker() for tests).
    """
    global _singleton
    if _singleton is None:
        b = budget_usd if budget_usd is not None else float(
            os.environ.get("DEVKID_SENTINEL_BUDGET_USD", _DEFAULT_BUDGET_USD)
        )
        w = warn_pct if warn_pct is not None else float(
            os.environ.get("DEVKID_SENTINEL_WARN_PCT", _DEFAULT_WARN_THRESHOLD_PCT)
        )
        h = handoff_per_task_usd if handoff_per_task_usd is not None else float(
            os.environ.get("DEVKID_SENTINEL_HANDOFF_THRESHOLD", _DEFAULT_HANDOFF_THRESHOLD_USD)
        )
        _singleton = BudgetTracker(budget_usd=b, warn_pct=w, handoff_per_task_usd=h)
    return _singleton


def reset_tracker() -> None:
    """Test helper: drop the singleton so the next get_tracker() rebuilds fresh."""
    global _singleton
    _singleton = None

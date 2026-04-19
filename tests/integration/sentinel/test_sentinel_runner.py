"""
Integration tests for cli/sentinel/runner.py — US1 acceptance scenarios

Tests (using fixtures from tests/integration/sentinel/fixtures/):
  1. PASS path: sentinel with mocked Tier 1 success → result=PASS, should_halt_wave=False
  2. FAIL path: both tiers fail → result=FAIL, should_halt_wave=True
  3. Ollama unreachable: Tier 1 skipped → Tier 2 escalation
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.sentinel.runner import SentinelRunner
from cli.sentinel import TierResult

FIXTURES = Path(__file__).parent / 'fixtures'


def _make_config(sentinel_placeholder_fail_on_detect=False):
    cfg = MagicMock()
    cfg.sentinel_tier1_ollama_url = "http://localhost:11434"
    cfg.sentinel_tier1_model = "qwen3-coder:30b"
    cfg.sentinel_tier1_max_iterations = 5
    cfg.sentinel_tier2_model = "claude-sonnet-4-20250514"
    cfg.sentinel_tier2_max_iterations = 10
    cfg.sentinel_tier2_max_budget_usd = 2.0
    cfg.sentinel_tier2_max_duration_min = 10
    cfg.sentinel_placeholder_fail_on_detect = sentinel_placeholder_fail_on_detect
    cfg.sentinel_placeholder_patterns = []
    cfg.sentinel_placeholder_exclude_paths = []
    return cfg


def _task(task_id="T001", file_locks=None):
    return {
        "task_id": task_id,
        "instruction": f"{task_id} Test task",
        "agent_role": "Developer",
        "file_locks": file_locks or ["src/auth.py"],
        "dependencies": [],
    }


# ---------------------------------------------------------------------------
# Scenario 1: PASS path
# ---------------------------------------------------------------------------

class TestPassPath:
    def test_tier1_success_returns_pass(self):
        config = _make_config()
        runner = SentinelRunner(config, PROJECT_ROOT)

        tier1_pass = TierResult(
            attempted=True, skipped=False, final_status="PASS", iterations=2
        )

        with patch("cli.sentinel.tier_runner.check_ollama_available", return_value=True), \
             patch("cli.sentinel.runner.detect_test_command", return_value="python -m pytest"), \
             patch("cli.sentinel.tier_runner.TierRunner.run_tier1", return_value=tier1_pass):
            result = runner.run(_task())

        assert result.result == "PASS"
        assert result.should_halt_wave is False
        assert result.tier_used == 1


# ---------------------------------------------------------------------------
# Scenario 2: FAIL path — both tiers exhausted
# ---------------------------------------------------------------------------

class TestFailPath:
    def test_both_tiers_fail_halts_wave(self):
        config = _make_config()
        runner = SentinelRunner(config, PROJECT_ROOT)

        tier1_fail = TierResult(attempted=True, skipped=False, final_status="FAIL")
        tier2_fail = TierResult(attempted=True, skipped=False, final_status="FAIL")

        with patch("cli.sentinel.tier_runner.check_ollama_available", return_value=True), \
             patch("cli.sentinel.runner.detect_test_command", return_value="python -m pytest"), \
             patch("cli.sentinel.tier_runner.TierRunner.run_tier1", return_value=tier1_fail), \
             patch("cli.sentinel.tier_runner.TierRunner.run_tier2", return_value=tier2_fail):
            result = runner.run(_task())

        assert result.result == "FAIL"
        assert result.should_halt_wave is True


# ---------------------------------------------------------------------------
# Scenario 3: Ollama unreachable → Tier 2 escalation
# ---------------------------------------------------------------------------

class TestOllamaUnreachable:
    def test_ollama_unavailable_escalates_to_tier2(self):
        config = _make_config()
        runner = SentinelRunner(config, PROJECT_ROOT)

        tier2_pass = TierResult(attempted=True, skipped=False, final_status="PASS", iterations=3)

        with patch("cli.sentinel.tier_runner.check_ollama_available", return_value=False), \
             patch("cli.sentinel.runner.detect_test_command", return_value="python -m pytest"), \
             patch("cli.sentinel.tier_runner.TierRunner.run_tier2", return_value=tier2_pass):
            result = runner.run(_task())

        assert result.result == "PASS"
        assert result.tier_used == 2


# ---------------------------------------------------------------------------
# Scenario 4: No test framework found
# ---------------------------------------------------------------------------

class TestNoTestFramework:
    def test_no_framework_returns_pass_without_loop(self):
        config = _make_config()
        runner = SentinelRunner(config, PROJECT_ROOT)

        with patch("cli.sentinel.runner.detect_test_command", return_value=None):
            result = runner.run(_task())

        # Without test framework: sentinel skips test loop, returns PASS
        assert result.result == "PASS"
        assert result.should_halt_wave is False


# ---------------------------------------------------------------------------
# Scenario 5: Placeholder scan blocks on violation
# ---------------------------------------------------------------------------

class TestPlaceholderBlocking:
    def test_placeholder_with_fail_on_detect_true_halts(self):
        config = _make_config(sentinel_placeholder_fail_on_detect=True)
        runner = SentinelRunner(config, PROJECT_ROOT)

        # Write placeholder content to a temp file OUTSIDE tests/ so scanner won't exclude it
        placeholder_content = (FIXTURES / "tasks_with_placeholder.py").read_text()
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', prefix='sentinel_prod_', dir='/tmp', delete=False
        ) as f:
            f.write(placeholder_content)
            tmp_path = f.name

        task = _task(file_locks=[tmp_path])

        # No need to mock test command — scanner should halt before test loop
        result = runner.run(task)

        assert result.result == "FAIL"
        assert result.should_halt_wave is True
        assert len(result.placeholder_violations) > 0

"""
Unit tests for cli/sentinel/tier_runner.py

Tests:
  - check_ollama_available: reachable vs unreachable
  - TierRunner.run_tier1: success, failure, Ollama unreachable → skip
  - TierRunner.run_tier2: success, failure, no API key
  - _parse_micro_agent_output: various stdout formats
"""

import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.sentinel.tier_runner import (
    TierRunner,
    check_ollama_available,
    _parse_micro_agent_output,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(
    *,
    tier1_url="http://localhost:11434",
    tier1_model="qwen3-coder:30b",
    tier1_max_iter=5,
    tier2_model="claude-sonnet-4-20250514",
    tier2_max_iter=10,
    tier2_budget=2.0,
    tier2_duration=10,
):
    cfg = MagicMock()
    cfg.sentinel_tier1_ollama_url = tier1_url
    cfg.sentinel_tier1_model = tier1_model
    cfg.sentinel_tier1_max_iterations = tier1_max_iter
    cfg.sentinel_tier2_model = tier2_model
    cfg.sentinel_tier2_max_iterations = tier2_max_iter
    cfg.sentinel_tier2_max_budget_usd = tier2_budget
    cfg.sentinel_tier2_max_duration_min = tier2_duration
    return cfg


def _completed(returncode=0, stdout="", stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ---------------------------------------------------------------------------
# check_ollama_available
# ---------------------------------------------------------------------------

class TestCheckOllamaAvailable:
    def test_reachable_returns_true(self):
        with patch("subprocess.run", return_value=_completed(0)):
            assert check_ollama_available("http://localhost:11434") is True

    def test_non_zero_exit_returns_false(self):
        with patch("subprocess.run", return_value=_completed(1)):
            assert check_ollama_available("http://localhost:11434") is False

    def test_exception_returns_false(self):
        with patch("subprocess.run", side_effect=Exception("connection refused")):
            assert check_ollama_available("http://localhost:11434") is False

    def test_timeout_returns_false(self):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("curl", 5)):
            assert check_ollama_available("http://localhost:11434") is False


# ---------------------------------------------------------------------------
# TierRunner.run_tier1
# ---------------------------------------------------------------------------

class TestRunTier1:
    def test_tier1_success(self):
        config = _make_config()
        runner = TierRunner(config)
        stdout = "Iterations: 2 total\nCost: $0.000 total\nDuration: 12.5s\n"

        with patch("cli.sentinel.tier_runner.check_ollama_available", return_value=True), \
             patch("subprocess.run", return_value=_completed(0, stdout)):
            result = runner.run_tier1("fix auth", "python -m pytest", config)

        assert result.attempted is True
        assert result.skipped is False
        assert result.final_status == "PASS"
        assert result.passed is True
        assert result.iterations == 2
        assert result.duration_sec == 12.5

    def test_tier1_failure(self):
        config = _make_config()
        runner = TierRunner(config)

        with patch("cli.sentinel.tier_runner.check_ollama_available", return_value=True), \
             patch("subprocess.run", return_value=_completed(1)):
            result = runner.run_tier1("fix auth", "python -m pytest", config)

        assert result.final_status == "FAIL"
        assert result.failed is True

    def test_ollama_unreachable_returns_skipped(self):
        config = _make_config()
        runner = TierRunner(config)

        with patch("cli.sentinel.tier_runner.check_ollama_available", return_value=False):
            result = runner.run_tier1("fix auth", "python -m pytest", config)

        assert result.attempted is True
        assert result.skipped is True
        assert result.final_status is None


# ---------------------------------------------------------------------------
# TierRunner.run_tier2
# ---------------------------------------------------------------------------

class TestRunTier2:
    def test_tier2_success(self):
        config = _make_config()
        runner = TierRunner(config)
        stdout = "Iterations: 4 total\nCost: $0.856 total\nDuration: 95.2s\n"

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("subprocess.run", return_value=_completed(0, stdout)):
            result = runner.run_tier2("fix payment", "python -m pytest", config)

        assert result.final_status == "PASS"
        assert result.iterations == 4
        assert abs(result.cost_usd - 0.856) < 0.001

    def test_tier2_failure(self):
        config = _make_config()
        runner = TierRunner(config)

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}), \
             patch("subprocess.run", return_value=_completed(1)):
            result = runner.run_tier2("fix payment", "python -m pytest", config)

        assert result.final_status == "FAIL"

    def test_no_api_key_returns_skipped(self):
        config = _make_config()
        runner = TierRunner(config)

        env_without_key = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env_without_key, clear=True):
            result = runner.run_tier2("fix payment", "python -m pytest", config)

        assert result.attempted is False
        assert result.skipped is True


# ---------------------------------------------------------------------------
# _parse_micro_agent_output
# ---------------------------------------------------------------------------

class TestParseMicroAgentOutput:
    def test_all_fields_present(self):
        stdout = (
            "Iterations: 3 total\n"
            "Cost: $0.123 total\n"
            "Duration: 45.7s\n"
        )
        parsed = _parse_micro_agent_output(stdout)
        assert parsed["iterations"] == 3
        assert abs(parsed["cost_usd"] - 0.123) < 0.001
        assert abs(parsed["duration_sec"] - 45.7) < 0.01

    def test_empty_stdout_returns_zeros(self):
        parsed = _parse_micro_agent_output("")
        assert parsed == {"iterations": 0, "cost_usd": 0.0, "duration_sec": 0.0}

    def test_partial_output(self):
        parsed = _parse_micro_agent_output("Iterations: 7 total")
        assert parsed["iterations"] == 7
        assert parsed["cost_usd"] == 0.0

    def test_case_insensitive(self):
        parsed = _parse_micro_agent_output("ITERATIONS: 2 Total\nCOST: $1.00 TOTAL")
        assert parsed["iterations"] == 2
        assert parsed["cost_usd"] == 1.0

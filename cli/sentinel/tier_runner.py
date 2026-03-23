"""
Integration Sentinel — Tier Runner

Executes the two-tier micro-agent test loop:
  Tier 1: Local Ollama (qwen3-coder:30b, max 5 iterations, free)
  Tier 2: Cloud Claude (claude-sonnet-4-20250514, max 10 iterations, $2.00 budget)

Tier 2 activates only if Tier 1 exhausts its iterations with a non-zero exit.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import SentinelConfig, TierResult


def sentinel_health_check(config) -> dict:
    """Check all sentinel providers and return health status.

    Checks:
      - micro-agent CLI is installed
      - Tier 1: Ollama server is reachable
      - Tier 2: ANTHROPIC_API_KEY is set

    Args:
        config: SentinelConfig (ConfigSchema) with sentinel_ attributes.

    Returns:
        Dict with keys: micro_agent_installed, tier1_available, tier1_url,
        tier2_available, any_tier_available, warnings (list[str]).
    """
    from shutil import which

    warnings: list = []

    # Check micro-agent CLI
    micro_agent_installed = which("micro-agent") is not None
    if not micro_agent_installed:
        warnings.append(
            "micro-agent CLI not found — install with: npm install -g @builder.io/micro-agent"
        )

    # Check Tier 1 (Ollama)
    ollama_url = getattr(config, "sentinel_tier1_ollama_url", "http://localhost:11434")
    tier1_available = check_ollama_available(ollama_url)
    if not tier1_available:
        warnings.append(f"Tier 1: Ollama not reachable at {ollama_url}")

    # Check Tier 2 (Anthropic API key)
    tier2_available = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    if not tier2_available:
        warnings.append("Tier 2: ANTHROPIC_API_KEY not set in environment")

    any_tier_available = micro_agent_installed and (tier1_available or tier2_available)

    return {
        "micro_agent_installed": micro_agent_installed,
        "tier1_available": tier1_available,
        "tier1_url": ollama_url,
        "tier2_available": tier2_available,
        "any_tier_available": any_tier_available,
        "warnings": warnings,
    }


def check_ollama_available(base_url: str) -> bool:
    """Check whether the Ollama server is reachable.

    Uses `curl -sf` for a lightweight HEAD-style probe to /api/tags.

    Args:
        base_url: Ollama server base URL (e.g. "http://192.168.0.159:11434").

    Returns:
        True if the server responds with exit code 0, False otherwise.
    """
    try:
        result = subprocess.run(
            ["curl", "-sf", f"{base_url}/api/tags"],
            timeout=5,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


class TierRunner:
    """Runs the micro-agent in either Tier 1 (Ollama) or Tier 2 (cloud)."""

    def __init__(self, config: "SentinelConfig") -> None:
        self._config = config

    def run_tier1(
        self,
        objective: str,
        test_cmd: str,
        config: "SentinelConfig",
    ) -> "TierResult":
        """Run micro-agent Tier 1 (local Ollama).

        Skips if Ollama is not reachable — caller should escalate to Tier 2.

        Args:
            objective: The task description / fix objective.
            test_cmd: Shell command to validate the fix (e.g. "python -m pytest").
            config: SentinelConfig with tier1 settings.

        Returns:
            TierResult with attempted/skipped/passed flags.
        """
        from . import TierResult

        ollama_url = getattr(
            config, "sentinel_tier1_ollama_url", "http://192.168.0.159:11434"
        )
        model = getattr(config, "sentinel_tier1_model", "qwen3-coder:30b")
        max_iter = getattr(config, "sentinel_tier1_max_iterations", 5)

        if not check_ollama_available(ollama_url):
            print(
                f"      ⚠️  Tier 1: Ollama not reachable at {ollama_url} — skipping to Tier 2"
            )
            return TierResult(
                attempted=True,
                skipped=True,
                model=model,
                ollama_url=ollama_url,
                final_status=None,
            )

        env = {**os.environ, "OLLAMA_BASE_URL": ollama_url}

        cmd = [
            "micro-agent",
            "--objective",
            objective,
            "--test",
            test_cmd,
            "--max-iterations",
            str(max_iter),
            "--simple",
            str(max_iter),
            "--no-escalate",
            "--artisan",
            f"ollama:{model}",
        ]

        print(
            f"      🤖 Tier 1: micro-agent (ollama:{model}, max {max_iter} iterations)..."
        )
        start = time.time()
        result = subprocess.run(
            cmd,
            env=env,
            timeout=300,
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.time() - start

        parsed = _parse_micro_agent_output(result.stdout)
        final_status = "PASS" if result.returncode == 0 else "FAIL"

        return TierResult(
            attempted=True,
            skipped=False,
            model=model,
            ollama_url=ollama_url,
            iterations=parsed.get("iterations", 0),
            cost_usd=parsed.get("cost_usd", 0.0),
            duration_sec=parsed.get("duration_sec", elapsed),
            final_status=final_status,
            error_messages=[result.stderr.strip()] if result.stderr.strip() else [],
        )

    def run_tier2(
        self,
        objective: str,
        test_cmd: str,
        config: "SentinelConfig",
    ) -> "TierResult":
        """Run micro-agent Tier 2 (cloud Claude).

        Requires ANTHROPIC_API_KEY in the environment.

        Args:
            objective: The task description / fix objective.
            test_cmd: Shell command to validate the fix.
            config: SentinelConfig with tier2 settings.

        Returns:
            TierResult with full result data.
        """
        from . import TierResult

        model = getattr(config, "sentinel_tier2_model", "claude-sonnet-4-20250514")
        max_iter = getattr(config, "sentinel_tier2_max_iterations", 10)
        max_budget = getattr(config, "sentinel_tier2_max_budget_usd", 2.0)
        max_duration = getattr(config, "sentinel_tier2_max_duration_min", 10)

        if "ANTHROPIC_API_KEY" not in os.environ:
            return TierResult(
                attempted=False,
                skipped=True,
                model=model,
                error_messages=["ANTHROPIC_API_KEY not set — Tier 2 unavailable"],
                final_status="FAIL",
            )

        cmd = [
            "micro-agent",
            "--objective",
            objective,
            "--test",
            test_cmd,
            "--max-iterations",
            str(max_iter),
            "--artisan",
            model,
            "--max-budget",
            str(max_budget),
            "--max-duration",
            str(max_duration),
        ]

        print(
            f"      🌩️  Tier 2: micro-agent ({model}, max {max_iter} iterations, ${max_budget} budget)..."
        )
        start = time.time()
        result = subprocess.run(
            cmd,
            timeout=600,
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed = time.time() - start

        parsed = _parse_micro_agent_output(result.stdout)
        final_status = "PASS" if result.returncode == 0 else "FAIL"

        return TierResult(
            attempted=True,
            skipped=False,
            model=model,
            ollama_url=None,
            iterations=parsed.get("iterations", 0),
            cost_usd=parsed.get("cost_usd", 0.0),
            duration_sec=parsed.get("duration_sec", elapsed),
            final_status=final_status,
            error_messages=[result.stderr.strip()] if result.stderr.strip() else [],
        )


def _parse_micro_agent_output(stdout: str) -> dict:
    """Extract summary metrics from micro-agent stdout.

    Looks for lines like:
      Iterations: 3 total
      Cost: $0.123 total
      Duration: 45.2s

    Args:
        stdout: Raw micro-agent stdout.

    Returns:
        Dict with 'iterations', 'cost_usd', 'duration_sec' (zero-values if not found).
    """
    result = {"iterations": 0, "cost_usd": 0.0, "duration_sec": 0.0}

    iter_match = re.search(r"Iterations:\s*(\d+)", stdout, re.IGNORECASE)
    if iter_match:
        result["iterations"] = int(iter_match.group(1))

    cost_match = re.search(r"Cost:\s*\$?([\d.]+)", stdout, re.IGNORECASE)
    if cost_match:
        result["cost_usd"] = float(cost_match.group(1))

    dur_match = re.search(r"Duration:\s*([\d.]+)s", stdout, re.IGNORECASE)
    if dur_match:
        result["duration_sec"] = float(dur_match.group(1))

    return result

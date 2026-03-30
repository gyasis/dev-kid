"""
Integration Sentinel — Tier Runner

Supports two modes:
  1. N-tier escalation via ralph-tiers.json (--tier-config) — micro-agent handles
     the full escalation ladder internally.  Configured via sentinel.tiers_file.
  2. Legacy 2-tier mode (Ollama → Claude) — used when tiers_file is empty.

When tiers_file is set, sentinel.min_tier lets you skip cheap tiers and start
from a stronger model (e.g. "azure-heavy" for weekend work).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import SentinelConfig, TierResult


def sentinel_health_check(config) -> dict:
    """Check all sentinel providers and return health status.

    Checks:
      - micro-agent CLI is installed
      - Tier 1: Ollama server is reachable
      - Tier 2: ANTHROPIC_API_KEY is set
      - Azure: AZURE_OPENAI_API_KEY or AZURE_API_KEY is set
      - Tiers file: exists and is valid JSON (when configured)

    Args:
        config: SentinelConfig (ConfigSchema) with sentinel_ attributes.

    Returns:
        Dict with keys: micro_agent_installed, tier1_available, tier1_url,
        tier2_available, azure_available, tiers_file_valid,
        any_tier_available, warnings (list[str]).
    """
    from shutil import which

    warnings: list = []

    # Check micro-agent CLI
    micro_agent_installed = which("micro-agent") is not None
    if not micro_agent_installed:
        warnings.append(
            "micro-agent CLI not found — install with: npm install -g @gyasis/micro-agent"
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

    # Check Azure OpenAI
    azure_available = bool(
        os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
        or os.environ.get("AZURE_API_KEY", "").strip()
    )
    if not azure_available:
        warnings.append(
            "Azure: AZURE_OPENAI_API_KEY / AZURE_API_KEY not set in environment"
        )

    # Check tiers file validity (when configured)
    tiers_file = getattr(config, "sentinel_tiers_file", "")
    tiers_file_valid = False
    tiers_file_tier_count = 0
    if tiers_file:
        tiers_path = Path(tiers_file)
        if tiers_path.exists():
            try:
                data = json.loads(tiers_path.read_text(encoding="utf-8"))
                tiers = data.get("tiers", [])
                tiers_file_valid = len(tiers) > 0
                tiers_file_tier_count = len(tiers)
                if not tiers_file_valid:
                    warnings.append(f"Tiers file {tiers_file} has no tiers defined")
            except Exception as exc:
                warnings.append(f"Tiers file {tiers_file} is invalid JSON: {exc}")
        else:
            warnings.append(f"Tiers file not found: {tiers_file}")

    # Determine overall availability
    if tiers_file and tiers_file_valid:
        # In N-tier mode, need micro-agent + at least one provider
        any_tier_available = micro_agent_installed and (
            tier1_available or tier2_available or azure_available
        )
    else:
        # Legacy mode: need micro-agent + ollama or anthropic
        any_tier_available = micro_agent_installed and (
            tier1_available or tier2_available
        )

    return {
        "micro_agent_installed": micro_agent_installed,
        "tier1_available": tier1_available,
        "tier1_url": ollama_url,
        "tier2_available": tier2_available,
        "azure_available": azure_available,
        "tiers_file_valid": tiers_file_valid,
        "tiers_file_tier_count": tiers_file_tier_count,
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
            config, "sentinel_tier1_ollama_url", "http://localhost:11434"
        )
        model = getattr(config, "sentinel_tier1_model", "") or "qwen2.5-coder:latest"
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

        model = getattr(config, "sentinel_tier2_model", "") or "claude-sonnet-4-20250514"
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


    def run_tiered(
        self,
        objective: str,
        test_cmd: str,
        config: "SentinelConfig",
        project_root: Path,
    ) -> "TierResult":
        """Run micro-agent with --tier-config for N-tier escalation.

        micro-agent handles the full escalation ladder internally.
        We pass the tiers file and optional min_tier filter, then parse
        the single pass/fail result.

        Args:
            objective: The task description / fix objective.
            test_cmd: Shell command to validate the fix.
            config: SentinelConfig with tiers_file and min_tier settings.
            project_root: Project root for resolving relative paths.

        Returns:
            TierResult with the final outcome from the tiered run.
        """
        from . import TierResult

        tiers_file = getattr(config, "sentinel_tiers_file", "")
        min_tier = getattr(config, "sentinel_min_tier", "")
        max_cost = getattr(config, "sentinel_max_total_cost_usd", 5.0)
        max_duration = getattr(config, "sentinel_max_total_duration_min", 30)

        # Resolve tiers file path
        tiers_path = Path(tiers_file)
        if not tiers_path.is_absolute():
            tiers_path = project_root / tiers_file
        if not tiers_path.exists():
            return TierResult(
                attempted=False,
                skipped=True,
                tier_name="tiered",
                error_messages=[f"Tiers file not found: {tiers_path}"],
                final_status="FAIL",
            )

        # If min_tier is set, create a filtered tiers file that skips earlier tiers
        effective_tiers_path = tiers_path
        temp_file = None
        if min_tier:
            effective_tiers_path, temp_file = _filter_tiers_file(
                tiers_path, min_tier
            )
            if effective_tiers_path is None:
                return TierResult(
                    attempted=False,
                    skipped=True,
                    tier_name="tiered",
                    error_messages=[
                        f"min_tier '{min_tier}' not found in {tiers_path}"
                    ],
                    final_status="FAIL",
                )

        cmd = [
            "micro-agent",
            "run",
            ".",  # target = current directory
            "--objective",
            objective,
            "--test",
            test_cmd,
            "--tier-config",
            str(effective_tiers_path),
            "--max-budget",
            str(max_cost),
            "--max-duration",
            str(max_duration),
        ]

        # Determine tier names for display
        try:
            tiers_data = json.loads(tiers_path.read_text(encoding="utf-8"))
            tier_names = [t["name"] for t in tiers_data.get("tiers", [])]
            if min_tier:
                start_idx = next(
                    (i for i, n in enumerate(tier_names) if n == min_tier), 0
                )
                tier_names = tier_names[start_idx:]
            tier_display = " → ".join(tier_names)
        except Exception:
            tier_display = "N-tier"

        print(
            f"      🚀 Tiered escalation: {tier_display} "
            f"(${max_cost} budget, {max_duration}min cap)..."
        )

        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                timeout=max_duration * 60 + 60,  # buffer beyond max_duration
                capture_output=True,
                text=True,
                check=False,
                cwd=str(project_root),
            )
        except subprocess.TimeoutExpired:
            return TierResult(
                attempted=True,
                skipped=False,
                tier_name="tiered",
                duration_sec=time.time() - start,
                final_status="FAIL",
                error_messages=["Tiered run timed out"],
            )
        finally:
            if temp_file:
                try:
                    Path(temp_file).unlink(missing_ok=True)
                except Exception:
                    pass

        elapsed = time.time() - start
        parsed = _parse_micro_agent_output(result.stdout)
        winning_tier = _extract_winning_tier(result.stdout)
        final_status = "PASS" if result.returncode == 0 else "FAIL"

        return TierResult(
            attempted=True,
            skipped=False,
            tier_name=winning_tier or "tiered",
            model=_extract_winning_model(result.stdout),
            iterations=parsed.get("iterations", 0),
            cost_usd=parsed.get("cost_usd", 0.0),
            duration_sec=parsed.get("duration_sec", elapsed),
            final_status=final_status,
            error_messages=(
                [result.stderr.strip()] if result.stderr.strip() else []
            ),
        )


def _filter_tiers_file(tiers_path: Path, min_tier: str) -> tuple:
    """Create a temporary tiers file that starts from min_tier.

    Args:
        tiers_path: Path to the original ralph-tiers.json.
        min_tier: Tier name to start from (e.g. "azure-heavy").

    Returns:
        (effective_path, temp_file_path) or (None, None) if min_tier not found.
    """
    try:
        data = json.loads(tiers_path.read_text(encoding="utf-8"))
        tiers = data.get("tiers", [])
        start_idx = None
        for i, t in enumerate(tiers):
            if t.get("name") == min_tier:
                start_idx = i
                break
        if start_idx is None:
            return None, None

        filtered = {**data, "tiers": tiers[start_idx:]}
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            prefix="ralph-tiers-filtered-",
            delete=False,
        )
        json.dump(filtered, tmp, indent=2)
        tmp.close()
        return Path(tmp.name), tmp.name
    except Exception:
        return None, None


def _extract_winning_tier(stdout: str) -> str:
    """Extract the tier name that achieved PASS from micro-agent output.

    Looks for patterns like:
      Tier 3: azure-mini [full] — PASS
      ✅ Tier 2 (azure-nano) passed
    """
    # Pattern: Tier N: name [mode] — PASS
    match = re.search(
        r"Tier\s+\d+:\s+(\S+)\s+\[.*?\]\s*[—-]\s*PASS", stdout, re.IGNORECASE
    )
    if match:
        return match.group(1)
    # Pattern: ✅ Tier N (name) passed
    match = re.search(r"Tier\s+\d+\s*\((\S+)\)\s*passed", stdout, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def _extract_winning_model(stdout: str) -> str:
    """Extract the model name from micro-agent tier output.

    Looks for patterns like:
      Artisan: azure/gpt-4.1-mini
      Model: azure/gpt-5
    """
    match = re.search(r"Artisan:\s*(\S+)", stdout, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"Model:\s*(\S+)", stdout, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


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

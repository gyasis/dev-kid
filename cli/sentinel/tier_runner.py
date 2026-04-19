"""
Integration Sentinel — Tier Runner

Supports two modes:
  1. N-tier escalation via ralph-tiers.json (--tier-config) — micro-agent handles
     the full escalation ladder internally.  Configured via sentinel.tiers_file.
  2. Legacy 2-tier mode (Ollama → Claude) — used when tiers_file is empty.

When tiers_file is set, sentinel.min_tier lets you skip cheap tiers and start
from a stronger model (e.g. "openai-heavy" for heavy-lift sessions).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import SentinelConfig, TierResult


def sentinel_health_check(config) -> dict:
    """Check all sentinel providers and return health status.

    When a tiers file is configured (ralph-tiers.json), validates each tier's
    specific model endpoints — not just generic provider availability. This
    ensures warnings are visible BEFORE dev-kid and micro-agent run.

    Checks per-tier:
      - ollama/ models: Ollama reachable AND specific model exists
      - anthropic/ models: ANTHROPIC_API_KEY set
      - google/ models: GOOGLE_API_KEY set
      - openai/ models: OPENAI_API_KEY set

    Args:
        config: SentinelConfig (ConfigSchema) with sentinel_ attributes.

    Returns:
        Dict with keys: micro_agent_installed, tier1_available, tier1_url,
        tier2_available, tiers_file_valid,
        any_tier_available, warnings (list[str]), tier_health (list[dict]).
    """
    from shutil import which

    warnings: list = []
    tier_health: list = []

    # Check micro-agent CLI
    micro_agent_installed = which("micro-agent") is not None
    if not micro_agent_installed:
        warnings.append(
            "micro-agent CLI not found — install with: npm install -g @gyasis/micro-agent"
        )

    # Check Ollama
    ollama_url = getattr(config, "sentinel_tier1_ollama_url", "http://localhost:11434")
    tier1_available = check_ollama_available(ollama_url)
    if not tier1_available:
        warnings.append(f"Ollama not reachable at {ollama_url}")

    # Check provider API keys
    tier2_available = bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
    google_available = bool(
        os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
    )
    openai_available = bool(os.environ.get("OPENAI_API_KEY", "").strip())

    # Provider status map
    provider_ok = {
        "ollama": tier1_available,
        "anthropic": tier2_available,
        "google": google_available,
        "openai": openai_available,
    }

    # Check tiers file and validate each tier's endpoints
    tiers_file = getattr(config, "sentinel_tiers_file", "")
    tiers_file_valid = False
    tiers_file_tier_count = 0
    usable_tier_count = 0

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
                else:
                    # Per-tier endpoint validation
                    for tier in tiers:
                        tier_name = tier.get("name", "?")
                        models = tier.get("models", {})
                        tier_ok = True
                        tier_issues = []

                        for role, model_str in models.items():
                            provider = model_str.split("/", 1)[0] if "/" in model_str else "openai"
                            model_name = model_str.split("/", 1)[1] if "/" in model_str else model_str

                            if not provider_ok.get(provider, False):
                                tier_ok = False
                                tier_issues.append(f"{role}: {provider} not available")
                            elif provider == "ollama":
                                # Check specific model exists
                                if not _check_ollama_model(ollama_url, model_name):
                                    tier_ok = False
                                    tier_issues.append(
                                        f"{role}: model '{model_name}' not found in Ollama "
                                        f"(pull with: ollama pull {model_name})"
                                    )

                        status = "ready" if tier_ok else "unavailable"
                        if tier_ok:
                            usable_tier_count += 1
                        tier_health.append({
                            "tier": tier_name,
                            "status": status,
                            "issues": tier_issues,
                        })

                        if tier_issues:
                            for issue in tier_issues:
                                warnings.append(f"{tier_name}: {issue}")

            except Exception as exc:
                warnings.append(f"Tiers file {tiers_file} is invalid JSON: {exc}")
        else:
            warnings.append(f"Tiers file not found: {tiers_file}")
    else:
        # Legacy mode warnings
        if not tier1_available:
            warnings.append(f"Tier 1: Ollama not reachable at {ollama_url}")
        if not tier2_available:
            warnings.append("Tier 2: ANTHROPIC_API_KEY not set in environment")

    # Determine overall availability
    if tiers_file and tiers_file_valid:
        any_tier_available = micro_agent_installed and usable_tier_count > 0
    else:
        any_tier_available = micro_agent_installed and (
            tier1_available or tier2_available
        )

    return {
        "micro_agent_installed": micro_agent_installed,
        "tier1_available": tier1_available,
        "tier1_url": ollama_url,
        "tier2_available": tier2_available,
        "google_available": google_available,
        "openai_available": openai_available,
        "tiers_file_valid": tiers_file_valid,
        "tiers_file_tier_count": tiers_file_tier_count,
        "usable_tier_count": usable_tier_count,
        "any_tier_available": any_tier_available,
        "tier_health": tier_health,
        "warnings": warnings,
    }


def _check_ollama_model(base_url: str, model_name: str) -> bool:
    """Check whether a specific model is available in Ollama.

    Args:
        base_url: Ollama server base URL.
        model_name: Model name to check (e.g. "qwen2.5-coder:latest").

    Returns:
        True if the model exists in Ollama's model list.
    """
    try:
        result = subprocess.run(
            ["curl", "-sf", f"{base_url}/api/tags"],
            timeout=5, capture_output=True, text=True, check=False,
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        available = {m.get("name", "") for m in data.get("models", [])}
        return model_name in available
    except Exception:
        return False


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
            "--prompt",
            objective,
            "--test",
            test_cmd,
            "--max-runs",
            str(max_iter),
        ]

        print(
            f"      🤖 Tier 1: micro-agent (ollama:{model}, max {max_iter} runs)..."
        )
        start = time.time()
        try:
            result = subprocess.run(
                cmd,
                env=env,
                timeout=300,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            print(f"      ⚠️  Tier 1 timed out after {elapsed:.0f}s")
            return TierResult(
                attempted=True, skipped=False, model=model,
                ollama_url=ollama_url, duration_sec=elapsed,
                final_status="FAIL",
                error_messages=["Tier 1 timed out after 300s"],
            )
        elapsed = time.time() - start

        parsed = _parse_micro_agent_output(result.stdout)
        final_status = "PASS" if result.returncode == 0 else "FAIL"

        # Surface micro-agent output for observability
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines()[-5:]:
                print(f"      │ stderr: {line}")
        if final_status == "FAIL" and result.stdout.strip():
            for line in result.stdout.strip().splitlines()[-5:]:
                print(f"      │ stdout: {line}")

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
            print("      ⚠️  Tier 2: ANTHROPIC_API_KEY not set — skipping (not exhausted)")
            return TierResult(
                attempted=False,
                skipped=True,
                model=model,
                error_messages=["ANTHROPIC_API_KEY not set — Tier 2 unavailable"],
                final_status="FAIL",
            )

        cmd = [
            "micro-agent",
            "--prompt",
            objective,
            "--test",
            test_cmd,
            "--max-runs",
            str(max_iter),
        ]

        print(
            f"      🌩️  Tier 2: micro-agent ({model}, max {max_iter} runs, ${max_budget} budget)..."
        )
        start = time.time()
        timeout_sec = int(max_duration * 60) + 60
        try:
            result = subprocess.run(
                cmd,
                timeout=timeout_sec,
                capture_output=True,
                text=True,
                check=False,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start
            print(f"      ⚠️  Tier 2 timed out after {elapsed:.0f}s")
            return TierResult(
                attempted=True, skipped=False, model=model,
                duration_sec=elapsed, final_status="FAIL",
                error_messages=[f"Tier 2 timed out after {timeout_sec}s"],
            )
        elapsed = time.time() - start

        parsed = _parse_micro_agent_output(result.stdout)
        final_status = "PASS" if result.returncode == 0 else "FAIL"

        # Surface micro-agent output for observability
        if result.stderr.strip():
            for line in result.stderr.strip().splitlines()[-5:]:
                print(f"      │ stderr: {line}")
        if final_status == "FAIL" and result.stdout.strip():
            for line in result.stdout.strip().splitlines()[-5:]:
                print(f"      │ stdout: {line}")

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
        """Run micro-agent through N-tier escalation ladder.

        Iterates through tiers defined in ralph-tiers.json, calling micro-agent
        for each tier with appropriate env vars. Escalates on failure until a
        tier passes or all tiers are exhausted.

        Args:
            objective: The task description / fix objective.
            test_cmd: Shell command to validate the fix.
            config: SentinelConfig with tiers_file and min_tier settings.
            project_root: Project root for resolving relative paths.

        Returns:
            TierResult with the final outcome from the winning (or last) tier.
        """
        from . import TierResult

        tiers_file = getattr(config, "sentinel_tiers_file", "")
        min_tier = (getattr(config, "sentinel_min_tier", "") or "").strip()
        max_cost = getattr(config, "sentinel_max_total_cost_usd", 5.0)
        max_duration = getattr(config, "sentinel_max_total_duration_min", 30)

        # Resolve and load tiers file
        tiers_path = Path(tiers_file)
        if not tiers_path.is_absolute():
            tiers_path = project_root / tiers_file
        if not tiers_path.exists():
            print(f"      ❌ Tiers file not found: {tiers_path}")
            return TierResult(
                attempted=False, skipped=True, tier_name="tiered",
                error_messages=[f"Tiers file not found: {tiers_path}"],
                final_status="FAIL",
            )

        try:
            tiers_data = json.loads(tiers_path.read_text(encoding="utf-8"))
            tiers = tiers_data.get("tiers", [])
        except Exception as exc:
            print(f"      ❌ Failed to parse tiers file: {exc}")
            return TierResult(
                attempted=False, skipped=True, tier_name="tiered",
                error_messages=[f"Invalid tiers file: {exc}"],
                final_status="FAIL",
            )

        if not tiers:
            print("      ❌ Tiers file has no tiers defined")
            return TierResult(
                attempted=False, skipped=True, tier_name="tiered",
                error_messages=["Tiers file has no tiers defined"],
                final_status="FAIL",
            )

        # Apply min_tier filter
        if min_tier:
            start_idx = next(
                (i for i, t in enumerate(tiers) if t.get("name") == min_tier), None
            )
            if start_idx is None:
                print(f"      ❌ min_tier '{min_tier}' not found in {tiers_path}")
                return TierResult(
                    attempted=False, skipped=True, tier_name="tiered",
                    error_messages=[f"min_tier '{min_tier}' not found in {tiers_path}"],
                    final_status="FAIL",
                )
            tiers = tiers[start_idx:]

        tier_names = [t["name"] for t in tiers]
        print(
            f"      🚀 Tiered escalation: {' → '.join(tier_names)} "
            f"(${max_cost} budget, {max_duration}min cap)..."
        )

        # Global cumulative-budget tracker (singleton across all sentinels in this
        # `dev-kid execute` run). Halts the whole run if cumulative cap exceeded —
        # prevents 65-task wave plans from burning 65 × per-task-cap = $325+ silently.
        from sentinel.budget_tracker import get_tracker
        from sentinel import handoff as _handoff
        global_tracker = get_tracker()

        # Surface global budget state once per sentinel run for visibility
        if global_tracker.task_count > 0:
            print(
                f"      💰 Cumulative spend: ${global_tracker.cumulative_cost:.2f} of "
                f"${global_tracker.budget_usd:.2f} ({global_tracker.task_count} prior sentinels)"
            )

        # Hard halt if global budget already exhausted from prior sentinels
        if global_tracker.is_exhausted():
            print(
                f"      🛑 GLOBAL BUDGET EXHAUSTED — ${global_tracker.cumulative_cost:.2f} >= "
                f"${global_tracker.budget_usd:.2f}. Halting before this sentinel runs. "
                f"To raise: `export DEVKID_SENTINEL_BUDGET_USD=<higher>` and resume, "
                f"or use the Claude Code handoff tier."
            )
            return TierResult(
                attempted=False, skipped=True, tier_name="global_budget_halt",
                error_messages=["global cumulative budget exhausted"],
                final_status="FAIL",
            )

        total_start = time.time()
        total_cost = 0.0
        last_result = None
        skipped_tiers: list[tuple[str, str]] = []  # (tier_name, reason) — for end-of-run summary
        tier_history: list[Dict[str, Any]] = []  # Phase B: passed to handoff request if reached

        for tier_idx, tier in enumerate(tiers):
            tier_name = tier.get("name", f"tier-{tier_idx}")
            models = tier.get("models", {})
            artisan_model = models.get("artisan", "")
            max_iter = tier.get("maxIterations", 5)
            tier_type = tier.get("type", "micro-agent")  # NEW: Phase B handoff support

            # Budget guard (per-sentinel cap, original behavior preserved)
            elapsed_total = time.time() - total_start
            if total_cost >= max_cost:
                print(f"      ⚠️  Per-sentinel budget exhausted (${total_cost:.2f} >= ${max_cost}) — stopping")
                break
            if elapsed_total >= max_duration * 60:
                print(f"      ⚠️  Duration cap reached ({elapsed_total:.0f}s >= {max_duration * 60}s) — stopping")
                break

            # Global budget guard — would this tier likely push us over the global cap?
            # Conservative estimate: assume worst case = remaining per-sentinel budget.
            projected_tier_cost = max_cost - total_cost
            if global_tracker.would_exceed(projected_tier_cost):
                print(
                    f"      🛑 Skipping {tier_name}: projected cost ${projected_tier_cost:.2f} "
                    f"would exceed global budget (${global_tracker.cumulative_cost:.2f} + "
                    f"${projected_tier_cost:.2f} > ${global_tracker.budget_usd:.2f})"
                )
                skipped_tiers.append((tier_name, "would exceed global cumulative budget"))
                continue

            # ---------------- Phase B: Claude Code handoff tier ----------------
            # Tiers with `"type": "handoff"` short-circuit the micro-agent invocation
            # and instead write a handoff-request file for the operator (Claude Code)
            # to handle, then poll for the complete marker.
            if tier_type == "handoff":
                # Robust task ID extraction:
                #   1. Prefer T### at start of objective (canonical speckit form)
                #   2. Fallback to T### anywhere in objective
                #   3. Last resort: hash the objective (avoids collisions like
                #      every "Fix the auth bug" task landing in SENTINEL-Fix/)
                import hashlib as _hashlib
                import re as _re
                task_id = None
                m = _re.match(r"^(T\d{1,4})\b", (objective or "").strip())
                if m:
                    task_id = m.group(1)
                else:
                    m2 = _re.search(r"\b(T\d{1,4})\b", objective or "")
                    if m2:
                        task_id = m2.group(1)
                if not task_id:
                    # Hash-based ID — deterministic per objective, no collision
                    digest = _hashlib.sha1((objective or "EMPTY").encode("utf-8")).hexdigest()[:8]
                    task_id = f"OBJ-{digest}"
                    print(
                        f"      ⚠️  No T### task ID in objective — using hash-derived id "
                        f"{task_id} (avoids collision with other handoffs)"
                    )
                print(
                    f"      🤝 [{tier_idx + 1}/{len(tiers)}] {tier_name} (Claude Code handoff) — "
                    f"writing request for task {task_id}"
                )
                request_path = _handoff.write_handoff_request(
                    task_id=task_id,
                    project_root=project_root,
                    task_description=objective,
                    test_command=test_cmd,
                    file_locks=[],
                    tier_history=tier_history,
                    cumulative_cost_so_far=global_tracker.cumulative_cost,
                    cumulative_budget=global_tracker.budget_usd,
                    reason="cheap_tiers_exhausted_or_handoff_explicitly_chosen",
                )
                print(
                    f"         📝 Request written to: {request_path}\n"
                    f"         ⏸  Wave executor will pause here. To resume, "
                    f"either let Claude Code (this session) handle it, or run:\n"
                    f"            dev-kid handoff-complete {task_id}\n"
                    f"         (Or invoke /devkid.handoff-process in Claude Code.)"
                )
                handoff_timeout = int(tier.get("handoff_timeout_sec", 1800))
                completion = _handoff.wait_for_handoff_complete(
                    task_id, project_root, timeout_sec=handoff_timeout
                )
                if completion is None:
                    print(f"         ❌ Handoff timed out after {handoff_timeout}s — escalating")
                    tier_history.append({
                        "tier": tier_name, "type": "handoff",
                        "result": "timeout", "duration_sec": handoff_timeout,
                    })
                    last_result = TierResult(
                        attempted=True, skipped=False, tier_name=tier_name,
                        tier_index=tier_idx, model="claude-code-handoff",
                        duration_sec=handoff_timeout, final_status="FAIL",
                        error_messages=[f"handoff timeout after {handoff_timeout}s"],
                    )
                    continue
                # Handoff completed — record it. Cost is $0 from dev-kid's perspective
                # (Claude Code subscription absorbs it).
                global_tracker.record(0.0, time.time() - total_start, task_id)
                tier_history.append({
                    "tier": tier_name, "type": "handoff",
                    "result": "complete", "succeeded": completion.get("succeeded"),
                })
                last_result = TierResult(
                    attempted=True, skipped=False,
                    tier_name=tier_name, tier_index=tier_idx,
                    model="claude-code-handoff",
                    iterations=1, cost_usd=0.0,
                    duration_sec=time.time() - total_start,
                    final_status="PASS" if completion.get("succeeded") else "FAIL",
                    error_messages=[completion.get("notes", "")] if not completion.get("succeeded") else [],
                )
                if completion.get("succeeded"):
                    print(f"         ✅ Handoff completed by Claude Code (free tier — $0)")
                    return last_result
                print(f"         ❌ Handoff reported failure — escalating to next tier")
                continue
            # ----------------- end Phase B handoff dispatch --------------------

            # Gated tier check — require marker file to proceed (per-tier; later gated tiers
            # with their own markers can still run independently).
            requires_marker = tier.get("requires_marker")
            if requires_marker:
                marker_path = project_root / ".claude" / "sentinel" / requires_marker
                if not marker_path.exists():
                    reason = f"gated (missing marker: {marker_path})"
                    print(f"      🔒 {tier_name}: GATED — {reason}")
                    print(f"         To allow: touch {marker_path}")
                    skipped_tiers.append((tier_name, reason))
                    continue

            # Per-role provider-key validation — report exactly which role(s) need which
            # missing provider so the user knows why a tier was skipped.
            env = {**os.environ}
            ollama_url = getattr(config, "sentinel_tier1_ollama_url", "http://localhost:11434")
            roles_needing_ollama = [r for r, m in models.items() if m and m.startswith("ollama/")]
            roles_needing_google = [r for r, m in models.items() if m and m.startswith("google/")]
            roles_needing_openai = [r for r, m in models.items() if m and m.startswith("openai/")]
            roles_needing_groq = [r for r, m in models.items() if m and m.startswith("groq/")]
            roles_needing_cerebras = [r for r, m in models.items() if m and m.startswith("cerebras/")]
            roles_needing_anthropic = [r for r, m in models.items() if m and m.startswith("anthropic/")]
            has_google_key = bool(
                os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
            )
            has_openai_key = bool(os.environ.get("OPENAI_API_KEY"))
            has_groq_key = bool(os.environ.get("GROQ_API_KEY"))
            has_cerebras_key = bool(os.environ.get("CEREBRAS_API_KEY"))
            has_anthropic_key = bool(os.environ.get("ANTHROPIC_API_KEY"))

            skip_reason = None
            if roles_needing_ollama:
                env["OLLAMA_BASE_URL"] = ollama_url
                if not check_ollama_available(ollama_url):
                    skip_reason = (
                        f"Ollama not reachable at {ollama_url} "
                        f"(needed for: {', '.join(roles_needing_ollama)})"
                    )
            if not skip_reason and roles_needing_google and not has_google_key:
                skip_reason = (
                    f"GOOGLE_API_KEY / GEMINI_API_KEY not set "
                    f"(needed for: {', '.join(roles_needing_google)})"
                )
            if not skip_reason and roles_needing_openai and not has_openai_key:
                skip_reason = (
                    f"OPENAI_API_KEY not set "
                    f"(needed for: {', '.join(roles_needing_openai)})"
                )
            if not skip_reason and roles_needing_groq and not has_groq_key:
                skip_reason = (
                    f"GROQ_API_KEY not set "
                    f"(needed for: {', '.join(roles_needing_groq)})"
                )
            if not skip_reason and roles_needing_cerebras and not has_cerebras_key:
                skip_reason = (
                    f"CEREBRAS_API_KEY not set "
                    f"(needed for: {', '.join(roles_needing_cerebras)})"
                )
            if not skip_reason and roles_needing_anthropic and not has_anthropic_key:
                skip_reason = (
                    f"ANTHROPIC_API_KEY not set "
                    f"(needed for: {', '.join(roles_needing_anthropic)})"
                )
            if skip_reason:
                print(f"      ⚠️  {tier_name}: skipping — {skip_reason}")
                skipped_tiers.append((tier_name, skip_reason))
                continue

            # Write per-tier ralph.config.yaml so micro-agent uses the right models
            tier_config_file = _write_tier_config(
                tier, ollama_url, project_root
            )

            base_cmd = [
                "micro-agent",
                "--prompt", objective,
                "--test", test_cmd,
                "--max-runs", str(max_iter),
            ]

            # micro-agent v0.1.5 unconditionally enters interactiveMode() which calls
            # @clack/prompts → uv_tty_init. When dev-kid is invoked from a non-TTY
            # context (Claude Code slash command, CI runner, captured subprocess),
            # uv_tty_init returns EINVAL and micro-agent crashes immediately with
            # 0 iterations. Wrap with `script -qfc` to provide a pseudo-TTY so
            # micro-agent's interactive prompts succeed.
            # See: https://github.com/BuilderIO/micro-agent/issues — TTY init failure
            #
            # Detection: if stdin is not a TTY, we're being called from a slash
            # command or pipeline. Use the wrapper. If stdin IS a TTY (operator
            # ran `dev-kid execute` directly in a terminal), pass-through native.
            import shlex
            if sys.stdin.isatty() or shutil.which("script") is None:
                cmd = base_cmd
            else:
                cmd_str = " ".join(shlex.quote(c) for c in base_cmd)
                cmd = ["script", "-qfc", cmd_str, "/dev/null"]

            print(f"      🔧 [{tier_idx + 1}/{len(tiers)}] {tier_name} ({artisan_model}, max {max_iter} runs)...")
            tier_start = time.time()
            try:
                result = subprocess.run(
                    cmd, env=env,
                    timeout=max(10, min(300, (max_duration * 60) - elapsed_total + 30)),
                    capture_output=True, text=True, check=False,
                    cwd=str(project_root),
                )
            except subprocess.TimeoutExpired:
                tier_elapsed = time.time() - tier_start
                print(f"      ⚠️  {tier_name} timed out after {tier_elapsed:.0f}s — escalating")
                last_result = TierResult(
                    attempted=True, skipped=False, tier_name=tier_name,
                    tier_index=tier_idx, model=artisan_model,
                    duration_sec=tier_elapsed, final_status="FAIL",
                    error_messages=[f"{tier_name} timed out"],
                )
                continue
            finally:
                # Clean up per-tier config
                if tier_config_file:
                    try:
                        Path(tier_config_file).unlink(missing_ok=True)
                    except Exception:
                        pass

            tier_elapsed = time.time() - tier_start
            parsed = _parse_micro_agent_output(result.stdout)
            tier_cost = parsed.get("cost_usd", 0.0)
            total_cost += tier_cost
            passed = result.returncode == 0

            # Record this tier's cost into the global cumulative budget tracker
            global_tracker.record(tier_cost, tier_elapsed, None)
            warn_msg = global_tracker.warn_if_approaching()
            if warn_msg:
                print(f"      {warn_msg}")
            tier_history.append({
                "tier": tier_name, "type": "micro-agent",
                "model": artisan_model,
                "iterations": parsed.get("iterations", 0),
                "cost_usd": tier_cost,
                "duration_sec": tier_elapsed,
                "passed": passed,
            })

            # Surface output for observability
            if result.stderr.strip():
                for line in result.stderr.strip().splitlines()[-3:]:
                    print(f"      │ {tier_name} stderr: {line}")
            if not passed and result.stdout.strip():
                for line in result.stdout.strip().splitlines()[-3:]:
                    print(f"      │ {tier_name} stdout: {line}")

            last_result = TierResult(
                attempted=True, skipped=False,
                tier_name=tier_name, tier_index=tier_idx,
                model=artisan_model,
                iterations=parsed.get("iterations", 0),
                cost_usd=tier_cost,
                duration_sec=parsed.get("duration_sec", tier_elapsed),
                final_status="PASS" if passed else "FAIL",
                error_messages=[result.stderr.strip()] if result.stderr.strip() else [],
            )

            if passed:
                print(
                    f"      ✅ {tier_name} PASSED in {last_result.iterations} run(s) "
                    f"({tier_elapsed:.1f}s, ${tier_cost:.2f})"
                )
                return last_result

            print(
                f"      ❌ {tier_name} FAILED after {last_result.iterations} run(s) "
                f"({tier_elapsed:.1f}s, ${tier_cost:.2f}) — escalating"
            )

        # Clean up any leftover ralph.config.yaml from tier runs
        _cleanup_tier_config = project_root / "ralph.config.yaml"
        if _cleanup_tier_config.exists():
            try:
                _cleanup_tier_config.unlink()
            except Exception:
                pass

        # End-of-run skip summary
        if skipped_tiers:
            print(f"      📋 Skipped {len(skipped_tiers)} tier(s):")
            for name, reason in skipped_tiers:
                print(f"         • {name}: {reason}")

        # All tiers exhausted
        total_elapsed = time.time() - total_start
        if last_result is None:
            print("      ❌ All tiers skipped — no providers available")
            return TierResult(
                attempted=False, skipped=True, tier_name="tiered",
                duration_sec=total_elapsed, final_status="FAIL",
                error_messages=["All tiers skipped — no providers available"],
            )

        print(
            f"      ❌ All tiers exhausted (${total_cost:.2f} spent, {total_elapsed:.0f}s elapsed)"
        )
        last_result.cost_usd = total_cost
        last_result.duration_sec = total_elapsed
        return last_result


def _extract_winning_tier(stdout: str) -> str:
    """Extract the tier name that achieved PASS from micro-agent output.

    Looks for patterns like:
      Tier 3: mixed-mid [full] — PASS
      ✅ Tier 2 (local-plus-gemini-lib) passed
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
      Artisan: openai/gpt-4.1-mini
      Model: google/gemini-2.5-pro
    """
    match = re.search(r"Artisan:\s*(\S+)", stdout, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"Model:\s*(\S+)", stdout, re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def _write_tier_config(
    tier: dict, ollama_url: str, project_root: Path
) -> str | None:
    """Write a temporary ralph.config.yaml for the given tier.

    micro-agent discovers ralph.config.yaml in the project directory and uses
    it to select models per agent role. We write a per-tier config so each
    escalation step uses the correct model.

    Args:
        tier: Tier dict from ralph-tiers.json with 'models' mapping.
        ollama_url: Ollama base URL for local tiers.
        project_root: Project root where ralph.config.yaml will be written.

    Returns:
        Path to the written config file, or None on failure.
    """
    models_raw = tier.get("models", {})
    if not models_raw:
        return None

    # Build ralph.config.yaml models section
    # ralph-tiers.json format: "artisan": "openai/gpt-4.1-mini"
    # ralph.config.yaml format: artisan: { provider: "openai", model: "gpt-4.1-mini" }
    yaml_models = {}
    for role, model_str in models_raw.items():
        if "/" in model_str:
            provider, model_name = model_str.split("/", 1)
        else:
            provider, model_name = "openai", model_str

        entry = {"provider": provider, "model": model_name}
        if provider == "ollama":
            entry["baseUrl"] = ollama_url
        yaml_models[role] = entry

    config = {"models": yaml_models}

    config_path = project_root / "ralph.config.yaml"
    try:
        # Simple YAML serialization (no PyYAML dependency needed)
        lines = ["# Auto-generated by dev-kid sentinel for tier escalation", "models:"]
        for role, entry in yaml_models.items():
            lines.append(f"  {role}:")
            for k, v in entry.items():
                lines.append(f"    {k}: '{v}'" if isinstance(v, str) else f"    {k}: {v}")

        config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return str(config_path)
    except Exception as exc:
        print(f"      ⚠️  Failed to write tier config: {exc}")
        return None


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

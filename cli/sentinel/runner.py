"""
Integration Sentinel — Runner

The main entry point for sentinel validation. SentinelRunner.run() orchestrates
the complete pipeline:
  1. Placeholder scan (pre-test-loop)
  2. Test framework detection
  3. Tiered micro-agent test loop (Tier 1 Ollama → Tier 2 cloud)
  4. Interface diff
  5. Change radius evaluation
  6. Cascade analysis
  7. Manifest writing
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli.sentinel import SentinelConfig, SentinelResult


def detect_test_command(working_dir: Path) -> str | None:
    """Auto-detect the test command for the project at working_dir.

    Detection order:
      1. pyproject.toml or setup.py  → "python -m pytest"
      2. package.json with vitest    → "npx vitest run"
      3. package.json with jest      → "npm test"
      4. Cargo.toml                  → "cargo test"
      5. None if no framework found

    Args:
        working_dir: Project root directory to inspect.

    Returns:
        Shell command string or None.
    """
    wdir = Path(working_dir)

    # Python
    if (wdir / 'pyproject.toml').exists() or (wdir / 'setup.py').exists():
        return 'python -m pytest'

    # JavaScript / TypeScript
    pkg_json = wdir / 'package.json'
    if pkg_json.exists():
        try:
            import json
            pkg = json.loads(pkg_json.read_text(encoding='utf-8'))
            deps = {
                **pkg.get('dependencies', {}),
                **pkg.get('devDependencies', {}),
            }
            if 'vitest' in deps:
                return 'npx vitest run'
            scripts = pkg.get('scripts', {})
            if 'test' in scripts:
                return 'npm test'
        except Exception:
            return 'npm test'

    # Rust
    if (wdir / 'Cargo.toml').exists():
        return 'cargo test'

    return None


class SentinelRunner:
    """Orchestrates the full sentinel validation pipeline for a single task."""

    def __init__(self, config: 'SentinelConfig', project_root: Path) -> None:
        """Initialise runner.

        Args:
            config: SentinelConfig (ConfigSchema) with sentinel_ attributes.
            project_root: Absolute project root directory.
        """
        self._config = config
        self._project_root = Path(project_root)

    def run(self, task: dict) -> 'SentinelResult':
        """Execute the full sentinel pipeline for the given task.

        Pipeline (integration points for later phases are no-ops until their
        wave is implemented):
          1. PlaceholderScanner (US2)
          2. detect_test_command
          3. TierRunner (US1)
          4. InterfaceDiff / ChangeRadius / Cascade (US3/US4 — stubbed)
          5. ManifestWriter (US3 — stubbed)
          6. Mark task [x] in tasks.md

        Args:
            task: Task dict from execution_plan.json with task_id, file_locks, etc.

        Returns:
            SentinelResult with result, should_halt_wave, and pipeline data.
        """
        from cli.sentinel import SentinelResult, TierResult

        task_id = task.get('task_id', 'UNKNOWN')
        sentinel_id = f'SENTINEL-{task_id}'
        file_locks = task.get('file_locks', [])

        # Resolve files to scan / diff
        files = [self._project_root / f for f in file_locks if f and '.' in f]

        result_obj = SentinelResult(
            task_id=task_id,
            sentinel_id=sentinel_id,
            result='PASS',
            should_halt_wave=False,
            tier1_result=TierResult(),
            tier2_result=TierResult(),
        )

        # ------------------------------------------------------------------
        # Phase 1 (US2): Placeholder scan
        # ------------------------------------------------------------------
        try:
            from cli.sentinel.placeholder_scanner import PlaceholderScanner
            scanner = PlaceholderScanner.from_config(self._config)
            violations = scanner.scan(files)
            result_obj.placeholder_violations = violations

            fail_on_detect = getattr(self._config, 'sentinel_placeholder_fail_on_detect', True)
            if violations and fail_on_detect:
                print(f"      🚫 Sentinel: {len(violations)} placeholder violation(s) detected")
                for v in violations:
                    print(f"         {v.file_path}:{v.line_number} — {v.matched_pattern}")
                result_obj.result = 'FAIL'
                result_obj.should_halt_wave = True
                result_obj.error_message = (
                    f'{len(violations)} placeholder violation(s) found in production code. '
                    'Fix before wave checkpoint.'
                )
                return result_obj
        except Exception as exc:
            print(f"      ⚠️  Placeholder scan error: {exc}")

        # ------------------------------------------------------------------
        # Phase 2 (US1): Test framework detection
        # ------------------------------------------------------------------
        test_cmd = detect_test_command(self._project_root)
        if not test_cmd:
            print(f"      ℹ️  Sentinel: No test framework found — skipping micro-agent loop")
            return result_obj

        # ------------------------------------------------------------------
        # Phase 3 (US1): Tiered micro-agent test loop
        # ------------------------------------------------------------------
        try:
            from cli.sentinel.tier_runner import TierRunner
            runner = TierRunner(self._config)

            objective = task.get('instruction', f'Verify task {task_id} output passes tests')

            # Tier 1
            t1 = runner.run_tier1(objective, test_cmd, self._config)
            result_obj.tier1_result = t1

            if t1.passed:
                result_obj.result = 'PASS'
                result_obj.tier_used = 1
                print(f"      ✅ Tier 1 passed in {t1.iterations} iteration(s)")
            else:
                # Tier 2 escalation
                print(f"      ⚠️  Tier 1 {'skipped' if t1.skipped else 'exhausted'} — escalating to Tier 2")
                t2 = runner.run_tier2(objective, test_cmd, self._config)
                result_obj.tier2_result = t2

                if t2.passed:
                    result_obj.result = 'PASS'
                    result_obj.tier_used = 2
                    print(f"      ✅ Tier 2 passed in {t2.iterations} iteration(s)")
                else:
                    result_obj.result = 'FAIL'
                    result_obj.should_halt_wave = True
                    result_obj.tier_used = 2
                    result_obj.error_message = (
                        f'Both tiers exhausted for {task_id}. '
                        'Manual intervention required.'
                    )
                    print(f"      ❌ Both tiers exhausted — wave will halt")
        except Exception as exc:
            result_obj.result = 'ERROR'
            result_obj.should_halt_wave = True
            result_obj.error_message = f'Sentinel pipeline error: {exc}'
            print(f"      ❌ Sentinel error: {exc}")

        # ------------------------------------------------------------------
        # Phase 4 (US3/US4): Interface diff, radius, cascade — stubbed
        # Populated by Wave 3/4 implementation of SentinelRunner.run() integration.
        # ------------------------------------------------------------------

        # ------------------------------------------------------------------
        # Phase 5 (US3): Manifest writing — stubbed
        # ManifestWriter integration added in T023 (Wave 3).
        # ------------------------------------------------------------------

        return result_obj

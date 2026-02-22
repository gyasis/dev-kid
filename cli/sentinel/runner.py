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
        # Phase 4 (US3/US4): Interface diff, change radius, cascade (T033)
        # ------------------------------------------------------------------
        try:
            self._run_cascade_phase(result_obj, files)
        except Exception as exc:
            print(f"      ⚠️  Cascade analysis error (non-fatal): {exc}")

        # ------------------------------------------------------------------
        # Phase 5 (US3): Manifest writing (T023)
        # Runs in try/finally so manifest is ALWAYS written (even on ERROR).
        # ------------------------------------------------------------------
        try:
            self._write_manifest(result_obj, files)
        except Exception as exc:
            print(f"      ⚠️  Manifest write error (non-fatal): {exc}")

        return result_obj

    def _run_cascade_phase(
        self,
        result_obj: 'SentinelResult',
        files: list,
    ) -> None:
        """Run InterfaceDiff, ChangeRadiusEvaluator, and CascadeAnalyzer.

        Populates result_obj.interface_changes, cascade_triggered, and
        cascade_tasks_annotated in place.

        Args:
            result_obj: SentinelResult to update with cascade information.
            files: Resolved file paths that may have been modified.
        """
        from cli.sentinel import InterfaceChangeReport
        from cli.sentinel.cascade_analyzer import CascadeAnalyzer, ChangeRadiusEvaluator
        from cli.sentinel.interface_diff import InterfaceDiff

        if not files:
            return

        # --- Interface diff for each modified file ---
        differ = InterfaceDiff()
        interface_reports: list[InterfaceChangeReport] = []
        for f in files:
            if not f.exists():
                continue
            try:
                post_content = f.read_text(encoding='utf-8', errors='replace')
                # Use git show HEAD:<file> as pre-content (fallback: empty)
                import subprocess
                rel = str(f.relative_to(self._project_root)) if f.is_absolute() else str(f)
                git_result = subprocess.run(
                    ['git', 'show', f'HEAD:{rel}'],
                    capture_output=True, text=True, check=False, timeout=10,
                    cwd=str(self._project_root),
                )
                pre_content = git_result.stdout if git_result.returncode == 0 else ''
                report = differ.compare(f, pre_content, post_content)
                interface_reports.append(report)
            except Exception:
                continue

        # --- Change radius evaluation ---
        files_changed = [
            {'path': str(f.relative_to(self._project_root) if f.is_absolute() else f),
             'lines_added': 0, 'lines_removed': 0}
            for f in files if f.exists()
        ]

        # Load execution plan for cross-wave detection (best-effort)
        execution_plan: dict = {}
        try:
            import json
            ep_path = self._project_root / 'execution_plan.json'
            if ep_path.exists():
                execution_plan = json.loads(ep_path.read_text(encoding='utf-8'))
        except Exception:
            pass

        evaluator = ChangeRadiusEvaluator(self._config)
        radius_report = evaluator.evaluate(files_changed, interface_reports, execution_plan)

        # Store interface reports in result_obj for manifest assembly
        result_obj.interface_reports = interface_reports

        if not radius_report.budget_exceeded:
            return

        # --- Cascade analysis ---
        result_obj.cascade_triggered = True

        # Find pending tasks in other waves that may be affected
        affected_ids: list[str] = []
        try:
            for wave in execution_plan.get('execution_plan', {}).get('waves', []):
                for t in wave.get('tasks', []):
                    if t.get('task_id') != result_obj.task_id:
                        affected_ids.append(t['task_id'])
        except Exception:
            pass

        cascade = CascadeAnalyzer()
        tasks_file = self._project_root / 'tasks.md'
        mode = getattr(self._config, 'sentinel_mode', 'auto')

        if mode == 'human-gated':
            from cli.sentinel.cascade_analyzer import cascade_human_gated
            from cli.wave_executor import WaveHaltError  # type: ignore[import]
            try:
                cascade_human_gated(affected_ids, result_obj.sentinel_id)
            except WaveHaltError:
                result_obj.should_halt_wave = True
                result_obj.result = 'FAIL'
                return

        annotations = cascade.annotate_tasks(
            affected_ids, result_obj.sentinel_id, interface_reports, tasks_file
        )
        result_obj.cascade_tasks_annotated = [a.task_id for a in annotations]

    def _write_manifest(
        self,
        result_obj: 'SentinelResult',
        files: list,
    ) -> None:
        """Assemble ManifestData from result_obj and write all three manifest files.

        Output directory: <project_root>/.claude/sentinel/<sentinel_id>/

        Args:
            result_obj: Completed SentinelResult.
            task: Original task dict (for instruction / parent context).
            files: Resolved file paths that were scanned / modified.
        """
        import subprocess
        from datetime import datetime, timezone

        from cli.sentinel import ManifestData, TierResult
        from cli.sentinel.manifest_writer import ManifestWriter

        sentinel_id = result_obj.sentinel_id
        output_dir = self._project_root / '.claude' / 'sentinel' / sentinel_id
        writer = ManifestWriter(output_dir)

        # Collect git diff stats for each file (lines added/removed)
        files_changed: list[dict] = []
        for f in files:
            rel = str(f.relative_to(self._project_root)) if f.is_absolute() else str(f)
            try:
                diff_stat = subprocess.run(
                    ['git', 'diff', '--numstat', 'HEAD', '--', rel],
                    capture_output=True, text=True, check=False, timeout=10,
                    cwd=str(self._project_root),
                )
                if diff_stat.returncode == 0 and diff_stat.stdout.strip():
                    parts = diff_stat.stdout.strip().split()
                    added = int(parts[0]) if parts[0].isdigit() else 0
                    removed = int(parts[1]) if parts[1].isdigit() else 0
                    files_changed.append({'path': rel, 'lines_added': added, 'lines_removed': removed})
                elif f.exists():
                    files_changed.append({'path': rel, 'lines_added': 0, 'lines_removed': 0})
            except Exception:
                if f.exists():
                    files_changed.append({'path': rel, 'lines_added': 0, 'lines_removed': 0})

        tier1 = result_obj.tier1_result or TierResult()
        tier2 = result_obj.tier2_result or TierResult()

        # Build interface_changes dict for ManifestData from stored reports
        iface_reports = getattr(result_obj, 'interface_reports', []) or []
        breaking: list[str] = []
        non_breaking: list[str] = []
        for r in iface_reports:
            breaking.extend(getattr(r, 'breaking_changes', []))
            non_breaking.extend(getattr(r, 'non_breaking_changes', []))
        interface_changes = {
            'breaking': breaking,
            'non_breaking': non_breaking,
            'is_breaking': bool(breaking),
        }

        data = ManifestData(
            task_id=result_obj.task_id,
            sentinel_id=sentinel_id,
            result=result_obj.result,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tier_used=getattr(result_obj, 'tier_used', 1),
            tier1_result=tier1,
            tier2_result=tier2,
            placeholder_violations=[
                {'file': str(v.file_path), 'line': v.line_number, 'pattern': v.matched_pattern}
                for v in (result_obj.placeholder_violations or [])
            ],
            files_changed=files_changed,
            interface_changes=interface_changes,
            fix_reason=getattr(result_obj, 'error_message', '') or '',
            cascade_triggered=bool(getattr(result_obj, 'cascade_triggered', False)),
            cascade_tasks_annotated=list(getattr(result_obj, 'cascade_tasks_annotated', []) or []),
        )

        writer.write(data)
        writer.write_diff_patch([fc['path'] for fc in files_changed])

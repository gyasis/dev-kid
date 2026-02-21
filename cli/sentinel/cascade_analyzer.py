"""
Integration Sentinel — Cascade Analyzer

Evaluates the three-axis change radius budget and auto-annotates pending tasks
in tasks.md when the budget is exceeded. Supports auto and human-gated modes.

Also contains ChangeRadiusEvaluator for three-axis budget enforcement.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli.sentinel import (
        CascadeAnnotation,
        ChangeRadiusReport,
        InterfaceChangeReport,
        SentinelConfig,
    )


class WaveHaltError(Exception):
    """Raised when human-gated cascade mode requires halting the wave."""


class ChangeRadiusEvaluator:
    """Evaluates whether sentinel's changes exceed the configured budget."""

    def __init__(self, config: 'SentinelConfig') -> None:
        self._max_files = getattr(config, 'sentinel_radius_max_files', 3)
        self._max_lines = getattr(config, 'sentinel_radius_max_lines', 150)
        self._allow_interface = getattr(config, 'sentinel_radius_allow_interface_changes', False)

    def evaluate(
        self,
        files_changed: list[dict],
        interface_reports: list['InterfaceChangeReport'],
        execution_plan: dict,
    ) -> 'ChangeRadiusReport':
        """Evaluate the three-axis change radius.

        Args:
            files_changed: List of {path, lines_added, lines_removed} dicts.
            interface_reports: InterfaceChangeReport for each modified file.
            execution_plan: The full execution_plan dict (for cross-wave detection).

        Returns:
            ChangeRadiusReport with budget_exceeded flag and violation list.
        """
        from cli.sentinel import ChangeRadiusReport

        files_count = len(files_changed)
        lines_total = sum(
            fc.get('lines_added', 0) + fc.get('lines_removed', 0)
            for fc in files_changed
        )
        interface_changes_count = sum(
            len(r.breaking_changes) + len(r.non_breaking_changes)
            for r in interface_reports
        )

        changed_paths = {fc['path'] for fc in files_changed}

        # Detect cross-wave files: files owned by tasks in *other* waves
        cross_wave_files = self._find_cross_wave_conflicts(changed_paths, execution_plan)

        violations: list[str] = []

        if files_count > self._max_files:
            violations.append('files')
        if lines_total > self._max_lines:
            violations.append('lines')
        if interface_changes_count > 0 and not self._allow_interface:
            violations.append('interface')
        if cross_wave_files:
            violations.append('cross_wave')

        budget_exceeded = bool(violations)

        return ChangeRadiusReport(
            files_changed_count=files_count,
            lines_changed_total=lines_total,
            interface_changes_count=interface_changes_count,
            budget_files=self._max_files,
            budget_lines=self._max_lines,
            allow_interface_changes=self._allow_interface,
            cross_wave_files=list(cross_wave_files),
            budget_exceeded=budget_exceeded,
            violations=violations,
        )

    def _find_cross_wave_conflicts(
        self,
        changed_paths: set[str],
        execution_plan: dict,
    ) -> set[str]:
        """Return subset of changed_paths that appear in other waves' file_locks."""
        cross_wave: set[str] = set()
        waves = execution_plan.get('execution_plan', {}).get('waves', [])
        for wave in waves:
            for task in wave.get('tasks', []):
                for lock in task.get('file_locks', []):
                    if lock in changed_paths:
                        cross_wave.add(lock)
        return cross_wave


class CascadeAnalyzer:
    """Annotates pending tasks in tasks.md with cascade warnings."""

    _WARNING_PATTERN = (
        '  > **[SENTINEL CASCADE WARNING - {timestamp}]**\n'
        '  > Sentinel for {sentinel_id} modified: {changed_files_str}'
        '{interface_str}\n'
        '  > Verify your implementation against the updated interface '
        'before marking complete.\n'
        '  > See: `.claude/sentinel/{sentinel_id}/summary.md`'
    )

    def annotate_tasks(
        self,
        affected_task_ids: list[str],
        sentinel_id: str,
        interface_changes: list['InterfaceChangeReport'],
        tasks_file: Path = Path('tasks.md'),
    ) -> list['CascadeAnnotation']:
        """Append cascade warnings to pending tasks in tasks.md.

        Only targets tasks whose line starts with '- [ ]' (incomplete).
        Writes tasks.md atomically via a temp file.

        Args:
            affected_task_ids: Task IDs to annotate.
            sentinel_id: SENTINEL-* ID that triggered the cascade.
            interface_changes: InterfaceChangeReport list for context.
            tasks_file: Path to tasks.md.

        Returns:
            List of applied CascadeAnnotation objects.
        """
        from cli.sentinel import CascadeAnnotation

        if not tasks_file.exists():
            return []

        content = tasks_file.read_text(encoding='utf-8')
        lines = content.splitlines(keepends=True)

        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

        # Build interface change summary
        changed_files = [r.file_path for r in interface_changes]
        changed_files_str = ', '.join(f'`{f}`' for f in changed_files) or 'unknown'

        iface_names = []
        for r in interface_changes:
            iface_names.extend(r.breaking_changes)
            iface_names.extend(r.non_breaking_changes)

        interface_str = ''
        if iface_names:
            interface_str = f' (interface changes: {", ".join(iface_names)})'

        warning_block = self._WARNING_PATTERN.format(
            timestamp=timestamp,
            sentinel_id=sentinel_id,
            changed_files_str=changed_files_str,
            interface_str=interface_str,
        )

        annotations: list[CascadeAnnotation] = []
        modified_lines = list(lines)

        for task_id in affected_task_ids:
            for i, line in enumerate(modified_lines):
                # Match pending tasks containing the task_id
                if line.startswith('- [ ]') and task_id in line:
                    # Append warning after the task line
                    modified_lines.insert(i + 1, warning_block + '\n')
                    annotations.append(CascadeAnnotation(
                        target_task_id=task_id,
                        sentinel_id=sentinel_id,
                        changed_files=changed_files,
                        interface_changes=iface_names,
                        warning_text=warning_block,
                        applied_at=timestamp,
                    ))
                    break  # Only annotate the first match per task_id

        if annotations:
            # Atomic write via temp file
            temp = tasks_file.with_suffix('.tmp')
            temp.write_text(''.join(modified_lines), encoding='utf-8')
            temp.replace(tasks_file)

        return annotations

    def cascade_human_gated(
        self,
        affected_tasks: list[str],
        sentinel_id: str,
        interface_changes: list['InterfaceChangeReport'] | None = None,
    ) -> None:
        """Present cascade options to the user and wait for input.

        Choices:
          a — auto-apply (annotate tasks.md and proceed)
          r — review-and-halt (annotate then raise WaveHaltError)
          h — halt immediately (raise WaveHaltError without annotating)

        Raises:
            WaveHaltError: If user selects 'r' or 'h'.
        """
        affected_str = '\n'.join(f'  - {t}' for t in affected_tasks)
        print(f"\n⚠️  CASCADE WARNING — Sentinel {sentinel_id}")
        print(f"The following pending tasks may be affected:\n{affected_str}\n")
        print("Options:")
        print("  [a] auto-apply  — annotate tasks.md and proceed")
        print("  [r] review-and-halt — annotate tasks.md then halt for review")
        print("  [h] halt — stop immediately without annotating\n")

        try:
            choice = input("Your choice [a/r/h]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = 'h'

        if choice == 'h':
            raise WaveHaltError(
                f"Wave halted by user (human-gated cascade from {sentinel_id})"
            )
        elif choice == 'r':
            if interface_changes is not None:
                self.annotate_tasks(affected_tasks, sentinel_id, interface_changes)
            raise WaveHaltError(
                f"Wave halted for manual review (cascade from {sentinel_id}). "
                "Annotations added to tasks.md."
            )
        # else 'a' — caller proceeds with auto-annotation

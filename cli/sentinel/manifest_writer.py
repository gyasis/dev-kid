"""
Integration Sentinel — Manifest Writer

Writes the three-file Change Manifest (.claude/sentinel/<SENTINEL-ID>/) after
every sentinel run, regardless of pass or fail.

Files written:
  manifest.json   — structured JSON result
  diff.patch      — git diff output (zero-byte if no changes)
  summary.md      — human-readable context for the next task agent
"""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import ManifestData, ManifestPaths, TierResult


class ManifestWriter:
    """Writes all three manifest artifacts for a sentinel run."""

    def __init__(self, output_dir: Path) -> None:
        """Initialise writer.

        Args:
            output_dir: Directory for this sentinel's artifacts
                        (e.g. .claude/sentinel/SENTINEL-T003/).
                        Created if it does not exist.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(self, data: 'ManifestData') -> 'ManifestPaths':
        """Write all three manifest files.

        Writing is best-effort: errors are caught and logged rather than
        propagated so that a FAIL result is always recorded.

        Args:
            data: Full sentinel run data.

        Returns:
            ManifestPaths with absolute paths to all three files.

        Raises:
            IOError: Only if the output directory cannot be created.
        """
        from . import ManifestPaths

        manifest_path = self._write_manifest_json(data)
        patch_path = self.write_diff_patch([fc['path'] for fc in data.files_changed])
        summary_path = self.write_summary_md(data)

        return ManifestPaths(
            manifest_json=manifest_path,
            diff_patch=patch_path,
            summary_md=summary_path,
        )

    # ------------------------------------------------------------------
    # Individual writers
    # ------------------------------------------------------------------

    def _write_manifest_json(self, data: 'ManifestData') -> Path:
        """Serialise ManifestData to manifest.json."""
        path = self.output_dir / 'manifest.json'

        def _tier_dict(t: 'TierResult') -> dict:
            return {
                'attempted': t.attempted,
                'skipped': t.skipped,
                'model': t.model,
                'ollama_url': t.ollama_url,
                'iterations': t.iterations,
                'cost_usd': t.cost_usd,
                'duration_sec': t.duration_sec,
                'final_status': t.final_status,
                'error_messages': t.error_messages,
            }

        doc = {
            'task_id': data.task_id,
            'sentinel_id': data.sentinel_id,
            'result': data.result,
            'timestamp': data.timestamp,
            'tier_used': data.tier_used,
            'tiers': {
                'tier1': _tier_dict(data.tier1_result),
                'tier2': _tier_dict(data.tier2_result),
            },
            'placeholder_violations': [
                {
                    'file_path': v.file_path,
                    'line_number': v.line_number,
                    'matched_pattern': v.matched_pattern,
                    'matched_text': v.matched_text,
                    'context_lines': v.context_lines,
                }
                for v in data.placeholder_violations
            ],
            'files_changed': data.files_changed,
            'interface_changes': data.interface_changes,
            'tests_fixed': data.tests_fixed,
            'tests_still_failing': data.tests_still_failing,
            'fix_reason': data.fix_reason,
            'cascade_triggered': data.cascade_triggered,
            'cascade_tasks_annotated': data.cascade_tasks_annotated,
            'radius': data.radius,
        }

        # Validate JSON before writing
        validated = json.loads(json.dumps(doc))
        path.write_text(json.dumps(validated, indent=2), encoding='utf-8')
        return path

    def write_diff_patch(self, files: list[str]) -> Path:
        """Capture git diff HEAD for the given files and write diff.patch.

        Returns an empty file if no changes exist or git is unavailable.

        Args:
            files: Relative file paths to diff.

        Returns:
            Absolute path to diff.patch.
        """
        path = self.output_dir / 'diff.patch'

        if not files:
            path.write_bytes(b'')
            return path

        try:
            result = subprocess.run(
                ['git', 'diff', 'HEAD', '--'] + list(files),
                capture_output=True,
                text=True,
                check=False,
                timeout=30,
            )
            patch_content = result.stdout if result.returncode == 0 else ''
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            patch_content = ''

        path.write_text(patch_content, encoding='utf-8')
        return path

    def write_summary_md(self, data: 'ManifestData') -> Path:
        """Generate human-readable Markdown summary for context injection.

        Args:
            data: Full sentinel run data.

        Returns:
            Absolute path to summary.md.
        """
        path = self.output_dir / 'summary.md'
        path.write_text(self._build_summary(data), encoding='utf-8')
        return path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_summary(self, data: 'ManifestData') -> str:
        """Render the Markdown summary string."""
        result = data.result
        sid = data.sentinel_id
        tid = data.task_id
        tier = data.tier_used

        # Parse timestamp for display
        try:
            dt = datetime.fromisoformat(data.timestamp.replace('Z', '+00:00'))
            time_str = dt.strftime('%Y-%m-%d %H:%M:%S')
        except (ValueError, AttributeError):
            time_str = data.timestamp or 'unknown'

        # Cost and duration from the tier actually used
        tier_result = data.tier1_result if tier == 1 else data.tier2_result
        cost = f"${tier_result.cost_usd:.3f}" if tier_result.cost_usd is not None else "$0.000"
        duration = f"{tier_result.duration_sec:.1f}s" if tier_result.duration_sec else "0.0s"

        lines: list[str] = [
            f"## Sentinel Report: {sid} — {result}",
            "",
            f"**Task**: {tid} | **Tier**: {tier} | **Result**: {result}",
            f"**Time**: {time_str} | **Duration**: {duration} | **Cost**: {cost}",
            "",
        ]

        # Files changed
        if data.files_changed:
            lines.append("### Changes Made")
            for fc in data.files_changed:
                added = fc.get('lines_added', 0)
                removed = fc.get('lines_removed', 0)
                lines.append(f"- `{fc['path']}` — {added} added, {removed} removed")
            lines.append("")

        # Tests fixed / still failing
        if data.tests_fixed:
            lines.append("### Tests Fixed")
            for t in data.tests_fixed:
                lines.append(f"- `{t}`")
            lines.append("")

        if data.tests_still_failing:
            lines.append("### Tests Still Failing")
            for t in data.tests_still_failing:
                lines.append(f"- `{t}`")
            lines.append("")

        # Interface changes
        iface = data.interface_changes or {}
        breaking = iface.get('breaking', [])
        non_breaking = iface.get('non_breaking', [])
        if breaking or non_breaking:
            lines.append("### Interface Changes")
            for s in breaking:
                lines.append(f"- **Breaking**: `{s}` removed or renamed")
            for s in non_breaking:
                lines.append(f"- Non-breaking: `{s}` (new)")
            lines.append("")

        # Cascade
        lines.append("### Cascade")
        if data.cascade_triggered:
            annotated = ', '.join(data.cascade_tasks_annotated) or 'none'
            lines.append(f"Cascade triggered — annotated tasks: {annotated}.")
            lines.append(f"See `.claude/sentinel/{sid}/` for details.")
        else:
            radius = data.radius or {}
            fc_count = radius.get('files_changed_count', 0)
            lc_total = radius.get('lines_changed_total', 0)
            ic_count = radius.get('interface_changes_count', 0)
            lines.append(
                f"No cascade triggered (radius within budget: "
                f"{fc_count} file(s), {lc_total} lines, "
                f"{ic_count} interface change(s))."
            )
        lines.append("")

        # Placeholder violations
        if data.placeholder_violations:
            lines.append("### Placeholder Violations")
            for v in data.placeholder_violations:
                lines.append(f"- `{v.file_path}:{v.line_number}` — `{v.matched_pattern}`")
            lines.append("")

        # Action required
        lines.append("### Action Required")
        if result == 'PASS':
            lines.append(
                f"None — tests pass. "
                f"Review the diff at `.claude/sentinel/{sid}/diff.patch` if needed."
            )
        else:
            lines.append(
                "⚠ WAVE HALTED\n"
                "This sentinel run exhausted both tiers without passing tests. "
                "Manual intervention required.\n"
                f"Review the full change history in `.claude/sentinel/{sid}/`."
            )

        return '\n'.join(lines) + '\n'

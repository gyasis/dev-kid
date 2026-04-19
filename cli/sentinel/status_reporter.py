"""
Integration Sentinel — Status Reporter

Reads all sentinel manifest files from .claude/sentinel/ and renders an
ASCII table with per-run statistics and session totals.

Usage:
  python cli/sentinel/status_reporter.py --project-root /path/to/project
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def _find_manifests(project_root: Path) -> list[Path]:
    """Find all manifest.json files in .claude/sentinel/."""
    sentinel_dir = project_root / '.claude' / 'sentinel'
    if not sentinel_dir.exists():
        return []
    return sorted(sentinel_dir.glob('*/manifest.json'), key=lambda p: p.stat().st_mtime)


def _shorten(text: str, max_len: int = 20) -> str:
    """Truncate text to max_len chars with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[:max_len - 1] + '…'


def render_table(manifests: list[Path]) -> None:
    """Render ASCII table of sentinel run history."""
    if not manifests:
        print("No sentinel runs found in .claude/sentinel/")
        return

    rows = []
    for m_path in manifests:
        try:
            data = json.loads(m_path.read_text(encoding='utf-8'))
        except Exception:
            continue

        task_id = data.get('task_id', '?')
        sentinel_id = data.get('sentinel_id', '?')
        result = data.get('result', '?')
        tier = data.get('tier_used', 0)
        timestamp = data.get('timestamp', '?')[:19].replace('T', ' ')

        tiers = data.get('tiers', {})
        t1 = tiers.get('tier1', {})
        t2 = tiers.get('tier2', {})
        iterations = t1.get('iterations', 0) + t2.get('iterations', 0)
        cost = t1.get('cost_usd', 0.0) + t2.get('cost_usd', 0.0)

        fc = data.get('files_changed', [])
        files_n = len(fc)
        lines_n = sum(f.get('lines_added', 0) + f.get('lines_removed', 0) for f in fc)

        placeholders = len(data.get('placeholder_violations', []))
        duration = t1.get('duration_sec', 0.0) + t2.get('duration_sec', 0.0)

        rows.append({
            'task': task_id,
            'sentinel': sentinel_id,
            'tier': str(tier),
            'iter': str(iterations),
            'files': str(files_n),
            'lines': str(lines_n),
            'phold': str(placeholders),
            'result': result,
            'dur': f'{duration:.0f}s',
            'cost': f'${cost:.3f}',
            'time': _shorten(timestamp, 16),
        })

    if not rows:
        print("No valid manifests found.")
        return

    # Column headers and widths
    headers = ['Task', 'Sentinel ID', 'Tier', 'Iter', 'Files', 'Lines', 'Placeh', 'Result', 'Dur', 'Cost', 'Time']
    keys =    ['task', 'sentinel',    'tier', 'iter', 'files', 'lines', 'phold',  'result', 'dur', 'cost', 'time']

    widths = {k: max(len(h), max(len(r[k]) for r in rows)) for k, h in zip(keys, headers)}

    sep = '+' + '+'.join('-' * (widths[k] + 2) for k in keys) + '+'
    header_row = '|' + '|'.join(f' {h:<{widths[k]}} ' for k, h in zip(keys, headers)) + '|'

    print(sep)
    print(header_row)
    print(sep)
    for row in rows:
        line = '|' + '|'.join(f' {row[k]:<{widths[k]}} ' for k in keys) + '|'
        print(line)
    print(sep)

    # Session totals
    total = len(rows)
    tier1_only = sum(1 for r in rows if r['tier'] == '1')
    tier2_esc = sum(1 for r in rows if r['tier'] == '2')
    failures = sum(1 for r in rows if r['result'] == 'FAIL')

    print(f"\nSession totals: {total} run(s) | "
          f"Tier-1 only: {tier1_only} | "
          f"Tier-2 escalations: {tier2_esc} | "
          f"Failures: {failures}")


def main() -> None:
    parser = argparse.ArgumentParser(description='Show sentinel run history')
    parser.add_argument('--project-root', default='.', help='Project root directory')
    args = parser.parse_args()

    project_root = Path(args.project_root).resolve()
    manifests = _find_manifests(project_root)
    render_table(manifests)


if __name__ == '__main__':
    main()

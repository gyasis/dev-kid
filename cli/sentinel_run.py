#!/usr/bin/env python3
"""
dev-kid sentinel-run <TASK-ID> — invoke SentinelRunner on a single task.

Standalone shim that bypasses execution_plan.json so users in sequential /
manual mode (e.g., after backing out of a wave plan) still get sentinel
validation, manifest writing, and the summary.md injection chain.

Usage:
    dev-kid sentinel-run T001
    dev-kid sentinel-run T001 --files src/foo.py src/bar.py
    dev-kid sentinel-run T001 --instruction "Override description"
    dev-kid sentinel-run T001 --tasks-file path/to/tasks.md
    dev-kid sentinel-run --list                  # Show IDs in tasks.md
    dev-kid sentinel-run --all                   # Every task in tasks.md
    dev-kid sentinel-run --pending               # Only [ ] tasks
    dev-kid sentinel-run --completed             # Only [x] tasks

Exit codes:
    0  PASS or SKIP (all tasks in batch mode)
    1  FAIL or ERROR (any task in batch mode)
    2  Misuse (bad arguments, task not found, config missing)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple


def _git_branch() -> str:
    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def find_tasks_md() -> Optional[Path]:
    """Locate tasks.md via the SINGLE shared resolver (cli/resolver.py).

    Previously this had its own precedence that ignored `.dk/tasks.md` and the
    `.dk/context.json` pointer — the divergence that let the sentinel validate a
    different file than orchestrate/execute used. Now it delegates so every
    component agrees on one path.
    """
    sys.path.insert(0, str(Path(__file__).parent))
    from resolver import resolve_tasks_file

    path, _reason = resolve_tasks_file()
    return path


def find_task_in_tasks_md(
    tasks_md: Path, task_id: str
) -> Tuple[Optional[str], List[str]]:
    """Find a task line by ID and return (instruction, file_locks).

    Matches:  - [ ] T001: <description>   or  - [x] T001: <description>
    Extracts file_locks from backticked paths in the description.
    """
    try:
        content = tasks_md.read_text(encoding="utf-8")
    except Exception:
        return None, []

    # Permissive pattern: colon after task ID is optional. Accepts both
    # speckit-canonical form (`- [ ] T001 description`) and the legacy
    # colon-prefixed form (`- [ ] T001: description`). Aligns with
    # orchestrator.py:102's permissive `line.startswith("- [ ]")` check
    # and resolves the inconsistency that made standalone sentinel-run
    # silently return "no tasks found" on speckit output.
    pattern = re.compile(
        rf"^\s*-\s*\[[x ]\]\s+{re.escape(task_id)}\b\s*:?\s*(.+)$",
        re.IGNORECASE,
    )
    for line in content.split("\n"):
        m = pattern.match(line.rstrip())
        if m:
            instruction = m.group(1).strip()
            file_locks = re.findall(r"`([^`]+\.[a-zA-Z]+)`", instruction)
            return instruction, list(set(file_locks))
    return None, []


def list_tasks_in_md(
    tasks_md: Path,
    include_checked: bool = True,
    include_unchecked: bool = True,
) -> List[Tuple[str, bool, str, List[str]]]:
    """Scan tasks.md and return (task_id, is_checked, instruction, file_locks) tuples.

    Skips SENTINEL-* tasks (they're managed by injection, not authored work).
    """
    try:
        content = tasks_md.read_text(encoding="utf-8")
    except Exception:
        return []

    # Permissive pattern: matches both speckit-canonical and colon-prefixed
    # forms. See find_task_in_tasks_md above for rationale.
    pattern = re.compile(
        r"^\s*-\s*\[([x ])\]\s+(T\d{1,4})\b\s*:?\s*(.+)$",
        re.IGNORECASE,
    )
    out: List[Tuple[str, bool, str, List[str]]] = []
    for line in content.split("\n"):
        m = pattern.match(line.rstrip())
        if not m:
            continue
        is_checked = m.group(1).lower() == "x"
        task_id = m.group(2).upper()
        if task_id.startswith("SENTINEL-"):
            continue
        # Normalize T1 → T001
        num = task_id[1:]
        task_id = f"T{num.zfill(3)}"
        if is_checked and not include_checked:
            continue
        if (not is_checked) and not include_unchecked:
            continue
        instruction = m.group(3).strip()
        file_locks = list(set(re.findall(r"`([^`]+\.[a-zA-Z]+)`", instruction)))
        out.append((task_id, is_checked, instruction, file_locks))
    return out


def load_config():
    """Mirror wave_executor.py's config-load order: dev-kid.yml first, then ConfigManager."""
    sys.path.insert(0, str(Path(__file__).parent))

    yml_path = Path("dev-kid.yml")
    if yml_path.exists():
        try:
            import yaml  # type: ignore
            from config_manager import ConfigSchema

            data = yaml.safe_load(yml_path.read_text(encoding="utf-8")) or {}
            return ConfigSchema.from_dict(data)
        except ImportError:
            print("⚠️  PyYAML not installed — falling back to ConfigManager")
        except Exception as exc:
            print(f"⚠️  Failed to parse dev-kid.yml: {exc}")

    try:
        from config_manager import ConfigManager

        mgr = ConfigManager()
        mgr.load()
        return mgr.schema
    except Exception as exc:
        print(f"⚠️  Config not loaded: {exc}")
        return None


def _build_task_dict(task_id: str, instruction: str, file_locks: List[str]) -> dict:
    return {
        "task_id": task_id,
        "agent_role": "Developer",
        "instruction": instruction,
        "file_locks": file_locks,
        "constitution_rules": [],
        "testability": {
            "isolated": True,
            "has_upstream_deps": False,
            "upstream_dep_ids": [],
            "wave_position": 0,
            "can_test_now": True,
            "test_hint": "manual-invocation",
        },
        "completion_handshake": "",
        "dependencies": [],
    }


def _run_single(runner, task: dict) -> str:
    """Run sentinel on one task dict, return the result string (PASS/FAIL/SKIP/ERROR)."""
    try:
        result = runner.run(task)
        return result.result
    except Exception as exc:
        print(f"   💥 Sentinel raised: {exc}")
        return "ERROR"


def _print_result(task_id: str, result) -> None:
    icons = {"PASS": "✅", "SKIP": "⏭️", "FAIL": "❌", "ERROR": "💥"}
    icon = icons.get(result.result, "⚠️")
    tier_used = getattr(result, "tier_name_used", None) or (
        f"tier {result.tier_used}" if getattr(result, "tier_used", None) else "no-test"
    )
    print(f"\n{icon} Sentinel {task_id}: {result.result} ({tier_used})")
    if getattr(result, "error_message", ""):
        print(f"   {result.error_message}")
    manifest = (
        Path.cwd() / ".claude" / "sentinel" / f"SENTINEL-{task_id}" / "manifest.json"
    )
    if manifest.exists():
        print(f"   Manifest: {manifest}")
        print(f"   Summary : {manifest.parent / 'summary.md'}")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="dev-kid sentinel-run",
        description=(
            "Invoke sentinel validation on one or more tasks without "
            "execution_plan.json. Useful when running tasks.md sequentially "
            "(e.g., /speckit.implement) or after backing out of a flawed wave plan."
        ),
    )
    parser.add_argument(
        "task_id",
        nargs="?",
        default=None,
        help="Task ID to run (e.g., T001). Omit with --list/--all/--pending/--completed.",
    )
    parser.add_argument(
        "--files",
        nargs="*",
        default=None,
        help="Override file_locks (default: extracted from task line)",
    )
    parser.add_argument(
        "--instruction",
        default=None,
        help="Override instruction (default: read from tasks.md)",
    )
    parser.add_argument(
        "--tasks-file",
        default=None,
        help="Path to tasks.md (default: auto-detect via speckit precedence)",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Run even if the task isn't found in tasks.md (uses fallback instruction)",
    )
    # Batch / discovery modes
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_only",
        help="List task IDs found in tasks.md and exit (no sentinel run).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run sentinel on every task in tasks.md (checked + unchecked).",
    )
    parser.add_argument(
        "--pending",
        action="store_true",
        help="Run sentinel only on unchecked [ ] tasks in tasks.md.",
    )
    parser.add_argument(
        "--completed",
        action="store_true",
        help="Run sentinel only on checked [x] tasks in tasks.md.",
    )
    args = parser.parse_args()

    # Validate mode selection
    batch_flags = [args.list_only, args.all, args.pending, args.completed]
    batch_count = sum(1 for f in batch_flags if f)
    if batch_count > 1:
        print("❌ Specify only one of --list, --all, --pending, --completed")
        return 2
    if batch_count == 0 and args.task_id is None:
        print("❌ Provide a TASK_ID or one of --list / --all / --pending / --completed")
        return 2
    if batch_count > 0 and args.task_id is not None:
        print("❌ TASK_ID and batch flags are mutually exclusive")
        return 2

    tasks_md = Path(args.tasks_file) if args.tasks_file else find_tasks_md()

    # ----- --list mode -----
    if args.list_only:
        if not tasks_md or not tasks_md.exists():
            print("❌ No tasks.md found")
            return 2
        rows = list_tasks_in_md(tasks_md)
        if not rows:
            print(f"(no tasks found in {tasks_md})")
            return 0
        print(f"Tasks in {tasks_md}:")
        for task_id, checked, instruction, _files in rows:
            mark = "x" if checked else " "
            trunc = instruction if len(instruction) <= 70 else instruction[:67] + "..."
            print(f"  [{mark}] {task_id}  {trunc}")
        pending = sum(1 for r in rows if not r[1])
        done = len(rows) - pending
        print(f"\n  {len(rows)} total  |  {pending} pending  |  {done} completed")
        return 0

    # ----- Batch modes (--all / --pending / --completed) -----
    if args.all or args.pending or args.completed:
        if not tasks_md or not tasks_md.exists():
            print("❌ No tasks.md found for batch mode")
            return 2
        rows = list_tasks_in_md(
            tasks_md,
            include_checked=(args.all or args.completed),
            include_unchecked=(args.all or args.pending),
        )
        if not rows:
            print("(no matching tasks)")
            return 0
        config = load_config()
        if config is None:
            print("❌ Config not loaded — cannot run sentinel")
            return 2
        try:
            from sentinel.runner import SentinelRunner  # type: ignore
        except Exception as exc:
            print(f"❌ Could not import sentinel runner: {exc}")
            return 2

        print(f"🛡️  Sentinel batch run: {len(rows)} task(s) from {tasks_md}\n")
        runner = SentinelRunner(config, Path.cwd())
        counts = {"PASS": 0, "SKIP": 0, "FAIL": 0, "ERROR": 0}
        for task_id, _checked, instruction, file_locks in rows:
            print(f"── {task_id} ─────────────────────────────────────────")
            print(f"   {instruction[:80]}{'...' if len(instruction) > 80 else ''}")
            task = _build_task_dict(task_id, instruction, file_locks)
            outcome = _run_single(runner, task)
            counts[outcome] = counts.get(outcome, 0) + 1
            icon = {"PASS": "✅", "SKIP": "⏭️", "FAIL": "❌", "ERROR": "💥"}.get(
                outcome, "⚠️"
            )
            print(f"   {icon} {outcome}")

        print("\n━━━ Sentinel batch summary ━━━")
        print(f"   ✅ PASS : {counts.get('PASS', 0)}")
        print(f"   ⏭️  SKIP : {counts.get('SKIP', 0)}")
        print(f"   ❌ FAIL : {counts.get('FAIL', 0)}")
        print(f"   💥 ERROR: {counts.get('ERROR', 0)}")
        return 0 if (counts.get("FAIL", 0) + counts.get("ERROR", 0)) == 0 else 1

    # ----- Single-task mode -----
    task_id = args.task_id.strip().upper()
    if not re.match(r"^T\d{1,4}$", task_id):
        print(f"❌ Invalid task_id '{args.task_id}' — expected format T001, T1, etc.")
        return 2
    # Normalize T1 → T001
    task_id = f"T{task_id[1:].zfill(3)}"

    instruction = args.instruction
    file_locks: Optional[List[str]] = args.files

    if (instruction is None or file_locks is None) and tasks_md and tasks_md.exists():
        found_instruction, found_files = find_task_in_tasks_md(tasks_md, task_id)
        if instruction is None:
            instruction = found_instruction
        if file_locks is None:
            file_locks = found_files
    elif tasks_md is None and not args.instruction:
        print("⚠️  No tasks.md found and no --instruction given")

    if instruction is None:
        if not args.allow_missing:
            print(
                f"❌ {task_id} not found in {tasks_md or 'any tasks.md'}. "
                "Pass --instruction to override or --allow-missing."
            )
            return 2
        instruction = f"Verify task {task_id} output passes tests"

    if file_locks is None:
        file_locks = []

    task = _build_task_dict(task_id, instruction, file_locks)

    config = load_config()
    if config is None:
        print(
            "❌ No config loaded. Sentinel needs dev-kid.yml or .devkid/config.json. "
            "Run from project root or pass --tasks-file with full context."
        )
        return 2

    if not getattr(config, "sentinel_enabled", False):
        print(
            "⚠️  sentinel.enabled is false in dev-kid.yml — running anyway "
            "(manual sentinel-run overrides the master toggle)."
        )

    try:
        from sentinel.runner import SentinelRunner  # type: ignore
    except Exception as exc:
        print(f"❌ Could not import sentinel runner: {exc}")
        return 2

    print(f"🛡️  Sentinel solo run → {task_id}")
    print(f"   tasks.md   : {tasks_md or '(none — using fallback)'}")
    print(f"   instruction: {instruction[:80]}{'...' if len(instruction) > 80 else ''}")
    print(f"   file_locks : {file_locks if file_locks else '(none)'}")
    print()

    runner = SentinelRunner(config, Path.cwd())
    try:
        result = runner.run(task)
    except Exception as exc:
        print(f"💥 Sentinel raised: {exc}")
        return 1

    _print_result(task_id, result)
    return 0 if result.result in ("PASS", "SKIP") else 1


if __name__ == "__main__":
    sys.exit(main())

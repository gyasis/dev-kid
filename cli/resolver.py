#!/usr/bin/env python3
"""Single source of truth for locating the project's tasks.md.

THE FIX (2026-05-29): dev-kid used to have four components each re-discovering
tasks.md on their own (orchestrator.py, wave_executor.py, sentinel_run.py,
task_watchdog.py all hardcoded `Path("tasks.md")`), bridged by a FRAGILE root
`tasks.md` symlink → `.dk/tasks.md`. Git/auto-checkpoint materialized the
symlink into a divergent real file, so `spec-resolve` and `execute` read
DIFFERENT files and the wave executor re-dispatched forever.

The robust model (debated Claude×Gemini): resolve the tasks file ONCE, lock its
absolute path into `.dk/context.json` (a plain pointer — NOT a symlink, so
nothing for git to rot), and have every component call `resolve_tasks_file()`.
"Solo/lite" is simply the case where only `.dk/tasks.md` exists; "SpecKit
sidekick" is when `.specify/` is present. No symlink, ever.

Stdlib-only so every component (and the bash wrapper) can call it.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

CONTEXT_FILE = Path(".dk/context.json")


def _git_branch() -> str:
    try:
        out = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def _candidates(branch: str) -> List[Tuple[Path, str]]:
    """Ordered (path, reason) candidates, lowest-priority last.

    Does NOT include the explicit-arg, env, or locked-pointer sources — those
    are handled by resolve_tasks_file() ahead of this list. Root `tasks.md` is
    the LAST resort only, so a stale materialized root file never shadows a real
    `.dk/` or `.specify/` source.
    """
    out: List[Tuple[Path, str]] = []
    # 1. lightweight / solo mode marker
    out.append((Path(".dk/tasks.md"), "lightweight mode (.dk/tasks.md)"))
    # 2. .specify/feature.json → feature dir
    fj = Path(".specify/feature.json")
    if fj.is_file():
        try:
            d = json.loads(fj.read_text(encoding="utf-8"))
            fd = d.get("feature_directory") or d.get("name") or ""
        except Exception:
            fd = ""
        if fd:
            for c in (
                Path(f".specify/{fd}/tasks.md"),
                Path(f"{fd}/tasks.md"),
                Path(f"specs/{fd}/tasks.md"),
                Path(f".specify/specs/{fd}/tasks.md"),
            ):
                out.append((c, f".specify/feature.json → {fd}"))
    # 3 & 4. branch-matched speckit layouts
    if branch:
        out.append(
            (Path(f".specify/specs/{branch}/tasks.md"), f"branch match (.specify/specs/{branch})")
        )
        out.append((Path(f"specs/{branch}/tasks.md"), f"branch match (specs/{branch})"))
    # 5. specs/*/tasks.md — most-recently-modified
    specs = Path("specs")
    if specs.is_dir():
        matches = sorted(
            (p for p in specs.rglob("tasks.md") if p.is_file()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if matches:
            out.append((matches[0], "mtime-newest fallback (specs/*/tasks.md)"))
    # 6. plain root tasks.md — LAST resort (only when nothing better exists)
    out.append((Path("tasks.md"), "root tasks.md (last resort)"))
    return out


def read_context() -> Optional[Path]:
    """The path locked by the most recent resolve (orchestrate). None if unset/stale."""
    if not CONTEXT_FILE.is_file():
        return None
    try:
        data = json.loads(CONTEXT_FILE.read_text(encoding="utf-8"))
        p = data.get("tasks_file")
        if p and Path(p).is_file():
            return Path(p)
    except Exception:
        pass
    return None


def write_context(path: Path, reason: str) -> None:
    """Lock the resolved tasks file path into .dk/context.json (a pointer, not a symlink)."""
    CONTEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tasks_file": str(Path(path).resolve()),
        "reason": reason,
        "branch": _git_branch(),
    }
    tmp = CONTEXT_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.rename(CONTEXT_FILE)


def _shadow_warning(chosen: Path, branch: str) -> Optional[str]:
    """Warn if a lower-priority candidate exists with DIFFERENT content (hidden shadowing)."""
    try:
        chosen_text = chosen.read_text(encoding="utf-8")
    except Exception:
        return None
    for cand, _reason in _candidates(branch):
        if cand == chosen or not cand.is_file():
            continue
        try:
            if cand.resolve() == chosen.resolve():
                continue
            if cand.read_text(encoding="utf-8") != chosen_text:
                return (
                    f"shadowing: using {chosen} but {cand} also exists with "
                    f"different content (pass --tasks-file to disambiguate)"
                )
        except Exception:
            continue
    return None


def resolve_tasks_file(
    explicit: Optional[str] = None,
    prefer_context: bool = True,
) -> Tuple[Optional[Path], str]:
    """Resolve which tasks.md to use. Returns (path|None, reason).

    Precedence:
      1. explicit (--tasks-file)
      2. DK_TASKS_FILE env var
      3. .dk/context.json locked pointer   (only when prefer_context)
      4. .dk/tasks.md → .specify chain → specs/{branch} → specs/* → root tasks.md

    `prefer_context=True` (components: execute/sentinel/watchdog) reuses the path
    orchestrate locked, so everyone agrees within a run. orchestrate itself calls
    with prefer_context=False to re-resolve fresh and then write_context().
    """
    if explicit:
        p = Path(explicit)
        return (p, "explicit --tasks-file") if p.is_file() else (None, f"explicit path missing: {explicit}")

    env = os.environ.get("DK_TASKS_FILE")
    if env:
        p = Path(env)
        return (p, "DK_TASKS_FILE env") if p.is_file() else (None, f"DK_TASKS_FILE missing: {env}")

    if prefer_context:
        locked = read_context()
        if locked is not None:
            return locked, "locked pointer (.dk/context.json)"

    branch = _git_branch()
    for cand, reason in _candidates(branch):
        if cand.is_file():
            return cand, reason
    return None, "unresolved (no .dk/tasks.md, no .specify, no specs/*/tasks.md)"


# --------------------------------------------------------------------------- #
# CLI entry — used by the bash wrapper so there is exactly ONE resolver.
#   python3 resolver.py resolve [--write]   → prints "<path>\t<reason>"; --write locks it
#   python3 resolver.py explain             → human introspection (spec-resolve)
# --------------------------------------------------------------------------- #
def _main(argv: List[str]) -> int:
    cmd = argv[0] if argv else "resolve"
    do_write = "--write" in argv
    branch = _git_branch()

    if cmd == "explain":
        locked = read_context()
        print("━━━ dev-kid tasks.md resolution (single resolver) ━━━")
        print(f"  git branch        : {branch or '(none)'}")
        print(f"  DK_TASKS_FILE     : {os.environ.get('DK_TASKS_FILE') or '(unset)'}")
        print(f"  .dk/context.json  : {locked or '(unset)'}")
        path, reason = resolve_tasks_file(prefer_context=True)
        print("  ─── RESOLUTION ───")
        print(f"  would use         : {path or '(UNRESOLVED)'}")
        print(f"  source            : {reason}")
        warn = _shadow_warning(path, branch) if path else None
        if warn:
            print(f"  ⚠️  {warn}")
        return 0 if path else 2

    if cmd == "lock":
        # Lock an explicit path the bash wrapper already resolved (verbatim — no
        # re-resolution, so bash and python can never pick different files).
        if len(argv) < 2:
            sys.stderr.write("resolver lock: missing <path>\n")
            return 2
        p = Path(argv[1])
        if not p.is_file():
            sys.stderr.write(f"resolver lock: not a file: {p}\n")
            return 2
        reason = argv[2] if len(argv) > 2 else "resolved by orchestrate"
        write_context(p, reason)
        return 0

    # resolve [--write]: orchestrate re-resolves fresh (ignore stale pointer) and locks it.
    path, reason = resolve_tasks_file(prefer_context=False)
    if path is None:
        sys.stderr.write(f"resolver: {reason}\n")
        return 2
    warn = _shadow_warning(path, branch)
    if warn:
        sys.stderr.write(f"⚠️  {warn}\n")
    if do_write:
        write_context(path, reason)
    sys.stdout.write(f"{path}\t{reason}\n")
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))

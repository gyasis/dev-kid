"""dev-kid init-check — validate project setup before orchestrate/execute.

Checks (each prints PASS/WARN/FAIL):
  1. dev-kid CLI on PATH
  2. dev-kid.yml present at project root
  3. ralph-tiers.json present at project root (sentinel tier config)
  4. .env present (project root) with at least ANTHROPIC_API_KEY or OPENAI_API_KEY
  5. tasks.md present (or symlinked from specs/<feature>/tasks.md)
  6. tasks.md is a symlink (warns if regular file — symlinks are recommended)
  7. execution_plan.json present (warns if missing — needed for execute)
  8. Constitution file present (.specify/memory/constitution.md or memory-bank/shared/.constitution.md)
  9. .claude/ hooks installed (warns if missing)
  10. Sentinel can parse tasks.md (the bug we fixed — confirms patches applied)

Exit code:
  0 — all PASS or WARN, ready for execute
  1 — at least one FAIL, project not ready
  2 — environment problem (dev-kid not installed, etc.)
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

CWD = Path.cwd()


class CheckResult:
    PASS = "✅ PASS"
    WARN = "⚠️  WARN"
    FAIL = "❌ FAIL"


def check_dev_kid_on_path() -> Tuple[str, str]:
    if shutil.which("dev-kid"):
        return CheckResult.PASS, f"dev-kid found at {shutil.which('dev-kid')}"
    return CheckResult.FAIL, "dev-kid CLI not on PATH — install via the dev-kid repo's ./install"


def check_dev_kid_yml() -> Tuple[str, str]:
    f = CWD / "dev-kid.yml"
    if f.exists():
        return CheckResult.PASS, f"{f.name} present"
    return CheckResult.WARN, "dev-kid.yml missing — sentinel will use defaults; run `dev-kid config init`"


def check_ralph_tiers() -> Tuple[str, str]:
    f = CWD / "ralph-tiers.json"
    if f.exists():
        return CheckResult.PASS, f"{f.name} present"
    return CheckResult.WARN, "ralph-tiers.json missing — sentinel will fall back to default tiers; copy from ~/.dev-kid/ralph-tiers.json"


def check_env_keys() -> Tuple[str, str]:
    env_path = CWD / ".env"
    if not env_path.exists() and not env_path.is_symlink():
        return CheckResult.WARN, ".env file/symlink missing in project root — providers will rely on shell env"
    try:
        content = env_path.read_text(encoding="utf-8")
    except Exception as e:
        return CheckResult.FAIL, f".env exists but cannot be read: {e}"
    keys_present = []
    for key in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"):
        if any(line.startswith(f"{key}=") and "=" in line for line in content.splitlines()):
            keys_present.append(key)
    if keys_present:
        return CheckResult.PASS, f".env has: {', '.join(keys_present)}"
    return CheckResult.WARN, ".env exists but no API keys detected; only Ollama tiers will work"


def check_tasks_md() -> Tuple[str, str]:
    f = CWD / "tasks.md"
    if not f.exists() and not f.is_symlink():
        return CheckResult.FAIL, "tasks.md missing — run `/speckit.tasks` to generate, or create manually"
    return CheckResult.PASS, "tasks.md present"


def check_tasks_md_symlink() -> Tuple[str, str]:
    f = CWD / "tasks.md"
    if not f.exists() and not f.is_symlink():
        return CheckResult.WARN, "(skipped — tasks.md missing)"
    if f.is_symlink():
        target = os.readlink(f)
        return CheckResult.PASS, f"tasks.md is a symlink → {target}"
    return CheckResult.WARN, "tasks.md is a regular file (recommended: symlink to specs/<feature>/tasks.md)"


def check_execution_plan() -> Tuple[str, str]:
    f = CWD / "execution_plan.json"
    if f.exists():
        return CheckResult.PASS, "execution_plan.json present"
    return CheckResult.WARN, "execution_plan.json missing — run `dev-kid orchestrate <phase>` before execute"


def check_constitution() -> Tuple[str, str]:
    candidates = [
        CWD / ".specify" / "memory" / "constitution.md",
        CWD / "memory-bank" / "shared" / ".constitution.md",
        CWD / "constitution.md",
    ]
    for c in candidates:
        if c.exists():
            return CheckResult.PASS, f"constitution at {c.relative_to(CWD)}"
    return CheckResult.WARN, "no constitution found — add one for compliance enforcement"


def check_claude_hooks() -> Tuple[str, str]:
    hooks_dir = CWD / ".claude" / "hooks"
    if not hooks_dir.is_dir():
        return CheckResult.WARN, ".claude/hooks/ missing — Claude Code hooks not installed"
    expected = {"stop.sh", "task-completed.sh", "pre-tool-use.sh", "session-start.sh"}
    present = {p.name for p in hooks_dir.glob("*.sh")}
    missing = expected - present
    if missing:
        return CheckResult.WARN, f".claude/hooks/ present but missing: {', '.join(sorted(missing))}"
    return CheckResult.PASS, f".claude/hooks/ has all expected hooks"


def check_sentinel_can_parse_tasks() -> Tuple[str, str]:
    """The patches we just shipped: sentinel-run --list must see tasks."""
    if not (CWD / "tasks.md").exists() and not (CWD / "tasks.md").is_symlink():
        return CheckResult.WARN, "(skipped — tasks.md missing)"
    try:
        result = subprocess.run(
            ["dev-kid", "sentinel-run", "--list"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as e:
        return CheckResult.FAIL, f"sentinel-run failed to invoke: {e}"
    out = (result.stdout or "") + (result.stderr or "")
    if "no tasks found" in out.lower():
        return CheckResult.FAIL, "sentinel-run sees 0 tasks — parser may be pre-permissive (re-apply parser patches)"
    # Count visible task lines
    task_count = sum(
        1 for line in out.splitlines()
        if line.strip().startswith("[ ]") or line.strip().startswith("[x]")
    )
    if task_count > 0:
        return CheckResult.PASS, f"sentinel-run sees {task_count} task(s) — permissive parser working"
    return CheckResult.WARN, "sentinel-run output unrecognized format — may need investigation"


def check_speckit_alignment() -> Tuple[str, str]:
    """Spec 002 audit fix #8 — verify branch / feature.json / symlink agree.

    The user's #1 friction event was a silent divergence between these three
    signals. This check surfaces the divergence so it's caught BEFORE
    orchestrate runs and (mis-)resolves to the wrong spec.
    """
    try:
        # branch
        result = subprocess.run(
            ["git", "branch", "--show-current"], capture_output=True, text=True, timeout=5
        )
        branch = result.stdout.strip()
    except Exception:
        branch = ""

    # feature.json
    feature_dir = None
    fj = CWD / ".specify" / "feature.json"
    if fj.exists():
        try:
            import json
            d = json.loads(fj.read_text())
            feature_dir = d.get("feature_directory") or d.get("name")
        except Exception as e:
            return CheckResult.WARN, f".specify/feature.json present but unparseable: {e}"

    # symlink target
    tm = CWD / "tasks.md"
    symlink_target = None
    if tm.is_symlink():
        try:
            symlink_target = os.readlink(tm)
        except Exception:
            pass

    # Cross-reference. What does each signal "point at"?
    branch_dir = f"specs/{branch}" if branch else None
    fj_dir = feature_dir if feature_dir else None
    sl_dir = None
    if symlink_target:
        # strip /tasks.md suffix
        sl_dir = symlink_target.rsplit("/tasks.md", 1)[0] if "/tasks.md" in symlink_target else symlink_target

    live_sources = {k: v for k, v in {
        "branch": branch_dir,
        "feature.json": fj_dir,
        "symlink": sl_dir,
    }.items() if v}

    if not live_sources:
        return CheckResult.WARN, "no speckit signals present (no branch, no feature.json, no symlink) — orchestrate will use mtime fallback"

    # All signals agree?
    distinct = set(live_sources.values())
    if len(distinct) == 1:
        return CheckResult.PASS, f"speckit signals agree → {next(iter(distinct))}  (sources: {list(live_sources)})"

    # Disagreement — show what each says
    summary = ", ".join(f"{k}={v}" for k, v in live_sources.items())
    return CheckResult.FAIL, f"speckit signals DISAGREE: {summary}. Run `dev-kid spec-resolve` to see which wins."


CHECKS = [
    ("dev-kid on PATH", check_dev_kid_on_path),
    ("dev-kid.yml", check_dev_kid_yml),
    ("ralph-tiers.json", check_ralph_tiers),
    (".env keys", check_env_keys),
    ("tasks.md", check_tasks_md),
    ("tasks.md symlink", check_tasks_md_symlink),
    ("speckit alignment", check_speckit_alignment),  # Spec 002 audit fix #8
    ("execution_plan.json", check_execution_plan),
    ("constitution", check_constitution),
    ("Claude Code hooks", check_claude_hooks),
    ("sentinel parser", check_sentinel_can_parse_tasks),
]


def main() -> int:
    print(f"dev-kid init-check — validating project at {CWD}\n")
    fail_count = 0
    warn_count = 0
    pass_count = 0
    for name, fn in CHECKS:
        try:
            status, detail = fn()
        except Exception as e:
            status = CheckResult.FAIL
            detail = f"check raised exception: {e}"
        print(f"  {status}  {name:24s}  {detail}")
        if status == CheckResult.FAIL:
            fail_count += 1
        elif status == CheckResult.WARN:
            warn_count += 1
        else:
            pass_count += 1
    print()
    print(f"Summary: {pass_count} pass, {warn_count} warn, {fail_count} fail")
    if fail_count > 0:
        print("Project NOT ready for execute. Address the FAIL items above.")
        return 1
    if warn_count > 0:
        print("Project ready for execute, but warnings above are worth reviewing.")
    else:
        print("Project ready for execute.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

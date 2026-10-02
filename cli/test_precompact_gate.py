"""The PreCompact hook must honour cli.auto_git_commit, like the Stop hook does.

`dev-kid checkpoint` runs `git add -A .` and commits the WHOLE tree. The Stop
hook was gated on `.devkid/config.json -> cli.auto_git_commit` on 2026-06-05;
the PreCompact hook was not, and the template shipped that gap to every project
scaffolded from it. In a repo where two sessions share a checkout, an ungated
pre-compact sweeps one session's in-progress work onto the other's branch.

These tests drive the real hook script with a stubbed `dev-kid` on PATH, so
they assert the gate OPENS as well as CLOSES — a gate that never fires is as
broken as one that always does.
"""
import os, subprocess, textwrap, json
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "templates/.claude/hooks/pre-compact.sh"


def _fixture(tmp_path, auto_git_commit, worktree=False):
    repo = tmp_path / "repo"
    (repo / ".devkid").mkdir(parents=True)
    (repo / ".claude").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", "."], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / ".devkid/config.json").write_text(json.dumps({"cli": {"auto_git_commit": auto_git_commit}}))
    (repo / "pre-compact.sh").write_text(HOOK.read_text())

    stub = tmp_path / "stub"; stub.mkdir()
    log = tmp_path / "called.log"
    (stub / "dev-kid").write_text(textwrap.dedent(f"""\
        #!/bin/sh
        echo "called $*" >> {log}
        """))
    (stub / "dev-kid").chmod(0o755)

    (repo / "f.txt").write_text("x")
    subprocess.run(["git", "add", "f.txt"], cwd=repo, check=True)

    cwd = repo
    if worktree:
        subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
        wt = tmp_path / "wt"
        subprocess.run(["git", "worktree", "add", "-q", str(wt), "-b", "b"], cwd=repo, check=True)
        (wt / ".devkid").mkdir(parents=True, exist_ok=True)
        (wt / ".claude").mkdir(parents=True, exist_ok=True)
        (wt / ".devkid/config.json").write_text((repo / ".devkid/config.json").read_text())
        (wt / "pre-compact.sh").write_text(HOOK.read_text())
        (wt / "g.txt").write_text("y")
        subprocess.run(["git", "add", "g.txt"], cwd=wt, check=True)
        cwd = wt

    env = dict(os.environ, PATH=f"{stub}:{os.environ['PATH']}",
               DEV_KID_GLOBAL_CONFIG="/nonexistent")
    env.pop("DEV_KID_AUTO_CHECKPOINT", None)
    subprocess.run(["bash", "pre-compact.sh"], cwd=cwd, env=env,
                   stdin=subprocess.DEVNULL, capture_output=True)
    return log


def test_gate_closed_when_auto_git_commit_false(tmp_path):
    assert not _fixture(tmp_path, False).exists(), \
        "pre-compact committed despite auto_git_commit=false — this is the bug"


def test_gate_opens_when_auto_git_commit_true(tmp_path):
    log = _fixture(tmp_path, True)
    assert log.exists() and "checkpoint" in log.read_text(), \
        "gate is stuck shut — opt-in users would silently lose their checkpoints"


def test_never_commits_inside_a_linked_worktree(tmp_path):
    assert not _fixture(tmp_path, True, worktree=True).exists(), \
        "auto-commit inside a linked worktree is never safe"

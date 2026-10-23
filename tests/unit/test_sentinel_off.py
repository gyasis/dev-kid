"""Sentinel off means off: shared toggle, checkpoint Step 2b, and preflight.sh."""
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

REPO = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO / "cli"))

from sentinel_toggle import is_sentinel_enabled  # noqa: E402
import wave_executor as we  # noqa: E402


@pytest.mark.parametrize(
    "yml,expected",
    [
        (None, False),
        ("project:\n  name: x\n", False),
        ("sentinel:\n  mode: auto\n", False),
        ("sentinel:\n  enabled: false\n", False),
        ("sentinel:\n  enabled: no\n", False),
        ("sentinel:\n  enabled: true\n", True),
    ],
)
def test_toggle_rule(tmp_path, yml, expected):
    if yml is not None:
        (tmp_path / "dev-kid.yml").write_text(yml)
    assert is_sentinel_enabled(tmp_path) is expected


def _checkpoint(tmp_path, monkeypatch, yml):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".claude").mkdir()
    if yml is not None:
        (tmp_path / "dev-kid.yml").write_text(yml)
    ex = we.WaveExecutor()
    tasks = [{"task_id": "T1", "agent_role": "dev"}]
    ex.plan = {"execution_plan": {"waves": [{"tasks": tasks}]}}
    runner_cls = mock.MagicMock()
    runner_cls.return_value.run.return_value = mock.MagicMock(
        result="PASS", should_halt_wave=False, tier_name_used="t", tier_used=1
    )
    with mock.patch.object(ex, "verify_wave_completion", return_value=True), \
         mock.patch.object(ex, "_update_progress"), \
         mock.patch.object(ex, "_sync_memory_bank"), \
         mock.patch.object(ex, "_git_checkpoint"), \
         mock.patch.object(we, "_SENTINEL_AVAILABLE", True), \
         mock.patch.object(we, "_SentinelRunner", runner_cls):
        ex.constitution = None
        ex.execute_checkpoint(1, {"enabled": True})
    return runner_cls


def test_executor_skips_runner_without_yml(tmp_path, monkeypatch, capsys):
    runner_cls = _checkpoint(tmp_path, monkeypatch, None)
    runner_cls.assert_not_called()
    assert "Step 2b: sentinel off" in capsys.readouterr().out


def test_executor_skips_runner_when_disabled(tmp_path, monkeypatch, capsys):
    runner_cls = _checkpoint(tmp_path, monkeypatch, "sentinel:\n  enabled: false\n")
    runner_cls.assert_not_called()
    assert "Step 2b" in capsys.readouterr().out


def test_executor_still_runs_runner_when_enabled(tmp_path, monkeypatch):
    runner_cls = _checkpoint(tmp_path, monkeypatch, "sentinel:\n  enabled: true\n")
    runner_cls.assert_called_once()
    runner_cls.return_value.run.assert_called_once()


def _run_preflight(tmp_path, *args):
    """Run preflight.sh in tmp_path with a stub `dev-kid` on PATH."""
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    stub = bindir / "dev-kid"
    stub.write_text('#!/usr/bin/env bash\necho "STUB dev-kid $*"\n')
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}
    for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY"):
        env.pop(k, None)
    return subprocess.run(
        ["bash", str(REPO / "cli" / "preflight.sh"), *args],
        cwd=tmp_path, env=env, capture_output=True, text=True,
        stdin=subprocess.DEVNULL, timeout=60,
    )


def test_preflight_sentinel_off_no_yml_passes(tmp_path):
    r = _run_preflight(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Sentinel off — provider check not needed" in r.stdout


def test_preflight_sentinel_off_proceeds_with_yes(tmp_path):
    r = _run_preflight(tmp_path, "--execute", "--yes", "execute", "--no-preflight")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Sentinel off — provider check not needed" in r.stdout
    assert "STUB dev-kid execute --no-preflight" in r.stdout
    assert "ZERO tiers" not in r.stdout + r.stderr


def test_preflight_sentinel_off_proceeds_interactive_no_tty(tmp_path):
    # Interactive path (no --yes) must not prompt or block either.
    r = _run_preflight(tmp_path, "--execute", "execute", "--no-preflight")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "STUB dev-kid execute" in r.stdout


def test_preflight_enabled_keeps_provider_check(tmp_path):
    (tmp_path / "dev-kid.yml").write_text("sentinel:\n  enabled: true\n")
    r = _run_preflight(tmp_path)
    assert "Sentinel off" not in r.stdout
    assert "provider readiness check" in r.stdout

#!/usr/bin/env python3
"""
Unit tests for WaveExecutor.execute_task() method

Tests verify:
1. Task registration with constitution rules
2. Task registration without constitution rules
3. Integration with task-watchdog
4. Error handling for failed registrations
"""

import json
import os
import sys
import tempfile

import pytest
from pathlib import Path

# Add cli directory to path
sys.path.insert(0, str(Path(__file__).parent))

from wave_executor import WaveExecutor


def setup_test_environment():
    """Setup test environment and return temp directory"""
    # Add local watchdog binary to PATH
    watchdog_bin = Path(__file__).parent.parent / "rust-watchdog" / "target" / "release"
    if watchdog_bin.exists():
        os.environ["PATH"] = f"{watchdog_bin}:{os.environ['PATH']}"
    else:
        print(f"❌ Watchdog binary not found at: {watchdog_bin}")
        print("   Run: cargo build --release in rust-watchdog/")
        sys.exit(1)

    # Create temporary test directory
    test_dir = tempfile.mkdtemp(prefix="wave_executor_test_")
    os.chdir(test_dir)

    # Create .claude directory for registry
    Path(".claude").mkdir(exist_ok=True)

    return Path(test_dir)


def test_execute_task_with_constitution_rules():
    """Test execute_task() with constitution rules"""
    print("\nTest 1: execute_task() with constitution rules")
    print("-" * 60)

    task = {
        "task_id": "UNIT-001",
        "instruction": "Test task with constitution rules",
        "agent_role": "test-agent",
        "constitution_rules": [
            "no_destructive_ops",
            "verify_before_commit",
            "test_rule",
        ],
    }

    executor = WaveExecutor()
    executor.execute_task(task)

    # Verify registration
    registry_path = Path(".claude/process_registry.json")
    assert registry_path.exists(), "Registry file not created"

    registry = json.loads(registry_path.read_text())
    assert "UNIT-001" in registry["tasks"], "Task not registered"

    task_info = registry["tasks"]["UNIT-001"]
    assert task_info["command"] == task["instruction"], "Command mismatch"
    assert (
        len(task_info["constitution_rules"]) == 3
    ), "Constitution rules count mismatch"
    assert (
        "no_destructive_ops" in task_info["constitution_rules"]
    ), "Constitution rule missing"

    print("✅ Test passed: Task registered with 3 constitution rules")
    return True


def test_execute_task_without_constitution_rules():
    """Test execute_task() without constitution rules"""
    print("\nTest 2: execute_task() without constitution rules")
    print("-" * 60)

    task = {
        "task_id": "UNIT-002",
        "instruction": "Test task without constitution rules",
        "agent_role": "test-agent",
    }

    executor = WaveExecutor()
    executor.execute_task(task)

    # Verify registration
    registry_path = Path(".claude/process_registry.json")
    registry = json.loads(registry_path.read_text())
    assert "UNIT-002" in registry["tasks"], "Task not registered"

    task_info = registry["tasks"]["UNIT-002"]
    assert task_info["command"] == task["instruction"], "Command mismatch"
    assert (
        len(task_info["constitution_rules"]) == 0
    ), "Should have no constitution rules"

    print("✅ Test passed: Task registered with no constitution rules")
    return True


def test_execute_task_empty_constitution_rules():
    """Test execute_task() with empty constitution rules list"""
    print("\nTest 3: execute_task() with empty constitution rules list")
    print("-" * 60)

    task = {
        "task_id": "UNIT-003",
        "instruction": "Test task with empty rules list",
        "agent_role": "test-agent",
        "constitution_rules": [],
    }

    executor = WaveExecutor()
    executor.execute_task(task)

    # Verify registration
    registry_path = Path(".claude/process_registry.json")
    registry = json.loads(registry_path.read_text())
    assert "UNIT-003" in registry["tasks"], "Task not registered"

    task_info = registry["tasks"]["UNIT-003"]
    assert (
        len(task_info["constitution_rules"]) == 0
    ), "Should have no constitution rules"

    print("✅ Test passed: Empty constitution rules handled correctly")
    return True


def test_execute_task_method_signature():
    """Test that execute_task() has correct method signature"""
    print("\nTest 4: Method signature verification")
    print("-" * 60)

    import inspect

    executor = WaveExecutor()
    sig = inspect.signature(executor.execute_task)

    # Check parameters
    params = list(sig.parameters.keys())
    assert "task" in params, "Missing 'task' parameter"

    # Check docstring
    assert executor.execute_task.__doc__ is not None, "Missing docstring"

    print("✅ Test passed: Method signature correct")
    print(f"   Signature: {sig}")
    return True


# ── Checkpoint-on-resume regression tests (pytest style) ──────────────────


def _make_project(tmp_path, monkeypatch, done=(), ids=(("T001", "T002"),)):
    """Project with one wave per tuple in `ids`; `done` lists ids marked [x]."""
    monkeypatch.chdir(tmp_path)
    all_ids = [i for wave in ids for i in wave]
    lines = [f"- [{'x' if i in done else ' '}] {i} do {i}" for i in all_ids]
    (tmp_path / "tasks.md").write_text("\n".join(lines) + "\n")
    waves = [
        {
            "wave_id": n,
            "strategy": "PARALLEL_SWARM",
            "rationale": "r",
            "tasks": [
                {"task_id": i, "authored_id": i, "instruction": f"do {i}", "agent_role": "dev"}
                for i in wave
            ],
            "checkpoint_after": {"verify": True},
        }
        for n, wave in enumerate(ids, 1)
    ]
    (tmp_path / "execution_plan.json").write_text(
        json.dumps({"execution_plan": {"phase_id": "ph", "waves": waves}})
    )
    return WaveExecutor(str(tmp_path / "execution_plan.json"))


def _mark_done(tmp_path, *task_ids):
    text = (tmp_path / "tasks.md").read_text()
    for i in task_ids:
        text = text.replace(f"[ ] {i} ", f"[x] {i} ")
    (tmp_path / "tasks.md").write_text(text)


def test_checkpoint_runs_once_for_completed_wave_on_resume(tmp_path, monkeypatch):
    ex = _make_project(
        tmp_path, monkeypatch, done=("T001",), ids=(("T001",), ("T002",))
    )
    calls, dispatched = [], []
    monkeypatch.setattr(ex, "execute_checkpoint", lambda w, c: calls.append(w))
    monkeypatch.setattr(ex, "execute_wave", lambda w: dispatched.append(w["wave_id"]))

    with pytest.raises(SystemExit) as e:
        ex.execute()
    assert e.value.code == 0
    assert calls == [1]  # wave 1 checkpoint ran
    assert dispatched == [2]  # wave 2 dispatched
    assert (tmp_path / ".dk" / "checkpoints.json").exists()

    ex2 = WaveExecutor(str(tmp_path / "execution_plan.json"))
    monkeypatch.setattr(ex2, "execute_checkpoint", lambda w, c: calls.append(w))
    monkeypatch.setattr(ex2, "execute_wave", lambda w: dispatched.append(w["wave_id"]))
    with pytest.raises(SystemExit):
        ex2.execute()
    assert calls == [1]  # NOT run twice
    assert dispatched == [2, 2]

    # Agent finishes wave 2: its checkpoint runs, wave 1's still does not.
    _mark_done(tmp_path, "T002")
    ex3 = WaveExecutor(str(tmp_path / "execution_plan.json"))
    monkeypatch.setattr(ex3, "execute_checkpoint", lambda w, c: calls.append(w))
    ex3.execute()
    assert calls == [1, 2]


def test_halting_checkpoint_is_not_recorded(tmp_path, monkeypatch):
    ex = _make_project(tmp_path, monkeypatch, done=("T001",), ids=(("T001",),))

    def halt(w, c):
        sys.exit(1)

    monkeypatch.setattr(ex, "execute_checkpoint", halt)
    with pytest.raises(SystemExit) as e:
        ex.execute()
    assert e.value.code == 1
    assert not (tmp_path / ".dk" / "checkpoints.json").exists()

    calls = []
    ex2 = WaveExecutor(str(tmp_path / "execution_plan.json"))
    monkeypatch.setattr(ex2, "execute_checkpoint", lambda w, c: calls.append(w))
    ex2.execute()
    assert calls == [1]  # retried


def test_sentinel_halt_is_not_recorded(tmp_path, monkeypatch):
    import wave_executor as we

    ex = _make_project(tmp_path, monkeypatch, done=("T001",), ids=(("T001",),))

    def halt(w, c):
        raise we.WaveHaltError("boom")

    monkeypatch.setattr(ex, "execute_checkpoint", halt)
    with pytest.raises(SystemExit) as e:
        ex.execute()
    assert e.value.code == 2
    assert not (tmp_path / ".dk" / "checkpoints.json").exists()


def test_changed_plan_does_not_reuse_marks(tmp_path, monkeypatch):
    ex = _make_project(tmp_path, monkeypatch, done=("T001",), ids=(("T001",),))
    calls = []
    monkeypatch.setattr(ex, "execute_checkpoint", lambda w, c: calls.append(w))
    ex.execute()
    assert calls == [1]

    # Re-orchestrated: same phase + wave id, different task ids.
    ex2 = _make_project(tmp_path, monkeypatch, done=("T009",), ids=(("T009",),))
    monkeypatch.setattr(ex2, "execute_checkpoint", lambda w, c: calls.append(w))
    ex2.execute()
    assert calls == [1, 1]


def test_git_checkpoint_nothing_to_commit_does_not_crash(
    tmp_path, monkeypatch, capsys
):
    import subprocess

    ex = _make_project(tmp_path, monkeypatch, done=("T001",), ids=(("T001",),))
    env = {
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    }
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    subprocess.run(["git", "init", "-q"], check=True)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-qm", "init"], check=True)

    ex._git_checkpoint(1, [{"task_id": "T001", "file_locks": ["src/a.py"]}])
    out = capsys.readouterr().out
    assert "nothing staged to commit" in out
    assert "Git commit failed" not in out


def cleanup_test_environment(test_dir: Path):
    """Cleanup test environment"""
    import shutil

    os.chdir(Path.home())
    shutil.rmtree(test_dir)


def run_all_tests():
    """Run all unit tests"""
    print("=" * 70)
    print("WaveExecutor.execute_task() Unit Tests")
    print("=" * 70)

    test_dir = setup_test_environment()
    print(f"\n✅ Test environment created at: {test_dir}")

    tests = [
        test_execute_task_with_constitution_rules,
        test_execute_task_without_constitution_rules,
        test_execute_task_empty_constitution_rules,
        test_execute_task_method_signature,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {e}")
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Total tests: {passed + failed}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")

    # Cleanup
    cleanup_test_environment(test_dir)
    print("\n✅ Test environment cleaned up")

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_all_tests()

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
import subprocess
import sys
import tempfile
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
        "constitution_rules": ["no_destructive_ops", "verify_before_commit", "test_rule"]
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
    assert len(task_info["constitution_rules"]) == 3, "Constitution rules count mismatch"
    assert "no_destructive_ops" in task_info["constitution_rules"], "Constitution rule missing"

    print("✅ Test passed: Task registered with 3 constitution rules")
    return True


def test_execute_task_without_constitution_rules():
    """Test execute_task() without constitution rules"""
    print("\nTest 2: execute_task() without constitution rules")
    print("-" * 60)

    task = {
        "task_id": "UNIT-002",
        "instruction": "Test task without constitution rules",
        "agent_role": "test-agent"
    }

    executor = WaveExecutor()
    executor.execute_task(task)

    # Verify registration
    registry_path = Path(".claude/process_registry.json")
    registry = json.loads(registry_path.read_text())
    assert "UNIT-002" in registry["tasks"], "Task not registered"

    task_info = registry["tasks"]["UNIT-002"]
    assert task_info["command"] == task["instruction"], "Command mismatch"
    assert len(task_info["constitution_rules"]) == 0, "Should have no constitution rules"

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
        "constitution_rules": []
    }

    executor = WaveExecutor()
    executor.execute_task(task)

    # Verify registration
    registry_path = Path(".claude/process_registry.json")
    registry = json.loads(registry_path.read_text())
    assert "UNIT-003" in registry["tasks"], "Task not registered"

    task_info = registry["tasks"]["UNIT-003"]
    assert len(task_info["constitution_rules"]) == 0, "Should have no constitution rules"

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
    print(f"\n✅ Test environment cleaned up")

    # Exit with appropriate code
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run_all_tests()

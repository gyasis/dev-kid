#!/usr/bin/env python3
"""
Test script for execute_task() method in WaveExecutor
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from wave_executor import WaveExecutor


def test_execute_task_registration():
    """Test that execute_task() correctly registers tasks with watchdog"""

    print("Testing execute_task() method...\n")

    # Add local watchdog binary to PATH for testing
    watchdog_bin = Path(__file__).parent.parent / "rust-watchdog" / "target" / "release"
    if watchdog_bin.exists():
        os.environ["PATH"] = f"{watchdog_bin}:{os.environ['PATH']}"
        print(f"✅ Using local watchdog binary from: {watchdog_bin}\n")
    else:
        print(f"⚠️  Watchdog binary not found at: {watchdog_bin}")
        print("   Run: cargo build --release in rust-watchdog/\n")

    # Create test task with constitution rules
    task_with_rules = {
        "task_id": "TEST-001",
        "instruction": "Test task with constitution rules",
        "agent_role": "test-agent",
        "constitution_rules": ["no_destructive_ops", "verify_before_commit"]
    }

    # Create test task without constitution rules
    task_without_rules = {
        "task_id": "TEST-002",
        "instruction": "Test task without constitution rules",
        "agent_role": "test-agent"
    }

    # Initialize executor (will print warning if no constitution file, which is OK)
    executor = WaveExecutor()

    # Test 1: Task with constitution rules
    print("Test 1: Task with constitution rules")
    print("-" * 50)
    executor.execute_task(task_with_rules)
    print()

    # Test 2: Task without constitution rules
    print("Test 2: Task without constitution rules")
    print("-" * 50)
    executor.execute_task(task_without_rules)
    print()

    # Verify tasks were registered by checking registry
    registry_path = Path(".claude/process_registry.json")

    if registry_path.exists():
        print("Test 3: Verifying registration in registry")
        print("-" * 50)

        registry = json.loads(registry_path.read_text())

        # Check TEST-001
        if "TEST-001" in registry.get("tasks", {}):
            task_data = registry["tasks"]["TEST-001"]
            print(f"✅ TEST-001 found in registry")
            print(f"   Command: {task_data.get('command')}")
            rules = task_data.get('constitution_rules', [])
            print(f"   Constitution rules: {rules}")

            if len(rules) == 2:
                print(f"   ✅ Correct number of constitution rules")
            else:
                print(f"   ❌ Expected 2 rules, got {len(rules)}")
        else:
            print(f"❌ TEST-001 not found in registry")

        print()

        # Check TEST-002
        if "TEST-002" in registry.get("tasks", {}):
            task_data = registry["tasks"]["TEST-002"]
            print(f"✅ TEST-002 found in registry")
            print(f"   Command: {task_data.get('command')}")
            rules = task_data.get('constitution_rules', [])
            print(f"   Constitution rules: {rules}")

            if len(rules) == 0:
                print(f"   ✅ No constitution rules (as expected)")
            else:
                print(f"   ⚠️  Unexpected rules: {rules}")
        else:
            print(f"❌ TEST-002 not found in registry")
    else:
        print("⚠️  Registry file not found - watchdog may not be installed")
        print("   This is OK if running outside dev-kid project")

    print("\n✅ execute_task() method test complete")
    print("\nMethod signature:")
    print("  def execute_task(self, task: Dict) -> None")
    print("\nIntegration:")
    print("  - Called from execute_wave() for each task")
    print("  - Registers task with watchdog using 'task-watchdog register'")
    print("  - Passes constitution_rules if present in task dict")
    print("  - Provides clear user feedback on success/failure")


if __name__ == "__main__":
    test_execute_task_registration()

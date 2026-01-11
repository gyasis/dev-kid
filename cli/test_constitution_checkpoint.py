#!/usr/bin/env python3
"""
Test script for constitution validation in checkpoints

Tests SPECKIT-009: execute_checkpoint() validates output against constitution
"""

import json
import subprocess
import sys
from pathlib import Path
import tempfile
import shutil


def setup_test_environment(tmp_dir: Path):
    """Setup test git repo with constitution and tasks"""
    # Initialize git repo
    subprocess.run(['git', 'init'], cwd=tmp_dir, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=tmp_dir)
    subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=tmp_dir)

    # Create initial commit
    readme = tmp_dir / "README.md"
    readme.write_text("# Test Project")
    subprocess.run(['git', 'add', '.'], cwd=tmp_dir)
    subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=tmp_dir)

    # Create memory-bank structure
    memory_bank = tmp_dir / "memory-bank" / "shared"
    memory_bank.mkdir(parents=True, exist_ok=True)

    # Create constitution
    constitution = memory_bank / ".constitution.md"
    constitution.write_text("""# Project Constitution

## Code Standards
- All functions must have type hints
- All public functions must have docstrings
- Use descriptive variable names

## Testing Standards
- Test coverage must exceed 80%
- All public functions must have tests

## Security Standards
- No hardcoded secrets or passwords
- Use environment variables for credentials
""")

    # Create private memory-bank directory for progress.md
    import getpass
    username = getpass.getuser()
    private_dir = tmp_dir / "memory-bank" / "private" / username
    private_dir.mkdir(parents=True, exist_ok=True)

    # Create tasks.md
    tasks_file = tmp_dir / "tasks.md"
    tasks_file.write_text("""# Tasks

- [x] TASK-001: Create calculator module with tests
""")

    # Create execution plan
    execution_plan = {
        "execution_plan": {
            "phase_id": "test-phase",
            "waves": [
                {
                    "wave_id": 1,
                    "strategy": "PARALLEL_SWARM",
                    "rationale": "Test wave",
                    "tasks": [
                        {
                            "task_id": "TASK-001",
                            "instruction": "Create calculator module with tests",
                            "agent_role": "test-agent"
                        }
                    ],
                    "checkpoint_after": {
                        "enabled": True,
                        "validation_required": True
                    }
                }
            ]
        }
    }

    plan_file = tmp_dir / "execution_plan.json"
    plan_file.write_text(json.dumps(execution_plan, indent=2))


def test_clean_code(tmp_dir: Path):
    """Test checkpoint succeeds with constitution-compliant code"""
    print("\n🧪 Test 1: Clean code (should PASS)")

    # Create compliant Python file
    test_file = tmp_dir / "calculator.py"
    test_file.write_text("""#!/usr/bin/env python3
\"\"\"Calculator module with clean code\"\"\"

def add(a: int, b: int) -> int:
    \"\"\"Add two numbers\"\"\"
    return a + b
""")

    # Create corresponding test file to satisfy TEST_COVERAGE_REQUIRED
    test_test_file = tmp_dir / "test_calculator.py"
    test_test_file.write_text("""#!/usr/bin/env python3
\"\"\"Tests for calculator module\"\"\"

def test_add() -> None:
    \"\"\"Test add function\"\"\"
    from calculator import add
    assert add(1, 2) == 3
""")

    subprocess.run(['git', 'add', '.'], cwd=tmp_dir)

    # Run wave executor in the temp directory
    import os
    original_dir = os.getcwd()
    os.chdir(tmp_dir)

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from wave_executor import WaveExecutor

        executor = WaveExecutor("execution_plan.json")
        executor.load_plan()

        try:
            executor.execute_checkpoint(1, executor.plan['execution_plan']['waves'][0]['checkpoint_after'])
            print("   ✅ Checkpoint passed (as expected)")
            return True
        except SystemExit as e:
            if e.code == 1:
                print("   ❌ Checkpoint failed (unexpected)")
                return False
            raise
    finally:
        os.chdir(original_dir)


def test_missing_type_hints(tmp_dir: Path):
    """Test checkpoint fails with missing type hints"""
    print("\n🧪 Test 2: Missing type hints (should FAIL)")

    # Reset git state
    subprocess.run(['git', 'reset', '--hard', 'HEAD'], cwd=tmp_dir, check=True)

    # Create non-compliant Python file (no type hints)
    test_file = tmp_dir / "calculator.py"
    test_file.write_text("""#!/usr/bin/env python3
\"\"\"Calculator module\"\"\"

def add(a, b):
    \"\"\"Add two numbers\"\"\"
    return a + b
""")

    # Create test file to avoid TEST_COVERAGE_REQUIRED violation
    test_test_file = tmp_dir / "test_calculator.py"
    test_test_file.write_text("""#!/usr/bin/env python3
\"\"\"Tests for calculator\"\"\"

def test_add():
    \"\"\"Test add function\"\"\"
    pass
""")

    subprocess.run(['git', 'add', '.'], cwd=tmp_dir)

    # Run wave executor in the temp directory
    import os
    original_dir = os.getcwd()
    os.chdir(tmp_dir)

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from wave_executor import WaveExecutor

        executor = WaveExecutor("execution_plan.json")
        executor.load_plan()

        try:
            executor.execute_checkpoint(1, executor.plan['execution_plan']['waves'][0]['checkpoint_after'])
            print("   ❌ Checkpoint passed (unexpected - should have failed)")
            return False
        except SystemExit as e:
            if e.code == 1:
                print("   ✅ Checkpoint blocked (as expected)")
                return True
            raise
    finally:
        os.chdir(original_dir)


def test_missing_docstring(tmp_dir: Path):
    """Test checkpoint fails with missing docstring"""
    print("\n🧪 Test 3: Missing docstring (should FAIL)")

    # Reset git state
    subprocess.run(['git', 'reset', '--hard', 'HEAD'], cwd=tmp_dir, check=True)

    # Create non-compliant Python file (no docstring)
    test_file = tmp_dir / "calculator.py"
    test_file.write_text("""#!/usr/bin/env python3

def add(a: int, b: int) -> int:
    return a + b
""")

    # Create test file to avoid TEST_COVERAGE_REQUIRED violation
    test_test_file = tmp_dir / "test_calculator.py"
    test_test_file.write_text("""#!/usr/bin/env python3
\"\"\"Tests for calculator\"\"\"

def test_add():
    \"\"\"Test add function\"\"\"
    pass
""")

    subprocess.run(['git', 'add', '.'], cwd=tmp_dir)

    # Run wave executor in the temp directory
    import os
    original_dir = os.getcwd()
    os.chdir(tmp_dir)

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from wave_executor import WaveExecutor

        executor = WaveExecutor("execution_plan.json")
        executor.load_plan()

        try:
            executor.execute_checkpoint(1, executor.plan['execution_plan']['waves'][0]['checkpoint_after'])
            print("   ❌ Checkpoint passed (unexpected - should have failed)")
            return False
        except SystemExit as e:
            if e.code == 1:
                print("   ✅ Checkpoint blocked (as expected)")
                return True
            raise
    finally:
        os.chdir(original_dir)


def test_no_constitution(tmp_dir: Path):
    """Test checkpoint works gracefully when constitution is missing"""
    print("\n🧪 Test 4: No constitution (should PASS with warning)")

    # Reset git state
    subprocess.run(['git', 'reset', '--hard', 'HEAD'], cwd=tmp_dir, check=True)

    # Remove constitution AFTER reset
    constitution = tmp_dir / "memory-bank" / "shared" / ".constitution.md"
    constitution.unlink()

    # Create any Python file (doesn't matter if compliant)
    test_file = tmp_dir / "utils.py"
    test_file.write_text("def foo(): pass")
    subprocess.run(['git', 'add', '.'], cwd=tmp_dir)

    # Run wave executor in the temp directory
    import os
    original_dir = os.getcwd()
    os.chdir(tmp_dir)

    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from wave_executor import WaveExecutor

        executor = WaveExecutor("execution_plan.json")
        executor.load_plan()

        try:
            executor.execute_checkpoint(1, executor.plan['execution_plan']['waves'][0]['checkpoint_after'])
            print("   ✅ Checkpoint passed with warning (as expected)")
            return True
        except SystemExit as e:
            if e.code == 1:
                print("   ❌ Checkpoint failed (unexpected - should pass with warning)")
                return False
            raise
    finally:
        os.chdir(original_dir)


def main():
    """Run all tests"""
    print("=" * 60)
    print("SPECKIT-009: Constitution Validation in Checkpoints")
    print("=" * 60)

    # Create temporary directory
    tmp_dir = Path(tempfile.mkdtemp(prefix="test_constitution_"))
    print(f"\n📁 Test directory: {tmp_dir}")

    try:
        # Setup test environment
        print("\n📦 Setting up test environment...")
        setup_test_environment(tmp_dir)
        print("   ✅ Environment ready")

        # Run tests
        results = []
        results.append(("Clean code", test_clean_code(tmp_dir)))

        # Re-setup for next test
        setup_test_environment(tmp_dir)
        results.append(("Missing type hints", test_missing_type_hints(tmp_dir)))

        # Re-setup for next test
        setup_test_environment(tmp_dir)
        results.append(("Missing docstring", test_missing_docstring(tmp_dir)))

        # Re-setup for next test
        setup_test_environment(tmp_dir)
        results.append(("No constitution", test_no_constitution(tmp_dir)))

        # Summary
        print("\n" + "=" * 60)
        print("RESULTS")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status}: {test_name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n✅ ALL TESTS PASSED")
            return 0
        else:
            print("\n❌ SOME TESTS FAILED")
            return 1

    finally:
        # Cleanup
        print(f"\n🧹 Cleaning up {tmp_dir}...")
        shutil.rmtree(tmp_dir)


if __name__ == '__main__':
    sys.exit(main())

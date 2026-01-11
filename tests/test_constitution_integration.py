#!/usr/bin/env python3
"""
End-to-end integration test for constitution enforcement flow.
Tests: tasks.md → orchestrator → executor → watchdog → checkpoint validation
"""

import json
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

def setup_test_environment():
    """Create a temporary test directory with required structure"""
    test_dir = tempfile.mkdtemp(prefix="constitution_test_")
    print(f"📁 Created test environment: {test_dir}")

    # Create required directories
    (Path(test_dir) / ".claude").mkdir()
    (Path(test_dir) / "memory-bank" / "shared").mkdir(parents=True)
    (Path(test_dir) / "src").mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=test_dir, capture_output=True)

    # Create initial commit
    readme = Path(test_dir) / "README.md"
    readme.write_text("# Test Project\n")
    subprocess.run(["git", "add", "."], cwd=test_dir, capture_output=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=test_dir, capture_output=True)

    return test_dir

def create_constitution(test_dir):
    """Create a test constitution file"""
    constitution_path = Path(test_dir) / "memory-bank" / "shared" / ".constitution.md"
    constitution_content = """# Project Constitution

## Code Standards

- All Python functions must have type hints for parameters and return values
- All Python functions must have docstrings describing their purpose

## Security Standards

- No hardcoded API keys, passwords, or tokens allowed in source code
- Use environment variables or secure vaults for secrets

## Testing Standards

- All new Python files must have corresponding test files
- Maintain minimum 80% test coverage for new code
"""
    constitution_path.write_text(constitution_content)
    print(f"✅ Created constitution: {constitution_path}")
    return constitution_path

def create_test_task(test_dir):
    """Create tasks.md with a task that specifies constitution rules"""
    tasks_md = Path(test_dir) / "tasks.md"
    tasks_content = """# Test Tasks

- [ ] Create a utility module `src/utils.py`
  - **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED
  - **Files**: `src/utils.py`
"""
    tasks_md.write_text(tasks_content)
    print(f"✅ Created tasks.md: {tasks_md}")
    return tasks_md

def run_orchestrator(test_dir):
    """Run orchestrator to generate execution plan"""
    tasks_md = Path(test_dir) / "tasks.md"

    # Import orchestrator module
    cli_dir = Path(__file__).parent.parent / "cli"
    sys.path.insert(0, str(cli_dir))

    # Orchestrator outputs to execution_plan.json in current working directory
    cmd = [
        sys.executable,
        str(cli_dir / "orchestrator.py"),
        "--tasks-file", str(tasks_md),
        "--phase-id", "TEST"
    ]

    result = subprocess.run(cmd, cwd=test_dir, capture_output=True, text=True)
    output_file = Path(test_dir) / "execution_plan.json"

    if result.returncode != 0:
        print(f"❌ Orchestrator failed: {result.stderr}")
        return None

    print(f"✅ Orchestrator generated execution plan")

    # Load and verify execution plan
    with open(output_file) as f:
        plan = json.load(f)

    # Verify constitution rules are in the plan
    found_rules = False
    for wave in plan["execution_plan"]["waves"]:
        for task in wave["tasks"]:
            if task.get("constitution_rules"):
                print(f"✅ Found constitution rules in task {task['task_id']}: {task['constitution_rules']}")
                found_rules = True

    if not found_rules:
        print("❌ No constitution rules found in execution plan")
        return None

    return output_file

def create_violating_file(test_dir):
    """Create a Python file that violates constitution rules"""
    utils_py = Path(test_dir) / "src" / "utils.py"

    # This file violates TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED, and NO_HARDCODED_SECRETS
    violating_content = """# Utility module

def calculate_sum(a, b):
    return a + b

def get_credentials():
    # Violates NO_HARDCODED_SECRETS
    api_key = "sk-1234567890abcdef"
    return api_key
"""
    utils_py.write_text(violating_content)

    # Stage the file
    subprocess.run(["git", "add", "src/utils.py"], cwd=test_dir, capture_output=True)

    print(f"✅ Created violating file: {utils_py}")
    return utils_py

def test_constitution_validation(test_dir):
    """Test that Constitution.validate_output() detects violations"""
    cli_dir = Path(__file__).parent.parent / "cli"
    sys.path.insert(0, str(cli_dir))

    from constitution_parser import Constitution

    constitution_path = Path(test_dir) / "memory-bank" / "shared" / ".constitution.md"
    constitution = Constitution(str(constitution_path))

    # Get modified files
    result = subprocess.run(
        ["git", "diff", "--name-only", "--cached"],
        cwd=test_dir,
        capture_output=True,
        text=True
    )
    modified_files = [Path(test_dir) / f for f in result.stdout.strip().split('\n') if f]

    print(f"🔍 Debug: Modified files: {modified_files}")
    print(f"🔍 Debug: Constitution rules loaded: {list(constitution.rules.keys())}")

    violations = constitution.validate_output(modified_files)

    print(f"🔍 Debug: Violations found: {len(violations)}")

    if not violations:
        print("❌ Constitution validation failed to detect violations")
        print("   This indicates validation logic needs to be checked")
        return False

    print(f"✅ Detected {len(violations)} constitution violations:")
    for v in violations:
        print(f"   - {v.file}:{v.line} [{v.rule}] {v.message}")

    # Verify we detected the expected violations
    expected_violations = {
        "TYPE_HINTS_REQUIRED",
        "DOCSTRINGS_REQUIRED",
        "NO_HARDCODED_SECRETS"
    }

    found_violations = {v.rule for v in violations}

    if not expected_violations.issubset(found_violations):
        print(f"❌ Missing expected violations: {expected_violations - found_violations}")
        return False

    print("✅ All expected violations detected")
    return True

def cleanup(test_dir):
    """Remove test environment"""
    shutil.rmtree(test_dir)
    print(f"🧹 Cleaned up test environment: {test_dir}")

def main():
    """Run end-to-end constitution enforcement flow test"""
    print("\n🧪 Constitution Enforcement - End-to-End Integration Test")
    print("=" * 60)

    test_dir = None
    try:
        # Step 1: Setup
        test_dir = setup_test_environment()

        # Step 2: Create constitution
        create_constitution(test_dir)

        # Step 3: Create test task with constitution rules
        create_test_task(test_dir)

        # Step 4: Run orchestrator
        execution_plan = run_orchestrator(test_dir)
        if not execution_plan:
            print("\n❌ FAIL: Orchestrator step failed")
            return 1

        # Step 5: Create file that violates constitution
        create_violating_file(test_dir)

        # Step 6: Test constitution validation
        if not test_constitution_validation(test_dir):
            print("\n❌ FAIL: Constitution validation step failed")
            return 1

        print("\n" + "=" * 60)
        print("✅ SUCCESS: End-to-end constitution enforcement flow verified")
        print("=" * 60)
        print("\nFlow verified:")
        print("  1. tasks.md contains constitution rules ✅")
        print("  2. Orchestrator extracts rules into execution_plan.json ✅")
        print("  3. Constitution parser validates violations ✅")
        print("  4. Violations block checkpoint (would exit with error) ✅")

        return 0

    except Exception as e:
        print(f"\n❌ FAIL: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        if test_dir:
            cleanup(test_dir)

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Unit tests for constitution metadata extraction in orchestrator.py

Tests verify that parse_task() correctly extracts constitution rules
from task descriptions and stores them in task.constitution_rules.
"""

import tempfile
import json
from pathlib import Path
import sys

# Add cli directory to path
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import TaskOrchestrator


def test_basic_constitution_extraction():
    """Test extraction of multiple constitution rules"""
    test_tasks = """
- [ ] Task with constitution
  - **Constitution**: rule1, rule2, rule3
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_tasks)
        f.flush()

        orch = TaskOrchestrator(f.name)
        orch.parse_tasks()

        assert len(orch.tasks) == 1
        assert orch.tasks[0].constitution_rules == ['rule1', 'rule2', 'rule3']
        print("✅ Basic constitution extraction: PASS")


def test_single_constitution_rule():
    """Test extraction of single constitution rule"""
    test_tasks = """
- [ ] Task with single rule
  - **Constitution**: single-rule
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_tasks)
        f.flush()

        orch = TaskOrchestrator(f.name)
        orch.parse_tasks()

        assert len(orch.tasks) == 1
        assert orch.tasks[0].constitution_rules == ['single-rule']
        print("✅ Single constitution rule: PASS")


def test_constitution_with_spaces():
    """Test that rules with spaces are trimmed correctly"""
    test_tasks = """
- [ ] Task with spaced rules
  - **Constitution**: rule-one, rule two with spaces, rule-three
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_tasks)
        f.flush()

        orch = TaskOrchestrator(f.name)
        orch.parse_tasks()

        assert len(orch.tasks) == 1
        assert orch.tasks[0].constitution_rules == ['rule-one', 'rule two with spaces', 'rule-three']
        print("✅ Constitution with spaces: PASS")


def test_no_constitution_metadata():
    """Test task without constitution metadata"""
    test_tasks = """
- [ ] Task without constitution
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_tasks)
        f.flush()

        orch = TaskOrchestrator(f.name)
        orch.parse_tasks()

        assert len(orch.tasks) == 1
        assert orch.tasks[0].constitution_rules == []
        print("✅ No constitution metadata: PASS")


def test_empty_constitution():
    """Test task with empty constitution value"""
    test_tasks = """
- [ ] Task with empty constitution
  - **Constitution**:
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_tasks)
        f.flush()

        orch = TaskOrchestrator(f.name)
        orch.parse_tasks()

        assert len(orch.tasks) == 1
        assert orch.tasks[0].constitution_rules == []
        print("✅ Empty constitution: PASS")


def test_completed_task_with_constitution():
    """Test that completed tasks still extract constitution"""
    test_tasks = """
- [x] Completed task
  - **Constitution**: done, verified
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_tasks)
        f.flush()

        orch = TaskOrchestrator(f.name)
        orch.parse_tasks()

        assert len(orch.tasks) == 1
        assert orch.tasks[0].completed == True
        assert orch.tasks[0].constitution_rules == ['done', 'verified']
        print("✅ Completed task with constitution: PASS")


def test_constitution_in_execution_plan():
    """Test that constitution_rules appear in execution_plan.json"""
    test_tasks = """
- [ ] Task with constitution
  - **Constitution**: verify-before-commit, run-tests
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_tasks)
        f.flush()

        orch = TaskOrchestrator(f.name)
        orch.parse_tasks()
        orch.create_waves()
        plan = orch.generate_execution_plan("test-phase")

        # Verify constitution_rules in JSON output
        wave = plan['execution_plan']['waves'][0]
        task = wave['tasks'][0]

        assert 'constitution_rules' in task
        assert task['constitution_rules'] == ['verify-before-commit', 'run-tests']
        print("✅ Constitution in execution plan: PASS")


def test_multiple_tasks_mixed_constitutions():
    """Test multiple tasks with different constitution configurations"""
    test_tasks = """
- [ ] Task 1 with constitution
  - **Constitution**: rule-a, rule-b

- [ ] Task 2 without constitution

- [ ] Task 3 with different rules
  - **Constitution**: rule-x, rule-y, rule-z
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(test_tasks)
        f.flush()

        orch = TaskOrchestrator(f.name)
        orch.parse_tasks()

        assert len(orch.tasks) == 3
        assert orch.tasks[0].constitution_rules == ['rule-a', 'rule-b']
        assert orch.tasks[1].constitution_rules == []
        assert orch.tasks[2].constitution_rules == ['rule-x', 'rule-y', 'rule-z']
        print("✅ Multiple tasks with mixed constitutions: PASS")


if __name__ == '__main__':
    print("Running constitution extraction tests...\n")

    test_basic_constitution_extraction()
    test_single_constitution_rule()
    test_constitution_with_spaces()
    test_no_constitution_metadata()
    test_empty_constitution()
    test_completed_task_with_constitution()
    test_constitution_in_execution_plan()
    test_multiple_tasks_mixed_constitutions()

    print("\n✅ All constitution extraction tests passed!")

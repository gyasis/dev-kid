"""
Integration test for sentinel task injection round-trip

Tests:
  - sentinel_enabled=False: orchestrator produces zero SENTINEL tasks in plan
  - sentinel_enabled=False: tasks.md is unchanged after orchestration
  - sentinel_enabled=True: orchestrator injects SENTINEL-* tasks
  - sentinel_enabled=True: tasks.md receives SENTINEL-* entries
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Change to a temp directory so orchestrator reads/writes there
FIXTURE_TASKS = """\
- [ ] T001 Implement login endpoint in `src/auth.py`
- [ ] T002 [P] Add JWT validation in `src/middleware.py`
- [ ] T003 Write integration tests in `tests/test_auth.py`
"""


def _setup_temp_project(sentinel_enabled: bool) -> tuple[Path, Path]:
    """Create a temporary project directory with tasks.md and dev-kid.yml."""
    tmp = Path(tempfile.mkdtemp())

    tasks_path = tmp / "tasks.md"
    tasks_path.write_text(FIXTURE_TASKS, encoding='utf-8')

    yml_content = f"""project: test-project
sentinel:
  enabled: {str(sentinel_enabled).lower()}
  mode: auto
"""
    (tmp / "dev-kid.yml").write_text(yml_content, encoding='utf-8')

    return tmp, tasks_path


# ---------------------------------------------------------------------------
# Sentinel disabled — zero injection
# ---------------------------------------------------------------------------

class TestSentinelDisabled:
    def test_zero_sentinel_tasks_in_plan(self):
        """When sentinel.enabled=false, execution_plan has zero SENTINEL tasks."""
        tmp, tasks_path = _setup_temp_project(sentinel_enabled=False)
        plan_path = tmp / "execution_plan.json"

        original_dir = os.getcwd()
        try:
            os.chdir(tmp)
            from cli.orchestrator import TaskOrchestrator
            orch = TaskOrchestrator(str(tasks_path))
            orch.parse_tasks()
            orch.create_waves()
            # Sentinel injection should NOT run
            with patch.object(orch, '_load_sentinel_config', return_value=False):
                plan = orch.generate_execution_plan("Test Phase")

            # Write plan to file
            plan_path.write_text(json.dumps(plan, indent=2), encoding='utf-8')

            # Verify zero SENTINEL tasks
            all_task_ids = [
                task["task_id"]
                for wave in plan["execution_plan"]["waves"]
                for task in wave["tasks"]
            ]
            sentinel_task_ids = [tid for tid in all_task_ids if "SENTINEL" in tid]
            assert len(sentinel_task_ids) == 0, f"Found unexpected SENTINEL tasks: {sentinel_task_ids}"
        finally:
            os.chdir(original_dir)

    def test_tasks_md_unchanged(self):
        """When sentinel.enabled=false, tasks.md is not modified."""
        tmp, tasks_path = _setup_temp_project(sentinel_enabled=False)

        original_dir = os.getcwd()
        try:
            os.chdir(tmp)
            from cli.orchestrator import TaskOrchestrator
            orch = TaskOrchestrator(str(tasks_path))
            orch.parse_tasks()
            orch.create_waves()
            with patch.object(orch, '_load_sentinel_config', return_value=False):
                orch.generate_execution_plan("Test Phase")
        finally:
            os.chdir(original_dir)

        final_content = tasks_path.read_text(encoding='utf-8')
        # No SENTINEL lines should be appended
        assert "SENTINEL" not in final_content, "tasks.md was unexpectedly modified with SENTINEL lines"
        # Original tasks still present
        assert "T001" in final_content
        assert "T002" in final_content

    def test_plan_structure_valid(self):
        """Plan structure has execution_plan.waves with developer tasks."""
        tmp, tasks_path = _setup_temp_project(sentinel_enabled=False)

        original_dir = os.getcwd()
        try:
            os.chdir(tmp)
            from cli.orchestrator import TaskOrchestrator
            orch = TaskOrchestrator(str(tasks_path))
            orch.parse_tasks()
            orch.create_waves()
            with patch.object(orch, '_load_sentinel_config', return_value=False):
                plan = orch.generate_execution_plan("Test Phase")
        finally:
            os.chdir(original_dir)

        assert "execution_plan" in plan
        assert "waves" in plan["execution_plan"]
        assert len(plan["execution_plan"]["waves"]) > 0

        # All tasks should be Developer role
        for wave in plan["execution_plan"]["waves"]:
            for task in wave["tasks"]:
                assert task["agent_role"] == "Developer", \
                    f"Unexpected agent_role: {task['agent_role']} for {task['task_id']}"

    def test_all_three_tasks_present(self):
        """T001, T002, T003 all appear in the plan when sentinel is disabled."""
        tmp, tasks_path = _setup_temp_project(sentinel_enabled=False)

        original_dir = os.getcwd()
        try:
            os.chdir(tmp)
            from cli.orchestrator import TaskOrchestrator
            orch = TaskOrchestrator(str(tasks_path))
            orch.parse_tasks()
            orch.create_waves()
            with patch.object(orch, '_load_sentinel_config', return_value=False):
                plan = orch.generate_execution_plan("Test Phase")
        finally:
            os.chdir(original_dir)

        all_task_ids = [
            task["task_id"]
            for wave in plan["execution_plan"]["waves"]
            for task in wave["tasks"]
        ]
        # Should have exactly 3 tasks (no sentinel doubles)
        assert len(all_task_ids) == 3, f"Expected 3 tasks, got: {all_task_ids}"


# ---------------------------------------------------------------------------
# Sentinel enabled — injection occurs
# ---------------------------------------------------------------------------

class TestSentinelEnabled:
    def test_sentinel_tasks_injected(self):
        """When sentinel.enabled=true, execution_plan has SENTINEL-* tasks."""
        tmp, tasks_path = _setup_temp_project(sentinel_enabled=True)

        original_dir = os.getcwd()
        try:
            os.chdir(tmp)
            from cli.orchestrator import TaskOrchestrator
            orch = TaskOrchestrator(str(tasks_path))
            orch.parse_tasks()
            orch.create_waves()
            # Injection happens separately from plan generation (mirrors execute() internals)
            orch._inject_sentinel_tasks(orch.waves, tasks_path)
            plan = orch.generate_execution_plan("Test Phase")
        finally:
            os.chdir(original_dir)

        all_task_ids = [
            task["task_id"]
            for wave in plan["execution_plan"]["waves"]
            for task in wave["tasks"]
        ]
        sentinel_tasks = [tid for tid in all_task_ids if "SENTINEL" in tid]
        assert len(sentinel_tasks) > 0, "Expected SENTINEL tasks but found none"

    def test_sentinel_tasks_have_correct_agent_role(self):
        """SENTINEL tasks have agent_role=Sentinel."""
        tmp, tasks_path = _setup_temp_project(sentinel_enabled=True)

        original_dir = os.getcwd()
        try:
            os.chdir(tmp)
            from cli.orchestrator import TaskOrchestrator
            orch = TaskOrchestrator(str(tasks_path))
            orch.parse_tasks()
            orch.create_waves()
            orch._inject_sentinel_tasks(orch.waves, tasks_path)
            plan = orch.generate_execution_plan("Test Phase")
        finally:
            os.chdir(original_dir)

        for wave in plan["execution_plan"]["waves"]:
            for task in wave["tasks"]:
                if "SENTINEL" in task["task_id"]:
                    assert task["agent_role"] == "Sentinel", \
                        f"Expected Sentinel role for {task['task_id']}"

    def test_tasks_md_receives_sentinel_entries(self):
        """When sentinel enabled, tasks.md gets SENTINEL-* appended lines."""
        tmp, tasks_path = _setup_temp_project(sentinel_enabled=True)

        original_dir = os.getcwd()
        try:
            os.chdir(tmp)
            from cli.orchestrator import TaskOrchestrator
            orch = TaskOrchestrator(str(tasks_path))
            orch.parse_tasks()
            orch.create_waves()
            orch._inject_sentinel_tasks(orch.waves, tasks_path)
            orch.generate_execution_plan("Test Phase")
        finally:
            os.chdir(original_dir)

        content = tasks_path.read_text(encoding='utf-8')
        assert "SENTINEL" in content, "tasks.md should have SENTINEL entries when enabled"

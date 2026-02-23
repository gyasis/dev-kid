#!/usr/bin/env python3
"""
Task Orchestrator - Converts linear tasks into parallel wave execution
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass, field
from collections import defaultdict

@dataclass
class Task:
    """Represents a single task"""
    id: str
    description: str
    agent_role: str = "Developer"
    file_locks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    constitution_rules: List[str] = field(default_factory=list)
    completed: bool = False

@dataclass
class Wave:
    """Represents an execution wave"""
    wave_id: int
    strategy: str  # PARALLEL_SWARM or SEQUENTIAL_MERGE
    tasks: List[Dict]
    rationale: str
    checkpoint_enabled: bool = True

class TaskOrchestrator:
    """Orchestrates task execution with waves and checkpoints"""

    def __init__(self, tasks_file: str = "tasks.md"):
        self.tasks_file = Path(tasks_file)
        self.tasks: List[Task] = []
        self.waves: List[Wave] = []
        self.file_to_tasks: Dict[str, List[str]] = defaultdict(list)

    def parse_tasks(self) -> None:
        """Parse tasks.md into Task objects"""
        if not self.tasks_file.exists():
            print(f"❌ Error: {self.tasks_file} not found")
            sys.exit(1)

        try:
            content = self.tasks_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"❌ Error reading {self.tasks_file}: {e}")
            sys.exit(1)

        lines = content.split('\n')

        task_id = 1
        current_task_lines = []

        for i, line in enumerate(lines):
            is_task_line = (line.startswith('- [ ]') or line.startswith('- [x]'))
            is_sentinel_line = 'SENTINEL-' in line  # managed by injection, never re-parsed
            if is_task_line and not is_sentinel_line:
                # Process previous task if exists
                if current_task_lines:
                    self._process_task(current_task_lines, task_id)
                    task_id += 1

                # Start new task
                current_task_lines = [line]
            elif is_task_line and is_sentinel_line:
                # End any open task block without processing the sentinel line
                if current_task_lines:
                    self._process_task(current_task_lines, task_id)
                    task_id += 1
                    current_task_lines = []
            elif current_task_lines and line.strip().startswith('- **Constitution**:'):
                # Add constitution line to current task
                current_task_lines.append(line)
            elif not line.strip() and current_task_lines:
                # Empty line ends task block
                self._process_task(current_task_lines, task_id)
                task_id += 1
                current_task_lines = []

        # Process final task if exists
        if current_task_lines:
            self._process_task(current_task_lines, task_id)

    def _process_task(self, task_lines: List[str], task_id: int) -> None:
        """Process a single task with its metadata"""
        import re

        # First line is the task description
        first_line = task_lines[0]
        completed = '[x]' in first_line
        description = first_line.split(']', 1)[1].strip()

        # Extract file references from description
        file_locks = self._extract_file_references(description)

        # Extract dependencies (if "after T123" or "depends on T456")
        dependencies = self._extract_dependencies(description)

        # Extract constitution rules from subsequent lines
        constitution_rules = []
        full_text = '\n'.join(task_lines)
        constitution_match = re.search(r'- \*\*Constitution\*\*: (.+)', full_text, re.MULTILINE)
        if constitution_match:
            rules_str = constitution_match.group(1)
            constitution_rules = [r.strip() for r in rules_str.split(',')]

        task = Task(
            id=f"T{task_id:03d}",
            description=description,
            file_locks=file_locks,
            dependencies=dependencies,
            constitution_rules=constitution_rules,
            completed=completed
        )

        self.tasks.append(task)

        # Build file-to-task mapping
        for file in file_locks:
            self.file_to_tasks[file].append(task.id)

    def _extract_file_references(self, description: str) -> List[str]:
        """Extract file paths from task description"""
        import re
        # Match patterns like: file.py, path/to/file.ts, `src/component.tsx`
        patterns = [
            r'`([^`]+\.[a-zA-Z]+)`',  # backtick-wrapped paths
            r'\b([\w/.-]+\.[a-zA-Z]{2,4})\b'  # plain file paths
        ]

        files = []
        for pattern in patterns:
            matches = re.findall(pattern, description)
            files.extend(matches)

        return list(set(files))  # deduplicate

    def _extract_dependencies(self, description: str) -> List[str]:
        """Extract task dependencies from description"""
        import re
        # Match "after T123" or "depends on T456"
        pattern = r'\b(?:after|depends on)\s+T(\d{3})\b'
        matches = re.findall(pattern, description, re.IGNORECASE)
        return [f"T{m}" for m in matches]

    def analyze_dependencies(self) -> Dict[str, Set[str]]:
        """Build dependency graph"""
        graph = defaultdict(set)

        for task in self.tasks:
            # Explicit dependencies from description
            for dep in task.dependencies:
                graph[task.id].add(dep)

            # Implicit dependencies from file locks
            for file in task.file_locks:
                # Task depends on all previous tasks that touch the same file
                for other_task_id in self.file_to_tasks[file]:
                    if other_task_id != task.id:
                        # Only depend on tasks that come before in original order
                        other_idx = next(i for i, t in enumerate(self.tasks) if t.id == other_task_id)
                        this_idx = next(i for i, t in enumerate(self.tasks) if t.id == task.id)
                        if other_idx < this_idx:
                            graph[task.id].add(other_task_id)

        return graph

    def create_waves(self) -> None:
        """Group tasks into execution waves"""
        dependency_graph = self.analyze_dependencies()

        # Skip tasks already marked [x] in tasks.md — never re-execute
        pending_tasks = [t for t in self.tasks if not t.completed]
        skipped = len(self.tasks) - len(pending_tasks)
        if skipped:
            print(f"   Skipping {skipped} already-completed task(s) [x]")

        # Track which tasks are assigned (seed with completed task IDs so
        # dependency resolution works correctly for remaining tasks)
        assigned_tasks = {t.id for t in self.tasks if t.completed}
        wave_id = 1

        while len(assigned_tasks) < len(self.tasks):
            # Only consider pending (incomplete) tasks for wave assignment
            remaining = [t for t in pending_tasks if t.id not in assigned_tasks]
            if not remaining:
                break
            wave_tasks = []
            wave_files = set()

            for task in remaining:
                if task.id in assigned_tasks:
                    continue

                # Check if all dependencies are assigned to previous waves
                deps_satisfied = all(dep in assigned_tasks for dep in dependency_graph[task.id])

                if not deps_satisfied:
                    continue

                # Check file lock conflicts within this wave
                file_conflict = any(f in wave_files for f in task.file_locks)

                if file_conflict:
                    # Move to next wave
                    continue

                # This task can be added to current wave
                wave_tasks.append(task)
                wave_files.update(task.file_locks)
                assigned_tasks.add(task.id)

            if not wave_tasks:
                # No tasks could be assigned - circular dependency or error
                print("❌ Error: Circular dependency or unresolvable conflicts detected")
                sys.exit(1)

            # Determine strategy
            strategy = "PARALLEL_SWARM" if len(wave_tasks) > 1 else "SEQUENTIAL_MERGE"

            # Create wave
            wave = Wave(
                wave_id=wave_id,
                strategy=strategy,
                tasks=[{
                    "task_id": t.id,
                    "agent_role": "Developer",
                    "instruction": t.description,
                    "file_locks": t.file_locks,
                    "constitution_rules": t.constitution_rules,
                    "completion_handshake": f"Upon success, update tasks.md line containing '{t.description}' to [x]",
                    "dependencies": list(dependency_graph[t.id])
                } for t in wave_tasks],
                rationale=f"Wave {wave_id}: {len(wave_tasks)} independent task(s) with no file conflicts",
                checkpoint_enabled=True
            )

            self.waves.append(wave)
            wave_id += 1

    def _load_sentinel_config(self) -> bool:
        """Return True if sentinel injection is enabled via dev-kid.yml."""
        try:
            import yaml  # optional dependency
        except ImportError:
            try:
                # Minimal YAML parsing without the yaml library
                yml_path = Path("dev-kid.yml")
                if not yml_path.exists():
                    return False
                content = yml_path.read_text(encoding='utf-8')
                # Find 'enabled:' under 'sentinel:' block
                in_sentinel = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith('sentinel:'):
                        in_sentinel = True
                        continue
                    if in_sentinel:
                        if stripped.startswith('enabled:'):
                            value = stripped.split(':', 1)[1].strip().lower()
                            return value not in ('false', '0', 'no', 'off')
                        elif stripped and not stripped.startswith('#') and ':' in stripped and not line.startswith(' '):
                            # New top-level key — sentinel block ended
                            break
                return False
            except Exception:
                return False

        try:
            yml_path = Path("dev-kid.yml")
            if not yml_path.exists():
                return False
            data = yaml.safe_load(yml_path.read_text(encoding='utf-8'))
            return bool(data.get('sentinel', {}).get('enabled', False))
        except Exception:
            return False

    def _load_sentinel_tier_info(self) -> tuple:
        """Return (tier1_model, tier1_url, tier2_model) from dev-kid.yml, with defaults."""
        defaults = ('qwen3-coder:30b', 'http://192.168.0.159:11434', 'claude-sonnet-4-20250514')
        try:
            yml_path = Path("dev-kid.yml")
            if not yml_path.exists():
                return defaults
            content = yml_path.read_text(encoding='utf-8')
            t1_model = t1_url = t2_model = None
            in_sentinel = in_tier1 = in_tier2 = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith('sentinel:'):
                    in_sentinel = True
                    continue
                if in_sentinel:
                    if stripped.startswith('tier1:'):
                        in_tier1, in_tier2 = True, False
                    elif stripped.startswith('tier2:'):
                        in_tier1, in_tier2 = False, True
                    elif stripped and not line.startswith(' ') and ':' in stripped:
                        break  # left sentinel block
                    if in_tier1:
                        if stripped.startswith('model:'):
                            t1_model = stripped.split(':', 1)[1].strip()
                        elif stripped.startswith('ollama_url:'):
                            t1_url = stripped.split(':', 1)[1].strip()
                    if in_tier2 and stripped.startswith('model:'):
                        t2_model = stripped.split(':', 1)[1].strip()
            return (
                t1_model or defaults[0],
                t1_url or defaults[1],
                t2_model or defaults[2],
            )
        except Exception:
            return defaults

    def _load_sentinel_granularity(self) -> tuple:
        """Return (granularity, n) from dev-kid.yml. Defaults: ('per-task', 3)."""
        granularity = 'per-task'
        n = 3
        try:
            yml_path = Path("dev-kid.yml")
            if not yml_path.exists():
                return (granularity, n)
            content = yml_path.read_text(encoding='utf-8')
            in_sentinel = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith('sentinel:'):
                    in_sentinel = True
                    continue
                if in_sentinel:
                    if stripped and not line.startswith(' ') and ':' in stripped:
                        break
                    if stripped.startswith('injection_granularity:'):
                        granularity = stripped.split(':', 1)[1].strip()
                    elif stripped.startswith('injection_n:'):
                        try:
                            n = int(stripped.split(':', 1)[1].strip())
                        except ValueError:
                            pass
        except Exception:
            pass
        return (granularity, max(1, n))

    def _inject_sentinel_tasks(self, waves: List['Wave'], tasks_file: Path) -> None:
        """Insert SENTINEL tasks according to injection_granularity in dev-kid.yml.

        Granularity modes:
          per-task : one SENTINEL after every developer task (default)
          per-wave : one SENTINEL at end of each wave (covers all tasks in wave)
          per-n    : one SENTINEL every N developer tasks within a wave

        Atomically appends matching '- [ ] SENTINEL-<id>: ...' lines to tasks.md.
        Called only when sentinel.enabled = true in dev-kid.yml.

        Args:
            waves: List of Wave objects (modified in-place).
            tasks_file: Path to tasks.md for atomic append.
        """
        granularity, n = self._load_sentinel_granularity()
        sentinel_lines_to_append: List[str] = []

        for wave in waves:
            dev_tasks = list(wave.tasks)
            injected: List[Dict] = []

            if granularity == 'per-wave':
                # One sentinel at the end of the wave, covering all tasks
                injected.extend(dev_tasks)
                last_task = dev_tasks[-1]
                covered = ', '.join(t['task_id'] for t in dev_tasks)
                sentinel_id = f"SENTINEL-W{wave.wave_id}"
                sentinel_instruction = (
                    f"Sentinel validation for wave {wave.wave_id} "
                    f"({covered}): verify all implementations pass tests"
                )
                sentinel_task = {
                    "task_id": sentinel_id,
                    "agent_role": "Sentinel",
                    "instruction": sentinel_instruction,
                    "file_locks": list(last_task.get("file_locks", [])),
                    "constitution_rules": [],
                    "completion_handshake": (
                        f"Upon success, update tasks.md line containing '{sentinel_instruction}' to [x]"
                    ),
                    "dependencies": [t['task_id'] for t in dev_tasks],
                    "parent_task_id": last_task['task_id'],
                }
                injected.append(sentinel_task)
                sentinel_lines_to_append.append(f"- [ ] {sentinel_id}: {sentinel_instruction}")

            elif granularity == 'per-n':
                # One sentinel every N developer tasks
                for i, task in enumerate(dev_tasks):
                    injected.append(task)
                    if (i + 1) % n == 0 or i == len(dev_tasks) - 1:
                        batch = dev_tasks[max(0, i + 1 - n):i + 1]
                        covered = ', '.join(t['task_id'] for t in batch)
                        sentinel_id = f"SENTINEL-{task['task_id']}"
                        sentinel_instruction = (
                            f"Sentinel validation for {covered}: verify implementations pass tests"
                        )
                        sentinel_task = {
                            "task_id": sentinel_id,
                            "agent_role": "Sentinel",
                            "instruction": sentinel_instruction,
                            "file_locks": list(task.get("file_locks", [])),
                            "constitution_rules": [],
                            "completion_handshake": (
                                f"Upon success, update tasks.md line containing '{sentinel_instruction}' to [x]"
                            ),
                            "dependencies": [t['task_id'] for t in batch],
                            "parent_task_id": task['task_id'],
                        }
                        injected.append(sentinel_task)
                        sentinel_lines_to_append.append(
                            f"- [ ] {sentinel_id}: {sentinel_instruction}"
                        )

            else:
                # per-task (default): one SENTINEL after every developer task
                for task in dev_tasks:
                    injected.append(task)
                    sentinel_id = f"SENTINEL-{task['task_id']}"
                    sentinel_instruction = (
                        f"Sentinel validation for {task['task_id']}: verify implementation passes tests"
                    )
                    sentinel_task = {
                        "task_id": sentinel_id,
                        "agent_role": "Sentinel",
                        "instruction": sentinel_instruction,
                        "file_locks": list(task.get("file_locks", [])),
                        "constitution_rules": [],
                        "completion_handshake": (
                            f"Upon success, update tasks.md line containing '{sentinel_instruction}' to [x]"
                        ),
                        "dependencies": [task["task_id"]],
                        "parent_task_id": task["task_id"],
                    }
                    injected.append(sentinel_task)
                    sentinel_lines_to_append.append(
                        f"- [ ] {sentinel_id}: {sentinel_instruction}"
                    )

            wave.tasks = injected

        # Atomic append to tasks.md
        if sentinel_lines_to_append and tasks_file.exists():
            existing = tasks_file.read_text(encoding='utf-8')
            # Only append lines not already present
            new_lines = [
                line for line in sentinel_lines_to_append
                if line not in existing
            ]
            if new_lines:
                separator = '\n' if existing.endswith('\n') else '\n\n'
                updated = existing + separator + '\n'.join(new_lines) + '\n'
                temp = tasks_file.with_suffix('.tmp')
                temp.write_text(updated, encoding='utf-8')
                temp.rename(tasks_file)

    def generate_execution_plan(self, phase_id: str = "default") -> Dict:
        """Generate complete execution plan in JSON schema format"""
        return {
            "execution_plan": {
                "phase_id": phase_id,
                "waves": [{
                    "wave_id": wave.wave_id,
                    "strategy": wave.strategy,
                    "rationale": wave.rationale,
                    "tasks": wave.tasks,
                    "checkpoint_after": {
                        "enabled": wave.checkpoint_enabled,
                        "verification_criteria": f"Verify all Wave {wave.wave_id} tasks are marked [x] in tasks.md",
                        "git_agent": "git-version-manager",
                        "memory_bank_agent": "memory-bank-keeper"
                    }
                } for wave in self.waves]
            }
        }

    def execute(self, phase_id: str = "default") -> None:
        """Parse tasks and generate execution plan"""
        print("🔍 Parsing tasks...")
        self.parse_tasks()
        print(f"   Found {len(self.tasks)} tasks")

        print("📊 Analyzing dependencies...")
        dep_graph = self.analyze_dependencies()
        total_deps = sum(len(deps) for deps in dep_graph.values())
        print(f"   Detected {total_deps} dependencies")

        print("🌊 Creating execution waves...")
        self.create_waves()
        print(f"   Organized into {len(self.waves)} waves")

        # Sentinel injection (post-wave-assignment, only if enabled)
        if self._load_sentinel_config():
            tier1_model, tier1_url, tier2_model = self._load_sentinel_tier_info()
            granularity, n = self._load_sentinel_granularity()
            granularity_label = {
                'per-task': 'per-task  (SENTINEL after every task)',
                'per-wave': 'per-wave  (one SENTINEL at end of each wave)',
                'per-n':    f'per-{n}    (SENTINEL every {n} tasks)',
            }.get(granularity, granularity)
            print("🛡️  Integration Sentinel: ENABLED")
            print(f"   Tier 1 → micro-agent via Ollama  ({tier1_model} @ {tier1_url})")
            print(f"   Tier 2 → micro-agent via cloud   ({tier2_model}, on Tier 1 exhaustion)")
            print(f"   Granularity: {granularity_label}")
            self._inject_sentinel_tasks(self.waves, self.tasks_file)
            sentinel_count = sum(
                1 for w in self.waves for t in w.tasks
                if isinstance(t, dict) and t.get('agent_role') == 'Sentinel'
            )
            print(f"   Injected {sentinel_count} SENTINEL tasks across waves")
        else:
            print("⬜ Integration Sentinel: DISABLED  (no micro-agent testing)")
            print("   Set sentinel.enabled: true in dev-kid.yml to activate.")

        plan = self.generate_execution_plan(phase_id)

        # dbt dependency ordering: if dbt_project.yml exists, override wave assignments
        if Path("dbt_project.yml").exists():
            try:
                import re as _re
                import sys as _sys
                _sys.path.insert(0, str(Path(__file__).parent))
                from dbt_graph import DBTGraph, DBTTopologicalSort, CycleDetector

                graph = DBTGraph().load(".")
                print(f"   🌿 dbt project detected — applying DAG-aware wave ordering")

                if graph.nodes:
                    cycle = CycleDetector.detect_cycle(graph)
                    if cycle:
                        print(f"   ❌ Circular dependency detected: {cycle}")
                        print("   Halting orchestration. Fix the circular ref() before proceeding.")
                        _sys.exit(1)

                    def _find_dbt_model_name(task_dict: dict, _graph: DBTGraph, _file_to_model: dict) -> "str | None":
                        """Find a dbt model name for a task by checking:
                        1. File locks ending in .sql — extract stem (filename without .sql)
                        2. Task instruction text — look for any word matching a known graph node
                        """
                        # Check file locks for .sql paths
                        for fl in task_dict.get("file_locks", []):
                            # Direct file_path → model lookup from manifest/regex data
                            model_name = _file_to_model.get(fl)
                            if model_name:
                                return model_name
                            # Stem-based fallback: models/stg_orders.sql → stg_orders
                            if fl.endswith(".sql"):
                                stem = Path(fl).stem
                                if stem in _graph.nodes:
                                    return stem
                        # Check instruction text for known model names
                        instruction = task_dict.get("instruction", "")
                        words = _re.findall(r'\b\w+\b', instruction.lower())
                        for word in words:
                            if word in _graph.nodes:
                                return word
                        return None

                    # Map file_path → model_name for tasks in the plan
                    file_to_model = graph.get_file_to_model_map()
                    task_model_names: list[str] = []
                    task_to_model: dict[str, str] = {}
                    for wave in plan["execution_plan"]["waves"]:
                        for task in wave["tasks"]:
                            model_name = _find_dbt_model_name(task, graph, file_to_model)
                            if model_name and task["task_id"] not in task_to_model:
                                task_model_names.append(model_name)
                                task_to_model[task["task_id"]] = model_name

                    print(f"   📊 {len(task_model_names)} dbt model task(s) identified")

                    if task_model_names:
                        wave_overrides = DBTTopologicalSort.assign_waves(task_model_names, graph)

                        # Snapshot original wave assignments for non-dbt tasks
                        task_id_to_orig_wave: dict[str, int] = {}
                        for orig_wave in plan["execution_plan"]["waves"]:
                            for task in orig_wave["tasks"]:
                                task_id_to_orig_wave[task["task_id"]] = orig_wave["wave_id"]

                        # Collect all tasks by id for rebuild
                        all_tasks_by_id: dict[str, dict] = {}
                        for orig_wave in plan["execution_plan"]["waves"]:
                            for task in orig_wave["tasks"]:
                                all_tasks_by_id[task["task_id"]] = task

                        new_waves_by_num: dict[int, list] = {}
                        for task_id, task in all_tasks_by_id.items():
                            model = task_to_model.get(task_id)
                            if model:
                                # dbt task: use DAG-derived wave number
                                wave_num = wave_overrides.get(model, 1)
                            else:
                                # Non-dbt task: preserve original file-lock-derived wave
                                wave_num = task_id_to_orig_wave.get(task_id, 1)
                            new_waves_by_num.setdefault(wave_num, []).append(task)

                        if new_waves_by_num:
                            max_wave = max(new_waves_by_num.keys())
                            new_waves = []
                            for wid in range(1, max_wave + 1):
                                tasks_in_wave = new_waves_by_num.get(wid, [])
                                if not tasks_in_wave:
                                    continue
                                # Determine strategy: SEQUENTIAL_MERGE if any file lock
                                # conflicts exist within this wave, else PARALLEL_SWARM
                                wave_file_locks: set[str] = set()
                                has_conflict = False
                                for wt in tasks_in_wave:
                                    for fl in wt.get("file_locks", []):
                                        if fl in wave_file_locks:
                                            has_conflict = True
                                            break
                                        wave_file_locks.add(fl)
                                    if has_conflict:
                                        break
                                if has_conflict or len(tasks_in_wave) == 1:
                                    strategy = "SEQUENTIAL_MERGE"
                                else:
                                    strategy = "PARALLEL_SWARM"
                                new_waves.append({
                                    "wave_id": wid,
                                    "strategy": strategy,
                                    "rationale": f"dbt dependency-ordered wave {wid}",
                                    "tasks": tasks_in_wave,
                                    "checkpoint_after": {
                                        "enabled": True,
                                        "verification_criteria": f"Verify all Wave {wid} tasks are marked [x] in tasks.md",
                                        "git_agent": "git-version-manager",
                                        "memory_bank_agent": "memory-bank-keeper"
                                    }
                                })
                            plan["execution_plan"]["waves"] = new_waves
                            print(f"   dbt DAG applied: {len(task_model_names)} model(s) reordered across {len(new_waves)} wave(s)")
            except SystemExit:
                raise
            except Exception as _dbt_err:
                print(f"   ⚠️  dbt wave ordering failed (non-fatal): {_dbt_err}")

        # Output to execution_plan.json (atomic write)
        output_file = Path("execution_plan.json")
        temp_file = output_file.with_suffix('.tmp')
        try:
            temp_file.write_text(json.dumps(plan, indent=2), encoding='utf-8')
            temp_file.rename(output_file)  # Atomic on POSIX
            print(f"✅ Execution plan written to: {output_file}")
        except Exception as e:
            print(f"❌ Error writing execution plan: {e}")
            if temp_file.exists():
                temp_file.unlink()
            sys.exit(1)

        # Print summary
        print("\n📋 Wave Summary:")
        for wave in self.waves:
            print(f"   Wave {wave.wave_id} ({wave.strategy}): {len(wave.tasks)} task(s)")
            for task in wave.tasks:
                print(f"      - {task['task_id']}: {task['instruction'][:60]}...")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Task Orchestrator - Wave-based parallel execution")
    parser.add_argument('--tasks-file', default='tasks.md', help='Path to tasks.md file')
    parser.add_argument('--phase-id', default='default', help='Phase identifier')

    args = parser.parse_args()

    orchestrator = TaskOrchestrator(args.tasks_file)
    orchestrator.execute(args.phase_id)

if __name__ == '__main__':
    main()

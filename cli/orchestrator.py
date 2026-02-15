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
            if line.startswith('- [ ]') or line.startswith('- [x]'):
                # Process previous task if exists
                if current_task_lines:
                    self._process_task(current_task_lines, task_id)
                    task_id += 1

                # Start new task
                current_task_lines = [line]
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

        # Track which tasks are completed (wave assignment)
        assigned_tasks = set()
        wave_id = 1

        while len(assigned_tasks) < len(self.tasks):
            wave_tasks = []
            wave_files = set()

            for task in self.tasks:
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

        plan = self.generate_execution_plan(phase_id)

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

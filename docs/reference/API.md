# Dev-Kid Python API Reference

**Version**: 2.0.0
**Last Updated**: 2026-01-05

Complete Python API documentation for dev-kid orchestration and monitoring modules.

---

## Table of Contents

1. [Overview](#overview)
2. [TaskOrchestrator](#taskorchestrator)
3. [WaveExecutor](#waveexecutor)
4. [TaskWatchdog](#taskwatchdog)
5. [Data Classes](#data-classes)
6. [Error Handling](#error-handling)
7. [Usage Examples](#usage-examples)

---

## Overview

Dev-kid provides three main Python modules:

- **orchestrator.py**: Convert linear tasks into parallel execution waves
- **wave_executor.py**: Execute waves with checkpoint verification
- **task_watchdog.py**: Background task monitoring daemon

All modules are located in `~/.dev-kid/cli/`.

### Import Paths

```python
# If running from project directory
from orchestrator import TaskOrchestrator, Task, Wave
from wave_executor import WaveExecutor
from task_watchdog import TaskWatchdog
```

---

## TaskOrchestrator

Convert linear task list into wave-based execution plan with dependency analysis and file locking.

### Class Definition

```python
class TaskOrchestrator:
    """Orchestrates task execution with waves and checkpoints"""

    def __init__(self, tasks_file: str = "tasks.md")
```

### Constructor

#### `__init__(tasks_file: str = "tasks.md")`

**Parameters**:
- `tasks_file` (str, optional): Path to tasks.md file. Default: "tasks.md"

**Description**: Initialize orchestrator with task file path.

**Example**:
```python
orchestrator = TaskOrchestrator()  # Use default tasks.md
orchestrator = TaskOrchestrator("custom_tasks.md")  # Custom file
```

---

### Public Methods

#### `parse_tasks() -> None`

**Description**: Parse tasks.md into Task objects with completion status, file locks, and dependencies.

**Raises**:
- `SystemExit(1)`: If tasks file not found

**Side Effects**:
- Populates `self.tasks` list
- Builds `self.file_to_tasks` mapping

**Task Format**:
```markdown
- [ ] Task description with `file.py` reference
- [x] Completed task with multiple `src/app.py` and `tests/test.py` files
- [ ] Task depends on T001
```

**Parsing Rules**:
1. Lines starting with `- [ ]` are pending tasks
2. Lines starting with `- [x]` are completed tasks
3. Files wrapped in backticks are extracted as file locks
4. Dependencies match "after T123" or "depends on T456" pattern

**Example**:
```python
orchestrator = TaskOrchestrator()
orchestrator.parse_tasks()
print(f"Found {len(orchestrator.tasks)} tasks")
```

---

#### `analyze_dependencies() -> Dict[str, Set[str]]`

**Description**: Build dependency graph from explicit and implicit dependencies.

**Returns**:
- `Dict[str, Set[str]]`: Mapping of task ID to set of dependency task IDs

**Dependency Types**:
1. **Explicit**: From "after T123" or "depends on T456" in description
2. **Implicit**: From file locks (tasks modifying same file are sequential)

**Algorithm**:
```
For each task:
  1. Add explicit dependencies from description
  2. For each file in task.file_locks:
     - Find all other tasks that modify this file
     - Add dependency if other task comes before in original order
```

**Example**:
```python
orchestrator = TaskOrchestrator()
orchestrator.parse_tasks()
graph = orchestrator.analyze_dependencies()

# Print dependencies
for task_id, deps in graph.items():
    if deps:
        print(f"{task_id} depends on: {deps}")
```

**Example Output**:
```
T003 depends on: {'T001', 'T002'}
T005 depends on: {'T003'}  # Implicit from file lock
```

---

#### `create_waves() -> None`

**Description**: Group tasks into execution waves using greedy algorithm with constraint satisfaction.

**Raises**:
- `SystemExit(1)`: If circular dependency or unresolvable conflict detected

**Side Effects**:
- Populates `self.waves` list

**Algorithm**:
```
Initialize: assigned_tasks = empty set, wave_id = 1

While tasks remain:
  For each unassigned task:
    If all dependencies assigned:
      If no file conflicts with current wave:
        Add to wave
        Add files to wave_files
        Mark as assigned

  If no tasks added:
    Error: circular dependency

  Create wave with collected tasks
  wave_id++
```

**Wave Strategy Assignment**:
- `PARALLEL_SWARM`: Multiple tasks in wave (can run in parallel)
- `SEQUENTIAL_MERGE`: Single task in wave (must run sequentially)

**Example**:
```python
orchestrator = TaskOrchestrator()
orchestrator.parse_tasks()
orchestrator.create_waves()

print(f"Created {len(orchestrator.waves)} waves")
for wave in orchestrator.waves:
    print(f"Wave {wave.wave_id}: {wave.strategy}, {len(wave.tasks)} tasks")
```

---

#### `generate_execution_plan(phase_id: str = "default") -> Dict`

**Description**: Generate complete execution plan in JSON schema format.

**Parameters**:
- `phase_id` (str, optional): Phase identifier for the plan. Default: "default"

**Returns**:
- `Dict`: JSON-serializable execution plan with waves

**Schema**:
```python
{
  "execution_plan": {
    "phase_id": str,
    "waves": [
      {
        "wave_id": int,
        "strategy": "PARALLEL_SWARM" | "SEQUENTIAL_MERGE",
        "rationale": str,
        "tasks": [
          {
            "task_id": str,
            "agent_role": str,
            "instruction": str,
            "file_locks": [str],
            "completion_handshake": str,
            "dependencies": [str]
          }
        ],
        "checkpoint_after": {
          "enabled": bool,
          "verification_criteria": str,
          "git_agent": str,
          "memory_bank_agent": str
        }
      }
    ]
  }
}
```

**Example**:
```python
orchestrator = TaskOrchestrator()
orchestrator.parse_tasks()
orchestrator.create_waves()
plan = orchestrator.generate_execution_plan("Phase 7")

import json
with open("execution_plan.json", "w") as f:
    json.dump(plan, f, indent=2)
```

---

#### `execute(phase_id: str = "default") -> None`

**Description**: Complete orchestration workflow: parse, analyze, create waves, and write plan.

**Parameters**:
- `phase_id` (str, optional): Phase identifier. Default: "default"

**Side Effects**:
- Prints progress to stdout
- Writes `execution_plan.json`

**Workflow**:
1. Parse tasks from tasks.md
2. Analyze dependencies
3. Create waves
4. Generate execution plan
5. Write to execution_plan.json
6. Print summary

**Example**:
```python
orchestrator = TaskOrchestrator("tasks.md")
orchestrator.execute("Phase 7: Workflow State")
```

**Output**:
```
🔍 Parsing tasks...
   Found 15 tasks

📊 Analyzing dependencies...
   Detected 8 dependencies

🌊 Creating execution waves...
   Organized into 4 waves

✅ Execution plan written to: execution_plan.json

📋 Wave Summary:
   Wave 1 (PARALLEL_SWARM): 5 task(s)
      - T001: Set up project structure
      ...
```

---

### Private Methods

#### `_extract_file_references(description: str) -> List[str]`

**Description**: Extract file paths from task description using regex patterns.

**Parameters**:
- `description` (str): Task description text

**Returns**:
- `List[str]`: Deduplicated list of file paths

**Patterns Matched**:
1. Backtick-wrapped: \`path/to/file.ext\`
2. Plain paths: path/to/file.ext

**Example**:
```python
desc = "Update `src/app.py` and tests/test_api.py"
files = orchestrator._extract_file_references(desc)
# Returns: ['src/app.py', 'tests/test_api.py']
```

---

#### `_extract_dependencies(description: str) -> List[str]`

**Description**: Extract task dependencies from description.

**Parameters**:
- `description` (str): Task description text

**Returns**:
- `List[str]`: List of dependency task IDs (e.g., ["T001", "T003"])

**Patterns Matched**:
- "after T123"
- "depends on T456"

**Example**:
```python
desc = "Build API after T001 and depends on T003"
deps = orchestrator._extract_dependencies(desc)
# Returns: ['T001', 'T003']
```

---

### Attributes

#### `tasks_file: Path`

**Type**: `pathlib.Path`
**Description**: Path to tasks.md file

#### `tasks: List[Task]`

**Type**: `List[Task]`
**Description**: Parsed task objects

#### `waves: List[Wave]`

**Type**: `List[Wave]`
**Description**: Grouped execution waves

#### `file_to_tasks: Dict[str, List[str]]`

**Type**: `Dict[str, List[str]]`
**Description**: Mapping of file path to task IDs that modify it

---

## WaveExecutor

Execute waves from execution plan with checkpoint verification.

### Class Definition

```python
class WaveExecutor:
    """Executes waves with parallel task execution and checkpoints"""

    def __init__(self, plan_file: str = "execution_plan.json")
```

### Constructor

#### `__init__(plan_file: str = "execution_plan.json")`

**Parameters**:
- `plan_file` (str, optional): Path to execution plan JSON. Default: "execution_plan.json"

**Description**: Initialize executor with plan file path.

**Example**:
```python
executor = WaveExecutor()  # Use default execution_plan.json
executor = WaveExecutor("custom_plan.json")  # Custom file
```

---

### Public Methods

#### `load_plan() -> None`

**Description**: Load execution plan from JSON file.

**Raises**:
- `SystemExit(1)`: If plan file not found

**Side Effects**:
- Populates `self.plan` dict

**Example**:
```python
executor = WaveExecutor()
executor.load_plan()
print(f"Loaded plan with {len(executor.plan['execution_plan']['waves'])} waves")
```

---

#### `verify_wave_completion(wave_id: int, tasks: List[Dict]) -> bool`

**Description**: Verify all tasks in wave are marked complete in tasks.md.

**Parameters**:
- `wave_id` (int): Wave number being verified
- `tasks` (List[Dict]): Task specifications from execution plan

**Returns**:
- `bool`: True if all tasks marked [x], False otherwise

**Verification Logic**:
1. Read tasks.md
2. For each task in wave:
   - Search for task description in tasks.md
   - Check if line contains [x]
   - Print verification status
3. Return False if any task incomplete or not found

**Example**:
```python
executor = WaveExecutor()
executor.load_plan()
wave = executor.plan['execution_plan']['waves'][0]
verified = executor.verify_wave_completion(1, wave['tasks'])

if verified:
    print("Wave 1 complete!")
else:
    print("Wave 1 incomplete - halting")
```

**Output**:
```
   ✅ T001: Verified complete
   ✅ T002: Verified complete
   ❌ T003: NOT marked complete!
```

---

#### `execute_checkpoint(wave_id: int, checkpoint: Dict) -> None`

**Description**: Execute checkpoint between waves with verification and git commit.

**Parameters**:
- `wave_id` (int): Wave number just completed
- `checkpoint` (Dict): Checkpoint configuration from execution plan

**Raises**:
- `SystemExit(1)`: If verification fails

**Checkpoint Steps**:
1. memory-bank-keeper validates tasks.md (verify_wave_completion)
2. memory-bank-keeper updates progress.md
3. git-version-manager creates checkpoint commit
4. Halt if verification fails

**Example**:
```python
executor = WaveExecutor()
executor.load_plan()
wave = executor.plan['execution_plan']['waves'][0]
executor.execute_checkpoint(1, wave['checkpoint_after'])
```

**Output**:
```
🔍 Checkpoint after Wave 1...
   Step 1: memory-bank-keeper validates tasks.md...
   ✅ T001: Verified complete
   ✅ All tasks verified complete
   Step 2: memory-bank-keeper updates progress.md...
   Step 3: git-version-manager creates checkpoint...
✅ Checkpoint 1 complete
```

---

#### `execute_wave(wave: Dict) -> None`

**Description**: Execute a single wave (display info, delegate to agents).

**Parameters**:
- `wave` (Dict): Wave specification from execution plan

**Description**: Displays wave information and task assignments. In production, would spawn agents for actual execution.

**Example**:
```python
executor = WaveExecutor()
executor.load_plan()
wave = executor.plan['execution_plan']['waves'][0]
executor.execute_wave(wave)
```

**Output**:
```
🌊 Executing Wave 1 (PARALLEL_SWARM)...
   Rationale: Wave 1: 5 independent task(s) with no file conflicts
   Tasks: 5
   Strategy: Parallel execution
      🤖 Agent Developer: T001 - Set up project structure
      🤖 Agent Developer: T002 - Configure database connection
   ⏳ Wave 1 in progress...
   ℹ️  Agents must mark tasks complete in tasks.md before wave ends
```

---

#### `execute() -> None`

**Description**: Execute all waves with checkpoints.

**Workflow**:
1. Load execution plan
2. For each wave:
   - Execute wave (execute_wave)
   - Verify completion (verify_wave_completion)
   - Create checkpoint (execute_checkpoint)
   - Halt if verification fails
3. Report completion

**Example**:
```python
executor = WaveExecutor()
executor.execute()
```

---

### Private Methods

#### `_update_progress(wave_id: int, tasks: List[Dict]) -> None`

**Description**: Update progress.md with wave completion.

**Parameters**:
- `wave_id` (int): Completed wave number
- `tasks` (List[Dict]): Task specifications

**Side Effects**:
- Appends to `memory-bank/private/$USER/progress.md`

---

#### `_git_checkpoint(wave_id: int) -> None`

**Description**: Create git checkpoint commit.

**Parameters**:
- `wave_id` (int): Completed wave number

**Side Effects**:
- Stages all changes (`git add .`)
- Creates commit with standard message

**Commit Message Format**:
```
[CHECKPOINT] Wave {wave_id} Complete

All tasks verified and validated
```

---

### Attributes

#### `plan_file: Path`

**Type**: `pathlib.Path`
**Description**: Path to execution plan JSON

#### `plan: Dict`

**Type**: `Dict`
**Description**: Loaded execution plan

#### `tasks_file: Path`

**Type**: `pathlib.Path`
**Description**: Path to tasks.md (default: "tasks.md")

---

## TaskWatchdog

Background task monitoring daemon that survives context compression.

### Class Definition

```python
class TaskWatchdog:
    """Monitors task execution and prevents loss during context compression"""

    def __init__(self, state_file: str = ".claude/task_timers.json")
```

### Constructor

#### `__init__(state_file: str = ".claude/task_timers.json")`

**Parameters**:
- `state_file` (str, optional): Path to state persistence file. Default: ".claude/task_timers.json"

**Description**: Initialize watchdog with state file path.

**Example**:
```python
watchdog = TaskWatchdog()  # Use default state file
watchdog = TaskWatchdog("custom_state.json")  # Custom file
```

---

### Public Methods

#### `load_state() -> None`

**Description**: Load task timer state from disk.

**Side Effects**:
- Populates `self.state` dict
- Creates default state if file doesn't exist

**State Schema**:
```python
{
  "running_tasks": {
    "TASK-001": {
      "description": str,
      "started_at": str,  # ISO format datetime
      "last_checked": str,
      "status": "running"
    }
  },
  "completed_tasks": {
    "TASK-002": {
      "description": str,
      "started_at": str,
      "completed_at": str,
      "duration_seconds": float,
      "duration_human": str  # e.g., "1h 15m"
    }
  },
  "warnings": [
    {
      "type": str,  # "long_running" | "possibly_forgotten"
      "task_id": str,
      "description": str,
      "duration": str,
      "timestamp": str
    }
  ]
}
```

**Example**:
```python
watchdog = TaskWatchdog()
watchdog.load_state()
print(f"Running: {len(watchdog.state['running_tasks'])}")
print(f"Completed: {len(watchdog.state['completed_tasks'])}")
```

---

#### `save_state() -> None`

**Description**: Persist state to disk (survives context compression).

**Side Effects**:
- Creates parent directory if needed
- Writes JSON to state file with indentation

**Example**:
```python
watchdog = TaskWatchdog()
watchdog.load_state()
# Modify state...
watchdog.save_state()
```

---

#### `start_task(task_id: str, description: str) -> None`

**Description**: Start timer for a task.

**Parameters**:
- `task_id` (str): Unique task identifier
- `description` (str): Task description

**Side Effects**:
- Adds task to running_tasks
- Persists state to disk
- Prints confirmation

**Example**:
```python
watchdog = TaskWatchdog()
watchdog.load_state()
watchdog.start_task("TASK-001", "Implement user authentication")
```

**Output**:
```
⏱️  Started timer for TASK-001: Implement user authentication
```

---

#### `complete_task(task_id: str) -> None`

**Description**: Complete a task and record timing.

**Parameters**:
- `task_id` (str): Task ID to complete

**Side Effects**:
- Removes from running_tasks
- Calculates duration
- Adds to completed_tasks with timing
- Persists state to disk
- Prints completion message

**Example**:
```python
watchdog = TaskWatchdog()
watchdog.load_state()
watchdog.complete_task("TASK-001")
```

**Output**:
```
✅ Completed TASK-001 in 1h 15m
```

or (if not found)

```
⚠️  Warning: Task TASK-001 not found in running tasks
```

---

#### `check_tasks() -> None`

**Description**: Check for tasks exceeding guidelines or showing signs of being stalled.

**Detection Rules**:
1. **Exceeds guideline**: Task running > 7 minutes (420 seconds) - investigate what's happening
2. **Possibly stalled**: Task no check > 15 min (900 seconds) - no activity detected

**Actions**:
1. Sync with tasks.md (detect [x] completions)
2. Update last_checked timestamps
3. Generate warnings for long-running tasks
4. Generate warnings for forgotten tasks
5. Save state

**Example**:
```python
watchdog = TaskWatchdog()
watchdog.load_state()
watchdog.check_tasks()
```

**Output**:
```
⚠️  TASK-003 running for 1h 15m
⚠️  TASK-007 may have been forgotten (no check for 45m)
```

---

#### `run_watchdog(duration_minutes: int = None) -> None`

**Description**: Run watchdog in continuous monitoring mode.

**Parameters**:
- `duration_minutes` (int, optional): Run for specified duration, or indefinitely if None

**Behavior**:
1. Infinite loop (or until duration reached)
2. Load state from disk
3. Run check_tasks
4. Print status
5. Sleep for check_interval (300 seconds = 5 minutes)
6. Handle KeyboardInterrupt gracefully

**Example**:
```python
# Run indefinitely
watchdog = TaskWatchdog()
watchdog.run_watchdog()

# Run for 30 minutes
watchdog.run_watchdog(duration_minutes=30)
```

**Output**:
```
🐕 Task Watchdog started (checking every 5 minutes)
   State file: .claude/task_timers.json
   Press Ctrl+C to stop

🔍 Watchdog check #1 - 14:30:00
   Running tasks: 2
   Completed tasks: 5
   Warnings: 1

💤 Next check in 5 minutes...

🔍 Watchdog check #2 - 14:35:00
   ...
```

---

#### `report() -> None`

**Description**: Generate task timing report.

**Output**:
1. Running tasks with duration
2. Completed tasks with duration
3. Total and average time
4. Active warnings

**Example**:
```python
watchdog = TaskWatchdog()
watchdog.load_state()
watchdog.report()
```

**Output**: See CLI_REFERENCE.md `watchdog-report` for full output example.

---

### Private Methods

#### `_format_duration(seconds: float) -> str`

**Description**: Format duration in human-readable form.

**Parameters**:
- `seconds` (float): Duration in seconds

**Returns**:
- `str`: Formatted duration (e.g., "45s", "1h 15m", "2h 30m")

**Format Rules**:
- < 60s: "Xs"
- < 3600s: "Xm Ys"
- >= 3600s: "Xh Ym"

**Example**:
```python
watchdog = TaskWatchdog()
print(watchdog._format_duration(45))        # "45s"
print(watchdog._format_duration(4500))      # "1h 15m"
print(watchdog._format_duration(135))       # "2m 15s"
```

---

#### `_sync_with_tasks_md() -> None`

**Description**: Synchronize with tasks.md to detect completed tasks.

**Behavior**:
1. Read tasks.md
2. For each running task:
   - Search for description in tasks.md
   - If line contains [x], call complete_task
3. Auto-complete tasks marked done

**Side Effects**:
- May move tasks from running to completed
- Persists state

---

### Attributes

#### `state_file: Path`

**Type**: `pathlib.Path`
**Description**: Path to state persistence file

#### `tasks_file: Path`

**Type**: `pathlib.Path`
**Description**: Path to tasks.md (default: "tasks.md")

#### `state: Dict`

**Type**: `Dict`
**Description**: Current state (running_tasks, completed_tasks, warnings)

#### `check_interval: int`

**Type**: `int`
**Description**: Check interval in seconds (default: 300 = 5 minutes)

---

## Data Classes

### Task

Represents a single task in the orchestration system.

```python
@dataclass
class Task:
    id: str                      # Task ID (e.g., "T001")
    description: str             # Task text from tasks.md
    agent_role: str = "Developer"  # Agent role assignment
    file_locks: List[str] = field(default_factory=list)  # Files modified
    dependencies: List[str] = field(default_factory=list)  # Dependency task IDs
    completed: bool = False      # Completion status
```

**Example**:
```python
from dataclasses import dataclass, field
from typing import List

task = Task(
    id="T001",
    description="Set up FastAPI project structure",
    file_locks=["src/app.py", "requirements.txt"],
    dependencies=[],
    completed=False
)

print(task.id)           # "T001"
print(task.file_locks)   # ["src/app.py", "requirements.txt"]
```

---

### Wave

Represents an execution wave containing grouped tasks.

```python
@dataclass
class Wave:
    wave_id: int                 # Wave number (1, 2, 3, ...)
    strategy: str                # "PARALLEL_SWARM" | "SEQUENTIAL_MERGE"
    tasks: List[Dict]            # Task specifications
    rationale: str               # Why these tasks grouped
    checkpoint_enabled: bool = True  # Whether to checkpoint after wave
```

**Example**:
```python
from dataclasses import dataclass
from typing import List, Dict

wave = Wave(
    wave_id=1,
    strategy="PARALLEL_SWARM",
    tasks=[
        {"task_id": "T001", "instruction": "Setup project", ...},
        {"task_id": "T002", "instruction": "Configure DB", ...}
    ],
    rationale="Wave 1: 2 independent tasks with no file conflicts",
    checkpoint_enabled=True
)

print(wave.wave_id)      # 1
print(wave.strategy)     # "PARALLEL_SWARM"
print(len(wave.tasks))   # 2
```

---

## Error Handling

### System Exits

All modules use `sys.exit()` for critical errors:

```python
# File not found
if not self.tasks_file.exists():
    print(f"❌ Error: {self.tasks_file} not found")
    sys.exit(1)

# Circular dependency
if not wave_tasks:
    print("❌ Error: Circular dependency or unresolvable conflicts detected")
    sys.exit(1)

# Verification failed
if not verified:
    print(f"\n❌ Checkpoint failed! Wave {wave_id} tasks not complete.")
    print("   Halting execution.")
    sys.exit(1)
```

### Exception Handling

KeyboardInterrupt handled in watchdog:

```python
try:
    while True:
        # Check tasks...
        time.sleep(self.check_interval)
except KeyboardInterrupt:
    print(f"\n\n🛑 Watchdog stopped by user")
    sys.exit(0)
```

---

## Usage Examples

### Complete Orchestration Workflow

```python
#!/usr/bin/env python3
"""
Example: Complete orchestration workflow
"""

from orchestrator import TaskOrchestrator
from wave_executor import WaveExecutor

# Step 1: Create execution plan
print("Creating execution plan...")
orchestrator = TaskOrchestrator("tasks.md")
orchestrator.parse_tasks()
orchestrator.create_waves()
plan = orchestrator.generate_execution_plan("Phase 7")

import json
with open("execution_plan.json", "w") as f:
    json.dump(plan, f, indent=2)

print(f"Created {len(orchestrator.waves)} waves")

# Step 2: Execute waves
print("\nExecuting waves...")
executor = WaveExecutor("execution_plan.json")
executor.execute()

print("Done!")
```

---

### Task Monitoring Daemon

```python
#!/usr/bin/env python3
"""
Example: Run task monitoring daemon
"""

from task_watchdog import TaskWatchdog

# Create and start watchdog
watchdog = TaskWatchdog()
watchdog.load_state()

# Start some tasks
watchdog.start_task("AUTH-001", "Implement JWT authentication")
watchdog.start_task("API-042", "Build user profile endpoint")

# Run monitoring (infinite loop)
watchdog.run_watchdog()
```

---

### Custom Wave Creation

```python
#!/usr/bin/env python3
"""
Example: Custom wave creation logic
"""

from orchestrator import TaskOrchestrator, Task, Wave
from typing import List

class CustomOrchestrator(TaskOrchestrator):
    """Custom orchestrator with domain-specific wave logic"""

    def create_waves(self) -> None:
        """Override to implement custom wave grouping"""
        # Custom logic here
        # Example: Group by agent role instead of dependencies

        dev_tasks = [t for t in self.tasks if "backend" in t.description.lower()]
        test_tasks = [t for t in self.tasks if "test" in t.description.lower()]

        # Create wave for dev tasks
        if dev_tasks:
            wave = Wave(
                wave_id=1,
                strategy="PARALLEL_SWARM",
                tasks=[self._task_to_dict(t) for t in dev_tasks],
                rationale="Development tasks can run in parallel",
                checkpoint_enabled=True
            )
            self.waves.append(wave)

        # Create wave for test tasks
        if test_tasks:
            wave = Wave(
                wave_id=2,
                strategy="SEQUENTIAL_MERGE",
                tasks=[self._task_to_dict(t) for t in test_tasks],
                rationale="Tests run after development complete",
                checkpoint_enabled=True
            )
            self.waves.append(wave)

    def _task_to_dict(self, task: Task) -> dict:
        """Convert Task to dict format"""
        return {
            "task_id": task.id,
            "agent_role": "Developer",
            "instruction": task.description,
            "file_locks": task.file_locks,
            "completion_handshake": f"Mark {task.id} complete in tasks.md",
            "dependencies": task.dependencies
        }

# Usage
orchestrator = CustomOrchestrator()
orchestrator.parse_tasks()
orchestrator.create_waves()
plan = orchestrator.generate_execution_plan("Custom Phase")
```

---

### Manual Task Tracking

```python
#!/usr/bin/env python3
"""
Example: Manual task tracking without daemon
"""

from task_watchdog import TaskWatchdog
from datetime import datetime

watchdog = TaskWatchdog()
watchdog.load_state()

# Start task
task_id = "FEATURE-123"
watchdog.start_task(task_id, "Implement user authentication")

# Simulate work
print("Working on task...")
import time
time.sleep(60)  # Work for 1 minute

# Complete task
watchdog.complete_task(task_id)

# Generate report
watchdog.report()
```

---

### Programmatic Wave Execution

```python
#!/usr/bin/env python3
"""
Example: Programmatic wave execution with custom logic
"""

from wave_executor import WaveExecutor
import subprocess

class CustomExecutor(WaveExecutor):
    """Custom executor with actual task execution"""

    def execute_wave(self, wave: dict) -> None:
        """Override to actually execute tasks"""
        wave_id = wave['wave_id']
        strategy = wave['strategy']
        tasks = wave['tasks']

        print(f"Executing Wave {wave_id} with {strategy}")

        if strategy == "PARALLEL_SWARM":
            # Execute in parallel using multiprocessing
            from multiprocessing import Pool
            with Pool(len(tasks)) as pool:
                pool.map(self._execute_task, tasks)
        else:
            # Execute sequentially
            for task in tasks:
                self._execute_task(task)

    def _execute_task(self, task: dict) -> None:
        """Execute individual task"""
        print(f"Executing {task['task_id']}: {task['instruction']}")

        # Example: Run script for task
        script = f"scripts/task_{task['task_id']}.sh"
        try:
            subprocess.run([script], check=True)
            print(f"✅ {task['task_id']} complete")
        except subprocess.CalledProcessError:
            print(f"❌ {task['task_id']} failed")

# Usage
executor = CustomExecutor()
executor.execute()
```

---

**Python API Reference v2.0.0**
Complete API documentation for dev-kid Python modules

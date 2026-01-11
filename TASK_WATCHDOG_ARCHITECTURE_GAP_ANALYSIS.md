# Task Watchdog Architecture Gap Analysis

**Review Date**: 2026-01-10
**Scope**: Verify task-watchdog alignment with dev-kid architecture and SpecKit integration
**Status**: 🔴 CRITICAL GAPS IDENTIFIED

---

## Executive Summary

**Architectural Verdict**: The task-watchdog system has **fundamental integration gaps** that break the constitution enforcement flow and create data silos. Constitution metadata is lost at multiple critical handoff points, defeating the purpose of Speckit integration.

**Critical Issues**:
1. **Constitution metadata loss** in orchestration pipeline
2. **No watchdog integration** with wave executor
3. **Schema incompatibility** between Rust registry and Python execution plan
4. **Missing enforcement layer** at checkpoint validation
5. **Process coordination gap** between executor and watchdog

---

## 1. State Persistence Layer Analysis

### 1.1 Current State Files

```
Watchdog Layer (Rust):
  └─ rust-watchdog/.claude/process_registry.json
     Schema: { tasks: { [task_id]: TaskInfo } }
     Fields: mode, command, status, started_at, completed_at, native, docker

Orchestration Layer (Python):
  └─ execution_plan.json
     Schema: { execution_plan: { phase_id, waves[] } }
     Fields: wave_id, strategy, rationale, tasks[], checkpoint_after{}

Memory Bank Layer (Markdown):
  └─ memory-bank/shared/.constitution.md
     Format: Markdown sections (Technology, Architecture, Testing, etc.)

SpecKit Layer (Markdown):
  └─ tasks.md
     Format: Checklist with metadata blocks
```

### 1.2 Compatibility Assessment

| Layer | State Format | Persistence | Constitution Aware? | Status |
|-------|--------------|-------------|---------------------|--------|
| Watchdog | JSON (Rust types) | `.claude/process_registry.json` | ❌ NO | 🔴 Isolated |
| Orchestrator | JSON (Python dicts) | `execution_plan.json` | ⚠️ PARTIAL | 🟡 Metadata exists but unused |
| Wave Executor | In-memory Python | None (reads execution_plan.json) | ❌ NO | 🔴 Gap |
| Memory Bank | Markdown | `memory-bank/shared/.constitution.md` | ✅ YES | 🟢 Source of truth |

**Finding**: State layers can coexist (different files), but they **don't communicate**. Watchdog is completely isolated from constitution enforcement.

---

## 2. Data Flow Architecture Analysis

### 2.1 Expected Flow (per SPECKIT docs)

```
[Constitution File] (.constitution.md)
         ↓
[SpecKit Tasks] (tasks.md with constitution metadata)
         ↓ INTEGRATION POINT 1
[Orchestrator] (parses metadata → execution_plan.json)
         ↓ INTEGRATION POINT 2
[Wave Executor] (loads constitution + plan → passes to agents)
         ↓ INTEGRATION POINT 3
[Task Watchdog] (monitors execution WITH constitution context)
         ↓ INTEGRATION POINT 4
[Checkpoint Validator] (validates against constitution)
         ↓
[Git Checkpoint] (constitution-compliant commit)
```

### 2.2 Actual Flow (as-built)

```
[Constitution File] (.constitution.md)
         ↓
[SpecKit Tasks] (tasks.md with constitution metadata)
         ↓ ❌ INTEGRATION POINT 1: BROKEN
[Orchestrator] (parses tasks BUT IGNORES constitution metadata)
         ↓ execution_plan.json: NO constitution_rules field
         ↓ ❌ INTEGRATION POINT 2: BROKEN
[Wave Executor] (loads execution plan WITHOUT constitution)
         ↓ Spawns agents WITHOUT constitution context
         ↓ ❌ INTEGRATION POINT 3: MISSING
[Task Watchdog] (monitors PIDs/containers ONLY - no constitution awareness)
         ↓ process_registry.json: NO constitution fields
         ↓ ❌ INTEGRATION POINT 4: MISSING
[Checkpoint Protocol] (verifies tasks.md completion - NO constitution validation)
         ↓
[Git Checkpoint] (commits without constitution compliance check)
```

### 2.3 Constitution Metadata Loss Points

**LOSS POINT 1: Orchestrator** (`cli/orchestrator.py`)
```python
# Current implementation (lines 62-68):
task = Task(
    id=f"T{task_id:03d}",
    description=description,
    file_locks=file_locks,
    dependencies=dependencies,
    completed=completed
)
# ❌ NO FIELD: constitution_rules
# ❌ NO PARSING: Extract metadata from task description
```

**Expected** (from SPECKIT_DEVKID_INTEGRATION_GUARANTEE.md):
```python
task = Task(
    id=f"T{task_id:03d}",
    description=description,
    file_locks=file_locks,
    dependencies=dependencies,
    completed=completed,
    constitution_rules=extract_metadata(description, "Constitution")  # ← MISSING
)
```

**LOSS POINT 2: Execution Plan Schema** (`execution_plan.json`)
```json
// Current schema (lines 170-177 in orchestrator.py):
{
  "task_id": t.id,
  "agent_role": "Developer",
  "instruction": t.description,
  "file_locks": t.file_locks,
  "completion_handshake": "...",
  "dependencies": list(dependency_graph[t.id])
  // ❌ MISSING: "constitution_rules": ["Use Pydantic", "Type hints required"]
}
```

**LOSS POINT 3: Wave Executor** (`cli/wave_executor.py`)
```python
# Current implementation (lines 103-129):
def execute_wave(self, wave: Dict) -> None:
    for task in tasks:
        print(f"      🤖 Agent {task['agent_role']}: {task['task_id']}")
        # ❌ NO CONSTITUTION LOADING
        # ❌ NO AGENT CONTEXT INJECTION
```

**Expected**:
```python
def execute_wave(self, wave: Dict) -> None:
    constitution = Constitution("memory-bank/shared/.constitution.md")  # ← MISSING

    for task in tasks:
        agent_context = {
            "task": task,
            "constitution_rules": constitution.get_rules_for_task(task),  # ← MISSING
            "validation": constitution.get_validators()  # ← MISSING
        }
        spawn_agent(task['agent_role'], agent_context)  # ← MISSING
```

**LOSS POINT 4: Watchdog** (`rust-watchdog/src/types.rs`)
```rust
// Current TaskInfo struct (lines 69-84):
pub struct TaskInfo {
    pub mode: ExecutionMode,
    pub command: String,
    pub status: TaskStatus,
    pub started_at: DateTime<Utc>,
    pub completed_at: Option<DateTime<Utc>>,
    pub native: Option<NativeTask>,
    pub docker: Option<DockerTask>,
    // ❌ MISSING: pub constitution_rules: Option<Vec<String>>,
}
```

**LOSS POINT 5: Checkpoint Validation** (`cli/wave_executor.py`)
```python
# Current implementation (lines 51-76):
def execute_checkpoint(self, wave_id: int, checkpoint: Dict) -> None:
    # Step 1: Verify tasks.md completion ✅
    verified = self.verify_wave_completion(wave_id, tasks)

    # Step 2: Update progress.md ✅
    self._update_progress(wave_id, tasks)

    # Step 3: Git checkpoint ✅
    self._git_checkpoint(wave_id)

    # ❌ MISSING: Step 4: Constitution validation
    # ❌ MISSING: constitution.validate_wave_output(wave_id)
```

---

## 3. Process Management Architecture

### 3.1 Current Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ Wave Executor (Python subprocess)                          │
│ - Loads execution_plan.json                                │
│ - Executes waves sequentially                              │
│ - Creates checkpoints                                       │
│ - ❌ NO watchdog coordination                              │
└─────────────────────────────────────────────────────────────┘
                            ║
                            ║ (no communication)
                            ║
┌─────────────────────────────────────────────────────────────┐
│ Task Watchdog (Rust daemon)                                │
│ - Monitors PIDs/containers every 5 min                     │
│ - Tracks task timing                                       │
│ - Detects orphans                                          │
│ - ❌ NO executor integration                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Integration Issues

**Issue 1: No Process Coordination**
- Wave executor spawns agents (hypothetically) but doesn't register with watchdog
- Watchdog runs independently - doesn't know about wave execution state
- No shared state between executor and watchdog

**Issue 2: Task ID Mismatch**
- Orchestrator generates: `T001, T002, T003` (from tasks.md)
- Watchdog expects: `task_id` (string, user-provided)
- No automatic task registration when wave starts

**Issue 3: Race Conditions**
- Wave executor marks task complete in tasks.md
- Watchdog independently checks process_registry.json
- No atomic transaction - state can be inconsistent

### 3.3 Expected Coordination Protocol

```python
# cli/wave_executor.py (MISSING IMPLEMENTATION)

def execute_wave(self, wave: Dict) -> None:
    for task in wave['tasks']:
        # Step 1: Register with watchdog BEFORE execution
        watchdog_register(
            task_id=task['task_id'],
            command=task['instruction'],
            constitution_rules=task.get('constitution_rules', [])  # ← Pass metadata
        )

        # Step 2: Execute task (spawn agent)
        pid = spawn_agent(task)

        # Step 3: Update watchdog with PID
        watchdog_update_pid(task['task_id'], pid)

        # Step 4: Watchdog now monitors this task
```

**Current Reality**: None of this exists. Executor and watchdog are disconnected.

---

## 4. Schema Compatibility Analysis

### 4.1 Schema Comparison

**Rust Process Registry** (`process_registry.json`):
```json
{
  "tasks": {
    "TASK-001": {
      "mode": "native",
      "command": "python script.py",
      "status": "running",
      "started_at": "2026-01-10T10:00:00Z",
      "native": {
        "pid": 12345,
        "pgid": 12344,
        "start_time": "...",
        "env_tag": null
      }
    }
  }
}
```

**Python Execution Plan** (`execution_plan.json`):
```json
{
  "execution_plan": {
    "phase_id": "Phase 7",
    "waves": [{
      "wave_id": 1,
      "strategy": "PARALLEL_SWARM",
      "tasks": [{
        "task_id": "T001",
        "agent_role": "Developer",
        "instruction": "Create models",
        "file_locks": ["models.py"],
        "dependencies": []
      }]
    }]
  }
}
```

**Constitution Metadata** (EXPECTED in tasks.md):
```markdown
- [ ] TASK-001: Create data models (30 min)
  - **Constitution**: Use Pydantic BaseModel
  - **Files**: cli/models/observability.py (new)
```

### 4.2 Schema Gap Matrix

| Field | process_registry.json | execution_plan.json | tasks.md (expected) | Status |
|-------|----------------------|---------------------|---------------------|--------|
| task_id | ✅ String key | ✅ "task_id" field | ✅ TASK-001 | 🟢 Compatible |
| command | ✅ String | ❌ "instruction" (different name) | N/A | 🟡 Semantic mismatch |
| status | ✅ Enum | ❌ None (executor doesn't track) | ❌ Checkbox only | 🔴 Gap |
| started_at | ✅ DateTime | ❌ None | ❌ None | 🔴 Watchdog-only |
| constitution_rules | ❌ Missing | ❌ Missing | ✅ Expected | 🔴 Critical gap |
| file_locks | ❌ Missing | ✅ Array | N/A | 🟡 Executor-only |
| dependencies | ❌ Missing | ✅ Array | N/A | 🟡 Executor-only |
| agent_role | ❌ Missing | ✅ String | N/A | 🟡 Executor-only |

**Finding**: Schemas are **incompatible**. They track different aspects of task execution with no overlapping state synchronization.

### 4.3 Required Unified Schema

```json
// PROPOSED: Unified task state (both systems must support)
{
  "task_id": "T001",
  "instruction": "Create data models",
  "agent_role": "python-pro",

  // Execution metadata (from execution_plan.json)
  "file_locks": ["cli/models/observability.py"],
  "dependencies": [],
  "wave_id": 1,

  // Constitution enforcement (MISSING EVERYWHERE)
  "constitution_rules": ["Use Pydantic BaseModel", "Type hints required"],
  "constitution_validated": false,

  // Process tracking (from process_registry.json)
  "mode": "native",
  "status": "running",
  "started_at": "2026-01-10T10:00:00Z",
  "pid": 12345,

  // Completion tracking
  "completed_at": null,
  "completion_verification": {
    "tasks_md_marked": false,
    "constitution_compliant": false,
    "files_created": []
  }
}
```

**This schema doesn't exist anywhere in the system.**

---

## 5. Integration Point Gaps

### 5.1 CLI → Orchestrator → Executor Flow

```bash
# CLI command
dev-kid orchestrate "Phase 7"
    ↓ calls
python3 cli/orchestrator.py --tasks-file tasks.md --phase-id "Phase 7"
    ↓ reads
tasks.md (with constitution metadata)
    ↓ ❌ GAP: Metadata parsing missing
execution_plan.json (WITHOUT constitution_rules field)
    ↓ executor reads
python3 cli/wave_executor.py
    ↓ ❌ GAP: No constitution loading
    ↓ ❌ GAP: Agents don't receive constitution context
Spawns agents WITHOUT enforcement rules
```

### 5.2 Executor → Watchdog Integration

**Expected API** (from task_watchdog.py docstring):
```python
# dev-kid task-start T001 "Create models"
# → Watchdog registers task with timer

# dev-kid task-complete T001
# → Watchdog marks complete and stops timer
```

**Actual Usage** (in wave_executor.py):
```python
# ❌ NO CALLS TO WATCHDOG
# ❌ NO TASK REGISTRATION
# ❌ NO COMPLETION NOTIFICATION
```

**Missing Integration Code**:
```python
# cli/wave_executor.py (NEEDS TO BE ADDED)

import subprocess

def execute_wave(self, wave: Dict) -> None:
    for task in wave['tasks']:
        # Register task with watchdog
        subprocess.run([
            'dev-kid', 'task-start',
            task['task_id'],
            task['instruction']
        ])

        # Execute task...

        # After completion:
        subprocess.run(['dev-kid', 'task-complete', task['task_id']])
```

**Current Reality**: Zero integration. Wave executor is unaware of watchdog.

### 5.3 Watchdog → Executor Feedback Loop

**Expected**:
- Watchdog detects task hanging (>7 min guideline)
- Watchdog signals executor: "T001 is stalled"
- Executor responds: retries, escalates, or marks failed

**Actual**:
- Watchdog prints warning to stdout (lines 91-94 in task_watchdog.py)
- Executor never sees this warning
- No feedback mechanism exists

---

## 6. Critical Gaps Summary

### Gap 1: Constitution Metadata Parsing

**Location**: `cli/orchestrator.py`, lines 62-68
**Impact**: 🔴 CRITICAL - Constitution rules never enter the system
**Root Cause**: `Task` dataclass missing `constitution_rules` field
**Fix Required**:
1. Add `constitution_rules: List[str]` to Task dataclass
2. Implement `extract_metadata()` function to parse task description
3. Store in execution_plan.json task objects

### Gap 2: Constitution Enforcement in Executor

**Location**: `cli/wave_executor.py`, lines 103-129
**Impact**: 🔴 CRITICAL - Agents execute without constitution awareness
**Root Cause**: No Constitution class, no agent context injection
**Fix Required**:
1. Create `cli/constitution_parser.py` (mentioned in docs but doesn't exist)
2. Load constitution in `execute_wave()`
3. Pass constitution_rules to agent context

### Gap 3: Watchdog Integration

**Location**: `cli/wave_executor.py` (integration points missing)
**Impact**: 🟡 HIGH - Task monitoring disconnected from execution
**Root Cause**: No subprocess calls to watchdog CLI
**Fix Required**:
1. Call `dev-kid task-start` before executing task
2. Call `dev-kid task-complete` after task finishes
3. Handle watchdog warnings (need IPC mechanism)

### Gap 4: Checkpoint Constitution Validation

**Location**: `cli/wave_executor.py`, lines 51-76
**Impact**: 🔴 CRITICAL - Checkpoints don't enforce constitution
**Root Cause**: No validation step in checkpoint protocol
**Fix Required**:
1. Add `constitution.validate_wave_output(wave_id)` before git commit
2. Block checkpoint if violations found
3. Report violations to user

### Gap 5: Schema Synchronization

**Location**: `rust-watchdog/src/types.rs` + `cli/orchestrator.py`
**Impact**: 🟡 HIGH - State duplication without synchronization
**Root Cause**: Different languages, different schemas
**Fix Required**:
1. Add `constitution_rules` field to Rust TaskInfo struct
2. Implement JSON serialization compatibility layer
3. Create state sync mechanism (watchdog reads execution_plan.json)

### Gap 6: Process Coordination

**Location**: Architecture-level (no coordination protocol)
**Impact**: 🟡 HIGH - Race conditions, inconsistent state
**Root Cause**: Executor and watchdog run independently
**Fix Required**:
1. Define atomic state transitions
2. Implement file-based locking (or use SQLite with transactions)
3. Document coordination protocol

---

## 7. Architecture Recommendations

### 7.1 Immediate Fixes (Phase 1)

**Priority 1: Constitution Parser** (Blocks all other fixes)
```python
# cli/constitution_parser.py (NEW FILE)

from pathlib import Path
from typing import List, Dict
import re

class Constitution:
    def __init__(self, file_path: str = "memory-bank/shared/.constitution.md"):
        self.file_path = Path(file_path)
        self.rules = self._parse()

    def _parse(self) -> Dict[str, List[str]]:
        """Parse constitution into structured rules"""
        if not self.file_path.exists():
            return {}

        content = self.file_path.read_text()
        sections = {}
        current_section = None

        for line in content.split('\n'):
            if line.startswith('## '):
                current_section = line[3:].strip()
                sections[current_section] = []
            elif line.startswith('- ') and current_section:
                sections[current_section].append(line[2:].strip())

        return sections

    def get_rules_for_task(self, task: Dict) -> List[str]:
        """Extract constitution rules relevant to a task"""
        # Match rules from task's constitution_rules metadata
        task_rules = task.get('constitution_rules', [])

        # Also check task instruction for keywords
        instruction = task.get('instruction', '').lower()
        relevant_rules = []

        for section, rules in self.rules.items():
            for rule in rules:
                # If task mentions this rule OR it's in task metadata
                if any(keyword in instruction for keyword in rule.lower().split()) or rule in task_rules:
                    relevant_rules.append(rule)

        return relevant_rules

    def validate_output(self, files: List[str]) -> List[Dict]:
        """Validate files against constitution rules"""
        # Placeholder - real implementation would check:
        # - Type hints present (if required)
        # - Docstrings present (if required)
        # - No forbidden patterns (raw SQL, etc.)
        return []
```

**Priority 2: Orchestrator Integration**
```python
# cli/orchestrator.py (MODIFY lines 62-68)

def _extract_constitution_metadata(self, description: str) -> List[str]:
    """Extract constitution rules from task description"""
    import re

    # Match pattern: **Constitution**: Rule1, Rule2
    match = re.search(r'\*\*Constitution\*\*:\s*(.+?)(?:\n|$)', description)
    if match:
        rules_text = match.group(1)
        return [r.strip() for r in rules_text.split(',')]
    return []

@dataclass
class Task:
    id: str
    description: str
    agent_role: str = "Developer"
    file_locks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    constitution_rules: List[str] = field(default_factory=list)  # ← ADD THIS
    completed: bool = False

def parse_tasks(self) -> None:
    # ... existing code ...

    task = Task(
        id=f"T{task_id:03d}",
        description=description,
        file_locks=file_locks,
        dependencies=dependencies,
        constitution_rules=self._extract_constitution_metadata(description),  # ← ADD THIS
        completed=completed
    )
```

**Priority 3: Executor Constitution Loading**
```python
# cli/wave_executor.py (MODIFY execute_wave method)

from cli.constitution_parser import Constitution

def execute_wave(self, wave: Dict) -> None:
    # Load constitution
    constitution = Constitution()  # ← ADD THIS

    wave_id = wave['wave_id']
    strategy = wave['strategy']
    tasks = wave['tasks']

    print(f"\n🌊 Executing Wave {wave_id} ({strategy})...")

    for task in tasks:
        # Get constitution rules for this task
        rules = constitution.get_rules_for_task(task)  # ← ADD THIS

        if rules:
            print(f"      📜 Constitution rules:")
            for rule in rules:
                print(f"         - {rule}")

        # Pass to agent (in real implementation)
        agent_context = {
            "task": task,
            "constitution_rules": rules  # ← ADD THIS
        }
        # spawn_agent(task['agent_role'], agent_context)
```

### 7.2 Medium-Term Fixes (Phase 2)

**Fix 1: Watchdog Integration**
```python
# cli/wave_executor.py (ADD watchdog calls)

import subprocess

def execute_wave(self, wave: Dict) -> None:
    for task in wave['tasks']:
        # Start watchdog timer
        subprocess.run(['dev-kid', 'task-start', task['task_id'], task['instruction']])

        # Execute task...
        # (agent spawning logic)

        # Mark complete (agents would do this, but for now manual)
        # User must run: dev-kid task-complete TASK-001
```

**Fix 2: Checkpoint Validation**
```python
# cli/wave_executor.py (MODIFY execute_checkpoint)

def execute_checkpoint(self, wave_id: int, checkpoint: Dict) -> None:
    print(f"\n🔍 Checkpoint after Wave {wave_id}...")

    # Step 1: Verify tasks.md (existing)
    tasks = self.plan['execution_plan']['waves'][wave_id - 1]['tasks']
    verified = self.verify_wave_completion(wave_id, tasks)
    if not verified:
        sys.exit(1)

    # Step 2: Constitution validation (NEW)
    constitution = Constitution()

    # Get files modified in this wave
    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD'],
                          capture_output=True, text=True)
    modified_files = result.stdout.strip().split('\n')

    # Validate against constitution
    violations = constitution.validate_output(modified_files)

    if violations:
        print(f"\n❌ Constitution Violations - Checkpoint BLOCKED:")
        for v in violations:
            print(f"   Rule: {v['rule']}")
            print(f"   File: {v['file']}:{v['line']}")
            print(f"   Issue: {v['message']}")
        sys.exit(1)

    print("   ✅ Constitution compliance verified")

    # Step 3: Update progress (existing)
    self._update_progress(wave_id, tasks)

    # Step 4: Git checkpoint (existing)
    self._git_checkpoint(wave_id)
```

### 7.3 Long-Term Architecture (Phase 3)

**Unified State Management**

```
┌─────────────────────────────────────────────────────────────┐
│ SQLite Database: dev-kid.db                                 │
├─────────────────────────────────────────────────────────────┤
│ Tables:                                                     │
│  - tasks (id, instruction, status, constitution_rules)      │
│  - processes (task_id, pid, started_at, status)            │
│  - waves (wave_id, phase_id, strategy, status)             │
│  - checkpoints (wave_id, timestamp, constitution_valid)     │
└─────────────────────────────────────────────────────────────┘
          ↑                    ↑                    ↑
          │                    │                    │
    Orchestrator          Executor              Watchdog
    (writes tasks)    (updates status)    (monitors processes)
```

**Benefits**:
- Atomic transactions (no race conditions)
- Single source of truth
- Both Rust and Python can query (SQLite is universal)
- Constitution rules stored in database alongside tasks

**Migration Path**:
1. Create `cli/database.py` with SQLite schema
2. Update orchestrator to write to DB instead of JSON
3. Update executor to read from DB
4. Add Rust SQLite bindings to watchdog
5. Deprecate `process_registry.json` and `execution_plan.json`

---

## 8. As-Built Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: Constitution Source (SpecKit)                         │
├─────────────────────────────────────────────────────────────────┤
│ memory-bank/shared/.constitution.md                            │
│ - Technology standards                                         │
│ - Architecture principles                                      │
│ - Testing standards                                            │
│ Status: ✅ File exists, 🔴 NOT CONSUMED by dev-kid             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ❌ NO INTEGRATION
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: Task Definition (SpecKit)                             │
├─────────────────────────────────────────────────────────────────┤
│ tasks.md                                                        │
│ - [ ] TASK-001: Create models                                  │
│   - **Constitution**: Use Pydantic                             │
│   - **Files**: models.py                                       │
│ Status: ✅ File format correct, 🔴 Metadata NOT PARSED         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    dev-kid orchestrate
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: Orchestration (dev-kid)                               │
├─────────────────────────────────────────────────────────────────┤
│ cli/orchestrator.py                                            │
│ - Parses tasks.md                                              │
│ - Extracts: file_locks, dependencies                           │
│ - ❌ IGNORES: constitution metadata                            │
│ - Outputs: execution_plan.json                                 │
│   {                                                            │
│     "tasks": [{"task_id": "T001", "instruction": "..."}]       │
│     ❌ "constitution_rules": MISSING                           │
│   }                                                            │
│ Status: 🔴 Constitution metadata LOST here                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                        dev-kid execute
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: Execution (dev-kid)                                   │
├─────────────────────────────────────────────────────────────────┤
│ cli/wave_executor.py                                           │
│ - Loads execution_plan.json                                    │
│ - Iterates through waves                                       │
│ - ❌ NO CONSTITUTION LOADING                                   │
│ - ❌ NO AGENT CONTEXT INJECTION                                │
│ - Prints task info to stdout                                   │
│ Status: 🔴 Agents execute WITHOUT constitution                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    (hypothetical agent spawning)
                              ↓
                    ❌ NO WATCHDOG REGISTRATION
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 5: Monitoring (task-watchdog) - ISOLATED SILO            │
├─────────────────────────────────────────────────────────────────┤
│ rust-watchdog/                                                 │
│ - Runs as daemon (dev-kid watchdog-start)                      │
│ - Monitors: PIDs, containers                                   │
│ - Stores: .claude/process_registry.json                        │
│   {                                                            │
│     "tasks": {                                                 │
│       "TASK-001": {"pid": 123, "status": "running"}            │
│       ❌ "constitution_rules": MISSING                         │
│     }                                                          │
│   }                                                            │
│ - ❌ NO COMMUNICATION with wave_executor                       │
│ - ❌ NO KNOWLEDGE of execution_plan.json                       │
│ Status: 🟡 Works independently, 🔴 NOT INTEGRATED              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    (manual task-complete)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 6: Checkpoint (dev-kid)                                  │
├─────────────────────────────────────────────────────────────────┤
│ cli/wave_executor.py::execute_checkpoint()                     │
│ - Step 1: Verify tasks.md completion ✅                        │
│ - Step 2: Update progress.md ✅                                │
│ - Step 3: Git commit ✅                                        │
│ - ❌ Step 4: Constitution validation MISSING                   │
│ Status: 🔴 Checkpoints DON'T enforce constitution              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                         git commit
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ RESULT: Constitution-UNAWARE Checkpoint                        │
│ - Code may violate constitution                                │
│ - No validation occurred                                       │
│ - Speckit integration DEFEATED                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Required Architecture (Target State)

```
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 1: Constitution Source                                   │
├─────────────────────────────────────────────────────────────────┤
│ memory-bank/shared/.constitution.md                            │
│ ✅ Parsed by ConstitutionParser                                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ✅ Constitution loaded into memory
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 2: Task Definition                                       │
├─────────────────────────────────────────────────────────────────┤
│ tasks.md (with constitution metadata)                          │
│ ✅ Metadata extracted by orchestrator                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    dev-kid orchestrate
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 3: Orchestration                                         │
├─────────────────────────────────────────────────────────────────┤
│ cli/orchestrator.py                                            │
│ - Parses: file_locks, dependencies, constitution_rules         │
│ - Outputs: execution_plan.json WITH constitution metadata      │
│   {                                                            │
│     "tasks": [{                                                │
│       "task_id": "T001",                                       │
│       "constitution_rules": ["Use Pydantic", "Type hints"]     │
│     }]                                                         │
│   }                                                            │
│ ✅ Constitution metadata PRESERVED                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                        dev-kid execute
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 4: Execution                                             │
├─────────────────────────────────────────────────────────────────┤
│ cli/wave_executor.py                                           │
│ - Loads: execution_plan.json                                   │
│ - Loads: Constitution from .constitution.md                    │
│ - For each task:                                               │
│   1. Extract constitution_rules from task                      │
│   2. Build agent_context with rules                            │
│   3. Spawn agent WITH constitution awareness                   │
│   4. ✅ Register with watchdog                                 │
│ ✅ Agents execute WITH constitution context                    │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    subprocess: dev-kid task-start T001
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 5: Monitoring (INTEGRATED)                               │
├─────────────────────────────────────────────────────────────────┤
│ rust-watchdog/                                                 │
│ - Receives: task_start(T001, constitution_rules)               │
│ - Stores: process_registry.json WITH constitution metadata     │
│   {                                                            │
│     "tasks": {                                                 │
│       "T001": {                                                │
│         "pid": 123,                                            │
│         "constitution_rules": ["Use Pydantic"],                │
│         "status": "running"                                    │
│       }                                                        │
│     }                                                          │
│   }                                                            │
│ - ✅ Monitors task with constitution context                   │
│ - ✅ Can validate output when task completes                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    agent completes task
                              ↓
                    subprocess: dev-kid task-complete T001
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ LAYER 6: Checkpoint (WITH VALIDATION)                          │
├─────────────────────────────────────────────────────────────────┤
│ cli/wave_executor.py::execute_checkpoint()                     │
│ - Step 1: Verify tasks.md completion ✅                        │
│ - Step 2: ✅ Load constitution                                 │
│ - Step 3: ✅ Validate modified files against rules             │
│ - Step 4: ✅ BLOCK checkpoint if violations found              │
│ - Step 5: Update progress.md ✅                                │
│ - Step 6: Git commit (only if constitution compliant) ✅       │
│ ✅ Constitution enforcement GUARANTEED                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                         git commit
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ RESULT: Constitution-COMPLIANT Checkpoint                      │
│ - All rules enforced                                           │
│ - Validation passed                                            │
│ - Speckit integration WORKING                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Implementation Roadmap

### Phase 1: Constitution Parser (Week 1)
**Deliverables**:
- [ ] `cli/constitution_parser.py` (new file)
- [ ] Unit tests for parsing
- [ ] Integration with config_manager.py

### Phase 2: Orchestrator Integration (Week 1)
**Deliverables**:
- [ ] Add `constitution_rules` field to Task dataclass
- [ ] Implement `_extract_constitution_metadata()` method
- [ ] Update `generate_execution_plan()` to include rules
- [ ] Update execution_plan.json schema documentation

### Phase 3: Executor Integration (Week 2)
**Deliverables**:
- [ ] Load Constitution in `execute_wave()`
- [ ] Pass constitution_rules to agent context
- [ ] Implement `get_rules_for_task()` logic
- [ ] Update wave execution logging to show rules

### Phase 4: Checkpoint Validation (Week 2)
**Deliverables**:
- [ ] Implement `constitution.validate_output()` method
- [ ] Add validation step to `execute_checkpoint()`
- [ ] Create violation reporting format
- [ ] Add violation examples to documentation

### Phase 5: Watchdog Integration (Week 3)
**Deliverables**:
- [ ] Add subprocess calls to wave_executor
- [ ] Update Rust TaskInfo struct with constitution_rules field
- [ ] Implement constitution_rules serialization in Rust
- [ ] Add watchdog registration before task execution
- [ ] Add watchdog notification after task completion

### Phase 6: Testing & Documentation (Week 4)
**Deliverables**:
- [ ] Integration test: Constitution → Tasks → Execution → Validation
- [ ] Integration test: Constitution violation blocks checkpoint
- [ ] Update DEVELOPER_TRAINING_GUIDE.md
- [ ] Create CONSTITUTION_ENFORCEMENT.md guide
- [ ] Video walkthrough of constitution workflow

---

## 11. Risk Assessment

### High-Risk Areas

**Risk 1: Breaking Changes**
- Modifying orchestrator.py schema will break existing execution_plan.json files
- Mitigation: Add schema versioning, backward compatibility layer

**Risk 2: Rust-Python Integration**
- Adding constitution_rules to Rust requires careful JSON serialization
- Mitigation: Use serde with optional fields, test thoroughly

**Risk 3: Performance Impact**
- Constitution validation on every checkpoint could slow down workflow
- Mitigation: Implement caching, only validate changed files

**Risk 4: Adoption Friction**
- Users need to update tasks.md format to include constitution metadata
- Mitigation: Make constitution_rules optional, provide auto-migration script

### Medium-Risk Areas

**Risk 5: State Synchronization**
- Watchdog and executor could have inconsistent state
- Mitigation: Use file locking, atomic writes, document coordination protocol

**Risk 6: Constitution Parsing Edge Cases**
- Complex markdown formats might break parser
- Mitigation: Strict schema validation, clear error messages

---

## 12. Conclusion

**Architecture Alignment Verdict**: 🔴 **CRITICAL MISALIGNMENT**

The task-watchdog system, while well-architected internally, is fundamentally **disconnected from the constitution enforcement flow** that Speckit integration requires. Constitution metadata enters the system via tasks.md but is lost at the orchestration layer, making the entire Speckit workflow ineffective.

**Key Findings**:
1. **Constitution metadata is lost** at `cli/orchestrator.py` (never parsed)
2. **Wave executor is constitution-blind** (doesn't load or enforce rules)
3. **Watchdog is isolated** (no integration with executor, no constitution awareness)
4. **Checkpoints don't validate** (no constitution compliance check)
5. **Schemas are incompatible** (Rust and Python track different state)

**Required Investment**:
- **Immediate**: Constitution parser + orchestrator integration (1-2 weeks)
- **Critical**: Executor enforcement + checkpoint validation (1-2 weeks)
- **Important**: Watchdog integration (1 week)
- **Long-term**: Unified state management with SQLite (2-3 weeks)

**Total Effort**: 5-8 weeks for complete integration

**Recommendation**: Prioritize Phase 1-4 (constitution enforcement) immediately. Task-watchdog can continue working independently in the short term, but constitution integration is **blocking Speckit workflow adoption**.

---

**Document Status**: ✅ COMPLETE
**Review Level**: Architecture Gap Analysis (Detailed)
**Next Step**: Review with team, prioritize implementation phases

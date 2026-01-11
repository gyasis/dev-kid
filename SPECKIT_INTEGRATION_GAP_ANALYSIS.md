# SpecKit + Dev-Kid Integration Gap Analysis

**Date**: 2026-01-10
**Status**: CRITICAL GAPS IDENTIFIED
**Reviewer**: Code Review Agent

---

## Executive Summary

The integration between SpecKit and Dev-Kid for constitution enforcement is **PARTIALLY IMPLEMENTED** with **CRITICAL GAPS** in the data flow pipeline. While foundation components exist (constitution parser, templates), the integration points that would make constitution rules flow through to task execution and validation are **MISSING**.

**Overall Status**: ❌ 40% Complete (4 of 10 integration points functional)

---

## Integration Point Analysis

### 1. Constitution File Path Consistency ✅ VERIFIED

**Expected**: Both SpecKit and dev-kid use `memory-bank/shared/.constitution.md`

**Actual Status**: ✅ CORRECT

**Evidence**:
- `cli/constitution_manager.py:257` - Hardcoded path matches spec
```python
self.constitution_path = self.project_path / "memory-bank" / "shared" / ".constitution.md"
```

- Constitution parser initialized with correct default:
```python
def __init__(self, file_path: str = "memory-bank/shared/.constitution.md"):
```

**Verdict**: PASSES - No issues

---

### 2. Task Registry Schema - Constitution Rules Field ❌ MISSING

**Expected**: `TaskInfo` struct in `rust-watchdog/src/types.rs` should have `constitution_rules` field

**Actual Status**: ❌ FIELD DOES NOT EXIST

**Evidence**:
```rust
// rust-watchdog/src/types.rs:69-84
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskInfo {
    pub mode: ExecutionMode,
    pub command: String,
    pub status: TaskStatus,
    pub started_at: DateTime<Utc>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub completed_at: Option<DateTime<Utc>>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub native: Option<NativeTask>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub docker: Option<DockerTask>,
    // ❌ NO constitution_rules field!
}
```

**Required Schema**:
```rust
pub struct TaskInfo {
    // ... existing fields ...

    #[serde(skip_serializing_if = "Option::is_none")]
    pub constitution_rules: Option<Vec<String>>,  // ← MISSING
}
```

**Impact**: HIGH - Watchdog cannot track which constitution rules apply to tasks

**Files Affected**:
- `rust-watchdog/src/types.rs` (TaskInfo struct)

---

### 3. Wave Executor Integration ❌ NOT IMPLEMENTED

**Expected**: `cli/wave_executor.py` should:
1. Load constitution from file
2. Pass constitution rules to task-watchdog when registering tasks
3. Validate files against constitution at checkpoints

**Actual Status**: ❌ NONE OF THIS EXISTS

#### 3a. Constitution Loading ❌ MISSING

**Evidence**: `cli/wave_executor.py` has NO constitution imports or loading

```python
# wave_executor.py:1-12
#!/usr/bin/env python3
"""
Wave Executor - Executes waves from execution_plan.json with checkpoints
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List
import time
# ❌ NO constitution imports!
```

**Required Code**:
```python
from constitution_manager import Constitution, ConstitutionViolation

class WaveExecutor:
    def __init__(self, plan_file: str = "execution_plan.json"):
        self.plan_file = Path(plan_file)
        self.plan = None
        self.tasks_file = Path("tasks.md")
        self.constitution = Constitution()  # ← MISSING
```

#### 3b. Task Registration with Watchdog ❌ MISSING

**Evidence**: No watchdog integration in `wave_executor.py`

**Expected Flow**:
```python
def execute_wave(self, wave: Dict) -> None:
    """Execute a single wave"""
    # ❌ MISSING: Register tasks with watchdog
    for task in wave['tasks']:
        constitution_rules = self.constitution.get_rules_for_task(task['instruction'])

        # Register with watchdog
        subprocess.run([
            'task-watchdog', 'register',
            '--task-id', task['task_id'],
            '--constitution-rules', json.dumps(constitution_rules)
        ])
```

**Current Code**: Only prints task execution, no watchdog calls

```python
# wave_executor.py:103-129
def execute_wave(self, wave: Dict) -> None:
    """Execute a single wave"""
    wave_id = wave['wave_id']
    strategy = wave['strategy']
    tasks = wave['tasks']

    print(f"\n🌊 Executing Wave {wave_id} ({strategy})...")
    # ... just prints, no watchdog registration
```

#### 3c. Checkpoint Constitution Validation ❌ MISSING

**Expected**: `execute_checkpoint()` should validate files against constitution

**Required Implementation**:
```python
def execute_checkpoint(self, wave_id: int, checkpoint: Dict) -> None:
    """Execute checkpoint between waves"""
    print(f"\n🔍 Checkpoint after Wave {wave_id}...")

    # Step 1: Verify tasks complete (EXISTS)
    tasks = self.plan['execution_plan']['waves'][wave_id - 1]['tasks']
    verified = self.verify_wave_completion(wave_id, tasks)

    # Step 2: ❌ MISSING - Constitution validation
    violations = self._validate_constitution(wave_id, tasks)
    if violations:
        print("❌ Constitution Violations - Checkpoint BLOCKED:")
        for v in violations:
            print(f"   Rule: {v.rule}")
            print(f"   File: {v.file}:{v.line}")
            print(f"   Issue: {v.message}")
        sys.exit(1)

    # Step 3: Proceed with git checkpoint
    self._git_checkpoint(wave_id)
```

**Current Code**: Only verifies task completion, NO constitution validation

```python
# wave_executor.py:51-75
def execute_checkpoint(self, wave_id: int, checkpoint: Dict) -> None:
    """Execute checkpoint between waves"""
    print(f"\n🔍 Checkpoint after Wave {wave_id}...")

    # Step 1: memory-bank-keeper verifies tasks.md
    print("   Step 1: memory-bank-keeper validates tasks.md...")
    tasks = self.plan['execution_plan']['waves'][wave_id - 1]['tasks']
    verified = self.verify_wave_completion(wave_id, tasks)

    if not verified:
        print(f"\n❌ Checkpoint failed! Wave {wave_id} tasks not complete.")
        print("   Halting execution.")
        sys.exit(1)

    print("   ✅ All tasks verified complete")

    # Step 2: Memory bank keeper updates progress.md
    print("   Step 2: memory-bank-keeper updates progress.md...")
    self._update_progress(wave_id, tasks)

    # Step 3: Git agent commits
    print("   Step 3: git-version-manager creates checkpoint...")
    self._git_checkpoint(wave_id)
    # ❌ NO constitution validation!
```

**Impact**: CRITICAL - Constitution rules never enforced during execution

**Files Affected**:
- `cli/wave_executor.py` (entire file needs constitution integration)

---

### 4. Orchestrator Constitution Metadata Extraction ❌ NOT IMPLEMENTED

**Expected**: `cli/orchestrator.py` should parse constitution metadata from tasks.md

**Task Format Expected**:
```markdown
- [ ] TASK-001: Create data models (30 min)
  - **Constitution**: Use Pydantic BaseModel
  - **Files**: cli/models/observability.py (new)
```

**Actual Status**: ❌ NO CONSTITUTION PARSING

**Evidence**: Orchestrator only extracts file locks and dependencies

```python
# cli/orchestrator.py:41-76
def parse_tasks(self) -> None:
    """Parse tasks.md into Task objects"""
    # ...
    for line in lines:
        if line.startswith('- [ ]') or line.startswith('- [x]'):
            completed = '[x]' in line
            description = line.split(']', 1)[1].strip()

            # Extract file references from description
            file_locks = self._extract_file_references(description)

            # Extract dependencies (if "after T123" or "depends on T456")
            dependencies = self._extract_dependencies(description)

            # ❌ NO constitution metadata extraction!
```

**Required Implementation**:
```python
def parse_tasks(self) -> None:
    """Parse tasks.md into Task objects"""
    if not self.tasks_file.exists():
        print(f"❌ Error: {self.tasks_file} not found")
        sys.exit(1)

    content = self.tasks_file.read_text()
    lines = content.split('\n')

    task_id = 1
    current_task = None

    for line in lines:
        if line.startswith('- [ ]') or line.startswith('- [x]'):
            # Create task object
            completed = '[x]' in line
            description = line.split(']', 1)[1].strip()

            file_locks = self._extract_file_references(description)
            dependencies = self._extract_dependencies(description)

            current_task = Task(
                id=f"T{task_id:03d}",
                description=description,
                file_locks=file_locks,
                dependencies=dependencies,
                completed=completed,
                constitution_rules=[]  # Will be populated from metadata
            )
            self.tasks.append(current_task)
            task_id += 1

        elif line.strip().startswith('- **Constitution**:') and current_task:
            # Extract constitution rule
            rule = line.split(':', 1)[1].strip()
            current_task.constitution_rules.append(rule)
```

**Task Schema Also Needs Update**:
```python
# cli/orchestrator.py:13-21
@dataclass
class Task:
    """Represents a single task"""
    id: str
    description: str
    agent_role: str = "Developer"
    file_locks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    completed: bool = False
    constitution_rules: List[str] = field(default_factory=list)  # ← MISSING
```

**Impact**: CRITICAL - Constitution rules never flow from tasks.md to execution plan

**Files Affected**:
- `cli/orchestrator.py` (Task dataclass, parse_tasks method)

---

### 5. Execution Plan JSON Schema ❌ INCOMPLETE

**Expected**: `execution_plan.json` should include constitution_rules in task objects

**Required Schema**:
```json
{
  "execution_plan": {
    "phase_id": "implementation",
    "waves": [
      {
        "wave_id": 1,
        "tasks": [
          {
            "task_id": "T001",
            "instruction": "Create models",
            "constitution_rules": [
              "Use Pydantic BaseModel",
              "Type hints required"
            ]
          }
        ]
      }
    ]
  }
}
```

**Actual Status**: ❌ NO constitution_rules FIELD

**Evidence**: Orchestrator generates execution plan without constitution

```python
# cli/orchestrator.py:185-203
def generate_execution_plan(self, phase_id: str = "default") -> Dict:
    """Generate complete execution plan in JSON schema format"""
    return {
        "execution_plan": {
            "phase_id": phase_id,
            "waves": [{
                "wave_id": wave.wave_id,
                "strategy": wave.strategy,
                "rationale": wave.rationale,
                "tasks": wave.tasks,  # ← Does not include constitution_rules
                "checkpoint_after": {
                    "enabled": wave.checkpoint_enabled,
                    "verification_criteria": f"Verify all Wave {wave.wave_id} tasks are marked [x] in tasks.md",
                    "git_agent": "git-version-manager",
                    "memory_bank_agent": "memory-bank-keeper"
                }
            } for wave in self.waves]
        }
    }
```

**Required Fix**:
```python
def create_waves(self) -> None:
    """Group tasks into execution waves"""
    # ...existing wave creation logic...

    # Create wave
    wave = Wave(
        wave_id=wave_id,
        strategy=strategy,
        tasks=[{
            "task_id": t.id,
            "agent_role": "Developer",
            "instruction": t.description,
            "file_locks": t.file_locks,
            "constitution_rules": t.constitution_rules,  # ← ADD THIS
            "completion_handshake": f"Upon success, update tasks.md line containing '{t.description}' to [x]",
            "dependencies": list(dependency_graph[t.id])
        } for t in wave_tasks],
        rationale=f"Wave {wave_id}: {len(wave_tasks)} independent task(s) with no file conflicts",
        checkpoint_enabled=True
    )
```

**Impact**: HIGH - Execution plan lacks constitution context

**Files Affected**:
- `cli/orchestrator.py` (create_waves method)

---

## Data Flow Verification

### Expected Data Flow (per SPECKIT_DEVKID_INTEGRATION_GUARANTEE.md)

```
[Constitution File: memory-bank/shared/.constitution.md]
  ↓
  ✅ WORKING: Constitution parser can read this file
  ↓
[Speckit: /speckit.tasks creates tasks.md with Constitution metadata]
  ↓
  ❌ BROKEN: Orchestrator does NOT parse Constitution metadata
  ↓
[execution_plan.json]
  ↓
  ❌ BROKEN: No constitution_rules field in JSON
  ↓
[Wave Executor]
  ↓
  ❌ BROKEN: Does NOT load constitution
  ❌ BROKEN: Does NOT pass rules to agents
  ❌ BROKEN: Does NOT validate at checkpoints
  ↓
[task-watchdog]
  ↓
  ❌ BROKEN: Cannot store constitution_rules (field missing from schema)
  ↓
[Checkpoint Validation]
  ❌ BROKEN: No constitution validation implemented
```

### Actual Data Flow (Current Implementation)

```
[Constitution File: memory-bank/shared/.constitution.md]
  ↓
  ✅ Constitution.py can parse this (but nothing uses it)
  ↓
[tasks.md]
  ↓
  ✅ Orchestrator parses task descriptions
  ❌ Orchestrator IGNORES constitution metadata
  ↓
[execution_plan.json]
  ❌ NO constitution data
  ↓
[Wave Executor]
  ✅ Executes waves
  ❌ NO constitution awareness
  ↓
[Checkpoint]
  ✅ Verifies tasks complete
  ❌ NO constitution validation
  ↓
[Git Commit]
  ✅ Creates checkpoint
```

**Verdict**: Data flow is **BROKEN** at 3 critical points:
1. Orchestrator does not extract constitution metadata
2. Wave executor does not load or use constitution
3. Checkpoint does not validate constitution compliance

---

## File-by-File Breakdown

### Files That SHOULD Exist (per spec) vs ACTUALLY Exist

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| Constitution Parser | `cli/constitution_manager.py` | ✅ EXISTS | Has Constitution class with parse/validate methods |
| Orchestrator | `cli/orchestrator.py` | ⚠️ INCOMPLETE | Missing constitution metadata parsing |
| Wave Executor | `cli/wave_executor.py` | ⚠️ INCOMPLETE | Missing constitution loading and validation |
| Task Schema | `rust-watchdog/src/types.rs` | ⚠️ INCOMPLETE | Missing constitution_rules field |
| Watchdog Registration | `rust-watchdog/src/main.rs` | ❌ MISSING | No register command for tasks with constitution |
| Constitution Templates | `templates/constitution_templates/*.md` | ✅ EXISTS | 5 templates available |

---

## Implementation Requirements (from spec) vs Reality

### 1. Constitution Parser ✅ IMPLEMENTED

**Required**:
```python
class Constitution:
    def __init__(self, file_path: str):
        self.rules = self._parse(file_path)

    def get_rules_for_task(self, task) -> List[str]:
        """Extract rules relevant to this task"""
        pass

    def validate_output(self, files: List[str]) -> List[Violation]:
        """Validate files against constitution"""
        pass
```

**Actual**: EXISTS in `cli/constitution_manager.py:32-240`
- `Constitution.__init__()` - ✅ Implemented
- `Constitution.get_rules_for_task()` - ✅ Implemented (line 135)
- `Constitution.validate_file()` - ✅ Implemented (line 172)

**Status**: ✅ COMPLETE

---

### 2. Orchestrator Integration ❌ NOT IMPLEMENTED

**Required**:
```python
def create_execution_plan(tasks_md: str):
    constitution = Constitution("memory-bank/shared/.constitution.md")

    for task in parse_tasks(tasks_md):
        # Extract constitution metadata from task
        task.constitution_rules = extract_metadata(task, "Constitution")

        # Store in execution plan
        plan.add_task(task)
```

**Actual**: MISSING
- No constitution loading in orchestrator
- No metadata extraction for "Constitution:" lines
- Task schema lacks constitution_rules field

**Status**: ❌ 0% IMPLEMENTED

---

### 3. Executor Integration ❌ NOT IMPLEMENTED

**Required**:
```python
def execute_wave(wave_id: int):
    constitution = Constitution("memory-bank/shared/.constitution.md")

    for task in get_wave_tasks(wave_id):
        # Pass constitution to agent
        agent_context = {
            "constitution": constitution.get_rules_for_task(task)
        }
        execute_task(task, agent_context)
```

**Actual**: MISSING
- Wave executor does not load constitution
- No agent context with constitution rules
- No integration with task-watchdog for rule tracking

**Status**: ❌ 0% IMPLEMENTED

---

### 4. Checkpoint Validation ❌ NOT IMPLEMENTED

**Required**:
```python
def checkpoint_wave(wave_id: int):
    constitution = Constitution("memory-bank/shared/.constitution.md")
    violations = constitution.validate_wave_output(wave_id)

    if violations:
        return False  # Block checkpoint

    git_checkpoint(...)
    return True
```

**Actual**: MISSING
- Checkpoint only verifies task completion (tasks.md markers)
- NO constitution validation
- NO file scanning for violations

**Status**: ❌ 0% IMPLEMENTED

---

## Critical Missing Components

### 1. Constitution Metadata Extractor (MISSING)

**Location**: Should be in `cli/orchestrator.py`

**Required Function**:
```python
def _extract_constitution_metadata(self, task_lines: List[str]) -> List[str]:
    """
    Extract constitution rules from task metadata

    Example:
      - [ ] TASK-001: Create models
        - **Constitution**: Use Pydantic BaseModel
        - **Constitution**: Type hints required

    Returns: ["Use Pydantic BaseModel", "Type hints required"]
    """
    rules = []
    for line in task_lines:
        if '**Constitution**:' in line:
            rule = line.split(':', 1)[1].strip()
            rules.append(rule)
    return rules
```

**Impact**: HIGH - Without this, constitution rules never enter the system

---

### 2. Wave Executor Constitution Validator (MISSING)

**Location**: Should be in `cli/wave_executor.py`

**Required Method**:
```python
def _validate_constitution(self, wave_id: int, tasks: List[Dict]) -> List[ConstitutionViolation]:
    """
    Validate all modified files against constitution

    Returns list of violations found
    """
    violations = []

    # Get all files modified in this wave
    modified_files = []
    for task in tasks:
        modified_files.extend(task.get('file_locks', []))

    # Validate each file
    for file_path in set(modified_files):
        if Path(file_path).exists():
            file_violations = self.constitution.validate_file(file_path)
            violations.extend(file_violations)

    return violations
```

**Impact**: CRITICAL - Constitution never enforced

---

### 3. Task-Watchdog Constitution Storage (MISSING)

**Location**: `rust-watchdog/src/types.rs`

**Required Schema Update**:
```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskInfo {
    pub mode: ExecutionMode,
    pub command: String,
    pub status: TaskStatus,
    pub started_at: DateTime<Utc>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub completed_at: Option<DateTime<Utc>>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub native: Option<NativeTask>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub docker: Option<DockerTask>,

    // ← ADD THIS
    #[serde(skip_serializing_if = "Option::is_none")]
    pub constitution_rules: Option<Vec<String>>,
}
```

**Impact**: MEDIUM - Prevents watchdog from tracking constitution context

---

### 4. Watchdog Registration Command (MISSING)

**Location**: `rust-watchdog/src/main.rs`

**Required Subcommand**:
```rust
#[derive(Subcommand)]
enum Commands {
    // ... existing commands ...

    /// Register a task with constitution rules
    Register {
        /// Task ID
        #[arg(long)]
        task_id: String,

        /// Task command
        #[arg(long)]
        command: String,

        /// Constitution rules (JSON array)
        #[arg(long)]
        constitution_rules: Option<String>,

        /// Registry file path
        #[arg(long, default_value = ".claude/process_registry.json")]
        registry: String,
    },
}
```

**Impact**: HIGH - Wave executor cannot register tasks with watchdog

---

## Gap Summary Table

| Integration Point | Spec Requirement | Current Status | Gap Severity |
|------------------|------------------|----------------|--------------|
| Constitution file path | `memory-bank/shared/.constitution.md` | ✅ Correct | None |
| Constitution parser | Parse markdown, extract sections | ✅ Implemented | None |
| Task schema (Python) | `constitution_rules: List[str]` | ❌ Missing | CRITICAL |
| Task schema (Rust) | `constitution_rules: Option<Vec<String>>` | ❌ Missing | HIGH |
| Orchestrator parsing | Extract constitution from tasks.md | ❌ Not implemented | CRITICAL |
| Execution plan JSON | Include constitution_rules field | ❌ Not implemented | HIGH |
| Wave executor loading | Load constitution from file | ❌ Not implemented | CRITICAL |
| Wave executor validation | Validate files at checkpoint | ❌ Not implemented | CRITICAL |
| Watchdog registration | Register tasks with rules | ❌ Not implemented | HIGH |
| Checkpoint enforcement | Block checkpoint on violations | ❌ Not implemented | CRITICAL |

**Summary**:
- ✅ Implemented: 2 / 10 (20%)
- ❌ Missing: 8 / 10 (80%)
- CRITICAL gaps: 5
- HIGH gaps: 3

---

## Root Cause Analysis

### Why is Integration Broken?

1. **Constitution parser exists but is isolated**
   - `constitution_manager.py` has all necessary parsing logic
   - BUT: No other modules import or use it
   - **Root cause**: Parser was built as standalone, never integrated

2. **Orchestrator and executor were built without constitution awareness**
   - Both modules focus only on task execution mechanics
   - No design consideration for constitution rules
   - **Root cause**: Likely built before constitution system was designed

3. **Task schema divergence between Python and Rust**
   - Python Task dataclass has no constitution field
   - Rust TaskInfo struct has no constitution field
   - **Root cause**: Schema evolution without constitution requirements

4. **No validation hook in checkpoint flow**
   - Checkpoint only verifies task completion markers
   - File validation logic exists in Constitution class but is never called
   - **Root cause**: Missing integration point in wave executor

---

## Recommendations

### Priority 1 (CRITICAL - Blocks all constitution enforcement)

1. **Update Task Schema**
   - Add `constitution_rules` field to `cli/orchestrator.py:Task` dataclass
   - Add `constitution_rules` field to `rust-watchdog/src/types.rs:TaskInfo`

2. **Implement Constitution Metadata Parsing**
   - Add `_extract_constitution_metadata()` to orchestrator
   - Modify `parse_tasks()` to call it for each task
   - Update `create_waves()` to include rules in execution plan

3. **Integrate Constitution into Wave Executor**
   - Import Constitution class in wave_executor.py
   - Load constitution in `__init__()`
   - Implement `_validate_constitution()` method
   - Call validation in `execute_checkpoint()`

### Priority 2 (HIGH - Enables full integration)

4. **Add Watchdog Registration**
   - Implement `Register` command in rust-watchdog
   - Call watchdog from wave executor when starting tasks

5. **Test End-to-End Flow**
   - Create test tasks.md with constitution metadata
   - Run orchestrator and verify execution_plan.json
   - Run wave executor and verify checkpoint validation

### Priority 3 (MEDIUM - Enhances usability)

6. **Add Constitution CLI Commands**
   - `dev-kid constitution validate` (already exists)
   - `dev-kid constitution check-file <path>` (validate single file)
   - `dev-kid constitution explain <task-id>` (show rules for task)

---

## Testing Recommendations

### Integration Test Checklist

1. **Constitution → Tasks → Execution Plan**
   - Create `.constitution.md`
   - Create `tasks.md` with constitution metadata
   - Run `dev-kid orchestrate`
   - Verify `execution_plan.json` contains constitution_rules

2. **Execution Plan → Wave Execution → Validation**
   - Run `dev-kid execute` with execution plan
   - Introduce constitution violation (e.g., function without type hints)
   - Verify checkpoint BLOCKS with violation message

3. **Watchdog Integration**
   - Start task-watchdog daemon
   - Execute wave with constitution rules
   - Check watchdog registry includes constitution_rules
   - Verify watchdog can report constitution context

---

## Code Locations Reference

### Files Requiring Changes

| File | Lines | Change Required |
|------|-------|-----------------|
| `cli/orchestrator.py` | 13-21 | Add constitution_rules to Task dataclass |
| `cli/orchestrator.py` | 41-76 | Add constitution metadata parsing in parse_tasks() |
| `cli/orchestrator.py` | 167-183 | Include constitution_rules in wave tasks |
| `cli/wave_executor.py` | 1-12 | Import Constitution class |
| `cli/wave_executor.py` | 16-19 | Load constitution in __init__() |
| `cli/wave_executor.py` | 51-75 | Add _validate_constitution() call in checkpoint |
| `cli/wave_executor.py` | NEW | Implement _validate_constitution() method |
| `rust-watchdog/src/types.rs` | 69-84 | Add constitution_rules field to TaskInfo |
| `rust-watchdog/src/main.rs` | 25-89 | Add Register command to Commands enum |
| `rust-watchdog/src/main.rs` | NEW | Implement register_task() function |

---

## Conclusion

The integration between SpecKit and dev-kid for constitution enforcement is **architecturally sound in design but critically incomplete in implementation**. The foundation exists (constitution parser, templates, validation logic) but the connective tissue that would make rules flow through the entire pipeline is **missing at 4 critical integration points**:

1. **Orchestrator** does not extract constitution metadata from tasks
2. **Execution plan** does not include constitution_rules field
3. **Wave executor** does not load or validate against constitution
4. **Task-watchdog** cannot store or track constitution rules

**Estimated Implementation Effort**:
- Priority 1 fixes: ~4-6 hours (schema updates, metadata parsing, checkpoint validation)
- Priority 2 fixes: ~2-3 hours (watchdog integration)
- Testing: ~2-3 hours (end-to-end integration tests)
- **Total**: ~8-12 hours of focused development

**Blocker Status**: This gap analysis reveals that **constitution enforcement is currently non-functional** despite the guarantee document claiming it works. All implementation must be completed before the integration can be considered operational.

---

**Report Generated**: 2026-01-10
**Reviewer**: Code Review Agent
**Next Steps**: Prioritize implementation of missing integration points starting with Priority 1 items

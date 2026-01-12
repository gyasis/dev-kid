# Architecture Data Flow Analysis
## Detailed Field-Level Tracing

**Purpose**: Track exactly where constitution metadata is lost in the pipeline

---

## Field Mapping Table

| Source | Field Name | Type | Next Layer | Preserved? | Lost At |
|--------|-----------|------|------------|------------|---------|
| `.constitution.md` | Technology Standards | Markdown list | tasks.md metadata | ✅ | - |
| `.constitution.md` | Architecture Principles | Markdown list | tasks.md metadata | ✅ | - |
| tasks.md | `**Constitution**: rule1, rule2` | Inline metadata | orchestrator.py | ❌ | **orchestrator.py:62-68** |
| tasks.md | `**Files**: file.py` | Inline metadata | orchestrator.py | ✅ → file_locks | - |
| tasks.md | Task description | Markdown line | orchestrator.py | ✅ | - |
| orchestrator.py | `task.description` | String | execution_plan.json | ✅ → instruction | - |
| orchestrator.py | `task.file_locks` | List[str] | execution_plan.json | ✅ | - |
| orchestrator.py | `task.constitution_rules` | **MISSING** | execution_plan.json | ❌ | **Never created** |
| execution_plan.json | `task.instruction` | String | wave_executor.py | ✅ | - |
| execution_plan.json | `task.file_locks` | Array | wave_executor.py | ✅ (unused) | - |
| execution_plan.json | `task.constitution_rules` | **MISSING** | wave_executor.py | ❌ | **Schema gap** |
| wave_executor.py | Task context | In-memory | Agent spawn | ✅ (incomplete) | - |
| wave_executor.py | Constitution rules | **MISSING** | Agent context | ❌ | **Never loaded** |
| Agent context | Constitution rules | **MISSING** | Watchdog | ❌ | **No registration** |
| Watchdog | `task.constitution_rules` | **MISSING** | process_registry.json | ❌ | **Rust struct missing field** |
| Checkpoint | Constitution validation | **MISSING** | Git commit | ❌ | **No validator** |

---

## Data Flow Trace: Constitution Rule "Use Pydantic BaseModel"

### Step 1: Source Definition
```markdown
FILE: memory-bank/shared/.constitution.md

## Technology Standards
- Python 3.11+ required
- FastAPI framework for APIs
- Pydantic for data validation  ← RULE DEFINED HERE
```

### Step 2: Task Creation (SpecKit)
```markdown
FILE: tasks.md

- [ ] TASK-001: Create data models (30 min)
  - **Constitution**: Use Pydantic BaseModel  ← RULE REFERENCED HERE
  - **Files**: cli/models/observability.py (new)
```

**Status**: ✅ Rule metadata present

---

### Step 3: Orchestration (dev-kid)
```python
FILE: cli/orchestrator.py

# Line 52-54: Parse task line
if line.startswith('- [ ]') or line.startswith('- [x]'):
    completed = '[x]' in line
    description = line.split(']', 1)[1].strip()
    # ← description = "TASK-001: Create data models (30 min)\n  - **Constitution**: Use Pydantic BaseModel\n  - **Files**: cli/models/observability.py"

# Line 56-58: Extract file references
file_locks = self._extract_file_references(description)
# ← file_locks = ["cli/models/observability.py"]  ✅ EXTRACTED

# Line 60: Extract dependencies
dependencies = self._extract_dependencies(description)
# ← dependencies = []  ✅ EXTRACTED

# ❌ MISSING: Extract constitution metadata
# constitution_rules = self._extract_constitution_metadata(description)
# ← This function DOESN'T EXIST

# Line 62-68: Create Task object
task = Task(
    id=f"T{task_id:03d}",
    description=description,  # ✅ Full text preserved
    file_locks=file_locks,    # ✅ Extracted
    dependencies=dependencies, # ✅ Extracted
    # ❌ MISSING: constitution_rules=constitution_rules
    completed=completed
)
```

**Status**: 🔴 **LOST HERE** - Constitution metadata not extracted

**Dataclass Definition** (Line 13-21):
```python
@dataclass
class Task:
    id: str
    description: str
    agent_role: str = "Developer"
    file_locks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    # ❌ MISSING FIELD: constitution_rules: List[str] = field(default_factory=list)
    completed: bool = False
```

---

### Step 4: Execution Plan Generation
```python
FILE: cli/orchestrator.py

# Line 170-177: Create execution plan task object
wave = Wave(
    wave_id=wave_id,
    strategy=strategy,
    tasks=[{
        "task_id": t.id,                    # ✅ T001
        "agent_role": "Developer",          # ✅ Default
        "instruction": t.description,       # ✅ Full description (with metadata text)
        "file_locks": t.file_locks,         # ✅ ["cli/models/observability.py"]
        "completion_handshake": f"...",     # ✅ Generated
        "dependencies": list(dependency_graph[t.id])  # ✅ []
        # ❌ MISSING: "constitution_rules": t.constitution_rules
    } for t in wave_tasks],
    rationale=f"...",
    checkpoint_enabled=True
)
```

**Output** (execution_plan.json):
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
        "instruction": "TASK-001: Create data models (30 min)\n  - **Constitution**: Use Pydantic BaseModel\n  - **Files**: cli/models/observability.py",
        "file_locks": ["cli/models/observability.py"],
        "dependencies": []
        // ❌ MISSING: "constitution_rules": ["Use Pydantic BaseModel"]
      }]
    }]
  }
}
```

**Status**: 🔴 **LOST** - Constitution metadata not in structured field (only in instruction string)

---

### Step 5: Wave Execution
```python
FILE: cli/wave_executor.py

# Line 16: Load execution plan
self.plan = json.loads(self.plan_file.read_text())

# Line 103-129: Execute wave
def execute_wave(self, wave: Dict) -> None:
    wave_id = wave['wave_id']
    strategy = wave['strategy']
    tasks = wave['tasks']  # ← List of task dicts

    for task in tasks:
        # task = {
        #   "task_id": "T001",
        #   "instruction": "TASK-001: Create data models...\n  - **Constitution**: Use Pydantic...",
        #   "file_locks": ["cli/models/observability.py"]
        # }

        # ❌ NO CONSTITUTION LOADING
        # constitution = Constitution()
        # rules = constitution.get_rules_for_task(task)

        # Line 117-118: Just print
        print(f"      🤖 Agent {task['agent_role']}: {task['task_id']} - {task['instruction'][:50]}...")

        # ❌ NO AGENT SPAWNING WITH CONSTITUTION CONTEXT
        # agent_context = {
        #     "task": task,
        #     "constitution_rules": rules  # ← Would be empty anyway
        # }
        # spawn_agent(task['agent_role'], agent_context)
```

**Status**: 🔴 **NEVER LOADED** - Constitution not accessed, rules not passed to agents

---

### Step 6: Agent Context (Hypothetical)
```python
# IF agents were spawned (they're not in current implementation)

agent_context = {
    "task_id": "T001",
    "instruction": "TASK-001: Create data models...",
    "file_locks": ["cli/models/observability.py"],
    # ❌ MISSING: "constitution_rules": ["Use Pydantic BaseModel"]
}

# Agent receives task WITHOUT constitution awareness
# Agent implements HOWEVER IT WANTS (could use dataclasses instead of Pydantic!)
```

**Status**: 🔴 **NEVER RECEIVED** - Agents execute without constitution constraints

---

### Step 7: Watchdog Registration (Not Happening)
```python
# EXPECTED (but doesn't exist):
subprocess.run(['dev-kid', 'task-start', 'T001', 'Create data models'])

# Would call: rust-watchdog CLI

# EXPECTED Rust code:
pub struct TaskInfo {
    pub mode: ExecutionMode,
    pub command: String,
    pub status: TaskStatus,
    // ❌ MISSING: pub constitution_rules: Option<Vec<String>>,
}

# process_registry.json would store:
{
  "tasks": {
    "T001": {
      "mode": "native",
      "command": "Create data models",
      "status": "running",
      "started_at": "2026-01-10T10:00:00Z"
      // ❌ MISSING: "constitution_rules": ["Use Pydantic BaseModel"]
    }
  }
}
```

**Status**: 🔴 **NEVER REGISTERED** - Watchdog doesn't know about task OR constitution

---

### Step 8: Checkpoint Validation
```python
FILE: cli/wave_executor.py

# Line 51-76: Checkpoint execution
def execute_checkpoint(self, wave_id: int, checkpoint: Dict) -> None:
    print(f"\n🔍 Checkpoint after Wave {wave_id}...")

    # Step 1: Verify tasks.md completion ✅
    tasks = self.plan['execution_plan']['waves'][wave_id - 1]['tasks']
    verified = self.verify_wave_completion(wave_id, tasks)
    # ← Only checks if tasks are marked [x] in tasks.md

    if not verified:
        sys.exit(1)

    # Step 2: Update progress.md ✅
    self._update_progress(wave_id, tasks)

    # Step 3: Git checkpoint ✅
    self._git_checkpoint(wave_id)

    # ❌ MISSING: Constitution validation
    # constitution = Constitution()
    # violations = constitution.validate_output(modified_files)
    # if violations:
    #     print("Constitution violated!")
    #     sys.exit(1)
```

**Status**: 🔴 **NEVER VALIDATED** - Code could violate "Use Pydantic" rule, checkpoint still passes

---

### Step 9: Git Commit (Unconditional)
```bash
# Line 100-101: Git checkpoint
subprocess.run(['git', 'add', '.'], check=True)
subprocess.run(['git', 'commit', '-m', commit_msg], check=False)

# Commits code that might use:
# - dataclasses INSTEAD of Pydantic (constitution violation!)
# - raw dictionaries
# - no validation at all

# ❌ NO ENFORCEMENT - Constitution rule completely ignored
```

**Status**: 🔴 **RULE VIOLATED** - Checkpoint created without constitution compliance

---

## Result: Constitution Rule Lost

```
INPUT: "Use Pydantic BaseModel" (in .constitution.md)
  ↓
REFERENCED: In tasks.md metadata
  ↓
❌ LOST: orchestrator.py doesn't extract metadata (line 62-68)
  ↓
MISSING: execution_plan.json has no constitution_rules field
  ↓
NOT LOADED: wave_executor.py doesn't read constitution
  ↓
NOT PASSED: Agents receive no constitution context
  ↓
NOT TRACKED: Watchdog has no constitution_rules field
  ↓
NOT VALIDATED: Checkpoint doesn't check compliance
  ↓
VIOLATED: Code uses dataclasses, git commit succeeds

OUTCOME: Constitution enforcement COMPLETELY BYPASSED
```

---

## Fix Sequence (with exact line numbers)

### Fix 1: Add Constitution Field to Task Dataclass
**File**: `cli/orchestrator.py`
**Lines**: 13-21

```python
@dataclass
class Task:
    id: str
    description: str
    agent_role: str = "Developer"
    file_locks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    constitution_rules: List[str] = field(default_factory=list)  # ← ADD THIS LINE
    completed: bool = False
```

### Fix 2: Add Metadata Extraction Method
**File**: `cli/orchestrator.py`
**After**: Line 101 (after `_extract_dependencies`)

```python
def _extract_constitution_metadata(self, description: str) -> List[str]:
    """Extract constitution rules from task description"""
    import re

    # Match pattern: **Constitution**: Rule1, Rule2
    match = re.search(r'\*\*Constitution\*\*:\s*(.+?)(?:\n|$)', description, re.MULTILINE)
    if match:
        rules_text = match.group(1)
        return [r.strip() for r in rules_text.split(',')]
    return []
```

### Fix 3: Extract Metadata During Parsing
**File**: `cli/orchestrator.py`
**Lines**: 62-68 (modify)

```python
task = Task(
    id=f"T{task_id:03d}",
    description=description,
    file_locks=file_locks,
    dependencies=dependencies,
    constitution_rules=self._extract_constitution_metadata(description),  # ← ADD THIS LINE
    completed=completed
)
```

### Fix 4: Include in Execution Plan
**File**: `cli/orchestrator.py`
**Lines**: 170-177 (modify)

```python
tasks=[{
    "task_id": t.id,
    "agent_role": "Developer",
    "instruction": t.description,
    "file_locks": t.file_locks,
    "completion_handshake": f"Upon success, update tasks.md line containing '{t.description}' to [x]",
    "dependencies": list(dependency_graph[t.id]),
    "constitution_rules": t.constitution_rules  # ← ADD THIS LINE
} for t in wave_tasks],
```

### Fix 5: Load Constitution in Executor
**File**: `cli/wave_executor.py`
**After**: Line 11 (imports)

```python
from cli.constitution_parser import Constitution  # ← ADD THIS
```

**Lines**: 103-129 (modify `execute_wave`)

```python
def execute_wave(self, wave: Dict) -> None:
    # Load constitution
    constitution = Constitution()  # ← ADD THIS

    wave_id = wave['wave_id']
    strategy = wave['strategy']
    tasks = wave['tasks']

    print(f"\n🌊 Executing Wave {wave_id} ({strategy})...")

    for task in tasks:
        # Get constitution rules for this task
        rules = task.get('constitution_rules', [])  # ← ADD THIS

        if rules:  # ← ADD THIS BLOCK
            print(f"      📜 Constitution rules:")
            for rule in rules:
                print(f"         - {rule}")

        print(f"      🤖 Agent {task['agent_role']}: {task['task_id']} - {task['instruction'][:50]}...")

        # In real implementation: pass rules to agent
        # agent_context = {"task": task, "constitution_rules": rules}
        # spawn_agent(task['agent_role'], agent_context)
```

### Fix 6: Validate at Checkpoint
**File**: `cli/wave_executor.py`
**Lines**: 51-76 (modify `execute_checkpoint`)

```python
def execute_checkpoint(self, wave_id: int, checkpoint: Dict) -> None:
    print(f"\n🔍 Checkpoint after Wave {wave_id}...")

    # Step 1: Verify tasks.md (existing)
    tasks = self.plan['execution_plan']['waves'][wave_id - 1]['tasks']
    verified = self.verify_wave_completion(wave_id, tasks)
    if not verified:
        sys.exit(1)

    # Step 2: Validate constitution (NEW)
    print("   Step 2: Validating constitution compliance...")  # ← ADD
    constitution = Constitution()  # ← ADD

    # Get modified files
    result = subprocess.run(['git', 'diff', '--name-only', 'HEAD'],  # ← ADD
                          capture_output=True, text=True)
    modified_files = result.stdout.strip().split('\n')

    violations = constitution.validate_output(modified_files)  # ← ADD

    if violations:  # ← ADD BLOCK
        print(f"\n❌ Constitution Violations - Checkpoint BLOCKED:")
        for v in violations:
            print(f"   Rule: {v['rule']}")
            print(f"   File: {v['file']}:{v['line']}")
            print(f"   Issue: {v['message']}")
        sys.exit(1)

    print("   ✅ Constitution compliance verified")  # ← ADD

    # Step 3: Update progress (renumbered)
    print("   Step 3: memory-bank-keeper updates progress.md...")
    self._update_progress(wave_id, tasks)

    # Step 4: Git checkpoint (renumbered)
    print("   Step 4: git-version-manager creates checkpoint...")
    self._git_checkpoint(wave_id)
```

### Fix 7: Add Constitution Parser
**File**: `cli/constitution_parser.py` (NEW FILE)

```python
#!/usr/bin/env python3
"""
Constitution Parser - Parse and validate against .constitution.md
"""

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
        return task.get('constitution_rules', [])

    def validate_output(self, files: List[str]) -> List[Dict]:
        """Validate files against constitution rules"""
        violations = []

        # Example validation: Check for Pydantic usage
        for file in files:
            if not Path(file).exists():
                continue

            if file.endswith('.py'):
                content = Path(file).read_text()

                # Check if file should use Pydantic
                if 'BaseModel' in str(self.rules.get('Technology Standards', [])):
                    if 'from pydantic import' not in content and 'class ' in content:
                        violations.append({
                            'rule': 'Use Pydantic BaseModel',
                            'file': file,
                            'line': 1,
                            'message': 'Model class found but not using Pydantic'
                        })

        return violations
```

---

## Verification Test

After implementing fixes, this trace should work:

```python
# 1. Create constitution
# FILE: memory-bank/shared/.constitution.md
## Technology Standards
- Use Pydantic BaseModel

# 2. Create task with metadata
# FILE: tasks.md
- [ ] TASK-001: Create models
  - **Constitution**: Use Pydantic BaseModel
  - **Files**: models.py

# 3. Orchestrate
$ dev-kid orchestrate

# VERIFY: execution_plan.json contains:
{
  "tasks": [{
    "task_id": "T001",
    "constitution_rules": ["Use Pydantic BaseModel"]  # ✅ PRESENT
  }]
}

# 4. Execute
$ dev-kid execute

# VERIFY: Console output shows:
🌊 Executing Wave 1...
   📜 Constitution rules:
      - Use Pydantic BaseModel  # ✅ LOADED

# 5. Create violating code
# FILE: models.py
from dataclasses import dataclass  # ❌ Violates Pydantic rule

@dataclass
class MyModel:
    name: str

# 6. Try checkpoint
$ dev-kid checkpoint "Wave 1"

# VERIFY: Checkpoint BLOCKED:
❌ Constitution Violations - Checkpoint BLOCKED:
   Rule: Use Pydantic BaseModel
   File: models.py:1
   Issue: Model class found but not using Pydantic

# 7. Fix code
# FILE: models.py
from pydantic import BaseModel  # ✅ Complies

class MyModel(BaseModel):
    name: str

# 8. Checkpoint again
$ dev-kid checkpoint "Wave 1"

# VERIFY: Checkpoint SUCCEEDS:
✅ Constitution compliance verified
✅ Checkpoint complete
```

**If all steps verify**: Constitution metadata preserved end-to-end ✅

---

## Summary: Field-Level Impact

| Phase | Constitution Field Status | Impact |
|-------|---------------------------|--------|
| Constitution File | ✅ Rules defined | Source of truth |
| tasks.md | ✅ Metadata present | Human-readable format |
| Orchestrator | ❌ **LOST** | Field not extracted |
| Execution Plan | ❌ **MISSING** | Schema gap |
| Wave Executor | ❌ **NOT LOADED** | Never accessed |
| Agent Context | ❌ **NOT PASSED** | Agents unaware |
| Watchdog | ❌ **NOT TRACKED** | Monitoring blind |
| Checkpoint | ❌ **NOT VALIDATED** | Enforcement gap |
| Git Commit | ❌ **UNCONSTRAINED** | Rules ignored |

**Critical Path**: All 6 fixes required to close the loop.


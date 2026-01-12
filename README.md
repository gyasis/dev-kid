# Dev-Kid v2.0 🚀

**Enhanced Planning System for Claude Code with Task Orchestration & Context Protection**

Dev-kid is a complete development workflow system that transforms how AI agents work with your codebase. It provides persistent memory, task orchestration with wave-based parallelization, and a task watchdog that survives context compression.

## Key Features

### 🌊 Wave-Based Task Orchestration
- **Intelligent Parallelization**: Automatically groups tasks into execution waves
- **Dependency Analysis**: Prevents race conditions with file locking
- **Checkpoint Verification**: Mandatory validation between waves
- **Progress Tracking**: Real-time monitoring of wave execution

### 🐕 Task Watchdog (Survives Context Compression)
- **Background Monitoring**: Process-based task timer (not token-dependent)
- **5-Minute Checks**: Automatic detection of forgotten tasks
- **Completion Tracking**: Records task timing and completion
- **Warning System**: Alerts for long-running or forgotten tasks
- **Context Resilient**: Persists state through context compression

### 💾 Memory Bank
- **6-Tier Architecture**: Shared + private institutional memory
- **Project Brief**: North Star vision document
- **System Patterns**: Architecture patterns and gotchas
- **Active Context**: Current focus and next actions
- **Progress Tracking**: Task completion metrics
- **Work Log**: Daily work entries

### 🛡️ Context Protection
- **Active Stack**: <500 token current focus
- **Activity Stream**: Append-only event log
- **Agent State**: Multi-agent coordination
- **System Bus**: Inter-agent messaging
- **Session Snapshots**: Zero-loss session recovery

### 🎯 Skills Layer (Auto-Triggering)
- **orchestrate-tasks.md**: Auto-orchestrates tasks.md into parallelized waves
- **execute-waves.md**: Auto-executes waves with monitoring & checkpoints
- **checkpoint-wave.md**: Auto-validates wave completion
- **sync-memory.md**: Auto-updates Memory Bank after checkpoints
- **speckit-workflow.md**: Complete workflow guide

### ⚡ Claude Code Commands (Manual)
- **/devkid.orchestrate**: Convert tasks to waves
- **/devkid.execute**: Execute waves with monitoring
- **/devkid.checkpoint**: Validate & commit
- **/devkid.sync-memory**: Update memory bank
- **/devkid.workflow**: Show complete workflow guide

### 🔗 Speckit Integration
- Seamless workflow from planning to execution
- Git hooks for branch-based task management
- Constitution enforcement at checkpoints
- Feature branch isolation with progress preservation

## Dependencies

### Required
- **Bash** 4.0+ (CLI and scripts)
- **Git** 2.0+ (version control and checkpointing)
- **Python 3.7+** (orchestration, no external packages needed)
- **jq** 1.5+ (JSON parsing)

### Recommended
- **sed**, **grep** (template processing)

The installer automatically checks all dependencies and provides installation instructions if anything is missing. See [DEPENDENCIES.md](DEPENDENCIES.md) for detailed requirements and platform-specific installation instructions.

## 🚀 Quickstart

**Want to get started in 5 minutes?** See **[QUICKSTART.md](QUICKSTART.md)** for a guided walkthrough.

**TL;DR:**
```bash
# Install
./scripts/install.sh

# In your project
cd your-project
dev-kid init

# With Speckit (recommended)
/speckit.constitution
/speckit.specify "Your feature"
/speckit.tasks
/devkid.execute

# Or standalone
echo "- [ ] Task 1" > tasks.md
dev-kid orchestrate "Phase 1"
dev-kid execute
```

## Installation

### Detailed Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/planning-with-files.git
cd planning-with-files

# Run installer
./scripts/install.sh

# Verify installation
dev-kid version
```

This installs:
- CLI to `~/.dev-kid/` with symlink at `/usr/local/bin/dev-kid`
- **Skills** to `~/.claude/skills/` (auto-triggering workflows)
- **Commands** to `~/.claude/commands/` (slash commands)
- Templates to `~/.dev-kid/templates/`

Verify installation:
```bash
./scripts/verify-install.sh
```

### Initialize in Your Project

```bash
cd your-project
dev-kid init

# This creates:
# - memory-bank/        (institutional memory)
# - .claude/            (context protection)
# - Git hooks           (auto-checkpoint on commit)
```

### Workflow Options

#### Option 1: With Speckit (Recommended)

Complete workflow from planning to execution:

```bash
# 1. Create project constitution (once per project)
/speckit.constitution

# 2. Create feature spec
/speckit.specify "Add user authentication with OAuth2"
# Creates: .specify/specs/001-user-auth/spec.md

# 3. Generate tasks
/speckit.tasks
# Creates: .specify/specs/001-user-auth/tasks.md
# Git hook auto-symlinks: tasks.md → .specify/specs/001-user-auth/tasks.md

# 4. Orchestrate into waves (auto-triggers or manual)
/devkid.orchestrate

# 5. Execute waves (auto-triggers or manual)
/devkid.execute

# 6. Checkpoint & sync (auto-triggers or manual)
/devkid.checkpoint
/devkid.sync-memory
```

**Branch switching preserves progress:**
```bash
git checkout 002-payment-flow
# Git hook auto-relinks: tasks.md → .specify/specs/002-payment-flow/tasks.md
```

#### Option 2: Standalone Dev-Kid

Basic workflow without speckit:

#### 1. Define Your Project

Edit `memory-bank/shared/projectbrief.md`:
```markdown
# Project Brief

## Vision
Build a task management API with real-time notifications

## Goals
- RESTful API with CRUD operations
- WebSocket support for live updates
- PostgreSQL database with migrations
```

#### 2. Create Task List

Create `tasks.md`:
```markdown
# Tasks

## Phase 1: Foundation
- [ ] Set up FastAPI project structure
- [ ] Configure PostgreSQL connection
- [ ] Create database models for tasks

## Phase 2: API
- [ ] Implement CRUD endpoints
- [ ] Add authentication middleware
- [ ] Write API tests
```

#### 3. Orchestrate into Waves

```bash
dev-kid orchestrate "Phase 1"
```

This creates `execution_plan.json` with parallelized execution waves:
```
Wave 1 (parallel):
  - Set up FastAPI project structure
  - Configure PostgreSQL connection

Wave 2 (sequential after Wave 1):
  - Create database models
```

#### 4. Start Task Watchdog

```bash
dev-kid watchdog-start
```

This starts background task monitoring that:
- Checks every 5 minutes for running tasks
- Warns if tasks exceed 7-minute guideline (investigate what's happening)
- Detects stalled tasks (no activity for >15 min)
- Task process continues until marked complete (doesn't auto-stop)
- Survives context compression

#### 5. Execute Waves

```bash
dev-kid execute
```

This:
- Executes each wave sequentially
- Verifies task completion between waves
- Creates git checkpoints after each wave
- Updates Memory Bank with progress

### Check Status

```bash
dev-kid status
```

Shows:
- Memory Bank health
- Context Protection status
- Task Watchdog activity (running/completed tasks)
- Skills installation
- Git status
- Execution plan waves

### Monitor Tasks

```bash
# View task timing report
dev-kid watchdog-report

# Check current watchdog status
dev-kid watchdog-check

# Stop watchdog
dev-kid watchdog-stop
```

### Manual Task Tracking

```bash
# Start a task timer
dev-kid task-start TASK-001 "Implement user authentication"

# Complete the task
dev-kid task-complete TASK-001
```

### Session Management

```bash
# Create checkpoint with message
dev-kid checkpoint "Feature complete: user auth"

# Finalize session (creates snapshot)
dev-kid finalize

# Recall last session (resume from snapshot)
dev-kid recall
```

## Command Reference

### Core Commands
- `dev-kid init [PATH]` - Initialize dev-kid in project
- `dev-kid orchestrate [PHASE]` - Convert tasks.md into waves
- `dev-kid execute` - Execute waves from execution plan
- `dev-kid status` - Show system status

### Task Watchdog
- `dev-kid watchdog-start` - Start background monitoring
- `dev-kid watchdog-stop` - Stop watchdog process
- `dev-kid watchdog-check` - Run one-time check
- `dev-kid watchdog-report` - Show timing report
- `dev-kid task-start ID DESC` - Start task timer
- `dev-kid task-complete ID` - Complete task

### Memory & Checkpoints
- `dev-kid sync-memory` - Update Memory Bank
- `dev-kid checkpoint MSG` - Create git checkpoint
- `dev-kid recall` - Resume from last snapshot
- `dev-kid finalize` - Create session snapshot

### System
- `dev-kid verify` - Run anti-hallucination check
- `dev-kid validate` - Validate system integrity
- `dev-kid waves` - Show execution plan waves
- `dev-kid help` - Show all commands

## Architecture

```
planning-with-files/
├── cli/
│   ├── dev-kid              # Main CLI entry point
│   ├── orchestrator.py      # Task → wave converter
│   ├── wave_executor.py     # Wave execution engine
│   └── task_watchdog.py     # Background task monitor
├── skills/
│   ├── sync_memory.sh       # Memory Bank updater
│   ├── checkpoint.sh        # Git checkpoint creator
│   ├── verify_existence.sh  # Anti-hallucination
│   ├── recall.sh            # Session recovery
│   ├── finalize_session.sh  # Session snapshot
│   └── maintain_integrity.sh # System validator
├── scripts/
│   ├── install.sh           # Global installation
│   └── init.sh              # Per-project scaffold
├── templates/
│   ├── memory-bank/         # Memory Bank templates
│   └── .claude/             # Context Protection templates
└── DEV_KID.md               # Complete documentation
```

## How It Works

### 1. Task Orchestration

**Input**: Linear task list in `tasks.md`
```markdown
- [ ] Task A (edits file1.py)
- [ ] Task B (edits file2.py)
- [ ] Task C (edits file1.py)
```

**Processing**:
- Dependency graph analysis
- File lock detection
- Wave grouping

**Output**: Parallelized execution plan
```
Wave 1: Task A, Task B (parallel - different files)
Wave 2: Task C (sequential - conflicts with Task A)
```

### 2. Task Watchdog

**Process-Based Monitoring**:
```bash
# Starts as background process
python3 task_watchdog.py run &

# State persisted to disk (survives compression)
.claude/task_timers.json:
{
  "running_tasks": {
    "TASK-001": {
      "started_at": "2025-01-05T10:30:00",
      "description": "Implement auth"
    }
  },
  "completed_tasks": {...},
  "warnings": [...]
}
```

**Check Cycle** (every 5 minutes):
1. Load state from disk
2. Sync with tasks.md (detect [x] completions)
3. Check for tasks exceeding 7-minute guideline
4. Check for stalled tasks (>15 min no activity)
5. Generate warnings
6. Save state to disk

### 3. Checkpoint Protocol

**Between Waves**:
1. memory-bank-keeper validates tasks.md
2. Checks all tasks marked [x]
3. Updates progress.md
4. git-version-manager creates checkpoint
5. Only proceeds if verification passes

**Prevents**:
- Tasks marked incomplete progressing to next wave
- Lost work during context compression
- Inconsistent state between Memory Bank and git

## API Reference: Constitution Enforcement

Dev-Kid v2.0 integrates with SpecKit Constitution to enforce code quality rules throughout the task orchestration lifecycle. This section provides complete API documentation for developers integrating constitution enforcement into their workflows.

### Constitution Class API

The `Constitution` class (from SpecKit) provides rule-based validation for task outputs.

#### Core Methods

**`__init__(rules_dir: str = None)`**

Initialize constitution with rules from a directory.

```python
from speckit.constitution import Constitution

# Load from default location (~/.speckit/rules/)
constitution = Constitution()

# Load from custom location
constitution = Constitution(rules_dir="/path/to/custom/rules")
```

**`validate_output(output: str, task_id: str, rules: List[str]) -> Dict[str, Any]`**

Validate task output against specified constitution rules.

```python
result = constitution.validate_output(
    output="def my_function():\n    return 42",
    task_id="TASK-001",
    rules=["TYPE_HINTS_REQUIRED", "DOCSTRINGS_REQUIRED"]
)

# Returns:
{
    "valid": False,
    "violations": [
        {
            "rule": "TYPE_HINTS_REQUIRED",
            "severity": "error",
            "message": "Function my_function missing return type hint",
            "line": 1
        },
        {
            "rule": "DOCSTRINGS_REQUIRED",
            "severity": "error",
            "message": "Function my_function missing docstring",
            "line": 1
        }
    ],
    "metrics": {
        "total_violations": 2,
        "error_count": 2,
        "warning_count": 0
    }
}
```

**`get_rules_for_task(task_description: str) -> List[str]`**

Extract constitution rules from task description.

```python
task_desc = "Implement user authentication\n**Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED"
rules = constitution.get_rules_for_task(task_desc)
# Returns: ["TYPE_HINTS_REQUIRED", "DOCSTRINGS_REQUIRED"]
```

#### Available Constitution Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `TYPE_HINTS_REQUIRED` | error | All functions must have type hints |
| `DOCSTRINGS_REQUIRED` | error | All functions/classes must have docstrings |
| `NO_PRINT_STATEMENTS` | warning | Use logging instead of print() |
| `NO_BARE_EXCEPT` | error | Catch specific exceptions, not bare except |
| `MAX_FUNCTION_LENGTH` | warning | Functions should not exceed 50 lines |
| `NO_GLOBAL_VARIABLES` | warning | Avoid global state |
| `PEP8_NAMING` | warning | Follow PEP 8 naming conventions |
| `NO_MAGIC_NUMBERS` | warning | Define constants for numeric literals |

### Orchestrator API: Constitution Metadata

The orchestrator extracts constitution rules from `tasks.md` and embeds them in `execution_plan.json`.

#### Task Format in tasks.md

Add `**Constitution**:` metadata to any task:

```markdown
# Tasks

## Phase 1: Core Features
- [ ] Implement user authentication module in `src/auth.py`
  **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED, NO_BARE_EXCEPT

- [ ] Create database models in `src/models.py`
  **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED

- [ ] Write API endpoints in `src/api.py`
  **Constitution**: TYPE_HINTS_REQUIRED, NO_PRINT_STATEMENTS
```

#### Orchestrator Execution

```bash
# Convert tasks.md into execution plan with constitution metadata
dev-kid orchestrate "Phase 1"
```

#### execution_plan.json Schema

The orchestrator generates JSON with `constitution_rules` field:

```json
{
  "execution_plan": {
    "phase_id": "Phase-1",
    "created_at": "2025-01-11T10:30:00Z",
    "waves": [
      {
        "wave_id": 1,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Tasks modify different files - no conflicts",
        "tasks": [
          {
            "task_id": "TASK-001",
            "description": "Implement user authentication module in `src/auth.py`",
            "files_affected": ["src/auth.py"],
            "dependencies": [],
            "constitution_rules": [
              "TYPE_HINTS_REQUIRED",
              "DOCSTRINGS_REQUIRED",
              "NO_BARE_EXCEPT"
            ]
          },
          {
            "task_id": "TASK-002",
            "description": "Create database models in `src/models.py`",
            "files_affected": ["src/models.py"],
            "dependencies": [],
            "constitution_rules": [
              "TYPE_HINTS_REQUIRED",
              "DOCSTRINGS_REQUIRED"
            ]
          }
        ],
        "checkpoint_after": {
          "verify_completion": true,
          "git_commit": true,
          "update_progress": true,
          "validate_constitution": true
        }
      }
    ]
  }
}
```

**Key Fields**:
- `constitution_rules`: List of rule IDs to enforce for this task
- `validate_constitution`: Boolean flag in checkpoint_after configuration

### Wave Executor API: Constitution Validation

The wave executor validates task outputs against constitution rules at checkpoint boundaries.

#### execute_task() Method

```python
from cli.wave_executor import WaveExecutor

executor = WaveExecutor()

# Execute task with constitution enforcement
task = {
    "task_id": "TASK-001",
    "description": "Implement auth module",
    "files_affected": ["src/auth.py"],
    "constitution_rules": ["TYPE_HINTS_REQUIRED", "DOCSTRINGS_REQUIRED"]
}

result = executor.execute_task(task)

# Returns:
{
    "task_id": "TASK-001",
    "status": "completed",
    "files_modified": ["src/auth.py"],
    "constitution_validation": {
        "valid": True,
        "violations": [],
        "metrics": {"total_violations": 0}
    }
}
```

#### execute_checkpoint() Method

Checkpoint validation runs constitution checks for all tasks in the wave:

```python
checkpoint_result = executor.execute_checkpoint(wave_id=1)

# Returns:
{
    "wave_id": 1,
    "checkpoint_status": "failed",  # Blocks progression
    "constitution_violations": [
        {
            "task_id": "TASK-001",
            "rule": "TYPE_HINTS_REQUIRED",
            "severity": "error",
            "message": "Function authenticate() missing return type hint",
            "file": "src/auth.py",
            "line": 42
        }
    ],
    "git_commit": None,  # No commit created due to violations
    "progress_updated": False
}
```

**Checkpoint Behavior**:
- If `valid = False`: Checkpoint BLOCKS wave progression
- Violations logged to `.claude/activity_stream.md`
- Tasks marked incomplete in `tasks.md`
- Agent receives violation report for remediation

#### Constitution Loading Flow

```python
# Pseudo-code for wave executor constitution integration

def execute_wave(wave):
    for task in wave.tasks:
        # 1. Execute task
        result = execute_task(task)

        # 2. Load constitution if rules specified
        if task.constitution_rules:
            constitution = Constitution()

            # 3. Read task output files
            output = read_files(task.files_affected)

            # 4. Validate against constitution
            validation = constitution.validate_output(
                output=output,
                task_id=task.task_id,
                rules=task.constitution_rules
            )

            # 5. Store validation result
            result["constitution_validation"] = validation

    # 6. Checkpoint with constitution check
    checkpoint = execute_checkpoint(wave)

    # 7. Block if violations found
    if not checkpoint.constitution_valid:
        raise ConstitutionViolationError(checkpoint.violations)

    return checkpoint
```

### Watchdog API: Process Registry Integration

The task watchdog tracks constitution rules for long-running processes.

#### CLI Command: task-watchdog register

Register a background process with constitution enforcement:

```bash
# Register process with constitution rules
dev-kid task-watchdog register TASK-001 \
    --command "python scripts/migration.py" \
    --rules "TYPE_HINTS_REQUIRED,DOCSTRINGS_REQUIRED,NO_PRINT_STATEMENTS"
```

**Arguments**:
- `TASK-001`: Task ID from execution plan
- `--command`: Shell command to execute
- `--rules`: Comma-separated list of constitution rules

#### Process Registry Schema

The watchdog stores process metadata in `.claude/task_timers.json`:

```json
{
  "running_tasks": {
    "TASK-001": {
      "description": "Run database migration",
      "started_at": "2025-01-11T10:30:00Z",
      "status": "running",
      "process_id": 12345,
      "command": "python scripts/migration.py",
      "constitution_rules": [
        "TYPE_HINTS_REQUIRED",
        "DOCSTRINGS_REQUIRED",
        "NO_PRINT_STATEMENTS"
      ]
    }
  },
  "completed_tasks": {
    "TASK-002": {
      "description": "Generate API docs",
      "started_at": "2025-01-11T09:15:00Z",
      "completed_at": "2025-01-11T09:20:00Z",
      "duration_seconds": 300,
      "constitution_validation": {
        "valid": true,
        "violations": [],
        "metrics": {"total_violations": 0}
      }
    }
  }
}
```

**Key Fields**:
- `constitution_rules`: Rules to enforce when process completes
- `constitution_validation`: Validation result after completion

#### Python API: Watchdog Process Registration

```python
from cli.task_watchdog import TaskWatchdog

watchdog = TaskWatchdog()

# Register process with constitution
watchdog.register_process(
    task_id="TASK-001",
    command="python scripts/migration.py",
    description="Run database migration",
    constitution_rules=["TYPE_HINTS_REQUIRED", "DOCSTRINGS_REQUIRED"]
)

# Watchdog automatically validates constitution when process completes
# Validation result stored in task_timers.json
```

### Complete Integration Example

This example shows the full workflow from task definition to constitution-enforced checkpoint.

#### Step 1: Define Tasks with Constitution Rules

**tasks.md**:
```markdown
# Tasks

## Phase 1: API Implementation
- [ ] Implement user authentication in `src/auth.py`
  **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED, NO_BARE_EXCEPT

- [ ] Create user models in `src/models.py`
  **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED

- [ ] Write API tests in `tests/test_api.py`
  **Constitution**: NO_PRINT_STATEMENTS, DOCSTRINGS_REQUIRED
```

#### Step 2: Orchestrate into Waves

```bash
dev-kid orchestrate "Phase 1"
```

**Generated execution_plan.json** (excerpt):
```json
{
  "waves": [
    {
      "wave_id": 1,
      "tasks": [
        {
          "task_id": "TASK-001",
          "description": "Implement user authentication in `src/auth.py`",
          "constitution_rules": [
            "TYPE_HINTS_REQUIRED",
            "DOCSTRINGS_REQUIRED",
            "NO_BARE_EXCEPT"
          ]
        }
      ],
      "checkpoint_after": {
        "validate_constitution": true
      }
    }
  ]
}
```

#### Step 3: Execute with Constitution Enforcement

```bash
# Start watchdog
dev-kid watchdog-start

# Execute waves
dev-kid execute
```

**Wave Execution Flow**:

1. **Task Execution**: Agent implements `src/auth.py`
2. **Mark Complete**: Agent updates `tasks.md` with `[x]`
3. **Checkpoint Trigger**: Wave executor calls `execute_checkpoint()`
4. **Constitution Validation**:
   ```python
   constitution = Constitution()
   output = read_file("src/auth.py")
   result = constitution.validate_output(
       output=output,
       task_id="TASK-001",
       rules=["TYPE_HINTS_REQUIRED", "DOCSTRINGS_REQUIRED", "NO_BARE_EXCEPT"]
   )
   ```

#### Step 4: Violation Detection

**Scenario**: `src/auth.py` missing type hints

**Validation Result**:
```json
{
  "valid": false,
  "violations": [
    {
      "rule": "TYPE_HINTS_REQUIRED",
      "severity": "error",
      "message": "Function authenticate() missing return type hint",
      "file": "src/auth.py",
      "line": 15
    },
    {
      "rule": "TYPE_HINTS_REQUIRED",
      "severity": "error",
      "message": "Parameter 'username' missing type hint",
      "file": "src/auth.py",
      "line": 15
    }
  ]
}
```

#### Step 5: Checkpoint Blocking

**Console Output**:
```
❌ Wave 1 Checkpoint FAILED - Constitution Violations Detected

Violations:
  TASK-001 (src/auth.py):
    - [ERROR] TYPE_HINTS_REQUIRED: Function authenticate() missing return type hint (line 15)
    - [ERROR] TYPE_HINTS_REQUIRED: Parameter 'username' missing type hint (line 15)

Action Required: Fix violations and re-run checkpoint
```

**System Behavior**:
- Wave 1 progression BLOCKED
- No git commit created
- Task marked incomplete in `tasks.md`: `- [ ]`
- Violations logged to `.claude/activity_stream.md`
- Agent receives violation report for remediation

#### Step 6: Fix and Re-Validate

Agent fixes `src/auth.py`:
```python
def authenticate(username: str, password: str) -> bool:
    """Authenticate user with username and password.

    Args:
        username: User's username
        password: User's password

    Returns:
        True if authentication successful, False otherwise
    """
    try:
        # Authentication logic
        return verify_credentials(username, password)
    except ValueError as e:
        logger.error(f"Authentication error: {e}")
        return False
```

Agent marks task complete: `- [x]` and re-runs checkpoint:

```bash
dev-kid execute
```

**Validation Result**:
```json
{
  "valid": true,
  "violations": [],
  "metrics": {"total_violations": 0}
}
```

**Console Output**:
```
✅ Wave 1 Checkpoint PASSED
   - Constitution validation: 0 violations
   - Git commit: a3f9c21 "Wave 1: User authentication implementation"
   - Progress updated: 1/3 tasks complete
```

**System Behavior**:
- Wave 1 complete - proceed to Wave 2
- Git checkpoint created
- Memory Bank updated with progress
- Activity stream logged

### Testing Constitution Integration

Reference implementation available in `tests/test_constitution_integration.py`:

```python
import unittest
from cli.orchestrator import Orchestrator
from cli.wave_executor import WaveExecutor
from speckit.constitution import Constitution

class TestConstitutionIntegration(unittest.TestCase):

    def test_orchestrator_extracts_constitution_rules(self):
        """Verify orchestrator extracts constitution metadata from tasks.md"""
        orchestrator = Orchestrator()
        tasks = orchestrator.parse_tasks("tasks.md")

        # Check rule extraction
        task = tasks[0]
        self.assertIn("constitution_rules", task)
        self.assertEqual(
            task["constitution_rules"],
            ["TYPE_HINTS_REQUIRED", "DOCSTRINGS_REQUIRED"]
        )

    def test_wave_executor_validates_constitution(self):
        """Verify wave executor blocks checkpoint on violations"""
        executor = WaveExecutor()

        # Execute wave with constitution violations
        wave = {
            "wave_id": 1,
            "tasks": [{
                "task_id": "TASK-001",
                "files_affected": ["src/bad_code.py"],
                "constitution_rules": ["TYPE_HINTS_REQUIRED"]
            }]
        }

        checkpoint = executor.execute_checkpoint(wave)

        # Verify checkpoint blocked
        self.assertEqual(checkpoint["status"], "failed")
        self.assertGreater(len(checkpoint["constitution_violations"]), 0)
        self.assertIsNone(checkpoint["git_commit"])

    def test_watchdog_tracks_constitution_rules(self):
        """Verify watchdog stores constitution metadata"""
        watchdog = TaskWatchdog()

        watchdog.register_process(
            task_id="TASK-001",
            command="python script.py",
            constitution_rules=["TYPE_HINTS_REQUIRED"]
        )

        # Verify rules stored
        state = watchdog.load_state()
        task = state["running_tasks"]["TASK-001"]
        self.assertEqual(
            task["constitution_rules"],
            ["TYPE_HINTS_REQUIRED"]
        )

if __name__ == "__main__":
    unittest.main()
```

**Running Tests**:
```bash
# Run all constitution tests
python3 -m pytest tests/test_constitution_integration.py -v

# Run specific test
python3 -m pytest tests/test_constitution_integration.py::TestConstitutionIntegration::test_checkpoint_blocking -v
```

### Constitution Enforcement Best Practices

1. **Specify Rules Per Task**: Different tasks may require different quality standards
   ```markdown
   - [ ] Core API logic in `src/api.py`
     **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED, NO_BARE_EXCEPT

   - [ ] Utility script in `scripts/migrate.py`
     **Constitution**: NO_PRINT_STATEMENTS
   ```

2. **Progressive Enforcement**: Start with warnings, escalate to errors
   ```markdown
   # Phase 1: Implement features (lenient)
   - [ ] Create prototype in `prototype.py`
     **Constitution**: NO_PRINT_STATEMENTS

   # Phase 2: Production-ready (strict)
   - [ ] Refine production code in `src/api.py`
     **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED, NO_BARE_EXCEPT, PEP8_NAMING
   ```

3. **Custom Rules**: Create project-specific rules in `~/.speckit/rules/custom/`
   ```python
   # ~/.speckit/rules/custom/no_todo_comments.py
   {
       "id": "NO_TODO_COMMENTS",
       "severity": "warning",
       "pattern": r"# TODO:",
       "message": "TODO comments should be tracked in tasks.md"
   }
   ```

4. **Automated Remediation**: Constitution violations trigger agent self-correction
   - Agent receives violation report
   - Fixes code to comply with rules
   - Re-runs checkpoint
   - Proceeds only after validation passes

5. **Integration with CI/CD**: Constitution checks can run in CI pipelines
   ```bash
   # .github/workflows/constitution.yml
   - name: Validate Constitution
     run: |
       dev-kid validate-constitution
   ```

### API Summary

| Component | Key API | Purpose |
|-----------|---------|---------|
| **Constitution** | `validate_output()` | Validate task output against rules |
| **Orchestrator** | `**Constitution**: RULES` | Embed rules in tasks.md |
| **Wave Executor** | `execute_checkpoint()` | Validate at checkpoint boundaries |
| **Watchdog** | `task-watchdog register --rules` | Track constitution for processes |

**Integration Points**:
1. tasks.md → Orchestrator: Rule extraction
2. execution_plan.json → Wave Executor: Rule metadata
3. Wave Executor → Constitution: Validation
4. Checkpoint → Agent: Violation reporting
5. Watchdog → Constitution: Process validation

For detailed implementation examples, see `tests/test_constitution_integration.py`.

## Advanced Features

### Custom Wave Strategies

Edit execution_plan.json:
```json
{
  "waves": [
    {
      "wave_id": 1,
      "strategy": "parallel",
      "tasks": [...]
    },
    {
      "wave_id": 2,
      "strategy": "sequential",
      "rationale": "Database migrations must run in order",
      "tasks": [...]
    }
  ]
}
```

### Multi-User Support

Memory Bank has per-user private spaces:
```
memory-bank/
├── shared/              # Team knowledge
│   ├── projectbrief.md
│   ├── systemPatterns.md
│   └── techContext.md
└── private/
    ├── alice/           # Alice's context
    │   ├── activeContext.md
    │   └── progress.md
    └── bob/             # Bob's context
        ├── activeContext.md
        └── progress.md
```

### Git Hook Integration

Auto-installed post-commit hook:
```bash
#!/bin/bash
# Logs commit to activity stream
echo "### $(date) - Git Checkpoint" >> .claude/activity_stream.md
echo "- Commit: $(git rev-parse --short HEAD)" >> .claude/activity_stream.md

# Updates system bus
python3 -c "import json; ..."
```

## Documentation

- **DEV_KID.md**: Complete implementation guide (1,500+ lines)
- **skills/**: Individual skill documentation
- **templates/**: Template file reference

## License

MIT License - See LICENSE file

## Contributing

Contributions welcome! Please:
1. Fork the repo
2. Create feature branch
3. Run `dev-kid validate` before committing
4. Submit PR with description

---

**Dev-Kid v2.0** | Enhanced Planning System | Claude Code Compatible | Context Compression Resilient

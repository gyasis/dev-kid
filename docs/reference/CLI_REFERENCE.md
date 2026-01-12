# Dev-Kid CLI Reference

**Version**: 2.0.0
**Last Updated**: 2026-01-05

Complete command-line interface reference for the dev-kid development workflow system.

---

## Table of Contents

1. [Overview](#overview)
2. [Global Options](#global-options)
3. [Core Commands](#core-commands)
4. [Orchestration Commands](#orchestration-commands)
5. [Task Watchdog Commands](#task-watchdog-commands)
6. [Memory Commands](#memory-commands)
7. [System Commands](#system-commands)
8. [Exit Codes](#exit-codes)
9. [Environment Variables](#environment-variables)
10. [Usage Examples](#usage-examples)

---

## Overview

The `dev-kid` CLI provides a unified interface to the complete development workflow system. All commands follow the pattern:

```
dev-kid [COMMAND] [ARGUMENTS] [OPTIONS]
```

### Installation Location

- CLI: `/usr/local/bin/dev-kid` (symlink to `~/.dev-kid/cli/dev-kid`)
- Implementation: `~/.dev-kid/cli/dev-kid` (Bash script)

### Quick Help

```bash
dev-kid help           # Show all commands
dev-kid version        # Show version
dev-kid status         # Show system status
```

---

## Global Options

Options that work with most commands:

### `--verbose`

Enable verbose output with detailed progress information.

```bash
dev-kid --verbose orchestrate "Phase 1"
```

**Output**: Shows parsing details, dependency analysis steps, wave creation logic.

### `--dry-run`

Show what would happen without executing the operation.

```bash
dev-kid --dry-run execute
```

**Output**: Displays execution plan without running tasks or creating commits.

---

## Core Commands

### `init`

Initialize dev-kid in a project directory.

#### Synopsis

```bash
dev-kid init [PATH]
```

#### Arguments

- `PATH` (optional): Project directory path (default: current directory)

#### Description

Creates complete project structure:
- Memory Bank (`memory-bank/shared/`, `memory-bank/private/$USER/`)
- Context Protection (`.claude/` directory with JSON state files)
- Session snapshots directory
- Git hooks (post-commit)
- Initial git commit (if not already initialized)
- Template files for Memory Bank

#### Examples

```bash
# Initialize in current directory
dev-kid init

# Initialize in specific directory
dev-kid init /path/to/project

# Initialize with project path option
dev-kid init --project-path ~/projects/myapp
```

#### Exit Codes

- `0`: Success
- `1`: Directory creation failed
- `2`: Git initialization failed

#### Created Structure

```
project/
├── memory-bank/
│   ├── shared/
│   │   ├── projectbrief.md
│   │   ├── systemPatterns.md
│   │   ├── techContext.md
│   │   └── productContext.md
│   └── private/$USER/
│       ├── activeContext.md
│       ├── progress.md
│       └── worklog.md
├── .claude/
│   ├── active_stack.md
│   ├── activity_stream.md
│   ├── AGENT_STATE.json
│   ├── system_bus.json
│   └── session_snapshots/
└── .git/
    └── hooks/
        └── post-commit
```

---

### `orchestrate`

Convert linear task list into wave-based execution plan.

#### Synopsis

```bash
dev-kid orchestrate [PHASE_ID] [OPTIONS]
```

#### Arguments

- `PHASE_ID` (optional): Phase identifier for the execution plan (default: "default")

#### Options

- `--tasks-file FILE`: Custom tasks file (default: `tasks.md`)
- `--phase-id ID`: Same as positional PHASE_ID argument

#### Description

Parses `tasks.md`, analyzes dependencies, groups tasks into parallel execution waves, and generates `execution_plan.json`.

**Algorithm**:
1. Parse tasks from tasks.md
2. Extract file references and explicit dependencies
3. Build dependency graph (explicit + implicit from file locks)
4. Group tasks into waves (no dependencies within wave, no file conflicts)
5. Generate JSON execution plan

#### Examples

```bash
# Orchestrate with default phase
dev-kid orchestrate

# Orchestrate with specific phase
dev-kid orchestrate "Phase 7: Workflow State"

# Custom tasks file
dev-kid orchestrate --tasks-file custom_tasks.md

# With phase ID option
dev-kid orchestrate --phase-id "Sprint 3"
```

#### Output

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
      - T002: Configure database connection
      ...
   Wave 2 (SEQUENTIAL_MERGE): 3 task(s)
      ...
```

#### Exit Codes

- `0`: Success
- `1`: tasks.md not found
- `2`: Circular dependency detected
- `3`: JSON write failed

---

### `execute`

Execute waves from execution plan with checkpoints.

#### Synopsis

```bash
dev-kid execute
```

#### Description

Executes waves sequentially from `execution_plan.json`. For each wave:
1. Display wave info (strategy, tasks, rationale)
2. Agents execute tasks (parallel or sequential based on strategy)
3. Verify all tasks marked `[x]` in tasks.md
4. Update Memory Bank progress.md
5. Create git checkpoint
6. Proceed to next wave

**Halts execution** if verification fails (task not marked complete).

#### Examples

```bash
# Execute all waves
dev-kid execute
```

#### Output

```
🚀 Starting wave execution...

📋 Phase: Phase 7: Workflow State
🌊 Total waves: 4

🌊 Executing Wave 1 (PARALLEL_SWARM)...
   Rationale: Wave 1: 5 independent task(s) with no file conflicts
   Tasks: 5
   Strategy: Parallel execution
      🤖 Agent Developer: T001 - Set up project structure
      🤖 Agent Developer: T002 - Configure database connection
      ...
   ⏳ Wave 1 in progress...
   ℹ️  Agents must mark tasks complete in tasks.md before wave ends

🔍 Checkpoint after Wave 1...
   Step 1: memory-bank-keeper validates tasks.md...
   ✅ T001: Verified complete
   ✅ T002: Verified complete
   ...
   ✅ All tasks verified complete
   Step 2: memory-bank-keeper updates progress.md...
   Step 3: git-version-manager creates checkpoint...
✅ Checkpoint 1 complete

...

✅ All waves complete!
```

#### Exit Codes

- `0`: All waves completed successfully
- `1`: execution_plan.json not found
- `2`: Checkpoint verification failed
- `3`: Git commit failed

---

### `checkpoint`

Create semantic git checkpoint with Memory Bank sync.

#### Synopsis

```bash
dev-kid checkpoint [MESSAGE]
```

#### Arguments

- `MESSAGE` (optional): Checkpoint description (default: "Checkpoint - YYYY-MM-DD HH:MM:SS")

#### Description

Creates a checkpoint by:
1. Syncing Memory Bank (calls sync_memory.sh)
2. Staging all changes (`git add .`)
3. Creating commit with standardized format
4. Including timestamp and Claude co-author attribution

#### Examples

```bash
# Default checkpoint
dev-kid checkpoint

# With custom message
dev-kid checkpoint "Feature complete: user authentication"

# Using quotes for multi-word message
dev-kid checkpoint "API endpoints implemented and tested"
```

#### Commit Message Format

```
[CHECKPOINT] {MESSAGE}

{TIMESTAMP}
Generated by: dev-kit checkpoint skill

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

#### Output

```
📸 Creating checkpoint: Feature complete

💾 Syncing Memory Bank...
   Updating activeContext.md...
   Updating progress.md from tasks.md...
✅ Memory Bank synced

✅ Checkpoint created: a3f2c1b
```

#### Exit Codes

- `0`: Success
- `1`: Git staging failed
- `2`: No changes to commit (info message, not error)

---

### `sync-memory`

Update Memory Bank with current project state.

#### Synopsis

```bash
dev-kid sync-memory
```

#### Description

Synchronizes Memory Bank files with current state:
1. Extract git changes since last commit
2. Update `activeContext.md` with recent changes and modified files
3. Calculate progress from tasks.md
4. Update `progress.md` with task completion metrics
5. Append sync event to activity stream

#### Examples

```bash
# Sync Memory Bank
dev-kid sync-memory
```

#### Files Updated

- `memory-bank/private/$USER/activeContext.md`: Current focus and recent changes
- `memory-bank/private/$USER/progress.md`: Task completion metrics
- `.claude/activity_stream.md`: Sync event logged

#### Output

```
💾 Syncing Memory Bank...
   Updating activeContext.md...
   Updating progress.md from tasks.md...
✅ Memory Bank synced
```

#### Exit Codes

- `0`: Success
- `1`: Memory Bank directories not found
- `2`: tasks.md parsing failed

---

### `verify`

Run anti-hallucination verification on task plan.

#### Synopsis

```bash
dev-kid verify [FILE]
```

#### Arguments

- `FILE` (optional): File to verify (default: `task_plan.md`)

#### Description

Verifies that file references in task plan exist:
1. Extract file references (backtick-wrapped paths)
2. Check each file exists in filesystem
3. Warn about non-existent functions (informational only)
4. Report hallucination errors

Prevents agents from referencing non-existent files in implementation plans.

#### Examples

```bash
# Verify default task_plan.md
dev-kid verify

# Verify custom file
dev-kid verify implementation_plan.md
```

#### Output (Success)

```
🔍 Running anti-hallucination verification...
   Checking file references...
   ✅ Verified: src/app.py
   ✅ Verified: config/database.yml
   ✅ Verified: tests/test_api.py
   Checking function references...
   ⚠️  WARNING: Function 'new_function' not found in codebase
✅ Verification passed
```

#### Output (Failure)

```
🔍 Running anti-hallucination verification...
   Checking file references...
   ✅ Verified: src/app.py
   ❌ HALLUCINATION: File does not exist: src/missing.py
   ✅ Verified: tests/test_api.py

❌ Verification failed: 1 hallucinated file(s) detected
   Update plan to reference existing files
```

#### Exit Codes

- `0`: All references verified
- `1`: Hallucinated files detected
- `2`: Target file not found

---

### `recall`

Resume from last session snapshot.

#### Synopsis

```bash
dev-kid recall
```

#### Description

Loads latest session snapshot and displays:
- Session timestamp
- Current phase
- Progress metrics (tasks completed/total)
- Mental state (last active context)
- Next steps
- Active blockers

Provides resumption guidance for starting new session.

#### Examples

```bash
# Recall last session
dev-kid recall
```

#### Output

```
🧠 Recalling last session...

📊 Session Restored from: 2026-01-05T14:30:00

📌 Phase: Feature implementation: user auth
📈 Progress: 12/20 tasks (60%)

💭 Mental State:
Working on user authentication endpoint
Recent changes: Added JWT token generation
Modified files: src/auth.py, tests/test_auth.py

🎯 Next Steps:
   - Review progress.md
   - Update projectbrief.md if needed
   - Continue next task from tasks.md

✅ Session context restored

Ready to continue? Run:
  dev-kid orchestrate    # Plan remaining tasks
  dev-kid execute         # Execute waves
  dev-kid sync-memory    # Update Memory Bank
```

#### Exit Codes

- `0`: Session restored successfully
- `1`: No previous session found (info message)

---

### `finalize`

Create session snapshot and final checkpoint.

#### Synopsis

```bash
dev-kid finalize
```

#### Description

Finalizes current session by:
1. Syncing Memory Bank
2. Creating session snapshot JSON
3. Capturing progress, git state, next steps, blockers
4. Creating symlink to latest snapshot
5. Creating git checkpoint

Session snapshot includes:
- Session ID and timestamp
- Mental state (active context)
- Current phase
- Progress percentage
- Tasks completed/total
- Next steps
- Blockers
- Git commits
- Modified files
- System state

#### Examples

```bash
# Finalize session
dev-kid finalize
```

#### Output

```
📦 Finalizing session...

💾 Syncing Memory Bank...
   Updating activeContext.md...
   Updating progress.md from tasks.md...
✅ Memory Bank synced

📸 Creating checkpoint: Session finalized - 12/20 tasks complete
✅ Checkpoint created: d4e5f6a

✅ Session finalized
   Snapshot: .claude/session_snapshots/snapshot_2026-01-05_14-30-00.json
   Progress: 12/20 tasks (60%)

   Next session: Run 'dev-kid recall' to resume
```

#### Exit Codes

- `0`: Session finalized successfully
- `1`: Snapshot creation failed
- `2`: Git checkpoint failed

---

## Orchestration Commands

### `waves`

Display current execution plan waves.

#### Synopsis

```bash
dev-kid waves
```

#### Description

Parses `execution_plan.json` and displays wave summary with:
- Phase ID
- Total wave count
- Each wave: ID, strategy, task count, rationale

#### Examples

```bash
# Show waves
dev-kid waves
```

#### Output

```
🌊 Execution Plan Waves

📋 Phase: Phase 7: Workflow State
🌊 Waves: 4

Wave 1 (PARALLEL_SWARM):
  Tasks: 5
  Rationale: Wave 1: 5 independent task(s) with no file conflicts

Wave 2 (SEQUENTIAL_MERGE):
  Tasks: 3
  Rationale: Wave 2: 3 independent task(s) with no file conflicts

Wave 3 (PARALLEL_SWARM):
  Tasks: 7
  Rationale: Wave 3: 7 independent task(s) with no file conflicts

Wave 4 (SEQUENTIAL_MERGE):
  Tasks: 1
  Rationale: Wave 4: 1 independent task(s) with no file conflicts
```

#### Exit Codes

- `0`: Success
- `1`: execution_plan.json not found

---

## Task Watchdog Commands

### `watchdog-start`

Start background task monitoring process.

#### Synopsis

```bash
dev-kid watchdog-start
```

#### Description

Starts Task Watchdog as background process that:
- Checks every 5 minutes for running tasks
- Syncs with tasks.md to detect completions
- Warns if tasks exceed 7-minute guideline (investigate what's happening)
- Detects stalled tasks (>15 min no activity)
- Task process continues until marked complete (doesn't auto-stop)
- Persists state to `.claude/task_timers.json`
- Survives context compression

Process runs until stopped with `watchdog-stop`.

#### Examples

```bash
# Start watchdog
dev-kid watchdog-start
```

#### Output

```
🐕 Starting Task Watchdog
   Monitoring tasks every 5 minutes...
   Press Ctrl+C to stop

✅ Watchdog started (PID: 12345)
   To stop: dev-kid watchdog-stop
```

#### Exit Codes

- `0`: Watchdog started successfully

---

### `watchdog-stop`

Stop background watchdog process.

#### Synopsis

```bash
dev-kid watchdog-stop
```

#### Description

Kills running Task Watchdog process by finding and terminating `task_watchdog.py run` process.

#### Examples

```bash
# Stop watchdog
dev-kid watchdog-stop
```

#### Output

```
🛑 Stopping Task Watchdog
✅ Watchdog stopped
```

or

```
🛑 Stopping Task Watchdog
⚠️  No watchdog running
```

#### Exit Codes

- `0`: Success (watchdog stopped or not running)

---

### `watchdog-check`

Run one-time task check without continuous monitoring.

#### Synopsis

```bash
dev-kid watchdog-check
```

#### Description

Performs single check cycle:
1. Load state from disk
2. Sync with tasks.md
3. Check for long-running tasks
4. Check for forgotten tasks
5. Generate warnings
6. Save state

Useful for manual monitoring without background process.

#### Examples

```bash
# Check tasks
dev-kid watchdog-check
```

#### Output

```
🔍 Running task check

🔍 Watchdog check #1 - 14:30:45
   Running tasks: 2
   Completed tasks: 5
   Warnings: 1

⚠️  TASK-003 running for 1h 15m
```

#### Exit Codes

- `0`: Check completed successfully

---

### `watchdog-report`

Generate task timing report.

#### Synopsis

```bash
dev-kid watchdog-report
```

#### Description

Displays comprehensive task timing report:
- Running tasks with duration
- Completed tasks with duration
- Total and average time
- Active warnings

#### Examples

```bash
# Generate report
dev-kid watchdog-report
```

#### Output

```
📊 Task Timing Report
============================================================

⏱️  Running Tasks (2)
  TASK-003: Implement user authentication
    Started: 2026-01-05 13:15
    Duration: 1h 15m

  TASK-007: Write API tests
    Started: 2026-01-05 14:00
    Duration: 30m

✅ Completed Tasks (5)
  TASK-001: Set up project structure
    Duration: 45m
  TASK-002: Configure database
    Duration: 1h 5m
  TASK-004: Create models
    Duration: 35m
  TASK-005: Build API endpoints
    Duration: 2h 10m
  TASK-006: Add middleware
    Duration: 50m

  Total time: 5h 25m
  Average time per task: 1h 5m

⚠️  Active Warnings (1)
  long_running: TASK-003
    Implement user authentication
```

#### Exit Codes

- `0`: Report generated successfully

---

### `task-start`

Start timer for a task.

#### Synopsis

```bash
dev-kid task-start TASK_ID "DESCRIPTION"
```

#### Arguments

- `TASK_ID` (required): Unique task identifier (e.g., "TASK-001")
- `DESCRIPTION` (required): Task description (must be quoted if contains spaces)

#### Description

Records task start time in watchdog state file. Task will be monitored for completion and duration.

#### Examples

```bash
# Start task timer
dev-kid task-start TASK-001 "Implement user authentication"

# With complex description
dev-kid task-start API-042 "Build REST endpoint for user profile updates"
```

#### Output

```
⏱️  Started timer for TASK-001: Implement user authentication
```

#### Exit Codes

- `0`: Timer started successfully
- `1`: Missing required arguments

---

### `task-complete`

Mark task as complete and record timing.

#### Synopsis

```bash
dev-kid task-complete TASK_ID
```

#### Arguments

- `TASK_ID` (required): Task identifier to complete

#### Description

Marks task complete by:
1. Removing from running tasks
2. Calculating duration
3. Adding to completed tasks with timing
4. Persisting state to disk

#### Examples

```bash
# Complete task
dev-kid task-complete TASK-001
```

#### Output

```
✅ Completed TASK-001 in 1h 15m
```

or (if not found)

```
⚠️  Warning: Task TASK-001 not found in running tasks
```

#### Exit Codes

- `0`: Task completed successfully
- `1`: Missing task ID argument

---

## Memory Commands

### `memory-status`

Show Memory Bank health and status.

#### Synopsis

```bash
dev-kid memory-status
```

#### Description

Displays Memory Bank health information:
- Shared files status
- Private files status
- Last update timestamps
- File sizes

#### Examples

```bash
# Check memory status
dev-kid memory-status
```

#### Output

```
📊 Memory Bank Status

Shared Knowledge:
  ✅ projectbrief.md (2.3 KB, updated 2026-01-05 10:30)
  ✅ systemPatterns.md (1.8 KB, updated 2026-01-04 16:45)
  ✅ techContext.md (1.2 KB, updated 2026-01-05 09:15)
  ✅ productContext.md (1.5 KB, updated 2026-01-03 14:20)

Private Context (user: alice):
  ✅ activeContext.md (0.8 KB, updated 2026-01-05 14:30)
  ✅ progress.md (1.1 KB, updated 2026-01-05 14:30)
  ✅ worklog.md (3.4 KB, updated 2026-01-05 14:00)

Overall Health: ✅ Healthy
```

#### Exit Codes

- `0`: Memory Bank healthy
- `1`: Missing files detected

---

### `memory-diff`

Show changes since last Memory Bank sync.

#### Synopsis

```bash
dev-kid memory-diff
```

#### Description

Displays git diff for Memory Bank files since last commit, showing what will be updated on next sync.

#### Examples

```bash
# Show memory diff
dev-kid memory-diff
```

#### Output

```
📋 Memory Bank Changes Since Last Sync

Modified Files:
  M memory-bank/private/alice/activeContext.md
  M memory-bank/private/alice/progress.md

Diff:
--- a/memory-bank/private/alice/progress.md
+++ b/memory-bank/private/alice/progress.md
@@ -5,7 +5,7 @@
 ## Overall Progress
 - Total Tasks: 20
-- Completed: 10 ✅
+- Completed: 12 ✅
```

#### Exit Codes

- `0`: Diff displayed successfully
- `1`: Git not initialized

---

## System Commands

### `validate`

Validate system integrity.

#### Synopsis

```bash
dev-kid validate
```

#### Description

Runs comprehensive system validation:
1. Check Memory Bank structure
2. Check Context Protection files
3. Check Skills installation
4. Check Git status
5. Report errors and warnings

Delegates to `maintain_integrity.sh` skill.

#### Examples

```bash
# Validate system
dev-kid validate
```

#### Output

```
🔧 Validating system integrity...
   Checking Memory Bank...
   Checking Context Protection...
   Checking Skills...
   ✅ Skills installed: 6
   Checking Git...
   ✅ Git initialized
✅ System integrity validated
```

or (if errors found)

```
🔧 Validating system integrity...
   Checking Memory Bank...
   ❌ Missing: memory-bank/shared/projectbrief.md
   Checking Context Protection...
   ❌ Missing: .claude/AGENT_STATE.json

❌ Integrity check failed: 2 error(s)
   Run 'dev-kid init' to repair
```

#### Exit Codes

- `0`: System valid
- `1`: Validation errors detected

---

### `status`

Show complete dev-kid system status.

#### Synopsis

```bash
dev-kid status
```

#### Description

Displays comprehensive system status:
- Memory Bank: Initialization status
- Context Protection: Enabled/disabled
- Task Watchdog: Running/completed tasks count
- Skills: Installation count
- Git: Initialization and commit count
- Execution Plan: Wave count

#### Examples

```bash
# Show status
dev-kid status
```

#### Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DEV-KID v2.0.0 - Claude Code Development Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Memory Bank: Initialized
✅ Context Protection: Enabled
✅ Task Watchdog: Active
   Running: 2 | Completed: 5
✅ Skills: 6 installed
✅ Git: Initialized
   Commits: 42
✅ Execution Plan: 4 waves
```

#### Exit Codes

- `0`: Status displayed successfully

---

### `version`

Show dev-kid version.

#### Synopsis

```bash
dev-kid version
```

#### Description

Displays current version number.

#### Examples

```bash
# Show version
dev-kid version
```

#### Output

```
dev-kid v2.0.0
```

#### Exit Codes

- `0`: Version displayed

---

### `help`

Show help information.

#### Synopsis

```bash
dev-kid help
dev-kid -h
dev-kid --help
```

#### Description

Displays complete command reference with usage examples.

#### Examples

```bash
# Show help
dev-kid help
```

#### Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DEV-KID v2.0.0 - Claude Code Development Workflow
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Usage: dev-kid [COMMAND] [OPTIONS]

CORE COMMANDS:
  init [PATH]              Initialize dev-kid in project
  orchestrate [PHASE]      Convert tasks.md into wave execution plan
  execute                  Execute waves from execution_plan.json
  ... (full command list)
```

#### Exit Codes

- `0`: Help displayed

---

## Exit Codes

Standard exit codes used across all commands:

| Code | Meaning |
|------|---------|
| 0    | Success |
| 1    | General error (file not found, validation failed) |
| 2    | Configuration error (missing dependencies, invalid setup) |
| 3    | Execution error (git failed, JSON write failed) |

---

## Environment Variables

### `DEV_KID_ROOT`

**Description**: Installation directory root
**Default**: `~/.dev-kid`
**Usage**: Set to custom location if non-standard installation

```bash
export DEV_KID_ROOT=/opt/dev-kid
```

### `USER`

**Description**: Current user (used for Memory Bank private directory)
**Default**: Output of `whoami`
**Usage**: Automatically set, no manual configuration needed

---

## Usage Examples

### Complete Workflow

```bash
# 1. Initialize project
cd ~/projects/myapp
dev-kid init

# 2. Create task list
cat > tasks.md << 'EOF'
# Tasks

- [ ] Set up FastAPI project
- [ ] Create database models
- [ ] Build API endpoints
- [ ] Write tests
EOF

# 3. Create execution plan
dev-kid orchestrate "Sprint 1"

# 4. Review waves
dev-kid waves

# 5. Start task monitoring
dev-kid watchdog-start

# 6. Execute tasks
dev-kid execute

# 7. Create checkpoint
dev-kid checkpoint "Sprint 1 complete"

# 8. Check status
dev-kid status

# 9. Finalize session
dev-kid finalize

# 10. Stop watchdog
dev-kid watchdog-stop
```

### Daily Workflow

```bash
# Morning: Resume from last session
dev-kid recall

# Validate system
dev-kid validate

# Work on tasks...

# Periodic: Sync memory
dev-kid sync-memory

# Create checkpoints as tasks complete
dev-kid checkpoint "Feature X complete"

# Evening: Finalize session
dev-kid finalize
```

### Task Tracking Workflow

```bash
# Start watchdog for monitoring
dev-kid watchdog-start

# Start task timer
dev-kid task-start AUTH-001 "Implement JWT authentication"

# Work on task...

# Complete task
dev-kid task-complete AUTH-001

# Check timing report
dev-kid watchdog-report

# Stop watchdog
dev-kid watchdog-stop
```

### Debugging Workflow

```bash
# Check overall status
dev-kid status

# Validate system integrity
dev-kid validate

# Check Memory Bank status
dev-kid memory-status

# View memory changes
dev-kid memory-diff

# Verify file references
dev-kid verify task_plan.md

# Check watchdog
dev-kid watchdog-check
```

---

## Color Output

CLI uses color-coded output:
- **Blue**: Headers and section titles
- **Green**: Success messages (✅)
- **Yellow**: Warnings (⚠️)
- **Red**: Errors (❌)

Colors can be disabled by redirecting output or using `NO_COLOR=1` environment variable.

---

## Shell Completion

Bash completion support (future enhancement):

```bash
# Install completion
dev-kid --install-completion

# Usage
dev-kid <TAB>         # Show all commands
dev-kid orch<TAB>     # Complete to "orchestrate"
```

---

**CLI Reference v2.0.0**
Complete command-line interface reference for dev-kid

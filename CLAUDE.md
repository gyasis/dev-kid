# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Dev-Kid v2.0** is a complete development workflow system for Claude Code that provides:
- **Wave-Based Task Orchestration**: Parallel execution with dependency management
- **Memory Bank**: Persistent institutional memory across sessions
- **Context Protection**: Compression-aware state management
- **Task Watchdog**: Background task monitoring that survives context compression
- **Skills Layer**: Auto-activating workflow automation
- **Git Integration**: Semantic checkpoints with verification

## Core Architecture

### Execution Flow

```
tasks.md → orchestrator.py → execution_plan.json → wave_executor.py
                ↓                                         ↓
            Wave Analysis                         Wave Execution + Checkpoints
```

### Key Components

1. **CLI Layer** (`cli/dev-kid`): Bash script that routes commands to Python modules and skills
2. **Orchestrator** (`cli/orchestrator.py`): Converts linear task lists into parallelized wave execution plans
3. **Wave Executor** (`cli/wave_executor.py`): Executes waves sequentially with mandatory checkpoints
4. **Task Watchdog** (`cli/task_watchdog.py`): Background daemon for task monitoring (process-based, survives context compression)
5. **Skills** (`skills/*.sh`): Bash scripts for common workflows (sync_memory, checkpoint, verify_existence, etc.)

### Directory Structure

```
dev-kid/
├── cli/                      # Core CLI and Python modules
│   ├── dev-kid              # Main Bash CLI entry point
│   ├── orchestrator.py      # Task → waves converter
│   ├── wave_executor.py     # Wave execution engine
│   └── task_watchdog.py     # Background task monitor
├── skills/                   # Workflow automation scripts
│   ├── sync_memory.sh       # Update Memory Bank
│   ├── checkpoint.sh        # Create git checkpoint
│   ├── verify_existence.sh  # Anti-hallucination check
│   ├── maintain_integrity.sh # System validation
│   ├── finalize_session.sh  # Session snapshot
│   └── recall.sh            # Resume from snapshot
├── scripts/                  # Installation & initialization
│   ├── install.sh           # System installation
│   └── init.sh              # Per-project scaffold
└── templates/               # Templates for Memory Bank & Context Protection
```

## Development Commands

### Testing the System

```bash
# Manual testing workflow
./scripts/install.sh                    # Install to ~/.dev-kid
dev-kid init /tmp/test-project         # Initialize in test project
cd /tmp/test-project
dev-kid status                          # Verify installation

# Create test tasks
cat > tasks.md << 'EOF'
- [ ] Task 1 affecting file1.py
- [ ] Task 2 affecting file2.py
- [ ] Task 3 affecting file1.py (should be in different wave)
EOF

# Test orchestration
dev-kid orchestrate "Test Phase"
cat execution_plan.json                 # Verify waves are correct

# Test watchdog
dev-kid watchdog-start
dev-kid task-start T001 "Test task"
dev-kid watchdog-check
dev-kid task-complete T001
dev-kid watchdog-stop

# Test skills
dev-kid sync-memory
dev-kid checkpoint "Test checkpoint"
dev-kid verify
dev-kid finalize
dev-kid recall
```

### Testing Python Modules Directly

```bash
# Test orchestrator
python3 cli/orchestrator.py --tasks-file tasks.md --phase-id "Test"

# Test wave executor
python3 cli/wave_executor.py

# Test task watchdog
python3 cli/task_watchdog.py start-task T001 "Test task"
python3 cli/task_watchdog.py check
python3 cli/task_watchdog.py complete-task T001
```

### Running Skills Individually

```bash
# Skills can be executed directly
./skills/sync_memory.sh
./skills/checkpoint.sh "Message"
./skills/verify_existence.sh task_plan.md
./skills/maintain_integrity.sh
```

## Critical Implementation Details

### Wave Orchestration Algorithm

**File Lock Detection**: Tasks that modify the same file CANNOT run in the same wave
- Pattern matching: Extracts file paths from task descriptions using regex
- Backtick convention: File paths in backticks (e.g., `src/file.py`) are guaranteed to be detected
- Implicit dependencies: Same-file tasks are automatically sequenced

**Dependency Analysis**:
- Explicit: "after T123" or "depends on T456" in task description
- Implicit: File lock conflicts create sequential dependencies
- Graph-based: Uses greedy wave assignment algorithm (O(n²) worst case)

### Checkpoint Protocol

**MANDATORY between waves**:
1. Wave executor calls `verify_wave_completion()`
2. Checks tasks.md for `[x]` completion markers
3. If ANY task incomplete → HALT execution
4. Only proceeds if verification passes
5. Updates progress.md via `_update_progress()`
6. Creates git commit via `_git_checkpoint()`

**IMPORTANT**: Agents MUST mark tasks complete in tasks.md (change `[ ]` to `[x]`) before wave ends.

### Task Watchdog Architecture

**Process-Based, Not Token-Based**:
- Runs as background daemon (`python3 task_watchdog.py run`)
- State persisted to `.claude/task_timers.json`
- 5-minute check intervals
- **Task Timing Guidelines**: Tasks should complete within 7 minutes
  - After 7 minutes: Check to see what's going on
  - Task process continues until marked complete (doesn't auto-stop)
  - Watchdog monitors but doesn't interrupt running tasks
- Syncs with tasks.md to auto-detect completion when tasks are marked `[x]`

**State File Schema**:
```json
{
  "running_tasks": {
    "TASK-001": {
      "description": "...",
      "started_at": "ISO8601",
      "status": "running"
    }
  },
  "completed_tasks": {...},
  "warnings": [...]
}
```

### Memory Bank Structure

**6-Tier Architecture**:
- `memory-bank/shared/`: Team knowledge (projectbrief.md, systemPatterns.md, techContext.md, productContext.md)
- `memory-bank/private/$USER/`: Per-user context (activeContext.md, progress.md, worklog.md)

**Update Pattern**:
1. Read current state
2. Extract new information (git diff, tasks.md stats, git log)
3. Generate updated Markdown
4. Write to file
5. Append to activity_stream.md

### Context Protection

**Files in `.claude/`**:
- `active_stack.md`: <500 token current focus
- `activity_stream.md`: Append-only event log
- `AGENT_STATE.json`: Agent coordination state
- `system_bus.json`: Inter-agent messaging
- `task_timers.json`: Watchdog state
- `session_snapshots/*.json`: Recovery points

## Code Patterns & Standards

### Python Code Style

- **Type hints**: All functions have type annotations
- **Dataclasses**: Used for Task and Wave objects
- **Pathlib**: Use `Path()` objects, not string paths
- **Error handling**: Print clear error messages, use `sys.exit(1)` for failures
- **No external dependencies**: Standard library only (json, pathlib, dataclasses, re, subprocess)

### Bash Script Patterns

- **Error handling**: All scripts start with `set -e`
- **User feedback**: Use echo with clear status indicators (✅ ❌ ⚠️  ℹ️)
- **File checks**: Always verify file existence before operations
- **Git operations**: Check if git initialized, handle empty repos gracefully

### JSON Schema Consistency

**execution_plan.json**:
- Must have `execution_plan.phase_id` and `execution_plan.waves[]`
- Each wave has: `wave_id`, `strategy`, `rationale`, `tasks[]`, `checkpoint_after{}`
- Strategy: `PARALLEL_SWARM` or `SEQUENTIAL_MERGE`

**session_snapshots/*.json**:
- Includes: `session_id`, `timestamp`, `mental_state`, `current_phase`, `progress`, `next_steps`, `blockers`, `git_commits`, `files_modified`, `system_state`

## Common Gotchas

### Installation Issues

**Symlink creation**: Requires sudo for `/usr/local/bin/dev-kid`
- Workaround: User can add `~/.dev-kid/cli` to PATH instead

**Skills not found**: Claude Code looks in `~/.claude/skills/planning-enhanced/`
- Ensure install.sh copies skills to correct location

### Git Hooks

**post-commit hook**: Auto-appends to activity_stream.md
- Must be executable: `chmod +x .git/hooks/post-commit`
- Won't fire if hook doesn't exist (silent failure)

### Wave Execution

**Common mistake**: Forgetting to mark tasks as `[x]` in tasks.md
- Wave executor will HALT if verification fails
- Agents must update tasks.md as part of task completion

**File lock over-detection**: Regex may detect file paths that aren't actual files
- Use backticks to explicitly mark file paths: `src/file.py`

### Task Watchdog

**Process management**: Watchdog runs as background process
- Must be manually stopped: `dev-kid watchdog-stop`
- Check if running: `ps aux | grep task_watchdog.py`
- Kill manually if needed: `pkill -f task_watchdog.py`

**State persistence**: Reads/writes `.claude/task_timers.json`
- File corruption can break watchdog (validate JSON)

## Testing Strategy

### Unit Testing (Future)

Python modules are designed for testability:
```bash
pytest cli/test_orchestrator.py     # Test task parsing, dependency analysis
pytest cli/test_wave_executor.py    # Test wave execution logic
pytest cli/test_task_watchdog.py    # Test watchdog state management
```

### Integration Testing

Manual workflow test:
1. Install system
2. Initialize in test project
3. Create tasks.md
4. Run orchestration
5. Verify execution_plan.json structure
6. Execute waves (with manual task completion)
7. Verify git commits and Memory Bank updates

### Skill Testing

Each skill should be testable independently:
```bash
# Create test environment
mkdir /tmp/skill-test
cd /tmp/skill-test
git init
dev-kid init

# Test individual skill
dev-kid sync-memory
# Verify: memory-bank files updated

dev-kid checkpoint "Test"
# Verify: git commit created
```

## Documentation Files

- **README.md**: User-facing quickstart guide
- **DEV_KID.md**: Complete implementation reference (1,680 lines - single-file documentation)
- **ARCHITECTURE.md**: System architecture deep dive
- **CLI_REFERENCE.md**: Command-line interface reference
- **SKILLS_REFERENCE.md**: Skills documentation
- **API.md**: Python API reference
- **CONTRIBUTING.md**: Contribution guidelines
- **DEPENDENCIES.md**: System dependencies and installation

## Important Notes for Claude Code

### When Working on Orchestrator

- Maintain O(n²) complexity or better for dependency analysis
- File lock extraction must handle: backtick paths, plain paths, paths with spaces
- Wave assignment algorithm should be greedy (assign to earliest possible wave)
- Don't modify JSON schema - breaks compatibility with executor

### When Working on Wave Executor

- NEVER skip verification step - data integrity depends on it
- Always check tasks.md for `[x]` completion markers
- Git operations should be safe (no force, no hard reset)
- Handle edge cases: no git repo, no tasks to commit

### When Working on Task Watchdog

- State file must be JSON (for cross-process communication)
- Process must handle SIGINT gracefully (KeyboardInterrupt)
- Time calculations should be UTC-aware
- Sync with tasks.md to detect manual completions

### When Working on Skills

- Keep skills simple and focused (single responsibility)
- All skills should be idempotent (safe to run multiple times)
- Provide clear user feedback (echo status messages)
- Never fail silently - always show errors

### When Working on CLI

- Command routing must be maintainable (simple case statement)
- Validate arguments before delegating to modules
- Provide helpful error messages with next steps
- Color output is optional (respect NO_COLOR environment variable)

## Development Philosophy

**Zero Configuration, Maximum Automation**: System should work with one command install. No manual configuration required.

**Reproducible Across Projects**: Same workflow works for any tech stack, any project size.

**Context Compression Resilient**: All critical state persisted to disk (git, JSON, Markdown). Process-based monitoring survives compression.

**Token Efficient**: Planning overhead <10% of context window. Skills auto-activate without coordination tokens.

**Git-Centric**: Every checkpoint is a git commit. History is source of truth.

**Fail-Safe**: Verification before progression. No silent failures. Clear error messages.

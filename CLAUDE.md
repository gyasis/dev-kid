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

1. **CLI Layer** (`cli/dev-kid`): Bash script that routes commands to Python modules, skills, and Rust binary
2. **Orchestrator** (`cli/orchestrator.py`): Converts linear task lists into parallelized wave execution plans
3. **Wave Executor** (`cli/wave_executor.py`): Executes waves sequentially with mandatory checkpoints
4. **Rust Watchdog** (`rust-watchdog/target/release/task-watchdog`): Blazing-fast process/container monitoring daemon (<3MB, <5ms startup)
5. **Skills** (`skills/*.sh`): Bash scripts for common workflows (sync_memory, checkpoint, verify_existence, etc.)

### Directory Structure

```
dev-kid/
├── cli/                      # Core CLI and Python modules
│   ├── dev-kid              # Main Bash CLI (routes to skills/Python/Rust)
│   ├── orchestrator.py      # Task → waves converter
│   ├── wave_executor.py     # Wave execution engine
│   └── config_manager.py    # Configuration management
├── rust-watchdog/            # High-performance process monitor
│   ├── src/                 # Rust source code
│   │   ├── main.rs          # CLI & daemon
│   │   ├── process.rs       # Native process monitoring
│   │   ├── docker.rs        # Container management
│   │   ├── registry.rs      # State persistence
│   │   └── types.rs         # Data structures
│   └── target/release/
│       └── task-watchdog    # 1.8MB compiled binary
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

# Test Rust watchdog
dev-kid watchdog-start          # Starts Rust daemon
dev-kid watchdog-check          # Runs rehydrate command
dev-kid task-complete T001      # Kills task via Rust binary
dev-kid watchdog-report         # Shows resource usage
dev-kid watchdog-stop           # Stops daemon

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

# Test Rust watchdog directly
cd rust-watchdog && cargo build --release
./target/release/task-watchdog --version
./target/release/task-watchdog stats
./target/release/task-watchdog rehydrate
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

### Rust Task Watchdog Architecture

**Blazing Fast, Process-Based Monitoring** (Rust Implementation):
- Binary: `rust-watchdog/target/release/task-watchdog` (1.8MB)
- Performance: <3MB memory, <5ms startup, 17x faster than Python
- Runs as background daemon (`task-watchdog run &`)
- State persisted to `.claude/process_registry.json`
- 5-minute check intervals
- Context compression resilient (process-based, not token-based)

**Key Capabilities**:
- **Hybrid Execution**: Tracks both native processes (PIDs) and Docker containers
- **Process Groups (PGID)**: Kill entire process trees reliably
- **PID Validation**: Prevents killing recycled PIDs using start-time validation
- **Orphan Detection**: Finds processes that died without cleanup
- **Zombie Detection**: Finds running processes marked complete
- **Resource Monitoring**: CPU/memory tracking per task
- **Environment Tagging**: `CLAUDE_TASK_ID` for orphan discovery

**State File Schema** (`.claude/process_registry.json`):
```json
{
  "tasks": {
    "TASK-001": {
      "execution_mode": "Native",
      "pid": 12345,
      "pgid": 12345,
      "start_time": "Mon Jan  6 10:30:00 2025",
      "status": "Running",
      "description": "Implement auth module",
      "environment_tag": "CLAUDE_TASK_ID=TASK-001"
    },
    "TASK-002": {
      "execution_mode": "Docker",
      "container_id": "abc123def456",
      "status": "Running",
      "description": "Run database migration",
      "resource_limits": {
        "memory": "512m",
        "cpu": "1.0"
      }
    }
  }
}
```

**Watchdog Commands** (via `cli/dev-kid`):
- `watchdog-start`: Launch Rust daemon in background
- `watchdog-stop`: Kill `task-watchdog run` process
- `watchdog-check`: Run `task-watchdog rehydrate` command
- `watchdog-report`: Run `task-watchdog report` for resource usage
- `task-complete ID`: Run `task-watchdog kill ID` to terminate task

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

## Project Intelligence (Discovered Patterns)

### Critical Implementation Insights

**Dual Interface Pattern**: Providing both auto-triggering skills AND manual slash commands proved essential. Users need automation for efficiency but also control for edge cases. Skills in ~/.claude/skills/ auto-activate based on file conditions, while commands in ~/.claude/commands/ provide manual override.

**Symlink Strategy**: For Speckit integration, symlinks (not copies) ensure single source of truth. tasks.md symlinks to .specify/specs/{branch}/tasks.md, updated automatically by git post-checkout hook. This prevents divergence and preserves progress across branch switches.

**Process-Based Monitoring**: Task watchdog runs as independent Python process, not token-based. State persisted to .claude/task_timers.json survives context compression. This was THE critical decision that enables reliable monitoring.

**Verification-Gated Progression**: Wave executor MUST verify tasks.md has [x] markers before proceeding to next wave. This fail-safe pattern prevents silent failures and ensures data integrity.

**Memory Bank Hierarchy**: Six-tier structure (projectbrief → productContext → activeContext → systemPatterns → techContext → progress) builds context progressively. Each tier depends on previous tiers, enabling efficient context loading.

### User Preferences & Patterns

**Error Messages**: Users strongly prefer actionable error messages. Format: "❌ Problem description" followed by "ℹ️ Next steps". Never fail silently.

**Git Operations**: Users are extremely cautious about git operations. NEVER use --force, --hard-reset, or --amend without explicit confirmation. Conservative operations only.

**Documentation**: Users prefer comprehensive inline documentation over external docs. CLAUDE.md serves as single source of truth for project context.

**Token Efficiency**: Users are highly sensitive to token usage. Skills must activate with minimal overhead, Memory Bank updates must be incremental, no verbose output.

### Critical Implementation Paths

**Installation Flow**:
1. Run ./scripts/install.sh (copies to ~/.dev-kid)
2. Creates symlink to /usr/local/bin/dev-kid (or PATH alternative)
3. Deploys skills to ~/.claude/skills/
4. Deploys commands to ~/.claude/commands/
5. Verify with ./scripts/verify-install.sh

**Orchestration Flow**:
1. Parse tasks.md (Markdown → Task objects)
2. Extract file paths (prioritize backtick convention)
3. Analyze dependencies (explicit + file locks)
4. Group into waves (greedy algorithm)
5. Write execution_plan.json
6. Verify JSON schema

**Execution Flow**:
1. Read execution_plan.json
2. For each wave sequentially:
   - Execute tasks (agent responsibility)
   - Verify completion (check tasks.md for [x])
   - HALT if verification fails
   - Update progress.md
   - Create git commit
   - Proceed to next wave

**Speckit Integration Flow**:
1. User switches branch (git checkout feature-x)
2. post-checkout hook fires
3. Hook checks .specify/specs/feature-x/tasks.md exists
4. Creates symlink: tasks.md → .specify/specs/feature-x/tasks.md
5. Dev-kid works with branch-specific tasks
6. Progress preserved when switching back

### Known Gotchas

**Skills Not Found**: Claude Code looks in specific directories. Ensure install.sh copies to ~/.claude/skills/ (NOT ~/.dev-kid/skills/). Common mistake during development.

**File Lock Over-Detection**: Regex may detect file-like strings that aren't actual files. Use backticks to explicitly mark file paths: `src/file.py`. This guarantees detection.

**Watchdog Process Orphans**: If watchdog crashes, process may remain. Always check with `ps aux | grep task_watchdog.py` and kill manually if needed: `pkill -f task_watchdog.py`.

**Git Hooks Not Executable**: Git hooks must have execute permission. After creating .git/hooks/post-checkout, run `chmod +x .git/hooks/post-checkout`. Silent failure if not executable.

**tasks.md Format**: Tasks MUST follow format: `- [ ] TASK-ID: Description affecting \`file.py\``. Wave executor depends on this structure for parsing and verification.

### Performance Optimization Notes

**O(n²) Dependency Analysis**: Acceptable for <1000 tasks (~1 second). If task lists grow larger, consider optimization. Current greedy algorithm trades optimality for predictability.

**JSON File I/O**: Execution plan and state files are small (<100KB typical). File I/O is not bottleneck. Git operations are slowest part of pipeline.

**Memory Bank Updates**: Incremental updates via git diff/log parsing. Avoid full file rewrites. Append-only activity stream prevents corruption.

**Watchdog Polling**: 5-minute check interval balances responsiveness with CPU usage. Configurable if needed, but 5min works for 99% of use cases.

### Testing Strategies

**Manual Testing Workflow**:
1. Install to /tmp/test-dev-kid (isolated environment)
2. Initialize test project with git init
3. Create test tasks.md with known dependencies
4. Run orchestration and verify execution_plan.json
5. Execute waves and verify git commits
6. Check Memory Bank updates

**Regression Testing**:
- Always test file lock detection with backtick and non-backtick paths
- Always test verification failure (incomplete tasks.md)
- Always test git hook activation (branch switches)
- Always test watchdog state persistence (kill and restart)

**Edge Cases to Test**:
- Empty tasks.md (should gracefully handle)
- No git repository (should error clearly)
- Circular dependencies (should detect and report)
- File paths with spaces (should handle with backticks)
- Very long task descriptions (should truncate gracefully)

### Constitution Integration Notes

**Pipeline Enforcement**: Constitution.md is checked at three points: pre-orchestration, during execution, post-checkpoint. This ensures quality standards are enforced throughout.

**Optional Feature**: Constitution is optional. If Constitution.md doesn't exist, system works normally. This allows gradual adoption.

**Violation Reporting**: When constitution violations detected, system provides clear explanation with specific rule violated and suggested fix. Never fail silently.

### Speckit Integration Notes

**Branch-Based Isolation**: Critical decision was to use .specify/specs/{branch}/ structure. Each feature branch has independent tasks.md, preventing conflicts.

**Symlink Management**: Git post-checkout hook is ONLY way to reliably detect branch switches. Running dev-kid commands doesn't work because git context isn't available.

**Progress Preservation**: Because tasks.md is symlinked (not copied), progress on each branch is automatically preserved. No manual syncing needed.

**Constitution Sharing**: Constitution.md lives in project root, shared across all branches. This ensures quality standards are consistent across features.

# Dev-Kid System Architecture

**Version**: 2.0.0
**Last Updated**: 2026-01-05

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Diagram](#component-diagram)
4. [Data Flow](#data-flow)
5. [Directory Structure](#directory-structure)
6. [Design Decisions](#design-decisions)
7. [Integration Points](#integration-points)

---

## Overview

Dev-kid is a complete development workflow system for Claude Code that provides:

- **Task Orchestration**: Wave-based parallel execution with dependency management
- **Persistent Memory**: Memory Bank with 6-tier architecture
- **Context Protection**: Compression-aware state management
- **Task Monitoring**: Background watchdog that survives context compression
- **Skills Layer**: Auto-activating workflow automation
- **Git Integration**: Semantic checkpoints with verification

### Key Principle

**Zero Configuration, Maximum Automation**: One command installs everything. Works in any project. Fully reproducible.

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     CLI Layer (Bash)                         │
│  /usr/local/bin/dev-kid → ~/.dev-kid/cli/dev-kid            │
│                                                              │
│  Commands: init, orchestrate, execute, checkpoint, etc.     │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┬──────────────┐
        │             │             │              │
        ▼             ▼             ▼              ▼
┌───────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│Orchestrator│  │  Wave    │  │  Task    │  │ Skills   │
│  Engine   │  │Executor  │  │Watchdog  │  │ Layer    │
│  (Python) │  │ (Python) │  │ (Python) │  │  (Bash)  │
└─────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
      │             │              │              │
      │             │              │              │
      └─────────────┴──────────────┴──────────────┘
                      │
        ┌─────────────┼─────────────┬──────────────┐
        │             │             │              │
        ▼             ▼             ▼              ▼
┌───────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│  Memory   │  │ Context  │  │   Git    │  │  State   │
│   Bank    │  │Protection│  │  System  │  │ Files    │
│(markdown) │  │ (JSON)   │  │ (.git)   │  │  (JSON)  │
└───────────┘  └──────────┘  └──────────┘  └──────────┘
```

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface                       │
│               (CLI Commands & Output)                   │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │
┌─────────────────────────────────────────────────────────┐
│                  Application Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Orchestrator │  │Wave Executor │  │Task Watchdog │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │
┌─────────────────────────────────────────────────────────┐
│                    Skills Layer                          │
│  sync_memory | checkpoint | verify | recall | finalize  │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │
┌─────────────────────────────────────────────────────────┐
│                   Storage Layer                          │
│  Memory Bank | Context Protection | Git | State Files   │
└─────────────────────────────────────────────────────────┘
```

---

## Component Diagram

### Core Components

#### 1. CLI Entry Point (`dev-kid`)

**Type**: Bash script
**Location**: `~/.dev-kid/cli/dev-kid`
**Responsibilities**:
- Command routing and validation
- User interaction and output formatting
- Environment setup and variable management
- Delegation to Python scripts and skills

**Key Functions**:
```bash
cmd_init()          # Initialize project structure
cmd_orchestrate()   # Delegate to orchestrator.py
cmd_execute()       # Delegate to wave_executor.py
cmd_watchdog_start()# Start task_watchdog.py background process
cmd_checkpoint()    # Delegate to checkpoint.sh skill
cmd_status()        # System health check
```

#### 2. Task Orchestrator (`orchestrator.py`)

**Type**: Python module
**Location**: `~/.dev-kid/cli/orchestrator.py`
**Responsibilities**:
- Parse tasks.md into Task objects
- Analyze dependencies (explicit and implicit)
- Build dependency graph
- Group tasks into execution waves
- Generate execution_plan.json

**Core Classes**:

```python
@dataclass
class Task:
    id: str                      # T001, T002, etc.
    description: str             # Task text from tasks.md
    agent_role: str = "Developer"
    file_locks: List[str]        # Files this task modifies
    dependencies: List[str]      # Task IDs this depends on
    completed: bool = False

@dataclass
class Wave:
    wave_id: int                 # 1, 2, 3, etc.
    strategy: str                # PARALLEL_SWARM | SEQUENTIAL_MERGE
    tasks: List[Dict]            # Task specifications
    rationale: str               # Why these tasks grouped
    checkpoint_enabled: bool = True
```

**Algorithms**:

1. **Dependency Analysis**:
   - Extract explicit dependencies: "after T123", "depends on T456"
   - Extract implicit file dependencies: same file = sequential execution
   - Build directed acyclic graph (DAG)

2. **Wave Creation**:
   - Greedy algorithm: assign tasks to earliest possible wave
   - Constraint: all dependencies satisfied
   - Constraint: no file lock conflicts within wave
   - Output: JSON execution plan

#### 3. Wave Executor (`wave_executor.py`)

**Type**: Python module
**Location**: `~/.dev-kid/cli/wave_executor.py`
**Responsibilities**:
- Load execution_plan.json
- Execute waves sequentially
- Verify task completion between waves
- Create checkpoints with git and Memory Bank
- Halt on verification failure

**Core Methods**:

```python
class WaveExecutor:
    def load_plan() -> None
        # Parse execution_plan.json

    def execute_wave(wave: Dict) -> None
        # Display wave info, tasks, strategy
        # (Actual execution delegated to Claude Code agents)

    def verify_wave_completion(wave_id: int, tasks: List[Dict]) -> bool
        # Check tasks.md for [x] completion markers
        # Return False if any task incomplete

    def execute_checkpoint(wave_id: int, checkpoint: Dict) -> None
        # 1. Verify completion
        # 2. Update progress.md
        # 3. Create git commit
        # Halt if verification fails
```

#### 4. Task Watchdog (`task_watchdog.py`)

**Type**: Python daemon
**Location**: `~/.dev-kid/cli/task_watchdog.py`
**Responsibilities**:
- Run as background process (survives context compression)
- Track task start/end times
- Monitor for forgotten or long-running tasks
- Sync with tasks.md for completion detection
- Persist state to disk

**Core Methods**:

```python
class TaskWatchdog:
    def __init__(state_file=".claude/task_timers.json")

    def start_task(task_id: str, description: str) -> None
        # Record start time, persist to disk

    def complete_task(task_id: str) -> None
        # Calculate duration, move to completed, persist

    def check_tasks() -> None
        # Sync with tasks.md
        # Check for tasks exceeding 7-minute guideline
        # Check for stalled tasks (>15 min no activity)
        # Generate warnings

    def run_watchdog(duration_minutes: int = None) -> None
        # Infinite loop with 5-minute intervals
        # Handles KeyboardInterrupt gracefully
```

**State File Schema**:

```json
{
  "running_tasks": {
    "TASK-001": {
      "description": "Task description",
      "started_at": "2026-01-05T10:30:00",
      "last_checked": "2026-01-05T10:35:00",
      "status": "running"
    }
  },
  "completed_tasks": {
    "TASK-002": {
      "description": "Task description",
      "started_at": "2026-01-05T09:00:00",
      "completed_at": "2026-01-05T09:45:00",
      "duration_seconds": 2700,
      "duration_human": "45m"
    }
  },
  "warnings": [
    {
      "type": "long_running",
      "task_id": "TASK-001",
      "duration": "1h 30m",
      "timestamp": "2026-01-05T11:00:00"
    }
  ]
}
```

#### 5. Skills Layer

**Type**: Bash scripts
**Location**: `~/.dev-kid/skills/*.sh`
**Responsibilities**: Encapsulate common workflows

**Skills**:

1. **sync_memory.sh**: Update Memory Bank
   - Parse git changes
   - Update activeContext.md
   - Calculate progress from tasks.md
   - Update progress.md
   - Append to activity stream

2. **checkpoint.sh**: Create semantic git checkpoint
   - Call sync_memory.sh first
   - Stage all changes
   - Create commit with standard format
   - Include timestamp and co-author

3. **verify_existence.sh**: Anti-hallucination verification
   - Parse file references from target file
   - Check file existence
   - Warn about non-existent functions
   - Prevent hallucinated file references

4. **maintain_integrity.sh**: System validation
   - Check Memory Bank structure
   - Check Context Protection files
   - Check Skills installation
   - Check Git status
   - Report errors and warnings

5. **finalize_session.sh**: Session snapshot
   - Sync Memory Bank
   - Create snapshot JSON
   - Include progress, git state, next steps
   - Create symlink to latest
   - Create checkpoint

6. **recall.sh**: Resume from snapshot
   - Load latest snapshot JSON
   - Display session state
   - Show progress, blockers, next steps
   - Provide resumption guidance

---

## Data Flow

### Task Orchestration Flow

```
┌────────────┐
│  tasks.md  │ (Linear task list)
└──────┬─────┘
       │
       ▼
┌─────────────────┐
│ orchestrator.py │
│                 │
│ 1. Parse tasks  │
│ 2. Extract deps │
│ 3. Build graph  │
│ 4. Create waves │
└──────┬──────────┘
       │
       ▼
┌────────────────────┐
│execution_plan.json │ (Wave-based plan)
└──────┬─────────────┘
       │
       ▼
┌──────────────────┐
│wave_executor.py  │
│                  │
│ For each wave:   │
│ 1. Execute tasks │
│ 2. Verify [x]    │
│ 3. Update Memory │
│ 4. Git commit    │
└──────────────────┘
```

### Memory Sync Flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Git diff │────▶│sync_mem  │────▶│activeCtx │
└──────────┘     │  ory.sh  │     │  .md     │
                 │          │     └──────────┘
┌──────────┐     │          │     ┌──────────┐
│tasks.md  │────▶│          │────▶│progress  │
└──────────┘     │          │     │  .md     │
                 │          │     └──────────┘
┌──────────┐     │          │     ┌──────────┐
│Git log   │────▶│          │────▶│activity  │
└──────────┘     └──────────┘     │_stream   │
                                  └──────────┘
```

### Checkpoint Flow

```
┌──────────────┐
│ User/Agent   │
│ calls        │
│ checkpoint   │
└──────┬───────┘
       │
       ▼
┌─────────────────┐
│checkpoint.sh    │
│                 │
│ 1. Sync memory  │──┐
│ 2. Git add .    │  │
│ 3. Git commit   │  │
└─────────────────┘  │
                     │
       ┌─────────────┘
       │
       ▼
┌─────────────────┐     ┌──────────────┐
│Memory Bank      │     │ Git History  │
│ Updated         │     │ New commit   │
└─────────────────┘     └──────────────┘
```

### Task Watchdog Flow

```
┌───────────────┐
│ Background    │
│ Process       │
│ (every 5 min) │
└───────┬───────┘
        │
        ▼
┌───────────────────┐
│ Load state from   │
│ .claude/task_     │
│ timers.json       │
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ Sync with         │
│ tasks.md          │
│ (detect [x])      │
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ Check for:        │
│ - Long running    │
│ - Forgotten tasks │
│ - Generate warns  │
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│ Save state to     │
│ disk              │
└───────────────────┘
```

---

## Directory Structure

### Installation Layout

```
~/.dev-kid/                         # Installation root
├── cli/
│   ├── dev-kid                     # Main CLI (bash)
│   ├── orchestrator.py             # Task → waves
│   ├── wave_executor.py            # Wave execution
│   └── task_watchdog.py            # Background monitor
├── skills/
│   ├── sync_memory.sh              # Memory Bank sync
│   ├── checkpoint.sh               # Git checkpoint
│   ├── verify_existence.sh         # Anti-hallucination
│   ├── maintain_integrity.sh       # System validation
│   ├── finalize_session.sh         # Session snapshot
│   └── recall.sh                   # Session recovery
├── scripts/
│   ├── install.sh                  # Global install
│   └── init.sh                     # Per-project init
└── templates/
    ├── memory-bank/                # Memory Bank templates
    └── .claude/                    # Context Protection templates

~/.claude/skills/planning-enhanced/ # Skills symlink location
├── sync_memory.sh -> ~/.dev-kid/skills/sync_memory.sh
├── checkpoint.sh -> ~/.dev-kid/skills/checkpoint.sh
└── ... (other skills)

/usr/local/bin/dev-kid -> ~/.dev-kid/cli/dev-kid  # PATH symlink
```

### Project Layout (After `dev-kid init`)

```
your-project/
├── memory-bank/                    # Persistent memory
│   ├── shared/                     # Team knowledge
│   │   ├── projectbrief.md         # North Star vision
│   │   ├── systemPatterns.md       # Architecture patterns
│   │   ├── techContext.md          # Tech stack & constraints
│   │   └── productContext.md       # User needs & strategy
│   └── private/
│       └── $USER/                  # Per-user context
│           ├── activeContext.md    # Current focus
│           ├── progress.md         # Task metrics
│           └── worklog.md          # Daily entries
│
├── .claude/                        # Context Protection
│   ├── active_stack.md             # <500 token current focus
│   ├── activity_stream.md          # Append-only event log
│   ├── AGENT_STATE.json            # Agent coordination
│   ├── system_bus.json             # Inter-agent messaging
│   ├── task_timers.json            # Watchdog state
│   └── session_snapshots/
│       ├── snapshot_latest.json -> snapshot_2026-01-05_14-30-00.json
│       ├── snapshot_2026-01-05_14-30-00.json
│       └── snapshot_2026-01-05_09-15-00.json
│
├── .git/                           # Version control
│   └── hooks/
│       └── post-commit             # Auto-log to activity stream
│
├── tasks.md                        # Task list (input)
├── execution_plan.json             # Wave plan (generated)
└── your-code/                      # Project files
```

---

## Design Decisions

### 1. Why Bash for CLI?

**Decision**: Main CLI is Bash script, delegates to Python for complex logic

**Rationale**:
- **Portability**: Bash available on all Unix systems
- **Simplicity**: CLI routing doesn't need Python overhead
- **Performance**: Fast startup for simple commands
- **Integration**: Easy subprocess management, git commands

**Trade-offs**:
- More verbose than Python for complex logic (mitigated by delegation)
- Harder to test (mitigated by keeping logic in Python modules)

### 2. Why Python for Orchestration?

**Decision**: Task orchestration and wave execution in Python

**Rationale**:
- **Data structures**: Dataclasses, defaultdict, easy JSON handling
- **Algorithms**: Graph analysis, dependency resolution
- **Type safety**: Type hints improve maintainability
- **Testing**: Easier unit testing than Bash

**Trade-offs**:
- Python 3 dependency (acceptable for development tools)

### 3. Why JSON for State?

**Decision**: Use JSON for execution_plan.json, AGENT_STATE.json, task_timers.json

**Rationale**:
- **Portable**: Universal format, easy parsing
- **Human-readable**: Can inspect/debug state files
- **Schema-friendly**: Easy validation
- **Language-agnostic**: Bash, Python, any tool can read

**Trade-offs**:
- Larger than binary formats (negligible for dev tool)
- No schema enforcement (mitigated by validation in code)

### 4. Why Markdown for Memory Bank?

**Decision**: Memory Bank uses Markdown files

**Rationale**:
- **Human-readable**: Easy to edit, review, understand
- **Version control**: Git-friendly text format
- **AI-friendly**: Claude Code can parse and modify easily
- **Portable**: Universal format, no lock-in

**Trade-offs**:
- No structured validation (mitigated by templates)
- Manual formatting needed (acceptable for knowledge documents)

### 5. Why Process-Based Watchdog?

**Decision**: Task Watchdog runs as background process, not token-dependent

**Rationale**:
- **Context compression resilient**: Process survives compression
- **Persistent monitoring**: Continues checking every 5 minutes
- **State preservation**: Disk persistence across sessions
- **Resource efficient**: Minimal overhead, sleep between checks

**Trade-offs**:
- Process management complexity (mitigated by simple start/stop commands)
- User must remember to stop watchdog (mitigated by status command)

### 6. Why File-Based Locking in Orchestrator?

**Decision**: Detect file conflicts by extracting file references from task descriptions

**Rationale**:
- **Prevents race conditions**: Tasks modifying same file can't run in parallel
- **Simple heuristic**: Regex extraction of file paths
- **No manual specification**: Automatic from task text

**Trade-offs**:
- May miss some file references (mitigated by backtick convention)
- May be overly conservative (acceptable for safety)

### 7. Why Checkpoint Between Waves?

**Decision**: Mandatory verification and git checkpoint between execution waves

**Rationale**:
- **Data integrity**: Ensures tasks actually completed
- **Context compression protection**: Git commit preserves state
- **Memory Bank sync**: Progress always recorded
- **Rollback capability**: Each wave is recoverable state

**Trade-offs**:
- Slower execution (acceptable for correctness)
- Requires manual task marking (enforced by protocol)

### 8. Why Skills in Bash?

**Decision**: Skills layer implemented as Bash scripts

**Rationale**:
- **System integration**: Easy git, file operations
- **Simplicity**: No Python overhead for simple workflows
- **Portability**: Run anywhere Bash available
- **Claude Code integration**: Easy to call from agents

**Trade-offs**:
- Limited error handling (mitigated by `set -e`)
- Harder to test (mitigated by simple, focused scripts)

---

## Integration Points

### 1. Git Integration

**Interface**: Skills call git commands via subprocess

**Checkpoints**:
```bash
git add .
git commit -m "[CHECKPOINT] $MESSAGE"
```

**Hooks**:
- `post-commit`: Logs to activity_stream.md

### 2. Claude Code Skills Integration

**Interface**: Skills installed to `~/.claude/skills/planning-enhanced/`

**Activation**: Auto-detected by Claude Code when keywords mentioned

**Examples**:
- "sync memory" → triggers sync_memory.sh
- "create checkpoint" → triggers checkpoint.sh
- "verify files" → triggers verify_existence.sh

### 3. Memory Bank Integration

**Interface**: Skills read/write Markdown files in `memory-bank/`

**Update Pattern**:
1. Read current state
2. Extract new information (git, tasks.md)
3. Generate updated Markdown
4. Write to file

### 4. Task Tracking Integration

**Interface**: tasks.md with checkbox format

**Protocol**:
- `- [ ]` = pending task
- `- [x]` = completed task

**Verification**:
- Orchestrator parses tasks.md
- Wave executor verifies [x] completion
- Watchdog syncs with tasks.md

### 5. Context Protection Integration

**Interface**: JSON files in `.claude/`

**Schema**:
- `AGENT_STATE.json`: Agent coordination
- `system_bus.json`: Event log
- `task_timers.json`: Watchdog state
- `session_snapshots/*.json`: Recovery points

---

## Performance Characteristics

### Time Complexity

**Orchestrator**:
- Task parsing: O(n) where n = number of tasks
- Dependency analysis: O(n²) worst case (checking all pairs)
- Wave creation: O(n × w) where w = average wave size
- Overall: O(n²) for reasonable task counts (<1000)

**Wave Executor**:
- Load plan: O(1)
- Execute waves: O(w) where w = number of waves
- Verify completion: O(t) where t = tasks in wave
- Overall: O(waves × tasks_per_wave)

**Task Watchdog**:
- Load state: O(1)
- Check tasks: O(r + c) where r = running, c = completed
- Sync with tasks.md: O(t) where t = total tasks
- Overall: O(n) per check cycle

### Space Complexity

**Memory Bank**: O(p) where p = project size (Markdown files)
**Execution Plan**: O(t) where t = total tasks
**Watchdog State**: O(r + c) where r = running, c = completed
**Session Snapshots**: O(s) where s = number of snapshots (typically <10)

### Token Efficiency

**Planning Overhead**: <10% of context window
- Memory Bank: 2-5k tokens
- Active Stack: <500 tokens
- Execution Plan: 1-3k tokens

**Skills Activation**: Zero coordination tokens (auto-triggered)

---

## Security Considerations

### 1. File Permissions

**Installed files**: User-owned, executable
**State files**: User-readable only (JSON contains sensitive info)
**Skills**: Execute bit set, but no sudo required

### 2. Git Safety

**No destructive operations**: No force push, hard reset
**Verification before commit**: Ensures valid state
**Co-author attribution**: Tracks AI collaboration

### 3. Path Safety

**No path injection**: All paths validated
**No arbitrary execution**: Scripts are predefined
**Symlink safety**: Checked before creation

### 4. Data Privacy

**Private context**: Stored in per-user directories
**No network calls**: All operations local
**Git hooks**: Opt-in, user-controlled

---

## Extension Points

### 1. Adding New Commands

Edit `dev-kid` CLI:
```bash
cmd_new_command() {
    echo "New command implementation"
}

# In main() dispatcher:
case "$command" in
    new-command) cmd_new_command "$@" ;;
esac
```

### 2. Adding New Skills

Create `skills/new_skill.sh`:
```bash
#!/usr/bin/env bash
# Skill: New Skill
# Trigger: keyword1, keyword2

echo "Executing new skill..."
# Implementation
```

Install:
```bash
chmod +x skills/new_skill.sh
cp skills/new_skill.sh ~/.claude/skills/planning-enhanced/
```

### 3. Customizing Wave Strategies

Edit `orchestrator.py`:
```python
def create_waves(self) -> None:
    # Custom strategy logic
    if custom_condition:
        strategy = "CUSTOM_STRATEGY"
```

### 4. Adding State Fields

Edit JSON schemas in respective files:
- `AGENT_STATE.json`: Add agent-related fields
- `task_timers.json`: Add task metadata
- `session_snapshots/*.json`: Add session info

---

## Testing Strategy

### Unit Testing

**Python modules**:
```bash
pytest cli/test_orchestrator.py
pytest cli/test_wave_executor.py
pytest cli/test_task_watchdog.py
```

**Bash scripts**:
```bash
# Use bats (Bash Automated Testing System)
bats skills/test_checkpoint.bats
```

### Integration Testing

**Full workflow**:
```bash
./scripts/integration_test.sh
# 1. Init project
# 2. Create tasks.md
# 3. Orchestrate
# 4. Execute
# 5. Verify git commits
# 6. Verify Memory Bank updates
```

### Manual Testing

**Checklist**:
1. Install on clean system
2. Initialize in test project
3. Run all CLI commands
4. Verify file structure
5. Check git commits
6. Validate JSON schemas
7. Test watchdog background process
8. Test session snapshots

---

## Troubleshooting

### Common Issues

1. **"command not found: dev-kid"**
   - Symlink not created in /usr/local/bin
   - Run: `sudo ln -sf ~/.dev-kid/cli/dev-kid /usr/local/bin/dev-kid`

2. **"No module named 'orchestrator'"**
   - Python 3 not installed or wrong PATH
   - Verify: `which python3`

3. **Watchdog doesn't start**
   - Process already running
   - Kill: `pkill -f task_watchdog.py`

4. **Memory Bank not updating**
   - Git not initialized
   - Run: `git init` in project root

### Debug Mode

Enable verbose output:
```bash
dev-kid --verbose orchestrate
dev-kid --dry-run execute
```

### Log Files

Check logs:
```bash
# Git hook logs
cat .git/hooks/post-commit

# Activity stream
cat .claude/activity_stream.md

# Watchdog state
cat .claude/task_timers.json
```

---

## Future Architecture Considerations

### Potential Enhancements

1. **Distributed Execution**: Support for multi-machine wave execution
2. **Plugin System**: Dynamic skill loading
3. **Web Dashboard**: Real-time monitoring UI
4. **Cloud Sync**: Memory Bank synchronization across machines
5. **Advanced Metrics**: Performance analytics, bottleneck detection

### Scalability

**Current limits**:
- Tasks: ~1000 (O(n²) dependency analysis)
- Waves: ~100 (sequential execution)
- Watchdog: ~50 concurrent tasks (5-min check interval)

**Optimization opportunities**:
- Parallel wave execution (multi-process)
- Incremental dependency analysis
- Database-backed state (SQLite)
- Streaming task execution

---

**Architecture Document v2.0.0**
Complete system architecture for dev-kid development workflow system

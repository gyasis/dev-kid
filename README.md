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

### 🎯 Skills Layer
- **sync_memory**: Update Memory Bank with current state
- **checkpoint**: Create semantic git checkpoints
- **verify_existence**: Anti-hallucination verification
- **recall**: Resume from last session snapshot
- **finalize_session**: Create session snapshot
- **maintain_integrity**: Validate system consistency

## Dependencies

### Required
- **Bash** 4.0+ (CLI and scripts)
- **Git** 2.0+ (version control and checkpointing)
- **Python 3.7+** (orchestration, no external packages needed)
- **jq** 1.5+ (JSON parsing)

### Recommended
- **sed**, **grep** (template processing)

The installer automatically checks all dependencies and provides installation instructions if anything is missing. See [DEPENDENCIES.md](DEPENDENCIES.md) for detailed requirements and platform-specific installation instructions.

## Quick Start

### Installation

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
- Skills to `~/.claude/skills/planning-enhanced/`
- Templates to `~/.dev-kid/templates/`

### Initialize in Your Project

```bash
cd your-project
dev-kid init

# This creates:
# - memory-bank/        (institutional memory)
# - .claude/            (context protection)
# - Git hooks           (auto-checkpoint on commit)
```

### Basic Workflow

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

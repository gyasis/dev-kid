# Dev-Kid Quick Start Guide

**Get productive with dev-kid in 5 minutes**

## Prerequisites Check

Before starting, verify you have:

```bash
# Required
bash --version        # Bash 4.0+
git --version         # Git 2.0+
python3 --version     # Python 3.7+
jq --version          # jq 1.5+

# Optional (for Rust watchdog)
cargo --version       # Rust 1.70+ (for building watchdog)
```

If anything is missing, see [DEPENDENCIES.md](docs/development/DEPENDENCIES.md) for installation instructions.

## Installation (2 minutes)

### Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/dev-kid.git
cd dev-kid

# Run the installer (no .sh extension needed!)
./install

# Verify installation
dev-kid --version
# Output: dev-kid v2.0.0
```

**What gets installed:**
- ✅ CLI tools → `~/.dev-kid/`
- ✅ Symlink → `/usr/local/bin/dev-kid`
- ✅ Skills → `~/.claude/skills/planning-enhanced/`
- ✅ Commands → `~/.claude/commands/`
- ✅ Templates → `~/.dev-kid/templates/`

### Step 2: Build Rust Watchdog (Optional but Recommended)

```bash
cd rust-watchdog
cargo build --release
cd ..

# Verify the binary works
./rust-watchdog/target/release/task-watchdog --version
# Output: task-watchdog 2.0.0
```

**Performance**: <3MB memory, <5ms startup, 17x faster than Python

**Skip if**: You don't need background task monitoring (core features work without it)

## The Modern Workflow: Speckit + Dev-Kid (RECOMMENDED)

**This is the primary workflow.** Speckit handles planning and specification, dev-kid handles execution.

### Step 1: Initialize Dev-Kid in Your Project

```bash
cd /path/to/your-project
dev-kid init
```

**This creates:**
```
your-project/
├── memory-bank/           # Auto-updated during checkpoints
│   ├── shared/
│   │   ├── projectbrief.md
│   │   ├── systemPatterns.md
│   │   ├── techContext.md
│   │   └── productContext.md
│   └── private/$USER/
│       ├── activeContext.md
│       ├── progress.md
│       └── worklog.md
├── .claude/               # Context protection (survives compression)
├── .devkid/               # Configuration
└── .git/hooks/            # Auto-checkpoint hooks
```

**Important**: With Speckit, these files **update automatically**. You DON'T manually edit them!

### Step 2: Create Project Constitution (One-Time Setup)

In Claude Code, run:

```
/speckit.constitution
```

**What happens:**
- Interactive prompt guides you through creating Constitution.md
- You choose a template (python-api, typescript-frontend, data-engineering, etc.)
- Constitution defines quality rules enforced at checkpoints
- Saved to `memory-bank/shared/.constitution.md`

**Example constitution rules:**
- TYPE_HINTS_REQUIRED
- DOCSTRINGS_REQUIRED
- NO_BARE_EXCEPT
- PEP8_NAMING

### Step 3: Specify Your Feature

In Claude Code, run:

```
/speckit.specify "Add user authentication with OAuth2"
```

**What happens:**
- Creates `.specify/specs/001-user-auth/spec.md`
- Spec includes:
  - Feature overview
  - Technical approach
  - Acceptance criteria
  - Dependencies
  - Risks

**You can refine the spec** before generating tasks!

### Step 4: Generate Tasks from Spec

In Claude Code, run:

```
/speckit.tasks
```

**What happens:**
- Reads your spec from `.specify/specs/001-user-auth/spec.md`
- Generates actionable tasks in `.specify/specs/001-user-auth/tasks.md`
- **Git hook auto-creates symlink**: `tasks.md → .specify/specs/001-user-auth/tasks.md`
- Tasks are already formatted for dev-kid orchestration
- Constitution rules embedded in tasks

**Example generated tasks.md:**
```markdown
# Tasks

## Phase 1: Authentication Setup
- [ ] TASK-001: Create user model in `src/models/user.py`
  **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED

- [ ] TASK-002: Implement OAuth2 flow in `src/auth/oauth.py`
  **Constitution**: TYPE_HINTS_REQUIRED, NO_BARE_EXCEPT

- [ ] TASK-003: Add authentication middleware in `src/middleware/auth.py`
  **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED
```

### Step 5: Orchestrate Tasks into Waves

```bash
dev-kid orchestrate "Phase 1"
```

**What happens:**
- Reads `tasks.md` (which is symlinked to your spec's tasks)
- Analyzes dependencies (explicit + file lock detection)
- Groups tasks into parallel execution waves
- Writes `execution_plan.json`

**Example output:**
```
📊 Creating execution plan for: Phase 1
✅ Analyzed 3 tasks
✅ Created 2 waves (parallel execution)
✅ Saved to: execution_plan.json
```

### Step 6: View the Execution Plan

```bash
dev-kid waves
```

**Output:**
```
🌊 Execution Plan Waves

📋 Phase: Phase-1
🌊 Waves: 2

Wave 1 (PARALLEL_SWARM):
  Tasks: 2
  Rationale: Tasks modify different files - no conflicts

Wave 2 (SEQUENTIAL_MERGE):
  Tasks: 1
  Rationale: Depends on Wave 1 completion
```

### Step 7: Start Watchdog (Optional but Recommended)

```bash
dev-kid watchdog-start
```

**Output:**
```
🐕 Starting Task Watchdog (Rust)
   Generic process monitor for AI coding tools
   Monitoring tasks every 5 minutes...
✅ Watchdog started (PID: 12345)
   Memory usage: <3MB | Startup: <5ms
   To stop: dev-kid watchdog-stop
```

### Step 8: Execute Waves

```bash
dev-kid execute
```

**What happens:**
1. Executes Wave 1 tasks (you implement them with Claude's help)
2. You mark tasks `[x]` in `tasks.md` as you complete them
3. Wave executor **verifies completion** (checks for `[x]` markers)
4. **Constitution validation** runs (checks your code against rules)
5. If violations found → **checkpoint BLOCKS**, you must fix
6. If validation passes → **git checkpoint created**
7. **Memory Bank auto-updated** with progress
8. Proceeds to Wave 2

**Critical**: You MUST mark tasks `[x]` for verification to pass!

### Step 9: Mark Tasks Complete as You Work

As you complete each task:

```bash
# Edit tasks.md
vim tasks.md

# Change:
- [ ] TASK-001: Create user model...
# To:
- [x] TASK-001: Create user model...
```

**Wave executor checks for `[x]` before proceeding to next wave!**

### Step 10: Create Manual Checkpoints (Optional)

```bash
dev-kid checkpoint "Completed OAuth2 integration"
```

**What happens:**
- Calls `sync_memory.sh` skill
- Extracts git history → updates `progress.md`
- Extracts task completion → updates `activeContext.md`
- Creates git commit with message
- Appends to `.claude/activity_stream.md`

**You DON'T manually edit Memory Bank files - they update automatically!**

### Step 11: Check Status Anytime

```bash
dev-kid status
```

**Output:**
```
✅ Memory Bank: Initialized
✅ Constitution: Configured
   Quality: Valid
✅ Config: Initialized
   Wave size: 5 | Watchdog: 7min
✅ Context Protection: Enabled
   📊 Context Budget: ✅ Smart Zone (optimal)
✅ Task Watchdog: Active (Rust)
   Running: 1 | Completed: 2 | Total: 3
✅ Skills: 6 installed
✅ Git: Initialized
   Commits: 15
✅ Execution Plan: 2 waves
```

### Step 12: End of Session

```bash
# Finalize session (creates snapshot for recovery)
dev-kid finalize

# Stop watchdog
dev-kid watchdog-stop
```

**What happens:**
- Creates session snapshot in `.claude/session_snapshots/`
- Includes: mental state, current phase, progress, next steps, blockers
- Git commits created
- Memory Bank synced

### Step 13: Resume Next Session

```bash
dev-kid recall
```

**What happens:**
- Reads latest session snapshot
- Shows:
  - Last state
  - Next steps
  - Blockers
  - Running tasks (from watchdog)
- Helps Claude resume context

## Branch Switching (Automatic!)

When you switch branches, Speckit integration **automatically relinks tasks.md**:

```bash
# Working on feature 1
git checkout feature/user-auth
# tasks.md → .specify/specs/001-user-auth/tasks.md

# Switch to feature 2
git checkout feature/payment-flow
# tasks.md → .specify/specs/002-payment-flow/tasks.md (automatic!)

# Your progress is preserved per branch!
```

**Git post-checkout hook** handles this automatically.

## Complete Example Workflow

Here's a full example from start to finish:

```bash
# 1. Initialize
cd my-api-project
dev-kid init

# 2. Create constitution (in Claude Code)
/speckit.constitution
# Choose: python-api template

# 3. Specify first feature (in Claude Code)
/speckit.specify "Add user registration and login with JWT"

# 4. Generate tasks (in Claude Code)
/speckit.tasks
# Output: Created .specify/specs/001-user-auth/tasks.md
#         Symlinked: tasks.md → .specify/specs/001-user-auth/tasks.md

# 5. Orchestrate
dev-kid orchestrate "Phase 1"
dev-kid waves
# Shows: 3 waves, 12 tasks total

# 6. Start watchdog
dev-kid watchdog-start

# 7. Execute
dev-kid execute
# Wave 1: Implement 4 tasks in parallel
# Mark each [x] as you complete
# System verifies, validates constitution, checkpoints

# 8. Check progress
dev-kid status
dev-kid watchdog-report

# 9. End session
dev-kid finalize
dev-kid watchdog-stop

# Next day...

# 10. Resume
dev-kid recall
# Shows: Last state, next steps, running tasks

# 11. Continue execution
dev-kid execute
# Picks up where you left off
```

## Legacy Workflow: Without Speckit

**Only use this if your project doesn't have Speckit integration.**

<details>
<summary>Click to expand standalone workflow</summary>

### Without Speckit, You Manually Create Everything

```bash
# 1. Initialize
cd your-project
dev-kid init

# 2. MANUALLY set up Memory Bank (provide context to Claude)
vim memory-bank/shared/projectbrief.md
```

**Example projectbrief.md:**
```markdown
# Project Brief

## Vision
Build a task management API with real-time notifications

## Goals
- FastAPI backend with PostgreSQL
- WebSocket support
- JWT authentication

## Success Criteria
- API response time < 100ms
- Test coverage > 90%
```

```bash
# 3. MANUALLY create tasks.md
cat > tasks.md << 'EOF'
# Tasks

## Phase 1: Foundation
- [ ] TASK-001: Set up FastAPI project structure in `src/main.py`
- [ ] TASK-002: Configure PostgreSQL connection in `src/database.py`
- [ ] TASK-003: Create user model in `src/models/user.py`

## Phase 2: API
- [ ] TASK-004: Implement CRUD endpoints in `src/api/users.py`
- [ ] TASK-005: Add JWT authentication in `src/auth.py`
- [ ] TASK-006: Write API tests in `tests/test_api.py`
EOF

# 4. Dev-kid workflow (same as Speckit)
dev-kid orchestrate "Phase 1"
dev-kid execute
```

**Differences from Speckit workflow:**
- ❌ NO automatic task generation
- ❌ NO constitution enforcement
- ❌ NO branch-based task isolation
- ❌ NO automatic spec → tasks workflow
- ✅ Manual Memory Bank editing required
- ✅ Manual tasks.md creation required

</details>

## Essential Commands Reference

### Core Workflow
```bash
dev-kid init                    # Initialize in project
dev-kid orchestrate "Phase"     # Convert tasks.md to waves
dev-kid execute                 # Execute waves with checkpoints
dev-kid status                  # Show system health
dev-kid waves                   # Show execution plan
```

### Watchdog (Process Monitoring)
```bash
dev-kid watchdog-start          # Start Rust daemon
dev-kid watchdog-check          # Check running tasks
dev-kid watchdog-report         # Show resource usage
dev-kid watchdog-stop           # Stop daemon
```

### Memory & Checkpoints
```bash
dev-kid sync-memory             # Update Memory Bank
dev-kid checkpoint "message"    # Create git checkpoint
dev-kid finalize                # End session (create snapshot)
dev-kid recall                  # Resume from snapshot
```

### Constitution & Config
```bash
dev-kid constitution init       # Initialize from template
dev-kid constitution validate   # Check constitution quality
dev-kid config show             # Display configuration
dev-kid config get KEY          # Get config value
dev-kid config set KEY VALUE    # Set config value
```

### System Validation
```bash
dev-kid verify                  # Anti-hallucination check
dev-kid validate                # System integrity check
```

## Key Concepts

### Memory Bank (Auto-Updated with Speckit)

The Memory Bank is your **institutional memory**:

```
memory-bank/
├── shared/                    # Team knowledge
│   ├── projectbrief.md       # Vision (from spec)
│   ├── systemPatterns.md     # Architecture (from tasks)
│   ├── techContext.md        # Tech stack (from implementation)
│   └── productContext.md     # Requirements (from spec)
└── private/$USER/             # Your context
    ├── activeContext.md      # Current focus (from tasks)
    ├── progress.md           # Metrics (from git history)
    └── worklog.md            # Daily log (from checkpoints)
```

**With Speckit**: Files update automatically during checkpoints
**Without Speckit**: You manually edit these files

### Task Format (Important!)

Use **backticks** around file paths for proper file lock detection:

```markdown
Good:
- [ ] TASK-001: Create model in `src/models/user.py`

Bad:
- [ ] TASK-001: Create model in src/models/user.py
```

Backticks guarantee the orchestrator detects file locks correctly!

### Constitution Enforcement

When tasks include constitution rules:

```markdown
- [ ] TASK-001: Implement auth in `src/auth.py`
  **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED
```

At checkpoint, the system:
1. Reads `src/auth.py`
2. Validates against rules
3. If violations found → **BLOCKS** checkpoint
4. You must fix violations
5. Re-run checkpoint
6. Only proceeds when validation passes

### Wave Execution

Tasks are grouped into waves based on:
- **File locks**: Tasks modifying same file run sequentially
- **Dependencies**: Tasks with "after TASK-123" run sequentially
- **Parallelization**: Tasks with no conflicts run in parallel

```
Wave 1: TASK-001, TASK-002, TASK-003 (parallel - different files)
Wave 2: TASK-004 (sequential - modifies same file as TASK-001)
```

## Troubleshooting

### Issue: Checkpoint Blocked by Constitution Violations

```
❌ Wave 1 Checkpoint FAILED - Constitution Violations Detected

Violations:
  TASK-001 (src/auth.py):
    - [ERROR] TYPE_HINTS_REQUIRED: Function authenticate() missing return type
    - [ERROR] DOCSTRINGS_REQUIRED: Function authenticate() missing docstring
```

**Fix:**
1. Add type hints and docstrings to `src/auth.py`
2. Mark task `[x]` in tasks.md
3. Re-run: `dev-kid execute`

### Issue: Wave Won't Proceed

```
⚠️  Cannot proceed to Wave 2 - incomplete tasks in Wave 1
```

**Fix:**
Check `tasks.md` - tasks must be marked `[x]`:

```bash
cat tasks.md | grep "\[x\]"  # Should show completed tasks
```

Change `[ ]` to `[x]` for completed tasks.

### Issue: Watchdog Not Found

```
❌ Rust watchdog binary not found
```

**Fix:**
```bash
cd rust-watchdog
cargo build --release
cd ..

# Or skip watchdog (core features work without it)
```

### Issue: Tasks Not Auto-Generated

If `/speckit.tasks` doesn't create tasks:

**Check:**
1. Is there a spec file? `ls .specify/specs/*/spec.md`
2. Is the spec complete? `cat .specify/specs/001-*/spec.md`
3. Re-run: `/speckit.tasks`

## Next Steps

1. **Read the full docs**:
   - [README.md](README.md) - Complete feature documentation
   - [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Architecture deep dive
   - [DEV_KID.md](DEV_KID.md) - Implementation reference

2. **Explore advanced features**:
   - Custom constitution rules
   - GitHub issue sync (`dev-kid gh-sync`)
   - Custom wave strategies
   - Multi-user support

3. **Join the community**:
   - Report issues: [GitHub Issues](https://github.com/yourusername/dev-kid/issues)
   - Contribute: [CONTRIBUTING.md](docs/development/CONTRIBUTING.md)

---

**Quick Start Guide v2.0** | Dev-Kid v2.0 | Speckit Integration | Get Productive in 5 Minutes

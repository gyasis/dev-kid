# System Patterns: Dev-Kid v2.0

## Architecture Patterns

### 1. Wave-Based Orchestration Pattern

**Pattern**: Convert linear task sequences into parallelized execution waves with dependency management.

**Implementation**:
```
Task List → Dependency Graph → Wave Groups → Sequential Execution
```

**Key Components**:
- **Orchestrator**: Parses tasks.md, extracts dependencies, creates execution_plan.json
- **Wave Executor**: Executes waves sequentially with verification between each
- **Checkpoint Protocol**: Mandatory validation before progressing to next wave

**Critical Rules**:
1. Tasks modifying the same file CANNOT run in the same wave (file locking)
2. Explicit dependencies ("after T123") create sequential ordering
3. Implicit dependencies (same-file edits) are auto-detected
4. ALL tasks must be marked [x] in tasks.md before wave completes
5. Verification failure HALTS execution (no progression with incomplete work)

**File Lock Detection**:
- Regex extracts file paths from task descriptions
- Backtick convention guarantees detection: `src/file.py`
- Plain paths detected with heuristics
- Same-file tasks automatically sequenced

**Complexity**: O(n²) for dependency analysis, practical limit ~1000 tasks

### 2. Process-Based Monitoring Pattern

**Pattern**: Background daemon with disk-based state persistence for context compression resilience.

**Implementation**:
```
Background Process → 5-Minute Checks → Disk State → Survives Compression
```

**Key Components**:
- **Task Watchdog**: Python daemon running as background process
- **State File**: `.claude/task_timers.json` persisted to disk
- **Sync Mechanism**: Reads tasks.md to detect [x] completions

**Critical Rules**:
1. Watchdog runs independently of AI agent sessions
2. State persisted after every check (5-minute intervals)
3. Tasks exceeding 7-minute guideline trigger check-in (not auto-stop)
4. Stalled tasks (>15 min no activity) generate warnings
5. Process continues until explicitly stopped or task marked complete

**State Schema**:
```json
{
  "running_tasks": {
    "TASK-001": {
      "description": "...",
      "started_at": "ISO8601",
      "last_checked": "ISO8601",
      "status": "running"
    }
  },
  "completed_tasks": {...},
  "warnings": [...]
}
```

### 3. Memory Bank Pattern

**Pattern**: 6-tier institutional memory with shared/private separation.

**Structure**:
```
memory-bank/
├── shared/              # Team knowledge (version controlled)
│   ├── projectbrief.md      # North Star vision
│   ├── systemPatterns.md    # This file - architecture patterns
│   ├── techContext.md       # Tech stack, setup, constraints
│   └── productContext.md    # User needs, strategy
└── private/$USER/       # Per-user context (version controlled)
    ├── activeContext.md     # Current focus, next actions
    ├── progress.md          # Task metrics, completion status
    └── worklog.md           # Daily work entries
```

**Update Pattern**:
1. Read current state from Memory Bank files
2. Extract new information (git diff, tasks.md stats, git log)
3. Generate updated Markdown content
4. Write to file atomically
5. Append summary to activity_stream.md

**Critical Rules**:
1. ALWAYS read ALL memory bank files before updating
2. Maintain consistency across all documentation
3. Update activeContext.md with every significant change
4. Update progress.md after task completions
5. Document decisions and rationale, not just changes

### 4. Checkpoint Protocol Pattern

**Pattern**: Mandatory verification before progression with git-based state snapshots.

**Flow**:
```
Wave Complete → Verify tasks.md → Update progress.md → Git Commit → Next Wave
                     ↓ FAIL
                 HALT EXECUTION
```

**Implementation**:
1. Wave executor calls `verify_wave_completion()`
2. Checks tasks.md for `[x]` on all wave tasks
3. If ANY task incomplete → HALT with clear error
4. If verification passes → Update Memory Bank
5. Create git checkpoint with semantic message
6. Only then proceed to next wave

**Critical Rules**:
1. Agents MUST mark tasks [x] in tasks.md before wave ends
2. No progression without complete verification
3. Git commit is source of truth for checkpoints
4. Commit message format: `[CHECKPOINT-W{wave_id}] {description}`
5. Co-author attribution: `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`

**Prevents**:
- Incomplete work progressing to next phase
- Lost work during context compression
- Inconsistent state between Memory Bank and git
- Silent failures in task execution

### 5. Context Protection Pattern

**Pattern**: Layered state management with different token budgets and persistence strategies.

**Layers**:
```
active_stack.md         <500 tokens   Current focus
activity_stream.md      Append-only   Event log
AGENT_STATE.json        ~1k tokens    Agent coordination
system_bus.json         ~500 tokens   Inter-agent messages
task_timers.json        ~2k tokens    Watchdog state
session_snapshots/      ~3k tokens    Recovery points
```

**Update Strategy**:
- **Active Stack**: Overwrite on focus change (current work only)
- **Activity Stream**: Append-only, never truncate (full history)
- **Agent State**: Update on coordination events
- **System Bus**: Ring buffer (last 50 messages)
- **Task Timers**: Update every watchdog check
- **Snapshots**: Create on finalize, load on recall

**Critical Rules**:
1. Active stack is ephemeral (regenerate on compression)
2. Activity stream is permanent (git-tracked)
3. JSON state files are atomic writes (no partial updates)
4. Snapshots include complete mental state + next steps
5. All state files survive context compression

### 6. Constitution Enforcement Pattern

**Pattern**: Project-specific rules extracted from tasks.md and enforced at checkpoint validation.

**Implementation**:
```
tasks.md (constitution rules) → Orchestrator → execution_plan.json → Wave Executor → Checkpoint Validation
                                                                              ↓
                                                                    Constitution.validate_output()
```

**Key Components**:
- **Constitution Parser**: Extracts rules from `@constitution:` metadata in tasks.md
- **Orchestrator Integration**: Parses constitution rules and includes in execution_plan.json
- **Wave Executor**: Loads Constitution from memory-bank, validates at checkpoint
- **Rust Watchdog**: Stores constitution rules in process registry (context-resilient)

**Constitution Rules Format**:
```markdown
@constitution: {
  "type_hints": "required",
  "docstrings": "required",
  "no_hardcoded_secrets": true,
  "test_coverage": 80
}
```

**Validation Points**:
1. After each wave completes
2. Before git checkpoint is created
3. Constitution.validate_output() runs on all modified files
4. Violations HALT progression (same as task completion verification)

**Critical Rules**:
1. Constitution loaded from `memory-bank/shared/constitution.yml` (if exists)
2. Task-specific rules override global constitution
3. Validation enforces: type hints, docstrings, secrets detection, test coverage
4. Context-resilient: Rules persisted in rust-watchdog process registry
5. Violations generate clear error messages with remediation guidance

**Prevents**:
- Code quality regressions (missing type hints, undocumented functions)
- Security issues (hardcoded secrets in commits)
- Test coverage decay (untested code reaching production)
- Technical debt accumulation (bypassing project standards)

### 7. Skills Auto-Activation Pattern

**Pattern**: Keyword-triggered workflow automation with zero coordination overhead.

**Mechanism**:
```
User/Agent mentions keyword → Claude Code detects → Executes skill script
```

**Skills**:
- `sync_memory.sh`: Keywords "sync memory", "update memory bank"
- `checkpoint.sh`: Keywords "checkpoint", "create checkpoint"
- `verify_existence.sh`: Keywords "verify files", "check existence"
- `maintain_integrity.sh`: Keywords "validate system", "check integrity"
- `finalize_session.sh`: Keywords "finalize", "end session"
- `recall.sh`: Keywords "recall", "resume session"

**Critical Rules**:
1. Skills are idempotent (safe to run multiple times)
2. All skills start with `set -e` (fail fast)
3. Clear user feedback with status indicators (✅ ❌ ⚠️  ℹ️)
4. No external dependencies (Bash standard utilities only)
5. Skills installed to `~/.claude/skills/planning-enhanced/`

## Technical Gotchas

### 1. Git Hook Silent Failures

**Issue**: Post-commit hook doesn't execute but doesn't show error.

**Cause**: Hook file not executable or doesn't exist.

**Solution**:
```bash
chmod +x .git/hooks/post-commit
test -f .git/hooks/post-commit || echo "Hook missing!"
```

### 2. File Lock Over-Detection

**Issue**: Orchestrator detects file paths that aren't actual files (e.g., URLs with .py extension).

**Cause**: Regex-based extraction is heuristic, not perfect.

**Solution**: Use backtick convention explicitly: `src/file.py`

**Workaround**: Accept conservative over-detection (prefer safety over parallelism)

### 3. Wave Executor Halts on Incomplete Tasks

**Issue**: Wave executor stops with error when tasks aren't marked [x].

**Cause**: Mandatory verification protocol (this is by design, not a bug).

**Solution**: Agents MUST update tasks.md as part of task completion workflow.

**Pattern**:
```bash
# After completing task work:
# 1. Mark task in tasks.md: - [x] Task description
# 2. Save file
# 3. Only then consider task complete
```

### 4. Watchdog Process Management

**Issue**: Multiple watchdog processes running or orphaned process.

**Cause**: Watchdog not stopped properly, or start called multiple times.

**Detection**:
```bash
ps aux | grep task_watchdog.py
```

**Solution**:
```bash
# Stop watchdog cleanly
dev-kid watchdog-stop

# Force kill if needed
pkill -f task_watchdog.py
```

### 5. JSON State File Corruption

**Issue**: task_timers.json or AGENT_STATE.json becomes invalid JSON.

**Cause**: Non-atomic writes or partial updates during crash.

**Detection**:
```bash
python3 -m json.tool .claude/task_timers.json
```

**Recovery**:
```bash
# Backup corrupted file
mv .claude/task_timers.json .claude/task_timers.json.bak

# Initialize empty state
echo '{"running_tasks": {}, "completed_tasks": {}, "warnings": []}' > .claude/task_timers.json
```

### 6. Tasks.md Parsing Ambiguity

**Issue**: Orchestrator misparses task descriptions with special characters.

**Cause**: Regex-based parsing doesn't handle all edge cases.

**Workaround**: Use simple task descriptions, avoid nested lists or special markdown in task lines.

**Pattern**:
```markdown
# Good
- [ ] Implement user authentication in `auth.py`
- [ ] Create tests for auth module (depends on previous)

# Problematic
- [ ] Implement user auth [with JWT tokens] in `auth.py` (see: #123)
```

### 7. Memory Bank Stale State

**Issue**: activeContext.md or progress.md out of sync with actual project state.

**Cause**: Memory sync not triggered after changes.

**Detection**:
```bash
# Check last update time
ls -lh memory-bank/private/$USER/activeContext.md
```

**Solution**:
```bash
dev-kid sync-memory
```

**Prevention**: Trigger sync after significant changes, before checkpoints, during finalize.

### 8. Session Snapshot Bloat

**Issue**: Too many session snapshots filling disk space.

**Cause**: Snapshots created frequently but never cleaned up.

**Detection**:
```bash
ls -lh .claude/session_snapshots/
```

**Cleanup**:
```bash
# Keep last 10 snapshots
cd .claude/session_snapshots/
ls -t snapshot_*.json | tail -n +11 | xargs rm -f
```

## Implementation Patterns

### 1. Atomic State Updates

**Pattern**: Read-modify-write with atomic replacement.

```python
# Read current state
with open(state_file, 'r') as f:
    state = json.load(f)

# Modify
state['new_field'] = 'value'

# Write atomically (write to temp, then rename)
temp_file = f"{state_file}.tmp"
with open(temp_file, 'w') as f:
    json.dump(state, f, indent=2)
os.rename(temp_file, state_file)
```

### 2. Error Handling in Skills

**Pattern**: Fail fast with clear error messages.

```bash
#!/usr/bin/env bash
set -e  # Exit on any error

# Validation
if [[ ! -f tasks.md ]]; then
    echo "❌ Error: tasks.md not found" >&2
    exit 1
fi

# Operation
echo "ℹ️  Processing tasks.md..."
# ... do work ...
echo "✅ Success: Task completed"
```

### 3. Dependency Extraction

**Pattern**: Multi-strategy extraction with fallbacks.

```python
# Strategy 1: Explicit dependencies
explicit_deps = re.findall(r'(?:after|depends on|requires)\s+([TW]\d+)', desc)

# Strategy 2: File paths in backticks
file_paths = re.findall(r'`([^`]+)`', desc)

# Strategy 3: Common file path patterns
plain_paths = re.findall(r'\b\w+(?:/\w+)*\.(?:py|js|ts|go|rs|java)\b', desc)

# Combine strategies
all_deps = explicit_deps + detect_file_conflicts(file_paths + plain_paths)
```

### 4. Wave Verification

**Pattern**: Parse-validate-halt on failure.

```python
def verify_wave_completion(wave_id: int, tasks: List[Dict]) -> bool:
    if not os.path.exists('tasks.md'):
        print(f"❌ Error: tasks.md not found")
        return False

    with open('tasks.md', 'r') as f:
        content = f.read()

    incomplete = []
    for task in tasks:
        task_id = task['id']
        # Check for [x] marker
        if not re.search(f'{task_id}.*\\[x\\]', content):
            incomplete.append(task_id)

    if incomplete:
        print(f"❌ Wave {wave_id} incomplete: {', '.join(incomplete)}")
        print("ℹ️  Mark tasks [x] in tasks.md before progressing")
        return False

    return True
```

### 5. Memory Bank Update Template

**Pattern**: Read-extract-generate-write-log.

```bash
#!/usr/bin/env bash
set -e

# 1. Read current state
current_context=$(cat memory-bank/private/$USER/activeContext.md)

# 2. Extract new information
git_changes=$(git diff --stat)
task_stats=$(grep -c '\[x\]' tasks.md || echo 0)
recent_commits=$(git log --oneline -5)

# 3. Generate updated content
updated_content=$(cat <<EOF
# Active Context - $(date +%Y-%m-%d)

## Current Focus
$(extract_focus_from_context "$current_context")

## Recent Changes
$git_changes

## Task Progress
Completed: $task_stats

## Recent Commits
$recent_commits
EOF
)

# 4. Write to file
echo "$updated_content" > memory-bank/private/$USER/activeContext.md

# 5. Log to activity stream
echo "### $(date) - Memory Sync" >> .claude/activity_stream.md
echo "- Updated activeContext.md" >> .claude/activity_stream.md
```

## Architectural Decisions

### 1. Bash CLI with Python Modules

**Decision**: Use Bash for CLI, delegate complex logic to Python.

**Rationale**:
- Bash: Universal on Unix, fast startup, easy system integration
- Python: Better data structures, type hints, testability

**Trade-off**: Two languages, but each used for its strengths

### 2. JSON for State, Markdown for Memory

**Decision**: JSON for machine state, Markdown for human knowledge.

**Rationale**:
- JSON: Portable, structured, easy parsing, schema validation
- Markdown: Human-readable, git-friendly, AI-friendly

**Trade-off**: No unified format, but optimal for each use case

### 3. Process-Based Watchdog

**Decision**: Background daemon, not token-based polling.

**Rationale**:
- Survives context compression
- Independent of AI agent lifecycle
- Persistent state monitoring

**Trade-off**: Process management complexity, but resilience is critical

### 4. Mandatory Verification

**Decision**: HALT execution if tasks incomplete, no auto-progression.

**Rationale**:
- Data integrity over convenience
- Prevents silent failures
- Forces explicit completion protocol

**Trade-off**: More manual work for agents, but prevents data loss

### 5. Zero External Dependencies

**Decision**: Python standard library only, no pip packages.

**Rationale**:
- Universal installation (no dependency hell)
- Faster startup
- More stable (no version conflicts)

**Trade-off**: Limited functionality, but adequate for dev tool

## Performance Patterns

### Token Efficiency
- Planning overhead: <10% of context window
- Memory Bank: 2-5k tokens
- Active Stack: <500 tokens
- Execution Plan: 1-3k tokens

### Time Complexity
- Orchestrator: O(n²) dependency analysis
- Wave Executor: O(waves × tasks_per_wave)
- Watchdog: O(running + completed tasks)

### Space Complexity
- Memory Bank: O(project knowledge)
- Execution Plan: O(total tasks)
- Watchdog State: O(running + completed)

---

**System Patterns v2.0** - Architecture patterns, gotchas, and implementation guidance for dev-kid

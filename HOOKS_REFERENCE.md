# Claude Code Hooks Reference

**Dev-Kid Automated State Management & GitHub Synchronization**

Dev-kid uses Claude Code's hooks system to automate state management, ensuring project consistency across sessions and context compression events. This document explains the hooks architecture and how it integrates with the dev-kid workflow.

## Overview

Claude Code provides 14 lifecycle hook events that fire during AI agent execution. Dev-kid leverages 6 critical hooks to:

1. **Auto-backup state before context compression** (PreCompact)
2. **Proactively trigger compression between waves** (when 5+ personas active)
3. **Auto-sync GitHub issues after task completion** (TaskCompleted)
4. **Auto-format code after file edits** (PostToolUse)
5. **Inject project context into prompts** (UserPromptSubmit)
6. **Restore context on session start** (SessionStart)
7. **Finalize session on exit** (SessionEnd)

## Proactive Pre-Compaction Strategy

**NEW**: Dev-kid proactively triggers context compression **between waves** when 5+ personas/agents are detected. This prevents mid-wave compression (data loss risk) by controlling WHEN compression happens.

**How It Works**:
1. After wave checkpoint completes
2. Context compactor checks active persona count
3. If 5+ personas detected → triggers PreCompact hook proactively
4. Hook backs up state to disk
5. Context compresses at safe boundary
6. Next wave starts with clean context

**Benefits**:
- ✅ Controlled compression timing (between waves, not during)
- ✅ Full state backup before compression
- ✅ No task interruption
- ✅ Debugging possible before compression

**Detection Methods**:
- AGENT_STATE.json: Counts agents with status: active/running/in_progress
- Task tool usage: Scans activity_stream.md for recent personas
- Uses max(method1, method2) for conservative detection

**Threshold**: 5+ personas (tunable via `ContextCompactor.persona_threshold`)

**See**: [CONTEXT_COMPACTION_STRATEGY.md](CONTEXT_COMPACTION_STRATEGY.md) for complete details

## Architecture

```
Claude Code Lifecycle
        ↓
   Hook Event Fires
        ↓
.claude/settings.json → .claude/hooks/{hook-name}.sh
        ↓                           ↓
    Reads stdin            Executes dev-kid commands
        ↓                           ↓
  Processes event        Updates state files
        ↓                           ↓
  Returns JSON           Syncs GitHub / creates checkpoints
        ↓
Claude continues execution
```

## Hook Deployment Model (symlinks)

Since v2.3.0, `dev-kid init` does **not** copy hook scripts into your
project. It **symlinks** them to the install-managed canonical source.

```
~/.dev-kid/templates/.claude/hooks/post-tool-use.sh   ← canonical source (versioned with dev-kid)
                ▲
                │  symlink (ln -sfn, absolute target)
                │
<project>/.claude/hooks/post-tool-use.sh              ← what Claude Code runs
```

| Artifact | How `init` deploys it | Why |
|---|---|---|
| Hook scripts (`.claude/hooks/*.sh`) | **symlink** → `~/.dev-kid/templates/.claude/hooks/` | one source of truth; a template edit propagates to every project; no drifting copies; `.claude/` is gitignored so links are never committed |
| `.claude/settings.json` | **copy** | per-project config you tweak (e.g. `DEV_KID_HOOKS_ENABLED`, hook wiring) — must be able to differ per project |

**Why symlinks over copies or a global install:**
- *Copies* (the pre-2.3.0 behavior) drift — edit a template and existing
  projects keep running their stale copy until re-init.
- *Global hooks* in `~/.claude/` would fire in **every** repo on the machine,
  including non-dev-kid ones — dangerous for the auto-checkpoint/commit hooks.
  Symlinks keep hooks **per-project** (only where you ran `init`) while still
  pointing at one canonical, versioned source.

### Failure mode + repair

A symlink breaks if the dev-kid install moves or is removed (the target no
longer exists). Claude Code then can't run that hook.

- **Detect:** `dev-kid init-check` reports `❌ FAIL … BROKEN symlinks: <names>`.
- **Repair:** re-run `dev-kid init` in the project — `ln -sfn` re-points every
  link to the current install. (Re-init is safe: `settings.json` and
  `.dk/tasks.md` are left untouched.)

### Adopting the model in an existing project

Projects initialized before v2.3.0 have *copied* hooks. They keep working.
To switch them to symlinks (and get future template edits automatically),
just re-run `dev-kid init` there.

## Hook Configuration

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreCompact": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/pre-compact.sh"
          }
        ]
      }
    ],
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/task-completed.sh"
          }
        ]
      }
    ]
  },
  "hookSettings": {
    "timeout": 30000,
    "env": {
      "DEV_KID_HOOKS_ENABLED": "true",
      "DEV_KID_AUTO_SYNC_GITHUB": "true",
      "DEV_KID_AUTO_CHECKPOINT": "true"
    }
  }
}
```

### Hook Properties

- **type**: Must be `"command"` for shell script hooks
- **command**: Path to executable script (relative to project root)

### Environment Variables

- `DEV_KID_HOOKS_ENABLED`: Master switch for all hooks (default: true)
- `DEV_KID_AUTO_SYNC_GITHUB`: Auto-sync tasks to GitHub issues (default: true)
- `DEV_KID_AUTO_CHECKPOINT`: Auto-create git checkpoints (default: true)

## Hook Events

### 1. PreCompact Hook (CRITICAL)

**When**: Fires BEFORE Claude compresses conversation context (memory limit)

**Purpose**: Emergency state backup to prevent data loss during compression

**Script**: `.claude/hooks/pre-compact.sh`

**Actions**:
- Backs up `AGENT_STATE.json` with timestamp
- Updates `system_bus.json` with compression event
- Auto-creates git checkpoint if uncommitted changes exist
- Logs event to `activity_stream.md`

**Exit Code**: 0 (always allows compression to proceed)

**Why Critical**: Context compression happens automatically when token limit reached. Without this hook, Claude might lose track of current wave, task status, or pending checkpoints. This hook ensures state is persisted to disk BEFORE compression occurs.

**Example Scenario**:
```
Claude executing Wave 3, Task 12 of 15
  ↓ Token limit reached (190k/200k)
  ↓ PreCompact hook fires
  ↓ Backs up AGENT_STATE.json (wave=3, task=12)
  ↓ Creates emergency checkpoint
  ↓ Context compresses
  ↓ Claude resumes with state preserved on disk
```

### 2. TaskCompleted Hook

**When**: Fires when Claude Code marks a task complete via its internal task system (TodoWrite). It does NOT fire on manual edits to tasks.md.

**Purpose**: Auto-checkpoint and sync GitHub issues

**Script**: `.claude/hooks/task-completed.sh`

**Actions**:
- Checks if `tasks.md` was modified
- Calls `dev-kid gh-sync` to update GitHub issues
- Creates micro-checkpoint if auto-checkpoint enabled
- Logs completion to `activity_stream.md`

**Exit Code**: 0 (non-blocking)

**Why Important**: Ensures GitHub issues stay in sync with tasks.md automatically. Previously, users had to manually run `dev-kid gh-sync` after each task. Now it happens automatically.

**Example Scenario**:
```
Task: "Implement user authentication" [x]
  ↓ TaskCompleted hook fires
  ↓ Detects tasks.md changed
  ↓ Runs dev-kid gh-sync
  ↓ GitHub issue #123 updated: Status → Completed
  ↓ Creates git checkpoint: "[TASK-COMPLETE] Auto-checkpoint"
```

### 3. PostToolUse Hook

**When**: Fires after Claude executes a tool (Edit, Write, Bash, etc.)

**Purpose**: Auto-format code files after editing

**Script**: `.claude/hooks/post-tool-use.sh`

**Actions**:
- Detects if tool was Edit or Write
- Extracts file path from tool metadata
- Runs language-specific formatters:
  - Python: `black`, `isort`
  - JavaScript/TypeScript: `prettier`
  - Bash: `shfmt`
- Returns success (non-blocking)

**Exit Code**: 0 (always succeeds, even if formatters not installed)

**Why Useful**: Ensures consistent code style without manual intervention. Claude can focus on logic while formatters handle style.

**Example Scenario**:
```
Claude edits src/auth.py
  ↓ PostToolUse hook fires
  ↓ Detects file is Python
  ↓ Runs: black src/auth.py
  ↓ Runs: isort src/auth.py
  ↓ File auto-formatted
```

### 4. UserPromptSubmit Hook

**When**: Fires BEFORE Claude processes user's prompt

**Purpose**: Inject project context into Claude's working memory

**Script**: `.claude/hooks/user-prompt-submit.sh`

**Actions**:
- Reads current git branch
- Extracts constitution rules (top 5 rules)
- Calculates task progress (X/Y completed)
- Identifies current wave from `execution_plan.json`
- Checks for recent errors in `activity_stream.md`
- Outputs context as markdown to stdout

**Exit Code**: 0 (outputs context, then allows prompt to process)

**Why Powerful**: Claude always knows:
- Which branch you're on (prevents cross-branch confusion)
- What constitution rules apply (enforces quality standards)
- Current progress (avoids redundant work)
- Recent errors (proactive debugging)

**Example Output**:
```markdown
---
🤖 **Project Context** (auto-injected)
📍 Current branch: feature/user-auth
📜 Active constitution rules:
## Development Principles
- Always write tests before implementation
- Use type hints for all Python functions
📊 Task progress: 12/15 completed
🌊 Current wave: Wave 3
---
```

### 5. SessionStart Hook

**When**: Fires when Claude Code session starts (first prompt in new session)

**Purpose**: Restore context from last session

**Script**: `.claude/hooks/session-start.sh`

**Actions**:
- Calls `dev-kid recall` to restore from last snapshot
- Updates `AGENT_STATE.json` with new session ID
- Logs session start to `activity_stream.md`

**Exit Code**: 0 (non-blocking)

**Why Essential**: Ensures continuity across sessions. When you close Claude Code and reopen tomorrow, this hook automatically loads where you left off.

**Example Scenario**:
```
User opens Claude Code (new day)
  ↓ SessionStart hook fires
  ↓ Runs: dev-kid recall
  ↓ Loads: snapshot_latest.json
  ↓ Restores:
      - Last wave completed: Wave 2
      - Next steps: ["Start Wave 3", "Review constitution"]
      - Blockers: []
  ↓ Claude resumes from exact state
```

### 6. SessionEnd Hook

**When**: Fires when Claude Code session ends (user closes, timeout, crash)

**Purpose**: Finalize session and create recovery snapshot

**Script**: `.claude/hooks/session-end.sh`

**Actions**:
- Calls `dev-kid finalize` to create final snapshot
- Creates git checkpoint if uncommitted work exists
- Updates `AGENT_STATE.json` with finalization timestamp
- Logs session end to `activity_stream.md`

**Exit Code**: 0 (non-blocking, allows session to close)

**Why Critical**: Ensures no work is lost. Even if Claude crashes mid-task, the SessionEnd hook (if it fires) will snapshot current state for recovery.

**Example Scenario**:
```
User closes Claude Code (work in progress)
  ↓ SessionEnd hook fires
  ↓ Runs: dev-kid finalize
  ↓ Creates: snapshot_2026-02-14_15-30-45.json
  ↓ Links: snapshot_latest.json → snapshot_2026-02-14_15-30-45.json
  ↓ Creates git checkpoint: "[SESSION-END] Auto-save"
  ↓ Session closes gracefully
```

## Hook Communication Protocol

Hooks communicate with Claude via stdin/stdout using JSON:

### Input (stdin)

Claude sends event metadata to hook via stdin:

```json
{
  "event": "TaskCompleted",
  "timestamp": "2026-02-14T15:30:45Z",
  "metadata": {
    "task_id": "TASK-012",
    "description": "Implement user authentication"
  }
}
```

### Output (stdout)

Hook returns status via stdout:

```json
{
  "status": "success",
  "message": "GitHub issue #123 synced"
}
```

### Exit Codes

- **0**: Success (hook completed normally)
- **1**: Error (hook failed, but allow Claude to continue)
- **2**: Block (prevent Claude from continuing - RARE, use only for critical errors)

## Integration with Dev-Kid Commands

Hooks automatically call dev-kid commands:

| Hook | Dev-Kid Command | Purpose |
|------|-----------------|---------|
| PreCompact | `dev-kid checkpoint "[PRE-COMPACT]..."` | Emergency save before compression |
| TaskCompleted | `dev-kid gh-sync` | Sync tasks to GitHub issues |
| TaskCompleted | `dev-kid checkpoint "[TASK-COMPLETE]..."` | Micro-checkpoint after task |
| SessionStart | `dev-kid recall` | Restore from last snapshot |
| SessionEnd | `dev-kid finalize` | Create final snapshot |

## State Files Updated by Hooks

Hooks read/write the following files:

- `.claude/AGENT_STATE.json`: Agent coordination state
- `.claude/activity_stream.md`: Append-only event log
- `.claude/system_bus.json`: Inter-agent messaging
- `tasks.md`: Task completion status
- `execution_plan.json`: Current wave/phase
- `memory-bank/shared/.constitution.md`: Quality rules

## Configuration

### Enabling/Disabling Hooks

`DEV_KID_HOOKS_ENABLED` is the **master switch for all hooks** (default:
`true`). Every hook script checks it first and exits early when it's
`false`, so flipping it off cleanly silences the entire dev-kid hook layer
(auto-checkpoint commits, the `🤖 Project Context` prompt banner, the
`git reset --hard` guard, session-start recall, etc.) **without removing
any wiring** — flip it back to re-enable.

Pick the scope you actually want:

| Method | Scope | Persists across sessions? | Use when |
|---|---|---|---|
| `export DEV_KID_HOOKS_ENABLED=false` | current shell only | ❌ gone next terminal/session | quick one-off; testing |
| `"DEV_KID_HOOKS_ENABLED": "false"` in the project's `.claude/settings.json` `env` block | that project, every session | ✅ yes | **you're done dev-kid-ing a repo and don't want hooks firing there anymore** |

**Persistently deactivate dev-kid for a project** (the common case once a
feature is shipped — stops auto-commits + banner injection on every future
session in that repo):

```jsonc
// <project>/.claude/settings.json
{
  "env": {
    "DEV_KID_HOOKS_ENABLED": "false"
  },
  "hooks": { /* ...leave the wiring intact... */ }
}
```

**Re-activate** later: set it to `"true"` or delete the `env` line. The hook
scripts and `dev-kid.yml` are untouched, so no `dev-kid init` is needed.

> This is a *deactivation*, not an uninstall. dev-kid itself (CLI, Rust
> watchdog, config) stays fully operational — you're only telling the
> harness not to fire the hooks in this one repo.

**Disable all hooks (current shell, temporary)**:
```bash
export DEV_KID_HOOKS_ENABLED=false
```

**Disable GitHub sync only**:
```bash
export DEV_KID_AUTO_SYNC_GITHUB=false
```

**Disable auto-checkpoints only**:
```bash
export DEV_KID_AUTO_CHECKPOINT=false
```

### Custom Hook Scripts

You can create custom hooks by:

1. Create script: `.claude/hooks/my-custom-hook.sh`
2. Add to `.claude/settings.json`:
```json
{
  "hooks": {
    "TaskCompleted": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/my-custom-hook.sh"
          }
        ]
      }
    ]
  }
}
```

## Debugging Hooks

### Check Hook Execution

```bash
# View hook activity in activity stream
tail -n 50 .claude/activity_stream.md | grep -i "hook\|checkpoint\|sync"

# View system bus events
jq '.events[] | select(.agent | contains("hook"))' .claude/system_bus.json
```

### Test Hooks Manually

```bash
# Test PreCompact hook
echo '{"event":"PreCompact"}' | .claude/hooks/pre-compact.sh

# Test TaskCompleted hook
echo '{"event":"TaskCompleted","metadata":{"task_id":"TEST-001"}}' | .claude/hooks/task-completed.sh

# Test UserPromptSubmit hook
echo '{"event":"UserPromptSubmit","prompt":"What is the current branch?"}' | .claude/hooks/user-prompt-submit.sh
```

### Common Issues

**Hook not firing**:
- Check `.claude/settings.json` exists
- Verify script is executable: `chmod +x .claude/hooks/*.sh`
- Check `DEV_KID_HOOKS_ENABLED=true`

**GitHub sync fails**:
- Ensure `gh` CLI installed and authenticated
- Check GitHub repo is configured: `gh repo view`

**Formatters not running**:
- Install formatters: `pip install black isort`, `npm install -g prettier`
- Formatters fail silently (won't break hook)

## Performance Impact

Hooks are designed to be lightweight:

- **PreCompact**: ~200ms (critical path, blocking)
- **TaskCompleted**: ~500ms (non-blocking, runs in background)
- **PostToolUse**: ~100ms (non-blocking, only for edited files)
- **UserPromptSubmit**: ~50ms (blocking, but very fast)
- **SessionStart**: ~300ms (non-blocking, one-time at session start)
- **SessionEnd**: ~400ms (non-blocking, one-time at session end)

**Total overhead**: <2 seconds per task (99% in background)

## Security Considerations

Hooks have access to:
- Full project filesystem
- Git repository
- GitHub API (via `gh` CLI)
- Environment variables

**Best Practices**:
- Hooks should never modify code without user knowledge
- Always log actions to `activity_stream.md`
- Never commit sensitive data (hooks respect `.gitignore`)
- Use exit code 0 for non-critical failures (fail gracefully)

## Advanced Patterns

### Conditional Hook Execution

```bash
# Only sync GitHub if in main/master branch
BRANCH=$(git branch --show-current)
if [[ "$BRANCH" == "main" ]] || [[ "$BRANCH" == "master" ]]; then
    dev-kid gh-sync
fi
```

### Multi-Hook Coordination

```bash
# PreCompact signals to TaskCompleted via system bus
echo '{"event":"pre_compact_fired"}' | jq '.' >> .claude/system_bus.json

# TaskCompleted checks bus before syncing
if jq -e '.events[] | select(.event=="pre_compact_fired")' .claude/system_bus.json; then
    echo "Skipping sync - compression in progress"
    exit 0
fi
```

### Hook Chaining

```bash
# SessionStart → calls SessionEnd of previous session (cleanup orphaned processes)
if [ -f .claude/AGENT_STATE.json ]; then
    LAST_STATUS=$(jq -r '.status' .claude/AGENT_STATE.json)
    if [ "$LAST_STATUS" != "finalized" ]; then
        .claude/hooks/session-end.sh < /dev/null  # Finalize previous session
    fi
fi
```

## Future Enhancements

Planned improvements to hooks system:

1. **Bidirectional GitHub Sync**: Sync GitHub issue changes → tasks.md
2. **Constitution Validation Hook**: Block commits that violate constitution rules
3. **Wave Boundary Hook**: Fire between waves (not just tasks)
4. **Conflict Detection Hook**: Warn if multiple users editing same file
5. **Performance Profiling Hook**: Track token usage, execution time per task

## References

- [Claude Code Hooks Documentation](https://docs.anthropic.com/claude/code/hooks) (official)
- [Dev-Kid Architecture](ARCHITECTURE.md)
- [Git Workflow Reference](CLI_REFERENCE.md#git-commands)
- [GitHub Sync Implementation](cli/github_sync.py)

---

**Hooks enable dev-kid to maintain state automatically across sessions and context compression, ensuring project consistency without manual intervention.**

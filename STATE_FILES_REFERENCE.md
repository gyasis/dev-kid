# Dev-Kid State Files Reference

**Audience:** humans + AI agents who need to inspect, debug, or safely modify dev-kid's runtime state.

Every state file dev-kid maintains under `.claude/` is documented here: its real schema, who writes it, when it gets written, and whether it's safe to edit by hand. **No black boxes** — if dev-kid stores it, this doc explains it.

> If you find a file under `.claude/` not listed here, that's a documentation bug — please open an issue.

---

## Map: file → writer → trigger

| File | Type | Written by | Triggered when | Safe to edit? |
|---|---|---|---|---|
| `.claude/AGENT_STATE.json` | JSON | `scripts/init.sh` (creation) → `hooks/session-start.sh`, `hooks/pre-compact.sh`, `hooks/session-end.sh` (updates) | init; session start; before context compression; session end | ❌ No — hook-managed |
| `.claude/system_bus.json` | JSON | `scripts/init.sh` (creation) → `hooks/pre-compact.sh` (append) | init; pre-compaction event | ❌ No — append-only event log |
| `.claude/task_timers.json` | JSON | `scripts/init.sh` (creation) → Rust watchdog daemon | init; every 5-min watchdog poll; `dev-kid task-start/complete` | ⚠️ No while watchdog runs (race condition) |
| `.claude/active_stack.md` | Markdown | `scripts/init.sh` (template) → `hooks/user-prompt-submit.sh` (refresh) | init; before each agent prompt | ❌ No — auto-refreshed each prompt; manual edits get overwritten |
| `.claude/activity_stream.md` | Markdown | `scripts/init.sh` (header) → `hooks/task-completed.sh`, `hooks/pre-compact.sh`, `hooks/stop.sh`, `hooks/post-tool-use-failure.sh`, `hooks/session-start.sh`, git `post-commit` hook | init; task complete; pre-compaction; session end; tool failure; session start; git commit | ✅ Yes (append-only — never delete prior entries) |
| `.claude/session_snapshots/*.json` | JSON | `dev-kid finalize`, `dev-kid recall` (read) | manual `finalize` + SessionEnd hook | ⚠️ Don't delete the most recent; older ones can be pruned |
| `.claude/sentinel/.budget-state.json` | JSON | `cli/sentinel/budget_tracker.py` | After each sentinel tier run | ✅ Yes (delete to reset; `dev-kid execute --fresh-budget` is equivalent) |
| `.claude/sentinel/SENTINEL-<TASK_ID>/manifest.json` | JSON | `cli/sentinel/manifest_writer.py` | After each sentinel run on a task (always — even on FAIL/ERROR) | ❌ No — audit trail |
| `.claude/sentinel/SENTINEL-<TASK_ID>/diff.patch` | Patch | Same | Same | ❌ No — audit trail |
| `.claude/sentinel/SENTINEL-<TASK_ID>/summary.md` | Markdown | Same | Same | ❌ No — auto-injected into next task's context |
| `.claude/sentinel/SENTINEL-<TASK_ID>/handoff/request.json` | JSON | `cli/sentinel/handoff.py` | When sentinel escalates to Tier 3 handoff | ❌ No — read by `dev-kid handoff-status` |
| `.claude/sentinel/allow-handoff` | Marker | User (manual `touch`) | Opt-in to handoff tier | ✅ Yes (presence/absence is the toggle) |
| `.claude/settings.json` | JSON | `scripts/init.sh` (template) | init only | ⚠️ Edit carefully — defines all hook wiring |
| `.claude/hooks/*.sh` | Bash | `scripts/init.sh` (cp from templates) | init only | ⚠️ Edits survive but are overwritten by reinstall |

---

## File schemas (real examples from a fresh `dev-kid init`)

### `.claude/AGENT_STATE.json`

```json
{
  "session_id": "",
  "user_id": "gyasis",
  "project_path": "/tmp/my-project",
  "status": "initialized",
  "agents": {
    "main":          {"status": "idle"},
    "memory-keeper": {"status": "idle"},
    "git-manager":   {"status": "idle"}
  },
  "initialized_at": "2026-05-23T13:30:41-04:00"
}
```

**Fields:**
- `session_id` (string) — Claude Code session UUID; empty until SessionStart hook fires
- `user_id` (string) — OS username (`$USER` at init time)
- `project_path` (string) — absolute path to project root
- `status` (enum: `initialized | active | compacted | finalized`) — coarse session lifecycle
- `agents` (object) — three logical agent slots (`main`, `memory-keeper`, `git-manager`); each has `status: idle | working | blocked`
- `initialized_at` (ISO 8601) — UTC offset timestamp of `dev-kid init`

**Updated by:** `hooks/session-start.sh` (status → `active`), `hooks/pre-compact.sh` (writes backup to `.claude/backups/`), `hooks/session-end.sh` (status → `finalized`).

**Inspect:**
```bash
jq . .claude/AGENT_STATE.json
```

---

### `.claude/system_bus.json`

```json
{
  "version": "1.0",
  "initialized_at": "2026-05-23T13:30:41-04:00",
  "events": [
    {
      "timestamp": "2026-05-23T13:30:41.493487",
      "agent": "git-manager",
      "event_type": "checkpoint_created"
    }
  ]
}
```

**Fields:**
- `version` (string) — schema version
- `initialized_at` (ISO 8601) — when the bus was created
- `events` (array) — append-only list of inter-agent messages
  - `timestamp` (ISO 8601)
  - `agent` (enum: `main | memory-keeper | git-manager`)
  - `event_type` (string — open enum; observed: `checkpoint_created`, `compaction_started`, `task_completed`)

**Updated by:** `hooks/pre-compact.sh` (appends `compaction_started`), `hooks/task-completed.sh` (appends `task_completed`), git `post-commit` hook (appends `checkpoint_created`).

**Inspect:**
```bash
jq '.events[-5:]' .claude/system_bus.json   # last 5 events
jq '.events | length' .claude/system_bus.json
```

---

### `.claude/task_timers.json`

```json
{
  "version": "1.0",
  "timers": []
}
```

**Active example (with running task):**
```json
{
  "version": "1.0",
  "timers": [
    {
      "task_id": "T001",
      "description": "Implement auth module",
      "started_at": "2026-05-23T14:00:00Z",
      "pid": 12345,
      "pgid": 12345,
      "start_time_validation": "Mon Jan  6 10:30:00 2026",
      "status": "running"
    }
  ]
}
```

**Fields per timer:**
- `task_id` (string) — `T###` matches `tasks.md` IDs
- `description` (string) — task summary
- `started_at` (ISO 8601 UTC)
- `pid` (int) — process ID (native mode only)
- `pgid` (int) — process group ID (for killing trees)
- `start_time_validation` (string) — defends against PID recycling
- `status` (enum: `running | completed | killed | orphaned | zombie`)

**Updated by:** Rust watchdog (`rust-watchdog/target/release/task-watchdog`) every 5 min. Also written by `dev-kid task-start` / `dev-kid task-complete`.

**Inspect:**
```bash
dev-kid watchdog-report    # human-readable
jq '.timers[] | select(.status=="running")' .claude/task_timers.json
```

**Don't edit while watchdog runs** — `dev-kid watchdog-stop` first.

---

### `.claude/active_stack.md`

```markdown
# Active Stack

**Budget**: <500 tokens

## Current Task
[Current focus]

## Active Files
- [File 1]

## Next Actions
1. [Action 1]
```

**Updated by:** `hooks/user-prompt-submit.sh` — refreshed before each agent prompt. The 500-token budget is hard: content exceeding ~500 tokens is dropped.

**Inspect:**
```bash
cat .claude/active_stack.md
wc -w .claude/active_stack.md   # rough token count (×0.75)
```

**Don't edit by hand** — your edits get overwritten on the next prompt.

---

### `.claude/activity_stream.md`

```markdown
# Activity Stream

### 2026-05-23T14:00:00-04:00 - Git Checkpoint
- Commit: abc1234
- Branch: feature/lightweight-mode
- Message: feat: implement task T001

### 2026-05-23T14:05:00-04:00 - TaskCompleted: T001
- Wave: 1
- Sentinel result: PASS (Tier 1, 2 iterations, $0.00)
```

**Updated by (append-only):**
- `hooks/task-completed.sh` — appends `TaskCompleted: <id>` entry
- `hooks/pre-compact.sh` — appends `Compaction at <timestamp>` entry
- `hooks/stop.sh` — appends `SessionStop` entry
- `hooks/post-tool-use-failure.sh` — appends `ToolFailure: <tool>` entry
- `hooks/session-start.sh` — appends `SessionStart` entry
- git `post-commit` hook — appends `Git Checkpoint`

**Inspect:**
```bash
tail -50 .claude/activity_stream.md
grep "TaskCompleted" .claude/activity_stream.md | wc -l
```

**Safe to read; safe to append manually; never delete prior entries** (downstream tools assume monotonic).

---

### `.claude/session_snapshots/*.json`

```json
{
  "session_id": "8af3-...",
  "timestamp": "2026-05-23T14:30:00Z",
  "mental_state": "executing wave 2",
  "current_phase": "lightweight-mode-phase-1",
  "progress": {"completed": 3, "total": 7},
  "next_steps": ["Implement T004", "Run sentinel"],
  "blockers": [],
  "git_commits": ["abc123", "def456"],
  "files_modified": ["cli/dev-kid", "scripts/init.sh"],
  "system_state": {
    "agent_state": "<embedded copy of AGENT_STATE.json>",
    "task_timers": "<embedded copy of task_timers.json>"
  }
}
```

**Written by:** `dev-kid finalize` (manual) AND `hooks/session-end.sh` (automatic on session shutdown).

**Read by:** `dev-kid recall` — picks the most-recent snapshot, hydrates context, prints summary.

**Naming:** `session-<YYYYMMDD-HHMMSS>.json`

**Inspect:**
```bash
ls -lt .claude/session_snapshots/ | head
jq '.mental_state, .progress, .next_steps' .claude/session_snapshots/<latest>.json
dev-kid recall   # auto-loads newest
```

**Pruning:** keep the most-recent snapshot. Older snapshots can be archived (`mv old.json archive/`).

---

### `.claude/sentinel/.budget-state.json`

```json
{
  "cumulative_cost_usd": 0.47,
  "cumulative_duration_sec": 142.3,
  "last_updated": "2026-05-23T14:15:00Z"
}
```

**Fields:**
- `cumulative_cost_usd` (float) — running total of sentinel spend within ONE `dev-kid execute` invocation
- `cumulative_duration_sec` (float) — running total of sentinel runtime
- `last_updated` (ISO 8601)

**Updated by:** `cli/sentinel/budget_tracker.py` after every tier run (T1/T2/T3).

**Caps:** read from `dev-kid.yml`:
```yaml
sentinel:
  tier_orchestration:
    max_total_cost_usd: 5.0       # halts execute if exceeded
    max_total_duration_min: 30
```

**Reset:** `dev-kid execute --fresh-budget` → deletes this file → starts at $0.
Or manually:
```bash
rm .claude/sentinel/.budget-state.json
```

**Check:**
```bash
dev-kid budget-status
jq . .claude/sentinel/.budget-state.json
```

**Safe to edit** — set `cumulative_cost_usd: 0` to manually reset.

---

### `.claude/sentinel/SENTINEL-<TASK_ID>/manifest.json`

```json
{
  "task_id": "T001",
  "sentinel_id": "SENTINEL-T001",
  "started_at": "2026-05-23T14:00:00Z",
  "ended_at":   "2026-05-23T14:02:30Z",
  "duration_sec": 150,
  "result": "PASS",
  "tier_used": "tier1",
  "tier_name": "all-local",
  "iterations": 3,
  "cost_usd": 0.00,
  "files_modified": ["src/auth.py", "tests/test_auth.py"],
  "test_command_detected": "pytest tests/test_auth.py",
  "placeholder_violations": [],
  "interface_changes": [],
  "change_radius": {
    "files_changed": 2,
    "lines_changed": 47,
    "violations": []
  },
  "should_halt_wave": false
}
```

**Result enum:** `PASS | FAIL | ERROR | SKIPPED`

**Written by:** `cli/sentinel/manifest_writer.py` — **always**, even on ERROR/exception paths (try/finally guarantee). This is the audit trail.

**Companion files in same dir:**
- `diff.patch` — `git diff HEAD` output (empty if no changes)
- `summary.md` — human-readable; auto-injected into next task's prompt via `hooks/user-prompt-submit.sh`
- `handoff/request.json` — only present if escalated to Tier 3

**Inspect (sentinel dashboard):**
```bash
dev-kid sentinel-status   # table view across all tasks
ls .claude/sentinel/      # all SENTINEL-* dirs
jq '.result, .tier_used, .cost_usd' .claude/sentinel/SENTINEL-T001/manifest.json
```

---

### `.claude/sentinel/SENTINEL-<TASK_ID>/handoff/request.json`

```json
{
  "task_id": "T001",
  "sentinel_id": "SENTINEL-T001",
  "requested_at": "2026-05-23T14:05:00Z",
  "reason": "tier2_budget_exceeded",
  "objective": "Implement auth module per tasks.md T001",
  "files_modified": ["src/auth.py"],
  "tier_history": [
    {"tier": "tier1", "result": "FAIL", "iterations": 5},
    {"tier": "tier2", "result": "FAIL", "cost_usd": 1.20, "iterations": 8}
  ],
  "status": "pending"
}
```

**Status enum:** `pending | in_progress | completed | failed`

**Written by:** `cli/sentinel/handoff.py` when sentinel exhausts Tier 1+2 AND `.claude/sentinel/allow-handoff` marker exists.

**Read by:** `dev-kid handoff-status` (lists pending), `/devkid.handoff-process` (slash command for Claude Code to claim + work).

**Closed via:**
```bash
dev-kid handoff-complete T001                            # mark success
dev-kid handoff-complete T001 --failed --notes "reason"  # mark failed
```

---

### `.claude/sentinel/allow-handoff`

Empty marker file. **Presence enables Tier 3 (Claude Code handoff)**; absence disables it.

```bash
touch .claude/sentinel/allow-handoff    # enable
rm .claude/sentinel/allow-handoff       # disable
```

---

### `.claude/settings.json`

```json
{
  "hooks": {
    "PreCompact":  [{"hooks": [{"type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/pre-compact.sh"}]}],
    "TaskCompleted": [{"hooks": [{"type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/task-completed.sh"}]}],
    "PostToolUse": [{"hooks": [{"type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/post-tool-use.sh"}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/user-prompt-submit.sh"}]}],
    "SessionStart": [{"hooks": [{"type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/session-start.sh"}]}],
    "SessionEnd": [{"hooks": [{"type": "command", "command": "${CLAUDE_PROJECT_DIR}/.claude/hooks/session-end.sh"}]}]
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

**Edit-with-care:** removing a hook entry disables that lifecycle event (no error, just silently no-op). To disable ALL dev-kid hooks without editing:
```bash
export DEV_KID_HOOKS_ENABLED=false
```

---

## Quick-reference cheatsheet

| Question | Command |
|---|---|
| What's the current session state? | `jq . .claude/AGENT_STATE.json` |
| What events happened recently? | `jq '.events[-10:]' .claude/system_bus.json` |
| What tasks are running? | `dev-kid watchdog-report` |
| How much has sentinel spent? | `dev-kid budget-status` |
| Did sentinel pass for task T001? | `jq '.result' .claude/sentinel/SENTINEL-T001/manifest.json` |
| What handoffs are pending? | `dev-kid handoff-status` |
| What was the last snapshot? | `ls -lt .claude/session_snapshots/ \| head -1` |
| When did wave 2 finish? | `grep "TaskCompleted" .claude/activity_stream.md \| tail -10` |

## Killswitches (when you need to disable something)

| Disable | How |
|---|---|
| All hooks | `export DEV_KID_HOOKS_ENABLED=false` |
| GitHub sync on TaskCompleted | `export DEV_KID_AUTO_SYNC_GITHUB=false` |
| Auto-checkpoint on TaskCompleted | `export DEV_KID_AUTO_CHECKPOINT=false` |
| Handoff notifier (UserPromptSubmit) | `export DEV_KID_HANDOFF_NOTIFIER=false` |
| Sentinel entirely | Edit `dev-kid.yml`: `sentinel.enabled: false` |
| Tier 3 handoff | `rm .claude/sentinel/allow-handoff` |
| Watchdog | `dev-kid watchdog-stop` |
| Reset cumulative budget | `dev-kid execute --fresh-budget` OR `rm .claude/sentinel/.budget-state.json` |

---

## See also

- `AGENT_GUIDE.md` — when/how AI agents should reach for dev-kid (decision tree, workflows)
- `HOOKS_REFERENCE.md` — hook lifecycle, stdin/stdout contract per hook
- `INTEGRATION_GUIDE.md` — Bash/Python/Rust architecture split
- `CLAUDE.md` — editing dev-kid itself

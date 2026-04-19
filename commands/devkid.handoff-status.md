---
name: devkid.handoff-status
description: List pending Claude Code handoff requests waiting for operator action
---

# Dev-Kid Handoff Status

Shows all pending Claude Code handoff requests in the current project. Each request was written by `dev-kid execute` when a sentinel hit the `claude-code-handoff` tier in `ralph-tiers.json` — it's now waiting for either Claude Code (this session) or the operator to handle it.

## Usage

```bash
/devkid.handoff-status
```

## Execution

```bash
#!/bin/bash
dev-kid handoff-status
```

## Output Example

```
Pending Claude Code handoffs (2):
  - T015: Fix the OAuth token refresh logic in src/auth.py...
    request file: .claude/sentinel/SENTINEL-T015/handoff/request.json
  - T032: Add retry handling to the rate-limited downstream call...
    request file: .claude/sentinel/SENTINEL-T032/handoff/request.json
```

## What's Inside Each request.json

- `task_id` — the failing task ID
- `task_description` — what the task wanted done
- `test_command` — what test the sentinel was trying to make pass
- `file_locks` — files the task expected to modify
- `tier_history` — what previous tiers tried and how they failed
- `cumulative_cost_so_far` / `cumulative_budget` — current spend vs cap
- `instructions_for_claude` — explicit ask of Claude Code

## Related

- `/devkid.handoff-process` — actually do the work and mark each request complete
- `dev-kid handoff-complete <task_id>` — manually mark a request complete from the CLI
- `/devkid.budget-status` — see cumulative sentinel spend

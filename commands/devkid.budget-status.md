---
name: devkid.budget-status
description: Show cumulative sentinel spend for this project (across all dev-kid execute runs)
---

# Dev-Kid Budget Status

Shows cumulative sentinel cost spent across all sentinels in the current project's `dev-kid execute` runs. State persists in `.claude/sentinel/.budget-state.json` so it survives crashes and restart-resume cycles.

## Usage

```bash
/devkid.budget-status
```

## Execution

```bash
#!/bin/bash
dev-kid budget-status
```

## Output Example

```
BudgetTracker: $7.50 of $25.00 spent across 12 sentinel(s), $17.50 remaining (4.2 cumulative minutes)
```

## When the Budget Halts

When cumulative spend reaches the configured cap (default $25.00, override via `DEVKID_SENTINEL_BUDGET_USD` env var), `dev-kid execute` halts cleanly with a clear message. To raise the cap and resume:

```bash
export DEVKID_SENTINEL_BUDGET_USD=50.0
dev-kid execute
```

To reset the cumulative counter (e.g., starting a fresh feature):

```bash
rm .claude/sentinel/.budget-state.json
# OR call BudgetTracker.reset() from a Python session
```

## Related

- `dev-kid.yml` `sentinel.max_total_cost_usd` — per-sentinel cap (default $5.00 per task)
- `DEVKID_SENTINEL_BUDGET_USD` env var — global cumulative cap (default $25.00 across all sentinels)
- `DEVKID_SENTINEL_WARN_PCT` env var — when to warn before hitting cap (default 0.80 = 80%)
- `DEVKID_SENTINEL_HANDOFF_THRESHOLD` env var — per-task spend that triggers Claude Code handoff (default $1.00)
- `/devkid.handoff-status` — see pending handoffs that may have been triggered by budget
- `/devkid.handoff-process` — process pending handoffs in this session

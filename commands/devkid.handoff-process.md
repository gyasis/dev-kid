---
name: devkid.handoff-process
description: Process all pending Claude Code handoff requests — read each request, do the work, mark complete
---

# Dev-Kid Handoff Process

This is the **Claude Code companion** to `dev-kid execute`'s `claude-code-handoff` tier. When dev-kid's sentinel can't pass on the cheap local tiers and the operator has configured the `claude-code-handoff` tier in `ralph-tiers.json`, dev-kid writes a handoff request file and pauses. This command tells the active Claude Code session to:

1. Read every pending `.claude/sentinel/SENTINEL-<task_id>/handoff/request.json`
2. For each request, perform the actual work the task wanted (apply the fix, make the test pass)
3. Write `complete.json` with `succeeded: true/false` so dev-kid's wave executor unpauses

## Usage

```bash
/devkid.handoff-process
```

## What Claude Code Should Do

When this command fires, Claude Code MUST:

1. **List pending handoffs**: run `dev-kid handoff-status` to enumerate what needs attention
2. **For each pending request**:
   - Read `.claude/sentinel/SENTINEL-<task_id>/handoff/request.json`
   - Inspect `task_description` (what the task asked for) and `test_command` (how to verify success)
   - Inspect `tier_history` to understand WHY the cheap tiers couldn't solve it (often gives a clue about the real problem)
   - Apply the fix to the files in `file_locks` (or the files the task description implies)
   - Run `test_command` and confirm it passes
   - Mark the request complete: `dev-kid handoff-complete <task_id> --notes "<what you did>"`
   - If the fix can't be made: `dev-kid handoff-complete <task_id> --failed --notes "<why>"`
3. **After processing all pending requests**, summarize what was done in the conversation

## Why This Tier Exists

The `claude-code-handoff` tier is a cost-optimization. The user pays a flat fee for Claude Code subscription, so leveraging this session is effectively "free" compared to escalating sentinel to a per-token API tier (OpenAI/Anthropic direct API). For tasks that the cheap local tiers can't solve but Claude can, this avoids burning $1-5 per task on API tiers while still getting a quality result.

## Critical Rules for Claude Code

- **Do NOT skip tasks**. If the request file exists and there's no `complete.json` next to it, process it.
- **Make the test pass**. The whole point of the handoff is to satisfy `test_command`. Verify before marking complete.
- **If you can't fix it**, mark it `--failed` with a clear note. Don't leave dev-kid hanging.
- **Match the file_locks scope**. If the request says only `src/auth.py` should change, don't touch `src/database.py` as a side effect.

## Execution

```bash
#!/bin/bash
echo "📋 Pending handoffs:"
dev-kid handoff-status
echo ""
echo "Claude Code: read each request file, do the work, then run:"
echo "  dev-kid handoff-complete <task_id> --notes \"<what you did>\""
echo ""
echo "If you cannot complete a request, mark it failed:"
echo "  dev-kid handoff-complete <task_id> --failed --notes \"<why>\""
```

## Related

- `/devkid.handoff-status` — list pending requests without processing
- `/devkid.budget-status` — see cumulative sentinel spend
- `/devkid.execute` — the wave executor that creates handoff requests when the handoff tier is reached

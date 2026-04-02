---
name: devkid.status
description: Show full dev-kid system status — memory bank, constitution, config, watchdog, execution plan, sentinel
---

# Dev-Kid Status

Shows complete system health: Memory Bank, Constitution, Config, Watchdog, Execution Plan, and Sentinel readiness.

## What This Does

1. Memory Bank status (6-tier structure, last sync time)
2. Constitution status (loaded, rule count, strict mode)
3. Config status (dev-kid.yml loaded, sentinel enabled, wave size)
4. Task Watchdog status (running, PID, task count)
5. Execution Plan status (waves, tasks, current wave)
6. Sentinel readiness (providers, tiers, health)

## Usage

```bash
/devkid.status
```

## Execution

```bash
#!/bin/bash
set -e

dev-kid status

echo ""
echo "📋 Additional diagnostics:"
echo ""

# Sentinel health summary
echo "🛡️  Sentinel:"
dev-kid sentinel-health 2>/dev/null | grep -E "tiers ready|will run|will SKIP" || echo "   (run /devkid.sentinel-health for details)"

echo ""

# Execution plan summary
if [ -f "execution_plan.json" ]; then
    echo "📊 Execution Plan:"
    if command -v jq &>/dev/null; then
        WAVES=$(jq '.execution_plan.waves | length' execution_plan.json)
        TASKS=$(jq '[.execution_plan.waves[].tasks[]] | length' execution_plan.json)
        echo "   $WAVES waves, $TASKS tasks"
    else
        echo "   execution_plan.json exists (install jq for summary)"
    fi
else
    echo "📊 No execution plan — run /devkid.orchestrate first"
fi

echo ""

# Tasks summary
if [ -f "tasks.md" ]; then
    TOTAL=$(grep -c '^\- \[' tasks.md 2>/dev/null || echo 0)
    DONE=$(grep -c '^\- \[x\]' tasks.md 2>/dev/null || echo 0)
    echo "📝 Tasks: $DONE/$TOTAL complete"
else
    echo "📝 No tasks.md found"
fi
```

## When To Use

- Start of session — understand current project state
- Before `/devkid.execute` — verify everything is ready
- After context compaction — re-orient
- Debugging — see what's running and what's configured

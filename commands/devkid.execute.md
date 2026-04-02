---
name: devkid.execute
description: Execute parallelized waves with constitution enforcement and automatic checkpoints
---

# Dev-Kid Execute

Executes wave-based implementation plan with automatic checkpointing, constitution validation, and task monitoring.

## What This Does

1. Runs sentinel health check (validates Ollama models, Azure keys, provider endpoints)
2. Starts task watchdog for monitoring
3. Loads constitution rules
4. Executes waves sequentially (max 10 tasks per wave, configurable via dev-kid.yml wave_size)
5. At each wave checkpoint:
   a. Validates task completion ([x] markers in tasks.md)
   b. Integration Sentinel validates output (placeholder scan, micro-agent test loop, interface diff)
   c. Constitution compliance check
   d. Memory sync via `memory-bank-keeper` agent
   e. Git checkpoint via `git-version-manager` agent
6. Reports PASS/FAIL/SKIP per task with tier info

## Usage

```bash
/devkid.execute
```

## Execution

```bash
#!/bin/bash
set -e

# Check prerequisites
if [ ! -f "execution_plan.json" ]; then
    echo "❌ No execution_plan.json found"
    echo "   Run /devkid.orchestrate first"
    exit 1
fi

if [ ! -f "tasks.md" ]; then
    echo "❌ No tasks.md found"
    exit 1
fi

echo "🚀 Starting wave-based execution..."
echo ""

# Start watchdog
echo "🐕 Starting task watchdog..."
dev-kid watchdog-start
echo ""

# Load constitution if exists
if [ -f "memory-bank/shared/.constitution.md" ]; then
    echo "📜 Constitution loaded - rules will be enforced at checkpoints"
    echo ""
fi

# Execute waves
echo "🌊 Executing waves..."
echo ""
dev-kid execute

# Check execution result
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All waves executed!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Review changes: git status"
    echo "   2. Update memory: /devkid.sync-memory"
    echo "   3. Finalize session: dev-kid finalize"
else
    echo ""
    echo "❌ Wave execution failed"
    echo "   Check tasks.md for completion markers [x]"
    echo "   Review constitution violations if any"
    exit 1
fi
```

## Wave Execution Flow

```
Wave 1 (PARALLEL_SWARM, max 10 tasks)
  → Register tasks with watchdog
  → Execute tasks in parallel
  → Mark [x] in tasks.md as complete
  ↓
  [CHECKPOINT — automatic via wave_executor.py]
  → Verify all tasks have [x] markers
  → Integration Sentinel per task:
     • Placeholder scan (TODO/FIXME/stub detection)
     • Test loop via micro-agent (tiered: Ollama → Azure)
     • Interface diff (public API changes)
     • Change radius check (file/line budget)
  → Constitution compliance check
  → Memory sync (memory-bank-keeper)
  → Git commit (git-version-manager)

Wave 2... (same pattern, automatic)
```

## Agent Delegation at Checkpoints

The execution_plan.json names specific Claude Code agents for checkpoint tasks:

| Agent | Role | Spawned when |
|-------|------|-------------|
| `memory-bank-keeper` | Syncs progress.md, memory bank, activity stream | After wave validation passes |
| `git-version-manager` | Creates semantic git checkpoint | After memory sync + constitution check |

When using `dev-kid execute`, these are handled in-process.
When working manually, Claude should spawn these agents at wave boundaries.

## Sentinel Health Check

Before execution, verify providers are ready:

```bash
dev-kid sentinel-health
```

Shows per-tier readiness (Ollama models, Azure endpoints, API keys).
If any tier is unavailable, sentinel will SKIP (not false PASS) and report why.

## Constitution Enforcement

At each checkpoint, validates:
- ✅ Type hints present (if required)
- ✅ Docstrings present (if required)
- ✅ No hardcoded secrets
- ✅ Test coverage >80% (if required)
- ✅ No forbidden patterns

**Checkpoint BLOCKED if violations found.**

## Task Watchdog

Each task registered with:
- Task ID (T001, T002...)
- Command/instruction
- Constitution rules
- Start timestamp

Monitors:
- ⏱️ Task duration (7-minute guideline)
- 🚨 Stalled tasks (>15 min no activity)
- ✅ Completion detection (tasks.md [x] markers)

## Integration with Speckit

- Tasks from: `.specify/specs/{branch}/tasks.md`
- Constitution from: `memory-bank/shared/.constitution.md`
- Enforcement happens at wave boundaries

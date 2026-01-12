---
name: devkid.execute
description: Execute parallelized waves with constitution enforcement and automatic checkpoints
---

# Dev-Kid Execute

Executes wave-based implementation plan with automatic checkpointing, constitution validation, and task monitoring.

## What This Does

1. Starts task watchdog for monitoring
2. Loads constitution rules
3. Executes waves sequentially
4. Validates completion at wave boundaries
5. Enforces constitution compliance
6. Creates git checkpoints between waves

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
Wave 1 (PARALLEL_SWARM)
  → Register tasks with watchdog
  → Execute tasks in parallel
  → Mark [x] in tasks.md as complete
  → Checkpoint validation
  → Constitution compliance check
  → Git commit

Wave 2 (SEQUENTIAL_MERGE)
  → Register tasks with watchdog
  → Execute tasks sequentially
  → Mark [x] in tasks.md as complete
  → Checkpoint validation
  → Constitution compliance check
  → Git commit

Wave 3...
```

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

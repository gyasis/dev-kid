---
name: Execute Wave-Based Implementation
description: Auto-executes parallelized waves with constitution enforcement and checkpoint validation
version: 1.0.0
triggers:
  - "execute waves"
  - "start implementation"
  - "run execution plan"
  - "begin waves"
parameters:
  - name: auto_checkpoint
    description: Automatically checkpoint after each wave
    type: boolean
    required: false
    default: true
  - name: start_watchdog
    description: Start task watchdog before execution
    type: boolean
    required: false
    default: true
---

# Execute Wave-Based Implementation

**Purpose**: Execute parallelized wave execution plan with automatic checkpointing, constitution validation, and task monitoring.

## Activation Logic

This skill activates when:
1. ✅ `execution_plan.json` exists
2. ✅ `tasks.md` exists
3. ✅ Constitution loaded from `memory-bank/shared/.constitution.md`
4. 📝 User message contains: "execute", "start implementation", "run waves"

## What This Skill Does

1. **Validates** execution plan and tasks are present
2. **Starts** task watchdog (if enabled)
3. **Loads** constitution for rule enforcement
4. **Executes** waves sequentially with checkpoints between
5. **Registers** each task with watchdog including constitution rules
6. **Validates** completion before proceeding to next wave
7. **Enforces** constitution rules at checkpoint boundaries

## Execution

```bash
#!/bin/bash
set -e

# Check prerequisites
if [ ! -f "execution_plan.json" ]; then
    echo "❌ No execution_plan.json found"
    echo "   Run orchestrate-tasks skill first"
    exit 1
fi

if [ ! -f "tasks.md" ]; then
    echo "❌ No tasks.md found"
    exit 1
fi

# Parse parameters
AUTO_CHECKPOINT="${1:-true}"
START_WATCHDOG="${2:-true}"

echo "🚀 Starting wave-based execution..."
echo ""

# Start watchdog if requested
if [ "$START_WATCHDOG" = "true" ]; then
    echo "🐕 Starting task watchdog..."
    dev-kid watchdog-start
    echo ""
fi

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
    echo "   2. Update memory: dev-kid sync-memory"
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

## Example Usage

### Auto-Execute After Orchestration
```
User: Execute the waves

Claude: 🚀 Starting wave-based execution...
        🐕 Starting task watchdog...
        📜 Constitution loaded - rules will be enforced

        🌊 Wave 1 (PARALLEL_SWARM): 4 tasks
           ✅ T001 registered with 2 constitution rule(s)
           ✅ T002 registered with 2 constitution rule(s)
           ...

        🔍 Checkpoint after Wave 1...
           ✅ All tasks complete
           ✅ Constitution compliant
           📝 Git checkpoint created

        🌊 Wave 2 (SEQUENTIAL_MERGE): 3 tasks
           ...
```

### Constitution Violation Block
```
Claude: 🔍 Checkpoint after Wave 1...
        ❌ Constitution Violations - Checkpoint BLOCKED:

           Rule: Type hints required
           File: src/models/user.py:15
           Issue: Function 'create_user' missing type hints

        Fix violations before proceeding to Wave 2.
```

## Task Watchdog Integration

Each task registered with:
- Task ID (T001, T002...)
- Command/instruction
- Constitution rules (embedded from tasks.md)
- Start timestamp

Watchdog monitors:
- ⏱️ Task duration (7-minute guideline)
- 🚨 Stalled tasks (>15 min no activity)
- ✅ Completion detection (tasks.md [x] markers)

## Integration with Speckit

- Tasks from: `.specify/specs/{branch}/tasks.md`
- Constitution from: `memory-bank/shared/.constitution.md`
- Each task has embedded constitution rules from /speckit.tasks
- Enforcement happens at wave boundaries

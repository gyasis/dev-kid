---
name: devkid.checkpoint
description: Validate wave completion and create git checkpoint with constitution enforcement
---

# Dev-Kid Checkpoint

Validates wave task completion, enforces constitution rules, and creates semantic git checkpoint.

## What This Does

1. Detects current wave from execution plan
2. Validates all wave tasks marked [x] in tasks.md
3. Integration Sentinel validates output (placeholder scan, test loop, interface diff, change radius)
4. Checks constitution compliance for modified files
5. Blocks checkpoint if sentinel or constitution violations found
6. Spawns `memory-bank-keeper` agent to sync progress.md and memory bank
7. Spawns `git-version-manager` agent to create semantic git checkpoint
8. Logs checkpoint to activity_stream.md

## Usage

```bash
# Auto-detect current wave
/devkid.checkpoint

# Specify wave number
/devkid.checkpoint 2

# Custom message
/devkid.checkpoint 2 "Wave 2: User service complete"
```

## Execution

```bash
#!/bin/bash
set -e

# Parse parameters
WAVE_ID="${1:-auto}"
CHECKPOINT_MSG="${2:-Wave checkpoint}"

echo "🔍 Checkpoint validation starting..."
echo ""

# Auto-detect current wave if not specified
if [ "$WAVE_ID" = "auto" ]; then
    if [ ! -f "execution_plan.json" ]; then
        echo "❌ No execution_plan.json found"
        exit 1
    fi

    # Find first completed wave
    WAVE_ID=$(python3 << 'PYTHON'
import json
from pathlib import Path

plan = json.loads(Path('execution_plan.json').read_text())
tasks_md = Path('tasks.md').read_text()

for wave in plan['execution_plan']['waves']:
    wave_id = wave['wave_id']
    all_complete = True

    for task in wave['tasks']:
        task_id = task['task_id']
        if f'- [x] {task_id}' not in tasks_md:
            all_complete = False
            break

    if all_complete:
        print(wave_id)
        break
PYTHON
)

    if [ -z "$WAVE_ID" ]; then
        echo "⚠️  Could not auto-detect completed wave"
        echo "   Specify wave number manually"
        exit 1
    fi

    echo "   Detected wave: $WAVE_ID"
fi

echo "   Validating Wave $WAVE_ID completion..."
echo ""

# Step 1: Verify all wave tasks marked [x]
echo "   Step 1: Checking task completion..."
INCOMPLETE_TASKS=$(python3 << PYTHON
import json
from pathlib import Path

plan = json.loads(Path('execution_plan.json').read_text())
tasks_md = Path('tasks.md').read_text()

for wave in plan['execution_plan']['waves']:
    if wave['wave_id'] == $WAVE_ID:
        for task in wave['tasks']:
            task_id = task['task_id']
            if f'- [x] {task_id}' not in tasks_md:
                print(task_id)
PYTHON
)

if [ -n "$INCOMPLETE_TASKS" ]; then
    echo "   ❌ Incomplete tasks found:"
    echo "$INCOMPLETE_TASKS" | while read task; do
        echo "      - $task"
    done
    echo ""
    echo "   Mark all tasks [x] in tasks.md before checkpoint"
    exit 1
fi

echo "   ✅ All tasks marked complete"
echo ""

# Step 2: Validate constitution compliance
echo "   Step 2: Constitution validation..."

if [ -f "memory-bank/shared/.constitution.md" ]; then
    if dev-kid constitution validate 2>/dev/null; then
        echo "   ✅ Constitution compliant"
    else
        echo "   ❌ Constitution violations detected"
        echo ""
        dev-kid constitution validate
        echo ""
        echo "   Fix violations before checkpoint"
        exit 1
    fi
else
    echo "   ⚠️  No constitution found - skipping validation"
fi

echo ""

# Step 3: Create git checkpoint
echo "   Step 3: Creating git checkpoint..."

# Auto-generate message if not provided
if [ "$CHECKPOINT_MSG" = "Wave checkpoint" ]; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "main")
    CHECKPOINT_MSG="Wave $WAVE_ID complete - $BRANCH"
fi

dev-kid checkpoint "$CHECKPOINT_MSG"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Checkpoint created!"
    echo "   Wave $WAVE_ID: Validated and committed"
    echo ""
    echo "📋 Next steps:"
    echo "   - Continue to next wave"
    echo "   - Or run: /devkid.sync-memory"
else
    echo ""
    echo "❌ Checkpoint failed"
    exit 1
fi
```

## Validation Sequence

```
1. Task Completion Check
   ├─ Parse execution_plan.json
   ├─ Extract tasks for wave N
   ├─ Verify all tasks marked [x] in tasks.md
   └─ HALT if incomplete

2. Integration Sentinel (if enabled in dev-kid.yml)
   ├─ Placeholder scan (TODO/FIXME/stub in prod code)
   ├─ Test loop via micro-agent (tiered escalation)
   ├─ Interface diff (public API changes)
   ├─ Change radius check (file/line budget)
   └─ HALT if sentinel fails, SKIP if no test command

3. Constitution Validation
   ├─ Load memory-bank/shared/.constitution.md
   ├─ Scan modified files
   ├─ Check rules (type hints, docstrings, secrets, coverage, patterns)
   └─ HALT if violations

4. Memory Sync (agent: memory-bank-keeper)
   ├─ Update progress.md
   ├─ Sync all 6 memory bank tiers
   └─ Log to activity_stream.md

5. Git Checkpoint (agent: git-version-manager)
   ├─ Stage modified files
   ├─ Create semantic commit: "Wave N complete - {branch}"
   └─ Verify commit succeeded
```

## Integration with Speckit

- Tasks from: `.specify/specs/{branch}/tasks.md`
- Constitution from: `memory-bank/shared/.constitution.md`
- Validates rules embedded in tasks by /speckit.tasks
- Ensures feature branches have clean checkpoints

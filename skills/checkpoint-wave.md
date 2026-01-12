---
name: Checkpoint Wave Completion
description: Validates wave completion and creates git checkpoint with constitution enforcement
version: 1.0.0
triggers:
  - "checkpoint"
  - "wave complete"
  - "commit wave"
  - "save progress"
parameters:
  - name: wave_id
    description: Wave number to checkpoint (auto-detected if not provided)
    type: integer
    required: false
  - name: message
    description: Custom checkpoint message
    type: string
    required: false
---

# Checkpoint Wave Completion

**Purpose**: Validate wave task completion, enforce constitution rules, and create semantic git checkpoint between waves.

## Activation Logic

This skill activates when:
1. ✅ `execution_plan.json` exists
2. ✅ `tasks.md` has tasks marked `[x]` for current wave
3. 📝 User message contains: "checkpoint", "wave complete", "commit"
4. 🔍 Wave boundary reached during execution

## What This Skill Does

1. **Detects** current wave from execution plan
2. **Validates** all wave tasks marked `[x]` in tasks.md
3. **Checks** constitution compliance for modified files
4. **Blocks** checkpoint if violations found
5. **Creates** git commit with semantic message
6. **Updates** progress.md in memory-bank
7. **Logs** checkpoint to activity_stream.md

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
    # Parse execution plan for current wave
    if [ ! -f "execution_plan.json" ]; then
        echo "❌ No execution_plan.json found"
        exit 1
    fi

    # Simple detection: find first wave with incomplete tasks
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
        # Check if task marked [x]
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
    # Run constitution validation
    if dev-kid constitution validate 2>/dev/null; then
        echo "   ✅ Constitution compliant"
    else
        echo "   ❌ Constitution violations detected"
        echo ""
        dev-kid constitution show-violations
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
    echo "   - Or run: dev-kid sync-memory"
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

2. Constitution Validation
   ├─ Load memory-bank/shared/.constitution.md
   ├─ Scan modified files
   ├─ Check rules:
   │  ├─ Type hints required?
   │  ├─ Docstrings required?
   │  ├─ No hardcoded secrets?
   │  ├─ Test coverage >80%?
   │  └─ No forbidden patterns?
   └─ HALT if violations

3. Git Checkpoint
   ├─ git add -A
   ├─ git commit -m "Wave N complete - {branch}"
   ├─ Update progress.md
   └─ Log to activity_stream.md
```

## Example Usage

### Auto-Checkpoint After Wave
```
User: Wave 1 is done

Claude: 🔍 Checkpoint validation starting...
        Detected wave: 1

        Step 1: Checking task completion...
        ✅ All tasks marked complete

        Step 2: Constitution validation...
        ✅ Constitution compliant

        Step 3: Creating git checkpoint...
        ✅ Checkpoint created!
        Wave 1: Validated and committed
```

### Constitution Violation
```
User: Checkpoint wave 2

Claude: 🔍 Checkpoint validation starting...

        Step 1: Checking task completion...
        ✅ All tasks marked complete

        Step 2: Constitution validation...
        ❌ Constitution violations detected

        Rule: Type hints required
        File: src/services/user_service.py:42
        Issue: Function 'create_user' missing return type hint

        Rule: No hardcoded secrets
        File: src/config.py:15
        Issue: Hardcoded API key detected

        Fix violations before checkpoint
```

### Incomplete Tasks
```
User: Checkpoint wave 1

Claude: 🔍 Checkpoint validation starting...

        Step 1: Checking task completion...
        ❌ Incomplete tasks found:
           - T003
           - T005

        Mark all tasks [x] in tasks.md before checkpoint
```

## Integration with Dev-Kid Execute

During wave execution, this skill:
1. Auto-triggers at wave boundaries
2. Validates before proceeding to next wave
3. Blocks execution if validation fails
4. Creates clean checkpoints between waves

## Integration with Speckit

- Tasks from: `.specify/specs/{branch}/tasks.md`
- Constitution from: `memory-bank/shared/.constitution.md`
- Validates rules embedded in tasks by /speckit.tasks
- Ensures feature branches have clean checkpoints

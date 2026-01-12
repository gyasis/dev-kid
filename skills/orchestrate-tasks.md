---
name: Orchestrate Tasks into Waves
description: Auto-detects new tasks.md and orchestrates into parallelized execution waves with dependency analysis
version: 1.0.0
triggers:
  - "tasks generated"
  - "orchestrate"
  - "create execution plan"
  - "what's next"
parameters:
  - name: phase_name
    description: Name for this execution phase
    type: string
    required: false
    default: "Feature Implementation"
---

# Orchestrate Tasks into Waves

**Purpose**: Automatically convert linear tasks.md into parallelized execution waves when new tasks are detected.

## Activation Logic

This skill activates when:
1. ✅ `tasks.md` exists (symlinked from .specify/specs/NNN-feature/tasks.md)
2. ❌ `execution_plan.json` does NOT exist OR is older than tasks.md
3. 📝 User message contains: "tasks generated", "orchestrate", "what's next"

## What This Skill Does

1. **Detects** new or updated tasks.md file
2. **Checks** if execution_plan.json needs regeneration
3. **Runs** `dev-kid orchestrate` to create wave execution plan
4. **Reports** wave structure (parallel vs sequential tasks)
5. **Suggests** next steps (execute waves or start watchdog)

## Execution

```bash
#!/bin/bash
set -e

# Check if tasks.md exists
if [ ! -f "tasks.md" ]; then
    echo "⚠️  No tasks.md found - run /speckit.tasks first"
    exit 1
fi

# Check if execution plan already exists and is newer than tasks.md
if [ -f "execution_plan.json" ]; then
    if [ "execution_plan.json" -nt "tasks.md" ]; then
        echo "ℹ️  Execution plan is up to date - skipping orchestration"
        echo "   To re-orchestrate: delete execution_plan.json or update tasks.md"
        exit 0
    fi
fi

# Determine phase name
PHASE_NAME="${1:-Feature Implementation}"

# Get current branch for feature context
BRANCH=$(git branch --show-current 2>/dev/null || echo "main")

echo "🌊 Orchestrating tasks into execution waves..."
echo "   Phase: $PHASE_NAME"
echo "   Branch: $BRANCH"
echo ""

# Run orchestration
dev-kid orchestrate "$PHASE_NAME"

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Execution plan created!"
    echo ""
    echo "📋 Next steps:"
    echo "   1. Review: cat execution_plan.json | jq '.execution_plan.waves'"
    echo "   2. Start watchdog: dev-kid watchdog-start"
    echo "   3. Execute waves: dev-kid execute"
else
    echo "❌ Orchestration failed - check tasks.md format"
    exit 1
fi
```

## Example Usage

### After /speckit.tasks
```
User: /speckit.tasks
      (tasks.md generated)

Claude: 🌊 Auto-orchestrating into waves...

        Phase: Feature Implementation
        Branch: 001-user-auth

        Wave 1 (PARALLEL_SWARM): 4 tasks
        Wave 2 (SEQUENTIAL_MERGE): 3 tasks
        Wave 3 (PARALLEL_SWARM): 5 tasks

        ✅ Execution plan created!
```

### Manual Trigger
```
User: Orchestrate the tasks into waves

Claude: [Runs this skill]
        🌊 Orchestrating tasks into execution waves...
```

## File Structure Created

```
execution_plan.json
{
  "execution_plan": {
    "phase_id": "Feature Implementation",
    "waves": [
      {
        "wave_id": 1,
        "strategy": "PARALLEL_SWARM",
        "tasks": [...],
        "checkpoint_after": {...}
      }
    ]
  }
}
```

## Integration with Speckit

- Reads tasks.md from: `.specify/specs/{branch}/tasks.md` (via symlink)
- Extracts constitution rules embedded in tasks
- Detects file locks to prevent race conditions
- Creates parallelized execution plan for dev-kid execute

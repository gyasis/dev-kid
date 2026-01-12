---
name: devkid.orchestrate
description: Orchestrate tasks.md into parallelized execution waves
---

# Dev-Kid Orchestrate

Converts linear tasks.md into parallelized wave execution plan with dependency analysis.

## What This Does

1. Reads tasks.md (symlinked from .specify/specs/{branch}/tasks.md)
2. Analyzes file locks and dependencies
3. Creates execution_plan.json with PARALLEL_SWARM and SEQUENTIAL_MERGE waves
4. Reports wave structure

## Usage

```bash
/devkid.orchestrate
```

Or with custom phase name:

```bash
/devkid.orchestrate "Feature Implementation"
```

## Execution

```bash
#!/bin/bash
set -e

PHASE_NAME="${1:-Feature Implementation}"

# Check prerequisites
if [ ! -f "tasks.md" ]; then
    echo "❌ No tasks.md found"
    echo "   Run /speckit.tasks first or ensure tasks.md exists"
    exit 1
fi

# Get current branch
BRANCH=$(git branch --show-current 2>/dev/null || echo "main")

echo "🌊 Orchestrating tasks into execution waves..."
echo "   Phase: $PHASE_NAME"
echo "   Branch: $BRANCH"
echo ""

# Run orchestration
dev-kid orchestrate "$PHASE_NAME"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Execution plan created!"
    echo ""

    # Show wave summary
    if command -v jq &> /dev/null; then
        echo "📊 Wave Summary:"
        jq '.execution_plan.waves[] | "Wave \(.wave_id) (\(.strategy)): \(.tasks | length) tasks"' -r execution_plan.json
        echo ""
    fi

    echo "📋 Next steps:"
    echo "   1. Review: cat execution_plan.json"
    echo "   2. Execute: /devkid.execute"
else
    echo ""
    echo "❌ Orchestration failed"
    exit 1
fi
```

## Output

Creates `execution_plan.json` with structure:

```json
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

- Reads tasks from: `.specify/specs/{branch}/tasks.md` (via symlink)
- Extracts constitution rules embedded by /speckit.tasks
- Creates parallelized plan for /devkid.execute

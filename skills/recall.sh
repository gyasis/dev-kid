#!/usr/bin/env bash
# Skill: Recall Last Session
# Trigger: session start, "recall"

set -e

echo "🧠 Recalling last session..."

# Find latest snapshot
LATEST_SNAPSHOT=".claude/session_snapshots/snapshot_latest.json"

if [ ! -f "$LATEST_SNAPSHOT" ]; then
    echo "   ℹ️  No previous session found - starting fresh"
    echo ""
    echo "   Suggested next steps:"
    echo "   1. Update memory-bank/shared/projectbrief.md"
    echo "   2. Create tasks.md with initial tasks"
    echo "   3. Run 'dev-kid orchestrate' to plan execution"
    exit 0
fi

# Parse snapshot
TIMESTAMP=$(jq -r '.timestamp' "$LATEST_SNAPSHOT")
MENTAL_STATE=$(jq -r '.mental_state' "$LATEST_SNAPSHOT")
PROGRESS=$(jq -r '.progress' "$LATEST_SNAPSHOT")
COMPLETED=$(jq -r '.tasks_completed' "$LATEST_SNAPSHOT")
TOTAL=$(jq -r '.tasks_total' "$LATEST_SNAPSHOT")
PHASE=$(jq -r '.current_phase' "$LATEST_SNAPSHOT")

echo ""
echo "📊 Session Restored from: $TIMESTAMP"
echo ""
echo "📌 Phase: $PHASE"
echo "📈 Progress: $COMPLETED/$TOTAL tasks ($PROGRESS%)"
echo ""
echo "💭 Mental State:"
echo "$MENTAL_STATE"
echo ""
echo "🎯 Next Steps:"
jq -r '.next_steps[]' "$LATEST_SNAPSHOT" | while read step; do
    echo "   - $step"
done

echo ""
BLOCKERS=$(jq -r '.blockers | length' "$LATEST_SNAPSHOT")
if [ "$BLOCKERS" -gt 0 ]; then
    echo "🚧 Blockers:"
    jq -r '.blockers[]' "$LATEST_SNAPSHOT" | while read blocker; do
        echo "   - $blocker"
    done
    echo ""
fi

echo "✅ Session context restored"
echo ""
echo "Ready to continue? Run:"
echo "  dev-kid orchestrate    # Plan remaining tasks"
echo "  dev-kid execute         # Execute waves"
echo "  dev-kid sync-memory    # Update Memory Bank"

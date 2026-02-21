#!/usr/bin/env bash
# Skill: Finalize Session
# Trigger: session end, manual "finalize"

set -e

# Helper function to find skills
find_skill() {
    local skill_name="$1"
    local search_paths=(
        "$SCRIPT_DIR/$skill_name"
        "${DEV_KID_ROOT:-$HOME/.dev-kid}/skills/$skill_name"
    )
    for path in "${search_paths[@]}"; do
        if [ -f "$path" ] && [ -x "$path" ]; then
            echo "$path"
            return 0
        fi
    done
    return 1
}

echo "📦 Finalizing session..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Sync memory
if sync_memory=$(find_skill "sync_memory.sh" 2>/dev/null); then
    "$sync_memory"
fi

# Create snapshot
SNAPSHOT_FILE=".claude/session_snapshots/snapshot_$(date +%Y-%m-%d_%H-%M-%S).json"
USER=$(whoami)

# Get current state
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "none")
MODIFIED_FILES=$(git diff --name-only HEAD 2>/dev/null || echo "")

# Read progress
if [ -f "tasks.md" ]; then
    TOTAL=$(grep -c "^- \[" tasks.md || echo 0)
    COMPLETED=$(grep -c "^- \[x\]" tasks.md || echo 0)
    if [ $TOTAL -gt 0 ]; then
        PROGRESS=$(( COMPLETED * 100 / TOTAL ))
    else
        PROGRESS=0
    fi
else
    TOTAL=0
    COMPLETED=0
    PROGRESS=0
fi

# Read active context
MENTAL_STATE="No context"
if [ -f "memory-bank/private/$USER/activeContext.md" ]; then
    MENTAL_STATE=$(head -10 "memory-bank/private/$USER/activeContext.md" | tail -5 || echo "No context")
fi

# Create snapshot JSON
cat > "$SNAPSHOT_FILE" << EOF
{
  "session_id": "session-$(date +%s)",
  "timestamp": "$(date -Iseconds)",
  "mental_state": "$MENTAL_STATE",
  "current_phase": "$(git log -1 --pretty=%s 2>/dev/null || echo 'initialization')",
  "progress": $PROGRESS,
  "tasks_completed": $COMPLETED,
  "tasks_total": $TOTAL,
  "next_steps": [
    "Review progress.md",
    "Update projectbrief.md if needed",
    "Continue next task from tasks.md"
  ],
  "blockers": [],
  "git_commits": ["$CURRENT_COMMIT"],
  "files_modified": $(echo "$MODIFIED_FILES" | jq -Rs 'split("\n") | map(select(length > 0))'),
  "system_state": {
    "memory_bank": "synchronized",
    "context_protection": "active",
    "skills": "operational"
  }
}
EOF

# Create symlink to latest
ln -sf "$(basename $SNAPSHOT_FILE)" ".claude/session_snapshots/snapshot_latest.json"

# Create final checkpoint
if checkpoint=$(find_skill "checkpoint.sh" 2>/dev/null); then
    "$checkpoint" "Session finalized - $COMPLETED/$TOTAL tasks complete"
else
    # Fallback: create checkpoint manually
    git add . 2>/dev/null || true
    if ! git diff --cached --quiet 2>/dev/null; then
        git commit -m "[FINALIZE] Session complete - $COMPLETED/$TOTAL tasks" 2>/dev/null || true
    fi
fi

echo "✅ Session finalized"
echo "   Snapshot: $SNAPSHOT_FILE"
echo "   Progress: $COMPLETED/$TOTAL tasks ($PROGRESS%)"
echo ""
echo "   Next session: Run 'dev-kid recall' to resume"

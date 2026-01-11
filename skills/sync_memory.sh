#!/usr/bin/env bash
# Skill: Sync Memory Bank
# Trigger: "sync memory", after code changes, before checkpoint

set -e

echo "💾 Syncing Memory Bank..."

# Get current user
USER=$(whoami)

# Paths
ACTIVE_CONTEXT="memory-bank/private/$USER/activeContext.md"
PROGRESS="memory-bank/private/$USER/progress.md"
ACTIVITY_STREAM=".claude/activity_stream.md"

# Get git changes since last commit
CHANGES=$(git diff HEAD --stat 2>/dev/null || echo "No changes")

# Update activeContext.md
echo "   Updating activeContext.md..."
cat > "$ACTIVE_CONTEXT" << EOF
# Active Context

**Last Updated**: $(date +%Y-%m-%d\ %H:%M:%S)

## Current Focus
$(git log -1 --pretty=%B 2>/dev/null || echo "Initial commit")

## Recent Changes
\`\`\`
$CHANGES
\`\`\`

## Modified Files
$(git diff --name-only HEAD 2>/dev/null || echo "None")

## Next Actions
- Continue implementation
- Run tests
- Create checkpoint
EOF

# Update progress.md if tasks.md exists
if [ -f "tasks.md" ]; then
    echo "   Updating progress.md from tasks.md..."

    TOTAL=$(grep -c "^- \[" tasks.md || echo 0)
    COMPLETED=$(grep -c "^- \[x\]" tasks.md || echo 0)
    PENDING=$(( TOTAL - COMPLETED ))

    if [ $TOTAL -gt 0 ]; then
        PERCENT=$(( COMPLETED * 100 / TOTAL ))
    else
        PERCENT=0
    fi

    cat > "$PROGRESS" << EOF
# Progress

**Last Updated**: $(date +%Y-%m-%d\ %H:%M:%S)

## Overall Progress
- Total Tasks: $TOTAL
- Completed: $COMPLETED ✅
- Pending: $PENDING ⏳
- Progress: $PERCENT%

## Task Breakdown
$(grep "^- \[" tasks.md || echo "No tasks found")

## Recent Milestones
$(git log --oneline -5 --grep=MILESTONE 2>/dev/null || echo "None yet")
EOF
fi

# Append to activity stream
echo "" >> "$ACTIVITY_STREAM"
echo "### $(date +%Y-%m-%d\ %H:%M:%S) - Memory Sync" >> "$ACTIVITY_STREAM"
echo "- Updated activeContext.md" >> "$ACTIVITY_STREAM"
echo "- Updated progress.md" >> "$ACTIVITY_STREAM"
echo "- Progress: $COMPLETED/$TOTAL tasks complete" >> "$ACTIVITY_STREAM"

echo "✅ Memory Bank synced"

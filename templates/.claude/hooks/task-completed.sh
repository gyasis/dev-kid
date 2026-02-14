#!/usr/bin/env bash
# TaskCompleted Hook - Auto-checkpoint and sync GitHub issues after task completion

set -e

# Read stdin (contains task metadata)
read -r EVENT_DATA

# Log the event
echo "✅ TaskCompleted: Auto-checkpoint initiated" >> .claude/activity_stream.md
echo "   Timestamp: $(date -Iseconds)" >> .claude/activity_stream.md

# Check if dev-kid is available
if ! command -v dev-kid &> /dev/null; then
    echo '{"status": "skipped", "message": "dev-kid not in PATH"}'
    exit 0
fi

# Auto-sync GitHub issues if tasks.md was modified
if [ -f tasks.md ]; then
    TASKS_MODIFIED=$(git diff --name-only tasks.md 2>/dev/null || echo "")
    TASKS_STAGED=$(git diff --cached --name-only tasks.md 2>/dev/null || echo "")

    if [ -n "$TASKS_MODIFIED" ] || [ -n "$TASKS_STAGED" ]; then
        # Sync tasks to GitHub issues
        if [ "$DEV_KID_AUTO_SYNC_GITHUB" = "true" ]; then
            dev-kid gh-sync 2>/dev/null || echo "   ⚠️ GitHub sync skipped (not configured)"
        fi
    fi
fi

# Create micro-checkpoint if auto-checkpoint enabled
if [ "$DEV_KID_AUTO_CHECKPOINT" = "true" ]; then
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        dev-kid checkpoint "[TASK-COMPLETE] Auto-checkpoint" 2>/dev/null || true
    fi
fi

# Return success
echo '{"status": "success", "message": "Task completion processed"}'
exit 0

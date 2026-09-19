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

# Honor the auto-checkpoint toggle (project .devkid/config.json > global > on).
# `dev-kid auto-checkpoint off` sets cli.auto_git_commit=false to suppress this.
# `|| true` on each lookup: `jq` exits non-zero when the config file doesn't
# exist yet (a fresh worktree, a project that hasn't run `dev-kid init`), and
# under this script's `set -e` that killed finalize_session.sh outright,
# before it ever reached the worktree guard below.
_AC=$(jq -r '.cli.auto_git_commit' .devkid/config.json 2>/dev/null || true)
if [ -z "$_AC" ] || [ "$_AC" = "null" ]; then
    _AC=$(jq -r '.cli.auto_git_commit' "${DEV_KID_GLOBAL_CONFIG:-$HOME/.config/dev-kid/config.json}" 2>/dev/null || true)
fi

# ------------------------------------------------------------------
# Refuse to auto-commit from inside a LINKED git worktree.
#
# See skills/checkpoint.sh for the full rationale — the short version:
# multiple agent sessions share one dev-kid-tracked repo via
# `git worktree add`, this script is a TRACKED file so every worktree
# inherits it, and finalizing one session's worktree should never land
# a generic "[FINALIZE]" commit on that worktree's own branch.
#
# Guarded here (not just delegated to checkpoint.sh) so the fallback
# manual-commit path below is covered too.
#
# Override: DEV_KID_ALLOW_WORKTREE_COMMIT=true restores the old
# always-commit behavior inside a worktree.
# ------------------------------------------------------------------
_devkid_in_linked_worktree() {
    local git_dir common_dir
    git_dir=$(git rev-parse --git-dir 2>/dev/null) || return 1
    common_dir=$(git rev-parse --git-common-dir 2>/dev/null) || return 1
    git_dir=$(cd "$git_dir" 2>/dev/null && pwd -P) || return 1
    common_dir=$(cd "$common_dir" 2>/dev/null && pwd -P) || return 1
    [ "$git_dir" != "$common_dir" ]
}

if _devkid_in_linked_worktree && [ "${DEV_KID_ALLOW_WORKTREE_COMMIT:-false}" != "true" ]; then
    echo "ℹ️  Linked git worktree detected — skipping git commit (finalize never auto-commits inside a worktree)"
    echo "   Override with DEV_KID_ALLOW_WORKTREE_COMMIT=true if you really want to commit here"
elif [ "$_AC" = "false" ]; then
    echo "ℹ️  auto-checkpoint disabled (dev-kid config) — skipping git commit"
# Create final checkpoint
elif checkpoint=$(find_skill "checkpoint.sh" 2>/dev/null); then
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

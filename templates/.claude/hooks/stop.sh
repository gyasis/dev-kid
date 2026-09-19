#!/usr/bin/env bash
# Stop Hook - optionally auto-finalize when Claude stops responding.
# Claude Code: exit 0 = allow stop, exit 2 = block stop (rare)
#
# Auto-commit policy (fixed 2026-06-05): the AUTHORITATIVE gate is
# `.devkid/config.json -> cli.auto_git_commit` (the same flag `dev-kid auto-checkpoint
# on|off` writes), with the global config as fallback. Default is OFF (opt-in) so the
# Stop hook NEVER commits the user's tree unless they explicitly enabled it. This
# replaces the old default-true `DEV_KID_AUTO_CHECKPOINT` env knob, which didn't read
# the config and silently hijacked git history.

# Master kill-switch
if [ "${DEV_KID_HOOKS_ENABLED:-true}" = "false" ]; then
    exit 0
fi

read -r EVENT_DATA || true

# Log the stop event
echo "$(date -Iseconds) SessionStop" >> .claude/activity_stream.md 2>/dev/null || true

# Resolve auto_git_commit: project config > global config > OFF (opt-in default).
_AC=$(jq -r '.cli.auto_git_commit' .devkid/config.json 2>/dev/null)
if [ -z "$_AC" ] || [ "$_AC" = "null" ]; then
    _AC=$(jq -r '.cli.auto_git_commit' "${DEV_KID_GLOBAL_CONFIG:-$HOME/.config/dev-kid/config.json}" 2>/dev/null)
fi
# Optional env override stays available but DEFAULTS OFF now.
[ "${DEV_KID_AUTO_CHECKPOINT:-}" = "true" ] && _AC=true

# Refuse to auto-commit from inside a LINKED git worktree (see
# skills/checkpoint.sh for the full rationale). `dev-kid finalize`
# already guards this itself, but this hook is TEMPLATE-copied into
# every project's .claude/hooks/, which can lag behind a dev-kid core
# update — so it guards independently too.
# Override: DEV_KID_ALLOW_WORKTREE_COMMIT=true.
_devkid_in_linked_worktree() {
    local git_dir common_dir
    git_dir=$(git rev-parse --git-dir 2>/dev/null) || return 1
    common_dir=$(git rev-parse --git-common-dir 2>/dev/null) || return 1
    git_dir=$(cd "$git_dir" 2>/dev/null && pwd -P) || return 1
    common_dir=$(cd "$common_dir" 2>/dev/null && pwd -P) || return 1
    [ "$git_dir" != "$common_dir" ]
}

if [ "$_AC" = "true" ]; then
    if _devkid_in_linked_worktree && [ "${DEV_KID_ALLOW_WORKTREE_COMMIT:-false}" != "true" ]; then
        echo "$(date -Iseconds) SessionStop: linked worktree detected, skipping auto-finalize" >> .claude/activity_stream.md 2>/dev/null || true
    elif command -v dev-kid &>/dev/null; then
        if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
            dev-kid finalize 2>/dev/null || true
        fi
    fi
fi

exit 0

#!/bin/bash
# Test script for the "never auto-commit from a linked git worktree" fix.
#
# dev-kid's checkpoint/finalize skills and Stop/TaskCompleted hooks used to
# `git add` + commit the WHOLE working tree unconditionally. Several agent
# sessions often share one repo via `git worktree add` (each gets its own
# branch + working directory), and these scripts are TRACKED files, so every
# worktree inherits them — meaning a session's own auto-commit would land a
# generic "[CHECKPOINT]"/"[FINALIZE]" commit on that worktree's own branch,
# which is usually meant to hold only that session's intentional commits.
#
# Covers: checkpoint.sh + finalize_session.sh skip staging/committing inside
# a linked worktree (dirty file stays untouched), old always-commit behavior
# is preserved in the MAIN checkout, DEV_KID_ALLOW_WORKTREE_COMMIT=true
# re-enables committing inside a worktree, task-completed.sh now resolves
# auto_git_commit the same way stop.sh does (and defaults OFF with no
# config, instead of the old always-on `${DEV_KID_AUTO_CHECKPOINT:-true}`),
# and both hook templates (stop.sh, task-completed.sh) skip their commit
# path inside a linked worktree even with auto_git_commit=true.
set -e

echo "🧪 Testing: never auto-commit from a linked git worktree"
echo "=========================================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

PASSED=0
FAILED=0

test_result() {
    if [ "$1" -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        FAILED=$((FAILED + 1))
    fi
}

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
CHECKPOINT_SH="$REPO_ROOT/skills/checkpoint.sh"
FINALIZE_SH="$REPO_ROOT/skills/finalize_session.sh"
STOP_HOOK="$REPO_ROOT/templates/.claude/hooks/stop.sh"
TASK_COMPLETED_HOOK="$REPO_ROOT/templates/.claude/hooks/task-completed.sh"

SANDBOX_ROOT="${TMPDIR:-/tmp}/dk-worktree-tests-$$"
trap "rm -rf \"$SANDBOX_ROOT\"" EXIT
mkdir -p "$SANDBOX_ROOT"

# ------------------------------------------------------------------
# Isolation: point dev-kid's fallback lookups at scratch locations
# that do NOT exist, so these tests never read the real machine's
# ~/.dev-kid or ~/.config/dev-kid/config.json (which may itself have
# auto_git_commit=true and would silently contaminate every "default"
# assertion below).
# ------------------------------------------------------------------
export DEV_KID_ROOT="$SANDBOX_ROOT/_empty-devkid-root"
export DEV_KID_GLOBAL_CONFIG="$SANDBOX_ROOT/_no-such-global-config.json"
mkdir -p "$DEV_KID_ROOT"

# Stub `dev-kid` binary for the hook tests (stop.sh / task-completed.sh call
# the real `dev-kid` command, not a skill script directly) — records every
# invocation instead of doing real work.
STUB_BIN="$SANDBOX_ROOT/_stubbin"
mkdir -p "$STUB_BIN"
cat > "$STUB_BIN/dev-kid" <<'EOF'
#!/usr/bin/env bash
echo "dev-kid $*" >> "$DEVKID_STUB_LOG"
exit 0
EOF
chmod +x "$STUB_BIN/dev-kid"
export PATH="$STUB_BIN:$PATH"
export DEVKID_STUB_LOG="$SANDBOX_ROOT/_stub.log"

new_sandbox() {
    local name="$1"
    local dir="$SANDBOX_ROOT/$name"
    rm -rf "$dir"
    mkdir -p "$dir"
    (
        cd "$dir"
        git init -q
        git config user.email "t@t.com"
        git config user.name "t"
        echo "line1" > tracked.txt
        git add tracked.txt
        git commit -qm "init" >/dev/null 2>&1
    )
    echo "$dir"
}

# Deliberately NOT copying skills/sync_memory.sh into any sandbox: it needs a
# memory-bank/private/<user>/ dir to exist and isn't part of what this fix
# touches. Since each sandbox's own skills/ dir lacks it, and DEV_KID_ROOT
# points at an empty scratch dir, `find_skill sync_memory.sh` fails cleanly
# and checkpoint.sh/finalize_session.sh just skip that step (verified).
#
# Files are COMMITTED right after being installed — worktrees only inherit
# TRACKED content, and that tracked-ness is the entire premise of the bug
# being fixed here, so tests must create it the same way.
install_checkpoint() {
    local dir="$1"
    mkdir -p "$dir/skills"
    cp "$CHECKPOINT_SH" "$dir/skills/checkpoint.sh"
    chmod +x "$dir/skills/checkpoint.sh"
    git -C "$dir" add skills/checkpoint.sh
    git -C "$dir" commit -qm "install checkpoint.sh" >/dev/null 2>&1
}

install_finalize() {
    local dir="$1"
    install_checkpoint "$dir"
    cp "$FINALIZE_SH" "$dir/skills/finalize_session.sh"
    chmod +x "$dir/skills/finalize_session.sh"
    mkdir -p "$dir/.claude/session_snapshots"
    touch "$dir/.claude/session_snapshots/.gitkeep"
    git -C "$dir" add skills/finalize_session.sh .claude/session_snapshots/.gitkeep
    git -C "$dir" commit -qm "install finalize_session.sh" >/dev/null 2>&1
}

install_hooks() {
    local dir="$1"
    mkdir -p "$dir/.claude/hooks"
    cp "$STOP_HOOK" "$dir/.claude/hooks/stop.sh"
    cp "$TASK_COMPLETED_HOOK" "$dir/.claude/hooks/task-completed.sh"
    chmod +x "$dir/.claude/hooks/stop.sh" "$dir/.claude/hooks/task-completed.sh"
    git -C "$dir" add .claude/hooks/stop.sh .claude/hooks/task-completed.sh
    git -C "$dir" commit -qm "install hooks" >/dev/null 2>&1
}

dirty_tracked_file() {
    local dir="$1"
    echo "dirty change $RANDOM" >> "$dir/tracked.txt"
}

head_of() { git -C "$1" rev-parse HEAD; }

# true (0) if tracked.txt has an uncommitted change, false (1) if clean.
tracked_is_dirty() {
    ! git -C "$1" diff --quiet -- tracked.txt
}

reset_stub_log() { : > "$DEVKID_STUB_LOG"; }
stub_was_called() { [ -s "$DEVKID_STUB_LOG" ]; }

# ══════════════════════════════════════════════════════════════════
# Test 1: checkpoint.sh skips staging/commit inside a linked worktree
# ══════════════════════════════════════════════════════════════════
echo "Test 1: checkpoint.sh — linked worktree, no commit, file stays unstaged"
echo "-------------------------------------------------------------------------"
SBX=$(new_sandbox test1)
install_checkpoint "$SBX"
git -C "$SBX" worktree add -q -b test1-wt "$SBX-wt" >/dev/null 2>&1
dirty_tracked_file "$SBX-wt"
BEFORE=$(head_of "$SBX-wt")

OUTPUT=$(cd "$SBX-wt" && bash skills/checkpoint.sh "attempted checkpoint" 2>&1)
RC=$?

test_result "$RC" "checkpoint.sh exits 0 inside a worktree (skip, not error)"

if [ "$(head_of "$SBX-wt")" = "$BEFORE" ]; then
    test_result 0 "No commit was created inside the worktree"
else
    test_result 1 "A commit WAS created inside the worktree (should have been skipped)"
fi

if tracked_is_dirty "$SBX-wt"; then
    test_result 0 "tracked.txt is still unstaged/uncommitted"
else
    test_result 1 "tracked.txt was staged/committed (should have been left alone)"
fi

if echo "$OUTPUT" | grep -qi "linked git worktree detected"; then
    test_result 0 "Prints a clear message explaining why it skipped"
else
    test_result 1 "No explanatory message printed"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 2: checkpoint.sh still commits normally in the MAIN checkout
# ══════════════════════════════════════════════════════════════════
echo "Test 2: checkpoint.sh — main checkout, old commit behavior preserved"
echo "-----------------------------------------------------------------------"
SBX=$(new_sandbox test2)
install_checkpoint "$SBX"
dirty_tracked_file "$SBX"
BEFORE=$(head_of "$SBX")

(cd "$SBX" && bash skills/checkpoint.sh "main checkpoint" >/dev/null 2>&1)

if [ "$(head_of "$SBX")" != "$BEFORE" ]; then
    test_result 0 "A commit was created in the main checkout"
else
    test_result 1 "No commit was created in the main checkout (regression)"
fi
if tracked_is_dirty "$SBX"; then
    test_result 1 "tracked.txt is still dirty after checkpoint (should be committed)"
else
    test_result 0 "tracked.txt was committed cleanly"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 3: DEV_KID_ALLOW_WORKTREE_COMMIT=true re-enables commit
# ══════════════════════════════════════════════════════════════════
echo "Test 3: checkpoint.sh — DEV_KID_ALLOW_WORKTREE_COMMIT=true overrides"
echo "-----------------------------------------------------------------------"
SBX=$(new_sandbox test3)
install_checkpoint "$SBX"
git -C "$SBX" worktree add -q -b test3-wt "$SBX-wt" >/dev/null 2>&1
dirty_tracked_file "$SBX-wt"
BEFORE=$(head_of "$SBX-wt")

(cd "$SBX-wt" && DEV_KID_ALLOW_WORKTREE_COMMIT=true bash skills/checkpoint.sh "override" >/dev/null 2>&1)

if [ "$(head_of "$SBX-wt")" != "$BEFORE" ]; then
    test_result 0 "Override env var re-enables the commit inside a worktree"
else
    test_result 1 "Override env var did NOT re-enable the commit"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 4: finalize_session.sh skips commit in a worktree, keeps
#          non-git bookkeeping (the snapshot file) working
# ══════════════════════════════════════════════════════════════════
echo "Test 4: finalize_session.sh — linked worktree, no commit, snapshot still written"
echo "-------------------------------------------------------------------------------"
SBX=$(new_sandbox test4)
install_finalize "$SBX"
git -C "$SBX" worktree add -q -b test4-wt "$SBX-wt" >/dev/null 2>&1
dirty_tracked_file "$SBX-wt"
BEFORE=$(head_of "$SBX-wt")

OUTPUT=$(cd "$SBX-wt" && bash skills/finalize_session.sh 2>&1)
RC=$?

test_result "$RC" "finalize_session.sh exits 0 inside a worktree"

if [ "$(head_of "$SBX-wt")" = "$BEFORE" ]; then
    test_result 0 "No commit was created inside the worktree"
else
    test_result 1 "A commit WAS created inside the worktree (should have been skipped)"
fi
if tracked_is_dirty "$SBX-wt"; then
    test_result 0 "tracked.txt is still unstaged/uncommitted"
else
    test_result 1 "tracked.txt was staged/committed (should have been left alone)"
fi
if compgen -G "$SBX-wt/.claude/session_snapshots/snapshot_*.json" > /dev/null; then
    test_result 0 "Session snapshot (non-git bookkeeping) was still written"
else
    test_result 1 "Session snapshot was NOT written"
fi
if echo "$OUTPUT" | grep -qi "linked git worktree detected"; then
    test_result 0 "Prints a clear message explaining why it skipped"
else
    test_result 1 "No explanatory message printed"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 5: finalize_session.sh still commits normally in the MAIN
#          checkout (old default-on behavior preserved)
# ══════════════════════════════════════════════════════════════════
echo "Test 5: finalize_session.sh — main checkout, old commit behavior preserved"
echo "-------------------------------------------------------------------------------"
SBX=$(new_sandbox test5)
install_finalize "$SBX"
dirty_tracked_file "$SBX"
BEFORE=$(head_of "$SBX")

(cd "$SBX" && bash skills/finalize_session.sh >/dev/null 2>&1)

if [ "$(head_of "$SBX")" != "$BEFORE" ]; then
    test_result 0 "A commit was created in the main checkout"
else
    test_result 1 "No commit was created in the main checkout (regression)"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 6: finalize_session.sh — DEV_KID_ALLOW_WORKTREE_COMMIT=true
# ══════════════════════════════════════════════════════════════════
echo "Test 6: finalize_session.sh — DEV_KID_ALLOW_WORKTREE_COMMIT=true overrides"
echo "-------------------------------------------------------------------------------"
SBX=$(new_sandbox test6)
install_finalize "$SBX"
git -C "$SBX" worktree add -q -b test6-wt "$SBX-wt" >/dev/null 2>&1
dirty_tracked_file "$SBX-wt"
BEFORE=$(head_of "$SBX-wt")

(cd "$SBX-wt" && DEV_KID_ALLOW_WORKTREE_COMMIT=true bash skills/finalize_session.sh >/dev/null 2>&1)

if [ "$(head_of "$SBX-wt")" != "$BEFORE" ]; then
    test_result 0 "Override env var re-enables the commit inside a worktree"
else
    test_result 1 "Override env var did NOT re-enable the commit"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 7: task-completed.sh defaults auto-checkpoint OFF with no
#          .devkid/config.json anywhere (the ${..:-true} bug)
# ══════════════════════════════════════════════════════════════════
echo "Test 7: task-completed.sh — defaults to OFF with no config present"
echo "-------------------------------------------------------------------------------"
SBX=$(new_sandbox test7)
install_hooks "$SBX"
dirty_tracked_file "$SBX"
reset_stub_log

(cd "$SBX" && echo '{}' | bash .claude/hooks/task-completed.sh >/dev/null 2>&1)

if stub_was_called; then
    test_result 1 "dev-kid checkpoint WAS invoked with no config (should default OFF)"
else
    test_result 0 "dev-kid checkpoint was NOT invoked — correctly defaults OFF"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 8: task-completed.sh respects auto_git_commit=true from
#          .devkid/config.json in the MAIN checkout
# ══════════════════════════════════════════════════════════════════
echo "Test 8: task-completed.sh — honors .devkid/config.json auto_git_commit=true"
echo "-------------------------------------------------------------------------------"
SBX=$(new_sandbox test8)
install_hooks "$SBX"
mkdir -p "$SBX/.devkid"
echo '{"cli":{"auto_git_commit":true}}' > "$SBX/.devkid/config.json"
dirty_tracked_file "$SBX"
reset_stub_log

(cd "$SBX" && echo '{}' | bash .claude/hooks/task-completed.sh >/dev/null 2>&1)

if stub_was_called; then
    test_result 0 "dev-kid checkpoint was invoked when config enables it"
else
    test_result 1 "dev-kid checkpoint was NOT invoked even though config enables it"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 9: task-completed.sh skips the commit path inside a linked
#          worktree, even with auto_git_commit=true
# ══════════════════════════════════════════════════════════════════
echo "Test 9: task-completed.sh — linked worktree overrides auto_git_commit=true"
echo "-------------------------------------------------------------------------------"
SBX=$(new_sandbox test9)
install_hooks "$SBX"
mkdir -p "$SBX/.devkid"
echo '{"cli":{"auto_git_commit":true}}' > "$SBX/.devkid/config.json"
git -C "$SBX" add .devkid/config.json
git -C "$SBX" commit -qm "add devkid config" >/dev/null 2>&1
git -C "$SBX" worktree add -q -b test9-wt "$SBX-wt" >/dev/null 2>&1
dirty_tracked_file "$SBX-wt"
reset_stub_log

(cd "$SBX-wt" && echo '{}' | bash .claude/hooks/task-completed.sh >/dev/null 2>&1)

if stub_was_called; then
    test_result 1 "dev-kid checkpoint WAS invoked inside a worktree (should be skipped)"
else
    test_result 0 "dev-kid checkpoint was NOT invoked inside a worktree"
fi

# ...and the override still works
reset_stub_log
(cd "$SBX-wt" && DEV_KID_ALLOW_WORKTREE_COMMIT=true bash -c 'echo "{}" | bash .claude/hooks/task-completed.sh' >/dev/null 2>&1)
if stub_was_called; then
    test_result 0 "DEV_KID_ALLOW_WORKTREE_COMMIT=true re-enables it inside a worktree"
else
    test_result 1 "Override env var did NOT re-enable it inside a worktree"
fi
echo ""

# ══════════════════════════════════════════════════════════════════
# Test 10: stop.sh skips the commit path inside a linked worktree,
#           even with auto_git_commit=true; override still works
# ══════════════════════════════════════════════════════════════════
echo "Test 10: stop.sh — linked worktree overrides auto_git_commit=true"
echo "-------------------------------------------------------------------------------"
SBX=$(new_sandbox test10)
install_hooks "$SBX"
mkdir -p "$SBX/.devkid"
echo '{"cli":{"auto_git_commit":true}}' > "$SBX/.devkid/config.json"
git -C "$SBX" add .devkid/config.json
git -C "$SBX" commit -qm "add devkid config" >/dev/null 2>&1
git -C "$SBX" worktree add -q -b test10-wt "$SBX-wt" >/dev/null 2>&1
dirty_tracked_file "$SBX-wt"
reset_stub_log

(cd "$SBX-wt" && echo '{}' | bash .claude/hooks/stop.sh >/dev/null 2>&1)

if stub_was_called; then
    test_result 1 "dev-kid finalize WAS invoked inside a worktree (should be skipped)"
else
    test_result 0 "dev-kid finalize was NOT invoked inside a worktree"
fi

reset_stub_log
(cd "$SBX-wt" && DEV_KID_ALLOW_WORKTREE_COMMIT=true bash -c 'echo "{}" | bash .claude/hooks/stop.sh' >/dev/null 2>&1)
if stub_was_called; then
    test_result 0 "DEV_KID_ALLOW_WORKTREE_COMMIT=true re-enables it inside a worktree"
else
    test_result 1 "Override env var did NOT re-enable it inside a worktree"
fi

# ...and the MAIN checkout with auto_git_commit=true still invokes it
reset_stub_log
dirty_tracked_file "$SBX"
(cd "$SBX" && echo '{}' | bash .claude/hooks/stop.sh >/dev/null 2>&1)
if stub_was_called; then
    test_result 0 "dev-kid finalize was invoked in the main checkout (old behavior preserved)"
else
    test_result 1 "dev-kid finalize was NOT invoked in the main checkout (regression)"
fi
echo ""

# ─── Summary ───
echo "=========================================================="
echo -e "Results: ${GREEN}${PASSED} passed${NC}, ${RED}${FAILED} failed${NC}"
echo ""

if [ "$FAILED" -gt 0 ]; then
    exit 1
fi
exit 0

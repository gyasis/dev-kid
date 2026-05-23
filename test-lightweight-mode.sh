#!/bin/bash
# Test script for lightweight mode (.dk/tasks.md marker)
# Covers: resolution priority, coexistence with SpecKit, no-regression, init scaffolder
set -e

echo "🧪 Testing Lightweight Mode (.dk/tasks.md)"
echo "==========================================="
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        FAILED=$((FAILED + 1))
    fi
}

DEV_KID="$(cd "$(dirname "$0")" && pwd)/cli/dev-kid"
SANDBOX_ROOT="${TMPDIR:-/tmp}/dk-lightweight-tests-$$"
trap "rm -rf $SANDBOX_ROOT" EXIT

new_sandbox() {
    local name="$1"
    local dir="$SANDBOX_ROOT/$name"
    rm -rf "$dir"
    mkdir -p "$dir"
    (cd "$dir" && git init -q && git commit --allow-empty -qm "init" >/dev/null 2>&1)
    echo "$dir"
}

# ─── Test 1: init --lightweight scaffolds .dk/tasks.md (non-TTY safe) ───
echo "Test 1: init --lightweight scaffolds .dk/tasks.md (non-TTY)"
echo "-----------------------------------------------------------"
SBX=$(new_sandbox test1)
# Use </dev/null to simulate non-TTY (CI, pipes) — must NOT hang or abort
if (cd "$SBX" && "$DEV_KID" init --lightweight . </dev/null >/dev/null 2>&1); then
    test_result 0 "init --lightweight exits 0 in non-TTY mode"
else
    test_result 1 "init --lightweight FAILED in non-TTY mode (exit non-zero)"
fi
if [ -f "$SBX/.dk/tasks.md" ]; then
    test_result 0 ".dk/tasks.md created by init --lightweight"
else
    test_result 1 ".dk/tasks.md NOT created by init --lightweight"
fi
echo ""

# ─── Test 2: .dk/tasks.md resolves at priority 1 ───
echo "Test 2: .dk/tasks.md resolves at priority 1"
echo "-------------------------------------------"
SBX=$(new_sandbox test2)
mkdir -p "$SBX/.dk"
echo "- [ ] T001: test task" > "$SBX/.dk/tasks.md"
OUTPUT=$(cd "$SBX" && "$DEV_KID" spec-resolve 2>&1)
if echo "$OUTPUT" | grep -q "devkid would use: .dk/tasks.md"; then
    test_result 0 "spec-resolve picks .dk/tasks.md when present"
else
    test_result 1 "spec-resolve did NOT pick .dk/tasks.md"
    echo "$OUTPUT" | tail -5
fi
if echo "$OUTPUT" | grep -q "priority 1"; then
    test_result 0 "Priority 1 reported correctly"
else
    test_result 1 "Priority 1 NOT reported"
fi
echo ""

# ─── Test 3: .dk/ wins over SpecKit when both exist ───
echo "Test 3: .dk/tasks.md wins over SpecKit when both present"
echo "--------------------------------------------------------"
SBX=$(new_sandbox test3)
mkdir -p "$SBX/.dk" "$SBX/.specify/specs/master"
echo "- [ ] DK001: lightweight version" > "$SBX/.dk/tasks.md"
echo "- [ ] SK001: speckit version" > "$SBX/.specify/specs/master/tasks.md"
OUTPUT=$(cd "$SBX" && "$DEV_KID" spec-resolve 2>&1)
if echo "$OUTPUT" | grep -q "devkid would use: .dk/tasks.md"; then
    test_result 0 ".dk/ wins coexistence with SpecKit"
else
    test_result 1 ".dk/ did NOT win — got: $(echo "$OUTPUT" | grep 'devkid would use')"
fi
echo ""

# ─── Test 4: No .dk/, SpecKit resolution unchanged (regression) ───
echo "Test 4: No regression — SpecKit chain works without .dk/"
echo "--------------------------------------------------------"
SBX=$(new_sandbox test4)
mkdir -p "$SBX/.specify/specs/master"
echo "- [ ] SK001: speckit task" > "$SBX/.specify/specs/master/tasks.md"
OUTPUT=$(cd "$SBX" && "$DEV_KID" spec-resolve 2>&1)
if echo "$OUTPUT" | grep -q "devkid would use: .specify/specs/master/tasks.md"; then
    test_result 0 "SpecKit chain resolves correctly when no .dk/"
else
    test_result 1 "SpecKit chain BROKEN — got: $(echo "$OUTPUT" | grep 'devkid would use')"
fi
if echo "$OUTPUT" | grep -q "priority 3"; then
    test_result 0 "SpecKit branch-match reported as priority 3 (shifted from 2)"
else
    test_result 1 "Priority numbering wrong for SpecKit branch match"
fi
echo ""

# ─── Test 5: orchestrate end-to-end via .dk/ ───
echo "Test 5: orchestrate builds plan from .dk/tasks.md"
echo "-------------------------------------------------"
SBX=$(new_sandbox test5)
mkdir -p "$SBX/.dk"
cat > "$SBX/.dk/tasks.md" <<'EOF'
# Tasks
- [ ] T001: Make `src/a.py`
- [ ] T002: Make `src/b.py`
EOF
OUTPUT=$(cd "$SBX" && "$DEV_KID" orchestrate "test5" 2>&1)
if echo "$OUTPUT" | grep -q "tasks.md = .dk/tasks.md"; then
    test_result 0 "orchestrate resolved .dk/tasks.md"
else
    test_result 1 "orchestrate did NOT resolve .dk/tasks.md"
fi
if [ -f "$SBX/execution_plan.json" ]; then
    test_result 0 "execution_plan.json generated"
else
    test_result 1 "execution_plan.json NOT generated"
fi
if [ -L "$SBX/tasks.md" ] && [ "$(readlink "$SBX/tasks.md")" = ".dk/tasks.md" ]; then
    test_result 0 "Symlink tasks.md → .dk/tasks.md created"
else
    test_result 1 "Symlink to .dk/tasks.md NOT created correctly"
fi
echo ""

# ─── Summary ───
echo "==========================================="
echo "Results: ${GREEN}${PASSED} passed${NC}, ${RED}${FAILED} failed${NC}"
echo ""

if [ $FAILED -gt 0 ]; then
    exit 1
fi
exit 0

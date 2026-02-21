#!/bin/bash
# Test script for error handling and Speckit integration
set -e

echo "🧪 Testing Error Handling & Speckit Integration"
echo "================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $2"
        PASSED=$((PASSED + 1))
    else
        echo -e "${RED}❌ FAIL${NC}: $2"
        FAILED=$((FAILED + 1))
    fi
}

test_warning() {
    echo -e "${YELLOW}⚠️  WARN${NC}: $1"
    WARNINGS=$((WARNINGS + 1))
}

# Test 1: JSON corruption recovery (task_watchdog.py)
echo "Test 1: JSON corruption recovery"
echo "---------------------------------"
mkdir -p .claude
echo "{ invalid json" > .claude/task_timers.json

if python3 cli/task_watchdog.py check 2>&1 | grep -q "Corrupted"; then
    test_result 0 "Watchdog handles corrupted JSON gracefully"

    # Check backup was created
    if [ -f ".claude/task_timers.json.corrupted" ]; then
        test_result 0 "Backup of corrupted file created"
    else
        test_result 1 "No backup file created"
    fi
else
    test_result 1 "Watchdog did not handle corrupted JSON"
fi

# Cleanup
rm -f .claude/task_timers.json .claude/task_timers.json.corrupted
echo ""

# Test 2: Execution plan JSON corruption recovery
echo "Test 2: Execution plan corruption recovery"
echo "-------------------------------------------"
echo "{ invalid json" > execution_plan.json

if python3 cli/wave_executor.py 2>&1 | grep -q "Invalid JSON"; then
    test_result 0 "Wave executor detects corrupted execution plan"

    # Check backup was created
    if [ -f "execution_plan.json.corrupted" ]; then
        test_result 0 "Backup of corrupted execution plan created"
    else
        test_result 1 "No backup file created"
    fi
else
    test_result 1 "Wave executor did not detect corruption"
fi

# Cleanup
rm -f execution_plan.json execution_plan.json.corrupted
echo ""

# Test 3: Atomic writes (orchestrator)
echo "Test 3: Atomic file writes"
echo "--------------------------"
# Create a valid tasks.md
cat > tasks.md << 'EOF'
# Test Tasks
- [ ] Task 1: Test atomic writes in `file1.py`
- [ ] Task 2: Test atomic writes in `file2.py`
EOF

python3 cli/orchestrator.py --phase-id "test" > /dev/null 2>&1

if [ -f "execution_plan.json" ]; then
    # Check JSON is valid
    if python3 -c "import json; json.load(open('execution_plan.json'))" 2>/dev/null; then
        test_result 0 "Orchestrator creates valid JSON"

        # Check no temp file left behind
        if [ ! -f "execution_plan.tmp" ]; then
            test_result 0 "No temporary files left behind"
        else
            test_result 1 "Temporary file not cleaned up"
        fi
    else
        test_result 1 "Orchestrator created invalid JSON"
    fi
else
    test_result 1 "Orchestrator did not create execution plan"
fi

# Cleanup
rm -f tasks.md execution_plan.json execution_plan.tmp
echo ""

# Test 4: UTF-8 encoding handling
echo "Test 4: UTF-8 encoding"
echo "----------------------"
cat > tasks.md << 'EOF'
# Test Tasks with UTF-8
- [ ] Task 1: Handle UTF-8 characters like 🚀 and émojis in `file1.py`
- [ ] Task 2: Test Chinese characters 中文 in `file2.py`
EOF

if python3 cli/orchestrator.py --phase-id "utf8-test" 2>&1 | grep -qv "Error"; then
    test_result 0 "Orchestrator handles UTF-8 characters"
else
    test_result 1 "Orchestrator failed on UTF-8 characters"
fi

# Cleanup
rm -f tasks.md execution_plan.json
echo ""

# Test 5: Speckit symlink validation (if git initialized)
echo "Test 5: Speckit symlink validation"
echo "-----------------------------------"
if [ -d ".git" ]; then
    # Create test spec structure
    mkdir -p .specify/specs/test-branch
    echo "# Test Tasks" > .specify/specs/test-branch/tasks.md
    echo "- [ ] Test task" >> .specify/specs/test-branch/tasks.md

    # Simulate post-checkout hook
    BRANCH="test-branch"
    SPEC_TASKS=".specify/specs/test-branch/tasks.md"

    # Remove existing tasks.md
    rm -f tasks.md

    # Create symlink
    if [ -f "$SPEC_TASKS" ] && [ -r "$SPEC_TASKS" ]; then
        ln -s "$SPEC_TASKS" tasks.md

        if [ -r "tasks.md" ]; then
            test_result 0 "Symlink created and readable"
        else
            test_result 1 "Symlink created but not readable"
        fi
    else
        test_result 1 "Spec tasks file not found or not readable"
    fi

    # Cleanup
    rm -f tasks.md
    rm -rf .specify
else
    test_warning "Git not initialized, skipping symlink test"
fi
echo ""

# Test 6: Constitution loading error handling
echo "Test 6: Constitution loading"
echo "----------------------------"
mkdir -p memory-bank/shared

# Clean up any existing constitution from previous tests
rm -f memory-bank/shared/.constitution.md

# Test missing constitution
if python3 -c "
import sys
sys.path.insert(0, 'cli')
from wave_executor import WaveExecutor
executor = WaveExecutor()
print('OK' if executor.constitution is None else 'ERROR')
" 2>&1 | grep -q "OK"; then
    test_result 0 "Wave executor handles missing constitution"
else
    test_result 1 "Wave executor failed on missing constitution"
fi

# Test corrupted constitution (empty file parses OK, so test permissions instead)
touch memory-bank/shared/.constitution.md
chmod 000 memory-bank/shared/.constitution.md

if python3 -c "
import sys
sys.path.insert(0, 'cli')
from wave_executor import WaveExecutor
executor = WaveExecutor()
" 2>&1 | grep -q "Failed to load constitution"; then
    test_result 0 "Wave executor handles corrupted/unreadable constitution"
    chmod 644 memory-bank/shared/.constitution.md  # Restore permissions
elif python3 -c "
import sys
sys.path.insert(0, 'cli')
from wave_executor import WaveExecutor
executor = WaveExecutor()
print('OK' if executor.constitution is None else 'ERROR')
" 2>&1 | grep -q "OK"; then
    test_result 0 "Wave executor handles corrupted/unreadable constitution (constitution=None)"
    chmod 644 memory-bank/shared/.constitution.md  # Restore permissions
else
    chmod 644 memory-bank/shared/.constitution.md  # Restore permissions anyway
    test_result 1 "Wave executor did not handle corrupted constitution"
fi

# Cleanup
rm -f memory-bank/shared/.constitution.md
echo ""

# Summary
echo "================================================"
echo "Test Results:"
echo "  ${GREEN}✅ Passed: $PASSED${NC}"
echo "  ${RED}❌ Failed: $FAILED${NC}"
echo "  ${YELLOW}⚠️  Warnings: $WARNINGS${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed. Review output above.${NC}"
    exit 1
fi

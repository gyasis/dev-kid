#!/bin/bash
# Edge Case Testing for Ralph Optimization Implementation
# Tests failure modes and data loss scenarios

# Don't exit on error - we're testing error conditions
set +e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Result arrays
declare -a FAILED_TESTS
declare -a PASSED_TESTS

# Logging
LOG_FILE="/tmp/ralph-edge-case-tests.log"
echo "Test started: $(date)" > "$LOG_FILE"

# Helper functions
log() {
    echo -e "${BLUE}[LOG]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[PASS]${NC} $1" | tee -a "$LOG_FILE"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    PASSED_TESTS+=("$1")
}

fail() {
    echo -e "${RED}[FAIL]${NC} $1" | tee -a "$LOG_FILE"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    FAILED_TESTS+=("$1")
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "$LOG_FILE"
}

test_header() {
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}TEST $TESTS_TOTAL: $1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

# Test environment setup
setup_test_env() {
    TEST_DIR="/tmp/ralph-edge-case-test-$$"
    mkdir -p "$TEST_DIR"
    cd "$TEST_DIR"
    git init -q
    git config user.name "Test User"
    git config user.email "test@example.com"

    log "Test environment: $TEST_DIR"
}

cleanup_test_env() {
    if [ -d "$TEST_DIR" ]; then
        cd /
        rm -rf "$TEST_DIR"
    fi
}

# Trap to ensure cleanup
trap cleanup_test_env EXIT

###########################################
# CONTEXT MONITOR EDGE CASES
###########################################

test_context_monitor_missing_claude_dir() {
    test_header "Context Monitor: Missing .claude/ directory"
    setup_test_env

    # Don't create .claude directory
    python3 /home/gyasis/Documents/code/dev-kid/cli/context_monitor.py --check
    RESULT=$?

    if [ $RESULT -eq 0 ]; then
        success "Context monitor handles missing .claude/ directory gracefully"
    else
        fail "Context monitor crashed on missing .claude/ directory (exit code: $RESULT)"
    fi

    cleanup_test_env
}

test_context_monitor_empty_activity_stream() {
    test_header "Context Monitor: Empty activity_stream.md"
    setup_test_env

    mkdir -p .claude
    touch .claude/activity_stream.md

    python3 /home/gyasis/Documents/code/dev-kid/cli/context_monitor.py --check
    RESULT=$?

    if [ $RESULT -eq 0 ]; then
        success "Context monitor handles empty activity_stream.md"
    else
        fail "Context monitor failed on empty activity_stream.md (exit code: $RESULT)"
    fi

    cleanup_test_env
}

test_context_monitor_large_file() {
    test_header "Context Monitor: Large activity_stream.md (>5MB)"
    setup_test_env

    mkdir -p .claude
    # Generate 6MB file
    dd if=/dev/urandom of=.claude/activity_stream.md bs=1M count=6 2>/dev/null

    START=$(date +%s)
    python3 /home/gyasis/Documents/code/dev-kid/cli/context_monitor.py --check || true
    RESULT=$?
    END=$(date +%s)
    DURATION=$((END - START))

    # Exit code 3 is expected for severe zone, check if it ran without crashing
    if [ $RESULT -eq 0 ] || [ $RESULT -eq 3 ]; then
        success "Context monitor handles 6MB file (took ${DURATION}s, exit code: $RESULT)"
        if [ $DURATION -gt 5 ]; then
            warn "Performance concern: took ${DURATION}s for 6MB file"
        fi
    else
        fail "Context monitor failed on large file (exit code: $RESULT)"
    fi

    cleanup_test_env
}

test_context_monitor_corrupted_file() {
    test_header "Context Monitor: Corrupted activity_stream.md (binary data)"
    setup_test_env

    mkdir -p .claude
    dd if=/dev/urandom of=.claude/activity_stream.md bs=1K count=100 2>/dev/null

    python3 /home/gyasis/Documents/code/dev-kid/cli/context_monitor.py --check 2>&1
    RESULT=$?

    if [ $RESULT -eq 0 ]; then
        success "Context monitor handles binary/corrupted file"
    else
        fail "Context monitor crashed on corrupted file (exit code: $RESULT)"
    fi

    cleanup_test_env
}

###########################################
# GITHUB SYNC FAILURE MODES
###########################################

test_github_sync_not_authenticated() {
    test_header "GitHub Sync: gh CLI not authenticated"
    setup_test_env

    # Create minimal tasks.md
    cat > tasks.md << 'EOF'
- [ ] TASK-001: Test task affecting `test.py`
EOF

    # Unset GitHub token temporarily
    OLD_TOKEN="${GITHUB_TOKEN:-}"
    unset GITHUB_TOKEN

    python3 /home/gyasis/Documents/code/dev-kid/cli/github_sync.py sync --dry-run 2>&1 | tee /tmp/gh_sync_output.txt
    RESULT=$?

    # Restore token
    if [ -n "$OLD_TOKEN" ]; then
        export GITHUB_TOKEN="$OLD_TOKEN"
    fi

    # Should handle gracefully, not crash
    if grep -q "Warning: Could not fetch GitHub issues" /tmp/gh_sync_output.txt; then
        success "GitHub sync handles unauthenticated gh CLI gracefully"
    else
        fail "GitHub sync did not handle unauthenticated gh CLI properly"
    fi

    cleanup_test_env
}

test_github_sync_missing_tasks_md() {
    test_header "GitHub Sync: Missing tasks.md"
    setup_test_env

    # Don't create tasks.md
    python3 /home/gyasis/Documents/code/dev-kid/cli/github_sync.py sync 2>&1 | tee /tmp/gh_sync_output.txt
    RESULT=$?

    if [ $RESULT -eq 1 ] && grep -q "tasks.md not found" /tmp/gh_sync_output.txt; then
        success "GitHub sync properly reports missing tasks.md"
    else
        fail "GitHub sync did not handle missing tasks.md correctly"
    fi

    cleanup_test_env
}

test_github_sync_malformed_tasks() {
    test_header "GitHub Sync: Malformed tasks.md"
    setup_test_env

    # Create malformed tasks.md
    cat > tasks.md << 'EOF'
This is not a valid task format
- [ ] Missing task ID
- [x] VALID-001: But this is valid
Random text
EOF

    python3 /home/gyasis/Documents/code/dev-kid/cli/github_sync.py sync --dry-run 2>&1 | tee /tmp/gh_sync_output.txt
    RESULT=$?

    # Should parse only valid tasks
    if grep -q "Found 1 tasks" /tmp/gh_sync_output.txt; then
        success "GitHub sync parses only valid tasks from malformed file"
    else
        fail "GitHub sync did not handle malformed tasks.md correctly"
    fi

    cleanup_test_env
}

###########################################
# MICRO-CHECKPOINT RACE CONDITIONS
###########################################

test_micro_checkpoint_no_changes() {
    test_header "Micro-Checkpoint: No uncommitted changes"
    setup_test_env

    # Create initial commit
    echo "test" > test.txt
    git add .
    git commit -m "Initial commit" -q

    python3 /home/gyasis/Documents/code/dev-kid/cli/micro_checkpoint.py 2>&1 | tee /tmp/micro_cp_output.txt
    RESULT=$?

    if [ $RESULT -eq 1 ] && grep -q "No changes to commit" /tmp/micro_cp_output.txt; then
        success "Micro-checkpoint handles no changes gracefully"
    else
        fail "Micro-checkpoint did not handle no changes correctly"
    fi

    cleanup_test_env
}

test_micro_checkpoint_rapid_succession() {
    test_header "Micro-Checkpoint: Rapid succession (race condition)"
    setup_test_env

    # Create initial commit
    echo "test" > test.txt
    git add .
    git commit -m "Initial commit" -q

    # Make changes
    echo "change1" >> test.txt
    python3 /home/gyasis/Documents/code/dev-kid/cli/micro_checkpoint.py "First change" &
    PID1=$!

    echo "change2" >> test.txt
    python3 /home/gyasis/Documents/code/dev-kid/cli/micro_checkpoint.py "Second change" &
    PID2=$!

    wait $PID1
    RESULT1=$?
    wait $PID2
    RESULT2=$?

    # Check git log
    COMMIT_COUNT=$(git log --oneline | wc -l)

    if [ $COMMIT_COUNT -ge 2 ]; then
        success "Rapid micro-checkpoints handled (${COMMIT_COUNT} commits created)"
    else
        fail "Race condition: only ${COMMIT_COUNT} commits created (expected 2+)"
    fi

    cleanup_test_env
}

test_micro_checkpoint_during_git_operation() {
    test_header "Micro-Checkpoint: During ongoing git operation"
    setup_test_env

    # Create initial commit
    echo "test" > test.txt
    git add .
    git commit -m "Initial commit" -q

    # Make changes
    echo "change1" >> test.txt

    # Start git add (slow operation)
    git add . &
    GIT_PID=$!

    # Immediately try micro-checkpoint
    python3 /home/gyasis/Documents/code/dev-kid/cli/micro_checkpoint.py "During git operation" 2>&1 | tee /tmp/micro_cp_output.txt
    RESULT=$?

    wait $GIT_PID

    if [ $RESULT -eq 0 ]; then
        success "Micro-checkpoint completed despite concurrent git operation"
    else
        warn "Micro-checkpoint may have conflicts with concurrent git operations"
    fi

    cleanup_test_env
}

test_micro_checkpoint_untracked_files() {
    test_header "Micro-Checkpoint: Large number of untracked files"
    setup_test_env

    # Create initial commit
    echo "test" > test.txt
    git add .
    git commit -m "Initial commit" -q

    # Create 1000 untracked files
    for i in {1..1000}; do
        echo "file$i" > "untracked_$i.txt"
    done

    START=$(date +%s)
    python3 /home/gyasis/Documents/code/dev-kid/cli/micro_checkpoint.py "Mass untracked files" 2>&1
    RESULT=$?
    END=$(date +%s)
    DURATION=$((END - START))

    if [ $RESULT -eq 0 ]; then
        success "Micro-checkpoint handles 1000 untracked files (took ${DURATION}s)"
        if [ $DURATION -gt 10 ]; then
            warn "Performance issue: took ${DURATION}s for 1000 files"
        fi
    else
        fail "Micro-checkpoint failed with large file count"
    fi

    cleanup_test_env
}

###########################################
# WAVE EXECUTOR INTERRUPTION
###########################################

test_wave_executor_ctrl_c_simulation() {
    test_header "Wave Executor: Ctrl+C interruption (SIGINT)"
    setup_test_env

    # Create minimal environment
    mkdir -p .claude memory-bank/private/$(whoami)
    cat > tasks.md << 'EOF'
- [ ] TASK-001: Test task affecting `test.py`
EOF

    cat > execution_plan.json << 'EOF'
{
  "execution_plan": {
    "phase_id": "Test",
    "waves": [
      {
        "wave_id": 1,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Test wave",
        "tasks": [
          {
            "task_id": "TASK-001",
            "instruction": "Test task affecting test.py",
            "agent_role": "test-agent"
          }
        ],
        "checkpoint_after": {
          "enabled": true
        }
      }
    ]
  }
}
EOF

    # Start wave executor in background
    timeout 2s python3 /home/gyasis/Documents/code/dev-kid/cli/wave_executor.py 2>&1 &
    EXECUTOR_PID=$!

    # Wait a moment, then send SIGINT
    sleep 1
    kill -INT $EXECUTOR_PID 2>/dev/null || true

    wait $EXECUTOR_PID 2>/dev/null
    RESULT=$?

    # Check for state files
    if [ -f "execution_plan.json" ]; then
        success "Wave executor preserves execution_plan.json on interruption"
    else
        fail "Wave executor lost execution_plan.json on interruption"
    fi

    cleanup_test_env
}

test_wave_executor_corrupted_json() {
    test_header "Wave Executor: Corrupted execution_plan.json"
    setup_test_env

    # Create corrupted JSON
    cat > execution_plan.json << 'EOF'
{
  "execution_plan": {
    "phase_id": "Test",
    "waves": [
      {
        "wave_id": 1,
        THIS IS INVALID JSON
EOF

    python3 /home/gyasis/Documents/code/dev-kid/cli/wave_executor.py 2>&1 | tee /tmp/wave_exec_output.txt
    RESULT=$?

    # Should handle gracefully and backup corrupted file
    if [ $RESULT -eq 1 ] && [ -f "execution_plan.json.corrupted" ]; then
        success "Wave executor backs up corrupted JSON and exits cleanly"
    else
        fail "Wave executor did not handle corrupted JSON properly"
    fi

    cleanup_test_env
}

test_wave_executor_missing_tasks_md() {
    test_header "Wave Executor: Missing tasks.md during verification"
    setup_test_env

    mkdir -p .claude memory-bank/private/$(whoami)

    cat > execution_plan.json << 'EOF'
{
  "execution_plan": {
    "phase_id": "Test",
    "waves": [
      {
        "wave_id": 1,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Test wave",
        "tasks": [
          {
            "task_id": "TASK-001",
            "instruction": "Test task",
            "agent_role": "test-agent"
          }
        ],
        "checkpoint_after": {
          "enabled": true
        }
      }
    ]
  }
}
EOF

    # Don't create tasks.md
    python3 /home/gyasis/Documents/code/dev-kid/cli/wave_executor.py 2>&1 | tee /tmp/wave_exec_output.txt
    RESULT=$?

    if [ $RESULT -ne 0 ]; then
        success "Wave executor fails safely when tasks.md missing"
    else
        warn "Wave executor may not properly validate missing tasks.md"
    fi

    cleanup_test_env
}

test_wave_executor_incomplete_tasks() {
    test_header "Wave Executor: Incomplete tasks at checkpoint"
    setup_test_env

    mkdir -p .claude memory-bank/private/$(whoami)

    cat > tasks.md << 'EOF'
- [ ] TASK-001: Test task affecting `test.py`
EOF

    cat > execution_plan.json << 'EOF'
{
  "execution_plan": {
    "phase_id": "Test",
    "waves": [
      {
        "wave_id": 1,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Test wave",
        "tasks": [
          {
            "task_id": "TASK-001",
            "instruction": "Test task affecting test.py",
            "agent_role": "test-agent"
          }
        ],
        "checkpoint_after": {
          "enabled": true
        }
      }
    ]
  }
}
EOF

    # Mark task as started in watchdog
    mkdir -p .claude
    cat > .claude/task_timers.json << 'EOF'
{
  "running_tasks": {
    "TASK-001": {
      "description": "Test task",
      "started_at": "2024-01-01T00:00:00",
      "status": "running"
    }
  }
}
EOF

    python3 /home/gyasis/Documents/code/dev-kid/cli/wave_executor.py 2>&1 | tee /tmp/wave_exec_output.txt
    RESULT=$?

    if [ $RESULT -eq 1 ] && grep -q "Checkpoint failed" /tmp/wave_exec_output.txt; then
        success "Wave executor halts on incomplete tasks (fail-safe works)"
    else
        fail "Wave executor did not properly validate task completion"
    fi

    cleanup_test_env
}

###########################################
# REPORT GENERATION
###########################################

generate_report() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}TEST SUMMARY${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "Total Tests: $TESTS_TOTAL"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo -e ""

    if [ $TESTS_FAILED -gt 0 ]; then
        echo -e "${RED}FAILED TESTS:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "  ${RED}✗${NC} $test"
        done
        echo -e ""
    fi

    if [ $TESTS_PASSED -gt 0 ]; then
        echo -e "${GREEN}PASSED TESTS:${NC}"
        for test in "${PASSED_TESTS[@]}"; do
            echo -e "  ${GREEN}✓${NC} $test"
        done
        echo -e ""
    fi

    echo -e "Full log: $LOG_FILE"

    # Exit code
    if [ $TESTS_FAILED -gt 0 ]; then
        exit 1
    else
        exit 0
    fi
}

###########################################
# RUN ALL TESTS
###########################################

main() {
    echo -e "${BLUE}Starting Ralph Optimization Edge Case Tests${NC}"
    echo -e "${BLUE}=============================================${NC}\n"

    # Context Monitor Tests
    test_context_monitor_missing_claude_dir
    test_context_monitor_empty_activity_stream
    test_context_monitor_large_file
    test_context_monitor_corrupted_file

    # GitHub Sync Tests
    test_github_sync_not_authenticated
    test_github_sync_missing_tasks_md
    test_github_sync_malformed_tasks

    # Micro-Checkpoint Tests
    test_micro_checkpoint_no_changes
    test_micro_checkpoint_rapid_succession
    test_micro_checkpoint_during_git_operation
    test_micro_checkpoint_untracked_files

    # Wave Executor Tests
    test_wave_executor_ctrl_c_simulation
    test_wave_executor_corrupted_json
    test_wave_executor_missing_tasks_md
    test_wave_executor_incomplete_tasks

    # Generate final report
    generate_report
}

main

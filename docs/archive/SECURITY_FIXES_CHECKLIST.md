# Security Fixes Implementation Checklist

**Source**: State Security Audit 2026-02-14
**Status**: 🔴 NOT STARTED
**Progress**: 0 / 23 issues fixed

---

## Priority 1: Critical Data Loss Prevention (2 days)

### 1. File Locking for tasks.md
**Issue**: Concurrent writes cause corruption
**CVSS**: 8.1 (CRITICAL)
**Files**: `cli/safe_file_ops.py` (new), `cli/wave_executor.py`, `cli/github_sync.py`

- [ ] Create `cli/safe_file_ops.py` with `locked_file()` context manager
- [ ] Update `wave_executor.py::verify_wave_completion()` to use locking
- [ ] Update `github_sync.py::parse_tasks_md()` to use locking
- [ ] Add timeout handling (30s default)
- [ ] Test: 10 parallel writes to tasks.md → no corruption

**Code Template**:
```python
# cli/safe_file_ops.py
import fcntl
import contextlib

@contextlib.contextmanager
def locked_file(path, mode='r', timeout=30):
    # Implementation from audit report
    pass
```

**Validation**:
```bash
# Test concurrent access
python3 -c "
import multiprocessing
from cli.safe_file_ops import locked_file
from pathlib import Path

def writer(n):
    with locked_file(Path('tasks.md'), 'a') as f:
        f.write(f'test {n}\n')

processes = [multiprocessing.Process(target=writer, args=(i,)) for i in range(10)]
for p in processes: p.start()
for p in processes: p.join()
"
# Verify: tasks.md has exactly 10 lines, no corruption
```

---

### 2. JSON Schema Validation for execution_plan.json
**Issue**: Corrupted JSON halts system, no recovery
**CVSS**: 7.8 (CRITICAL)
**Files**: `cli/wave_executor.py`

- [ ] Add `jsonschema` dependency (standard library alternative: manual validation)
- [ ] Define `EXECUTION_PLAN_SCHEMA` in wave_executor.py
- [ ] Update `load_plan()` to validate before accepting
- [ ] Implement backup recovery (try `.json.backup` before failing)
- [ ] Create backup on every successful orchestration
- [ ] Test: Truncated JSON → recovers from backup

**Code Template**:
```python
EXECUTION_PLAN_SCHEMA = {
    "type": "object",
    "required": ["execution_plan"],
    "properties": {
        "execution_plan": {
            "type": "object",
            "required": ["phase_id", "waves"],
            # ... from audit report
        }
    }
}

def load_plan(self):
    # Try primary
    try:
        plan = json.loads(self.plan_file.read_text())
        self._validate_plan(plan)  # Raises on invalid
        self.plan = plan
    except Exception as e:
        # Try backup
        backup = self.plan_file.with_suffix('.json.backup')
        if backup.exists():
            plan = json.loads(backup.read_text())
            self._validate_plan(plan)
            self.plan = plan
            backup.rename(self.plan_file)  # Restore
        else:
            raise
```

**Validation**:
```bash
# Test corrupted JSON recovery
echo '{"corrupted": true' > execution_plan.json
python3 cli/wave_executor.py
# Should recover from .backup if exists, or fail gracefully
```

---

### 3. Atomic Git Commits
**Issue**: Staging succeeds but commit fails → partial state
**CVSS**: 6.5 (HIGH)
**Files**: `cli/wave_executor.py::_git_checkpoint()`, `cli/micro_checkpoint.py`

- [ ] Add pre-commit verification (check for staged changes)
- [ ] Change `check=False` to `check=True` in git commit
- [ ] Add rollback on commit failure (`git reset HEAD`)
- [ ] Verify commit hash after success
- [ ] Log all git operations to `.claude/git_operations.log`
- [ ] Test: Simulate commit failure (full disk) → clean rollback

**Code Template**:
```python
def _git_checkpoint(self, wave_id: int) -> None:
    try:
        # Check if changes exist
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'])
        if result.returncode == 0:
            subprocess.run(['git', 'add', '.'], check=True)

        # Verify changes to commit
        result = subprocess.run(['git', 'diff', '--cached', '--quiet'])
        if result.returncode == 0:
            return  # Nothing to commit

        # Attempt commit
        result = subprocess.run(
            ['git', 'commit', '-m', f"[CHECKPOINT] Wave {wave_id}"],
            capture_output=True, text=True
        )

        if result.returncode != 0:
            # ROLLBACK
            subprocess.run(['git', 'reset', 'HEAD'], check=False)
            raise Exception(f"Git commit failed: {result.stderr}")

        # Verify commit created
        commit_hash = subprocess.run(
            ['git', 'rev-parse', 'HEAD'],
            capture_output=True, text=True, check=True
        ).stdout.strip()

        print(f"   ✅ Checkpoint: {commit_hash[:7]}")

    except Exception as e:
        print(f"❌ Checkpoint failed: {e}")
        subprocess.run(['git', 'reset', 'HEAD'], check=False)
        raise
```

**Validation**:
```bash
# Test rollback on failure
git config --local commit.gpgsign true  # Force failure if no GPG
echo "test" >> test.txt
python3 -c "
from cli.wave_executor import WaveExecutor
executor = WaveExecutor()
try:
    executor._git_checkpoint(1)
except:
    pass
"
git status  # Should show: nothing staged (rollback successful)
git config --local --unset commit.gpgsign
```

---

### 4. activity_stream.md Rotation
**Issue**: Unbounded growth exhausts context window
**CVSS**: 6.2 (HIGH)
**Files**: `skills/sync_memory.sh`

- [ ] Add size check before appending (100KB threshold)
- [ ] Implement rotation (archive to `activity_stream_archive_TIMESTAMP.md`)
- [ ] Keep last 5 archives only
- [ ] Create new stream with summary header
- [ ] Test: Write 200KB → auto-rotation occurs

**Code Template**:
```bash
# Add to sync_memory.sh BEFORE appending

ACTIVITY_STREAM=".claude/activity_stream.md"
MAX_SIZE=102400  # 100KB

if [ -f "$ACTIVITY_STREAM" ]; then
    SIZE=$(stat -c%s "$ACTIVITY_STREAM" 2>/dev/null || stat -f%z "$ACTIVITY_STREAM")

    if [ "$SIZE" -gt "$MAX_SIZE" ]; then
        echo "   ℹ️  Rotating activity stream (${SIZE} bytes > 100KB)"

        TIMESTAMP=$(date +%Y-%m-%d_%H-%M-%S)
        mv "$ACTIVITY_STREAM" ".claude/activity_stream_archive_${TIMESTAMP}.md"

        # Create new stream
        cat > "$ACTIVITY_STREAM" << EOF
# Activity Stream

**Rotated from**: activity_stream_archive_${TIMESTAMP}.md
**Rotation Date**: $(date)

---

EOF

        # Cleanup old archives (keep 5)
        ls -1t .claude/activity_stream_archive_*.md | tail -n +6 | xargs rm -f 2>/dev/null || true
    fi
fi
```

**Validation**:
```bash
# Test rotation
for i in {1..1000}; do
    echo "### $(date) - Test entry $i with some content to increase size" >> .claude/activity_stream.md
done

./skills/sync_memory.sh

# Verify:
# - activity_stream.md is small (<5KB)
# - Archive created in .claude/
# - Only 5 archives exist
```

---

## Priority 2: State Consistency (3 days)

### 5. Wave Executor State Persistence
**Issue**: Crash during wave 3 → restart from wave 1
**CVSS**: 6.3 (HIGH)
**Files**: `cli/wave_executor.py`

- [ ] Create `.claude/wave_executor_state.json` schema
- [ ] Add `save_progress()` method (atomic write)
- [ ] Add `load_progress()` method
- [ ] Update `execute()` to save before/after each wave
- [ ] Skip completed waves on resume
- [ ] Cleanup state file on successful completion
- [ ] Test: Kill -9 during wave 3 → resume from wave 3

**State File Schema**:
```json
{
    "current_wave": 3,
    "completed_waves": [1, 2],
    "timestamp": "2026-02-14T10:30:00Z",
    "phase_id": "implementation"
}
```

---

### 6. Task Watchdog Process Locking
**Issue**: Multiple watchdog instances corrupt state
**CVSS**: 6.8 (HIGH)
**Files**: `cli/task_watchdog.py`

- [ ] Add `.claude/task_watchdog.lock` file
- [ ] Implement `acquire_lock()` with fcntl
- [ ] Implement `release_lock()` on shutdown
- [ ] Check lock on startup (fail if already running)
- [ ] Add PID to lock file for debugging
- [ ] Test: Start 2 watchdogs → second fails with clear error

**Lock Implementation**:
```python
def acquire_lock(self) -> bool:
    import fcntl
    import os

    try:
        self.lock_fd = open(self.lock_file, 'w')
        fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.lock_fd.write(str(os.getpid()))
        self.lock_fd.flush()
        return True
    except IOError:
        return False
```

---

### 7. Checkpoint Coordination
**Issue**: Micro-checkpoint during wave creates conflicts
**CVSS**: 6.5 (HIGH)
**Files**: `cli/micro_checkpoint.py`, `cli/wave_executor.py`

- [ ] Create `cli/checkpoint_coordinator.py`
- [ ] Add `.claude/checkpoint.lock` file
- [ ] Update micro_checkpoint to acquire lock
- [ ] Update wave_executor to acquire lock
- [ ] Implement timeout and retry logic
- [ ] Test: Micro during wave → micro waits for wave to finish

---

### 8. Bidirectional GitHub Sync
**Issue**: Manual issue closures don't update tasks.md
**CVSS**: 6.1 (MEDIUM)
**Files**: `cli/github_sync.py`

- [ ] Add `sync_issues_to_tasks()` function
- [ ] Query GitHub issue states with `gh issue view`
- [ ] Update tasks.md for closed issues
- [ ] Handle state mismatches (task complete, issue open)
- [ ] Add `--direction` flag (to-github, from-github, both)
- [ ] Test: Close issue on GitHub → run sync → tasks.md updated

---

## Priority 3: Best Practices (1.5 days)

### 9. Constitution Validation Caching
**Issue**: Re-validates all files every checkpoint
**CVSS**: 5.4 (MEDIUM)
**Files**: `cli/wave_executor.py`

- [ ] Create `.claude/constitution_validation_cache.json`
- [ ] Add `_get_file_hash()` method (SHA256)
- [ ] Cache validation results by file hash
- [ ] Skip validation if hash unchanged
- [ ] Clear cache when constitution changes
- [ ] Test: Validate 10 files, change 1, re-run → only 1 validated

---

### 10. Session Snapshot Rotation
**Issue**: Unlimited snapshots → disk exhaustion
**CVSS**: 5.1 (MEDIUM)
**Files**: `skills/finalize_session.sh`

- [ ] Count existing snapshots before creating new
- [ ] Delete oldest if count > 20
- [ ] Add rotation log message
- [ ] Test: Create 30 snapshots → only 20 remain

---

### 11. Git Hook Verification
**Issue**: Hooks may fail silently
**CVSS**: 4.6 (MEDIUM)
**Files**: `scripts/init.sh`

- [ ] Add test commit after hook installation
- [ ] Verify activity_stream.md updated
- [ ] Remove test commit
- [ ] Warn if hook verification fails
- [ ] Test: Fresh init → hook verified message appears

---

### 12. Constitution Quality Enforcement
**Issue**: Corrupted constitution silently ignored
**CVSS**: 5.3 (MEDIUM)
**Files**: `cli/wave_executor.py`

- [ ] Add quality score check on load
- [ ] Require score > 50 or fail
- [ ] Show recommendations if score < 80
- [ ] Require explicit bypass for degraded mode
- [ ] Test: Corrupt constitution → clear error + recommendations

---

## Testing Matrix

| Test Scenario | Before Fix | After Fix | Validation Command |
|--------------|-----------|-----------|-------------------|
| 10 concurrent tasks.md writes | Corruption | Serialized | `test-concurrent-writes.sh` |
| Kill -9 during wave 3 | Restart wave 1 | Resume wave 3 | `test-crash-recovery.sh` |
| Truncated execution_plan.json | System halt | Backup recovery | `test-json-corruption.sh` |
| Disk full during commit | Partial state | Clean rollback | `test-commit-failure.sh` |
| 200KB activity stream | Context exhaustion | Auto-rotation | `test-stream-rotation.sh` |
| 2 watchdog instances | State corruption | Second fails | `test-watchdog-lock.sh` |
| Micro during wave checkpoint | Conflict/empty commit | Serialized | `test-checkpoint-coordination.sh` |
| Manual GitHub issue close | tasks.md stale | Auto-update | `test-github-sync.sh` |

---

## Automated Test Suite

Create `security-tests/run_all.sh`:

```bash
#!/usr/bin/env bash
set -e

echo "🧪 Running Security Test Suite"
echo ""

PASS=0
FAIL=0

run_test() {
    local test_name="$1"
    local test_script="$2"

    echo "Running: $test_name"
    if bash "$test_script"; then
        echo "   ✅ PASS"
        ((PASS++))
    else
        echo "   ❌ FAIL"
        ((FAIL++))
    fi
    echo ""
}

run_test "Concurrent Write Protection" "security-tests/test-concurrent-writes.sh"
run_test "Crash Recovery" "security-tests/test-crash-recovery.sh"
run_test "JSON Corruption Recovery" "security-tests/test-json-corruption.sh"
run_test "Git Commit Atomicity" "security-tests/test-commit-failure.sh"
run_test "Stream Rotation" "security-tests/test-stream-rotation.sh"
run_test "Watchdog Process Locking" "security-tests/test-watchdog-lock.sh"
run_test "Checkpoint Coordination" "security-tests/test-checkpoint-coordination.sh"
run_test "GitHub Bidirectional Sync" "security-tests/test-github-sync.sh"

echo "════════════════════════════════"
echo "Results: $PASS passed, $FAIL failed"
echo "════════════════════════════════"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
```

---

## Progress Tracking

Update this section as fixes are implemented:

### Completed Fixes

- [ ] 1. File Locking (tasks.md)
- [ ] 2. JSON Schema Validation (execution_plan.json)
- [ ] 3. Atomic Git Commits
- [ ] 4. Activity Stream Rotation
- [ ] 5. Wave Executor State Persistence
- [ ] 6. Task Watchdog Process Locking
- [ ] 7. Checkpoint Coordination
- [ ] 8. Bidirectional GitHub Sync
- [ ] 9. Constitution Validation Caching
- [ ] 10. Session Snapshot Rotation
- [ ] 11. Git Hook Verification
- [ ] 12. Constitution Quality Enforcement

### Test Results

- [ ] All Priority 1 tests passing
- [ ] All Priority 2 tests passing
- [ ] All Priority 3 tests passing
- [ ] Load test: 100 waves, 500 tasks
- [ ] Chaos test: Random failures during execution
- [ ] Production dry-run: Real project, 7 days

---

## Sign-Off

### Developer Sign-Off

- [ ] All code implemented and reviewed
- [ ] All tests passing locally
- [ ] Code committed to feature branch
- [ ] PR created with test results

**Developer**: _________________ **Date**: _______

### QA Sign-Off

- [ ] All test scenarios executed
- [ ] Edge cases verified
- [ ] Performance acceptable
- [ ] Documentation updated

**QA**: _________________ **Date**: _______

### Security Sign-Off

- [ ] All critical vulnerabilities fixed
- [ ] Re-audit completed
- [ ] No new vulnerabilities introduced
- [ ] Ready for production

**Security**: _________________ **Date**: _______

---

## Rollback Plan

If issues discovered after deployment:

1. **Immediate Rollback**:
   ```bash
   git checkout main
   git revert <security-fixes-commit>
   ./scripts/install.sh
   ```

2. **Preserve State**:
   ```bash
   # Backup current state before rollback
   cp -r .claude .claude.backup.$(date +%s)
   cp tasks.md tasks.md.backup.$(date +%s)
   ```

3. **Restore Service**:
   ```bash
   # If system broken after fix
   git reset --hard <last-known-good-commit>
   ./scripts/install.sh
   dev-kid recall  # Restore from snapshot
   ```

---

## Maintenance Schedule

### Daily
- [ ] Check `.claude/state_health.json` metrics
- [ ] Review git operation logs
- [ ] Verify no `.corrupted` files created

### Weekly
- [ ] Run full test suite
- [ ] Review activity stream rotation logs
- [ ] Check disk usage (`.claude/` directory)

### Monthly
- [ ] Review accumulated archives
- [ ] Clean up old session snapshots
- [ ] Re-run security audit

---

**Checklist Version**: 1.0
**Last Updated**: 2026-02-14
**Next Review**: After all Priority 1 fixes implemented

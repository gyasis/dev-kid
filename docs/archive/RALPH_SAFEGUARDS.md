# Ralph Optimization Safeguards

Code patches to fix critical issues identified in edge case testing.

---

## CRITICAL FIX 1: task-watchdog Command Missing

### Problem
`wave_executor.py` calls `task-watchdog` binary which doesn't exist in PATH.

### Solution: Add startup validation

**File**: `cli/wave_executor.py`

**Add after imports** (around line 13):

```python
import shutil

def validate_dependencies():
    """Ensure task-watchdog command is available"""
    # Check if task-watchdog exists (either as standalone or via dev-kid)
    if not shutil.which("task-watchdog"):
        if not shutil.which("dev-kid"):
            print("❌ Error: task-watchdog command not found")
            print("")
            print("   This component is required for wave execution.")
            print("   Please install dev-kid:")
            print("   ./scripts/install.sh")
            print("")
            print("   Or create symlink manually:")
            print("   sudo ln -s /usr/local/bin/dev-kid /usr/local/bin/task-watchdog")
            sys.exit(1)
```

**Modify WaveExecutor.__init__()** (around line 19):

```python
def __init__(self, plan_file: str = "execution_plan.json"):
    # Validate dependencies first
    validate_dependencies()

    self.plan_file = Path(plan_file)
    self.plan = None
    self.tasks_file = Path("tasks.md")
    # ... rest of __init__ ...
```

### Alternative: Use dev-kid CLI instead

**File**: `cli/wave_executor.py`

**Modify execute_task()** (around line 174):

```python
def execute_task(self, task: Dict) -> None:
    """Execute a single task and register it with the watchdog"""
    task_id = task["task_id"]
    command = task["instruction"]
    constitution_rules = task.get("constitution_rules", [])

    # Use dev-kid CLI instead of task-watchdog binary
    cmd_parts = ["dev-kid", "watchdog-register", task_id, "--command", command]

    # Add constitution rules if present
    if constitution_rules:
        rules_arg = ",".join(constitution_rules)
        cmd_parts.extend(["--rules", rules_arg])

    # Execute registration
    result = subprocess.run(cmd_parts, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"      ❌ Failed to register task {task_id}: {result.stderr.strip()}")
    else:
        if constitution_rules:
            print(f"      ✅ Task {task_id} registered with {len(constitution_rules)} constitution rule(s)")
        else:
            print(f"      ✅ Task {task_id} registered (no constitution rules)")
```

**Also update install.sh** to create symlink:

```bash
# Create task-watchdog symlink
if [ -w /usr/local/bin ]; then
    ln -sf "$INSTALL_DIR/cli/dev-kid" /usr/local/bin/task-watchdog
    echo "   ✅ task-watchdog symlink created"
else
    echo "   ⚠️  Cannot create task-watchdog symlink (requires sudo)"
    echo "   Run: sudo ln -s $INSTALL_DIR/cli/dev-kid /usr/local/bin/task-watchdog"
fi
```

---

## CRITICAL FIX 2: Missing tasks.md Error Handling

### Problem
`verify_wave_completion()` crashes if tasks.md deleted during execution.

### Solution: Add try/except with clear error

**File**: `cli/wave_executor.py`

**Modify verify_wave_completion()** (around line 57):

```python
def verify_wave_completion(self, wave_id: int, tasks: List[Dict]) -> bool:
    """Verify all tasks in wave are marked complete in tasks.md"""

    # Check if tasks.md exists first
    if not self.tasks_file.exists():
        print(f"❌ Error: tasks.md not found at {self.tasks_file}")
        print("   ")
        print("   Possible causes:")
        print("   - File deleted during wave execution")
        print("   - Symlink broken (if using Speckit integration)")
        print("   - Working directory changed")
        print("   ")
        print("   Recovery:")
        print("   1. Check if tasks.md exists in project root")
        print("   2. If using Speckit, verify .specify/specs/<branch>/tasks.md exists")
        print("   3. Re-create tasks.md or restore from git")
        return False

    try:
        content = self.tasks_file.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        print(f"❌ Error: tasks.md contains invalid UTF-8")
        print("   File may be corrupted. Restore from git:")
        print(f"   git checkout HEAD -- {self.tasks_file}")
        return False
    except Exception as e:
        print(f"❌ Error reading tasks.md: {e}")
        return False

    # ... rest of verification logic ...
```

---

## CRITICAL FIX 3: Micro-Checkpoint Race Condition

### Problem
Concurrent micro-checkpoints can conflict when both run `git add .`.

### Solution: Add file-based locking

**File**: `cli/micro_checkpoint.py`

**Add imports** (around line 9):

```python
import fcntl
import time
```

**Replace create_micro_checkpoint()** (around line 37):

```python
def create_micro_checkpoint(message: str = None, auto: bool = False) -> bool:
    """
    Create a micro-checkpoint (frequent git commit).

    Args:
        message: Optional commit message
        auto: If True, auto-generate message from changed files

    Returns:
        True if checkpoint created, False if no changes or lock timeout
    """

    # Acquire lock to prevent concurrent checkpoints
    lock_file = Path(".git/dev-kid-checkpoint.lock")
    lock_fd = None

    for attempt in range(5):
        try:
            lock_fd = open(lock_file, 'w')
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            break  # Lock acquired
        except (BlockingIOError, IOError):
            if attempt == 4:
                print("   ⏳ Another checkpoint in progress (timeout after 5s)")
                print("      Changes will be captured in next checkpoint")
                return False
            time.sleep(1)

    try:
        if not has_uncommitted_changes():
            print("   ℹ️  No changes to commit")
            return False

        # Get changed files for auto message
        changed_files = get_changed_files()

        # Generate message if auto
        if auto and not message:
            if len(changed_files) == 1:
                message = f"Update {changed_files[0]}"
            elif len(changed_files) <= 3:
                message = f"Update {', '.join(changed_files)}"
            else:
                message = f"Update {len(changed_files)} files"

        if not message:
            message = f"Micro-checkpoint {datetime.now().strftime('%H:%M:%S')}"

        # Stage all changes
        subprocess.run(['git', 'add', '.'], check=True)

        # Create commit
        commit_msg = f"""[MICRO-CHECKPOINT] {message}

{datetime.now().isoformat()}
Generated by: dev-kid micro-checkpoint
Files: {', '.join(changed_files[:5])}{'...' if len(changed_files) > 5 else ''}

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"""

        subprocess.run(
            ['git', 'commit', '-m', commit_msg],
            check=True,
            capture_output=True
        )

        # Get commit hash
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            check=True
        )
        commit_hash = result.stdout.strip()

        print(f"   ✅ Micro-checkpoint: {commit_hash}")
        print(f"      {message}")

        return True

    finally:
        # Release lock
        if lock_fd:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
            lock_fd.close()
            lock_file.unlink(missing_ok=True)
```

**Alternative: Timestamp-based deduplication** (lighter weight):

```python
def should_skip_recent_checkpoint() -> bool:
    """Skip if commit created within last 5 seconds (prevents duplicates)"""
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%ct'],
            capture_output=True,
            text=True,
            check=True
        )
        last_commit_time = int(result.stdout.strip())
        elapsed = time.time() - last_commit_time

        if elapsed < 5:
            print(f"   ⏭️  Skipping (commit created {elapsed:.1f}s ago)")
            return True
    except:
        pass

    return False

def create_micro_checkpoint(message: str = None, auto: bool = False) -> bool:
    # Check for recent checkpoint
    if should_skip_recent_checkpoint():
        return False

    # ... rest of function ...
```

---

## IMPROVEMENT 1: Malformed Task Warnings

### Problem
Malformed tasks silently ignored, confusing users.

### Solution: Add warning count

**File**: `cli/github_sync.py`

**Replace parse_tasks_md()** (around line 25):

```python
def parse_tasks_md(tasks_file: Path = Path("tasks.md")) -> List[Task]:
    """Parse tasks.md into Task objects"""
    if not tasks_file.exists():
        print(f"❌ tasks.md not found at {tasks_file}")
        sys.exit(1)

    tasks = []
    malformed_lines = []
    content = tasks_file.read_text()

    # Match: - [ ] TASK-001: Description affecting `file.py`
    pattern = r'^- \[([ x])\] ([A-Z]+-\d+): (.+)$'

    for line_num, line in enumerate(content.split('\n'), start=1):
        # Skip empty lines and headers
        if not line.strip() or line.startswith('#'):
            continue

        # Check if line looks like a task
        if line.strip().startswith('- ['):
            match = re.match(pattern, line)
            if match:
                completed = match.group(1) == 'x'
                task_id = match.group(2)
                description = match.group(3)

                # Extract file paths (backtick-enclosed)
                file_paths = re.findall(r'`([^`]+)`', description)

                # Extract dependencies (after T123, depends on T456)
                deps = re.findall(r'(?:after|depends on) ([A-Z]+-\d+)', description)

                tasks.append(Task(
                    id=task_id,
                    description=description,
                    completed=completed,
                    file_paths=file_paths,
                    dependencies=deps
                ))
            else:
                # Line looks like task but doesn't match format
                malformed_lines.append((line_num, line))

    # Warn about malformed tasks
    if malformed_lines:
        print(f"⚠️  Warning: {len(malformed_lines)} malformed task line(s) ignored")
        print(f"   Expected format: - [ ] TASK-ID: Description")
        for line_num, line in malformed_lines[:3]:  # Show first 3
            print(f"   Line {line_num}: {line[:70]}")
        if len(malformed_lines) > 3:
            print(f"   ... and {len(malformed_lines) - 3} more")
        print()

    return tasks
```

---

## IMPROVEMENT 2: Context Monitor Exit Codes

### Problem
Exit codes confusing (only work with --check flag).

### Solution: Document behavior in help

**File**: `cli/context_monitor.py`

**Replace main()** (around line 100):

```python
def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Monitor context budget for Ralph smart zone optimization",
        epilog="""
Exit Codes:
  Without --check:
    Always exits 0 (display-only mode)

  With --check:
    0 - Optimal zone (<60K tokens, <30%)
    1 - Warning zone (60K-80K tokens, 30-40%)
    2 - Critical zone (80K-100K tokens, 40-50%)
    3 - Severe zone (>100K tokens, >50%)

  With --check --warn-only:
    0 - Smart zone (optimal or warning)
    2 - Dumb zone (critical)
    3 - Severe dumb zone

Usage Examples:
  # Display status (human-readable)
  dev-kid context-check

  # Check status in script
  if ! dev-kid context-check --check --warn-only; then
      echo "Context budget critical - finalize session"
      dev-kid finalize
  fi

Ralph Smart Zone Strategy:
  - Stay below 60K tokens (30% of 200K window)
  - Use micro-checkpoints to compress context
  - Finalize session when approaching 100K tokens
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--check', action='store_true',
                       help='Check context budget and exit with status code')
    parser.add_argument('--warn-only', action='store_true',
                       help='Only exit with error if in dumb zone (use with --check)')

    args = parser.parse_args()

    result = check_context_budget(verbose=True)

    # Exit codes (only if --check provided)
    if args.check:
        level = result['level']
        if level == 'optimal':
            sys.exit(0)
        elif level == 'warning':
            sys.exit(0 if args.warn_only else 1)
        elif level == 'critical':
            sys.exit(2)
        else:  # severe
            sys.exit(3)

    sys.exit(0)
```

---

## IMPROVEMENT 3: Better Error Messages

### Context Monitor: Add actionable recommendations

**File**: `cli/context_monitor.py`

**Modify get_zone_info()** (around line 37):

```python
def get_zone_info(tokens: int) -> dict:
    """Get zone classification for token count"""
    if tokens < OPTIMAL_TOKENS:
        return {
            'zone': 'smart',
            'level': 'optimal',
            'percentage': int((tokens / 200000) * 100),
            'status': '✅',
            'message': 'Optimal - stay in smart zone',
            'action': 'Continue normally',
            'details': 'Context budget healthy. Normal development workflow.'
        }
    elif tokens < WARNING_TOKENS:
        return {
            'zone': 'smart',
            'level': 'warning',
            'percentage': int((tokens / 200000) * 100),
            'status': '⚠️',
            'message': 'Approaching dumb zone threshold',
            'action': 'Consider micro-checkpoint soon',
            'details': 'Run: dev-kid micro-checkpoint --auto'
        }
    elif tokens < CRITICAL_TOKENS:
        return {
            'zone': 'dumb',
            'level': 'critical',
            'percentage': int((tokens / 200000) * 100),
            'status': '🚨',
            'message': 'In dumb zone - quality degraded',
            'action': 'FINALIZE NOW: dev-kid finalize && dev-kid recall',
            'details': 'Context compression has degraded Claude performance. Session reset recommended.'
        }
    else:
        return {
            'zone': 'dumb',
            'level': 'severe',
            'percentage': int((tokens / 200000) * 100),
            'status': '❌',
            'message': 'Deep in dumb zone - severe degradation',
            'action': 'STOP WORK - dev-kid finalize IMMEDIATELY',
            'details': 'CRITICAL: Further work will produce low-quality output. Finalize session NOW.'
        }
```

**Update display** (around line 82):

```python
if verbose:
    print(f"📊 Context Budget Status")
    print(f"")
    print(f"   Estimated tokens: {tokens:,} / 200,000 ({zone_info['percentage']}%)")
    print(f"   Zone: {zone_info['status']} {zone_info['zone'].upper()} ZONE - {zone_info['level']}")
    print(f"   Message: {zone_info['message']}")
    print(f"")
    print(f"   Thresholds:")
    print(f"   - Optimal: <{OPTIMAL_TOKENS:,} tokens (30%)")
    print(f"   - Warning: <{WARNING_TOKENS:,} tokens (40%)")
    print(f"   - Critical: <{CRITICAL_TOKENS:,} tokens (50%)")
    print(f"")
    print(f"   Recommended action: {zone_info['action']}")

    # Add detailed recommendation for warning/critical zones
    if zone_info['level'] in ['warning', 'critical', 'severe']:
        print(f"   Details: {zone_info['details']}")
```

---

## TEST SCRIPT FIX: PIPESTATUS Bug

### Problem
Test script doesn't capture correct exit codes when using pipes.

### Solution: Add set -o pipefail

**File**: `test-ralph-edge-cases.sh`

**Add after shebang** (line 5):

```bash
#!/bin/bash
# Edge Case Testing for Ralph Optimization Implementation
# Tests failure modes and data loss scenarios

# Don't exit on error - we're testing error conditions
set +e

# Make pipes return exit code of first failing command
set -o pipefail
```

**Also fix individual tests**:

```bash
test_github_sync_missing_tasks_md() {
    test_header "GitHub Sync: Missing tasks.md"
    setup_test_env

    # Don't create tasks.md
    python3 /home/gyasis/Documents/code/dev-kid/cli/github_sync.py sync 2>&1 | tee /tmp/gh_sync_output.txt
    # With pipefail, $? now correctly captures python3 exit code
    RESULT=$?

    if [ $RESULT -eq 1 ] && grep -q "tasks.md not found" /tmp/gh_sync_output.txt; then
        success "GitHub sync properly reports missing tasks.md"
    else
        fail "GitHub sync did not handle missing tasks.md correctly (exit: $RESULT)"
    fi

    cleanup_test_env
}
```

---

## Installation Script Updates

### Add task-watchdog symlink

**File**: `scripts/install.sh`

**Add after dev-kid symlink creation** (around line 80):

```bash
# Create task-watchdog symlink (required for wave executor)
echo "Creating task-watchdog symlink..."
if [ -w /usr/local/bin ]; then
    ln -sf "$INSTALL_DIR/cli/dev-kid" /usr/local/bin/task-watchdog
    echo "   ✅ task-watchdog symlink created"
else
    echo "   ⚠️  Cannot create task-watchdog symlink (requires sudo)"
    echo "   Manual step required:"
    echo "   sudo ln -s $INSTALL_DIR/cli/dev-kid /usr/local/bin/task-watchdog"
    echo ""
    echo "   Alternatively, add to PATH:"
    echo "   export PATH=\"$INSTALL_DIR/cli:\$PATH\""
fi
```

### Add post-install validation

**File**: `scripts/install.sh`

**Add at end of script**:

```bash
# Validate installation
echo ""
echo "🔍 Validating installation..."

# Check dev-kid command
if command -v dev-kid >/dev/null 2>&1; then
    echo "   ✅ dev-kid command found"
else
    echo "   ❌ dev-kid command not found in PATH"
    INSTALL_FAILED=1
fi

# Check task-watchdog command
if command -v task-watchdog >/dev/null 2>&1; then
    echo "   ✅ task-watchdog command found"
else
    echo "   ⚠️  task-watchdog command not found (wave executor will fail)"
    echo "      Run: sudo ln -s $INSTALL_DIR/cli/dev-kid /usr/local/bin/task-watchdog"
fi

# Check skills
if [ -d "$HOME/.claude/skills/planning-enhanced" ]; then
    SKILL_COUNT=$(ls -1 "$HOME/.claude/skills/planning-enhanced"/*.sh 2>/dev/null | wc -l)
    echo "   ✅ $SKILL_COUNT skills installed"
else
    echo "   ❌ Skills not found"
    INSTALL_FAILED=1
fi

if [ -n "$INSTALL_FAILED" ]; then
    echo ""
    echo "❌ Installation incomplete. See errors above."
    exit 1
else
    echo ""
    echo "✅ Installation complete!"
    echo ""
    echo "Next steps:"
    echo "1. cd /path/to/your/project"
    echo "2. dev-kid init"
    echo "3. dev-kid status"
fi
```

---

## Summary of Safeguards

### Immediate (Blocking Issues)
1. ✅ task-watchdog dependency validation
2. ✅ task-watchdog symlink creation
3. ✅ Missing tasks.md error handling
4. ✅ Micro-checkpoint race condition locking

### Short-term (Quality Improvements)
5. ✅ Malformed task warnings
6. ✅ Context monitor exit code documentation
7. ✅ Better error messages with recommendations
8. ✅ Test script PIPESTATUS fix

### Long-term (Hardening)
9. Integration test suite (after watchdog fix)
10. Performance monitoring for large files
11. Recovery documentation for each error type
12. User troubleshooting guide

---

## Testing the Fixes

After applying patches, re-run edge case tests:

```bash
# Apply all patches
# ... (manually apply each code change above)

# Re-run test suite
./test-ralph-edge-cases.sh

# Expected result: 15/15 tests pass (was 10/15)
# Expected failures fixed:
# - TEST 6: GitHub sync missing tasks.md (now passes with pipefail fix)
# - TEST 8: Micro-checkpoint no changes (now passes with pipefail fix)
# - TEST 12-15: Wave executor tests (now pass with task-watchdog fix)
```

### Validation Checklist

- [ ] task-watchdog symlink created during install
- [ ] Wave executor validates dependencies at startup
- [ ] Missing tasks.md produces clear error message
- [ ] Concurrent micro-checkpoints use file locking
- [ ] Malformed tasks produce warning count
- [ ] Context monitor help shows exit code documentation
- [ ] Test script uses set -o pipefail
- [ ] All 15 edge case tests pass

---

## Deployment Procedure

1. **Backup current installation**
   ```bash
   cp -r ~/.dev-kid ~/.dev-kid.backup
   ```

2. **Apply code patches**
   - Update cli/wave_executor.py (dependency validation, missing tasks.md handling)
   - Update cli/micro_checkpoint.py (file locking)
   - Update cli/github_sync.py (malformed task warnings)
   - Update cli/context_monitor.py (exit code docs)
   - Update test-ralph-edge-cases.sh (pipefail fix)
   - Update scripts/install.sh (task-watchdog symlink, validation)

3. **Re-run installation**
   ```bash
   ./scripts/install.sh
   ```

4. **Validate installation**
   ```bash
   dev-kid status
   command -v task-watchdog
   ```

5. **Run test suite**
   ```bash
   ./test-ralph-edge-cases.sh
   ```

6. **Test in real project**
   ```bash
   cd /path/to/test/project
   dev-kid init
   # Create test tasks.md
   dev-kid orchestrate "Test"
   dev-kid execute-wave
   ```

7. **If tests pass, deploy to production**
   - Tag release: `git tag v2.1-ralph-safeguards`
   - Update documentation
   - Notify users of upgrade

---

End of safeguards document.

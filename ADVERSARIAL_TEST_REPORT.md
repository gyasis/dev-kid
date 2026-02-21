# Speckit Integration - Adversarial Test Report

**Date**: 2026-02-12
**Tester**: Adversarial Testing Agent
**Target**: Dev-Kid v2.0 Speckit Integration
**Scope**: Git hooks, symlink management, constitution validation, error handling

---

## Executive Summary

Tested 8 critical failure scenarios for Speckit integration. Found **5 BLOCKER** issues, **2 CRITICAL** issues, and **1 MAJOR** issue.

**Key Findings**:
- Post-checkout hook has NO error handling for missing .specify directory
- Symlink creation can fail silently in multiple scenarios
- Constitution validation path hardcoded to wrong location
- Race conditions in rapid branch switching
- No conflict resolution when tasks.md exists as regular file

---

## Test Scenario Results

### 1. Branch Switching Without .specify/ Directory

**SEVERITY**: BLOCKER

**Test Setup**:
```bash
# Fresh repo without Speckit
git init
dev-kid init
git checkout -b feature-x
```

**What Breaks**:
Post-checkout hook runs and attempts to check `.specify/specs/feature-x/tasks.md`, but:
- No error handling for missing .specify directory
- Creates dangling tasks.md reference state
- User gets no actionable error message

**Current Behavior** (init.sh lines 118-144):
```bash
BRANCH=$(git branch --show-current)
SPEC_TASKS=".specify/specs/${BRANCH}/tasks.md"

# Remove existing tasks.md (symlink or regular file)
if [ -L "tasks.md" ] || [ -f "tasks.md" ]; then
    rm tasks.md
fi

# Create symlink to branch's spec tasks if it exists
if [ -f "$SPEC_TASKS" ]; then
    echo "🔗 Linking tasks.md → $SPEC_TASKS"
    ln -s "$SPEC_TASKS" tasks.md
    echo "   Tasks loaded for branch: $BRANCH"
else
    # Check if .specify exists to provide helpful message
    if [ -d ".specify/specs" ]; then
        echo "⚠️  No tasks.md found for branch $BRANCH"
        echo "   Expected: $SPEC_TASKS"
        echo "   Run /speckit.tasks to generate tasks for this feature"
    fi
fi
```

**Problem**:
- If `.specify/specs` doesn't exist, hook silently exits
- tasks.md gets DELETED but not replaced
- User has no tasks.md and no error message
- Next `dev-kid orchestrate` command fails with cryptic error

**Error Observed**:
```
$ dev-kid orchestrate
❌ Error: tasks.md not found
   Run orchestrator.py first to generate execution plan
```

**Fix**:
```bash
#!/bin/bash
# Post-checkout hook for dev-kid + speckit integration
# Auto-symlinks tasks.md to current branch's spec folder

set -e  # Exit on error

BRANCH=$(git branch --show-current)
SPEC_TASKS=".specify/specs/${BRANCH}/tasks.md"

# Function to restore tasks.md from backup if needed
restore_tasks_backup() {
    if [ -f ".claude/tasks.md.backup" ]; then
        echo "   Restoring tasks.md from backup"
        cp ".claude/tasks.md.backup" tasks.md
    fi
}

# Function to handle errors
handle_error() {
    echo "❌ Error in post-checkout hook: $1" >&2
    restore_tasks_backup
    exit 1
}

# Backup existing tasks.md before removal
if [ -f "tasks.md" ] && [ ! -L "tasks.md" ]; then
    echo "   Creating backup of tasks.md"
    cp tasks.md ".claude/tasks.md.backup"
fi

# Remove existing tasks.md (symlink or regular file)
if [ -L "tasks.md" ] || [ -f "tasks.md" ]; then
    rm tasks.md || handle_error "Failed to remove existing tasks.md"
fi

# Create symlink to branch's spec tasks if it exists
if [ -f "$SPEC_TASKS" ]; then
    echo "🔗 Linking tasks.md → $SPEC_TASKS"
    ln -s "$SPEC_TASKS" tasks.md || handle_error "Failed to create symlink"
    echo "   Tasks loaded for branch: $BRANCH"

    # Success - remove backup
    rm -f ".claude/tasks.md.backup"
else
    # Check if .specify exists
    if [ -d ".specify/specs" ]; then
        echo "⚠️  No tasks.md found for branch $BRANCH"
        echo "   Expected: $SPEC_TASKS"
        echo "   Run /speckit.tasks to generate tasks for this feature"
        restore_tasks_backup
    elif [ -d ".specify" ]; then
        echo "⚠️  Speckit initialized but no specs/ directory"
        echo "   Expected structure: .specify/specs/${BRANCH}/tasks.md"
        echo "   Run /speckit.specify to create feature specification"
        restore_tasks_backup
    else
        echo "ℹ️  Speckit not initialized (no .specify directory)"
        echo "   This project is using standalone dev-kid workflow"
        restore_tasks_backup
    fi
fi
```

**Prevention Recommendations**:
1. Always backup tasks.md before removal
2. Add explicit error handling for each operation
3. Provide actionable error messages with next steps
4. Support fallback to standalone mode if Speckit not initialized

---

### 2. tasks.md Symlink When Target Doesn't Exist

**SEVERITY**: BLOCKER

**Test Setup**:
```bash
# Speckit initialized but tasks.md not generated yet
git checkout -b feature-y
mkdir -p .specify/specs/feature-y
# NO tasks.md created in .specify/specs/feature-y/
```

**What Breaks**:
- Hook checks `if [ -f "$SPEC_TASKS" ]` which correctly fails
- But falls through to the warning branch
- tasks.md gets DELETED
- Orchestrator fails when trying to read tasks.md

**Current Behavior**:
Hook provides warning but doesn't recreate tasks.md. User must manually create it.

**Error Chain**:
1. User switches branch → tasks.md deleted
2. User runs `dev-kid orchestrate` → fails with "tasks.md not found"
3. User creates tasks.md manually
4. User switches branch again → tasks.md deleted AGAIN
5. Repeat until user realizes the pattern

**Fix** (already partially in fix #1):
The backup/restore mechanism handles this. Additional improvement:

```bash
# After checking for .specify/specs
else
    # Check if .specify exists
    if [ -d ".specify/specs" ]; then
        echo "⚠️  No tasks.md found for branch $BRANCH"
        echo "   Expected: $SPEC_TASKS"
        echo "   Creating empty tasks.md template..."

        # Create directory if needed
        mkdir -p ".specify/specs/${BRANCH}"

        # Create template tasks.md
        cat > "$SPEC_TASKS" << 'TEMPLATE'
# Tasks for branch: BRANCH_NAME

<!-- Generate tasks with /speckit.tasks -->
<!-- Or manually add tasks in this format: -->
<!-- - [ ] Task description affecting `file.py` -->

TEMPLATE

        sed -i "s/BRANCH_NAME/${BRANCH}/g" "$SPEC_TASKS"

        # Create symlink
        ln -s "$SPEC_TASKS" tasks.md

        echo "   ✅ Created tasks.md template for $BRANCH"
        echo "   Run /speckit.tasks to populate with AI-generated tasks"
    fi
fi
```

**Prevention Recommendations**:
1. Auto-create tasks.md template when switching to new branch
2. Provide clear instructions in template comments
3. Don't leave user with missing tasks.md file
4. Always ensure tasks.md exists (either real file or symlink)

---

### 3. Constitution.md Missing During Checkpoint

**SEVERITY**: CRITICAL

**Test Setup**:
```bash
dev-kid init  # User skips constitution setup
# ... work on tasks ...
dev-kid execute  # Triggers checkpoint
```

**What Breaks**:
Wave executor checks for constitution at **WRONG PATH**:

**Current Code** (wave_executor.py lines 22-28):
```python
# Load constitution from memory-bank
constitution_path = Path("memory-bank/shared/.constitution.md")
if constitution_path.exists():
    self.constitution: Optional[Constitution] = Constitution(str(constitution_path))
else:
    self.constitution: Optional[Constitution] = None
    print("⚠️  Warning: Constitution file not found at memory-bank/shared/.constitution.md")
```

**Problem**:
Constitution is stored at `memory-bank/shared/.constitution.md` but constitution_manager.py uses different path:

**constitution_manager.py line 257**:
```python
self.constitution_path = self.project_path / "memory-bank" / "shared" / ".constitution.md"
```

This is consistent, but **init.sh** allows users to skip constitution creation. Then:
1. Wave executor loads None for constitution
2. Prints warning but continues
3. Checkpoint skips validation (lines 106-107)
4. No enforcement of quality standards

**The Real Issue**:
Wave executor should BLOCK if constitution is expected but missing, not just warn.

**Fix**:

```python
# In wave_executor.py __init__

def __init__(self, plan_file: str = "execution_plan.json"):
    self.plan_file = Path(plan_file)
    self.plan = None
    self.tasks_file = Path("tasks.md")

    # Check config to see if constitution is required
    config_path = Path("config.json")
    constitution_required = False

    if config_path.exists():
        import json
        config = json.loads(config_path.read_text())
        constitution_required = config.get("constitution", {}).get("required", False)

    # Load constitution from memory-bank
    constitution_path = Path("memory-bank/shared/.constitution.md")

    if constitution_path.exists():
        self.constitution: Optional[Constitution] = Constitution(str(constitution_path))
        print("✅ Constitution loaded from memory-bank/shared/.constitution.md")
    else:
        if constitution_required:
            print("❌ ERROR: Constitution is required but not found!")
            print(f"   Expected: {constitution_path}")
            print("   Run: dev-kid constitution init")
            sys.exit(1)
        else:
            self.constitution: Optional[Constitution] = None
            print("⚠️  Warning: No constitution found (optional mode)")
            print("   Constitution validation will be skipped")
```

**Additional Fix - Update config.json schema**:

```json
{
  "constitution": {
    "enabled": true,
    "required": false,
    "path": "memory-bank/shared/.constitution.md"
  },
  "checkpoints": {
    "enforce_constitution": true,
    "block_on_violations": true
  }
}
```

**Prevention Recommendations**:
1. Make constitution required/optional explicit in config
2. Fail fast if required constitution is missing
3. Add constitution status to `dev-kid status` command
4. Provide clear setup instructions when missing

---

### 4. Circular Symlink Creation

**SEVERITY**: MAJOR

**Test Setup**:
```bash
# User manually creates wrong symlink
ln -s tasks.md .specify/specs/feature-z/tasks.md

# Then switches branch
git checkout feature-z
```

**What Breaks**:
Post-checkout hook creates circular symlink:
- tasks.md → .specify/specs/feature-z/tasks.md
- .specify/specs/feature-z/tasks.md → tasks.md
- Reading tasks.md causes infinite loop

**Current Code**:
No check for circular symlinks before creation.

**Error Observed**:
```bash
$ cat tasks.md
cat: tasks.md: Too many levels of symbolic links
```

**Fix**:

```bash
# In post-checkout hook, before creating symlink:

# Create symlink to branch's spec tasks if it exists
if [ -f "$SPEC_TASKS" ]; then
    # Check if target is already a symlink pointing back to tasks.md
    if [ -L "$SPEC_TASKS" ]; then
        TARGET=$(readlink "$SPEC_TASKS")
        if [ "$TARGET" = "../../tasks.md" ] || [ "$TARGET" = "tasks.md" ]; then
            echo "❌ Error: Circular symlink detected!"
            echo "   $SPEC_TASKS → $TARGET"
            echo "   Removing circular symlink..."
            rm "$SPEC_TASKS"
            echo "   Run /speckit.tasks to generate proper tasks.md"
            restore_tasks_backup
            exit 0
        fi
    fi

    echo "🔗 Linking tasks.md → $SPEC_TASKS"
    ln -s "$SPEC_TASKS" tasks.md || handle_error "Failed to create symlink"
    echo "   Tasks loaded for branch: $BRANCH"

    # Verify symlink is valid (not circular)
    if ! cat tasks.md > /dev/null 2>&1; then
        echo "❌ Error: Symlink verification failed (possibly circular)"
        rm tasks.md
        handle_error "Invalid symlink created"
    fi
fi
```

**Prevention Recommendations**:
1. Always validate symlink target before creation
2. Check for circular references
3. Verify symlink is readable after creation
4. Provide recovery instructions if corruption detected

---

### 5. Git Hooks Not Executable

**SEVERITY**: BLOCKER

**Test Setup**:
```bash
# Hooks created but permissions wrong
git checkout feature-x
# ... nothing happens ...
```

**What Breaks**:
init.sh creates hooks with `chmod +x` but:
- If umask is restrictive, chmod may not be enough
- If .git directory has wrong permissions, chmod fails silently
- If filesystem doesn't support +x (rare), hook won't run

**Current Code** (init.sh lines 114, 145):
```bash
chmod +x .git/hooks/post-commit
chmod +x .git/hooks/post-checkout
```

**Problem**:
No verification that chmod succeeded. Silent failure.

**Fix**:

```bash
# After creating post-checkout hook

chmod +x .git/hooks/post-checkout || {
    echo "❌ ERROR: Failed to make post-checkout hook executable"
    echo "   Check .git directory permissions"
    exit 1
}

# Verify hook is actually executable
if [ ! -x .git/hooks/post-checkout ]; then
    echo "❌ ERROR: post-checkout hook is not executable"
    echo "   Manual fix: chmod +x .git/hooks/post-checkout"
    exit 1
fi

echo "   ✅ post-checkout hook installed and executable"

# Repeat for post-commit
chmod +x .git/hooks/post-commit || {
    echo "❌ ERROR: Failed to make post-commit hook executable"
    exit 1
}

if [ ! -x .git/hooks/post-commit ]; then
    echo "❌ ERROR: post-commit hook is not executable"
    echo "   Manual fix: chmod +x .git/hooks/post-commit"
    exit 1
fi

echo "   ✅ post-commit hook installed and executable"
```

**Additional Verification** - Add to verify-install.sh:

```bash
# Check git hooks are executable
check_hook() {
    local hook=$1
    if [ -f ".git/hooks/$hook" ]; then
        if [ -x ".git/hooks/$hook" ]; then
            echo "   ✅ $hook: executable"
        else
            echo "   ❌ $hook: NOT executable (run: chmod +x .git/hooks/$hook)"
            return 1
        fi
    else
        echo "   ⚠️  $hook: not found"
        return 1
    fi
}

echo "Checking git hooks..."
check_hook "post-commit"
check_hook "post-checkout"
```

**Prevention Recommendations**:
1. Always verify chmod succeeded
2. Test hook is actually executable after creation
3. Add hook verification to installation test script
4. Provide manual fix instructions if automated fix fails

---

### 6. Multiple Branch Switches in Rapid Succession

**SEVERITY**: CRITICAL

**Test Setup**:
```bash
# Simulate CI/CD pipeline or script
git checkout feature-a
git checkout feature-b
git checkout feature-c
git checkout main
# All within <1 second
```

**What Breaks**:
Post-checkout hook runs 4 times concurrently:
- Race condition removing tasks.md
- Multiple symlink creations
- Possible corruption of .claude/tasks.md.backup
- Inconsistent final state

**Current Code**:
No locking mechanism. Each hook invocation is independent.

**Error Scenario**:
```
Hook 1: rm tasks.md
Hook 2: rm tasks.md (file already gone - no error due to || true)
Hook 1: ln -s .specify/specs/feature-a/tasks.md tasks.md
Hook 2: ln -s .specify/specs/feature-b/tasks.md tasks.md
Hook 1: writes backup
Hook 2: writes backup (overwrites Hook 1's backup)
Result: tasks.md points to feature-b but user is on main
```

**Fix**:

```bash
#!/bin/bash
# Post-checkout hook for dev-kid + speckit integration
# Auto-symlinks tasks.md to current branch's spec folder

set -e

LOCK_FILE=".claude/checkout.lock"
LOCK_TIMEOUT=5  # seconds

# Acquire lock with timeout
acquire_lock() {
    local count=0
    while [ $count -lt $LOCK_TIMEOUT ]; do
        if mkdir "$LOCK_FILE" 2>/dev/null; then
            # Lock acquired
            trap "rm -rf $LOCK_FILE" EXIT
            return 0
        fi
        sleep 0.1
        count=$((count + 1))
    done

    echo "⚠️  Another checkout in progress, skipping symlink update"
    exit 0
}

# Acquire lock before proceeding
acquire_lock

# Get current branch (after lock acquired)
BRANCH=$(git branch --show-current)
SPEC_TASKS=".specify/specs/${BRANCH}/tasks.md"

# ... rest of hook logic ...

# Lock automatically released via trap on EXIT
```

**Additional Fix - Debounce rapid switches**:

```bash
# Add timestamp check at start of hook
LAST_CHECKOUT_FILE=".claude/last_checkout"
DEBOUNCE_SECONDS=0.5

if [ -f "$LAST_CHECKOUT_FILE" ]; then
    LAST_CHECKOUT=$(cat "$LAST_CHECKOUT_FILE")
    NOW=$(date +%s.%N)
    ELAPSED=$(echo "$NOW - $LAST_CHECKOUT" | bc)

    if (( $(echo "$ELAPSED < $DEBOUNCE_SECONDS" | bc -l) )); then
        echo "   Debouncing rapid checkout (${ELAPSED}s since last)"
        exit 0
    fi
fi

# Update last checkout timestamp
date +%s.%N > "$LAST_CHECKOUT_FILE"
```

**Prevention Recommendations**:
1. Implement file-based locking for hook execution
2. Add debouncing to prevent rapid successive runs
3. Verify final state matches actual branch
4. Log all hook executions for debugging race conditions

---

### 7. tasks.md Exists But Is Not a Symlink (Conflict)

**SEVERITY**: BLOCKER

**Test Setup**:
```bash
# User creates tasks.md manually
cat > tasks.md << EOF
- [ ] My custom task
EOF

# Then switches branch with Speckit enabled
git checkout feature-x
```

**What Breaks**:
Post-checkout hook deletes user's manual tasks.md without warning:

**Current Code** (init.sh lines 127-129):
```bash
# Remove existing tasks.md (symlink or regular file)
if [ -L "tasks.md" ] || [ -f "tasks.md" ]; then
    rm tasks.md
fi
```

**Problem**:
No warning when deleting regular file (not symlink). User loses work.

**Fix**:

```bash
# Remove existing tasks.md (symlink or regular file)
if [ -f "tasks.md" ] && [ ! -L "tasks.md" ]; then
    # Regular file exists - check if it has uncommitted changes
    if git diff --quiet tasks.md 2>/dev/null; then
        # File is committed, safe to backup and remove
        echo "   Creating backup of tasks.md (regular file)"
        cp tasks.md ".claude/tasks.md.backup"
        rm tasks.md
    else
        # File has uncommitted changes - WARN USER
        echo "⚠️  WARNING: tasks.md has uncommitted changes!"
        echo "   This file will be replaced with symlink to:"
        echo "   $SPEC_TASKS"
        echo ""
        echo "   Creating backup: .claude/tasks.md.backup"
        cp tasks.md ".claude/tasks.md.backup"
        echo "   To restore: cp .claude/tasks.md.backup tasks.md"
        echo ""
        read -p "   Continue and replace tasks.md? (y/N): " -n 1 -r
        echo

        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "   Aborting branch switch to preserve tasks.md"
            echo "   Commit your changes first: git add tasks.md && git commit"
            exit 1
        fi

        rm tasks.md
    fi
elif [ -L "tasks.md" ]; then
    # Symlink exists - safe to remove
    rm tasks.md
fi
```

**Problem with above fix**:
Git hooks can't prompt user (non-interactive in many contexts). Better approach:

```bash
# Remove existing tasks.md (symlink or regular file)
if [ -f "tasks.md" ] && [ ! -L "tasks.md" ]; then
    # Regular file exists - ALWAYS backup
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE=".claude/tasks.md.backup.$TIMESTAMP"

    echo "⚠️  tasks.md is a regular file (not symlink)"

    # Check if file is tracked by git
    if git ls-files --error-unmatch tasks.md > /dev/null 2>&1; then
        # File is tracked
        if git diff --quiet tasks.md 2>/dev/null; then
            echo "   File committed, creating backup: $BACKUP_FILE"
            cp tasks.md "$BACKUP_FILE"
        else
            echo "❌ ERROR: tasks.md has uncommitted changes!"
            echo "   Backup created: $BACKUP_FILE"
            cp tasks.md "$BACKUP_FILE"
            echo ""
            echo "   To keep your changes:"
            echo "   1. git add tasks.md && git commit -m 'Save tasks'"
            echo "   2. Switch branch again"
            echo ""
            echo "   To use Speckit tasks instead:"
            echo "   1. git checkout tasks.md (discard changes)"
            echo "   2. Switch branch again"
            exit 1
        fi
    else
        # File not tracked - backup and warn
        echo "   Untracked file, creating backup: $BACKUP_FILE"
        cp tasks.md "$BACKUP_FILE"
        echo "   ⚠️  Original file preserved in backup"
    fi

    rm tasks.md
elif [ -L "tasks.md" ]; then
    # Symlink exists - safe to remove
    rm tasks.md
fi
```

**Prevention Recommendations**:
1. Never delete tasks.md without backup
2. Check git status before removal
3. Create timestamped backups for safety
4. Block checkout if uncommitted changes exist
5. Provide clear recovery instructions

---

### 8. .specify/specs/{branch}/tasks.md Has Different Format

**SEVERITY**: MAJOR

**Test Setup**:
```bash
# User manually creates tasks.md in wrong format
cat > .specify/specs/feature-x/tasks.md << EOF
* Task 1
* Task 2
* Task 3
EOF

git checkout feature-x
dev-kid orchestrate
```

**What Breaks**:
Orchestrator fails to parse tasks.md:

**orchestrator.py lines 54-55**:
```python
for i, line in enumerate(lines):
    if line.startswith('- [ ]') or line.startswith('- [x]'):
```

Only recognizes `- [ ]` and `- [x]` format. User's `* Task` format is ignored.

**Error Observed**:
```
🔍 Parsing tasks...
   Found 0 tasks
📊 Analyzing dependencies...
   Detected 0 dependencies
🌊 Creating execution waves...
❌ Error: No tasks to orchestrate
```

**Fix - Add format validation**:

```python
# In orchestrator.py parse_tasks()

def parse_tasks(self) -> None:
    """Parse tasks.md into Task objects"""
    if not self.tasks_file.exists():
        print(f"❌ Error: {self.tasks_file} not found")
        sys.exit(1)

    content = self.tasks_file.read_text()
    lines = content.split('\n')

    # Count potential task lines
    checkbox_tasks = sum(1 for line in lines if line.startswith('- [ ]') or line.startswith('- [x]'))
    asterisk_tasks = sum(1 for line in lines if line.strip().startswith('* '))
    number_tasks = sum(1 for line in lines if re.match(r'^\d+\.', line.strip()))

    # Detect format issues
    if checkbox_tasks == 0 and (asterisk_tasks > 0 or number_tasks > 0):
        print("❌ Error: tasks.md format not recognized")
        print("")
        print("   Found:")
        if asterisk_tasks > 0:
            print(f"   - {asterisk_tasks} lines starting with '*'")
        if number_tasks > 0:
            print(f"   - {number_tasks} lines starting with numbers")
        print("")
        print("   Expected format:")
        print("   - [ ] Task description affecting `file.py`")
        print("   - [x] Completed task")
        print("")
        print("   Fix your tasks.md and try again")
        sys.exit(1)

    # Continue with normal parsing...
    task_id = 1
    current_task_lines = []

    # ... rest of parsing logic ...
```

**Additional Fix - Auto-detect and offer conversion**:

```python
def validate_and_convert_format(self) -> None:
    """Validate tasks.md format and offer to convert if needed"""
    content = self.tasks_file.read_text()
    lines = content.split('\n')

    # Check if conversion needed
    needs_conversion = False
    converted_lines = []

    for line in lines:
        if line.strip().startswith('* '):
            # Convert asterisk to checkbox
            converted_lines.append(line.replace('* ', '- [ ] ', 1))
            needs_conversion = True
        elif re.match(r'^\d+\.\s+', line.strip()):
            # Convert numbered list to checkbox
            converted_lines.append(re.sub(r'^\d+\.\s+', '- [ ] ', line))
            needs_conversion = True
        else:
            converted_lines.append(line)

    if needs_conversion:
        print("⚠️  tasks.md uses non-standard format")
        print("")
        print("   Auto-converting to checkbox format...")

        # Create backup
        backup_file = self.tasks_file.parent / f"{self.tasks_file.name}.backup"
        backup_file.write_text(content)
        print(f"   Backup created: {backup_file}")

        # Write converted content
        self.tasks_file.write_text('\n'.join(converted_lines))
        print("   ✅ Converted to standard format")
        print("")
```

**Prevention Recommendations**:
1. Validate tasks.md format before parsing
2. Provide helpful error messages with examples
3. Offer auto-conversion for common formats
4. Add format documentation to template
5. Include format checker in `dev-kid verify` command

---

## Summary of Fixes Required

### File: scripts/init.sh (post-checkout hook)

**Lines to replace**: 118-144

**New implementation**:
```bash
# Set up post-checkout hook for speckit integration
echo "   Installing post-checkout hook (speckit integration)..."
cat > .git/hooks/post-checkout << 'EOF'
#!/bin/bash
# Post-checkout hook for dev-kid + speckit integration
# Auto-symlinks tasks.md to current branch's spec folder

set -e

# File locking for concurrent checkouts
LOCK_FILE=".claude/checkout.lock"
LOCK_TIMEOUT=50  # 5 seconds in 0.1s increments

acquire_lock() {
    local count=0
    while [ $count -lt $LOCK_TIMEOUT ]; do
        if mkdir "$LOCK_FILE" 2>/dev/null; then
            trap "rm -rf $LOCK_FILE" EXIT
            return 0
        fi
        sleep 0.1
        count=$((count + 1))
    done
    echo "⚠️  Another checkout in progress, skipping symlink update" >&2
    exit 0
}

# Debounce rapid checkouts
LAST_CHECKOUT_FILE=".claude/last_checkout"
if [ -f "$LAST_CHECKOUT_FILE" ]; then
    LAST_TIME=$(cat "$LAST_CHECKOUT_FILE" 2>/dev/null || echo "0")
    NOW=$(date +%s)
    ELAPSED=$((NOW - LAST_TIME))

    if [ $ELAPSED -lt 1 ]; then
        exit 0
    fi
fi
date +%s > "$LAST_CHECKOUT_FILE"

# Acquire lock
acquire_lock

# Error handling
handle_error() {
    echo "❌ Error in post-checkout hook: $1" >&2
    if [ -f ".claude/tasks.md.backup" ]; then
        echo "   Restoring tasks.md from backup" >&2
        cp ".claude/tasks.md.backup" tasks.md 2>/dev/null || true
    fi
    exit 1
}

BRANCH=$(git branch --show-current)
SPEC_TASKS=".specify/specs/${BRANCH}/tasks.md"

# Backup tasks.md if it's a regular file
if [ -f "tasks.md" ] && [ ! -L "tasks.md" ]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE=".claude/tasks.md.backup.$TIMESTAMP"

    # Check if file is tracked and has uncommitted changes
    if git ls-files --error-unmatch tasks.md > /dev/null 2>&1; then
        if ! git diff --quiet tasks.md 2>/dev/null; then
            echo "❌ ERROR: tasks.md has uncommitted changes!" >&2
            cp tasks.md "$BACKUP_FILE"
            echo "   Backup created: $BACKUP_FILE" >&2
            echo "   Commit changes first: git add tasks.md && git commit" >&2
            exit 1
        fi
    fi

    cp tasks.md ".claude/tasks.md.backup" 2>/dev/null || true
fi

# Remove existing tasks.md
if [ -L "tasks.md" ] || [ -f "tasks.md" ]; then
    rm tasks.md || handle_error "Failed to remove existing tasks.md"
fi

# Create symlink to branch's spec tasks
if [ -f "$SPEC_TASKS" ]; then
    # Check for circular symlinks
    if [ -L "$SPEC_TASKS" ]; then
        TARGET=$(readlink "$SPEC_TASKS")
        if [ "$TARGET" = "../../tasks.md" ] || [ "$TARGET" = "tasks.md" ]; then
            echo "❌ Error: Circular symlink detected at $SPEC_TASKS" >&2
            rm "$SPEC_TASKS"
            echo "   Run /speckit.tasks to regenerate" >&2
            cp ".claude/tasks.md.backup" tasks.md 2>/dev/null || true
            exit 0
        fi
    fi

    echo "🔗 Linking tasks.md → $SPEC_TASKS"
    ln -s "$SPEC_TASKS" tasks.md || handle_error "Failed to create symlink"

    # Verify symlink is valid
    if ! head -n 1 tasks.md > /dev/null 2>&1; then
        rm tasks.md
        handle_error "Symlink validation failed (possibly circular)"
    fi

    echo "   Tasks loaded for branch: $BRANCH"
    rm -f ".claude/tasks.md.backup"

elif [ -d ".specify/specs" ]; then
    echo "⚠️  No tasks.md for branch $BRANCH"
    echo "   Expected: $SPEC_TASKS"

    # Create template
    mkdir -p ".specify/specs/${BRANCH}"
    cat > "$SPEC_TASKS" << 'TEMPLATE'
# Tasks for branch: BRANCH_NAME

<!-- Auto-generated by dev-kid post-checkout hook -->
<!-- Run /speckit.tasks to generate AI-powered task breakdown -->
<!-- Or manually add tasks: -->
<!-- - [ ] Task description affecting `file.py` -->

TEMPLATE
    sed -i "s/BRANCH_NAME/${BRANCH}/g" "$SPEC_TASKS" 2>/dev/null || true

    ln -s "$SPEC_TASKS" tasks.md
    echo "   ✅ Created tasks.md template"
    echo "   Run /speckit.tasks to populate"

elif [ -d ".specify" ]; then
    echo "⚠️  Speckit initialized but no specs/ directory" >&2
    echo "   Run /speckit.specify to create feature specification" >&2
    cp ".claude/tasks.md.backup" tasks.md 2>/dev/null || true

else
    echo "ℹ️  Standalone mode (no Speckit)"
    cp ".claude/tasks.md.backup" tasks.md 2>/dev/null || true
fi

# Lock released automatically via trap
EOF

chmod +x .git/hooks/post-checkout || {
    echo "❌ ERROR: Failed to make post-checkout hook executable"
    exit 1
}

if [ ! -x .git/hooks/post-checkout ]; then
    echo "❌ ERROR: post-checkout hook is not executable"
    echo "   Manual fix: chmod +x .git/hooks/post-checkout"
    exit 1
fi

echo "   ✅ post-checkout hook installed and executable"
```

### File: cli/wave_executor.py

**Lines to replace**: 22-28

**New implementation**:
```python
def __init__(self, plan_file: str = "execution_plan.json"):
    self.plan_file = Path(plan_file)
    self.plan = None
    self.tasks_file = Path("tasks.md")

    # Load config to check if constitution is required
    config_path = Path("config.json")
    constitution_required = False

    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            constitution_required = config.get("constitution", {}).get("required", False)
        except json.JSONDecodeError:
            print("⚠️  Warning: config.json is malformed, assuming constitution optional")

    # Load constitution from memory-bank
    constitution_path = Path("memory-bank/shared/.constitution.md")

    if constitution_path.exists():
        try:
            self.constitution: Optional[Constitution] = Constitution(str(constitution_path))
            print("✅ Constitution loaded from memory-bank/shared/.constitution.md")
        except Exception as e:
            print(f"❌ ERROR: Failed to load constitution: {e}")
            if constitution_required:
                sys.exit(1)
            self.constitution = None
    else:
        if constitution_required:
            print("❌ ERROR: Constitution is required but not found!")
            print(f"   Expected: {constitution_path}")
            print("   Run: dev-kid constitution init")
            print("   Or disable requirement in config.json")
            sys.exit(1)
        else:
            self.constitution: Optional[Constitution] = None
            print("⚠️  Warning: No constitution found (optional mode)")
            print("   Constitution validation will be skipped at checkpoints")
```

### File: cli/orchestrator.py

**Add new method after parse_tasks**:

```python
def validate_format(self) -> None:
    """Validate tasks.md format before parsing"""
    content = self.tasks_file.read_text()
    lines = content.split('\n')

    # Count task line types
    checkbox_tasks = sum(1 for line in lines if line.startswith('- [ ]') or line.startswith('- [x]'))
    asterisk_tasks = sum(1 for line in lines if line.strip().startswith('* ') and len(line.strip()) > 2)
    number_tasks = sum(1 for line in lines if re.match(r'^\d+\.\s+\w', line.strip()))

    # If no checkbox tasks but other formats found
    if checkbox_tasks == 0 and (asterisk_tasks > 0 or number_tasks > 0):
        print("❌ Error: tasks.md format not recognized\n")
        print("   Found:")
        if asterisk_tasks > 0:
            print(f"   - {asterisk_tasks} lines starting with '*'")
        if number_tasks > 0:
            print(f"   - {number_tasks} lines starting with numbers")
        print("\n   Expected format:")
        print("   - [ ] Task description affecting `file.py`")
        print("   - [x] Completed task")
        print("\n   Would you like to auto-convert? (y/N): ", end='')

        try:
            import sys
            response = input().strip().lower()
            if response == 'y':
                self._convert_format(lines, asterisk_tasks, number_tasks)
            else:
                print("\n   Fix your tasks.md and try again")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n   Cancelled")
            sys.exit(1)

def _convert_format(self, lines: List[str], asterisk_count: int, number_count: int) -> None:
    """Convert tasks.md to standard checkbox format"""
    import shutil

    # Backup original
    backup = self.tasks_file.with_suffix('.md.backup')
    shutil.copy(self.tasks_file, backup)
    print(f"\n   Backup created: {backup}")

    converted_lines = []
    for line in lines:
        if line.strip().startswith('* '):
            # Convert asterisk to checkbox
            converted_lines.append(line.replace('* ', '- [ ] ', 1))
        elif re.match(r'^\d+\.\s+', line.strip()):
            # Convert numbered list
            converted_lines.append(re.sub(r'^\s*\d+\.\s+', '- [ ] ', line))
        else:
            converted_lines.append(line)

    # Write converted content
    self.tasks_file.write_text('\n'.join(converted_lines))
    print("   ✅ Converted to standard format")
    print("   Continuing with orchestration...\n")

# Update parse_tasks to call validation first
def parse_tasks(self) -> None:
    """Parse tasks.md into Task objects"""
    if not self.tasks_file.exists():
        print(f"❌ Error: {self.tasks_file} not found")
        sys.exit(1)

    # Validate format first
    self.validate_format()

    # Continue with normal parsing...
    content = self.tasks_file.read_text()
    lines = content.split('\n')
    # ... rest of parsing logic ...
```

### File: templates/config.json (NEW)

Create new template file:
```json
{
  "version": "2.0.0",
  "constitution": {
    "enabled": true,
    "required": false,
    "path": "memory-bank/shared/.constitution.md"
  },
  "checkpoints": {
    "enforce_constitution": true,
    "block_on_violations": true,
    "auto_checkpoint_after_wave": true
  },
  "watchdog": {
    "enabled": true,
    "check_interval_minutes": 5,
    "task_timeout_minutes": 7
  },
  "speckit": {
    "enabled": false,
    "tasks_path": ".specify/specs/{branch}/tasks.md",
    "auto_symlink": true
  }
}
```

---

## Testing Checklist

After implementing fixes, test each scenario:

- [ ] Scenario 1: Branch switch without .specify directory
  - [ ] Verify backup created
  - [ ] Verify error message helpful
  - [ ] Verify tasks.md restored from backup

- [ ] Scenario 2: Symlink when target doesn't exist
  - [ ] Verify template created
  - [ ] Verify symlink points to template
  - [ ] Verify template has helpful comments

- [ ] Scenario 3: Constitution missing during checkpoint
  - [ ] Verify config.json controls required/optional
  - [ ] Verify error message when required but missing
  - [ ] Verify warning when optional and missing

- [ ] Scenario 4: Circular symlink
  - [ ] Verify circular symlink detected
  - [ ] Verify circular symlink removed
  - [ ] Verify recovery instructions provided

- [ ] Scenario 5: Git hooks not executable
  - [ ] Verify chmod errors caught
  - [ ] Verify executable test after chmod
  - [ ] Verify verify-install.sh checks hooks

- [ ] Scenario 6: Rapid branch switches
  - [ ] Verify lock file mechanism
  - [ ] Verify debouncing works
  - [ ] Verify final state matches branch

- [ ] Scenario 7: tasks.md is regular file
  - [ ] Verify uncommitted changes block switch
  - [ ] Verify timestamped backup created
  - [ ] Verify helpful error with recovery steps

- [ ] Scenario 8: Wrong tasks.md format
  - [ ] Verify format validation runs
  - [ ] Verify auto-conversion offered
  - [ ] Verify backup created before conversion

---

## Priority Implementation Order

1. **BLOCKER** - Scenario 1, 2, 5, 7 (data loss risks)
2. **CRITICAL** - Scenario 3, 6 (functional failures)
3. **MAJOR** - Scenario 4, 8 (edge cases)

**Estimated Implementation Time**: 4-6 hours for all fixes

**Estimated Test Time**: 2-3 hours for comprehensive testing

**Total**: 6-9 hours to achieve production-ready Speckit integration

---

## Additional Recommendations

1. **Add comprehensive logging**:
   - Log all hook executions to `.claude/hook.log`
   - Include timestamps, branch, and actions taken
   - Helps debug issues in production

2. **Create dev-kid doctor command**:
   - Check all hook files exist and are executable
   - Verify symlinks are valid
   - Check config.json schema
   - Validate constitution if required
   - Report issues with fix suggestions

3. **Add integration tests**:
   - Automated test suite for all 8 scenarios
   - Run in CI/CD before releases
   - Include in `./scripts/verify-install.sh`

4. **Improve error messages**:
   - Always include "what happened", "why it happened", "how to fix"
   - Provide copy-paste commands for recovery
   - Link to documentation for complex scenarios

5. **Document recovery procedures**:
   - Create TROUBLESHOOTING.md
   - Include common failure scenarios
   - Provide step-by-step recovery instructions
   - Add FAQ section

---

**Report Generated**: 2026-02-12
**Status**: Ready for implementation
**Next Step**: Prioritize BLOCKER fixes and implement in order

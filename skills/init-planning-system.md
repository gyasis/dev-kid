---
name: Initialize Planning System
description: Scaffolds the enhanced planning system (Memory Bank, Speckit, Context Protection) into any project directory
version: 2.0.0
triggers:
  - "init planning"
  - "setup planning system"
  - "scaffold planning"
parameters:
  - name: project_path
    description: Absolute path to project directory (defaults to current directory)
    type: string
    required: false
    default: "."
  - name: remote_scaffold
    description: Git URL to pull scaffold templates from
    type: string
    required: false
    default: "https://github.com/gyasis/planning-with-files.git"
  - name: include_skills
    description: Copy core skills to ~/.claude/skills/planning-enhanced/
    type: boolean
    required: false
    default: true
---

# Initialize Planning System v2.0

**Purpose**: Scaffold the complete enhanced planning system into any project directory with memory-bank, context protection, skills, and git hooks.

## What This Skill Does

1. **Validates** project directory exists and has write permissions
2. **Scaffolds** Memory Bank structure with templates
3. **Creates** context protection files (.claude/)
4. **Installs** 6 core skills to ~/.claude/skills/planning-enhanced/
5. **Sets up** git hooks for semantic commits
6. **Initializes** with first checkpoint
7. **Pulls** templates from remote scaffold repository if needed

## Usage

### Basic (current directory)
```bash
claude init-planning
```

### Specific project
```bash
claude init-planning --project_path=/path/to/my-project
```

### With custom scaffold repository
```bash
claude init-planning --project_path=./my-app --remote_scaffold=https://github.com/myorg/custom-scaffold.git
```

### Skip skills installation (if already installed)
```bash
claude init-planning --include_skills=false
```

## Implementation

### Step 1: Validate Environment

```bash
# Check project directory
if [ ! -d "$PROJECT_PATH" ]; then
  echo "❌ Error: Project directory does not exist: $PROJECT_PATH"
  exit 1
fi

# Check write permissions
if [ ! -w "$PROJECT_PATH" ]; then
  echo "❌ Error: No write permission for: $PROJECT_PATH"
  exit 1
fi

# Check if already initialized
if [ -d "$PROJECT_PATH/memory-bank" ]; then
  echo "⚠️  Warning: Planning system already exists in this project"
  echo "Do you want to:"
  echo "  1. Merge (preserve existing, add missing)"
  echo "  2. Overwrite (reset to scaffold templates)"
  echo "  3. Cancel"
  read -p "Choice [1/2/3]: " choice

  case $choice in
    1) MODE="merge" ;;
    2) MODE="overwrite" ;;
    3) exit 0 ;;
    *) echo "Invalid choice"; exit 1 ;;
  esac
else
  MODE="create"
fi
```

### Step 2: Clone Scaffold Templates (if remote)

```bash
TEMP_SCAFFOLD="/tmp/planning-scaffold-$$"

if [ -n "$REMOTE_SCAFFOLD" ]; then
  echo "📥 Cloning scaffold templates from $REMOTE_SCAFFOLD..."
  git clone --depth 1 "$REMOTE_SCAFFOLD" "$TEMP_SCAFFOLD"
  SCAFFOLD_SOURCE="$TEMP_SCAFFOLD"
else
  # Use local templates from this repo
  SCAFFOLD_SOURCE="$(dirname $0)/../templates"
fi
```

### Step 3: Scaffold Memory Bank

```bash
echo "📚 Creating Memory Bank structure..."

# Create directories
mkdir -p "$PROJECT_PATH/memory-bank/shared"
mkdir -p "$PROJECT_PATH/memory-bank/private/$USER"

# Copy or merge templates
if [ "$MODE" = "merge" ]; then
  # Only copy files that don't exist
  for file in projectbrief systemPatterns techContext productContext; do
    if [ ! -f "$PROJECT_PATH/memory-bank/shared/${file}.md" ]; then
      cp "$SCAFFOLD_SOURCE/memory-bank/shared/${file}.md" \
         "$PROJECT_PATH/memory-bank/shared/"
    fi
  done

  for file in activeContext progress worklog; do
    if [ ! -f "$PROJECT_PATH/memory-bank/private/$USER/${file}.md" ]; then
      cp "$SCAFFOLD_SOURCE/memory-bank/private/USER/${file}.md" \
         "$PROJECT_PATH/memory-bank/private/$USER/"
    fi
  done
else
  # Fresh copy or overwrite
  cp -r "$SCAFFOLD_SOURCE/memory-bank/shared/"* \
        "$PROJECT_PATH/memory-bank/shared/"
  cp -r "$SCAFFOLD_SOURCE/memory-bank/private/USER/"* \
        "$PROJECT_PATH/memory-bank/private/$USER/"
fi

echo "  ✅ Memory Bank: memory-bank/shared/ (4 files)"
echo "  ✅ Memory Bank: memory-bank/private/$USER/ (3 files)"
```

### Step 4: Scaffold Context Protection

```bash
echo "🛡️  Creating context protection files..."

mkdir -p "$PROJECT_PATH/.claude/session_snapshots"

# active_stack.md
cat > "$PROJECT_PATH/.claude/active_stack.md" << 'EOF'
# Active Stack (Current Focus)

**Budget**: <500 tokens | **Last Updated**: $(date +%Y-%m-%d)

## Current Task
[What you're working on RIGHT NOW]

## Active Files
- [File 1]
- [File 2]
- [File 3]

## Next 3 Actions
1. [Next action]
2. [Then this]
3. [Finally this]

## Blockers
- [Any blockers]
EOF

# activity_stream.md
cat > "$PROJECT_PATH/.claude/activity_stream.md" << 'EOF'
# Activity Stream (Append-Only Event Log)

**Purpose**: Immutable event log for cross-session history

## Events

### $(date +%Y-%m-%d) - System Initialized
- Planning system scaffolded
- Memory Bank created
- Context protection enabled
EOF

# AGENT_STATE.json
cat > "$PROJECT_PATH/.claude/AGENT_STATE.json" << EOF
{
  "session_id": "",
  "user_id": "$USER",
  "project_path": "$PROJECT_PATH",
  "status": "initialized",
  "agents": {
    "main": {"status": "idle"},
    "memory-keeper": {"status": "idle"},
    "git-manager": {"status": "idle"}
  },
  "initialized_at": "$(date -Iseconds)"
}
EOF

# system_bus.json
cat > "$PROJECT_PATH/.claude/system_bus.json" << 'EOF'
{
  "events": [],
  "metadata": {
    "created_at": "$(date -Iseconds)",
    "version": "2.0.0"
  }
}
EOF

echo "  ✅ Context Protection: .claude/ (4 files + snapshots/)"
```

### Step 5: Install Core Skills

```bash
if [ "$INCLUDE_SKILLS" = true ]; then
  echo "⚡ Installing core skills to ~/.claude/skills/planning-enhanced/..."

  mkdir -p ~/.claude/skills/planning-enhanced

  # Copy 6 core skills
  SKILLS="sync_memory checkpoint verify_existence maintain_integrity finalize_session recall"

  for skill in $SKILLS; do
    cp "$SCAFFOLD_SOURCE/skills/${skill}.md" \
       ~/.claude/skills/planning-enhanced/
  done

  # Copy lazy router
  cp "$SCAFFOLD_SOURCE/skills/router.py" \
     ~/.claude/skills/planning-enhanced/

  # Copy registry
  cp "$SCAFFOLD_SOURCE/skills/registry.json" \
     ~/.claude/skills/planning-enhanced/

  echo "  ✅ Skills installed: 6 core skills + router + registry"
else
  echo "  ⏭️  Skipping skills installation (already installed)"
fi
```

### Step 6: Set Up Git Hooks

```bash
echo "🔗 Setting up git hooks..."

if [ -d "$PROJECT_PATH/.git" ]; then
  # Create post-commit hook
  cat > "$PROJECT_PATH/.git/hooks/post-commit" << 'EOF'
#!/bin/bash
# Auto-generated by planning-with-files skill

# Read progress from Memory Bank
PROGRESS=$(cat memory-bank/private/$USER/progress.md 2>/dev/null || echo "")

# Append to activity stream
echo "" >> .claude/activity_stream.md
echo "### $(date +%Y-%m-%d\ %H:%M:%S) - Git Checkpoint" >> .claude/activity_stream.md
echo "- Commit: $(git rev-parse --short HEAD)" >> .claude/activity_stream.md
echo "- Message: $(git log -1 --pretty=%B | head -1)" >> .claude/activity_stream.md

# Post to system bus
COMMIT_HASH=$(git rev-parse HEAD)
COMMIT_MSG=$(git log -1 --pretty=%B)

python3 << PYTHON
import json
from datetime import datetime

with open('.claude/system_bus.json', 'r') as f:
    bus = json.load(f)

bus['events'].append({
    'timestamp': datetime.now().isoformat(),
    'agent': 'git-manager',
    'event_type': 'checkpoint_created',
    'data': {
        'commit': '$COMMIT_HASH',
        'message': '$COMMIT_MSG'
    }
})

with open('.claude/system_bus.json', 'w') as f:
    json.dump(bus, f, indent=2)
PYTHON

echo "📝 Git checkpoint logged to system bus"
EOF

  chmod +x "$PROJECT_PATH/.git/hooks/post-commit"
  echo "  ✅ Git hooks: post-commit installed"
else
  echo "  ⚠️  No .git directory found - skipping git hooks"
  echo "     Run 'git init' then re-run this skill to install hooks"
fi
```

### Step 7: Create Initial Checkpoint

```bash
echo "📸 Creating initial checkpoint..."

cd "$PROJECT_PATH"

# Initialize git if not already
if [ ! -d .git ]; then
  git init
fi

# Stage planning system files
git add memory-bank/ .claude/ 2>/dev/null || true

# Create milestone commit
git commit -m "[MILESTONE] Planning system v2.0 initialized

- Memory Bank scaffolded (7 files)
- Context protection enabled (.claude/)
- Skills installed (6 core skills)
- Git hooks configured
- System ready for use

Scaffold source: $REMOTE_SCAFFOLD
Initialized by: claude init-planning skill" 2>/dev/null || echo "  ℹ️  No changes to commit (already initialized)"

echo "  ✅ Initial checkpoint created"
```

### Step 8: Create Snapshot

```bash
echo "💾 Creating initial snapshot..."

SNAPSHOT_FILE="$PROJECT_PATH/.claude/session_snapshots/snapshot_$(date +%Y-%m-%d_%H-%M-%S).json"

cat > "$SNAPSHOT_FILE" << EOF
{
  "session_id": "init-$(date +%s)",
  "timestamp": "$(date -Iseconds)",
  "mental_state": "Planning system initialized - ready for first feature",
  "current_phase": "initialization",
  "progress": 0,
  "next_steps": [
    "Read QUICK_START_GUIDE.md to understand daily workflows",
    "Update memory-bank/shared/projectbrief.md with project vision",
    "Create first feature spec with Speckit"
  ],
  "blockers": [],
  "git_commits": ["$(git rev-parse HEAD 2>/dev/null || echo 'none')"],
  "files_modified": [],
  "system_state": {
    "memory_bank": "initialized",
    "context_protection": "enabled",
    "skills": "installed",
    "git_hooks": "active"
  }
}
EOF

# Create symlink to latest snapshot
ln -sf "$(basename $SNAPSHOT_FILE)" \
       "$PROJECT_PATH/.claude/session_snapshots/snapshot_latest.json"

echo "  ✅ Snapshot: $SNAPSHOT_FILE"
```

### Step 9: Cleanup & Summary

```bash
# Remove temp scaffold
if [ -d "$TEMP_SCAFFOLD" ]; then
  rm -rf "$TEMP_SCAFFOLD"
fi

echo ""
echo "✅ Planning System v2.0 Initialized!"
echo ""
echo "📁 Project: $PROJECT_PATH"
echo ""
echo "Created:"
echo "  📚 memory-bank/shared/ (projectbrief, systemPatterns, techContext, productContext)"
echo "  📚 memory-bank/private/$USER/ (activeContext, progress, worklog)"
echo "  🛡️  .claude/ (active_stack, activity_stream, AGENT_STATE, system_bus)"
echo "  📸 .claude/session_snapshots/ (snapshot_*.json)"
echo "  ⚡ ~/.claude/skills/planning-enhanced/ (6 skills + router)"
echo "  🔗 .git/hooks/post-commit (semantic commits)"
echo ""
echo "Next steps:"
echo "  1. Read: QUICK_START_GUIDE.md"
echo "  2. Update: memory-bank/shared/projectbrief.md"
echo "  3. Test: claude recall (should show initial snapshot)"
echo ""
echo "Quick commands:"
echo "  claude sync-memory        # Update Memory Bank"
echo "  claude checkpoint         # Create git checkpoint"
echo "  claude verify-existence   # Anti-hallucination check"
echo "  claude finalize-session   # End session snapshot"
echo "  claude recall             # Resume from snapshot"
echo ""
```

## Error Handling

### Directory Already Exists
- **Action**: Prompt user for merge/overwrite/cancel
- **Default**: Merge (preserve existing, add missing)

### No Git Repository
- **Action**: Initialize git automatically
- **Warning**: User informed that git was initialized

### No Write Permissions
- **Action**: Fail fast with clear error message
- **Suggestion**: Check directory permissions

### Remote Scaffold Unavailable
- **Action**: Fall back to local templates
- **Warning**: Using bundled templates instead of remote

### Skills Directory Permission Denied
- **Action**: Skip skills installation, warn user
- **Suggestion**: Manual installation instructions provided

## Post-Installation Validation

```bash
# Automatic validation after setup
echo "🧪 Validating installation..."

VALIDATION_PASSED=true

# Check Memory Bank
if [ ! -f "$PROJECT_PATH/memory-bank/shared/projectbrief.md" ]; then
  echo "❌ Memory Bank validation failed"
  VALIDATION_PASSED=false
fi

# Check Context Protection
if [ ! -f "$PROJECT_PATH/.claude/AGENT_STATE.json" ]; then
  echo "❌ Context protection validation failed"
  VALIDATION_PASSED=false
fi

# Check Skills
if [ "$INCLUDE_SKILLS" = true ] && [ ! -f ~/.claude/skills/planning-enhanced/sync_memory.md ]; then
  echo "❌ Skills validation failed"
  VALIDATION_PASSED=false
fi

# Check Git Hooks
if [ -d "$PROJECT_PATH/.git" ] && [ ! -x "$PROJECT_PATH/.git/hooks/post-commit" ]; then
  echo "❌ Git hooks validation failed"
  VALIDATION_PASSED=false
fi

if [ "$VALIDATION_PASSED" = true ]; then
  echo "✅ Validation passed - system ready!"
else
  echo "⚠️  Validation warnings - review output above"
  exit 1
fi
```

## Integration with Other Skills

### Recall Skill
After initialization, `claude recall` will find the initial snapshot and present:
```
🔍 No previous session found - starting fresh

📊 System Initialized: 2026-01-05 14:30
Ready to begin first feature!

Suggested next steps:
1. Update projectbrief.md with project vision
2. Create first spec with /speckit.specify
3. Begin development workflow
```

### Checkpoint Skill
First checkpoint after initialization will reference milestone:
```
[CHECKPOINT] First feature planning begun

Following initialization from:
- [MILESTONE] Planning system v2.0 initialized
```

### Verify Existence Skill
Immediately available after installation - validates against scaffolded files:
```bash
claude verify-existence task_plan.md
# ✅ Verified: All referenced files exist
# ✅ Verified: All functions found in codebase
```

## Template Structure (Remote Scaffold)

Expected structure in remote scaffold repository:

```
planning-scaffold/
├── memory-bank/
│   ├── shared/
│   │   ├── projectbrief.md
│   │   ├── systemPatterns.md
│   │   ├── techContext.md
│   │   └── productContext.md
│   └── private/
│       └── USER/
│           ├── activeContext.md
│           ├── progress.md
│           └── worklog.md
├── skills/
│   ├── sync_memory.md
│   ├── checkpoint.md
│   ├── verify_existence.md
│   ├── maintain_integrity.md
│   ├── finalize_session.md
│   ├── recall.md
│   ├── router.py
│   └── registry.json
└── docs/
    ├── QUICK_START_GUIDE.md
    ├── ENHANCED_SYSTEM_ARCHITECTURE.md
    └── PRACTICAL_WORKFLOWS.md
```

## Success Criteria

✅ Memory Bank directory structure created with 7 files
✅ Context protection files created in .claude/
✅ 6 core skills installed to ~/.claude/skills/planning-enhanced/
✅ Git hooks configured (if .git exists)
✅ Initial snapshot created
✅ Initial checkpoint committed
✅ Validation passes

## Time Estimate

- Fresh installation: ~30 seconds
- With remote scaffold clone: ~1 minute
- Merge mode (existing project): ~15 seconds

---

*Planning System Initialization Skill v2.0*
*Created: 2026-01-05*
*Compatible with: Claude Code, planning-with-files v2.0*

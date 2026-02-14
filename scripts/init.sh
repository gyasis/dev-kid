#!/usr/bin/env bash
# Project initialization script for dev-kid

set -e

PROJECT_PATH="${1:-.}"
USER=$(whoami)

cd "$PROJECT_PATH"

echo "📁 Initializing dev-kid in: $(pwd)"

# Create directory structure
echo "   Creating directories..."
mkdir -p memory-bank/shared
mkdir -p "memory-bank/private/$USER"
mkdir -p .claude/session_snapshots

# Get templates directory
if [ -d "$HOME/.dev-kid/templates" ]; then
    TEMPLATES="$HOME/.dev-kid/templates"
else
    # Try relative path (during development)
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    TEMPLATES="$(dirname "$SCRIPT_DIR")/templates"
fi

# Verify templates directory exists
if [ ! -d "$TEMPLATES" ]; then
    echo "❌ Template directory not found"
    echo "   Expected: $TEMPLATES"
    echo ""
    echo "To fix: ./scripts/install.sh"
    exit 1
fi

# Validate critical templates
CRITICAL_TEMPLATES=(
    "memory-bank/shared/projectbrief.md"
    "memory-bank/shared/systemPatterns.md"
    ".claude/active_stack.md"
    ".claude/AGENT_STATE.json"
)

MISSING=()
for template in "${CRITICAL_TEMPLATES[@]}"; do
    if [ ! -f "$TEMPLATES/$template" ]; then
        MISSING+=("$template")
    fi
done

if [ ${#MISSING[@]} -gt 0 ]; then
    echo "❌ Critical templates missing:"
    for t in "${MISSING[@]}"; do
        echo "   - $t"
    done
    echo ""
    echo "To fix: ./scripts/install.sh"
    exit 1
fi

# Create Memory Bank templates
echo "   Creating Memory Bank templates..."

# Copy shared templates
cp "$TEMPLATES/memory-bank/shared/projectbrief.md" memory-bank/shared/ || { echo "❌ Failed to copy projectbrief.md"; exit 1; }
cp "$TEMPLATES/memory-bank/shared/systemPatterns.md" memory-bank/shared/ || { echo "❌ Failed to copy systemPatterns.md"; exit 1; }
cp "$TEMPLATES/memory-bank/shared/techContext.md" memory-bank/shared/ || { echo "❌ Failed to copy techContext.md"; exit 1; }
cp "$TEMPLATES/memory-bank/shared/productContext.md" memory-bank/shared/ || { echo "❌ Failed to copy productContext.md"; exit 1; }

# Copy private templates (USER placeholder gets replaced by actual username)
cp "$TEMPLATES/memory-bank/private/USER/activeContext.md" "memory-bank/private/$USER/" || { echo "❌ Failed to copy activeContext.md"; exit 1; }
cp "$TEMPLATES/memory-bank/private/USER/progress.md" "memory-bank/private/$USER/" || { echo "❌ Failed to copy progress.md"; exit 1; }
cp "$TEMPLATES/memory-bank/private/USER/worklog.md" "memory-bank/private/$USER/" || { echo "❌ Failed to copy worklog.md"; exit 1; }

# Create Context Protection files
echo "   Creating Context Protection..."

# Copy static templates
cp "$TEMPLATES/.claude/active_stack.md" .claude/ || { echo "❌ Failed to copy active_stack.md"; exit 1; }

# Copy templates with variable substitution
sed "s|{{INIT_DATE}}|$(date +%Y-%m-%d)|g" "$TEMPLATES/.claude/activity_stream.md" > .claude/activity_stream.md || { echo "❌ Failed to create activity_stream.md"; exit 1; }

sed -e "s|{{USER}}|$USER|g" \
    -e "s|{{PROJECT_PATH}}|$(pwd)|g" \
    -e "s|{{TIMESTAMP}}|$(date -Iseconds)|g" \
    "$TEMPLATES/.claude/AGENT_STATE.json" > .claude/AGENT_STATE.json || { echo "❌ Failed to create AGENT_STATE.json"; exit 1; }

sed "s|{{TIMESTAMP}}|$(date -Iseconds)|g" "$TEMPLATES/.claude/system_bus.json" > .claude/system_bus.json || { echo "❌ Failed to create system_bus.json"; exit 1; }

# Copy task timers
cp "$TEMPLATES/.claude/task_timers.json" .claude/ || { echo "❌ Failed to copy task_timers.json"; exit 1; }

# Initialize config.json
echo "   Creating config.json..."
DEV_KID_ROOT="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"
python3 "$DEV_KID_ROOT/cli/config_manager.py" init --force > /dev/null 2>&1

# Ask about constitution setup
echo ""
read -p "📜 Initialize project constitution? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "   Setting up constitution..."
    python3 "$DEV_KID_ROOT/cli/constitution_manager.py" init
    echo ""
fi

# Initialize git if needed
if [ ! -d .git ]; then
    echo "   Initializing git..."
    git init
fi

# Set up git hooks
echo "   Installing git hooks..."
cat > .git/hooks/post-commit << 'EOF'
#!/bin/bash
# Post-commit hook for dev-kid

# Log to activity stream
echo "" >> .claude/activity_stream.md
echo "### $(date +%Y-%m-%d\ %H:%M:%S) - Git Checkpoint" >> .claude/activity_stream.md
echo "- Commit: $(git rev-parse --short HEAD)" >> .claude/activity_stream.md

# Update system bus
python3 << 'PYTHON'
import json
from pathlib import Path
from datetime import datetime

bus_file = Path('.claude/system_bus.json')
if bus_file.exists():
    with open(bus_file) as f:
        bus = json.load(f)

    bus['events'].append({
        'timestamp': datetime.now().isoformat(),
        'agent': 'git-manager',
        'event_type': 'checkpoint_created'
    })

    with open(bus_file, 'w') as f:
        json.dump(bus, f, indent=2)
PYTHON
EOF
chmod +x .git/hooks/post-commit

# Set up post-checkout hook for speckit integration
echo "   Installing post-checkout hook (speckit integration)..."
cat > .git/hooks/post-checkout << 'EOF'
#!/bin/bash
# Post-checkout hook for dev-kid + speckit integration
# Auto-symlinks tasks.md and constitution to speckit locations

BRANCH=$(git branch --show-current)
SPEC_TASKS=".specify/specs/${BRANCH}/tasks.md"
SPEC_CONSTITUTION=".specify/memory/constitution.md"
MEMORY_BANK_CONSTITUTION="memory-bank/shared/.constitution.md"

# ===== TASKS SYMLINKING =====

# Backup existing tasks.md if it's a regular file with uncommitted changes
if [ -f "tasks.md" ] && [ ! -L "tasks.md" ]; then
    # Check if it has uncommitted changes
    if ! git diff --quiet tasks.md 2>/dev/null; then
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        BACKUP_FILE=".claude/tasks.md.backup.$TIMESTAMP"
        mkdir -p .claude
        cp tasks.md "$BACKUP_FILE"
        echo "⚠️  Backed up uncommitted tasks.md → $BACKUP_FILE"
    fi
fi

# Remove existing tasks.md (symlink or regular file)
if [ -L "tasks.md" ] || [ -f "tasks.md" ]; then
    rm tasks.md
fi

# Create symlink to branch's spec tasks if it exists
if [ -f "$SPEC_TASKS" ]; then
    # Verify target is readable before creating symlink
    if [ -r "$SPEC_TASKS" ]; then
        echo "🔗 Linking tasks.md → $SPEC_TASKS"
        ln -s "$SPEC_TASKS" tasks.md

        # Verify symlink works
        if [ -r "tasks.md" ]; then
            echo "   ✅ Tasks loaded for branch: $BRANCH"
        else
            echo "   ❌ ERROR: Symlink created but target not readable"
            rm tasks.md
        fi
    else
        echo "   ❌ ERROR: $SPEC_TASKS exists but not readable"
    fi
else
    # Check if .specify exists to provide helpful message
    if [ -d ".specify/specs" ]; then
        echo "⚠️  No tasks.md found for branch $BRANCH"
        echo "   Expected: $SPEC_TASKS"
        echo "   Run /speckit.tasks to generate tasks for this feature"
    fi
fi

# ===== CONSTITUTION SYMLINKING =====

# Remove existing constitution symlink if it exists
if [ -L "$MEMORY_BANK_CONSTITUTION" ]; then
    rm "$MEMORY_BANK_CONSTITUTION"
fi

# Create symlink to speckit constitution if it exists
if [ -f "$SPEC_CONSTITUTION" ]; then
    # Verify target is readable before creating symlink
    if [ -r "$SPEC_CONSTITUTION" ]; then
        echo "🔗 Linking $MEMORY_BANK_CONSTITUTION → $SPEC_CONSTITUTION"
        ln -s "../../.specify/memory/constitution.md" "$MEMORY_BANK_CONSTITUTION"

        # Verify symlink works
        if [ -r "$MEMORY_BANK_CONSTITUTION" ]; then
            echo "   ✅ Constitution linked"
        else
            echo "   ❌ ERROR: Constitution symlink created but target not readable"
            rm "$MEMORY_BANK_CONSTITUTION"
        fi
    else
        echo "   ❌ ERROR: $SPEC_CONSTITUTION exists but not readable"
    fi
else
    # Check if .specify exists to provide helpful message
    if [ -d ".specify/memory" ]; then
        echo "⚠️  No constitution found"
        echo "   Expected: $SPEC_CONSTITUTION"
        echo "   Run /speckit.constitution to create project constitution"
    fi
fi
EOF
chmod +x .git/hooks/post-checkout

# Create initial checkpoint
git add .
git commit -m "[MILESTONE] Dev-kid initialized

- Memory Bank created
- Context Protection enabled
- Task Watchdog configured
- Git hooks installed
- System ready for use" 2>/dev/null || echo "   ℹ️  Already initialized"

# Create initial snapshot
SNAPSHOT_FILE=".claude/session_snapshots/snapshot_$(date +%Y-%m-%d_%H-%M-%S).json"
cat > "$SNAPSHOT_FILE" << EOF
{
  "session_id": "init-$(date +%s)",
  "timestamp": "$(date -Iseconds)",
  "mental_state": "System initialized - ready to begin",
  "current_phase": "initialization",
  "progress": 0,
  "next_steps": [
    "Update projectbrief.md with project vision",
    "Create tasks.md with initial tasks",
    "Run 'dev-kid orchestrate' to plan execution",
    "Run 'dev-kid watchdog-start' to enable task monitoring"
  ],
  "blockers": [],
  "git_commits": ["$(git rev-parse HEAD 2>/dev/null || echo 'none')"],
  "files_modified": [],
  "system_state": {
    "memory_bank": "initialized",
    "context_protection": "enabled",
    "task_watchdog": "ready",
    "skills": "operational"
  }
}
EOF

ln -sf "$(basename $SNAPSHOT_FILE)" ".claude/session_snapshots/snapshot_latest.json"

echo "✅ Dev-kid initialized!"
echo ""
echo "📚 Memory Bank: memory-bank/"
echo "🛡️  Context Protection: .claude/"
echo "⏱️  Task Watchdog: .claude/task_timers.json"
echo "📸 Snapshots: .claude/session_snapshots/"
echo "🔗 Git Hooks: post-commit, post-checkout (speckit integration)"
echo ""
echo "Next steps:"
echo ""
echo "Option A - With Speckit (recommended for feature-branch workflow):"
echo "  1. Run: /speckit.constitution (create project rules)"
echo "  2. Run: /speckit.specify 'Your feature description' (create branch + spec)"
echo "  3. Run: /speckit.tasks (generate tasks.md from spec)"
echo "  4. Run: dev-kid orchestrate (create execution plan)"
echo "  5. Run: dev-kid execute (execute waves)"
echo ""
echo "Option B - Standalone (manual tasks.md):"
echo "  1. Setup constitution: dev-kid constitution init (if not done)"
echo "  2. Edit memory-bank/shared/projectbrief.md (define project vision)"
echo "  3. Create tasks.md (list your tasks)"
echo "  4. Run: dev-kid orchestrate (create execution plan)"
echo "  5. Run: dev-kid watchdog-start (start task monitoring)"
echo "  6. Run: dev-kid execute (execute waves)"
echo ""
echo "Quick commands:"
echo "  dev-kid constitution show  # View development rules"
echo "  dev-kid config show        # View runtime config"
echo "  dev-kid status             # Check system status"
echo "  dev-kid help               # Show all commands"

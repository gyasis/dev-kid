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

# Create Memory Bank templates
echo "   Creating Memory Bank templates..."

# Copy shared templates
cp "$TEMPLATES/memory-bank/shared/projectbrief.md" memory-bank/shared/
cp "$TEMPLATES/memory-bank/shared/systemPatterns.md" memory-bank/shared/
cp "$TEMPLATES/memory-bank/shared/techContext.md" memory-bank/shared/
cp "$TEMPLATES/memory-bank/shared/productContext.md" memory-bank/shared/

# Copy private templates (USER placeholder gets replaced by actual username)
cp "$TEMPLATES/memory-bank/private/USER/activeContext.md" "memory-bank/private/$USER/"
cp "$TEMPLATES/memory-bank/private/USER/progress.md" "memory-bank/private/$USER/"
cp "$TEMPLATES/memory-bank/private/USER/worklog.md" "memory-bank/private/$USER/"

# Create Context Protection files
echo "   Creating Context Protection..."

# Copy static templates
cp "$TEMPLATES/.claude/active_stack.md" .claude/

# Copy templates with variable substitution
sed "s|{{INIT_DATE}}|$(date +%Y-%m-%d)|g" "$TEMPLATES/.claude/activity_stream.md" > .claude/activity_stream.md

sed -e "s|{{USER}}|$USER|g" \
    -e "s|{{PROJECT_PATH}}|$(pwd)|g" \
    -e "s|{{TIMESTAMP}}|$(date -Iseconds)|g" \
    "$TEMPLATES/.claude/AGENT_STATE.json" > .claude/AGENT_STATE.json

sed "s|{{TIMESTAMP}}|$(date -Iseconds)|g" "$TEMPLATES/.claude/system_bus.json" > .claude/system_bus.json

# Copy task timers
cp "$TEMPLATES/.claude/task_timers.json" .claude/

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
# Auto-symlinks tasks.md to current branch's spec folder

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

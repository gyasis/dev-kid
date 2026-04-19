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

# Create Memory Bank templates (guarded — never overwrite existing user data)
echo "   Creating Memory Bank templates..."

_copy_if_missing() {
    local src="$1" dst="$2" label="$3"
    if [ ! -f "$dst" ]; then
        cp "$src" "$dst" || { echo "❌ Failed to copy $label"; exit 1; }
        echo "   ✅ $label"
    else
        echo "   ⏭️  $label (exists — kept)"
    fi
}

# Copy shared templates
_copy_if_missing "$TEMPLATES/memory-bank/shared/projectbrief.md"  memory-bank/shared/projectbrief.md  "projectbrief.md"
_copy_if_missing "$TEMPLATES/memory-bank/shared/systemPatterns.md" memory-bank/shared/systemPatterns.md "systemPatterns.md"
_copy_if_missing "$TEMPLATES/memory-bank/shared/techContext.md"    memory-bank/shared/techContext.md    "techContext.md"
_copy_if_missing "$TEMPLATES/memory-bank/shared/productContext.md" memory-bank/shared/productContext.md "productContext.md"

# Copy private templates
_copy_if_missing "$TEMPLATES/memory-bank/private/USER/activeContext.md" "memory-bank/private/$USER/activeContext.md" "activeContext.md"
_copy_if_missing "$TEMPLATES/memory-bank/private/USER/progress.md"      "memory-bank/private/$USER/progress.md"      "progress.md"
_copy_if_missing "$TEMPLATES/memory-bank/private/USER/worklog.md"       "memory-bank/private/$USER/worklog.md"        "worklog.md"

# Create Context Protection files (guarded — preserve user state)
echo "   Creating Context Protection..."

_copy_if_missing "$TEMPLATES/.claude/active_stack.md" .claude/active_stack.md "active_stack.md"

if [ ! -f ".claude/activity_stream.md" ]; then
    sed "s|{{INIT_DATE}}|$(date +%Y-%m-%d)|g" "$TEMPLATES/.claude/activity_stream.md" > .claude/activity_stream.md || { echo "❌ Failed to create activity_stream.md"; exit 1; }
    echo "   ✅ activity_stream.md"
else
    echo "   ⏭️  activity_stream.md (exists — kept)"
fi

if [ ! -f ".claude/AGENT_STATE.json" ]; then
    sed -e "s|{{USER}}|$USER|g" \
        -e "s|{{PROJECT_PATH}}|$(pwd)|g" \
        -e "s|{{TIMESTAMP}}|$(date -Iseconds)|g" \
        "$TEMPLATES/.claude/AGENT_STATE.json" > .claude/AGENT_STATE.json || { echo "❌ Failed to create AGENT_STATE.json"; exit 1; }
    echo "   ✅ AGENT_STATE.json"
else
    echo "   ⏭️  AGENT_STATE.json (exists — kept)"
fi

if [ ! -f ".claude/system_bus.json" ]; then
    sed "s|{{TIMESTAMP}}|$(date -Iseconds)|g" "$TEMPLATES/.claude/system_bus.json" > .claude/system_bus.json || { echo "❌ Failed to create system_bus.json"; exit 1; }
    echo "   ✅ system_bus.json"
else
    echo "   ⏭️  system_bus.json (exists — kept)"
fi

# task_timers.json — always reset (ephemeral watchdog state, safe to overwrite)
cp "$TEMPLATES/.claude/task_timers.json" .claude/ || { echo "❌ Failed to copy task_timers.json"; exit 1; }

# Copy hooks configuration and scripts
echo "   Installing Claude Code hooks..."
cp "$TEMPLATES/.claude/settings.json" .claude/ || { echo "❌ Failed to copy settings.json"; exit 1; }
mkdir -p .claude/hooks
cp -r "$TEMPLATES/.claude/hooks/"* .claude/hooks/ || { echo "❌ Failed to copy hooks"; exit 1; }
chmod +x .claude/hooks/*.sh

# Remove orphaned nested hooks/ dir created by glob expansion
rm -rf .claude/hooks/hooks/

# Validate hooks deployed correctly
for hook in pre-compact.sh task-completed.sh post-tool-use.sh user-prompt-submit.sh session-start.sh session-end.sh pre-tool-use.sh stop.sh post-tool-use-failure.sh; do
    if [ ! -f ".claude/hooks/$hook" ]; then
        echo "⚠️  Warning: Hook not deployed: .claude/hooks/$hook"
    else
        chmod +x ".claude/hooks/$hook"
    fi
done
if [ ! -f ".claude/settings.json" ]; then
    echo "⚠️  Warning: .claude/settings.json not deployed"
fi

# Copy dev-kid.yml (sentinel + orchestration config) — first init only
DEV_KID_ROOT="$(dirname "$(dirname "${BASH_SOURCE[0]}")")"
if [ ! -f "dev-kid.yml" ]; then
    if [ -f "$DEV_KID_ROOT/dev-kid.yml" ]; then
        cp "$DEV_KID_ROOT/dev-kid.yml" dev-kid.yml
        echo "   ✅ Copied dev-kid.yml"
    fi

    # Ask about sentinel setup (only on first init — dev-kid.yml didn't exist)
    echo ""
    read -p "🛡️  Enable Integration Sentinel (auto test-fix loop after each task)? (y/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    sed -i 's/enabled: false/enabled: true/' dev-kid.yml
    echo "   ✅ Sentinel enabled"
    echo ""
    read -p "   Ollama URL for Tier 1 (local model) [http://localhost:11434, Enter to skip Tier 1]: " OLLAMA_URL
    if [ -n "$OLLAMA_URL" ]; then
        sed -i "s|ollama_url:.*|ollama_url: $OLLAMA_URL|" dev-kid.yml
        echo "   ✅ Ollama URL set to $OLLAMA_URL"
    else
        echo "   ℹ️  Skipping Tier 1 — sentinel will go straight to Tier 2 (Claude Sonnet)"
    fi

    # Provider health check
    echo ""
    echo "   Running provider health check..."
    python3 - <<PYEOF
import sys, os
sys.path.insert(0, '$DEV_KID_ROOT/cli')
try:
    from sentinel.tier_runner import sentinel_health_check
    class _Cfg:
        sentinel_tier1_ollama_url = '${OLLAMA_URL:-http://localhost:11434}'
    health = sentinel_health_check(_Cfg())
    ok = True
    if not health['micro_agent_installed']:
        print("   ❌ micro-agent CLI not found")
        print("      Install: npm install -g @gyasis/micro-agent")
        ok = False
    if health['tier1_available']:
        print(f"   ✅ Tier 1 (Ollama): reachable at {health['tier1_url']}")
    else:
        print(f"   ⚠️  Tier 1 (Ollama): not reachable at {health['tier1_url']}")
    if health['tier2_available']:
        print("   ✅ Tier 2 (Claude): ANTHROPIC_API_KEY found")
    else:
        print("   ⚠️  Tier 2 (Claude): ANTHROPIC_API_KEY not set")
    if not health['any_tier_available']:
        print("")
        print("   ⚠️  WARNING: No working providers detected.")
        print("      Sentinel is enabled but will SKIP the test loop until a provider is reachable.")
        print("      Fix one of the above, then re-run: dev-kid sentinel-status")
    elif ok:
        print("   ✅ Sentinel ready")
except Exception as e:
    print(f"   ⚠️  Health check failed: {e}")
PYEOF
    else
        echo "   ℹ️  Sentinel disabled — edit dev-kid.yml to enable later"
    fi
else
    echo "   ⏭️  dev-kid.yml (exists — kept, sentinel config unchanged)"
fi

# Initialize config.json
echo "   Creating config.json..."
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

# Link speckit constitution immediately if it already exists
SPEC_CONSTITUTION=".specify/memory/constitution.md"
MEMORY_CONSTITUTION="memory-bank/shared/.constitution.md"
if [ -f "$SPEC_CONSTITUTION" ]; then
    echo "   Linking constitution from speckit..."
    ln -sf "../../.specify/memory/constitution.md" "$MEMORY_CONSTITUTION"
    echo "   ✅ Constitution linked: $MEMORY_CONSTITUTION → $SPEC_CONSTITUTION"
elif [ -d ".specify/memory" ]; then
    echo "   ⚠️  .specify/memory exists but no constitution.md — run /speckit.constitution to create one"
fi

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
echo "🪝 Claude Code Hooks: .claude/hooks/ (auto-checkpoint, GitHub sync)"
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

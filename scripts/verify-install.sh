#!/usr/bin/env bash
# Dev-Kid Installation Verification Script

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔍 Verifying dev-kid installation..."
echo ""

ERRORS=0
WARNINGS=0

# Check function
check() {
    local name="$1"
    local test_cmd="$2"
    local expected="$3"

    if eval "$test_cmd" &> /dev/null; then
        echo -e "   ${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "   ${RED}✗${NC} $name - $expected"
        ERRORS=$((ERRORS + 1))
        return 1
    fi
}

check_optional() {
    local name="$1"
    local test_cmd="$2"
    local suggestion="$3"

    if eval "$test_cmd" &> /dev/null; then
        echo -e "   ${GREEN}✓${NC} $name"
        return 0
    else
        echo -e "   ${YELLOW}⚠${NC}  $name - $suggestion"
        WARNINGS=$((WARNINGS + 1))
        return 1
    fi
}

# 1. Check CLI installation
echo "📦 CLI Installation"
check "dev-kid executable" "command -v dev-kid" "Run: ./scripts/install.sh"
check "dev-kid symlink" "[ -L /usr/local/bin/dev-kid ] || grep -q 'dev-kid/cli' ~/.bashrc" "Check PATH or symlink"

echo ""

# 2. Check system files
echo "📁 System Files (~/.dev-kid)"
check "Installation directory" "[ -d ~/.dev-kid ]" "Run: ./scripts/install.sh"
check "CLI scripts" "[ -f ~/.dev-kid/cli/dev-kid ]" "Missing CLI scripts"
check "Orchestrator module" "[ -f ~/.dev-kid/cli/orchestrator.py ]" "Missing orchestrator.py"
check "Wave executor module" "[ -f ~/.dev-kid/cli/wave_executor.py ]" "Missing wave_executor.py"
check "Task watchdog module" "[ -f ~/.dev-kid/cli/task_watchdog.py ]" "Missing task_watchdog.py"

echo ""

# 3. Check Claude Code skills
echo "🎯 Claude Code Skills (~/.claude/skills)"
SKILL_COUNT=$(ls -1 ~/.claude/skills/*.md 2>/dev/null | wc -l || echo 0)
if [ "$SKILL_COUNT" -ge 5 ]; then
    echo -e "   ${GREEN}✓${NC} Skills installed: $SKILL_COUNT"
else
    echo -e "   ${RED}✗${NC} Skills installed: $SKILL_COUNT (expected >= 5)"
    ERRORS=$((ERRORS + 1))
fi

check "orchestrate-tasks.md" "[ -f ~/.claude/skills/orchestrate-tasks.md ]" "Missing skill"
check "execute-waves.md" "[ -f ~/.claude/skills/execute-waves.md ]" "Missing skill"
check "checkpoint-wave.md" "[ -f ~/.claude/skills/checkpoint-wave.md ]" "Missing skill"
check "sync-memory.md" "[ -f ~/.claude/skills/sync-memory.md ]" "Missing skill"
check "speckit-workflow.md" "[ -f ~/.claude/skills/speckit-workflow.md ]" "Missing skill"

echo ""

# 4. Check Claude Code commands
echo "⚡ Claude Code Commands (~/.claude/commands)"
CMD_COUNT=$(ls -1 ~/.claude/commands/devkid.*.md 2>/dev/null | wc -l || echo 0)
if [ "$CMD_COUNT" -ge 5 ]; then
    echo -e "   ${GREEN}✓${NC} Commands installed: $CMD_COUNT"
else
    echo -e "   ${RED}✗${NC} Commands installed: $CMD_COUNT (expected >= 5)"
    ERRORS=$((ERRORS + 1))
fi

check "devkid.orchestrate.md" "[ -f ~/.claude/commands/devkid.orchestrate.md ]" "Missing command"
check "devkid.execute.md" "[ -f ~/.claude/commands/devkid.execute.md ]" "Missing command"
check "devkid.checkpoint.md" "[ -f ~/.claude/commands/devkid.checkpoint.md ]" "Missing command"
check "devkid.sync-memory.md" "[ -f ~/.claude/commands/devkid.sync-memory.md ]" "Missing command"
check "devkid.workflow.md" "[ -f ~/.claude/commands/devkid.workflow.md ]" "Missing command"

echo ""

# 5. Check dependencies
echo "🔧 Dependencies"
check "Python 3.7+" "python3 -c 'import sys; exit(0 if sys.version_info >= (3,7) else 1)'" "Install Python 3.7+"
check "Git" "command -v git" "Install git"
check "jq" "command -v jq" "Install jq"
check_optional "sed" "command -v sed" "Recommended for text processing"
check_optional "grep" "command -v grep" "Recommended for searching"

echo ""

# 6. Test basic functionality
echo "🧪 Functional Tests"

# Test orchestrator import
if python3 -c "import sys; sys.path.insert(0, '$HOME/.dev-kid/cli'); import orchestrator" 2>/dev/null; then
    echo -e "   ${GREEN}✓${NC} Orchestrator module loads"
else
    echo -e "   ${RED}✗${NC} Orchestrator module import failed"
    ERRORS=$((ERRORS + 1))
fi

# Test wave executor import
if python3 -c "import sys; sys.path.insert(0, '$HOME/.dev-kid/cli'); import wave_executor" 2>/dev/null; then
    echo -e "   ${GREEN}✓${NC} Wave executor module loads"
else
    echo -e "   ${RED}✗${NC} Wave executor module import failed"
    ERRORS=$((ERRORS + 1))
fi

# Test watchdog import
if python3 -c "import sys; sys.path.insert(0, '$HOME/.dev-kid/cli'); import task_watchdog" 2>/dev/null; then
    echo -e "   ${GREEN}✓${NC} Task watchdog module loads"
else
    echo -e "   ${RED}✗${NC} Task watchdog module import failed"
    ERRORS=$((ERRORS + 1))
fi

echo ""

# 7. Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ Installation verified successfully!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $WARNINGS optional items missing${NC}"
    fi
    echo ""
    echo "Next steps:"
    echo "  cd your-project"
    echo "  dev-kid init"
    echo "  dev-kid status"
    echo ""
    echo "Or use slash commands in Claude Code:"
    echo "  /devkid.workflow"
    exit 0
else
    echo -e "${RED}❌ Installation verification failed!${NC}"
    echo "   Errors: $ERRORS"
    echo "   Warnings: $WARNINGS"
    echo ""
    echo "Fix issues and run again:"
    echo "  ./scripts/install.sh"
    echo "  ./scripts/verify-install.sh"
    exit 1
fi

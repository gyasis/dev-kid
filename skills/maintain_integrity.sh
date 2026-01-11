#!/usr/bin/env bash
# Skill: Maintain Integrity
# Trigger: session start, after context compression

set -e

echo "🔧 Validating system integrity..."

ERRORS=0

# Check Memory Bank structure
echo "   Checking Memory Bank..."
REQUIRED_SHARED=("projectbrief.md" "systemPatterns.md" "techContext.md" "productContext.md")
for file in "${REQUIRED_SHARED[@]}"; do
    if [ ! -f "memory-bank/shared/$file" ]; then
        echo "   ❌ Missing: memory-bank/shared/$file"
        ERRORS=$((ERRORS + 1))
    fi
done

USER=$(whoami)
REQUIRED_PRIVATE=("activeContext.md" "progress.md" "worklog.md")
for file in "${REQUIRED_PRIVATE[@]}"; do
    if [ ! -f "memory-bank/private/$USER/$file" ]; then
        echo "   ❌ Missing: memory-bank/private/$USER/$file"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check Context Protection
echo "   Checking Context Protection..."
REQUIRED_CLAUDE=("active_stack.md" "activity_stream.md" "AGENT_STATE.json" "system_bus.json")
for file in "${REQUIRED_CLAUDE[@]}"; do
    if [ ! -f ".claude/$file" ]; then
        echo "   ❌ Missing: .claude/$file"
        ERRORS=$((ERRORS + 1))
    fi
done

# Check Skills
echo "   Checking Skills..."
SKILLS_DIR="$HOME/.claude/skills/planning-enhanced"
if [ ! -d "$SKILLS_DIR" ]; then
    echo "   ⚠️  WARNING: Skills directory not found: $SKILLS_DIR"
else
    SKILL_COUNT=$(ls -1 "$SKILLS_DIR"/*.sh 2>/dev/null | wc -l)
    echo "   ✅ Skills installed: $SKILL_COUNT"
fi

# Check Git
echo "   Checking Git..."
if [ ! -d ".git" ]; then
    echo "   ⚠️  WARNING: Git not initialized"
else
    echo "   ✅ Git initialized"
fi

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "❌ Integrity check failed: $ERRORS error(s)"
    echo "   Run 'dev-kit init' to repair"
    exit 1
fi

echo "✅ System integrity validated"

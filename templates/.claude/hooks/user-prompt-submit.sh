#!/usr/bin/env bash
# UserPromptSubmit Hook - Inject project context before prompt processing

set -e

# Read stdin (contains user prompt)
read -r EVENT_DATA

# Build context injection
CONTEXT_INJECTION=""

# 1. Current git branch
if git rev-parse --git-dir > /dev/null 2>&1; then
    BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")
    CONTEXT_INJECTION+="📍 Current branch: $BRANCH\n"
fi

# 2. Constitution rules (if exists)
if [ -f memory-bank/shared/.constitution.md ]; then
    CONSTITUTION_SUMMARY=$(head -n 20 memory-bank/shared/.constitution.md | grep -E "^##|^-" | head -n 5 || echo "Constitution exists")
    if [ -n "$CONSTITUTION_SUMMARY" ]; then
        CONTEXT_INJECTION+="📜 Active constitution rules:\n$CONSTITUTION_SUMMARY\n"
    fi
fi

# 3. Task progress (if tasks.md exists)
if [ -f tasks.md ]; then
    TOTAL=$(grep -c "^- \[.\]" tasks.md 2>/dev/null || echo "0")
    COMPLETED=$(grep -c "^- \[x\]" tasks.md 2>/dev/null || echo "0")
    if [ "$TOTAL" -gt 0 ]; then
        CONTEXT_INJECTION+="📊 Task progress: $COMPLETED/$TOTAL completed\n"
    fi
fi

# 4. Current wave (if execution_plan.json exists)
if [ -f execution_plan.json ]; then
    CURRENT_WAVE=$(jq -r '.execution_plan.current_wave // "unknown"' execution_plan.json 2>/dev/null || echo "unknown")
    if [ "$CURRENT_WAVE" != "unknown" ]; then
        CONTEXT_INJECTION+="🌊 Current wave: $CURRENT_WAVE\n"
    fi
fi

# 5. Recent errors (check activity stream for errors)
if [ -f .claude/activity_stream.md ]; then
    RECENT_ERRORS=$(grep -i "error\|failed\|❌" .claude/activity_stream.md 2>/dev/null | tail -n 3 || echo "")
    if [ -n "$RECENT_ERRORS" ]; then
        CONTEXT_INJECTION+="⚠️ Recent issues detected:\n$RECENT_ERRORS\n"
    fi
fi

# Output context injection to stdout (Claude will prepend to prompt)
if [ -n "$CONTEXT_INJECTION" ]; then
    echo -e "\n---\n🤖 **Project Context** (auto-injected)\n$CONTEXT_INJECTION\n---\n"
fi

# Return success
exit 0

#!/usr/bin/env bash
# Skill: Verify Existence (Anti-Hallucination)
# Trigger: before code generation, before file operations

set -e

echo "🔍 Running anti-hallucination verification..."

# File to verify (default: task_plan.md)
TARGET="${1:-task_plan.md}"

if [ ! -f "$TARGET" ]; then
    echo "❌ Error: $TARGET not found"
    exit 1
fi

# Extract file references
FILES=$(grep -oP '`[^`]+\.(js|ts|py|md|json|sh|yml|yaml)`' "$TARGET" | tr -d '`' | sort -u)

ERRORS=0

echo "   Checking file references..."
for file in $FILES; do
    if [ ! -f "$file" ]; then
        echo "   ❌ HALLUCINATION: File does not exist: $file"
        ERRORS=$((ERRORS + 1))
    else
        echo "   ✅ Verified: $file"
    fi
done

# Extract function references (simple pattern matching)
FUNCTIONS=$(grep -oP '[a-zA-Z_][a-zA-Z0-9_]*\(' "$TARGET" | tr -d '(' | sort -u)

echo "   Checking function references..."
for func in $FUNCTIONS; do
    # Search for function definition in codebase
    if ! grep -rq "function $func\|def $func\|const $func =\|let $func =\|var $func =" . 2>/dev/null; then
        echo "   ⚠️  WARNING: Function '$func' not found in codebase"
        # Don't count as error - might be new function to implement
    fi
done

if [ $ERRORS -gt 0 ]; then
    echo ""
    echo "❌ Verification failed: $ERRORS hallucinated file(s) detected"
    echo "   Update plan to reference existing files"
    exit 1
fi

echo "✅ Verification passed"

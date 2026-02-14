#!/usr/bin/env bash
# PostToolUse Hook - Format and lint after file edits

set -e

# Read stdin (contains tool usage metadata)
read -r EVENT_DATA

# Extract tool name and file path (if available)
TOOL_NAME=$(echo "$EVENT_DATA" | grep -oP '"tool":\s*"\K[^"]+' || echo "unknown")
FILE_PATH=$(echo "$EVENT_DATA" | grep -oP '"file_path":\s*"\K[^"]+' || echo "")

# Only process Edit/Write tools
if [[ "$TOOL_NAME" != "Edit" ]] && [[ "$TOOL_NAME" != "Write" ]]; then
    echo '{"status": "skipped", "message": "Not a file edit operation"}'
    exit 0
fi

# If no file path detected, skip
if [ -z "$FILE_PATH" ]; then
    echo '{"status": "skipped", "message": "No file path detected"}'
    exit 0
fi

# Auto-format Python files
if [[ "$FILE_PATH" == *.py ]]; then
    if command -v black &> /dev/null; then
        black "$FILE_PATH" 2>/dev/null || true
    fi
    if command -v isort &> /dev/null; then
        isort "$FILE_PATH" 2>/dev/null || true
    fi
fi

# Auto-format JavaScript/TypeScript files
if [[ "$FILE_PATH" == *.js ]] || [[ "$FILE_PATH" == *.ts ]] || [[ "$FILE_PATH" == *.jsx ]] || [[ "$FILE_PATH" == *.tsx ]]; then
    if command -v prettier &> /dev/null; then
        prettier --write "$FILE_PATH" 2>/dev/null || true
    fi
fi

# Auto-format Bash scripts
if [[ "$FILE_PATH" == *.sh ]]; then
    if command -v shfmt &> /dev/null; then
        shfmt -w "$FILE_PATH" 2>/dev/null || true
    fi
fi

# Return success
echo '{"status": "success", "message": "Post-edit formatting completed"}'
exit 0

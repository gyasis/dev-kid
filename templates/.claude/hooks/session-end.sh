#!/usr/bin/env bash
# SessionEnd Hook - Finalize session and create snapshot

set -e

# Read stdin
read -r EVENT_DATA

# Log the event
echo "" >> .claude/activity_stream.md
echo "### $(date +%Y-%m-%d\ %H:%M:%S) - Session Ended" >> .claude/activity_stream.md

# Check if dev-kid is available
if ! command -v dev-kid &> /dev/null; then
    echo '{"status": "skipped", "message": "dev-kid not in PATH"}'
    exit 0
fi

# Finalize session (creates snapshot + checkpoint if needed)
dev-kid finalize 2>/dev/null || echo "   ⚠️ Finalization skipped (may not be in dev-kid project)"

# Update AGENT_STATE
if [ -f .claude/AGENT_STATE.json ]; then
    python3 << 'PYTHON'
import json
from pathlib import Path
from datetime import datetime

state_file = Path('.claude/AGENT_STATE.json')
if state_file.exists():
    with open(state_file) as f:
        state = json.load(f)

    state['status'] = 'finalized'
    state['last_session_end'] = datetime.now().isoformat()

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
PYTHON
fi

# Return success
echo '{"status": "success", "message": "Session finalized"}'
exit 0

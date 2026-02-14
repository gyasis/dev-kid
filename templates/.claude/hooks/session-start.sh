#!/usr/bin/env bash
# SessionStart Hook - Restore context from last session

set -e

# Read stdin
read -r EVENT_DATA

# Log the event
echo "" >> .claude/activity_stream.md
echo "### $(date +%Y-%m-%d\ %H:%M:%S) - Session Started" >> .claude/activity_stream.md

# Check if dev-kid is available
if ! command -v dev-kid &> /dev/null; then
    echo '{"status": "skipped", "message": "dev-kid not in PATH"}'
    exit 0
fi

# Restore from last snapshot
if [ -f .claude/session_snapshots/snapshot_latest.json ]; then
    echo "🔄 Restoring from last session..." >> .claude/activity_stream.md
    dev-kid recall 2>/dev/null || echo "   ⚠️ Recall skipped (snapshot may be incomplete)"
else
    echo "ℹ️  No previous snapshot found - starting fresh" >> .claude/activity_stream.md
fi

# Update AGENT_STATE with new session
if [ -f .claude/AGENT_STATE.json ]; then
    python3 << 'PYTHON'
import json
from pathlib import Path
from datetime import datetime
import uuid

state_file = Path('.claude/AGENT_STATE.json')
if state_file.exists():
    with open(state_file) as f:
        state = json.load(f)

    state['session_id'] = str(uuid.uuid4())
    state['status'] = 'active'
    state['last_session_start'] = datetime.now().isoformat()

    with open(state_file, 'w') as f:
        json.dump(state, f, indent=2)
PYTHON
fi

# Return success
echo '{"status": "success", "message": "Session context restored"}'
exit 0

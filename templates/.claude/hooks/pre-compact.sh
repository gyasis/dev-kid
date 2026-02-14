#!/usr/bin/env bash
# PreCompact Hook - Emergency state backup before context compression
# CRITICAL: This fires BEFORE Claude compresses the conversation context

set -e

# Read stdin (hook receives event data here)
read -r EVENT_DATA

# Log the event
echo "🚨 PreCompact: Emergency state backup initiated" >> .claude/activity_stream.md
echo "   Timestamp: $(date -Iseconds)" >> .claude/activity_stream.md

# Emergency micro-checkpoint: Save AGENT_STATE
if [ -f .claude/AGENT_STATE.json ]; then
    cp .claude/AGENT_STATE.json ".claude/AGENT_STATE.backup.$(date +%Y%m%d_%H%M%S).json"
fi

# Update system bus with compression event
if [ -f .claude/system_bus.json ]; then
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
        'agent': 'pre-compact-hook',
        'event_type': 'context_compression_detected',
        'backup_created': True
    })

    with open(bus_file, 'w') as f:
        json.dump(bus, f, indent=2)
PYTHON
fi

# Auto-checkpoint if uncommitted changes exist
if command -v dev-kid &> /dev/null; then
    if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
        dev-kid checkpoint "[PRE-COMPACT] Auto-save before context compression" 2>/dev/null || true
    fi
fi

# Return success (allows compression to proceed)
echo '{"status": "success", "message": "State backed up before compression"}'
exit 0

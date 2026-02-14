# Context Compaction Strategy

**Proactive Pre-Compaction for Multi-Persona Workflows**

## Problem Statement

When 5+ personas/agents are active in Claude Code, token usage accelerates rapidly. If context compression happens **mid-wave**, state can be lost and debugging becomes difficult. We need to **control WHEN compression happens** - between waves, not during them.

## Solution: Proactive Pre-Compact

**Key Insight**: Our architecture (Memory Bank, AGENT_STATE.json, hooks) survives compression IF we trigger it at safe boundaries.

### Architecture

```
Wave N completes
    ↓
Checkpoint created (git commit)
    ↓
Context Compactor checks persona count
    ↓
If 5+ personas detected
    ↓
Trigger PreCompact hook proactively
    ↓
Hook backs up state to disk
    ↓
Context compresses (controlled timing)
    ↓
Wave N+1 starts with clean context
```

### Benefits

1. **Controlled Timing**: Compression happens between waves, not mid-wave
2. **Full State Backup**: PreCompact hook has complete context to save
3. **Debugging Possible**: Can inspect state before compression
4. **Prevents Mid-Wave Failures**: No task interruption

## Implementation

### Component: context_compactor.py

**Location**: `cli/context_compactor.py`

**Purpose**: Detects multi-persona workflows and triggers proactive pre-compaction

**Key Functions**:

```python
class ContextCompactor:
    def count_active_personas(self) -> int:
        """Count active personas from AGENT_STATE.json"""
        # Reads .claude/AGENT_STATE.json
        # Counts agents with status: active/running/in_progress

    def detect_task_tool_usage(self) -> int:
        """Count personas from Task tool usage (alternative)"""
        # Scans activity_stream.md for recent Task tool calls
        # Extracts unique subagent types

    def should_precompact(self) -> tuple[bool, int, str]:
        """Determine if pre-compaction needed"""
        # Returns (should_compact, persona_count, reason)
        # Threshold: 5+ personas

    def trigger_precompact(self, wave_id: int, persona_count: int) -> bool:
        """Trigger pre-compaction by running PreCompact hook"""
        # Executes .claude/hooks/pre-compact.sh
        # Passes event data via stdin
        # Logs to activity_stream.md and system_bus.json
```

### Integration with Wave Executor

**File**: `cli/wave_executor.py`

**Modified Section**:

```python
for wave in waves:
    wave_id = wave['wave_id']

    # Execute wave
    self.execute_wave(wave)

    # Checkpoint after wave
    if wave['checkpoint_after']['enabled']:
        self.execute_checkpoint(wave_id, wave['checkpoint_after'])

    # NEW: Proactive pre-compact check
    print(f"\n🔍 Checking context health before next wave...")
    self.compactor.check_and_trigger(wave_id)
```

**What Happens**:

1. Wave completes
2. Checkpoint created (state saved)
3. Compactor checks persona count
4. If 5+ personas: triggers PreCompact hook
5. Hook backs up state, creates emergency checkpoint
6. Context compresses (if needed)
7. Next wave starts fresh

## Detection Methods

### Method 1: AGENT_STATE.json

Reads `.claude/AGENT_STATE.json`:

```json
{
  "agents": {
    "python-pro": {"status": "active"},
    "sql-pro": {"status": "active"},
    "debugger": {"status": "running"},
    "frontend-developer": {"status": "in_progress"},
    "backend-architect": {"status": "active"}
  }
}
```

Counts agents with status: `active`, `running`, `in_progress`

**Result**: 5 personas detected → trigger pre-compact

### Method 2: Task Tool Usage

Scans `activity_stream.md` for recent Task tool invocations:

```markdown
### 2026-02-14 14:30:00 - Task tool: python-pro
### 2026-02-14 14:32:15 - Task tool: sql-pro
### 2026-02-14 14:35:20 - Task tool: debugger
### 2026-02-14 14:38:45 - Task tool: frontend-developer
### 2026-02-14 14:40:10 - Task tool: backend-architect
```

Extracts unique subagent types from last 20 lines.

**Result**: 5 unique personas detected → trigger pre-compact

### Combined Detection

```python
state_count = self.count_active_personas()      # Method 1
task_count = self.detect_task_tool_usage()      # Method 2
persona_count = max(state_count, task_count)    # Use max

if persona_count >= 5:
    trigger_precompact()
```

**Why Max?**: More conservative - catches personas either way

## Threshold: 5 Personas

**Why 5?**

1. **Claude Code Token Limit**: ~200k tokens
2. **Average Persona Overhead**: ~20k-40k tokens each
3. **5 Personas**: ~100k-200k tokens used
4. **Leaves Buffer**: Room for code context, conversation, tool outputs

**Tunable**: Can adjust via `ContextCompactor.persona_threshold`

## Example Workflow

### Scenario: Complex Full-Stack Feature

**Wave 1**: Database schema design
- **Personas**: sql-pro, database-admin
- **Count**: 2 personas
- **Action**: No pre-compact (below threshold)

**Wave 2**: Backend API implementation
- **Personas**: sql-pro, database-admin, backend-architect, python-pro, security-auditor
- **Count**: 5 personas
- **Action**: ✅ **Pre-compact triggered** between Wave 1 and Wave 2

**Output**:
```
✅ Wave 1 complete
🔍 Checkpoint after Wave 1...
   ✅ All tasks verified
   📝 Constitution validation passed
   💾 Git checkpoint created

🔍 Checking context health before next wave...
🔄 Proactive Pre-Compact Triggered
   Wave: 1
   Active personas: 5
   Reason: Multi-agent coordination requires context management
   ✅ Pre-compact successful
   💾 State backed up before potential compression

🌊 Starting Wave 2...
```

**Wave 3**: Frontend integration
- **Personas**: frontend-developer, backend-architect, test-automator
- **Count**: 3 personas (some dropped from previous waves)
- **Action**: No pre-compact (below threshold)

## PreCompact Hook Integration

When `context_compactor.py` triggers pre-compaction, it runs:

```bash
.claude/hooks/pre-compact.sh
```

**Event Data** (via stdin):
```json
{
  "event": "ProactivePreCompact",
  "wave_id": 1,
  "persona_count": 5,
  "timestamp": "2026-02-14T14:45:00Z",
  "trigger": "multi_persona_detection"
}
```

**Hook Actions**:
1. Backs up `AGENT_STATE.json` with timestamp
2. Updates `system_bus.json` with compression event
3. Creates emergency git checkpoint (if uncommitted changes)
4. Logs to `activity_stream.md`

**Result**: State fully persisted before compression

## Logging & Observability

### Activity Stream

```markdown
### 2026-02-14 14:45:00 - Proactive Pre-Compact
- Wave: 1
- Active personas: 5
- Trigger: Multi-agent coordination detected
- Action: State backup initiated before potential compression
```

### System Bus

```json
{
  "events": [
    {
      "timestamp": "2026-02-14T14:45:00Z",
      "agent": "context-compactor",
      "event_type": "proactive_precompact",
      "wave_id": 1,
      "persona_count": 5,
      "trigger": "multi_persona_detection"
    }
  ]
}
```

### Console Output

```
🔍 Checking context health before next wave...
🔄 Proactive Pre-Compact Triggered
   Wave: 1
   Active personas: 5
   Reason: Multi-agent coordination requires context management
   ✅ Pre-compact successful
   💾 State backed up before potential compression
```

## Testing

### Manual Test

```bash
# Test persona detection
cd /path/to/project
python3 cli/context_compactor.py count
# Output: Active personas: 0 (or actual count)

# Test pre-compact check
python3 cli/context_compactor.py check
# Output: Should pre-compact: False (or True)
#         Persona count: 0
#         Reason: Below threshold

# Manually trigger (for testing)
python3 cli/context_compactor.py trigger --wave-id 1
# Output: Runs PreCompact hook with wave_id=1
```

### Integration Test

```bash
# Create multi-persona scenario
echo '{"agents": {"p1": {"status": "active"}, "p2": {"status": "active"}, "p3": {"status": "active"}, "p4": {"status": "active"}, "p5": {"status": "active"}}}' > .claude/AGENT_STATE.json

# Run wave execution
dev-kid execute

# Observe pre-compact trigger
# Check activity_stream.md for log entry
tail -n 20 .claude/activity_stream.md | grep -i "pre-compact"
```

## Performance Impact

**Overhead per wave**: ~200-500ms

**Breakdown**:
- Persona detection: ~50ms (read AGENT_STATE.json + activity_stream.md)
- Hook execution: ~200ms (PreCompact hook runtime)
- Logging: ~50ms (activity_stream, system_bus updates)

**Total**: <500ms per wave (non-blocking between waves)

**Benefit**: Prevents mid-wave compression that could take 2-5 seconds and lose state

## Configuration

### Adjust Threshold

**File**: `cli/context_compactor.py`

```python
class ContextCompactor:
    def __init__(self):
        self.persona_threshold = 5  # Change this value
```

**Options**:
- `3`: More aggressive (pre-compact earlier)
- `7`: More conservative (allow more personas)
- `10`: Very conservative (rarely pre-compact)

### Disable Proactive Pre-Compact

**Option 1**: Environment variable (not yet implemented, future)
```bash
export DEV_KID_PROACTIVE_PRECOMPACT=false
```

**Option 2**: Comment out in wave_executor.py
```python
# self.compactor.check_and_trigger(wave_id)  # Disabled
```

## Edge Cases

### 1. Personas Dropped Between Waves

**Scenario**: Wave 1 has 6 personas, Wave 2 has 2 personas

**Behavior**: Pre-compact triggers after Wave 1 (6 > 5), but not after Wave 2 (2 < 5)

**Result**: ✅ Correct - compression only when needed

### 2. PreCompact Hook Missing

**Scenario**: `.claude/hooks/pre-compact.sh` doesn't exist

**Behavior**:
```
⚠️ PreCompact hook not found at .claude/hooks/pre-compact.sh
```

**Result**: Warning logged, execution continues (graceful degradation)

### 3. Hook Execution Fails

**Scenario**: PreCompact hook returns non-zero exit code

**Behavior**:
```
⚠️ Pre-compact hook returned: 1
<stderr output>
```

**Result**: Warning logged, execution continues (non-blocking failure)

### 4. No AGENT_STATE.json

**Scenario**: `.claude/AGENT_STATE.json` doesn't exist

**Behavior**: Falls back to Task tool detection from activity_stream.md

**Result**: ✅ Alternative detection method used

## Future Enhancements

1. **Token Usage Estimation**: Directly measure token usage instead of persona count
2. **User Notification**: Warn user before triggering pre-compact ("Context filling up - compacting...")
3. **Compression Stats**: Track how often pre-compact triggered, tokens saved
4. **Configurable Threshold**: Allow threshold to be set in `.devkid/config.json`
5. **Wave Complexity Scoring**: Weight waves by complexity (some waves need more context than others)

## References

- [Claude Code Hooks](HOOKS_REFERENCE.md#precompact-hook-critical)
- [Wave Executor](cli/wave_executor.py)
- [Context Compactor](cli/context_compactor.py)
- [AGENT_STATE.json Schema](templates/.claude/AGENT_STATE.json)

---

**Proactive pre-compaction ensures dev-kid's multi-persona workflows survive context compression by controlling WHEN it happens - between waves, not during them.**

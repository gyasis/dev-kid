---
name: Sync Memory Bank
description: Updates memory-bank with current project state, git history, and task progress
version: 1.0.0
triggers:
  - "sync memory"
  - "update memory bank"
  - "save context"
  - "after checkpoint"
parameters:
  - name: full_sync
    description: Perform full memory sync (all files) instead of incremental
    type: boolean
    required: false
    default: false
---

# Sync Memory Bank

**Purpose**: Keep memory-bank up to date with current project state, preserving institutional knowledge across sessions and context compression.

## Activation Logic

This skill activates when:
1. 📝 User message contains: "sync memory", "update memory", "save context"
2. 🎯 After major events: checkpoint, wave completion, session end
3. ⏱️ Periodically: After significant changes detected
4. 🔄 Manual: User explicitly requests memory update

## What This Skill Does

1. **Analyzes** git history for recent changes
2. **Parses** tasks.md for completion statistics
3. **Extracts** key decisions from commit messages
4. **Updates** memory-bank files:
   - `shared/systemPatterns.md` - Architecture patterns discovered
   - `shared/techContext.md` - Technology decisions made
   - `private/{user}/progress.md` - Task completion metrics
   - `private/{user}/activeContext.md` - Current focus
   - `private/{user}/worklog.md` - Daily work entries
5. **Appends** to activity_stream.md
6. **Preserves** institutional knowledge

## Execution

```bash
#!/bin/bash
set -e

# Parse parameters
FULL_SYNC="${1:-false}"

echo "💾 Syncing Memory Bank..."
echo ""

# Check if memory-bank exists
if [ ! -d "memory-bank" ]; then
    echo "⚠️  memory-bank/ not found - run dev-kid init first"
    exit 1
fi

# Determine sync type
if [ "$FULL_SYNC" = "true" ]; then
    echo "   Mode: Full sync (all files)"
else
    echo "   Mode: Incremental sync"
fi

echo ""

# Run sync
dev-kid sync-memory

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Memory Bank synchronized!"
    echo ""
    echo "📊 Updated files:"
    git status --short memory-bank/ | head -10
    echo ""
    echo "📋 Memory Bank contents:"
    echo "   Shared knowledge:"
    echo "      - projectbrief.md (vision)"
    echo "      - systemPatterns.md (architecture)"
    echo "      - techContext.md (decisions)"
    echo "   Personal context:"
    echo "      - progress.md (metrics)"
    echo "      - activeContext.md (focus)"
    echo "      - worklog.md (daily log)"
else
    echo ""
    echo "❌ Memory sync failed"
    exit 1
fi
```

## Memory Update Flow

```
1. Gather Context
   ├─ git log (recent commits)
   ├─ git diff (file changes)
   ├─ tasks.md (completion stats)
   └─ execution_plan.json (wave progress)

2. Analyze Changes
   ├─ Extract patterns (new architecture decisions)
   ├─ Identify tech choices (libraries added)
   ├─ Calculate metrics (tasks complete, time spent)
   └─ Detect blockers (incomplete tasks, errors)

3. Update Memory Bank
   ├─ shared/systemPatterns.md
   │  └─ Add new patterns discovered
   ├─ shared/techContext.md
   │  └─ Document tech decisions
   ├─ private/{user}/progress.md
   │  └─ Update completion metrics
   ├─ private/{user}/activeContext.md
   │  └─ Current focus and next actions
   └─ private/{user}/worklog.md
      └─ Append daily work entry

4. Log Event
   └─ .claude/activity_stream.md
      └─ Append sync event with timestamp
```

## Example Updates

### progress.md
```markdown
## Current Phase: Feature Implementation

### Task Statistics
- Total: 12 tasks
- Complete: 8 tasks (67%)
- In Progress: 2 tasks
- Pending: 2 tasks

### Wave Progress
- Wave 1: ✅ Complete (4 tasks)
- Wave 2: 🏗️ In Progress (3/4 tasks)
- Wave 3: ⏳ Pending

### Last Updated
2026-01-11 14:30:00 - Wave 2 checkpoint
```

### systemPatterns.md
```markdown
## Architecture Patterns

### Data Model Layer (Added: 2026-01-11)
- Using Pydantic BaseModel for all data models
- Type hints enforced at runtime
- Validation at model boundary
- Decision: Chosen for FastAPI integration

**Gotcha**: Pydantic v2 has breaking changes from v1
```

### activeContext.md
```markdown
## Current Focus

### Active Wave: 2
- Implementing UserService layer
- 3/4 tasks complete
- Next: UserService.update_user() method

### Blockers
- None

### Next Actions
1. Complete Wave 2 (UserService.update_user)
2. Checkpoint Wave 2
3. Start Wave 3 (API endpoints)
```

## Example Usage

### Auto-Sync After Checkpoint
```
Claude: ✅ Checkpoint created!
        💾 Syncing Memory Bank...

        Updated files:
        M  memory-bank/private/gyasis/progress.md
        M  memory-bank/shared/systemPatterns.md

        ✅ Memory Bank synchronized!
```

### Manual Sync
```
User: Sync the memory bank

Claude: 💾 Syncing Memory Bank...
        Mode: Incremental sync

        [Analyzes git history]
        [Updates progress metrics]
        [Extracts new patterns]

        ✅ Memory Bank synchronized!

        📊 Updates:
        - 2 new architecture patterns documented
        - Progress: 67% complete (8/12 tasks)
        - Current wave: 2 (in progress)
```

### Full Sync
```
User: Do a full memory sync

Claude: 💾 Syncing Memory Bank...
        Mode: Full sync (all files)

        [Regenerates all memory-bank files]
        [Comprehensive git analysis]
        [Full task statistics]

        ✅ Memory Bank synchronized!
```

## When to Sync

**Automatic triggers**:
- ✅ After each wave checkpoint
- ✅ After session finalize
- ✅ When significant changes detected (>10 files modified)

**Manual triggers**:
- 📝 User requests: "sync memory"
- 🎯 Before major context switch
- 💾 Before ending work session
- 🔄 After implementing major feature

## Integration with Dev-Kid

Memory Bank provides:
- 📚 **Persistent knowledge** across sessions
- 🧠 **Context for agents** (systemPatterns, techContext)
- 📊 **Progress tracking** (completion metrics)
- 🎯 **Focus management** (activeContext)
- 📝 **Work history** (worklog entries)

## Integration with Speckit

- Updates reflect current feature branch
- Progress tied to `.specify/specs/{branch}/` artifacts
- Constitution compliance tracked
- Feature-specific patterns documented

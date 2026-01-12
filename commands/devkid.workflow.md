---
name: devkid.workflow
description: Complete feature workflow guide from constitution to implementation using speckit and dev-kid integration
---

# Speckit + Dev-Kid Complete Workflow

Complete guide for feature development using speckit (planning) + dev-kid (execution).

## Workflow Overview

```
Constitution → Specify → Tasks → Orchestrate → Execute → Checkpoint → Sync
     ↓            ↓         ↓         ↓            ↓          ↓         ↓
  Rules      PRD       Linear    Waves      Code    Validate  Memory
```

## Quick Reference

| Command | Purpose | When |
|---------|---------|------|
| `/speckit.constitution` | Create rules | Once per project |
| `/speckit.specify "desc"` | Create feature spec | Per feature |
| `/speckit.tasks` | Generate tasks | After spec approved |
| `/devkid.orchestrate` | Create waves | After tasks generated |
| `/devkid.execute` | Run implementation | User initiated |
| `/devkid.checkpoint` | Validate & commit | Between waves |
| `/devkid.sync-memory` | Update knowledge | After checkpoint |

## Complete Workflow Steps

### Step 0: Constitution (One-Time Setup)

```bash
/speckit.constitution
```

Creates:
- `.specify/memory/constitution.md` (source)
- `memory-bank/shared/.constitution.md` (dev-kid copy)

Example rules:
- Use Pydantic BaseModel for data models
- Type hints required
- No threading.local
- Test coverage >80%

### Step 1: Specify Feature (Per Feature)

```bash
/speckit.specify "Add user authentication with OAuth2"
```

Creates:
- Branch: `001-user-auth`
- Spec: `.specify/specs/001-user-auth/spec.md`
- Checklist: `.specify/specs/001-user-auth/checklists/requirements.md`

Output: PRD with user stories, success criteria, constraints

### Step 2: Generate Tasks (After Spec Approved)

```bash
/speckit.tasks
```

Reads:
- `.specify/specs/001-user-auth/spec.md`
- `.specify/specs/001-user-auth/plan.md`

Creates:
- `.specify/specs/001-user-auth/tasks.md`

Git hook symlinks:
- `tasks.md` → `.specify/specs/001-user-auth/tasks.md`

Output: Linear task list with constitution rules embedded

### Step 3: Orchestrate into Waves

```bash
/devkid.orchestrate
```

Reads:
- `tasks.md` (symlinked to current branch's spec folder)

Creates:
- `execution_plan.json` (parallelized waves)

Output: PARALLEL_SWARM and SEQUENTIAL_MERGE wave groups

### Step 4: Execute Waves

```bash
/devkid.execute
```

Runs:
- `dev-kid watchdog-start`
- `dev-kid execute`

Does:
- Registers tasks with watchdog
- Executes waves sequentially
- Marks [x] in tasks.md
- Auto-checkpoints between waves

### Step 5: Checkpoint Validation (Between Waves)

```bash
/devkid.checkpoint
```

Validates:
- All wave tasks marked [x]
- Constitution compliance

Creates:
- Git commit
- Updates progress.md

### Step 6: Sync Memory (After Checkpoint)

```bash
/devkid.sync-memory
```

Updates:
- systemPatterns.md
- techContext.md
- progress.md
- activeContext.md
- worklog.md

## Example Session Flow

```
User: Start a new feature for user authentication with OAuth2

Claude: 🚀 Starting feature workflow...

        Step 1: Creating specification
        /speckit.specify "Add user authentication with OAuth2"

        ✅ Spec created: .specify/specs/001-user-auth/spec.md
        Branch: 001-user-auth

User: /speckit.tasks

Claude: ✅ Tasks generated: 12 tasks
        🌊 Auto-orchestrating into waves...

        Wave 1 (PARALLEL_SWARM): 4 tasks
        Wave 2 (SEQUENTIAL_MERGE): 3 tasks
        Wave 3 (PARALLEL_SWARM): 5 tasks

User: /devkid.execute

Claude: 🚀 Starting execution...
        🐕 Watchdog started

        🌊 Wave 1 (4 tasks)...
        ✅ T001 complete
        ✅ T002 complete
        ✅ T003 complete
        ✅ T004 complete

        🔍 Checkpoint Wave 1...
        ✅ All tasks complete
        ✅ Constitution compliant
        📝 Git commit created

        🌊 Wave 2 (3 tasks)...
        ...
```

## Switching Between Features

```bash
# On feature 001-user-auth
git checkout 002-payment-flow

# Git hook auto-relinks:
# tasks.md → .specify/specs/002-payment-flow/tasks.md

# Start workflow for new feature
Claude: 🔗 Linked to feature: 002-payment-flow
        📋 Tasks loaded for this branch

        Ready to orchestrate or continue existing work
```

## File Structure

```
project/
├── .specify/
│   ├── memory/constitution.md
│   └── specs/
│       ├── 001-user-auth/
│       │   ├── spec.md
│       │   ├── plan.md
│       │   ├── tasks.md
│       │   └── execution_plan.json
│       └── 002-payment-flow/
│           └── ...
├── memory-bank/
│   ├── shared/
│   │   └── .constitution.md
│   └── private/{user}/
│       ├── progress.md
│       ├── activeContext.md
│       └── worklog.md
└── tasks.md (symlink to current branch)
```

## Execution

This command displays the workflow guide above. No actual execution.

```bash
#!/bin/bash

cat << 'EOF'
========================================
Speckit + Dev-Kid Complete Workflow
========================================

See the complete guide above for:
1. Constitution creation
2. Feature specification
3. Task generation
4. Wave orchestration
5. Wave execution
6. Checkpoint validation
7. Memory synchronization

Quick Start:
1. /speckit.constitution (once per project)
2. /speckit.specify "Your feature description"
3. /speckit.tasks
4. /devkid.orchestrate
5. /devkid.execute
6. /devkid.checkpoint (auto or manual)
7. /devkid.sync-memory

For detailed documentation, see:
- skills/speckit-workflow.md
- DEV_KID.md
- ARCHITECTURE.md

EOF
```

## Integration with Speckit

- Constitution flows through entire pipeline
- Tasks inherit spec context
- Branch-based feature isolation
- Symlinked tasks.md for seamless integration

## Integration with Dev-Kid

- Orchestration parallelizes tasks
- Wave execution enforces constitution
- Checkpoints validate completion
- Memory bank preserves knowledge

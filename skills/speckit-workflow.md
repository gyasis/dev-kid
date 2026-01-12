---
name: Speckit + Dev-Kid Workflow
description: Complete feature workflow from constitution to implementation using speckit and dev-kid integration
version: 1.0.0
triggers:
  - "new feature workflow"
  - "start feature"
  - "full workflow"
  - "speckit workflow"
parameters:
  - name: feature_description
    description: Natural language feature description
    type: string
    required: false
---

# Speckit + Dev-Kid Complete Workflow

**Purpose**: Guide users through the complete feature development workflow using speckit (planning) + dev-kid (execution).

## Workflow Overview

```
Constitution → Specify → Tasks → Orchestrate → Execute → Checkpoint → Sync
     ↓            ↓         ↓         ↓            ↓          ↓         ↓
  Rules      PRD       Linear    Waves      Code    Validate  Memory
```

## What This Skill Does

Provides an interactive guide through the complete workflow:

1. **Constitution** - Define project rules (if not exists)
2. **Specify** - Create feature spec and branch
3. **Tasks** - Generate task breakdown
4. **Orchestrate** - Convert to parallelized waves
5. **Execute** - Implement with monitoring
6. **Checkpoint** - Validate and commit
7. **Sync** - Update memory-bank

## Execution

```bash
#!/bin/bash
set -e

FEATURE_DESC="${1:-}"

echo "🚀 Speckit + Dev-Kid Feature Workflow"
echo "======================================"
echo ""

# Step 0: Check if constitution exists
echo "Step 0: Constitution Check"
echo "--------------------------"
if [ ! -f "memory-bank/shared/.constitution.md" ]; then
    echo "⚠️  No constitution found"
    echo ""
    echo "📜 RECOMMENDED: Create project constitution first"
    echo "   Command: /speckit.constitution"
    echo ""
    read -p "Continue without constitution? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Workflow cancelled"
        echo "   Run /speckit.constitution first"
        exit 1
    fi
else
    echo "✅ Constitution exists"
fi
echo ""

# Step 1: Feature Specification
echo "Step 1: Feature Specification"
echo "-----------------------------"
if [ -z "$FEATURE_DESC" ]; then
    echo "📝 Feature description required"
    echo ""
    echo "Example workflow:"
    echo "   User: Start a new feature for user authentication with OAuth2"
    echo "   Claude: [Launches this workflow with description]"
    echo ""
    echo "📋 Next step:"
    echo "   Run: /speckit.specify 'Your feature description'"
    echo ""
    exit 0
else
    echo "Feature: $FEATURE_DESC"
    echo ""
    echo "📝 Creating specification..."
    echo "   Command: /speckit.specify '$FEATURE_DESC'"
    echo ""
    echo "⚠️  MANUAL STEP REQUIRED:"
    echo "   1. Run: /speckit.specify '$FEATURE_DESC'"
    echo "   2. Review the generated spec.md"
    echo "   3. Answer any clarification questions"
    echo "   4. Continue to Step 2"
    echo ""
    exit 0
fi
```

## Complete Workflow Guide

### Step 0: Constitution (One-Time Setup)
```
Command: /speckit.constitution

Creates:
- .specify/memory/constitution.md (source)
- memory-bank/shared/.constitution.md (dev-kid copy)

Example rules:
- Use Pydantic BaseModel for data models
- Type hints required
- No threading.local
- Test coverage >80%
```

### Step 1: Specify Feature (Per Feature)
```
Command: /speckit.specify "Add user authentication with OAuth2"

Creates:
- Branch: 001-user-auth
- Spec: .specify/specs/001-user-auth/spec.md
- Checklist: .specify/specs/001-user-auth/checklists/requirements.md

Output: PRD with user stories, success criteria, constraints
```

### Step 2: Generate Tasks (After Spec Approved)
```
Command: /speckit.tasks

Reads:
- .specify/specs/001-user-auth/spec.md
- .specify/specs/001-user-auth/plan.md

Creates:
- .specify/specs/001-user-auth/tasks.md

Git hook symlinks:
- tasks.md → .specify/specs/001-user-auth/tasks.md

Output: Linear task list with constitution rules embedded
```

### Step 3: Orchestrate into Waves (Auto-Triggered)
```
Skill: orchestrate-tasks.md

Triggers when:
- tasks.md exists
- execution_plan.json missing or outdated

Runs:
- dev-kid orchestrate "Feature Implementation"

Creates:
- execution_plan.json (parallelized waves)

Output: PARALLEL_SWARM and SEQUENTIAL_MERGE wave groups
```

### Step 4: Execute Waves (User Initiated)
```
Command: Execute the waves
Skill: execute-waves.md

Runs:
- dev-kid watchdog-start
- dev-kid execute

Does:
- Registers tasks with watchdog
- Executes waves sequentially
- Marks [x] in tasks.md
- Auto-checkpoints between waves
```

### Step 5: Checkpoint Validation (Auto Between Waves)
```
Skill: checkpoint-wave.md

Triggers:
- Wave completion detected
- User says "checkpoint"

Validates:
- All wave tasks marked [x]
- Constitution compliance

Creates:
- Git commit
- Updates progress.md
```

### Step 6: Sync Memory (After Checkpoint)
```
Skill: sync-memory.md

Triggers:
- After checkpoint
- User says "sync memory"

Updates:
- systemPatterns.md
- techContext.md
- progress.md
- activeContext.md
- worklog.md
```

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

User: Execute the waves

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

## Quick Reference

| Command | Purpose | When |
|---------|---------|------|
| `/speckit.constitution` | Create rules | Once per project |
| `/speckit.specify "desc"` | Create feature spec | Per feature |
| `/speckit.tasks` | Generate tasks | After spec approved |
| `dev-kid orchestrate` | Create waves | Auto after tasks |
| `dev-kid execute` | Run implementation | User initiated |
| `dev-kid checkpoint` | Validate & commit | Auto between waves |
| `dev-kid sync-memory` | Update knowledge | After checkpoint |

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

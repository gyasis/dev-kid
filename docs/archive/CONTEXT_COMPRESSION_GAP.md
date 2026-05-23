# Context Compression Within a Wave - Gap Analysis & Solution

## The Problem

**Scenario**:
```
Wave 1 has 10 tasks
After task 3: Context = 35% (smart zone)
After task 6: Context = 45% (DUMB ZONE!)  ← Problem!
After task 10: Context would be 70%+ (severe degradation)
```

**Current flaw**: We only checkpoint BETWEEN waves, not WITHIN waves.

## Why This Is Critical

Ralph principle: Stay in first 30-40% of context (smart zone).

If wave has many tasks:
- Task 1-3: Smart zone ✅
- Task 4-6: Crossing into dumb zone ⚠️
- Task 7-10: Deep in dumb zone ❌ (poor quality work)

**Result**: Later tasks in wave suffer from degraded LLM performance!

## Solution: Micro-Wave Checkpoints

### Strategy 1: Auto-Detect Mid-Wave (Recommended)

Add context budget check DURING wave execution:

```python
# cli/wave_executor.py
def execute_wave_tasks(wave):
    for i, task in enumerate(wave['tasks'], 1):
        # Execute task
        execute_task(task)
        
        # Mark complete in tasks.md
        mark_task_complete(task['id'])
        
        # CRITICAL: Check context budget after each task
        context_check = check_context_budget()
        
        if context_check['level'] in ['critical', 'severe']:
            print(f"🚨 Context budget critical after task {i}/{len(wave['tasks'])}")
            print(f"   Creating mid-wave checkpoint to reset context...")
            
            # Micro-checkpoint
            subprocess.run(['dev-kid', 'micro-checkpoint', f'Mid-wave checkpoint (task {i})'])
            
            # Update progress
            update_progress(f"Paused wave at task {i}/{len(wave['tasks'])} - context reset needed")
            
            print(f"")
            print(f"✅ Mid-wave checkpoint created")
            print(f"   Completed: {i}/{len(wave['tasks'])} tasks")
            print(f"   Remaining: {len(wave['tasks']) - i} tasks")
            print(f"")
            print(f"⚠️  EXIT THIS SESSION NOW")
            print(f"   Run: dev-kid execute-wave {wave['wave_id']} --continue")
            print(f"   (Fresh context, resumes from task {i+1})")
            
            sys.exit(0)  # Force exit for fresh context
```

### Strategy 2: Task Count Threshold

Add to config.json:
```json
{
  "task_orchestration": {
    "wave_size": 7,
    "max_tasks_per_session": 5  ← New setting
  }
}
```

If wave has >5 tasks:
1. Execute tasks 1-5
2. Micro-checkpoint
3. Exit session
4. Resume with tasks 6-N in fresh context

### Strategy 3: Manual Mid-Wave Checkpoint

Agent can call anytime:
```bash
# During wave execution, if feeling context bloat:
dev-kid micro-checkpoint "Mid-wave save"
dev-kid finalize
# Exit session
dev-kid recall
dev-kid execute-wave 1 --continue
```

## Implementation Plan

### Phase 1: Add Resume Capability to Wave Executor

```python
# cli/wave_executor.py
def execute_wave(wave_id: int, resume: bool = False):
    """Execute wave with resume support"""
    wave = load_wave(wave_id)
    
    if resume:
        # Find last completed task in tasks.md
        completed_tasks = get_completed_task_ids()
        remaining_tasks = [t for t in wave['tasks'] if t['id'] not in completed_tasks]
        print(f"📋 Resuming wave {wave_id}")
        print(f"   Completed: {len(completed_tasks)}")
        print(f"   Remaining: {len(remaining_tasks)}")
        tasks_to_execute = remaining_tasks
    else:
        tasks_to_execute = wave['tasks']
    
    for i, task in enumerate(tasks_to_execute, 1):
        execute_task(task)
        mark_task_complete(task['id'])
        
        # Auto context check (every 3 tasks)
        if i % 3 == 0:
            context_check = check_context_budget()
            if context_check['percentage'] > 35:
                print(f"⚠️  Context: {context_check['percentage']}% - recommend micro-checkpoint")
            if context_check['percentage'] > 40:
                # Force mid-wave checkpoint
                create_mid_wave_checkpoint(wave_id, i, len(tasks_to_execute))
                sys.exit(0)  # Exit for fresh context
```

### Phase 2: Update CLI to Support Resume

```bash
# cli/dev-kid
cmd_execute_wave() {
    local wave_id="$1"
    local resume_flag=""
    
    if [ "$2" = "--continue" ] || [ "$2" = "--resume" ]; then
        resume_flag="--resume"
    fi
    
    python3 "$DEV_KID_ROOT/cli/wave_executor.py" --wave "$wave_id" $resume_flag
}
```

### Phase 3: Add Context Monitoring Hook

Create pre-task hook in wave executor:
```python
def before_task_hook(task_index: int, total_tasks: int):
    """Run before each task in wave"""
    context = check_context_budget()
    
    print(f"📊 Task {task_index}/{total_tasks} - Context: {context['percentage']}% {context['status']}")
    
    # Auto micro-checkpoint every 3 tasks (preventive)
    if task_index > 0 and task_index % 3 == 0:
        if context['percentage'] > 25:  # Approaching 30% threshold
            print(f"   💾 Preventive micro-checkpoint (every 3 tasks)")
            subprocess.run(['dev-kid', 'micro-checkpoint', '--auto'])
    
    # Force checkpoint if critical
    if context['level'] in ['critical', 'severe']:
        create_mid_wave_checkpoint(...)
        sys.exit(0)
```

## Recommended Workflow

### Before (No Mid-Wave Protection)
```
Wave 1: 10 tasks
[Execute all 10 in one session]
Context: 0% → 15% → 30% → 45% → 70%  ← Quality degrades!
Checkpoint after wave complete
```

### After (With Mid-Wave Protection)
```
Wave 1: 10 tasks

Session 1:
- Execute tasks 1-5
- Context: 0% → 15% → 30% → 35%
- Auto mid-wave checkpoint (context = 35%)
- EXIT

Session 2 (Fresh context):
- Resume wave 1 from task 6
- Execute tasks 6-10
- Context: 0% → 10% → 20% → 30%
- Checkpoint after wave complete
```

**Result**: All tasks executed in smart zone! ✅

## Configuration

Add to `.devkid/config.json`:
```json
{
  "ralph_optimization": {
    "context_budget": {
      "optimal_threshold": 0.30,
      "warning_threshold": 0.35,
      "critical_threshold": 0.40
    },
    "auto_checkpoint": {
      "enabled": true,
      "check_frequency": 3,  // Check every 3 tasks
      "force_at_percentage": 40
    },
    "mid_wave_resume": {
      "enabled": true,
      "preserve_state": "tasks.md + git"
    }
  }
}
```

## Benefits

✅ **Stay in Smart Zone**: Never exceed 40% context within wave
✅ **Automatic Protection**: Auto-detects and checkpoints when needed
✅ **Seamless Resume**: Fresh context, pick up where left off
✅ **No Manual Intervention**: System handles it automatically
✅ **Quality Maintained**: All tasks executed with peak LLM performance

## Next Steps

1. ✅ Add `--resume` flag to wave executor
2. ✅ Implement `check_context_budget()` integration
3. ✅ Add mid-wave checkpoint logic
4. ✅ Update CLI commands
5. ✅ Document in systemPatterns.md

---

**Status**: Gap identified and solution designed. Ready to implement!

# System Patterns: Dev-Kid v2.0

## Architectural Patterns

### 1. Wave-Based Orchestration Pattern

**Problem**: Linear task execution wastes time when tasks could run in parallel

**Solution**: Automatic wave analysis with file lock detection

```
tasks.md → Parse Tasks → Analyze Dependencies → Group into Waves → Execute
                           ↓
                    File Lock Detection
                    Explicit Dependencies
                    Greedy Wave Assignment
```

**Implementation**:
- `orchestrator.py`: O(n²) dependency analysis
- File paths extracted via regex (prioritizes backtick convention)
- Tasks affecting same file cannot be in same wave
- Explicit dependencies create sequential constraints

**Key Decision**: Greedy algorithm over optimal scheduling (trades optimality for predictability)

### 2. Checkpoint Protocol Pattern

**Problem**: Wave execution needs verification before progression

**Solution**: Mandatory checkpoint between waves

```
Execute Wave → Verify Completion → Update Progress → Git Commit → Next Wave
                     ↓ FAIL
                   HALT
```

**Implementation**:
- `verify_wave_completion()`: Checks tasks.md for [x] markers
- Halts execution if ANY task incomplete
- Only proceeds after verification passes
- Git commit creates verifiable history

**Key Decision**: Fail-safe over fail-fast (prevents silent failures)

### 3. Process-Based Monitoring Pattern

**Problem**: Context compression destroys token-based state

**Solution**: Background daemon with disk-persisted state

```
Task Start → Watchdog Records → Background Monitor → State File
                                       ↓ 5min check
                                 Sync with tasks.md
                                       ↓
                                 Detect Completion
```

**Implementation**:
- `task_watchdog.py`: Independent Python process
- State in `.claude/task_timers.json`
- Syncs with tasks.md for auto-detection
- Survives context compression

**Key Decision**: Process-based over token-based (resilient to compression)

### 4. Memory Bank Pattern

**Problem**: Institutional knowledge lost between sessions

**Solution**: 6-tier persistent knowledge architecture

```
Shared Knowledge (Team)
├── projectbrief.md      - Project identity
├── productContext.md    - Why project exists
├── systemPatterns.md    - Architecture decisions
└── techContext.md       - Technologies & setup

Private Knowledge (Per-User)
├── activeContext.md     - Current focus
├── progress.md          - What works/what's left
└── worklog.md           - Activity log
```

**Implementation**:
- Markdown files for human readability
- Git-versioned for history
- Auto-updated via sync-memory skill
- Hierarchy builds context progressively

**Key Decision**: Markdown over database (human-readable, git-compatible)

### 5. Constitution Enforcement Pattern

**Problem**: Quality standards only enforced manually

**Solution**: Automated enforcement throughout pipeline

```
Orchestrate → Check Constitution → Execute → Check Constitution → Checkpoint
     ↓                                ↓                              ↓
Constitution.md              Constitution.md                  Constitution.md
```

**Implementation**:
- Constitution.md defines standards
- Orchestrator checks before wave creation
- Executor checks during execution
- Checkpoint validates compliance

**Key Decision**: Declarative standards over imperative checks (flexible, auditable)

### 6. Dual Interface Pattern

**Problem**: Users need both automation and control

**Solution**: Auto-triggering skills + manual commands

```
Auto-Trigger Path (Skills)
tasks.md exists → orchestrate-tasks.md activates → Auto-orchestrate

Manual Control Path (Commands)
User types /devkid.orchestrate → Manual orchestration
```

**Implementation**:
- Skills in ~/.claude/skills/ (Claude Code auto-loads)
- Commands in ~/.claude/commands/ (slash command interface)
- Same underlying Python modules
- Different activation mechanisms

**Key Decision**: Dual interface over single (flexibility + automation)

## Design Patterns

### File Lock Detection

```python
def extract_file_paths(task_description: str) -> set[str]:
    # Priority 1: Backtick convention
    backtick_files = re.findall(r'`([^`]+\.[a-z]+)`', task_description)

    # Priority 2: General file patterns
    general_files = re.findall(r'\b([a-zA-Z0-9_/-]+\.[a-z]+)\b', task_description)

    return set(backtick_files + general_files)
```

**Pattern**: Progressive extraction with priority ordering

### Verification Protocol

```python
def verify_wave_completion(wave_id: str) -> bool:
    tasks = parse_tasks_md()
    wave_tasks = get_wave_tasks(wave_id)

    for task in wave_tasks:
        if not task.completed:
            print(f"❌ Task {task.id} incomplete")
            return False

    print(f"✅ Wave {wave_id} verified")
    return True
```

**Pattern**: All-or-nothing validation (fail-safe)

### State Persistence

```python
def save_state(state: dict):
    state_file = Path('.claude/task_timers.json')
    state_file.parent.mkdir(exist_ok=True)

    with state_file.open('w') as f:
        json.dump(state, f, indent=2)
```

**Pattern**: Atomic file writes with directory creation

### Dependency Analysis

```python
def analyze_dependencies(tasks: list[Task]) -> dict[str, set[str]]:
    dependencies = defaultdict(set)

    for task in tasks:
        # Explicit dependencies
        deps = extract_explicit_deps(task.description)
        dependencies[task.id].update(deps)

        # File lock dependencies
        for other_task in tasks:
            if task.id != other_task.id:
                if file_conflict(task, other_task):
                    dependencies[task.id].add(other_task.id)

    return dependencies
```

**Pattern**: Multi-source dependency aggregation

## Integration Patterns

### Speckit Integration

**Branch-Based Isolation**:
```bash
# Git post-checkout hook
if [ -f ".specify/specs/$NEW_BRANCH/tasks.md" ]; then
    ln -sf ".specify/specs/$NEW_BRANCH/tasks.md" tasks.md
fi
```

**Pattern**: Symlink redirection based on branch context

### Constitution Integration

**Pipeline Enforcement**:
```python
def orchestrate_with_constitution():
    constitution = load_constitution()
    tasks = parse_tasks()

    # Pre-orchestration check
    if not check_tasks_compliance(tasks, constitution):
        raise ConstitutionViolation()

    waves = create_waves(tasks)

    # Post-orchestration check
    if not check_waves_compliance(waves, constitution):
        raise ConstitutionViolation()

    return waves
```

**Pattern**: Pre/post validation hooks

## Data Flow Patterns

### Task Lifecycle

```
tasks.md (Markdown)
    ↓ parse
Task Objects (Python)
    ↓ analyze
Dependency Graph
    ↓ group
Wave Objects
    ↓ serialize
execution_plan.json
    ↓ execute
Git Commits
```

### Memory Bank Update Flow

```
Git Diff → Extract Changes → Update activeContext.md
Git Log → Extract Commits → Update progress.md
Tasks Stats → Calculate Progress → Update progress.md
Patterns → Document Insights → Update systemPatterns.md
    ↓
Append to activity_stream.md
```

### Watchdog Monitoring Flow

```
Task Start → Record in task_timers.json
    ↓ every 5min
Check Duration → Compare to tasks.md
    ↓ if complete
Move to completed_tasks
    ↓ if >7min
Add to warnings
```

## Error Handling Patterns

### Graceful Degradation

```python
try:
    waves = orchestrate_tasks()
except FileNotFoundError:
    print("❌ tasks.md not found")
    print("ℹ️  Create tasks.md to begin")
    sys.exit(1)
```

**Pattern**: Clear error messages with actionable next steps

### State Recovery

```python
def recover_watchdog_state():
    try:
        with open('.claude/task_timers.json') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'running_tasks': {}, 'completed_tasks': {}}
```

**Pattern**: Default empty state on corruption

## Performance Patterns

### Lazy File Reading

```python
@lru_cache(maxsize=1)
def get_tasks():
    return parse_tasks_md()
```

**Pattern**: Cache frequently-read files

### Incremental Updates

```python
def update_activity_stream(event: str):
    with open('.claude/activity_stream.md', 'a') as f:
        f.write(f"\n{timestamp()}: {event}")
```

**Pattern**: Append-only logs avoid full rewrites

## Security Patterns

### Safe Git Operations

```bash
# Never force push or hard reset
git add .
git commit -m "Message"  # No --force, no --amend
```

**Pattern**: Conservative git operations

### Path Validation

```python
def safe_path(path: str) -> Path:
    p = Path(path).resolve()
    if not p.is_relative_to(Path.cwd()):
        raise SecurityError("Path outside project")
    return p
```

**Pattern**: Prevent path traversal attacks

## Testing Patterns

### Idempotent Skills

```bash
# Skills can run multiple times safely
dev-kid sync-memory  # Safe to run repeatedly
dev-kid checkpoint   # Checks if changes exist first
```

**Pattern**: Idempotent operations prevent double-application

### Verification Before Mutation

```python
def execute_wave(wave_id: str):
    if not verify_prerequisites(wave_id):
        return False

    # Only mutate after verification
    result = perform_execution(wave_id)

    if not verify_result(result):
        rollback()
        return False

    return True
```

**Pattern**: Verify → Mutate → Verify

## Evolution Patterns

### Backward Compatibility

```python
# Support old and new JSON schemas
if 'execution_plan' in data:
    # New format
    return data['execution_plan']
else:
    # Legacy format
    return migrate_to_new_format(data)
```

**Pattern**: Graceful schema migration

### Feature Flags

```bash
# Constitution enforcement can be disabled
if [ -f "Constitution.md" ]; then
    enforce_constitution
fi
```

**Pattern**: Optional features via file presence

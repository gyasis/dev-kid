# Technical Context: Dev-Kid v2.0

## Technology Stack

### Core Technologies

**Bash**
- Version: 4.0+ (tested on 5.x)
- Usage: CLI routing, skills, git hooks
- Rationale: Universal availability, git integration, simple scripting

**Python**
- Version: 3.10+
- Usage: Orchestration, execution, watchdog
- Dependencies: Standard library only (json, pathlib, dataclasses, re, subprocess, datetime)
- Rationale: Type safety, rich standard library, maintainability

**Git**
- Version: 2.0+
- Usage: Checkpointing, hooks, history
- Rationale: Universal version control, verifiable history

**Markdown**
- Usage: Documentation, memory bank, tasks
- Rationale: Human-readable, git-compatible, Claude Code native

### System Dependencies

```bash
# Required
bash >= 4.0
python3 >= 3.10
git >= 2.0

# Optional (for enhanced features)
jq          # JSON processing in bash scripts
tree        # Directory visualization
```

### Installation Locations

```
~/.dev-kid/               # System installation
├── cli/                  # Python modules & bash CLI
├── skills/               # Original skill scripts
├── commands/             # Original command scripts
└── templates/            # Memory bank templates

~/.claude/                # Claude Code integration
├── skills/               # Auto-triggering skills (symlinked)
└── commands/             # Slash commands (symlinked)

/usr/local/bin/           # System PATH
└── dev-kid               # Symlink to ~/.dev-kid/cli/dev-kid
```

## Development Environment

### Required Tools

```bash
# Development
python3     # Core language
bash        # Scripting
git         # Version control

# Testing
shellcheck  # Bash linting
pylint      # Python linting
pytest      # Unit testing (future)

# Documentation
markdown    # Docs preview
```

### Environment Variables

```bash
# Optional configuration
NO_COLOR=1              # Disable color output
DEV_KID_DEBUG=1         # Enable debug logging
CONSTITUTION_PATH=...   # Custom constitution file location
```

## System Architecture

### Component Layers

```
┌─────────────────────────────────────┐
│   Claude Code Interface             │
│   (Skills + Commands)               │
├─────────────────────────────────────┤
│   CLI Layer (Bash)                  │
│   - Route commands                  │
│   - User feedback                   │
├─────────────────────────────────────┤
│   Core Logic (Python)               │
│   - Orchestrator                    │
│   - Executor                        │
│   - Watchdog                        │
├─────────────────────────────────────┤
│   State Management                  │
│   - Git (commits)                   │
│   - JSON (execution plans, state)   │
│   - Markdown (memory bank, tasks)   │
├─────────────────────────────────────┤
│   File System                       │
│   - .claude/ (context protection)   │
│   - memory-bank/ (knowledge)        │
│   - .git/ (history)                 │
└─────────────────────────────────────┘
```

### Data Formats

**JSON Schemas**

execution_plan.json:
```json
{
  "execution_plan": {
    "phase_id": "string",
    "waves": [
      {
        "wave_id": "W001",
        "strategy": "PARALLEL_SWARM",
        "rationale": "...",
        "tasks": [
          {
            "task_id": "T001",
            "description": "...",
            "files_affected": ["file1.py"]
          }
        ],
        "checkpoint_after": {
          "message": "...",
          "verification_required": true
        }
      }
    ]
  }
}
```

task_timers.json:
```json
{
  "running_tasks": {
    "T001": {
      "description": "...",
      "started_at": "2025-01-12T10:00:00Z",
      "status": "running"
    }
  },
  "completed_tasks": {},
  "warnings": []
}
```

**Markdown Conventions**

tasks.md:
```markdown
## Wave 1
- [ ] T001: Task description affecting `file1.py`
- [x] T002: Completed task
```

Constitution.md:
```markdown
# Constitution

## Quality Standards
- Rule 1
- Rule 2
```

## File Organization

### Project Structure

```
dev-kid/
├── cli/                          # Core implementation
│   ├── dev-kid                   # Bash CLI entry point
│   ├── orchestrator.py           # Wave orchestration
│   ├── wave_executor.py          # Wave execution
│   └── task_watchdog.py          # Background monitoring
├── skills/                       # Auto-triggering skills
│   ├── orchestrate-tasks.md      # Auto-orchestrate
│   ├── execute-waves.md          # Auto-execute
│   ├── checkpoint-wave.md        # Auto-checkpoint
│   ├── sync-memory.md            # Auto-sync memory
│   └── speckit-workflow.md       # Workflow guide
├── commands/                     # Slash commands
│   ├── devkid.orchestrate.md     # Manual orchestrate
│   ├── devkid.execute.md         # Manual execute
│   ├── devkid.checkpoint.md      # Manual checkpoint
│   ├── devkid.sync-memory.md     # Manual sync
│   └── devkid.workflow.md        # Workflow display
├── scripts/                      # Installation & init
│   ├── install.sh                # System install
│   ├── verify-install.sh         # Install verification
│   └── init.sh                   # Project initialization
├── templates/                    # Memory bank templates
│   └── memory-bank/              # Template files
├── docs/                         # Documentation
│   ├── architecture/             # Architecture docs
│   ├── reference/                # API, CLI, skills reference
│   ├── development/              # Contributing, dependencies
│   ├── constitution/             # Constitution docs
│   ├── speckit-integration/      # Integration docs
│   └── testing/                  # Test reports
├── memory-bank/                  # Institutional memory
│   ├── projectbrief.md
│   ├── productContext.md
│   ├── activeContext.md
│   ├── systemPatterns.md
│   ├── techContext.md
│   └── progress.md
├── .claude/                      # Context protection (per-project)
│   ├── active_stack.md
│   ├── activity_stream.md
│   ├── task_timers.json
│   └── session_snapshots/
└── .git/                         # Version control
    └── hooks/
        └── post-checkout         # Branch sync automation
```

### State Files

**.claude/ (Context Protection)**
- `active_stack.md`: Current focus (<500 tokens)
- `activity_stream.md`: Append-only event log
- `task_timers.json`: Watchdog state
- `AGENT_STATE.json`: Agent coordination
- `system_bus.json`: Inter-agent messaging
- `session_snapshots/*.json`: Recovery points

**Project Root**
- `tasks.md`: Current task list (Speckit-synced symlink)
- `execution_plan.json`: Wave execution plan
- `Constitution.md`: Quality standards (optional)

## Integration Points

### Claude Code Integration

**Skills (Auto-Trigger)**
- Location: ~/.claude/skills/
- Activation: File condition matching
- Format: Markdown with trigger patterns
- Example: "When tasks.md exists, orchestrate automatically"

**Commands (Manual)**
- Location: ~/.claude/commands/
- Activation: User types /devkid.*
- Format: Markdown with execution blocks
- Example: "/devkid.orchestrate triggers manual orchestration"

### Git Integration

**Hooks**
- `post-checkout`: Auto-sync tasks.md when switching branches
- `post-commit`: Append to activity_stream.md (optional)

**Commit Strategy**
- One commit per wave completion
- Semantic commit messages
- Verification before commit

### Speckit Integration

**File Locations**
- Specs: `.specify/specs/{branch}/`
- Tasks: `.specify/specs/{branch}/tasks.md`
- Symlink: `tasks.md → .specify/specs/{branch}/tasks.md`

**Branch Isolation**
- Each branch has independent task list
- Progress preserved across switches
- Constitution shared across branches

## Performance Characteristics

### Time Complexity

**Orchestration**
- Task parsing: O(n) where n = number of tasks
- Dependency analysis: O(n²) worst case
- Wave assignment: O(n²) greedy algorithm
- File lock detection: O(n×m) where m = avg file paths per task

**Execution**
- Wave verification: O(n) per wave
- Checkpoint creation: O(1) git operation
- Memory bank update: O(1) file writes

**Watchdog**
- State check: O(1) JSON read
- Task sync: O(n) task comparison
- Background loop: 5-minute intervals

### Space Complexity

**Memory Usage**
- Python processes: ~10-20MB each
- State files: <1MB typical
- Memory bank: <100KB per tier
- Git commits: ~1KB per checkpoint

**Disk Usage**
- Installation: ~500KB
- Per-project: ~1MB (.claude/ + memory-bank/)
- Git history: Variable (depends on project size)

## Constraints & Limitations

### Technical Constraints

**Python Version**
- Requires 3.10+ for dataclasses and type hints
- Standard library only (no pip dependencies)

**Git Requirement**
- Project must be git-initialized
- Checkpointing requires git repository

**File System**
- Requires POSIX-compliant filesystem
- Symlinks must be supported (Speckit integration)

**Process Management**
- Watchdog requires background process support
- Signal handling for graceful shutdown

### Design Constraints

**Token Efficiency**
- Skills must activate with minimal token overhead
- Memory bank updates must be incremental
- Context protection files <500 tokens each

**Reproducibility**
- Same workflow must work across projects
- No project-specific configuration
- Zero-configuration installation

**Safety**
- Verification before progression (fail-safe)
- No destructive git operations (no force, no hard reset)
- Clear error messages with next steps

## Security Considerations

### Input Validation

```python
# Path traversal prevention
def safe_path(path: str) -> Path:
    p = Path(path).resolve()
    if not p.is_relative_to(Path.cwd()):
        raise SecurityError()
    return p
```

### Git Safety

```bash
# Conservative git operations only
git add .              # OK
git commit -m "..."    # OK
git push --force       # NEVER
git reset --hard       # NEVER
```

### State File Protection

```python
# Atomic writes with temp files
def atomic_write(file_path: Path, content: str):
    temp = file_path.with_suffix('.tmp')
    temp.write_text(content)
    temp.replace(file_path)
```

## Troubleshooting

### Common Issues

**Skills not activating**
- Check ~/.claude/skills/ exists
- Verify skill files are readable
- Check trigger patterns match file conditions

**Git hooks not firing**
- Ensure .git/hooks/post-checkout is executable
- Check hook doesn't have syntax errors
- Verify git version >= 2.0

**Watchdog process stuck**
- Kill manually: `pkill -f task_watchdog.py`
- Check .claude/task_timers.json for corruption
- Restart with `dev-kid watchdog-start`

**Wave execution halts**
- Check tasks.md for unmarked completions
- Verify all tasks have [x] markers
- Review verification error messages

## Future Technical Considerations

### Scalability

**Large Task Lists**
- Current O(n²) algorithm sufficient for <1000 tasks
- Consider optimization if >1000 tasks common

**Multi-Repository**
- Current single-repo design
- Future: orchestrate across multiple repos

### Advanced Features

**Performance Monitoring**
- Track wave execution times
- Identify bottlenecks
- Optimize file lock detection

**Analytics Dashboard**
- Visualize progress over time
- Identify patterns in task execution
- Constitution compliance metrics

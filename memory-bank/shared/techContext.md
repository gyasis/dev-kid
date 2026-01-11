# Technical Context: Dev-Kid v2.0

## Technology Stack

### Core Technologies

#### Bash 4.0+
**Purpose**: CLI entry point, skills layer, system integration

**Usage**:
- Main CLI router (`cli/dev-kid`)
- All skills (`skills/*.sh`)
- Installation and initialization scripts

**Rationale**:
- Universal availability on Unix systems
- Fast startup time
- Excellent for file operations and git integration
- Easy subprocess management

**Constraints**:
- Limited data structure support (mitigated by delegation to Python)
- Harder to test (mitigated by simple, focused scripts)

#### Python 3.7+
**Purpose**: Orchestration engine, complex logic, data processing

**Usage**:
- Task orchestrator (`cli/orchestrator.py`)
- Wave executor (`cli/wave_executor.py`)
- Task watchdog daemon (`cli/task_watchdog.py`)
- Constitution parser (`cli/constitution_parser.py`) - NEW: SpecKit integration
- Constitution manager (`cli/constitution_manager.py`)
- Config manager (`cli/config_manager.py`)

**Standard Library Modules**:
- `json`: State file parsing/generation
- `pathlib`: Path manipulation
- `dataclasses`: Task and Wave objects
- `re`: Regex for dependency extraction
- `subprocess`: Git commands
- `datetime`: Timestamp handling
- `sys`, `os`: System operations

**Rationale**:
- No external dependencies (universal installation)
- Type hints for maintainability
- Better data structures than Bash
- Easier unit testing

**Constraints**:
- Requires Python 3.7+ (typing features, dataclasses)
- No pip packages allowed (zero-config principle)

#### Rust 1.70+
**Purpose**: High-performance task watchdog with process-based monitoring

**Usage**:
- Rust watchdog daemon (`rust-watchdog/src/main.rs`)
- Task registry with constitution support (`rust-watchdog/src/types.rs`)
- Process-based monitoring (survives context compression)

**Key Features**:
- Constitution rules storage in process registry
- 'register' subcommand for task registration with metadata
- JSON-RPC 2.0 API for CLI integration
- Context-resilient state management

**Rationale**:
- Performance: Low memory overhead, fast startup
- Reliability: Process-based, survives context compression
- Type safety: Rust's type system prevents state corruption

**SpecKit Integration** (2026-01-10):
- TaskInfo struct extended with `constitution_rules` field
- Constitution rules persist across context compression
- Integration with Python constitution_parser.py

#### Git 2.0+
**Purpose**: Version control, checkpoints, history tracking

**Usage**:
- Semantic checkpoints after each wave
- Post-commit hooks for activity logging
- History analysis for Memory Bank updates
- Rollback capability

**Key Commands**:
```bash
git add .
git commit -m "[CHECKPOINT-W1] Wave 1 complete"
git diff --stat
git log --oneline -10
git rev-parse --short HEAD
```

**Rationale**:
- Universal in development environments
- Natural fit for checkpoint pattern
- Provides audit trail
- Enables rollback to any wave

**Constraints**:
- Requires git initialization in project
- No support for non-git projects (deliberate limitation)

#### jq 1.5+
**Purpose**: JSON parsing and manipulation in Bash scripts

**Usage**:
- Parse execution_plan.json in skills
- Extract fields from state files
- Validate JSON structure

**Example**:
```bash
wave_count=$(jq '.execution_plan.waves | length' execution_plan.json)
task_id=$(jq -r '.running_tasks | keys[0]' .claude/task_timers.json)
```

**Rationale**:
- Standard tool for JSON in shell scripts
- Powerful query language
- Lightweight and fast

**Constraints**:
- Additional dependency (checked during install)

### File Formats

#### Markdown (.md)
**Purpose**: Memory Bank, documentation, human-readable state

**Structure**:
```markdown
# Title
## Section
- List item
### Subsection
[Link](url)
```

**Used In**:
- Memory Bank files (all shared and private)
- Documentation (README, DEV_KID, etc.)
- Active Stack and Activity Stream

**Rationale**:
- Human-readable and editable
- Git-friendly (line-based diffs)
- AI-friendly (Claude can parse and generate)
- Universal format (no lock-in)

#### JSON (.json)
**Purpose**: Structured state, execution plans, coordination

**Schema Examples**:

**execution_plan.json**:
```json
{
  "execution_plan": {
    "phase_id": "Phase 1",
    "waves": [
      {
        "wave_id": 1,
        "strategy": "PARALLEL_SWARM",
        "rationale": "Independent file modifications",
        "tasks": [
          {
            "id": "T001",
            "description": "Task description",
            "agent_role": "Developer",
            "file_locks": ["src/file.py"]
          }
        ],
        "checkpoint_after": {
          "enabled": true,
          "message": "Wave 1 complete"
        }
      }
    ]
  }
}
```

**task_timers.json**:
```json
{
  "running_tasks": {
    "TASK-001": {
      "description": "Task description",
      "started_at": "2026-01-10T10:30:00Z",
      "last_checked": "2026-01-10T10:35:00Z",
      "status": "running"
    }
  },
  "completed_tasks": {},
  "warnings": []
}
```

**Used In**:
- Execution plans
- State files (AGENT_STATE, system_bus, task_timers)
- Session snapshots
- Constitution and config files

**Rationale**:
- Structured and machine-parseable
- Universal format across languages
- Easy schema validation
- Human-readable when formatted

## Directory Structure

### Installation Layout

```
~/.dev-kid/                         # Installation root
├── cli/
│   ├── dev-kid                     # Bash CLI (chmod +x)
│   ├── orchestrator.py             # Python module
│   ├── wave_executor.py            # Python module
│   ├── task_watchdog.py            # Python module
│   ├── constitution_manager.py     # Python module
│   └── config_manager.py           # Python module
├── skills/
│   ├── sync_memory.sh              # Bash script (chmod +x)
│   ├── checkpoint.sh               # Bash script (chmod +x)
│   ├── verify_existence.sh         # Bash script (chmod +x)
│   ├── maintain_integrity.sh       # Bash script (chmod +x)
│   ├── finalize_session.sh         # Bash script (chmod +x)
│   └── recall.sh                   # Bash script (chmod +x)
├── scripts/
│   ├── install.sh                  # Installation script
│   └── init.sh                     # Project initialization
└── templates/
    ├── memory-bank/                # Memory Bank templates
    │   ├── shared/
    │   │   ├── projectbrief.md
    │   │   ├── systemPatterns.md
    │   │   ├── techContext.md
    │   │   └── productContext.md
    │   └── private/
    │       └── activeContext.md.template
    └── .claude/                    # Context Protection templates
        ├── active_stack.md
        ├── activity_stream.md
        ├── AGENT_STATE.json
        └── system_bus.json

~/.claude/skills/planning-enhanced/  # Claude Code skills location
├── sync_memory.sh -> ~/.dev-kid/skills/sync_memory.sh
├── checkpoint.sh -> ~/.dev-kid/skills/checkpoint.sh
└── ... (symlinks to all skills)

/usr/local/bin/dev-kid -> ~/.dev-kid/cli/dev-kid  # PATH entry
```

### Project Layout (Post-Initialization)

```
project-root/
├── memory-bank/
│   ├── shared/
│   │   ├── projectbrief.md
│   │   ├── systemPatterns.md
│   │   ├── techContext.md
│   │   └── productContext.md
│   └── private/$USER/
│       ├── activeContext.md
│       ├── progress.md
│       └── worklog.md
├── .claude/
│   ├── active_stack.md
│   ├── activity_stream.md
│   ├── AGENT_STATE.json
│   ├── system_bus.json
│   ├── task_timers.json
│   └── session_snapshots/
│       ├── snapshot_latest.json -> snapshot_TIMESTAMP.json
│       └── snapshot_TIMESTAMP.json
├── .git/
│   └── hooks/
│       └── post-commit
├── tasks.md
├── execution_plan.json
└── (project files)
```

## Development Environment

### Required Tools

#### Bash
- **Version**: 4.0+ (for associative arrays)
- **Check**: `bash --version`
- **Installation**: Pre-installed on most Unix systems

#### Python
- **Version**: 3.7+ (for dataclasses, typing features)
- **Check**: `python3 --version`
- **Installation**:
  - Ubuntu/Debian: `sudo apt install python3`
  - macOS: `brew install python3`
  - Arch: `sudo pacman -S python`

#### Git
- **Version**: 2.0+ (for modern commands)
- **Check**: `git --version`
- **Installation**:
  - Ubuntu/Debian: `sudo apt install git`
  - macOS: `brew install git` or Xcode Command Line Tools
  - Arch: `sudo pacman -S git`

#### jq
- **Version**: 1.5+
- **Check**: `jq --version`
- **Installation**:
  - Ubuntu/Debian: `sudo apt install jq`
  - macOS: `brew install jq`
  - Arch: `sudo pacman -S jq`

### Recommended Tools

#### sed, grep
- **Purpose**: Text processing in skills
- **Check**: `sed --version`, `grep --version`
- **Installation**: Pre-installed on most Unix systems

### Platform Support

#### Fully Supported
- **Linux**: All distributions with Bash 4+
- **macOS**: 10.14+ (Mojave and later)

#### Limited Support
- **WSL**: Windows Subsystem for Linux (tested on WSL2)
- **BSD**: Should work but not actively tested

#### Not Supported
- **Windows**: Native Windows not supported (use WSL)
- **Mobile**: iOS, Android not applicable

## Build and Installation

### Installation Process

```bash
# 1. Clone repository
git clone https://github.com/yourusername/planning-with-files.git
cd planning-with-files

# 2. Run installer
./scripts/install.sh

# What it does:
# - Checks dependencies (bash, python3, git, jq)
# - Creates ~/.dev-kid/ structure
# - Copies CLI and Python modules
# - Copies skills to ~/.dev-kid/skills/
# - Creates symlinks in ~/.claude/skills/planning-enhanced/
# - Creates symlink /usr/local/bin/dev-kid (requires sudo)
# - Sets executable permissions
# - Displays success message

# 3. Verify installation
dev-kid version
dev-kid status
```

### Project Initialization

```bash
# Initialize in existing project
cd your-project
dev-kid init

# What it does:
# - Creates memory-bank/ structure from templates
# - Creates .claude/ structure
# - Installs git post-commit hook
# - Creates initial tasks.md template
# - Displays setup instructions
```

### Uninstallation

```bash
# Remove global installation
rm -rf ~/.dev-kid
rm -rf ~/.claude/skills/planning-enhanced
sudo rm /usr/local/bin/dev-kid

# Remove from project (careful - deletes Memory Bank!)
cd your-project
rm -rf memory-bank/ .claude/ tasks.md execution_plan.json
rm .git/hooks/post-commit
```

## Configuration

### Zero Configuration Philosophy

Dev-kid has NO configuration files by design. All behavior is determined by:
1. **Project structure**: Presence of memory-bank/, .claude/, tasks.md
2. **Git state**: Commit history, working tree status
3. **File content**: tasks.md format, execution_plan.json schema

### Customization Points

#### 1. Task Descriptions
Control wave assignment through explicit dependencies:
```markdown
- [ ] Task A
- [ ] Task B (after Task A)
- [ ] Task C (depends on Task B)
```

#### 2. Wave Strategy
Edit execution_plan.json to change strategy:
```json
{
  "wave_id": 1,
  "strategy": "SEQUENTIAL_MERGE"  // Force sequential execution
}
```

#### 3. Checkpoint Messages
Control git commit messages through checkpoint calls:
```bash
dev-kid checkpoint "Feature complete: user authentication"
```

#### 4. Memory Bank Content
Edit Markdown files directly to customize context:
- `projectbrief.md`: Update vision and goals
- `systemPatterns.md`: Document new patterns
- `activeContext.md`: Set current focus

## Constraints and Limitations

### Technical Constraints

#### Platform Limitations
- **Unix-only**: Requires Bash, not portable to native Windows
- **Git-required**: No support for non-git projects
- **Python 3.7+**: Won't work on older Python versions

#### Scale Limitations
- **Task count**: O(n²) algorithm, practical limit ~1000 tasks
- **Wave count**: Sequential execution, not parallelized across machines
- **Watchdog tasks**: 5-minute check interval, not real-time

#### Design Constraints
- **No external dependencies**: Python standard library only
- **No network calls**: All operations local
- **No database**: File-based state only
- **No GUI**: CLI-only interface

### Operational Constraints

#### File System Requirements
- **Write access**: To project root, ~/.dev-kid, ~/.claude
- **Executable permissions**: For CLI and skills
- **Symlink support**: For /usr/local/bin/dev-kid

#### Git Requirements
- **Initialized repository**: `git init` must be run
- **Write access**: To .git/hooks/
- **No empty repo**: At least one commit for some operations

#### User Requirements
- **CLI familiarity**: Comfortable with terminal
- **Git knowledge**: Understanding of commits, branches, diffs
- **Markdown knowledge**: Able to edit Memory Bank files

## Development Setup

### For Contributors

```bash
# Clone repository
git clone https://github.com/yourusername/planning-with-files.git
cd planning-with-files

# Install in development mode (no symlink to /usr/local/bin)
export PATH="$PWD/cli:$PATH"

# Run tests (future)
pytest cli/test_orchestrator.py
pytest cli/test_wave_executor.py
pytest cli/test_task_watchdog.py

# Test in sample project
mkdir /tmp/test-project
cd /tmp/test-project
git init
dev-kid init
```

### Testing Tools

#### Manual Testing
```bash
# Test CLI commands
dev-kid status
dev-kid orchestrate "Test Phase"
dev-kid watchdog-start
dev-kid watchdog-check
dev-kid watchdog-stop

# Test skills directly
~/.dev-kid/skills/sync_memory.sh
~/.dev-kid/skills/checkpoint.sh "Test"
```

#### Python Module Testing
```bash
# Test orchestrator
python3 cli/orchestrator.py --tasks-file tasks.md --phase-id "Test"

# Test wave executor
python3 cli/wave_executor.py

# Test task watchdog
python3 cli/task_watchdog.py start-task T001 "Test task"
python3 cli/task_watchdog.py check
```

## Performance Characteristics

### Startup Time
- **CLI command**: <100ms (Bash interpreter overhead)
- **Orchestrator**: ~200ms (Python import + parsing)
- **Wave executor**: ~150ms (JSON loading)
- **Watchdog check**: ~100ms (state file I/O)

### Resource Usage
- **Memory**: <50MB for typical operations
- **CPU**: Minimal (mostly I/O bound)
- **Disk**: ~1-10MB for Memory Bank + state files

### Scalability
- **Small projects** (<100 tasks): Instant orchestration
- **Medium projects** (100-500 tasks): <2s orchestration
- **Large projects** (500-1000 tasks): <5s orchestration
- **Very large projects** (>1000 tasks): May need optimization

## Security Considerations

### No Elevated Privileges Required
- Skills run as user, no sudo
- File operations in user-owned directories
- Git operations as user

### Path Safety
- All paths validated before operations
- No arbitrary command execution
- Skills are predefined, not dynamic

### Data Privacy
- No network calls (all operations local)
- No telemetry or analytics
- Git history contains all changes (review before push)

### Safe Git Operations
- No force operations
- No destructive resets
- Verification before commits

---

**Technical Context v2.0** - Technology stack, environment setup, and constraints for dev-kid

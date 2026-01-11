# Contributing to Dev-Kid

**Version**: 2.0.0
**Last Updated**: 2026-01-05

Thank you for your interest in contributing to dev-kid! This guide will help you understand the project structure, development workflow, and contribution guidelines.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Setup](#development-setup)
3. [Project Structure](#project-structure)
4. [Adding New Commands](#adding-new-commands)
5. [Creating New Skills](#creating-new-skills)
6. [Testing Procedures](#testing-procedures)
7. [Code Style Guidelines](#code-style-guidelines)
8. [Submitting Changes](#submitting-changes)
9. [Release Process](#release-process)

---

## Getting Started

### Prerequisites

**Required**:
- Bash 4.0+ (macOS: install via Homebrew)
- Python 3.8+ with standard library
- Git 2.0+
- jq (JSON processor)

**Optional**:
- pytest (for Python tests)
- bats (for Bash tests)
- shellcheck (for shell linting)

### Fork and Clone

```bash
# Fork repository on GitHub first, then:
git clone https://github.com/YOUR_USERNAME/planning-with-files.git
cd planning-with-files/dev-kid
```

### Development Installation

```bash
# Install in development mode (symlinks to your working directory)
./scripts/install.sh --dev

# This creates symlinks instead of copies:
# /usr/local/bin/dev-kid -> ~/dev/planning-with-files/dev-kid/cli/dev-kid
# ~/.claude/skills/planning-enhanced/*.sh -> ~/dev/planning-with-files/dev-kid/skills/*.sh

# Now edits to your working directory are immediately active
```

---

## Development Setup

### Environment Configuration

Create `.env` in dev-kid root (not committed):

```bash
# Development settings
DEV_MODE=1
VERBOSE=1
DRY_RUN=0

# Test project path
TEST_PROJECT_PATH=~/dev/test-project
```

### Editor Setup

**VS Code** (`.vscode/settings.json`):
```json
{
  "files.associations": {
    "*.sh": "shellscript"
  },
  "shellcheck.enable": true,
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true
}
```

**Vim** (`.vimrc`):
```vim
autocmd FileType sh setlocal expandtab shiftwidth=4 softtabstop=4
autocmd FileType python setlocal expandtab shiftwidth=4 softtabstop=4
```

### Code Checks

```bash
# Bash linting
shellcheck cli/dev-kid
shellcheck skills/*.sh

# Python linting
pylint cli/orchestrator.py
pylint cli/wave_executor.py
pylint cli/task_watchdog.py

# Python type checking
mypy cli/orchestrator.py
mypy cli/wave_executor.py
mypy cli/task_watchdog.py
```

---

## Project Structure

```
dev-kid/
├── cli/                      # Command-line interface
│   ├── dev-kid              # Main CLI (bash) - command routing
│   ├── orchestrator.py      # Task orchestration engine
│   ├── wave_executor.py     # Wave execution engine
│   └── task_watchdog.py     # Background task monitor
│
├── skills/                   # Workflow automation scripts
│   ├── sync_memory.sh       # Memory Bank sync
│   ├── checkpoint.sh        # Git checkpoint
│   ├── verify_existence.sh  # Anti-hallucination
│   ├── maintain_integrity.sh # System validation
│   ├── finalize_session.sh  # Session snapshot
│   └── recall.sh            # Session recovery
│
├── scripts/                  # Installation and setup
│   ├── install.sh           # Global installation
│   └── init.sh              # Per-project initialization
│
├── templates/                # File templates
│   ├── memory-bank/         # Memory Bank templates
│   └── .claude/             # Context Protection templates
│
├── tests/                    # Test suite
│   ├── test_orchestrator.py  # Orchestrator tests
│   ├── test_wave_executor.py # Wave executor tests
│   ├── test_watchdog.py      # Watchdog tests
│   └── skills/               # Skill tests
│       ├── test_checkpoint.bats
│       └── test_sync_memory.bats
│
└── docs/                     # Documentation
    ├── ARCHITECTURE.md       # System architecture
    ├── CLI_REFERENCE.md      # CLI command reference
    ├── API.md                # Python API reference
    ├── SKILLS_REFERENCE.md   # Skills documentation
    └── CONTRIBUTING.md       # This file
```

---

## Adding New Commands

### 1. Define Command Function

Edit `cli/dev-kid`:

```bash
cmd_new_command() {
    local arg1="${1}"
    local arg2="${2:-default}"

    echo -e "${GREEN}🎯 Executing new command${NC}"

    # Validate inputs
    if [ -z "$arg1" ]; then
        echo -e "${RED}❌ Error: arg1 required${NC}"
        exit 1
    fi

    # Implementation
    # Option A: Call Python script
    python3 "$DEV_KID_ROOT/cli/new_script.py" --arg "$arg1"

    # Option B: Call skill
    "$DEV_KID_ROOT/skills/new_skill.sh" "$arg1"

    # Option C: Direct bash implementation
    echo "Processing $arg1..."
    # ... logic here ...

    echo -e "${GREEN}✅ Command complete${NC}"
}
```

### 2. Add to Command Dispatcher

In `main()` function:

```bash
case "$command" in
    init)           cmd_init "$@" ;;
    orchestrate)    cmd_orchestrate "$@" ;;
    # ... existing commands ...
    new-command)    cmd_new_command "$@" ;;  # ADD HERE
    help|-h|--help) show_help ;;
    *)
        echo -e "${RED}❌ Unknown command: $command${NC}"
        exit 1
        ;;
esac
```

### 3. Update Help Text

In `show_help()` function:

```bash
cat << EOF

CORE COMMANDS:
  init [PATH]              Initialize dev-kid in project
  # ... existing commands ...
  new-command ARG1 [ARG2]  Description of new command

EOF
```

### 4. Document the Command

Add to `CLI_REFERENCE.md`:

```markdown
### `new-command`

Description of the command.

#### Synopsis

\`\`\`bash
dev-kid new-command ARG1 [ARG2]
\`\`\`

#### Arguments

- `ARG1` (required): Description
- `ARG2` (optional): Description (default: value)

#### Examples

\`\`\`bash
dev-kid new-command value1
dev-kid new-command value1 value2
\`\`\`
```

### 5. Add Tests

Create `tests/test_new_command.bats`:

```bash
#!/usr/bin/env bats

@test "new-command with valid args" {
    run dev-kid new-command test-arg
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Command complete" ]]
}

@test "new-command without required arg" {
    run dev-kid new-command
    [ "$status" -eq 1 ]
    [[ "$output" =~ "Error: arg1 required" ]]
}
```

---

## Creating New Skills

### 1. Create Skill Script

Create `skills/new_skill.sh`:

```bash
#!/usr/bin/env bash
# Skill: New Skill Name
# Trigger: keyword1, keyword2, condition
# Description: What this skill does

set -e

echo "🎯 Executing new skill..."

# Get script directory (for calling other skills)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- Configuration ---
TARGET_FILE="${1:-default.txt}"
USER=$(whoami)

# --- Validation ---
if [ ! -f "$TARGET_FILE" ]; then
    echo "❌ Error: Target file not found: $TARGET_FILE"
    exit 1
fi

# --- Implementation ---

# Read current state
if [ -f ".claude/new_state.json" ]; then
    CURRENT_STATE=$(cat .claude/new_state.json)
else
    CURRENT_STATE="{}"
fi

# Perform operations
NEW_DATA=$(some_processing "$TARGET_FILE")

# Update state
cat > .claude/new_state.json << EOF
{
  "timestamp": "$(date -Iseconds)",
  "target": "$TARGET_FILE",
  "data": "$NEW_DATA"
}
EOF

# Call other skills if needed
if [ -f "$SCRIPT_DIR/sync_memory.sh" ]; then
    "$SCRIPT_DIR/sync_memory.sh"
fi

# --- Output ---
echo "✅ New skill complete"
echo "   Processed: $TARGET_FILE"
```

### 2. Make Executable

```bash
chmod +x skills/new_skill.sh
```

### 3. Add CLI Command

In `cli/dev-kid`:

```bash
cmd_new_skill() {
    local target="${1:-default.txt}"
    echo -e "${GREEN}🎯 Running new skill${NC}"
    "$DEV_KID_ROOT/skills/new_skill.sh" "$target"
}

# In main() dispatcher:
case "$command" in
    # ...
    new-skill) cmd_new_skill "$@" ;;
esac
```

### 4. Document the Skill

Add to `SKILLS_REFERENCE.md`:

```markdown
### new_skill.sh

Description of the skill.

#### Metadata

**File**: `~/.dev-kid/skills/new_skill.sh`
**Triggers**: "keyword1", "keyword2"
**Dependencies**: jq, grep
**Runtime**: ~1 second

#### Purpose

What this skill accomplishes.

#### Input

**Arguments**:
- `$1` (optional): Target file (default: "default.txt")

#### Output

**Files Modified**:
- `.claude/new_state.json`

**stdout**:
\`\`\`
🎯 Executing new skill...
✅ New skill complete
   Processed: target.txt
\`\`\`

#### Usage Examples

\`\`\`bash
new_skill.sh custom.txt
\`\`\`
```

### 5. Add Tests

Create `tests/skills/test_new_skill.bats`:

```bash
#!/usr/bin/env bats

setup() {
    # Create test environment
    mkdir -p test-project
    cd test-project
    dev-kid init
}

teardown() {
    # Cleanup
    cd ..
    rm -rf test-project
}

@test "new_skill creates state file" {
    echo "test data" > input.txt
    run ~/.dev-kid/skills/new_skill.sh input.txt
    [ "$status" -eq 0 ]
    [ -f ".claude/new_state.json" ]
}

@test "new_skill with missing file fails" {
    run ~/.dev-kid/skills/new_skill.sh missing.txt
    [ "$status" -eq 1 ]
    [[ "$output" =~ "not found" ]]
}
```

---

## Testing Procedures

### Unit Tests (Python)

```bash
# Run all Python tests
pytest tests/

# Run specific test file
pytest tests/test_orchestrator.py

# Run with coverage
pytest --cov=cli tests/

# Run specific test
pytest tests/test_orchestrator.py::TestTaskOrchestrator::test_parse_tasks
```

**Example test**:

```python
# tests/test_orchestrator.py
import pytest
from pathlib import Path
from orchestrator import TaskOrchestrator, Task

def test_parse_tasks():
    """Test task parsing from tasks.md"""
    # Create test tasks.md
    test_file = Path("test_tasks.md")
    test_file.write_text("""
# Tasks

- [ ] Task 1 with `file1.py`
- [x] Task 2 completed
- [ ] Task 3 depends on T001
    """)

    # Parse
    orchestrator = TaskOrchestrator(str(test_file))
    orchestrator.parse_tasks()

    # Assertions
    assert len(orchestrator.tasks) == 3
    assert orchestrator.tasks[0].id == "T001"
    assert orchestrator.tasks[0].completed == False
    assert "file1.py" in orchestrator.tasks[0].file_locks
    assert orchestrator.tasks[1].completed == True
    assert "T001" in orchestrator.tasks[2].dependencies

    # Cleanup
    test_file.unlink()
```

### Integration Tests (Bash)

```bash
# Run all bash tests
bats tests/skills/*.bats

# Run specific test file
bats tests/skills/test_checkpoint.bats

# Verbose output
bats -t tests/skills/test_sync_memory.bats
```

**Example test**:

```bash
# tests/skills/test_checkpoint.bats
#!/usr/bin/env bats

setup() {
    # Create test project
    export TEST_DIR=$(mktemp -d)
    cd "$TEST_DIR"
    git init
    dev-kid init
}

teardown() {
    # Cleanup
    cd /
    rm -rf "$TEST_DIR"
}

@test "checkpoint creates git commit" {
    # Make some changes
    echo "test" > test.txt
    git add test.txt

    # Create checkpoint
    run dev-kid checkpoint "Test checkpoint"

    # Verify
    [ "$status" -eq 0 ]
    [[ "$output" =~ "Checkpoint created" ]]

    # Check git log
    run git log -1 --oneline
    [[ "$output" =~ "[CHECKPOINT] Test checkpoint" ]]
}

@test "checkpoint with no changes" {
    # No changes made
    run dev-kid checkpoint "No changes"

    # Should succeed but not create commit
    [ "$status" -eq 0 ]
    [[ "$output" =~ "No changes to commit" ]]
}
```

### Manual Testing Checklist

Before submitting PR:

- [ ] Install on clean system
- [ ] Initialize test project
- [ ] Run all CLI commands
- [ ] Test orchestration workflow
- [ ] Test task watchdog (start/stop/check/report)
- [ ] Test all skills
- [ ] Test session finalize/recall
- [ ] Verify git commits
- [ ] Validate JSON output
- [ ] Check Memory Bank updates
- [ ] Test error cases

### Test Coverage Goals

- **Python modules**: >80% coverage
- **Skills**: 100% of core paths
- **CLI commands**: All commands tested
- **Error cases**: Critical errors tested

---

## Code Style Guidelines

### Bash Style

**General**:
- Use 4 spaces for indentation (no tabs)
- Maximum line length: 100 characters
- Use `set -e` at the top of scripts
- Quote all variables: `"$var"` not `$var`

**Functions**:
```bash
# Good
function_name() {
    local arg1="$1"
    local arg2="${2:-default}"

    echo "Processing $arg1"
    return 0
}

# Avoid
function_name()
{
  arg1=$1  # Unquoted, global
  echo Processing $arg1  # Unquoted
}
```

**Conditionals**:
```bash
# Good
if [ -f "$file" ]; then
    echo "File exists"
elif [ -d "$file" ]; then
    echo "Directory exists"
else
    echo "Not found"
fi

# Good (for strings)
if [[ "$var" == "value" ]]; then
    echo "Match"
fi
```

**Error Handling**:
```bash
# Always check critical operations
if ! git commit -m "message"; then
    echo "❌ Commit failed"
    exit 1
fi

# Or use set -e and ignore non-critical failures
set -e
git commit -m "message" || true  # OK if nothing to commit
```

**Variable Naming**:
- `GLOBAL_VARS` in UPPER_CASE
- `local_vars` in lower_case
- `readonly CONSTANTS` in UPPER_CASE

### Python Style

**Follow PEP 8**:
```bash
# Check style
pylint cli/orchestrator.py
black --check cli/
```

**Type Hints**:
```python
# Good
def parse_tasks(self, file_path: str) -> List[Task]:
    """Parse tasks from file"""
    tasks: List[Task] = []
    return tasks

# Avoid
def parse_tasks(self, file_path):
    tasks = []
    return tasks
```

**Docstrings**:
```python
def create_waves(self) -> None:
    """Group tasks into execution waves.

    Uses greedy algorithm to assign tasks to earliest possible wave
    while respecting dependency and file lock constraints.

    Raises:
        SystemExit: If circular dependency detected
    """
    # Implementation...
```

**Class Structure**:
```python
@dataclass
class Task:
    """Represents a single task.

    Attributes:
        id: Unique task identifier (e.g., "T001")
        description: Task text from tasks.md
        file_locks: List of files this task modifies
    """
    id: str
    description: str
    file_locks: List[str] = field(default_factory=list)
```

### JSON Style

**Formatting**:
```json
{
  "key": "value",
  "nested": {
    "indent": "2 spaces"
  },
  "array": [
    "item1",
    "item2"
  ]
}
```

**Generated JSON**:
```python
import json

# Good
with open("output.json", "w") as f:
    json.dump(data, f, indent=2)

# Avoid
with open("output.json", "w") as f:
    json.dump(data, f)  # No formatting
```

### Documentation Style

**Markdown**:
- Use ATX-style headers (`# Header` not `Header\n======`)
- Code blocks with language: \`\`\`bash not \`\`\`
- Bullet lists: `-` not `*`
- Numbered lists: `1.` `2.` `3.` (not all `1.`)

**Comments**:
```bash
# Good: Explain WHY not WHAT
# Cache result to avoid re-parsing on subsequent calls
cache_result "$data"

# Avoid: States the obvious
# Call cache_result function
cache_result "$data"
```

---

## Submitting Changes

### Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feature/new-command
   ```

2. **Make changes with commits**:
   ```bash
   git add cli/dev-kid
   git commit -m "Add new-command to CLI

   - Implements new-command function
   - Adds help text
   - Includes error handling"
   ```

3. **Test thoroughly**:
   ```bash
   # Run all tests
   pytest tests/
   bats tests/skills/*.bats

   # Manual testing
   dev-kid validate
   dev-kid new-command test-arg
   ```

4. **Update documentation**:
   ```bash
   # Update relevant docs
   vim CLI_REFERENCE.md
   vim SKILLS_REFERENCE.md  # If skill added
   vim ARCHITECTURE.md  # If architecture changed
   ```

5. **Create checkpoint**:
   ```bash
   dev-kid checkpoint "Feature complete: new-command"
   ```

6. **Push and create PR**:
   ```bash
   git push origin feature/new-command
   # Create PR on GitHub
   ```

### Commit Message Format

```
Type: Brief description (50 chars or less)

More detailed explanation (72 chars per line):
- What changed
- Why the change was needed
- How it works

Refs: #123 (issue number if applicable)
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance (build, dependencies)

**Examples**:
```
feat: Add task-complete command to CLI

Implements task-complete command that marks running tasks
as complete in the watchdog state. Includes validation and
timing calculation.

Refs: #45
```

```
fix: Handle missing tasks.md in sync_memory.sh

sync_memory.sh now checks if tasks.md exists before
attempting to parse progress. Prevents error when run
in projects without tasks.md.

Refs: #67
```

### Pull Request Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] `dev-kid validate` passes
- [ ] All tests pass (`pytest`, `bats`)
- [ ] Code follows style guidelines
- [ ] Commits are well-formatted

## Testing

Describe testing performed:
- Unit tests: ...
- Integration tests: ...
- Manual testing: ...

## Screenshots (if applicable)

Paste relevant output or screenshots.
```

### Review Process

1. **Automated checks**: CI runs tests and linting
2. **Code review**: Maintainer reviews code
3. **Discussion**: Address feedback, make changes
4. **Approval**: Maintainer approves PR
5. **Merge**: Maintainer merges to main branch

---

## Release Process

### Version Numbering

Follow Semantic Versioning (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes (e.g., 2.0.0 → 3.0.0)
- **MINOR**: New features, backward compatible (e.g., 2.0.0 → 2.1.0)
- **PATCH**: Bug fixes (e.g., 2.0.0 → 2.0.1)

### Release Checklist

1. **Update version**:
   ```bash
   # Update VERSION in cli/dev-kid
   VERSION="2.1.0"

   # Update docs
   sed -i 's/Version: 2.0.0/Version: 2.1.0/g' docs/*.md
   ```

2. **Update CHANGELOG**:
   ```markdown
   ## [2.1.0] - 2026-01-15

   ### Added
   - New command: `dev-kid new-command`
   - Task watchdog auto-recovery feature

   ### Changed
   - Improved orchestrator performance (30% faster)

   ### Fixed
   - Bug in checkpoint.sh with large files
   ```

3. **Run full test suite**:
   ```bash
   pytest tests/
   bats tests/skills/*.bats
   shellcheck cli/dev-kid skills/*.sh
   ```

4. **Create release commit**:
   ```bash
   git add .
   git commit -m "chore: Release v2.1.0"
   ```

5. **Tag release**:
   ```bash
   git tag -a v2.1.0 -m "Release v2.1.0

   - New task completion command
   - Performance improvements
   - Bug fixes"
   ```

6. **Push to GitHub**:
   ```bash
   git push origin main --tags
   ```

7. **Create GitHub release**:
   - Go to Releases on GitHub
   - Draft new release
   - Select tag v2.1.0
   - Add release notes from CHANGELOG
   - Publish release

---

## Getting Help

### Documentation

- **Architecture**: See `ARCHITECTURE.md`
- **CLI Reference**: See `CLI_REFERENCE.md`
- **API Reference**: See `API.md`
- **Skills**: See `SKILLS_REFERENCE.md`

### Communication

- **Issues**: GitHub Issues for bugs, feature requests
- **Discussions**: GitHub Discussions for questions, ideas
- **Email**: [maintainer email] for sensitive issues

### Resources

- **Bash Guide**: https://mywiki.wooledge.org/BashGuide
- **Python PEP 8**: https://peps.python.org/pep-0008/
- **Semantic Versioning**: https://semver.org/
- **Conventional Commits**: https://www.conventionalcommits.org/

---

**Thank you for contributing to dev-kid!**

Your contributions help make development with Claude Code more efficient and reliable for everyone.

**Contributing Guide v2.0.0**

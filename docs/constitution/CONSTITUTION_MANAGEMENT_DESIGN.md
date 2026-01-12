# Constitution Management System Design

**Team Orchestrator Analysis**: Multiple Agent Coordination

---

## Question 1: Is there currently a dev-kid command for constitution?

**🔍 Evidence Agent Report:**
- ✅ Searched cli/dev-kid: NO constitution command exists
- ✅ Available commands: init, orchestrate, execute, watchdog, checkpoint, etc.
- ✅ Constitution mentioned in DEVELOPER_TRAINING_GUIDE.md but no tooling
- ❌ NO config.json file exists in project
- ❌ NO constitution management in skills/

**Conclusion**: Gap identified - constitution is critical but has no tooling!

---

## Question 2: Should this be CLI Command OR Claude Code Skill?

**🎨 UX Designer Agent Analysis:**

### Option A: CLI Command (`dev-kid constitution`)
**Pros:**
- Consistent with existing dev-kid commands
- Works offline (no Claude Code needed)
- Fast execution (bash script)
- Integrates naturally with `dev-kid init`

**Cons:**
- Less intelligent (template-based only)
- No AI assistance for writing good rules
- User must know what to write

### Option B: Claude Code Skill (`/create-constitution`)
**Pros:**
- AI-assisted: Claude helps write constitution
- Interactive: Asks questions, suggests rules
- Learns from project: Analyzes codebase for patterns
- More powerful: Can validate against best practices

**Cons:**
- Requires Claude Code active
- Slower (AI processing time)
- Doesn't work offline

### 🎯 **RECOMMENDATION: HYBRID APPROACH (Both!)**

```
dev-kid constitution init     → CLI: Fast template creation (offline)
/create-constitution          → Skill: AI-assisted (Claude Code)
dev-kid constitution validate → CLI: Check constitution quality
dev-kid constitution edit     → CLI: Opens in $EDITOR
```

**Why Hybrid?**
1. **Fast start**: `dev-kid constitution init` for templates
2. **AI power**: `/create-constitution` for intelligent assistance
3. **Flexibility**: Users choose based on context
4. **Validation**: Both can validate quality

---

## Question 3: What should constitution and config.json contain?

**📋 Systems Architect Agent Analysis:**

### .constitution.md (Speckit - Development Rules)
**Purpose**: Immutable development rules enforced during implementation
**Location**: `memory-bank/shared/.constitution.md`
**Content**:
- Technology standards (Python 3.11+, FastAPI, etc.)
- Architecture principles (SRP, DI, Repository pattern)
- Testing standards (>80% coverage, pytest)
- Code standards (type hints, docstrings)
- Security rules (no hardcoded secrets)

**Example**:
```markdown
# Project Constitution

## Technology Standards
- Python 3.11+ required
- FastAPI for all APIs
- SQLAlchemy ORM only (no raw SQL)

## Testing Standards
- pytest with >80% coverage
- Unit tests required for all public functions
```

### config.json (dev-kid - Tool Configuration)
**Purpose**: Runtime configuration for dev-kid tooling
**Location**: `.devkid/config.json`
**Content**:
- Orchestration settings (max parallel tasks, wave strategy)
- Task watchdog settings (check interval, guideline minutes)
- Memory Bank settings (sync frequency, validation rules)
- Git settings (checkpoint message format, auto-push)
- Agent preferences (which agents for which tasks)

**Example**:
```json
{
  "version": "2.0.0",
  "orchestration": {
    "max_parallel_tasks": 3,
    "default_wave_strategy": "auto",
    "task_timeout_minutes": 120
  },
  "watchdog": {
    "check_interval_seconds": 300,
    "guideline_minutes": 7,
    "stalled_threshold_minutes": 15,
    "auto_start": true
  },
  "memory_bank": {
    "sync_on_checkpoint": true,
    "validate_on_finalize": true
  },
  "git": {
    "checkpoint_message_format": "[CHECKPOINT] {message}",
    "auto_push": false,
    "require_tests_pass": true
  },
  "agents": {
    "python_tasks": "python-pro",
    "api_tasks": "backend-architect",
    "test_tasks": "test-automator"
  }
}
```

**🎯 Key Distinction:**
- **Constitution** = WHAT rules to follow (immutable principles)
- **Config** = HOW dev-kid operates (mutable settings)

---

## Question 4: Complete Design Specification

**🏗️ Technical Architect Agent Design:**

### File Structure
```
project-root/
├── memory-bank/
│   └── shared/
│       └── .constitution.md          # Speckit rules (NEW)
├── .devkid/
│   ├── config.json                   # dev-kid settings (NEW)
│   └── constitution_templates/       # Built-in templates (NEW)
│       ├── python-api.constitution.md
│       ├── typescript-frontend.constitution.md
│       ├── data-engineering.constitution.md
│       └── full-stack.constitution.md
├── .claude/
│   ├── active_stack.md
│   └── ... (existing)
└── cli/
    ├── dev-kid                        # Main CLI (UPDATE)
    └── constitution_manager.py        # Constitution logic (NEW)
```

### CLI Commands Design

#### 1. `dev-kid constitution init [--template TYPE]`
**Purpose**: Create constitution from template
**Interactive Flow**:
```bash
$ dev-kid constitution init

📜 Constitution Initialization

Select project type:
  1. Python API (FastAPI/Flask)
  2. TypeScript Frontend (React/Next.js)
  3. Data Engineering (Airflow/dbt)
  4. Full-Stack (Frontend + Backend)
  5. Custom (blank template)

Choice [1-5]: 1

✅ Created: memory-bank/shared/.constitution.md
   Template: Python API

Next steps:
  1. Edit constitution: dev-kid constitution edit
  2. Validate: dev-kid constitution validate
  3. Use in workflow: /speckit.constitution
```

**Template Example** (python-api.constitution.md):
```markdown
# Project Constitution

## Technology Standards
- Python 3.11+ required
- FastAPI framework for APIs
- Pydantic for data validation
- SQLAlchemy ORM (no raw SQL)
- Alembic for migrations
- Type hints required (mypy strict)

## Architecture Principles
- Single Responsibility Principle
- Dependency Injection via FastAPI
- Repository pattern for data access
- Service layer for business logic

## Testing Standards
- pytest with >80% coverage required
- Unit tests for all public functions
- Integration tests for API endpoints
- Mock external services

## Code Standards
- Black formatter (line length: 88)
- Docstrings required (Google style)
- Max function complexity: 10 cyclomatic
- Max file length: 500 lines

## Security Standards
- No hardcoded secrets (use env vars)
- Input validation with Pydantic
- SQL injection prevention (ORM only)
- Authentication required for all endpoints
```

#### 2. `dev-kid constitution validate`
**Purpose**: Check constitution quality against best practices
**Output**:
```bash
$ dev-kid constitution validate

🔍 Validating Constitution...

✅ Technology Standards: 5 rules defined
✅ Architecture Principles: 4 principles defined
✅ Testing Standards: Coverage threshold specified
✅ Code Standards: Formatter and linting configured
⚠️  Security Standards: Missing rate limiting rules

Quality Score: 85/100

Recommendations:
  1. Add rate limiting rules for API endpoints
  2. Specify error handling patterns
  3. Define logging standards

Constitution Status: GOOD (ready for use)
```

#### 3. `dev-kid constitution edit`
**Purpose**: Open constitution in editor
```bash
$ dev-kid constitution edit

# Opens $EDITOR with memory-bank/shared/.constitution.md
# After save: Runs validation automatically
```

#### 4. `dev-kid constitution show`
**Purpose**: Display current constitution
```bash
$ dev-kid constitution show

📜 Current Constitution
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Project Constitution

## Technology Standards
- Python 3.11+ required
- FastAPI framework for APIs
...
```

### Claude Code Skill Design

**File**: `~/.claude/skills/create-constitution.md`

```markdown
---
name: Create Constitution
description: AI-assisted project constitution creation with intelligent analysis
version: 1.0.0
triggers:
  - "create constitution"
  - "setup constitution"
  - "write constitution"
---

# Create Constitution Skill

**Purpose**: Interactively create a project constitution with AI assistance.

## Workflow

### Step 1: Analyze Project
```python
# Use Grep, Glob, Read to analyze project
- Detect languages (Python, TypeScript, etc.)
- Identify frameworks (FastAPI, React, etc.)
- Find existing patterns (ORM usage, testing setup)
- Read package files (requirements.txt, package.json)
```

### Step 2: Ask Clarifying Questions
```
🤔 AI Assistant Questions:

Q1: What's the primary programming language?
    [Detected: Python 3.11]
    Confirm? [Y/n]:

Q2: What API framework are you using?
    [Detected: FastAPI imports]
    Confirm? [Y/n]:

Q3: What's your minimum test coverage requirement?
    Common: 70%, 80%, 90%
    Your choice: 80

Q4: Do you use type hints?
    [Detected: mypy in dev dependencies]
    Strict mode? [Y/n]: Y

Q5: What's your preferred code formatter?
    1. Black (Python standard)
    2. Ruff (faster)
    3. Other
    Choice: 1
```

### Step 3: Generate Constitution
```bash
# AI generates constitution based on:
# - Detected patterns
# - User answers
# - Best practices database
# - Similar project constitutions

✅ Generated: memory-bank/shared/.constitution.md
```

### Step 4: Review & Refine
```
📜 Generated Constitution:

# Project Constitution

## Technology Standards
- Python 3.11+ required (detected from pyproject.toml)
- FastAPI framework (detected from imports)
- Pydantic v2 for validation (detected from dependencies)

Review:
  [E]dit section
  [A]dd rule
  [D]elete rule
  [S]ave and finish
  [C]ancel

Choice: S

✅ Constitution saved!
✅ Validation passed (Quality Score: 92/100)
```

### Step 5: Integration
```bash
# Automatically updates:
# - memory-bank/shared/.constitution.md
# - .devkid/config.json (if not exists)
# - .claude/AGENT_STATE.json (marks constitution ready)

Next step: /speckit.specify <feature>
```

## Implementation

```bash
#!/usr/bin/env bash
# skills/create-constitution.sh

# Step 1: Analyze project
echo "🔍 Analyzing project structure..."
python3 <<PYTHON
import json
from pathlib import Path

# Detect patterns
project_info = {
    "languages": detect_languages(),
    "frameworks": detect_frameworks(),
    "testing": detect_testing_setup(),
    "linting": detect_linting()
}

print(json.dumps(project_info, indent=2))
PYTHON

# Step 2: Interactive questions
echo ""
echo "🤔 Let's create your constitution..."
read -p "Primary language [Python]: " language
language=${language:-Python}

read -p "Minimum test coverage [80%]: " coverage
coverage=${coverage:-80}

# Step 3: Generate from template + AI
echo ""
echo "✨ Generating constitution..."
claude <<PROMPT
Based on this project analysis:
- Language: $language
- Test coverage target: $coverage%
- Detected frameworks: [from analysis]

Generate a project constitution following the template structure.
Include specific, actionable rules based on detected patterns.
PROMPT

# Step 4: Validate
echo ""
dev-kid constitution validate

echo ""
echo "✅ Constitution created!"
echo "   Location: memory-bank/shared/.constitution.md"
echo "   Next: /speckit.specify <feature>"
```
```

### Config Management Commands

#### `dev-kid config init`
**Purpose**: Create .devkid/config.json with defaults
```bash
$ dev-kid config init

⚙️  Creating dev-kid configuration...

✅ Created: .devkid/config.json
   - Orchestration: max_parallel_tasks=3
   - Watchdog: check_interval=300s, guideline=7min
   - Memory: sync_on_checkpoint=true
   - Git: auto_push=false

Edit: dev-kid config edit
View: dev-kid config show
```

#### `dev-kid config get KEY`
**Purpose**: Get config value
```bash
$ dev-kid config get watchdog.guideline_minutes
7
```

#### `dev-kid config set KEY VALUE`
**Purpose**: Set config value
```bash
$ dev-kid config set watchdog.guideline_minutes 10

✅ Updated: watchdog.guideline_minutes = 10
   Config: .devkid/config.json
```

---

## Integration with Existing Workflow

**🔗 Integration Architect Agent Design:**

### Updated `dev-kid init` Flow

**Before** (current):
```bash
dev-kid init
  → Creates memory-bank/
  → Creates .claude/
  → Sets up git hooks
```

**After** (with constitution):
```bash
dev-kid init
  → Creates memory-bank/
  → Creates .claude/
  → Creates .devkid/
  → Prompts: "Create constitution? [Y/n]"
      Yes → Runs: dev-kid constitution init
      No  → Skips (can run later)
  → Sets up git hooks
  → Creates config.json with defaults
```

### Speckit Integration

**Current Workflow**:
```
/speckit.specify → Creates spec
```

**Enhanced Workflow**:
```
/speckit.constitution
  ↓ (checks for existing)
  ├─ Found: memory-bank/shared/.constitution.md
  │   → Loads rules
  │   → Validates format
  │   → Ready for /speckit.specify
  │
  └─ Not Found:
      → Suggests: dev-kid constitution init
      → OR: /create-constitution (AI-assisted)
      → Blocks until constitution exists
```

### Execution Integration

**During Wave Execution**:
```python
# cli/wave_executor.py

def execute_wave(wave_id):
    # Load constitution
    constitution = load_constitution()

    for task in wave.tasks:
        # Pass constitution to agent
        agent_context = {
            "task": task,
            "constitution_rules": constitution.rules_for_task(task),
            "validation": constitution.get_validators()
        }

        execute_task(agent_context)
```

### Checkpoint Validation

**Updated Checkpoint Protocol**:
```python
# After wave completes, before checkpoint:

def validate_wave_completion(wave_id):
    constitution = load_constitution()

    # Check constitution compliance
    violations = []

    for task in wave.completed_tasks:
        # Validate against constitution rules
        violations.extend(
            constitution.validate_task_output(task)
        )

    if violations:
        print("⚠️  Constitution Violations:")
        for v in violations:
            print(f"   - {v.rule}: {v.file} (line {v.line})")

        return False  # Block checkpoint

    return True  # Proceed with checkpoint
```

---

## Complete Usage Examples

### Example 1: New Project Setup

```bash
# Initialize project with dev-kid
$ cd my-new-project
$ dev-kid init

🚀 Initializing dev-kid...

Create constitution? [Y/n]: Y

📜 Constitution Initialization

Select project type:
  1. Python API (FastAPI/Flask)
  2. TypeScript Frontend (React/Next.js)
  3. Data Engineering (Airflow/dbt)
  4. Full-Stack (Frontend + Backend)
  5. Custom (blank template)

Choice [1-5]: 1

✅ Created: memory-bank/shared/.constitution.md
✅ Created: .devkid/config.json
✅ Created: .claude/ (context protection)

Project initialized! Ready for Speckit workflow.

Next steps:
  1. Review constitution: dev-kid constitution show
  2. Start feature: /speckit.specify <feature>
```

### Example 2: AI-Assisted Constitution

```bash
# In Claude Code
$ /create-constitution

🔍 Analyzing your project...

Detected:
  ✅ Python 3.11 (pyproject.toml)
  ✅ FastAPI framework (imports)
  ✅ pytest testing (conftest.py found)
  ✅ Black formatter (pyproject.toml)
  ✅ mypy type checking (mypy.ini)

🤔 Quick questions:

Q1: Minimum test coverage? [80%]: 85
Q2: Max function complexity? [10]: 10
Q3: Require docstrings? [Y/n]: Y
Q4: SQL: ORM only or allow raw SQL? [ORM only]: ORM only

✨ Generating constitution...

📜 Generated Constitution:

# Project Constitution

## Technology Standards
- Python 3.11+ required
- FastAPI framework for all APIs
- Pydantic v2 for data validation
- SQLAlchemy ORM only (no raw SQL)

## Testing Standards
- pytest with >85% coverage required
- Unit tests for all public functions
- Integration tests for API endpoints

## Code Standards
- Black formatter (line length: 88)
- Type hints required (mypy strict mode)
- Docstrings required (Google style)
- Max function complexity: 10 cyclomatic

Review? [E]dit/[S]ave/[C]ancel: S

✅ Constitution saved!
   Quality Score: 94/100
   Location: memory-bank/shared/.constitution.md

Ready for Speckit workflow: /speckit.specify <feature>
```

### Example 3: Validate Existing Constitution

```bash
$ dev-kid constitution validate

🔍 Validating Constitution...

✅ Technology Standards: 5 rules defined
✅ Architecture Principles: 4 principles defined
✅ Testing Standards: Coverage threshold: 85%
✅ Code Standards: Formatter, linting, type checking configured
✅ Security Standards: 6 security rules defined

Quality Score: 94/100

Recommendations:
  ✅ All critical areas covered
  ✅ Rules are specific and actionable
  ✅ No conflicts detected

Constitution Status: EXCELLENT (ready for production)
```

### Example 4: Config Management

```bash
# View config
$ dev-kid config show

⚙️  Current Configuration (.devkid/config.json)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

orchestration:
  max_parallel_tasks: 3
  default_wave_strategy: auto

watchdog:
  check_interval_seconds: 300
  guideline_minutes: 7
  auto_start: true

# Update config
$ dev-kid config set watchdog.guideline_minutes 10

✅ Updated: watchdog.guideline_minutes = 10

# Verify
$ dev-kid config get watchdog.guideline_minutes
10
```

---

## Implementation Priority

**Phase 1: Core CLI (Week 1)**
1. ✅ Add constitution commands to cli/dev-kid
2. ✅ Create constitution_manager.py
3. ✅ Add templates to .devkid/constitution_templates/
4. ✅ Update init command to prompt for constitution
5. ✅ Add config.json support

**Phase 2: Validation (Week 2)**
1. ✅ Implement constitution validator
2. ✅ Add checkpoint protocol validation
3. ✅ Integrate with wave executor

**Phase 3: Claude Code Skill (Week 3)**
1. ✅ Create /create-constitution skill
2. ✅ Add project analysis logic
3. ✅ Implement AI-assisted generation

**Phase 4: Documentation (Week 4)**
1. ✅ Update DEVELOPER_TRAINING_GUIDE.md
2. ✅ Add constitution best practices
3. ✅ Create video tutorials

---

## Summary: Team Orchestrator Recommendations

**Systems Architect**: ✅ Hybrid CLI + Skill approach
**UX Designer**: ✅ Template-based for speed, AI-assisted for quality
**Technical Architect**: ✅ Separate constitution (rules) from config (settings)
**Developer Advocate**: ✅ Integrate with init command, block Speckit without constitution
**Integration Architect**: ✅ Constitution validation at checkpoint, agent context injection

**Final Answer**:
1. **No**, there's currently NO constitution command (GAP!)
2. **Yes**, we need BOTH CLI command AND Claude Code skill
3. **Yes**, we need config.json for dev-kid settings (separate from constitution)
4. **Design complete** - Ready for implementation!

---

*Constitution Management System Design v1.0*
*Created: 2026-01-07*
*Team Orchestrator Analysis: 5 Specialized Agents*

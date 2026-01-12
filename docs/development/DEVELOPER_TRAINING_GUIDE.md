# Developer Training Guide: Spec-Driven Development with Orchestrated Execution

## Table of Contents

1. [System Overview](#system-overview)
2. [Prerequisites & Setup](#prerequisites--setup)
3. [The Complete Workflow](#the-complete-workflow)
4. [Practical Example: MLflow Observability](#practical-example-mlflow-observability)
5. [Best Practices](#best-practices)
6. [Common Pitfalls & Solutions](#common-pitfalls--solutions)
7. [Quick Reference](#quick-reference)

---

## System Overview

### What Is This System?

This is a **rigorous, constitution-enforced development workflow** that combines three powerful tools:

1. **Speckit** (GitHub's Spec-Driven Development toolkit)
   - Enforces a 6-phase specification process
   - Prevents vague requirements from reaching code
   - Creates verifiable acceptance criteria

2. **dev-kid** (Wave-based task orchestration)
   - Breaks work into parallel execution waves
   - Provides task watchdog for time estimation
   - Manages checkpoints and execution flow

3. **Team Orchestrator** (Multi-agent coordination)
   - Coordinates specialized AI agents
   - Enforces constitution rules during execution
   - Maintains quality through agent specialization

### Why Use This Workflow?

**Traditional Development Problems:**
- Vague requirements lead to rework
- Poor task estimation causes delays
- Missing context between agents causes bugs
- No enforcement of architectural rules

**This System Solves:**
- Constitution enforces architectural decisions upfront
- Specification must be concrete before coding starts
- Task watchdog prevents scope creep
- Agent coordination ensures consistency
- Verification phase catches deviations

### When to Use This Workflow

**Use for:**
- New features requiring multiple components
- Architectural changes affecting multiple systems
- Complex integrations with external services
- Features requiring cross-team coordination
- Any work estimated >4 hours

**Don't Use for:**
- Simple bug fixes (<30 min)
- Documentation-only changes
- Configuration updates
- Dependency version bumps

---

## Prerequisites & Setup

### Required Tools

1. **Claude Code CLI** (with Speckit skill installed)
2. **dev-kid** orchestration system
3. **Python 3.10+** with UV package manager
4. **Git** for version control

### Installation

```bash
# Install dev-kid
cd /path/to/dev-kid
uv venv
source .venv/bin/activate
uv pip install -e .

# Verify Speckit is available
claude-code --help | grep speckit

# Verify dev-kid commands
dev-kid --help
```

### Configuration

Create `.claude/config.json` in your project:

```json
{
  "skills": {
    "speckit": {
      "enabled": true,
      "constitution_path": ".speckit/constitution.md",
      "specs_dir": ".speckit/specs"
    }
  }
}
```

### Project Structure

Your project should have:

```
project-root/
├── .speckit/
│   ├── constitution.md          # Project rules & standards
│   ├── specs/                   # Feature specifications
│   └── plans/                   # Execution plans
├── .team-orchestrator/
│   ├── execution_plan.json      # Current orchestration plan
│   └── checkpoints/             # Execution checkpoints
├── src/                         # Your source code
└── tests/                       # Your tests
```

---

## The Complete Workflow

### Phase 1: Constitution & Specification (Speckit)

#### Step 1.1: Create Constitution

**Command:** `/speckit.constitution`

**What it does:** Creates the foundational rules for your project.

**Example:**

```markdown
User: /speckit.constitution

Claude: I'll help create a constitution for your project.

What are the key architectural principles and standards
that all implementations must follow?

User:
- All services must use FastAPI with structured logging
- Database access only through SQLAlchemy ORM
- All API endpoints require JWT authentication
- Error handling must use centralized error middleware
- All async operations must have timeout limits
- Observability required: metrics, traces, logs

Claude: [Creates .speckit/constitution.md with these rules]
```

**Constitution Template:**

```markdown
# Project Constitution

## Architectural Principles

1. **Service Architecture**
   - Framework: FastAPI 0.104+
   - Async-first design required
   - Dependency injection for all services

2. **Data Layer**
   - ORM: SQLAlchemy 2.x only
   - No raw SQL queries in business logic
   - All models must have created_at/updated_at

3. **Security**
   - JWT authentication on all non-health endpoints
   - Rate limiting: 100 req/min per user
   - Input validation with Pydantic models

4. **Observability**
   - Structured JSON logging (loguru)
   - OpenTelemetry tracing required
   - Prometheus metrics on /metrics endpoint

## Standards

### Code Quality
- Type hints mandatory
- pytest coverage minimum 80%
- No direct dependencies on external APIs in core logic

### Error Handling
- Use custom exception hierarchy
- All errors return RFC 7807 problem details
- Rollbar integration for error tracking

## Forbidden Practices
- No print() statements (use logger)
- No environment variables read directly (use config service)
- No synchronous blocking calls in async contexts
```

#### Step 1.2: Create Specification

**Command:** `/speckit.specify`

**What it does:** Creates detailed specification following constitution.

**Example:**

```markdown
User: /speckit.specify

Feature: Add MLflow experiment tracking to training pipeline

Claude: I'll create a detailed specification. Let me check the
constitution first to ensure compliance.

[Creates .speckit/specs/mlflow-experiment-tracking.md]
```

**Good Specification Example:**

```markdown
# Specification: MLflow Experiment Tracking

## Overview
Integrate MLflow experiment tracking into the existing model
training pipeline to capture metrics, parameters, and artifacts.

## Requirements

### Functional Requirements

1. **Experiment Tracking**
   - Track all hyperparameters passed to training jobs
   - Log training/validation metrics per epoch
   - Store model artifacts (weights, configs) to MLflow
   - Support experiment comparison in MLflow UI

2. **Integration Points**
   - Hook into existing TrainingOrchestrator class
   - Minimal changes to existing training code
   - Backward compatible with non-MLflow runs

### Non-Functional Requirements

1. **Performance**
   - Logging overhead <5% of training time
   - Async artifact uploads to avoid blocking
   - Batch metric logging (not per-step)

2. **Reliability**
   - Training continues if MLflow unavailable
   - Failed uploads retry with exponential backoff
   - Local artifact caching before upload

## Technical Approach

### Architecture Compliance
- Uses FastAPI dependency injection for MLflow client
- Structured logging via loguru for all MLflow operations
- Configuration via centralized config service
- OpenTelemetry spans for MLflow API calls

### Components

1. **MLflowClient Service** (src/services/mlflow_client.py)
   - Singleton client with connection pooling
   - Async methods for all MLflow operations
   - Circuit breaker pattern for failures

2. **TrainingLogger** (src/training/logger.py)
   - Wraps MLflow tracking API
   - Batches metrics for efficient upload
   - Handles artifact staging and upload

3. **Configuration** (src/config/mlflow.py)
   - MLflow tracking URI from config service
   - Experiment naming conventions
   - Retry policy settings

## Acceptance Criteria

1. Training job creates MLflow experiment with job ID
2. All hyperparameters logged before training starts
3. Metrics logged every N epochs (configurable)
4. Model artifacts uploaded on training completion
5. Training succeeds even if MLflow is down
6. Failed uploads retry up to 3 times
7. MLflow operations captured in OpenTelemetry traces
8. Unit test coverage >80% for new code
9. Integration test validates end-to-end flow

## Out of Scope

- MLflow model registry integration (future work)
- Custom metric plugins
- MLflow authentication (uses existing auth)
```

#### Step 1.3: Clarify Specification

**Command:** `/speckit.clarify`

**What it does:** Interactive Q&A to remove ambiguities.

**Example:**

```markdown
User: /speckit.clarify .speckit/specs/mlflow-experiment-tracking.md

Claude: I have some questions to clarify the specification:

1. What happens if MLflow is down at training start?
   - Should we fail the job?
   - Create a "pending" run and sync later?
   - Log locally and upload when available?

2. "Batch metric logging" - what's the batch size?
   - Every N steps?
   - Every N seconds?
   - Configurable threshold?

3. Artifact uploads - what's included?
   - Model weights only?
   - Optimizer state?
   - Training plots/visualizations?
   - Config files used?

4. Experiment naming - what's the convention?
   - Job ID only?
   - Include timestamp?
   - Include model architecture?

User:
1. Log locally, upload when available (resilient mode)
2. Batch every 10 seconds or 100 metrics, whichever comes first
3. Model weights + final config + loss plot (PNG)
4. Format: {model_name}_{job_id}_{timestamp}

Claude: [Updates specification with clarifications]
```

#### Step 1.4: Create Execution Plan

**Command:** `/speckit.plan`

**What it does:** Breaks specification into concrete implementation tasks.

**Example:**

```markdown
User: /speckit.plan .speckit/specs/mlflow-experiment-tracking.md

Claude: [Creates .speckit/plans/mlflow-experiment-tracking-plan.md]
```

**Plan Structure:**

```markdown
# Execution Plan: MLflow Experiment Tracking

## Phase 1: Infrastructure (Wave 1 - Parallel)

### Task 1.1: MLflow Client Service
- **Estimated Time:** 3 hours
- **Dependencies:** None
- **Deliverables:**
  - src/services/mlflow_client.py
  - Unit tests (test_mlflow_client.py)
- **Acceptance:**
  - Client initializes from config
  - Async methods for create_experiment, log_params, log_metrics
  - Circuit breaker opens after 3 failures
  - Connection pooling configured

### Task 1.2: Configuration Setup
- **Estimated Time:** 1 hour
- **Dependencies:** None
- **Deliverables:**
  - src/config/mlflow.py
  - Environment variable schema
- **Acceptance:**
  - Config loads from centralized config service
  - Default values for all settings
  - Validation on startup

## Phase 2: Core Integration (Wave 2 - Sequential)

### Task 2.1: TrainingLogger Implementation
- **Estimated Time:** 4 hours
- **Dependencies:** Task 1.1 complete
- **Deliverables:**
  - src/training/logger.py
  - Unit tests (test_training_logger.py)
- **Acceptance:**
  - Batches metrics with 10s/100-metric threshold
  - Handles MLflow unavailability gracefully
  - Retry logic with exponential backoff
  - Local caching for offline mode

### Task 2.2: TrainingOrchestrator Integration
- **Estimated Time:** 3 hours
- **Dependencies:** Task 2.1 complete
- **Deliverables:**
  - Modified src/training/orchestrator.py
  - Integration tests
- **Acceptance:**
  - Minimal changes to existing code
  - Dependency injection for MLflow logger
  - Backward compatible (no MLflow = skip logging)

## Phase 3: Artifact Management (Wave 3 - Parallel)

### Task 3.1: Artifact Upload Handler
- **Estimated Time:** 2 hours
- **Dependencies:** Task 2.1 complete
- **Deliverables:**
  - src/training/artifacts.py
  - Unit tests
- **Acceptance:**
  - Async upload to MLflow
  - Supports model weights (.pt files)
  - Supports config files (.yaml)
  - Supports plots (.png)

### Task 3.2: Plot Generation
- **Estimated Time:** 2 hours
- **Dependencies:** None
- **Deliverables:**
  - src/training/visualization.py
  - Loss plot generator
- **Acceptance:**
  - Generates loss curve PNG
  - Includes train/val metrics
  - Saves to temp directory for upload

## Phase 4: Testing & Validation (Wave 4 - Sequential)

### Task 4.1: End-to-End Integration Test
- **Estimated Time:** 3 hours
- **Dependencies:** All previous tasks
- **Deliverables:**
  - tests/integration/test_mlflow_e2e.py
- **Acceptance:**
  - Runs full training job with MLflow
  - Validates experiment created
  - Validates metrics logged
  - Validates artifacts uploaded
  - Validates offline mode works

### Task 4.2: Documentation
- **Estimated Time:** 1 hour
- **Dependencies:** Task 4.1 complete
- **Deliverables:**
  - docs/mlflow-integration.md
  - Code comments
- **Acceptance:**
  - Setup instructions for developers
  - Configuration examples
  - Troubleshooting guide

## Dependency Graph

```
Wave 1: [Task 1.1] [Task 1.2]
           ↓           ↓
Wave 2:   [Task 2.1] ←┘
              ↓
          [Task 2.2]
              ↓
Wave 3: [Task 3.1] [Task 3.2]
           ↓           ↓
Wave 4:   [Task 4.1]
              ↓
          [Task 4.2]
```

## Total Estimate: 19 hours (2.5 days)
```

#### Step 1.5: Convert to Dev-Kid Tasks

**Command:** `/speckit.tasks`

**What it does:** Converts plan to dev-kid task format.

**Example:**

```markdown
User: /speckit.tasks .speckit/plans/mlflow-experiment-tracking-plan.md

Claude: [Creates .team-orchestrator/execution_plan.json]
```

**Generated execution_plan.json:**

```json
{
  "project": "mlflow-experiment-tracking",
  "constitution": ".speckit/constitution.md",
  "specification": ".speckit/specs/mlflow-experiment-tracking.md",
  "total_estimated_hours": 19,
  "waves": [
    {
      "wave_id": 1,
      "name": "Infrastructure Setup",
      "tasks": [
        {
          "task_id": "1.1",
          "title": "MLflow Client Service",
          "assigned_agent": "backend-engineer",
          "estimated_hours": 3,
          "dependencies": [],
          "deliverables": [
            "src/services/mlflow_client.py",
            "tests/unit/test_mlflow_client.py"
          ],
          "acceptance_criteria": [
            "Client initializes from config",
            "Async methods for create_experiment, log_params, log_metrics",
            "Circuit breaker opens after 3 failures",
            "Connection pooling configured"
          ],
          "constitution_requirements": [
            "FastAPI dependency injection",
            "Structured logging with loguru",
            "Type hints mandatory"
          ]
        },
        {
          "task_id": "1.2",
          "title": "Configuration Setup",
          "assigned_agent": "backend-engineer",
          "estimated_hours": 1,
          "dependencies": [],
          "deliverables": [
            "src/config/mlflow.py"
          ],
          "acceptance_criteria": [
            "Config loads from centralized config service",
            "Default values for all settings",
            "Validation on startup"
          ],
          "constitution_requirements": [
            "No environment variables read directly",
            "Pydantic models for validation"
          ]
        }
      ]
    },
    {
      "wave_id": 2,
      "name": "Core Integration",
      "tasks": [
        {
          "task_id": "2.1",
          "title": "TrainingLogger Implementation",
          "assigned_agent": "backend-engineer",
          "estimated_hours": 4,
          "dependencies": ["1.1"],
          "deliverables": [
            "src/training/logger.py",
            "tests/unit/test_training_logger.py"
          ],
          "acceptance_criteria": [
            "Batches metrics with 10s/100-metric threshold",
            "Handles MLflow unavailability gracefully",
            "Retry logic with exponential backoff",
            "Local caching for offline mode"
          ],
          "constitution_requirements": [
            "Async-first design",
            "Timeout limits on async operations",
            "Type hints mandatory",
            "Test coverage >80%"
          ]
        },
        {
          "task_id": "2.2",
          "title": "TrainingOrchestrator Integration",
          "assigned_agent": "backend-engineer",
          "estimated_hours": 3,
          "dependencies": ["2.1"],
          "deliverables": [
            "src/training/orchestrator.py",
            "tests/integration/test_orchestrator_mlflow.py"
          ],
          "acceptance_criteria": [
            "Minimal changes to existing code",
            "Dependency injection for MLflow logger",
            "Backward compatible (no MLflow = skip logging)"
          ],
          "constitution_requirements": [
            "FastAPI dependency injection",
            "No breaking changes to existing API"
          ]
        }
      ]
    },
    {
      "wave_id": 3,
      "name": "Artifact Management",
      "tasks": [
        {
          "task_id": "3.1",
          "title": "Artifact Upload Handler",
          "assigned_agent": "backend-engineer",
          "estimated_hours": 2,
          "dependencies": ["2.1"],
          "deliverables": [
            "src/training/artifacts.py",
            "tests/unit/test_artifacts.py"
          ],
          "acceptance_criteria": [
            "Async upload to MLflow",
            "Supports model weights (.pt files)",
            "Supports config files (.yaml)",
            "Supports plots (.png)"
          ],
          "constitution_requirements": [
            "Async-first design",
            "Type hints mandatory"
          ]
        },
        {
          "task_id": "3.2",
          "title": "Plot Generation",
          "assigned_agent": "backend-engineer",
          "estimated_hours": 2,
          "dependencies": [],
          "deliverables": [
            "src/training/visualization.py",
            "tests/unit/test_visualization.py"
          ],
          "acceptance_criteria": [
            "Generates loss curve PNG",
            "Includes train/val metrics",
            "Saves to temp directory for upload"
          ],
          "constitution_requirements": [
            "Type hints mandatory",
            "Test coverage >80%"
          ]
        }
      ]
    },
    {
      "wave_id": 4,
      "name": "Testing & Validation",
      "tasks": [
        {
          "task_id": "4.1",
          "title": "End-to-End Integration Test",
          "assigned_agent": "qa-engineer",
          "estimated_hours": 3,
          "dependencies": ["2.2", "3.1", "3.2"],
          "deliverables": [
            "tests/integration/test_mlflow_e2e.py"
          ],
          "acceptance_criteria": [
            "Runs full training job with MLflow",
            "Validates experiment created",
            "Validates metrics logged",
            "Validates artifacts uploaded",
            "Validates offline mode works"
          ],
          "constitution_requirements": [
            "Test coverage >80%",
            "Uses pytest fixtures"
          ]
        },
        {
          "task_id": "4.2",
          "title": "Documentation",
          "assigned_agent": "tech-writer",
          "estimated_hours": 1,
          "dependencies": ["4.1"],
          "deliverables": [
            "docs/mlflow-integration.md"
          ],
          "acceptance_criteria": [
            "Setup instructions for developers",
            "Configuration examples",
            "Troubleshooting guide"
          ],
          "constitution_requirements": []
        }
      ]
    }
  ]
}
```

---

### Phase 2: Orchestration (dev-kid)

#### Step 2.1: Generate Orchestration Plan

**Command:** `dev-kid orchestrate`

**What it does:** Validates execution plan and prepares for execution.

**Example:**

```bash
# From project root
dev-kid orchestrate

# Output:
# ✓ Constitution loaded: .speckit/constitution.md
# ✓ Specification loaded: .speckit/specs/mlflow-experiment-tracking.md
# ✓ Execution plan validated: .team-orchestrator/execution_plan.json
#
# Orchestration Summary:
# - Total Waves: 4
# - Total Tasks: 8
# - Total Estimated Hours: 19
# - Agents Required: backend-engineer, qa-engineer, tech-writer
#
# Wave Breakdown:
#   Wave 1 (Infrastructure Setup): 2 tasks (4h) - Parallel
#   Wave 2 (Core Integration): 2 tasks (7h) - Sequential
#   Wave 3 (Artifact Management): 2 tasks (4h) - Parallel
#   Wave 4 (Testing & Validation): 2 tasks (4h) - Sequential
#
# Dependency Validation: PASSED
# Constitution Compliance Check: PASSED
#
# Ready for execution. Run: dev-kid execute --wave 1
```

#### Step 2.2: Start Task Watchdog

**Command:** `dev-kid watchdog-start`

**What it does:** Monitors task execution time and warns about overruns.

**Example:**

```bash
# Start watchdog before execution
dev-kid watchdog-start

# Output:
# Task Watchdog Started
# Monitoring: .team-orchestrator/execution_plan.json
# Warning threshold: 125% of estimate
# Alert threshold: 150% of estimate
#
# Press Ctrl+C to stop watchdog
```

**Watchdog Output During Execution:**

```
[12:00:00] Task 1.1 started (estimate: 3h)
[12:45:00] Task 1.2 started (estimate: 1h)
[14:00:00] Task 1.2 completed (actual: 1h 15m, 125% of estimate)
[14:30:00] ⚠️  WARNING: Task 1.1 at 150% of estimate (4.5h elapsed, estimated 3h)
[15:00:00] Task 1.1 completed (actual: 5h, 167% of estimate)
           📊 Consider revising estimates for similar tasks
```

---

### Phase 3: Execution (team orchestrator + dev-kid)

#### Step 3.1: Execute Wave 1

**Command:** `dev-kid execute --wave 1`

**What it does:** Executes all tasks in wave 1 with agent coordination.

**Example:**

```bash
dev-kid execute --wave 1

# Output:
# Executing Wave 1: Infrastructure Setup
# Tasks: 2 (parallel execution enabled)
#
# Starting Task 1.1: MLflow Client Service
#   Agent: backend-engineer
#   Estimated: 3 hours
#   Deliverables: src/services/mlflow_client.py, tests/unit/test_mlflow_client.py
#
# Starting Task 1.2: Configuration Setup
#   Agent: backend-engineer
#   Estimated: 1 hour
#   Deliverables: src/config/mlflow.py
#
# [Agent backend-engineer working on Task 1.1...]
# [Agent backend-engineer working on Task 1.2...]
```

**Agent Execution (What Happens Behind the Scenes):**

```markdown
[backend-engineer agent receives Task 1.1]

Agent: I'll implement the MLflow Client Service according to the
constitution and specification.

Step 1: Review constitution requirements
  ✓ FastAPI dependency injection
  ✓ Structured logging with loguru
  ✓ Type hints mandatory
  ✓ Async-first design

Step 2: Create src/services/mlflow_client.py
  [Implements client with all requirements]

Step 3: Create tests/unit/test_mlflow_client.py
  [Implements tests covering >80%]

Step 4: Validate against acceptance criteria
  ✓ Client initializes from config
  ✓ Async methods for create_experiment, log_params, log_metrics
  ✓ Circuit breaker opens after 3 failures
  ✓ Connection pooling configured

Step 5: Run tests
  pytest tests/unit/test_mlflow_client.py
  ✓ 15 tests passed, coverage: 87%

Task 1.1 COMPLETE - Ready for checkpoint
```

#### Step 3.2: Checkpoint Protocol

**Command:** (Automatic after each wave)

**What it does:** Validates wave completion before proceeding.

**Example:**

```bash
# After wave 1 completes
# dev-kid automatically runs checkpoint

# Output:
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHECKPOINT: Wave 1 Complete
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Task Completion Status:
#   ✓ Task 1.1: MLflow Client Service (5h actual / 3h estimated)
#   ✓ Task 1.2: Configuration Setup (1h 15m actual / 1h estimated)
#
# Deliverables Verification:
#   ✓ src/services/mlflow_client.py (created)
#   ✓ tests/unit/test_mlflow_client.py (created, 15 tests, 87% coverage)
#   ✓ src/config/mlflow.py (created)
#
# Acceptance Criteria Validation:
#   Task 1.1:
#     ✓ Client initializes from config
#     ✓ Async methods implemented
#     ✓ Circuit breaker opens after 3 failures
#     ✓ Connection pooling configured
#
#   Task 1.2:
#     ✓ Config loads from centralized config service
#     ✓ Default values for all settings
#     ✓ Validation on startup
#
# Constitution Compliance:
#   ✓ FastAPI dependency injection used
#   ✓ Structured logging (loguru) present
#   ✓ Type hints on all functions
#   ✓ Async-first design followed
#   ✓ Test coverage >80%
#
# Time Analysis:
#   Estimated: 4 hours
#   Actual: 6h 15m (156% of estimate)
#   ⚠️  Tasks took longer than estimated
#   💡 Recommendation: Adjust estimates for Wave 2 tasks
#
# Wave 1 Status: ✓ APPROVED
#
# Next: dev-kid execute --wave 2
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**What Happens if Checkpoint Fails:**

```bash
# Example: Missing deliverable
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHECKPOINT: Wave 1 FAILED
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Task Completion Status:
#   ✓ Task 1.1: MLflow Client Service
#   ✗ Task 1.2: Configuration Setup
#
# Failures:
#   Task 1.2:
#     ✗ Missing deliverable: src/config/mlflow.py
#     ✗ Acceptance criterion not met: "Validation on startup"
#
# Constitution Violations:
#   Task 1.1:
#     ⚠️  Test coverage: 72% (required: >80%)
#
# Wave 1 Status: ✗ REJECTED
#
# Action Required:
#   1. Complete missing deliverables
#   2. Fix acceptance criteria failures
#   3. Address constitution violations
#   4. Re-run: dev-kid execute --wave 1 --retry
#
# Do NOT proceed to Wave 2 until checkpoint passes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### Step 3.3: Execute Remaining Waves

```bash
# Execute wave 2 (sequential tasks)
dev-kid execute --wave 2

# After checkpoint passes:
dev-kid execute --wave 3

# After checkpoint passes:
dev-kid execute --wave 4
```

---

### Phase 4: Verification & Completion

#### Step 4.1: Verify Implementation

**Command:** `/speckit.verify-implementation`

**What it does:** Validates entire implementation against original specification.

**Example:**

```markdown
User: /speckit.verify-implementation .speckit/specs/mlflow-experiment-tracking.md

Claude: I'll verify the implementation against the specification.

Checking:
1. Constitution compliance
2. Specification requirements
3. Acceptance criteria
4. Code quality standards

[Runs comprehensive verification]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IMPLEMENTATION VERIFICATION REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Constitution Compliance: ✓ PASS
  ✓ FastAPI dependency injection used throughout
  ✓ Structured logging present (loguru)
  ✓ SQLAlchemy ORM used (no raw SQL)
  ✓ JWT authentication preserved
  ✓ Error middleware integration complete
  ✓ Async operations have timeout limits
  ✓ OpenTelemetry tracing added

Functional Requirements: ✓ PASS
  ✓ All hyperparameters tracked
  ✓ Training/validation metrics logged per epoch
  ✓ Model artifacts stored to MLflow
  ✓ Experiment comparison supported in UI
  ✓ TrainingOrchestrator integration minimal
  ✓ Backward compatible with non-MLflow runs

Non-Functional Requirements: ✓ PASS
  ✓ Logging overhead <5% (measured: 2.3%)
  ✓ Async artifact uploads implemented
  ✓ Batch metric logging (10s/100 metric threshold)
  ✓ Training continues if MLflow unavailable
  ✓ Retry with exponential backoff implemented
  ✓ Local artifact caching present

Acceptance Criteria: ✓ 9/9 PASS
  ✓ Training job creates MLflow experiment with job ID
  ✓ All hyperparameters logged before training starts
  ✓ Metrics logged every N epochs (configurable)
  ✓ Model artifacts uploaded on training completion
  ✓ Training succeeds even if MLflow is down
  ✓ Failed uploads retry up to 3 times
  ✓ MLflow operations in OpenTelemetry traces
  ✓ Unit test coverage: 84% (>80% required)
  ✓ Integration test validates end-to-end flow

Code Quality: ✓ PASS
  ✓ Type hints on all functions
  ✓ No print() statements
  ✓ Environment variables via config service
  ✓ No synchronous blocking in async contexts
  ✓ Custom exception hierarchy used
  ✓ RFC 7807 problem details returned

Test Results:
  Unit Tests: 47 passed, 0 failed
  Integration Tests: 8 passed, 0 failed
  Coverage: 84%

Documentation: ✓ PASS
  ✓ docs/mlflow-integration.md created
  ✓ Setup instructions present
  ✓ Configuration examples included
  ✓ Troubleshooting guide complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OVERALL STATUS: ✓ VERIFIED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Implementation meets all specification requirements and
adheres to project constitution.

Ready for: dev-kid finalize
```

#### Step 4.2: Finalize Implementation

**Command:** `dev-kid finalize`

**What it does:** Creates final snapshot and closes execution.

**Example:**

```bash
dev-kid finalize

# Output:
#
# Finalization Summary
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#
# Project: mlflow-experiment-tracking
# Specification: .speckit/specs/mlflow-experiment-tracking.md
# Constitution: .speckit/constitution.md
#
# Execution Statistics:
#   Total Waves: 4
#   Total Tasks: 8
#   Estimated Time: 19 hours
#   Actual Time: 23.5 hours (124% of estimate)
#
# Deliverables Created:
#   - src/services/mlflow_client.py
#   - src/config/mlflow.py
#   - src/training/logger.py
#   - src/training/orchestrator.py (modified)
#   - src/training/artifacts.py
#   - src/training/visualization.py
#   - tests/unit/test_mlflow_client.py
#   - tests/unit/test_training_logger.py
#   - tests/unit/test_artifacts.py
#   - tests/unit/test_visualization.py
#   - tests/integration/test_orchestrator_mlflow.py
#   - tests/integration/test_mlflow_e2e.py
#   - docs/mlflow-integration.md
#
# Test Results:
#   Unit Tests: 47/47 passed
#   Integration Tests: 8/8 passed
#   Coverage: 84%
#
# Constitution Compliance: ✓ VERIFIED
# Specification Verification: ✓ VERIFIED
#
# Session Snapshot: .team-orchestrator/snapshots/mlflow-tracking-2025-01-06.json
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ✓ Implementation Complete
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Practical Example: MLflow Observability

Let's walk through implementing MLflow observability from start to finish.

### Scenario

You need to add experiment tracking to an existing ML training pipeline. The pipeline currently trains models but doesn't track hyperparameters, metrics, or artifacts.

### Step-by-Step Execution

#### 1. Create Constitution (if not exists)

```bash
# Open Claude Code
claude-code

# In chat:
/speckit.constitution
```

**You provide:**

```
Our ML platform must follow these rules:

Architecture:
- FastAPI for all services
- Async-first design
- PostgreSQL for metadata (SQLAlchemy ORM)
- Redis for caching

Training Pipeline:
- PyTorch for models
- Ray for distributed training
- All hyperparameters via config files (YAML)
- Model artifacts stored in S3

Observability:
- Structured logging (loguru)
- OpenTelemetry for traces
- Prometheus metrics on /metrics

Security:
- JWT auth on all endpoints except /health
- No secrets in code or configs
- All S3 access via IAM roles

Quality:
- Type hints required
- Pytest coverage >80%
- Integration tests for all workflows
```

**Claude creates:** `.speckit/constitution.md`

#### 2. Create Specification

```bash
/speckit.specify
```

**You provide:**

```
Feature: MLflow Experiment Tracking

Add MLflow to our training pipeline so data scientists can:
- Track experiments with hyperparameters and metrics
- Compare model performance across runs
- Store and retrieve model artifacts
- Visualize training progress

Integration should be:
- Minimal changes to existing TrainingOrchestrator
- Backward compatible (works without MLflow)
- Resilient to MLflow outages
```

**Claude creates:** `.speckit/specs/mlflow-experiment-tracking.md` with:
- Detailed requirements
- Technical approach
- Architecture diagrams
- Acceptance criteria

#### 3. Clarify Ambiguities

```bash
/speckit.clarify .speckit/specs/mlflow-experiment-tracking.md
```

**Claude asks:**

```
1. What happens if MLflow is unavailable at training start?
2. How often should metrics be logged? Every epoch? Every batch?
3. Which artifacts should be uploaded?
4. What's the experiment naming convention?
5. Should we track model registry versions?
```

**You answer:**

```
1. Log locally, upload when available (resilient mode)
2. Batch metrics every 10 seconds OR 100 metrics (whichever first)
3. Upload: model weights, final config, loss plot
4. Naming: {model_architecture}_{job_id}_{timestamp}
5. No model registry yet - future work
```

**Claude updates:** `.speckit/specs/mlflow-experiment-tracking.md` with clarifications

#### 4. Create Execution Plan

```bash
/speckit.plan .speckit/specs/mlflow-experiment-tracking.md
```

**Claude creates:** `.speckit/plans/mlflow-experiment-tracking-plan.md` with:
- 4 waves of tasks
- Dependencies mapped
- 19 hour estimate

#### 5. Convert to Dev-Kid Format

```bash
/speckit.tasks .speckit/plans/mlflow-experiment-tracking-plan.md
```

**Claude creates:** `.team-orchestrator/execution_plan.json`

#### 6. Validate Plan

```bash
dev-kid orchestrate
```

**Output:**

```
✓ Constitution loaded
✓ Specification loaded
✓ Execution plan validated

4 waves, 8 tasks, 19 hours estimated
Ready for execution
```

#### 7. Start Watchdog

```bash
# In separate terminal
dev-kid watchdog-start
```

#### 8. Execute Wave 1

```bash
dev-kid execute --wave 1
```

**Tasks executed:**
- MLflow Client Service (3h estimate)
- Configuration Setup (1h estimate)

**Checkpoint:**

```
✓ Wave 1 complete
✓ All deliverables created
✓ All acceptance criteria met
✓ Constitution compliant
⚠️  Time: 6h 15m (156% of estimate)

Approved for Wave 2
```

#### 9. Execute Wave 2

```bash
dev-kid execute --wave 2
```

**Tasks executed:**
- TrainingLogger Implementation (4h estimate)
- TrainingOrchestrator Integration (3h estimate)

**Checkpoint:**

```
✓ Wave 2 complete
✓ All deliverables created
✓ Integration tests passing
✓ Backward compatibility verified

Approved for Wave 3
```

#### 10. Execute Wave 3

```bash
dev-kid execute --wave 3
```

**Tasks executed:**
- Artifact Upload Handler (2h estimate)
- Plot Generation (2h estimate)

**Checkpoint:**

```
✓ Wave 3 complete
✓ Async uploads working
✓ Plot generation tested

Approved for Wave 4
```

#### 11. Execute Wave 4

```bash
dev-kid execute --wave 4
```

**Tasks executed:**
- End-to-End Integration Test (3h estimate)
- Documentation (1h estimate)

**Checkpoint:**

```
✓ Wave 4 complete
✓ E2E test passes
✓ Documentation complete

All waves complete
```

#### 12. Verify Implementation

```bash
/speckit.verify-implementation .speckit/specs/mlflow-experiment-tracking.md
```

**Claude validates:**

```
✓ Constitution compliance
✓ Functional requirements met
✓ Non-functional requirements met
✓ All 9 acceptance criteria pass
✓ Test coverage: 84%
✓ Documentation complete

VERIFIED - Ready to finalize
```

#### 13. Finalize

```bash
dev-kid finalize
```

**Output:**

```
✓ Implementation complete
  Estimated: 19h
  Actual: 23.5h (124%)

✓ 13 deliverables created
✓ 55 tests passing
✓ 84% coverage

Session snapshot saved
```

### What You've Achieved

- **Zero ambiguity:** Specification forced you to clarify edge cases upfront
- **Constitution enforced:** All code follows architectural standards
- **Predictable execution:** Wave-based approach prevented chaos
- **Quality assured:** Checkpoint protocol caught issues early
- **Documented:** Automatically created comprehensive docs
- **Verifiable:** Implementation provably meets requirements

---

## Best Practices

### When to Use This Workflow

**Use for features that involve:**

1. **Multiple components/services**
   - Frontend + backend changes
   - Database schema + API + UI
   - Multiple microservices

2. **Architectural significance**
   - New design patterns
   - Integration with external systems
   - Performance-critical changes

3. **Cross-team coordination**
   - Multiple agents/developers
   - Dependencies between tasks
   - Shared resources

4. **High complexity**
   - Estimated >4 hours
   - Multiple edge cases
   - Complex error handling

**Don't use for:**

- Simple bug fixes
- Documentation updates
- Dependency version bumps
- Configuration changes
- Hotfixes

### How to Write Good Constitutions

**Do:**

```markdown
# Good Constitution Example

## Architectural Principles

1. **API Design**
   - REST for synchronous operations
   - GraphQL for complex queries
   - gRPC for service-to-service communication
   - All endpoints versioned (/v1/, /v2/)

2. **Data Layer**
   - PostgreSQL for transactional data
   - Redis for caching (TTL: 5 minutes default)
   - S3 for artifacts (lifecycle: 90 days)
   - No data stored in application memory

3. **Error Handling**
   - Use custom exception hierarchy (AppException)
   - Return RFC 7807 problem details
   - Log all errors with request_id
   - Never expose internal errors to users

## Forbidden Practices

- ❌ No raw SQL in business logic
- ❌ No print() statements (use logger)
- ❌ No global variables
- ❌ No synchronous I/O in async functions
```

**Don't:**

```markdown
# Bad Constitution Example

## Rules

- Write good code
- Use best practices
- Make it fast
- Keep it simple
- Test everything
```

**Why it's bad:** Vague, unenforceable, no concrete standards

### How to Write Good Specifications

**Do:**

```markdown
# Good Specification Example

## Requirement: User Authentication

### Functional Behavior

When a user submits login credentials:

1. System validates email format (RFC 5322)
2. System checks password against bcrypt hash
3. On success: Returns JWT token (expiry: 24h)
4. On failure: Returns 401 with error code

### Edge Cases

- **Account locked:** Return 423 after 5 failed attempts
- **Email not verified:** Return 403 with verification_required
- **Password expired:** Return 403 with password_reset_required

### Non-Functional Requirements

- Response time: <200ms (p95)
- Rate limit: 5 attempts per IP per minute
- Token rotation: Every 12 hours
- Audit log: All login attempts

### Acceptance Criteria

1. Valid credentials return JWT token
2. Invalid credentials return 401
3. Locked account returns 423
4. Rate limit blocks after 5 attempts
5. All attempts logged with IP, timestamp, result
6. Response time <200ms in 95% of requests
```

**Don't:**

```markdown
# Bad Specification Example

## User Login

Users should be able to log in with email and password.
The system should return a token if successful.
Failed logins should show an error.
```

**Why it's bad:** No edge cases, no metrics, no acceptance criteria

### Task Estimation Guidelines

**How to Estimate:**

1. **Break down to smallest units** (<4 hours each)
2. **Include testing time** (usually 30-50% of dev time)
3. **Add buffer for unknowns** (20% for new tech)
4. **Consider dependencies** (waiting time)

**Estimation Formula:**

```
Total = (Development + Testing + Integration) × Complexity Factor

Complexity Factors:
- Familiar tech: 1.0x
- New library: 1.2x
- New paradigm: 1.5x
- Research required: 2.0x
```

**Example:**

```
Task: Implement OAuth2 callback handler

Development:
- Parse callback parameters (30 min)
- Validate state token (30 min)
- Exchange code for token (1 hour)
- Store user session (1 hour)
= 3 hours

Testing:
- Unit tests for validation (1 hour)
- Integration test for flow (1 hour)
= 2 hours

Total: 5 hours
Complexity: New to OAuth (1.5x)
Final Estimate: 7.5 hours → Round to 8 hours
```

### Using Task Watchdog Effectively

**Start watchdog before execution:**

```bash
dev-kid watchdog-start
```

**Interpreting warnings:**

```
[14:30:00] ⚠️  WARNING: Task 1.1 at 125% of estimate
```

**Action:** Review progress, decide if task needs more time or re-scoping

```
[15:00:00] ⚠️  ALERT: Task 1.1 at 150% of estimate
```

**Action:** Stop task, reassess estimate, possibly split into subtasks

**Updating estimates mid-execution:**

```bash
# If task clearly underestimated
dev-kid update-estimate --task 1.1 --hours 6

# Watchdog recalculates thresholds
```

---

## Common Pitfalls & Solutions

### Pitfall 1: Vague Specifications

**Symptom:**

```markdown
Specification: "Add caching to improve performance"
```

**Problem:**
- What should be cached?
- How long?
- What invalidation strategy?
- What performance improvement is expected?

**Solution:**

```markdown
Specification: "Add Redis caching to product API"

Functional Requirements:
- Cache GET /products/:id responses
- Cache GET /products (list) with pagination
- TTL: 5 minutes for detail, 1 minute for list
- Invalidate on POST/PUT/DELETE operations

Performance Requirements:
- p95 latency: <50ms (cached) vs <200ms (uncached)
- Cache hit ratio: >80%

Edge Cases:
- Cache miss: Fetch from database, populate cache
- Cache error: Fall back to database, log error
- Stale data: Background refresh before TTL expiry
```

### Pitfall 2: Skipping Clarification Phase

**Symptom:**

Agent implements feature, then discovers ambiguities:
- "Should this support concurrent users?"
- "What happens if the API is down?"
- "How big can the file upload be?"

**Problem:** Implementation has to be redone

**Solution:**

Always run `/speckit.clarify` and ask:
- What are the edge cases?
- What are the failure modes?
- What are the performance expectations?
- What are the security implications?

### Pitfall 3: Ignoring Constitution Rules

**Symptom:**

Checkpoint fails with:

```
Constitution Violations:
- Uses print() instead of logger
- Synchronous I/O in async function
- No type hints on functions
```

**Problem:** Code doesn't match project standards

**Solution:**

Before starting implementation:
1. Read the constitution
2. Understand the rules
3. Set up linters/formatters to enforce rules
4. Run pre-commit hooks

### Pitfall 4: Not Using Task Watchdog

**Symptom:**

Tasks take 3x longer than estimated, no one notices until wave is complete.

**Problem:** Can't adjust plans mid-execution

**Solution:**

1. Always start watchdog: `dev-kid watchdog-start`
2. Review warnings immediately
3. Update estimates if needed
4. Split tasks that are too large

### Pitfall 5: Poor Task Breakdown

**Symptom:**

```json
{
  "task_id": "1.1",
  "title": "Implement entire feature",
  "estimated_hours": 40
}
```

**Problem:**
- Can't track progress
- Can't parallelize
- Checkpoint too coarse-grained

**Solution:**

Break into waves and smaller tasks:

```json
{
  "wave_1": {
    "tasks": [
      {
        "task_id": "1.1",
        "title": "Implement data models",
        "estimated_hours": 3
      },
      {
        "task_id": "1.2",
        "title": "Create API endpoints",
        "estimated_hours": 4
      }
    ]
  },
  "wave_2": {
    "tasks": [
      {
        "task_id": "2.1",
        "title": "Add business logic",
        "estimated_hours": 5
      }
    ]
  }
}
```

**Rule of thumb:** No task >4 hours

### Pitfall 6: Skipping Verification

**Symptom:**

Implementation "looks done" but:
- Acceptance criteria not all met
- Edge cases not tested
- Performance requirements not validated

**Problem:** Feature is incomplete

**Solution:**

Always run `/speckit.verify-implementation` before finalizing:

```bash
/speckit.verify-implementation .speckit/specs/your-feature.md
```

Don't skip even if "everything looks good"

### Pitfall 7: Over-Engineering

**Symptom:**

Specification includes:
- Future features "just in case"
- Abstractions for "flexibility"
- "Framework" for one use case

**Problem:** Takes 3x longer, delivers no value

**Solution:**

Apply YAGNI (You Ain't Gonna Need It):
- Only implement current requirements
- Mark future work as "Out of Scope"
- Defer abstractions until second use case

**Good scope:**

```markdown
## Scope

In Scope:
- OAuth2 authentication for Google
- User profile sync
- Token refresh

Out of Scope:
- Other OAuth providers (future)
- SSO integration (future)
- Profile editing (separate feature)
```

---

## Quick Reference

### Command Cheat Sheet

```bash
# ============================================
# Speckit Commands (in Claude Code chat)
# ============================================

# 1. Create project constitution
/speckit.constitution

# 2. Create feature specification
/speckit.specify

# 3. Clarify ambiguities in spec
/speckit.clarify .speckit/specs/your-feature.md

# 4. Create execution plan
/speckit.plan .speckit/specs/your-feature.md

# 5. Convert plan to dev-kid format
/speckit.tasks .speckit/plans/your-feature-plan.md

# 6. Verify implementation
/speckit.verify-implementation .speckit/specs/your-feature.md

# ============================================
# dev-kid Commands (in terminal)
# ============================================

# Validate execution plan
dev-kid orchestrate

# Start task time monitoring
dev-kid watchdog-start

# Execute specific wave
dev-kid execute --wave 1
dev-kid execute --wave 2

# Execute all waves
dev-kid execute --all

# Update task estimate mid-execution
dev-kid update-estimate --task 1.1 --hours 6

# Retry failed wave
dev-kid execute --wave 1 --retry

# Finalize implementation
dev-kid finalize

# Show execution status
dev-kid status

# Show execution history
dev-kid history
```

### File Structure Reference

```
project-root/
├── .speckit/
│   ├── constitution.md                    # Project rules & standards
│   ├── specs/                             # Feature specifications
│   │   ├── feature-a.md
│   │   └── feature-b.md
│   └── plans/                             # Execution plans
│       ├── feature-a-plan.md
│       └── feature-b-plan.md
│
├── .team-orchestrator/
│   ├── execution_plan.json                # Current orchestration plan
│   ├── checkpoints/                       # Wave completion records
│   │   ├── wave-1-checkpoint.json
│   │   └── wave-2-checkpoint.json
│   └── snapshots/                         # Session snapshots
│       └── feature-a-2025-01-06.json
│
├── src/                                   # Source code
│   ├── services/
│   ├── models/
│   └── api/
│
├── tests/                                 # Tests
│   ├── unit/
│   └── integration/
│
└── docs/                                  # Documentation
    └── features/
```

### Agent Specializations

| Agent | Specialization | Typical Tasks |
|-------|----------------|---------------|
| **backend-engineer** | Server-side logic, APIs, databases | API endpoints, business logic, database queries |
| **frontend-engineer** | UI components, client-side logic | React components, state management, styling |
| **data-engineer** | Data pipelines, ETL, analytics | Data transformations, batch jobs, data quality |
| **devops-engineer** | Infrastructure, deployment, monitoring | CI/CD, Docker, Kubernetes, observability |
| **qa-engineer** | Testing, quality assurance | Integration tests, E2E tests, test plans |
| **security-engineer** | Security, authentication, authorization | Auth flows, encryption, vulnerability fixes |
| **tech-writer** | Documentation, guides | API docs, user guides, README files |

### Execution Plan JSON Schema

```json
{
  "project": "string (feature name)",
  "constitution": "string (path to constitution)",
  "specification": "string (path to spec)",
  "total_estimated_hours": "number",
  "waves": [
    {
      "wave_id": "number",
      "name": "string",
      "tasks": [
        {
          "task_id": "string (e.g., '1.1')",
          "title": "string",
          "assigned_agent": "string (agent specialization)",
          "estimated_hours": "number",
          "dependencies": ["array of task_ids"],
          "deliverables": ["array of file paths"],
          "acceptance_criteria": ["array of criteria"],
          "constitution_requirements": ["array of rules"]
        }
      ]
    }
  ]
}
```

### Checkpoint Validation Checklist

For each wave, checkpoint validates:

- [ ] All tasks completed
- [ ] All deliverables created
- [ ] All acceptance criteria met
- [ ] Constitution requirements followed
- [ ] Tests passing (>80% coverage)
- [ ] No new errors introduced
- [ ] Documentation updated

### Verification Checklist

Before running `/speckit.verify-implementation`:

- [ ] All waves executed and checkpoints passed
- [ ] All tests passing locally
- [ ] No TODO/FIXME comments in production code
- [ ] Documentation complete
- [ ] No constitution violations
- [ ] Performance requirements met
- [ ] Security requirements met
- [ ] Edge cases tested

---

## Summary

This workflow ensures:

1. **Requirements are concrete** before coding starts (Speckit)
2. **Work is organized** into manageable, parallelizable tasks (dev-kid)
3. **Quality is enforced** at every checkpoint (constitution + verification)
4. **Progress is tracked** with realistic estimates (task watchdog)
5. **Implementation is verified** against original requirements

**Key Success Factors:**

- Write detailed constitutions upfront
- Don't skip the clarification phase
- Break tasks into <4 hour chunks
- Always use task watchdog
- Validate at every checkpoint
- Verify before finalizing

**When done right, this workflow:**

- Reduces rework by 80%+
- Prevents scope creep
- Catches bugs early
- Maintains consistent quality
- Provides predictable delivery

---

## Next Steps

1. **Review existing projects** - Do you have a constitution? If not, create one
2. **Start small** - Pick a medium-sized feature to test the workflow
3. **Refine your process** - Adjust based on what works for your team
4. **Train your team** - Share this guide and run a practice session
5. **Integrate with CI/CD** - Automate constitution validation in pipelines

**Questions?**

Refer to:
- Speckit documentation: [GitHub Spec-Driven Development]
- dev-kid repository: `/home/gyasis/Documents/code/dev-kid`
- Team orchestrator docs: `.team-orchestrator/README.md`

---

**Document Version:** 1.0
**Last Updated:** 2025-01-06
**Maintainer:** Development Team

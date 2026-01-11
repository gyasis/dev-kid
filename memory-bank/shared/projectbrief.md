# Project Brief: Dev-Kid v2.0

## Vision

Dev-Kid is a complete development workflow system for Claude Code that transforms AI-assisted development through persistent memory, intelligent task orchestration, and context compression resilience. The system enables AI agents to work like experienced developers with institutional memory and systematic workflow patterns.

## Mission

Provide a zero-configuration, maximum automation development framework that:
- Maintains persistent institutional memory across sessions
- Orchestrates complex tasks with wave-based parallelization
- Protects against context compression through disk-based state management
- Automates common workflows through auto-activating skills
- Creates semantic checkpoints with git integration

## Core Problems Solved

### 1. Context Compression Memory Loss
**Problem**: AI agents lose context during long sessions, forgetting earlier work and decisions.

**Solution**: Memory Bank system with 6-tier architecture persisting project knowledge, active context, and progress to disk. Git checkpoints preserve state at every milestone.

### 2. Sequential Task Bottlenecks
**Problem**: Tasks executed linearly even when many could run in parallel, wasting time and agent capacity.

**Solution**: Wave-based orchestration with automatic dependency analysis and file lock detection. Tasks are intelligently grouped into parallel execution waves.

### 3. Forgotten Long-Running Tasks
**Problem**: Tasks start but agents forget to complete them, especially during context compression.

**Solution**: Process-based Task Watchdog that runs as background daemon, survives compression, and monitors task timing with 5-minute check intervals.

### 4. Workflow Repetition
**Problem**: Common workflows (checkpoints, memory sync, verification) require manual execution and coordination.

**Solution**: Skills layer with auto-activating Bash scripts that encapsulate common patterns and trigger based on keywords.

### 5. Race Conditions in Parallel Work
**Problem**: Multiple agents editing the same file simultaneously causes conflicts and lost work.

**Solution**: File lock detection in orchestrator prevents tasks modifying the same file from running in the same wave.

### 6. Lost Session Context
**Problem**: Resuming work after breaks requires manual reconstruction of mental state and progress.

**Solution**: Session snapshots with finalize/recall pattern capture complete mental state, progress, blockers, and next steps.

## Key Features

### Wave-Based Task Orchestration
- Converts linear task lists into parallelized execution waves
- Automatic dependency analysis (explicit and implicit)
- File lock detection prevents race conditions
- Mandatory checkpoint verification between waves
- Real-time progress tracking

### Task Watchdog (Context Compression Resilient)
- Background process-based monitoring (not token-dependent)
- 5-minute check intervals for running tasks
- 7-minute guideline for task completion (check-in point)
- Automatic detection of stalled tasks (>15 min)
- Syncs with tasks.md for completion tracking
- State persisted to disk (survives compression)

### Memory Bank (6-Tier Architecture)
- **Shared Layer**: Team knowledge (projectbrief, systemPatterns, techContext, productContext)
- **Private Layer**: Per-user context (activeContext, progress, worklog)
- Markdown format for human and AI readability
- Git-tracked for version control
- Updated automatically through skills

### Context Protection
- **Active Stack**: <500 token current focus
- **Activity Stream**: Append-only event log
- **Agent State**: Multi-agent coordination
- **System Bus**: Inter-agent messaging
- **Session Snapshots**: Zero-loss recovery points

### Skills Layer
- **sync_memory**: Update Memory Bank with current state
- **checkpoint**: Create semantic git checkpoints
- **verify_existence**: Anti-hallucination file verification
- **maintain_integrity**: System validation
- **finalize_session**: Create session snapshot
- **recall**: Resume from last snapshot

### Git Integration
- Semantic checkpoints with standardized format
- Post-commit hooks for automatic activity logging
- Co-author attribution for AI collaboration
- No destructive operations (no force, no hard reset)

## Target Users

### Primary: AI Agents (Claude Code)
- Need persistent memory across sessions
- Require structured workflow patterns
- Must coordinate with other agents
- Benefit from automated checkpointing

### Secondary: Human Developers
- Want AI collaboration with institutional memory
- Need to resume work after breaks
- Desire systematic workflow automation
- Value git-based progress tracking

## Success Metrics

### Quantitative
- **Planning Overhead**: <10% of context window used for coordination
- **Task Completion Rate**: >95% of started tasks completed
- **Context Recovery Time**: <1 minute to resume from snapshot
- **Parallel Efficiency**: 2-4x speedup for independent tasks
- **Memory Bank Freshness**: Updated within 5 minutes of changes

### Qualitative
- Zero manual configuration required
- Works with any tech stack/project size
- Clear progress visibility at all times
- Reproducible across projects
- Fail-safe execution with verification

## Design Principles

### 1. Zero Configuration, Maximum Automation
One command installs everything. No manual setup. Works immediately in any project.

### 2. Reproducible Across Projects
Same workflow works for Python, JavaScript, Go, Rust, or any codebase. Universal patterns.

### 3. Context Compression Resilient
All critical state persisted to disk (git, JSON, Markdown). Process-based monitoring survives compression.

### 4. Token Efficient
Planning overhead <10% of context window. Skills auto-activate without coordination tokens.

### 5. Git-Centric
Every checkpoint is a git commit. History is the source of truth. Rollback to any wave.

### 6. Fail-Safe
Verification before progression. No silent failures. Clear error messages with next steps.

### 7. Human and AI Readable
Markdown for documentation. JSON for state. Clear schemas. Easy to inspect and debug.

## Technical Architecture

### Execution Flow
```
tasks.md → orchestrator.py → execution_plan.json → wave_executor.py
              ↓                                           ↓
          Wave Analysis                          Wave Execution + Checkpoints
```

### Technology Stack
- **CLI**: Bash 4.0+ (portability, system integration)
- **Orchestration**: Python 3.7+ standard library only (no external deps)
- **Skills**: Bash scripts (simple, portable, easy to maintain)
- **State**: JSON files (universal, portable, human-readable)
- **Memory**: Markdown files (git-friendly, AI-friendly, human-friendly)
- **Version Control**: Git 2.0+ (checkpoints, history, rollback)

### Component Responsibilities
- **CLI Layer**: Command routing, user interaction, delegation
- **Orchestrator**: Task parsing, dependency analysis, wave creation
- **Wave Executor**: Sequential wave execution, verification, checkpoints
- **Task Watchdog**: Background monitoring, timing, completion detection
- **Skills Layer**: Workflow automation, auto-activation, git integration
- **Memory Bank**: Institutional memory, context preservation
- **Context Protection**: Active state, coordination, session snapshots

## Constraints and Limitations

### Current Constraints
- **Task Scale**: O(n²) dependency analysis, practical limit ~1000 tasks
- **Wave Execution**: Sequential (one wave at a time), not multi-process
- **Watchdog Interval**: 5-minute checks, not real-time
- **Platform**: Unix-like systems only (Linux, macOS)
- **Python**: Requires Python 3.7+ (standard library only)

### Deliberate Limitations
- **No Network Calls**: All operations local for privacy and reliability
- **No External Dependencies**: Python standard library only
- **No Configuration Files**: Zero config by design
- **No Database**: File-based state for simplicity
- **No GUI**: CLI-only for automation and scriptability

## Future Evolution

### Planned Enhancements
- **Constitution System**: Project-specific rules and standards enforcement
- **Config Management**: Centralized configuration for teams
- **Enhanced Reporting**: Task timing analytics, bottleneck detection
- **Multi-Project Support**: Shared Memory Bank across related projects
- **Integration Tests**: Automated full workflow testing

### Potential Extensions
- **Distributed Execution**: Multi-machine wave execution
- **Plugin System**: Dynamic skill loading and registration
- **Web Dashboard**: Real-time monitoring UI
- **Cloud Sync**: Memory Bank synchronization across machines
- **Advanced Metrics**: Performance analytics and optimization suggestions

## Project Status

**Version**: 2.0.0 (Complete)
**Maturity**: Production-ready
**Stability**: Core features stable and tested
**Documentation**: Comprehensive (7+ reference documents)

## Key Documents

- **README.md**: User-facing quickstart guide
- **DEV_KID.md**: Complete implementation reference (1,680 lines)
- **ARCHITECTURE.md**: System architecture deep dive
- **CLI_REFERENCE.md**: Command-line interface reference
- **SKILLS_REFERENCE.md**: Skills documentation
- **CLAUDE.md**: Project instructions for AI agents
- **CONTRIBUTING.md**: Contribution guidelines
- **DEPENDENCIES.md**: System requirements

---

**Dev-Kid v2.0** - Transforming AI-Assisted Development Through Persistent Memory and Intelligent Orchestration

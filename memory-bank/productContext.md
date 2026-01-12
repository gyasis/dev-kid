# Product Context: Dev-Kid v2.0

## Why This Project Exists

### The Problem

When working with Claude Code, developers face several critical challenges:

1. **Context Compression**: Claude's context window resets during compression, losing institutional knowledge
2. **Linear Execution**: Tasks are executed sequentially even when they could run in parallel
3. **Manual Checkpointing**: Developers must manually create git commits and update documentation
4. **Knowledge Loss**: Decisions, patterns, and progress disappear between sessions
5. **No Workflow Structure**: Projects lack systematic execution patterns

### The Solution

Dev-Kid provides a structured development environment with:

1. **Memory Bank**: 6-tier persistent knowledge system that survives context compression
2. **Wave Orchestration**: Automatic task parallelization with file lock detection
3. **Automated Checkpointing**: Git commits created after each wave with verification
4. **Task Watchdog**: Background monitoring that survives context compression
5. **Auto-Triggering Skills**: Workflows activate automatically based on file conditions

## User Personas

### Primary: Senior Software Developer
- **Goal**: Maintain project velocity with Claude Code assistance
- **Pain Points**: Context loss, manual checkpointing, workflow coordination
- **Value**: Automated workflow, persistent memory, parallel execution

### Secondary: Engineering Team Lead
- **Goal**: Standardize development workflows across team
- **Pain Points**: Inconsistent practices, knowledge silos
- **Value**: Reproducible workflows, constitution enforcement, documentation

## Use Cases

### 1. Feature Development
**Scenario**: Developer needs to implement a multi-file feature
**Workflow**:
1. Create tasks.md with feature tasks
2. System auto-orchestrates into parallelized waves
3. Execute waves with automatic checkpointing
4. Memory bank preserves decisions and patterns
5. Constitution enforces quality standards

### 2. Bug Investigation
**Scenario**: Debugging a production issue across multiple files
**Workflow**:
1. Document investigation steps in tasks.md
2. Task watchdog monitors investigation time
3. Checkpoint discoveries at each stage
4. Memory bank captures insights
5. Resume investigation after context compression

### 3. Codebase Onboarding
**Scenario**: New developer joining existing project
**Workflow**:
1. Initialize dev-kid in project
2. Memory bank automatically populated from git history
3. Skills provide guided workflow
4. Documentation auto-generated from structure

### 4. Multi-Branch Development
**Scenario**: Working on multiple features simultaneously
**Workflow**:
1. Speckit manages feature specifications per branch
2. Git hooks auto-sync tasks.md when switching branches
3. Progress preserved per branch
4. Memory bank tracks context across branches

## Market Position

### Competitive Landscape
- **Traditional IDEs**: No AI integration, manual workflows
- **GitHub Copilot**: Code completion only, no workflow orchestration
- **Cursor AI**: Conversational but no structured workflows
- **Claude Code (vanilla)**: Conversational but context-limited

### Differentiation
- **Only solution** with context-compression-resilient memory
- **Only solution** with automatic wave-based parallelization
- **Only solution** with process-based task monitoring
- **Only solution** with constitution enforcement pipeline

## Product Strategy

### Core Principles
1. **Zero Configuration**: Works immediately after one-command install
2. **Token Efficiency**: Minimal overhead (<10% context window)
3. **Git-Centric**: Every checkpoint is a verifiable commit
4. **Fail-Safe**: Verification before progression
5. **Reproducible**: Same workflow across all projects

### Feature Priorities
1. Core orchestration and checkpointing (COMPLETE)
2. Memory bank persistence (COMPLETE)
3. Task watchdog monitoring (COMPLETE)
4. Constitution enforcement (COMPLETE)
5. Speckit integration (COMPLETE)
6. Skills and commands (COMPLETE)
7. Advanced analytics (FUTURE)
8. Multi-repository support (FUTURE)

## Success Metrics

### Technical Metrics
- Wave orchestration accuracy: >95% (file lock detection)
- Checkpoint success rate: 100% (verification-gated)
- Memory bank persistence: 100% (survives compression)
- Skill activation rate: >90% (auto-trigger accuracy)

### User Metrics
- Time to first checkpoint: <5 minutes
- Context recovery time: <2 minutes (from memory bank)
- Workflow reproducibility: 100% (across projects)
- Documentation completeness: >80% (auto-generated)

## Product Evolution

### v1.0 (Complete)
- Basic orchestration
- Memory bank foundation
- Manual checkpointing

### v2.0 (Current - Complete)
- Auto-triggering skills
- Claude Code commands
- Speckit integration
- Constitution enforcement
- Branch-based isolation
- Complete documentation

### v2.1 (Planned)
- Advanced analytics
- Performance optimization
- Multi-repository orchestration
- GUI dashboard

## Integration Strategy

### Speckit Integration
- **Seamless Workflow**: Spec → Tasks → Waves → Execution → Checkpoint
- **Branch Isolation**: Each feature branch has independent tasks.md
- **Constitution Enforcement**: Quality standards from planning through execution
- **Progress Preservation**: Work preserved across branch switches

### Claude Code Integration
- **Skills**: Auto-activate on file conditions
- **Commands**: Manual slash commands for control
- **Progressive Disclosure**: Token savings through lazy loading
- **Context Protection**: Memory bank reduces re-explanation

## Risk Mitigation

### Technical Risks
- **Context Compression**: Mitigated by disk-persisted state (git, JSON, Memory Bank)
- **File Lock Detection**: Mitigated by regex patterns and backtick convention
- **Process Management**: Mitigated by proper signal handling and state files

### Adoption Risks
- **Learning Curve**: Mitigated by comprehensive documentation and auto-triggering
- **Installation Complexity**: Mitigated by single-command install script
- **Migration Cost**: Mitigated by zero-configuration design

## Future Vision

Dev-Kid becomes the standard workflow system for AI-assisted development, enabling:
- Multi-agent collaboration with preserved context
- Cross-project pattern discovery and reuse
- Automated quality enforcement
- Reproducible development workflows at scale

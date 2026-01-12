# Project Brief: Dev-Kid v2.0

## Project Identity

**Name**: Dev-Kid v2.0
**Type**: Development Workflow System for Claude Code
**Status**: Production Ready (v2.0.0)
**Repository**: /home/gyasis/Documents/code/dev-kid

## Mission Statement

Dev-Kid is a comprehensive development workflow system for Claude Code that enables wave-based task orchestration, persistent institutional memory, and context-compression-resilient automation. It transforms Claude Code from a conversational assistant into a structured development environment with checkpointed execution, automated knowledge preservation, and constitution-enforced quality standards.

## Core Value Proposition

1. **Wave-Based Orchestration**: Automatically parallelizes independent tasks while respecting file locks and dependencies
2. **Memory Bank Persistence**: Institutional memory survives context compression and session boundaries
3. **Constitution Enforcement**: Automated quality standards throughout the development pipeline
4. **Dual Interface**: Auto-triggering skills + manual slash commands for maximum flexibility
5. **Git-Centric Checkpointing**: Every wave completion creates verifiable git commits
6. **Speckit Integration**: Seamless workflow from feature planning to implementation

## Key Stakeholders

- **Primary User**: Software developers using Claude Code for project development
- **Target Environment**: Claude Code CLI (claude.ai/code)
- **Integration Partner**: Speckit (feature specification system)

## Project Scope

### In Scope
- Task orchestration and parallelization
- Memory bank management (6-tier architecture)
- Git checkpoint automation
- Task watchdog monitoring
- Constitution enforcement
- Speckit integration (branch-based isolation)
- Claude Code skills and commands
- Documentation system

### Out of Scope
- CI/CD pipeline execution
- Cloud deployment automation
- Multi-repository orchestration
- GUI interface

## Success Criteria

- [x] Zero-configuration installation (one command)
- [x] Automatic task parallelization with file lock detection
- [x] Checkpointed execution with verification
- [x] Memory bank survives context compression
- [x] Skills auto-activate on trigger conditions
- [x] Complete workflow documentation
- [x] Speckit integration with branch isolation
- [x] Constitution enforcement throughout pipeline

## Timeline

- **Project Start**: Q4 2024
- **v1.0 Release**: January 2025
- **v2.0 (Current)**: January 2025
- **Status**: Feature complete, production ready

## Resources

- **Technology Stack**: Bash, Python 3.10+, Git, Markdown
- **Dependencies**: Standard library only (zero external dependencies)
- **Installation Target**: ~/.dev-kid and ~/.claude directories
- **Documentation**: 15+ comprehensive markdown files in docs/

## Project Vision

Dev-Kid transforms Claude Code into a structured development environment where:
- Tasks are automatically parallelized and monitored
- Progress is checkpointed and verifiable
- Knowledge persists across sessions
- Quality standards are enforced automatically
- Workflows are reproducible across projects

# Product Context: Task Watchdog

## Problem Space

### The AI Context Compression Challenge

AI coding assistants (Claude Code, Gemini, etc.) have limited context windows. When conversations grow too long, context compression occurs - losing track of:
- Running background processes
- Long-running build tasks
- Container orchestration state
- Task execution history

**Impact**: AI loses awareness of what's running, causing duplicate processes, orphaned tasks, and broken workflows.

### Python Watchdog Limitations

The original Python implementation suffered from:
- Slow startup (200ms) impacting workflow responsiveness
- High memory usage (50MB) - significant for daemon process
- Runtime dependency (requires Python installation)
- GIL limitations (no true parallelism)
- Slow JSON parsing (50ms for 100KB files)

## Solution Approach

### Rust Rewrite Benefits

**Performance**: 40x faster startup, 17x less memory, 50x faster JSON parsing
**Deployment**: Single binary, no runtime dependencies
**Reliability**: Type safety, memory safety, no GIL
**Portability**: Cross-platform (Linux, macOS, Windows via WSL)

### Architecture Strategy

**Process Registry Pattern**: JSON-based state file tracks all tasks
- Task ID prefix for multi-tool support (CLAUDE-, GEMINI-, etc.)
- Hybrid execution modes (native processes, Docker containers)
- PID + start time for recycling protection
- PGID for process tree management

**Context Resilience**: State persisted to disk, survives AI resets
- Registry file at `.claude/process_registry.json`
- Rehydration command restores full context
- Auto-sync with task completion markers

## User Workflows

### Primary: Claude Code Integration

1. Start watchdog daemon (`task-watchdog run`)
2. Claude spawns background tasks (build, test, deploy)
3. Tasks registered in process registry
4. Watchdog monitors every 5 minutes
5. Context compression occurs (AI loses memory)
6. Claude runs rehydration (`task-watchdog rehydrate`)
7. Full context restored - Claude knows what's running

### Secondary: Multi-Tool Dev Environment

1. Multiple AI tools share same project (Claude + Gemini + Cursor)
2. Each tool uses prefixed task IDs in shared registry
3. Single watchdog monitors all tools' processes
4. Cross-tool visibility and resource monitoring

## Competitive Landscape

**No direct competitors** - this is novel infrastructure for AI coding tools

**Related Tools**:
- `systemd` - process management, but not AI-aware
- `supervisord` - daemon monitoring, no context rehydration
- `pm2` - Node.js process manager, wrong domain

**Unique Differentiation**: Built specifically for AI context compression resilience

## Business Context

**Open Source**: MIT license, community-driven
**Integration Point**: Part of Dev-Kid workflow system
**Ecosystem Play**: Generic enough for any AI coding tool to adopt

## Stakeholders

**Users**: Developers using AI coding assistants
**Maintainers**: Dev-Kid core team
**Integrators**: AI tool vendors (Anthropic, Google, etc.)
**Contributors**: Rust community, AI workflow enthusiasts

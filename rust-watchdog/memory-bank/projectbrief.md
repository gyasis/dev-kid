# Project Brief: Task Watchdog (Rust)

## Project Identity

**Name**: Task Watchdog (formerly Claude Watchdog)
**Version**: 2.0.0
**Language**: Rust
**License**: MIT
**Parent Project**: Dev-Kid v2.0

## Purpose

High-performance process monitoring daemon for AI coding tools, built in Rust for maximum speed and minimal resource usage. Provides context-resilient task tracking that survives AI context compression events.

## Core Value Proposition

Replace Python-based watchdog with Rust implementation delivering:
- 40x faster startup (<5ms vs 200ms)
- 17x less memory usage (<3MB vs 50MB)
- 50x faster JSON parsing
- Single binary distribution (no runtime dependencies)
- True parallelism (no GIL)

## Target Users

**Primary**: Claude Code users (Dev-Kid workflow)
**Secondary**: Any AI coding tool (Gemini Code, OpenCode, Cursor, Windsurf, Blocks)

## Design Philosophy

**Claude-First, Platform-Open**
- Branded for Claude Code recognition and primary use case
- Generic architecture allows any AI coding tool to integrate
- No tool coupling in implementation
- Configurable registry paths for separation or sharing

## Key Features

- Hybrid execution (native processes + Docker containers)
- Process tracking with PGID (process groups)
- PID recycling protection via start time validation
- Orphan/zombie detection and auto-cleanup
- CPU/memory resource monitoring
- Context rehydration after AI compression events
- Single binary deployment

## Success Criteria

- Drop-in replacement for Python watchdog in Dev-Kid
- Zero API changes for existing workflows
- Performance targets met (startup, memory, parsing)
- Cross-platform compatibility (Linux, macOS)
- Production-ready security (no shell injection, path validation)

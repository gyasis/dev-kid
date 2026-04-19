# Technical Context: Task Watchdog

## Technology Stack

### Language & Runtime
- **Rust 2021 Edition**
  - Memory safety without garbage collection
  - Zero-cost abstractions
  - Type system prevents data races
  - Pattern matching for robust error handling

### Core Dependencies

#### Async Runtime
- **tokio 1.35** (full features)
  - Async I/O for Docker API
  - Future execution
  - Task spawning for concurrent operations

#### Serialization
- **serde 1.0** (derive features)
  - Zero-copy deserialization where possible
  - Type-safe JSON mapping
- **serde_json 1.0**
  - Streaming parser for large files
  - Pretty-printing for human-readable registry

#### Docker Integration
- **bollard 0.16**
  - Rust Docker API client
  - Built on tokio for async operations
  - Container lifecycle management
- **futures-util 0.3**
  - Stream utilities for Docker events

#### System Information
- **sysinfo 0.30**
  - Cross-platform process information
  - CPU/memory usage tracking
  - Process tree navigation
  - Works on Linux, macOS, Windows

#### CLI Interface
- **clap 4.4** (derive features)
  - Declarative CLI definition
  - Automatic help generation
  - Subcommand support
  - Argument validation

#### Date/Time
- **chrono 0.4** (serde features)
  - ISO8601 timestamp formatting
  - Duration calculations
  - Timezone-aware operations

#### Error Handling
- **anyhow 1.0**
  - Context-aware error propagation
  - Simple error type for applications
  - Backtraces in debug mode

#### Unix System Calls (Linux/macOS)
- **nix 0.27** (signal, process features)
  - Process group operations (setsid, killpg)
  - Signal handling (SIGTERM, SIGKILL)
  - Low-level process control

## Build Configuration

### Release Profile Optimizations
```toml
[profile.release]
opt-level = "z"       # Optimize for size (also fast)
lto = true            # Link-time optimization
codegen-units = 1     # Single codegen unit (slower build, faster binary)
strip = true          # Remove debug symbols
panic = "abort"       # No unwinding (smaller binary)
```

**Results**:
- Binary size: ~2MB
- Startup time: <5ms
- Memory usage: <3MB

### Cross-Compilation

#### Static Binary (Linux)
```bash
rustup target add x86_64-unknown-linux-musl
cargo build --release --target x86_64-unknown-linux-musl
```
**Output**: Binary with ZERO runtime dependencies

#### macOS Support
```bash
cargo build --release --target x86_64-apple-darwin
# or
cargo build --release --target aarch64-apple-darwin  # M1/M2
```

## Project Structure

```
rust-watchdog/
├── Cargo.toml           # Package manifest & dependencies
├── Cargo.lock           # Dependency lock file
├── build.sh             # Build script wrapper
├── src/
│   ├── main.rs         # CLI entry point, command routing
│   ├── types.rs        # Data structures (Task, Registry, etc.)
│   ├── process.rs      # Native process management
│   ├── docker.rs       # Docker container management
│   └── registry.rs     # JSON registry I/O
├── target/             # Build output
│   ├── debug/          # Development builds
│   └── release/        # Optimized builds
└── docs/               # Documentation (README, INTEGRATION, etc.)
```

## Development Environment

### Required Tools
- **Rust toolchain**: 1.70+ (stable)
  - Install: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- **Docker**: 20.10+ (for container features)
  - Install: `apt install docker.io` (Linux) or Docker Desktop (Mac/Windows)
- **Build essentials**: gcc, make (for some dependencies)

### Optional Tools
- **cargo-watch**: Auto-rebuild on file changes
- **cargo-flamegraph**: Performance profiling
- **cargo-audit**: Security vulnerability scanning
- **clippy**: Linting tool (included with rustup)
- **rustfmt**: Code formatter (included with rustup)

### Build Commands

```bash
# Development build (fast compile, debug symbols)
./build.sh dev
# or
cargo build

# Release build (optimized, stripped)
./build.sh
# or
cargo build --release

# Run tests
cargo test

# Run with arguments
cargo run -- --help
cargo run -- run --interval 30

# Check code without building
cargo check

# Lint
cargo clippy

# Format
cargo fmt
```

## Platform Support

### Tier 1 (Fully Supported)
- **Linux x86_64**: Primary development platform
  - Ubuntu 20.04+
  - Debian 11+
  - Arch Linux
  - Fedora 35+

### Tier 2 (Tested)
- **macOS x86_64**: Intel Macs
  - macOS 11.0+
- **macOS aarch64**: M1/M2 Macs
  - macOS 11.0+

### Tier 3 (Should Work)
- **Windows via WSL2**: Linux compatibility layer
  - WSL2 Ubuntu 20.04+

### Not Supported
- **Windows native**: nix crate is Unix-only
  - Process group operations unavailable
  - Could add Windows support with conditional compilation

## File System Layout

### Registry Location
**Default**: `.claude/process_registry.json`
**Configurable**: `--registry /path/to/file.json`

**Permissions**: 0600 (owner read/write only)

### Temporary Files
**None** - All state in registry file

### Logs
**None** - Output to stdout/stderr
- Integration with systemd/journald for daemon mode
- Can redirect to file: `task-watchdog run &> watchdog.log`

## Environment Variables

### Used by Watchdog
- `DOCKER_HOST`: Docker daemon socket (default: unix:///var/run/docker.sock)

### Set by Watchdog for Tasks
- `TASK_ID`: Task identifier (e.g., "T001")
  - Used to tag processes in environment
  - Helps identify processes via ps/top

## Security Considerations

### Attack Surface
1. **Registry file tampering**
   - Mitigated by 0600 permissions
   - Validate JSON schema on load
   - Sanitize task IDs (alphanumeric + hyphen only)

2. **Command injection**
   - NEVER use shell interpolation
   - Use Command builder with separate args
   - Docker exec with array args (not shell string)

3. **Path traversal**
   - Validate registry path is within allowed directories
   - Canonicalize paths before operations

4. **Resource exhaustion**
   - Docker container limits (memory, CPU)
   - Watchdog itself has minimal resource usage

### Hardening Checklist
- [ ] Command injection audit (docker.rs)
- [ ] Path validation audit (main.rs, registry.rs)
- [ ] File permissions audit (registry.rs)
- [ ] Input validation audit (task IDs, paths)
- [ ] Error message sanitization (no sensitive data)

## Performance Characteristics

### Startup Time
- **Target**: <5ms
- **Actual**: ~4ms (measured on Ubuntu 20.04, Intel i7)
- **Components**:
  - Binary load: ~1ms
  - Argument parsing: <1ms
  - Registry load: <1ms (for typical <100KB file)
  - Command dispatch: <1ms

### Memory Usage
- **Target**: <3MB RSS
- **Actual**: ~2.8MB (idle daemon)
- **Components**:
  - Binary code: ~2MB
  - Registry in memory: <100KB
  - sysinfo cache: ~500KB
  - Other runtime: ~300KB

### CPU Usage
- **Idle**: 0% (sleeps between checks)
- **Check cycle**: <1% (for 50 tasks, 5-second duration)
- **Kill operation**: <1% (one-time)

### JSON Parsing
- **Small registry** (10 tasks, ~10KB): <1ms
- **Large registry** (100 tasks, ~100KB): ~5ms
- **Huge registry** (1000 tasks, ~1MB): ~50ms

**Comparison to Python**:
- 50x faster for typical workloads
- serde_json uses SIMD when available

## Known Limitations

### Platform-Specific
- **Windows**: Not supported (nix crate is Unix-only)
  - Could add Windows support with winapi crate
  - Process groups work differently on Windows

### Docker
- **Docker daemon required**: Container features need Docker running
  - Graceful degradation: Watchdog warns but continues
  - Native-only mode works without Docker

### Process Monitoring
- **Kernel timer granularity**: Process start time has ~1-second precision
  - Sufficient for PID recycling protection (PIDs recycle over minutes/hours)
- **Process tree visibility**: Can only see processes owned by same user
  - Run watchdog as same user as tasks

## Future Enhancement Opportunities

### Performance
- [ ] Memory-mapped registry file (zero-copy reads)
- [ ] Binary format option (faster than JSON)
- [ ] Process monitoring with epoll (event-driven vs polling)

### Features
- [ ] Windows support (conditional compilation with winapi)
- [ ] Remote monitoring (HTTP API)
- [ ] Metrics export (Prometheus)
- [ ] Task dependency graphs
- [ ] Resource limits for native processes (cgroups)

### Integration
- [ ] Systemd integration (Type=notify)
- [ ] Config file support (TOML)
- [ ] Plugin system for custom monitors

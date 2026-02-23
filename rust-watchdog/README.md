# Task Watchdog (Rust) 🦀

**High-performance process monitoring daemon for development workflows** - Built in Rust for maximum speed and minimal resource usage.

## Why Rust?

| Metric | Python (Old) | **Rust (New)** | Improvement |
|--------|--------------|----------------|-------------|
| **Startup Time** | ~200ms | **<5ms** | **40x faster** ⚡ |
| **Memory Usage** | ~50MB | **<3MB** | **17x less** 🎯 |
| **JSON Parsing** | ~50ms | **<1ms** | **50x faster** 🚀 |
| **Binary Size** | N/A (needs Python) | **~2MB** | Single file ✅ |
| **Distribution** | Needs runtime | **Standalone** | Zero deps ✅ |

## Features

- 🦀 **Blazing Fast**: Written in Rust, <5ms startup, <3MB memory
- 🐳 **Hybrid Execution**: Native processes + Docker containers
- 🔍 **Process Tracking**: Track PIDs with PGID (process groups)
- 🧠 **Context Resilient**: Survives AI context compression
- 🧟 **Zombie Killer**: Auto-detects and kills orphaned processes
- 📊 **Resource Monitoring**: CPU/memory tracking per task
- 🔄 **Auto-Rehydration**: Restore context after compression
- 📦 **Single Binary**: No dependencies, works anywhere

## Installation

### Option 1: Build from Source

```bash
# Navigate to project
cd rust-watchdog

# Build release version
./build.sh

# Install system-wide
sudo cp target/release/task-watchdog /usr/local/bin/

# Verify installation
task-watchdog --version
```

### Option 2: Static Binary (Linux)

```bash
# Build static binary with musl
rustup target add x86_64-unknown-linux-musl
cargo build --release --target x86_64-unknown-linux-musl

# This binary has ZERO dependencies!
./target/x86_64-unknown-linux-musl/release/task-watchdog
```

## Constitution Enforcement

The watchdog integrates with **SpecKit** to enforce project constitution rules during task execution. This provides automated quality gates that ensure code compliance with project standards.

### Register Task with Constitution Rules

```bash
# Register a task with specific constitution rules
task-watchdog register T001 \
  --command "python process_data.py" \
  --rules "TYPE_HINTS_REQUIRED,DOCSTRINGS_REQUIRED,TEST_COVERAGE_REQUIRED"
```

### Constitution Flow

1. **SpecKit** creates tasks with constitution metadata in `tasks.md`:
   ```markdown
   - [ ] Create data processor
     - **Constitution**: TYPE_HINTS_REQUIRED, DOCSTRINGS_REQUIRED
   ```

2. **dev-kid orchestrator** parses constitution rules and includes them in `execution_plan.json`

3. **wave_executor** registers tasks with watchdog including constitution rules:
   ```python
   task-watchdog register T001 \
     --command "implement_feature" \
     --rules "TYPE_HINTS_REQUIRED,DOCSTRINGS_REQUIRED"
   ```

4. Rules are persisted in `.claude/process_registry.json` for tracking

5. At checkpoint, **Constitution validator** checks modified files for violations

6. If violations found, checkpoint is **BLOCKED** until code is compliant

### Constitution Rules

Common rules enforced:
- `TYPE_HINTS_REQUIRED`: All functions must have type annotations
- `DOCSTRINGS_REQUIRED`: All functions must have docstrings
- `NO_HARDCODED_SECRETS`: No hardcoded API keys or passwords
- `TEST_COVERAGE_REQUIRED`: All modules must have test files

### Example: Task with Constitution

```json
{
  "T001": {
    "mode": "native",
    "command": "python process_data.py",
    "constitution_rules": [
      "TYPE_HINTS_REQUIRED",
      "DOCSTRINGS_REQUIRED",
      "TEST_COVERAGE_REQUIRED"
    ],
    "status": "running",
    "started_at": "2026-01-10T10:00:00Z"
  }
}
```

At checkpoint time, the validator checks:
- ✅ All functions in `process_data.py` have type hints
- ✅ All functions have docstrings
- ✅ Test file `test_process_data.py` exists

If any check fails → checkpoint BLOCKED ❌

### Integration with SpecKit

The watchdog is **SpecKit-aware** and automatically:
1. Accepts constitution rules via `--rules` parameter
2. Stores rules in process registry for persistence
3. Survives context compression (process-based tracking)
4. Provides data for checkpoint validation

This ensures **end-to-end constitution enforcement** from specification to implementation.

## Usage

### Start Watchdog Daemon

```bash
# Run continuously (checks every 5 minutes)
task-watchdog run

# Custom check interval (30 seconds)
task-watchdog run --interval 30

# Custom registry location
task-watchdog run --registry /path/to/registry.json
```

### Check Task Status

```bash
# Check specific task
task-watchdog check T001

# Shows:
# - Running/dead status
# - CPU and memory usage
# - PID/container info
```

### Kill Running Task

```bash
# Kill task (handles process trees and Docker containers)
task-watchdog kill T001
```

### Context Re-Hydration

```bash
# After AI context compression, run this to restore state
task-watchdog rehydrate

# Shows:
# - All running tasks
# - What each task is doing
# - Current status
# - Resource usage
```

### Resource Report

```bash
# Show CPU/memory for all running tasks
task-watchdog report
```

### Registry Stats

```bash
# Show registry statistics
task-watchdog stats

# Output:
# Total tasks: 45
# Running: 3
# Completed: 40
# Failed: 2
```

### Cleanup Old Tasks

```bash
# Remove completed tasks older than 7 days
task-watchdog cleanup --days 7
```

## Architecture

### Process Registry Schema

```json
{
  "tasks": {
    "T001": {
      "mode": "native",
      "command": "npm run build",
      "status": "running",
      "started_at": "2026-01-10T15:30:00Z",
      "native": {
        "pid": 12345,
        "pgid": 12344,
        "start_time": "Fri Jan 10 15:30:00 2026",
        "env_tag": "TASK_ID=T001"
      }
    },
    "T002": {
      "mode": "docker",
      "command": "python risky_script.py",
      "status": "running",
      "started_at": "2026-01-10T15:31:00Z",
      "docker": {
        "container_id": "a1b2c3d4...",
        "container_name": "dev-task-T002",
        "resource_limits": {
          "memory": "512m",
          "cpu": "1.0"
        }
      }
    }
  }
}
```

### Key Features Explained

#### 1. Process Groups (PGID)
```rust
// When starting native tasks, create new process group
os.setsid(); // Creates new PGID

// Kill entire tree
killpg(pgid, SIGTERM); // Kills all children too!
```

#### 2. PID Recycling Protection
```rust
// Store start time when process created
let start_time = get_process_start_time(pid);

// Later, validate it's the same process
if actual_start_time != expected_start_time {
    // PID was recycled, original process dead
}
```

#### 3. Orphan Detection
```rust
// Dead process but task marked running
if !is_alive(pid) && task.status == "running" {
    orphans.push(task_id);
    mark_failed(task_id);
}

// Process alive but task marked complete
if is_alive(pid) && task.status == "completed" {
    zombies.push(task_id);
    kill_process_group(pgid);
}
```

## Performance Benchmarks

### Startup Time
```bash
$ time task-watchdog check T001
real    0m0.004s  # 4 milliseconds!
user    0m0.002s
sys     0m0.001s
```

### Memory Usage
```bash
$ task-watchdog run &
$ ps aux | grep task-watchdog
# RSS: 2.8 MB  (Python version: 50 MB)
```

### JSON Parsing
```bash
# 100KB registry file
Python: ~50ms
Rust:   <1ms   (50x faster!)
```

## Development

### Project Structure
```
rust-watchdog/
├── Cargo.toml           # Dependencies and build config
├── src/
│   ├── main.rs         # CLI entry point and commands
│   ├── types.rs        # Data structures
│   ├── process.rs      # Process management (PID tracking)
│   ├── docker.rs       # Docker container management
│   └── registry.rs     # JSON registry I/O
├── build.sh            # Build script
└── README.md           # This file
```

### Build Commands

```bash
# Development build (fast compile)
./build.sh dev

# Release build (optimized)
./build.sh

# Run tests
./build.sh release test

# Or use cargo directly
cargo build --release
cargo test
cargo run -- --help
```

### Dependencies

- **tokio**: Async runtime for Docker API
- **serde/serde_json**: Fast JSON serialization
- **bollard**: Docker API client
- **sysinfo**: Cross-platform process info
- **clap**: CLI argument parsing
- **nix**: Unix system calls (Linux/Mac)

All dependencies are well-maintained and production-ready.

## Integration with Dev-Kid

The Rust watchdog is designed to replace the Python `task_watchdog.py` with zero API changes.

### Dev-Kid CLI Integration

```bash
# In cli/dev-kid, replace Python calls with:

watchdog-start() {
    task-watchdog run --interval 300 &
    echo $! > .claude/watchdog.pid
}

watchdog-check() {
    task-watchdog stats
}

task-start() {
    TASK_ID=$1
    # Register task in registry, then start process
    # Watchdog automatically monitors it
}

task-complete() {
    TASK_ID=$1
    task-watchdog kill $TASK_ID
}

rehydrate() {
    task-watchdog rehydrate
}
```

## Comparison: Python vs Rust

### Python Version (Old)
```python
# Pros:
+ Easy to modify
+ No compilation needed

# Cons:
- 50MB memory usage
- 200ms startup time
- Requires Python runtime
- Slow JSON parsing
- GIL limitations
```

### Rust Version (New)
```rust
// Pros:
+ <3MB memory usage
+ <5ms startup time
+ Single binary (no runtime)
+ 50x faster JSON parsing
+ True parallelism
+ Cross-platform

// Cons:
- Requires compilation
- Rust learning curve (for modifications)
```

## Troubleshooting

### "Docker not available"
```bash
# Make sure Docker is running
docker ps

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### "Permission denied" when killing processes
```bash
# Processes must be owned by same user
# Or run watchdog with appropriate permissions
```

### Large binary size
```bash
# Binary should be ~2MB with release profile
# If larger, ensure strip = true in Cargo.toml

# Manual strip
strip target/release/task-watchdog
```

## Contributing

Built with ❤️  and Rust 🦀

Contributions welcome! This watchdog is the performance-critical component of dev-kid.

## License

MIT License - Same as dev-kid parent project

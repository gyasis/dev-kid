# System Patterns: Task Watchdog Architecture

## Core Architecture

### Three-Layer Design

```
┌─────────────────────────────────────┐
│   CLI Layer (main.rs)               │  Command routing, argument parsing
├─────────────────────────────────────┤
│   Domain Logic (types.rs)           │  Task, Registry, ProcessInfo structs
├─────────────────────────────────────┤
│   Execution Layer                   │
│   - process.rs (native processes)   │
│   - docker.rs (containers)          │
│   - registry.rs (JSON I/O)          │
└─────────────────────────────────────┘
```

## Key Design Patterns

### 1. Process Registry Pattern

**File-Based State Management**
- JSON file at `.claude/process_registry.json` (configurable)
- Single source of truth for all task state
- Survives process restarts and context compression
- Lock-free (single-writer, multiple readers safe via atomic writes)

**Schema**:
```json
{
  "tasks": {
    "TASK-ID": {
      "mode": "native" | "docker",
      "command": "string",
      "status": "running" | "completed" | "failed",
      "started_at": "ISO8601",
      "native": { "pid", "pgid", "start_time", "env_tag" },
      "docker": { "container_id", "container_name", "resource_limits" }
    }
  }
}
```

### 2. Hybrid Execution Strategy

**Native Processes** (Trusted Code):
- Start with `setsid()` to create new process group
- Track PID + PGID for full tree control
- Store process start time for PID recycling protection
- Tag with environment variable for identification

**Docker Containers** (Untrusted Code):
- Isolated execution environment
- Resource limits (CPU, memory)
- Named containers for easy identification
- Automatic cleanup on container stop

**Decision Criteria**:
- Use native for: builds, tests, known scripts
- Use Docker for: user-provided code, risky operations, isolation needs

### 3. PID Recycling Protection

**Problem**: PIDs wrap around (~32K max), can be reused

**Solution**: Store process start time at creation
```rust
// At task start
let start_time = get_process_start_time(pid); // "Fri Jan 10 15:30:00 2026"

// At verification
if get_process_start_time(pid) != stored_start_time {
    // PID was recycled, original process is dead
    mark_task_failed();
}
```

### 4. Process Group Management

**PGID Strategy**:
- Create new process group (`setsid()`) when spawning task
- Kill entire group (`killpg(pgid, SIGTERM)`) to clean up children
- Prevents orphaned child processes

**Example**:
```
Parent Process (PID 1000, PGID 1000)
├─ Child 1 (PID 1001, PGID 1000)
│  └─ Grandchild (PID 1002, PGID 1000)
└─ Child 2 (PID 1003, PGID 1000)

killpg(1000, SIGTERM) → All 4 processes killed
```

### 5. Orphan/Zombie Detection

**Orphan**: Dead process but task marked "running"
```rust
if !is_alive(pid) && task.status == "running" {
    mark_failed(task_id);
}
```

**Zombie**: Process alive but task marked "completed"
```rust
if is_alive(pid) && task.status == "completed" {
    kill_process_group(pgid);
}
```

**Watchdog Loop**:
- Runs every 5 minutes (configurable)
- Scans all "running" tasks
- Validates process state matches task state
- Auto-corrects inconsistencies

### 6. Context Rehydration Pattern

**Problem**: AI loses context after compression

**Solution**: Rehydration command reconstructs mental model
```rust
task-watchdog rehydrate
// Output:
// - All running tasks (IDs, descriptions, status)
// - Resource usage (CPU, memory)
// - Duration running
// - What each task is doing
```

**AI Integration**:
1. Context compression occurs
2. AI runs `task-watchdog rehydrate`
3. Receives summary of all running tasks
4. Continues workflow with full context

## Data Flow

### Task Start Flow
```
User Command
  ↓
CLI (main.rs)
  ↓
Process/Docker Manager
  ↓
Spawn Process/Container
  ↓
Registry Manager (add task)
  ↓
Write JSON to disk
```

### Watchdog Check Flow
```
Timer (5 min interval)
  ↓
Load Registry
  ↓
For each "running" task:
  ├─ Check process alive (PID + start time)
  ├─ Check Docker container running
  ├─ Measure CPU/memory
  └─ Update task status
  ↓
Write updated registry
```

### Task Kill Flow
```
User Command (kill TASK-ID)
  ↓
Load Registry
  ↓
If native:
  └─ killpg(pgid, SIGTERM)
     wait 5s
     killpg(pgid, SIGKILL) if still alive
  ↓
If Docker:
  └─ docker.stop(container_id, timeout=10)
  ↓
Mark task "completed"
  ↓
Write registry
```

## Error Handling Strategy

### Graceful Degradation
- Registry load failure → Empty registry (fresh start)
- Process check failure → Mark task as "unknown" (not failed)
- Docker unavailable → Log warning, skip container tasks
- JSON parse error → Backup file, restart with empty registry

### User Feedback
- Clear error messages with actionable advice
- Exit codes: 0 (success), 1 (user error), 2 (system error)
- Verbose mode for debugging (`--verbose`)

## Performance Optimizations

### JSON Parsing
- **serde_json**: Zero-copy deserialization where possible
- Small registry files (<100KB typical) → <1ms parse time

### Process Checks
- **sysinfo crate**: Efficient /proc filesystem access
- Cached system info, refresh only when needed

### Docker API
- **bollard**: Async Docker client (tokio runtime)
- Batch operations when checking multiple containers

### Binary Size
- **Cargo profile**: `opt-level = "z"`, LTO enabled, strip symbols
- Target: ~2MB binary size

## Security Patterns

### Command Injection Prevention
**CRITICAL**: Never use shell interpolation with user input
```rust
// BAD:
let cmd = format!("bash -c '{}'", user_command);

// GOOD:
let cmd = Command::new("bash")
    .arg("-c")
    .arg(user_command)  // Properly escaped by OS
```

### Path Traversal Protection
**CRITICAL**: Validate registry path
```rust
fn validate_path(path: &str) -> Result<()> {
    let canonical = fs::canonicalize(path)?;
    if !canonical.starts_with(allowed_dir) {
        bail!("Path traversal attempt blocked");
    }
    Ok(())
}
```

### File Permissions
**CRITICAL**: Registry should be user-private
```rust
// Create file with mode 0600 (owner read/write only)
use std::fs::OpenOptions;
use std::os::unix::fs::OpenOptionsExt;

OpenOptions::new()
    .create(true)
    .write(true)
    .mode(0o600)
    .open(registry_path)?;
```

## Integration Patterns

### Dev-Kid CLI Integration
```bash
# Start watchdog daemon
task-watchdog run --interval 300 &

# Register task (CLI handles this)
# Watchdog auto-monitors via registry

# Rehydrate after context loss
task-watchdog rehydrate
```

### Multi-Tool Integration
```bash
# Tool-specific registries
task-watchdog run --registry .claude/registry.json &
task-watchdog run --registry .gemini/registry.json &

# Shared registry
task-watchdog run --registry .devtools/shared_registry.json &
```

## Testing Strategy

### Unit Tests
- Process alive/dead detection
- PID recycling validation
- Registry serialization/deserialization
- Path validation logic

### Integration Tests
- End-to-end task lifecycle (start → monitor → kill)
- Docker container management
- Registry corruption recovery
- Multi-task scenarios

### Performance Tests
- Startup time benchmark (<5ms target)
- Memory usage verification (<3MB target)
- JSON parse speed (large registries)

## Deployment Patterns

### Single Binary
```bash
# Build static binary (zero dependencies)
cargo build --release --target x86_64-unknown-linux-musl

# Deploy
sudo cp target/x86_64-unknown-linux-musl/release/task-watchdog /usr/local/bin/
```

### Systemd Service (Optional)
```ini
[Unit]
Description=Task Watchdog Daemon
After=docker.service

[Service]
Type=simple
ExecStart=/usr/local/bin/task-watchdog run --interval 300
Restart=always

[Install]
WantedBy=multi-user.target
```

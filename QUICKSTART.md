# Dev-Kid Quick Start Guide

**Get productive with dev-kid in 5 minutes**

## Prerequisites Check

Before starting, verify you have:

```bash
# Required
bash --version        # Bash 4.0+
git --version         # Git 2.0+
python3 --version     # Python 3.7+
jq --version          # jq 1.5+

# Optional (for Rust watchdog)
cargo --version       # Rust 1.70+ (for building watchdog)
```

If anything is missing, see [DEPENDENCIES.md](docs/development/DEPENDENCIES.md) for installation instructions.

## Installation (2 minutes)

### Step 1: Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/dev-kid.git
cd dev-kid

# Run the installer (no .sh extension needed!)
./install

# Verify installation
dev-kid --version
# Output: dev-kid v2.0.0
```

**What gets installed:**
- ✅ CLI tools → \`~/.dev-kid/\`
- ✅ Symlink → \`/usr/local/bin/dev-kid\`
- ✅ Skills → \`~/.claude/skills/planning-enhanced/\`
- ✅ Commands → \`~/.claude/commands/\`
- ✅ Templates → \`~/.dev-kid/templates/\`

### Step 2: Build Rust Watchdog (Optional but Recommended)

```bash
cd rust-watchdog
cargo build --release
cd ..

# Verify the binary works
./rust-watchdog/target/release/task-watchdog --version
# Output: task-watchdog 2.0.0
```

**Performance**: <3MB memory, <5ms startup, 17x faster than Python

**Skip if**: You don't need background task monitoring (core features work without it)

## Your First Workflow (3 minutes)

### Option A: With Speckit (Recommended)

Complete workflow from planning to execution:

```bash
# 1. Initialize in your project
cd /path/to/your-project
dev-kid init

# 2. Create project constitution (one-time setup)
# In Claude Code, run:
/speckit.constitution

# 3. Specify a feature
/speckit.specify "Add user authentication with OAuth2"

# 4. Generate tasks
/speckit.tasks

# 5. View the execution plan
dev-kid orchestrate "Phase 1"
dev-kid waves

# 6. Execute the waves
dev-kid execute

# 7. Check status
dev-kid status
```

### Option B: Standalone (No Speckit)

Basic workflow without speckit integration - see full document for complete example.

## Essential Commands Reference

### Core Commands
```bash
dev-kid init              # Initialize in project
dev-kid orchestrate       # Convert tasks.md to waves
dev-kid execute           # Execute waves
dev-kid status            # Show system health
```

### Watchdog Commands
```bash
dev-kid watchdog-start    # Start Rust daemon
dev-kid watchdog-check    # Check running tasks
dev-kid watchdog-report   # Show resource usage
dev-kid watchdog-stop     # Stop daemon
```

### Memory & Checkpoints
```bash
dev-kid sync-memory       # Update Memory Bank
dev-kid checkpoint "msg"  # Create git checkpoint
dev-kid finalize          # Snapshot session
dev-kid recall            # Resume from snapshot
```

## Next Steps

1. **Read the docs**:
   - [README.md](README.md) - Full feature documentation
   - [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md) - Architecture deep dive

2. **Explore advanced features**:
   - Constitution enforcement
   - GitHub issue sync
   - Custom wave strategies

---

**Quick Start Guide v1.0** | Dev-Kid v2.0 | Get Productive in 5 Minutes

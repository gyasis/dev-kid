# Dev-Kid Claude Code Commands

Slash commands for manual triggering of dev-kid workflow steps.

## Available Commands

| Command | Description | When to Use |
|---------|-------------|-------------|
| `/devkid.orchestrate` | Convert tasks.md into parallelized waves | After /speckit.tasks |
| `/devkid.execute` | Execute waves with monitoring & checkpoints | After orchestration |
| `/devkid.checkpoint` | Validate wave & create git commit | Between waves or manual |
| `/devkid.sync-memory` | Update memory-bank with current state | After checkpoint |
| `/devkid.workflow` | Display complete workflow guide | Anytime for reference |

## Installation

These commands are automatically installed to `~/.claude/commands/` when you run:

```bash
./scripts/install.sh
```

Or manually copy to Claude Code commands directory:

```bash
mkdir -p ~/.claude/commands
cp commands/devkid.*.md ~/.claude/commands/
```

## Usage

In Claude Code, type `/devkid.` and autocomplete will show available commands:

```
/devkid.orchestrate
/devkid.execute
/devkid.checkpoint
/devkid.sync-memory
/devkid.workflow
```

## Workflow Integration

These commands work seamlessly with speckit:

```
1. /speckit.constitution      # Create project rules
2. /speckit.specify "..."     # Create feature spec
3. /speckit.tasks             # Generate linear tasks
4. /devkid.orchestrate        # Parallelize into waves
5. /devkid.execute            # Execute with monitoring
6. /devkid.checkpoint         # Validate & commit
7. /devkid.sync-memory        # Update knowledge base
```

## Auto-Trigger Skills

The `skills/` directory contains auto-triggering versions that activate based on file state and user messages. Commands are for manual, explicit triggering.

## Documentation

- `devkid.workflow.md` - Complete workflow guide
- `../skills/speckit-workflow.md` - Detailed integration documentation
- `../DEV_KID.md` - Full system reference

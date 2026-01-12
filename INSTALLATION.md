# Dev-Kid Installation Guide

Complete installation guide for dev-kid with Claude Code integration.

## Quick Install

```bash
cd /home/gyasis/Documents/code/dev-kid
./scripts/install.sh
```

## What Gets Installed

### System Installation (`~/.dev-kid/`)

```
~/.dev-kid/
├── cli/                      # Core Python modules & CLI
│   ├── dev-kid              # Main Bash CLI entry point
│   ├── orchestrator.py      # Task → waves converter
│   ├── wave_executor.py     # Wave execution engine
│   └── task_watchdog.py     # Background task monitor
├── skills/                   # Workflow automation (both .md and .sh)
├── commands/                 # Slash commands (.md)
├── scripts/                  # Installation & init scripts
├── templates/                # Memory Bank & context templates
└── DEV_KID.md               # Documentation
```

### Claude Code Integration

#### Skills (`~/.claude/skills/`)

Auto-triggering workflows that activate based on file state and user messages:

```
~/.claude/skills/
├── orchestrate-tasks.md      # Auto-orchestrates when tasks.md exists
├── execute-waves.md          # Auto-executes when execution_plan.json exists
├── checkpoint-wave.md        # Auto-validates wave completion
├── sync-memory.md            # Auto-updates memory bank after checkpoints
├── speckit-workflow.md       # Complete workflow guide
└── init-planning-system.md   # Planning system initialization
```

#### Commands (`~/.claude/commands/`)

Manual slash commands for explicit control:

```
~/.claude/commands/
├── devkid.orchestrate.md     # /devkid.orchestrate
├── devkid.execute.md         # /devkid.execute
├── devkid.checkpoint.md      # /devkid.checkpoint
├── devkid.sync-memory.md     # /devkid.sync-memory
└── devkid.workflow.md        # /devkid.workflow
```

#### Legacy Skills (`~/.claude/skills/planning-enhanced/`)

Backward-compatible bash scripts:

```
~/.claude/skills/planning-enhanced/
├── checkpoint.sh
├── sync_memory.sh
├── verify_existence.sh
├── maintain_integrity.sh
├── finalize_session.sh
├── recall.sh
└── task_watchdog.py
```

### System PATH (`/usr/local/bin/`)

```
/usr/local/bin/dev-kid → ~/.dev-kid/cli/dev-kid
```

## Verification

After installation, verify everything is in sync:

```bash
# Check CLI installation
which dev-kid
dev-kid --version

# Check skills installation
ls -la ~/.claude/skills/*.md

# Check commands installation
ls -la ~/.claude/commands/devkid.*.md

# Count installed files
echo "Skills: $(ls -1 ~/.claude/skills/*.md 2>/dev/null | wc -l)"
echo "Commands: $(ls -1 ~/.claude/commands/devkid.*.md 2>/dev/null | wc -l)"
```

Expected output:
```
Skills: 6
Commands: 5
```

## Testing Installation

Initialize in a test project:

```bash
mkdir /tmp/test-dev-kid
cd /tmp/test-dev-kid
git init
dev-kid init

# Verify files created
ls -la .claude/
ls -la memory-bank/
ls -la .git/hooks/
```

## Usage After Installation

### With Speckit (Recommended)

```bash
# 1. Create project constitution
/speckit.constitution

# 2. Create feature spec
/speckit.specify "Add user authentication"

# 3. Generate tasks
/speckit.tasks

# 4. Orchestrate into waves (auto-triggers or manual)
/devkid.orchestrate

# 5. Execute waves (auto-triggers or manual)
/devkid.execute

# 6. Checkpoint waves (auto-triggers or manual)
/devkid.checkpoint

# 7. Sync memory (auto-triggers or manual)
/devkid.sync-memory
```

### Standalone Dev-Kid

```bash
# Create tasks.md manually
cat > tasks.md << 'EOF'
- [ ] T001: Create User model in models/user.py
- [ ] T002: Create UserService in services/user_service.py
- [ ] T003: Add tests for User model
EOF

# Orchestrate
dev-kid orchestrate "Feature Implementation"

# Execute
dev-kid execute

# Or use slash commands
/devkid.orchestrate
/devkid.execute
```

## Troubleshooting

### Skills Not Auto-Triggering

**Issue**: Skills don't activate automatically

**Solution**: Check Claude Code settings:
1. Settings → Skills → Progressive Disclosure → Enabled
2. Restart Claude Code after installation
3. Verify skill files exist: `ls ~/.claude/skills/*.md`

### Commands Not Showing in Autocomplete

**Issue**: `/devkid.` doesn't show in autocomplete

**Solution**:
1. Verify commands installed: `ls ~/.claude/commands/devkid.*.md`
2. Restart Claude Code
3. Try typing `/devkid.` and wait for autocomplete

### Permission Denied on /usr/local/bin

**Issue**: Cannot create symlink

**Solution**:
```bash
# Add to PATH instead
echo 'export PATH="$HOME/.dev-kid/cli:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Skills Conflicting with Each Other

**Issue**: Multiple skills triggering simultaneously

**Solution**: Skills have built-in activation conditions to prevent conflicts:
- `orchestrate-tasks.md` - Only triggers when tasks.md exists + no execution_plan.json
- `execute-waves.md` - Only triggers when execution_plan.json exists
- Checkpoints happen at wave boundaries

## Uninstallation

```bash
# Remove symlink
sudo rm /usr/local/bin/dev-kid

# Remove installation directory
rm -rf ~/.dev-kid

# Remove Claude Code integration
rm -rf ~/.claude/skills/*.md
rm -rf ~/.claude/commands/devkid.*.md
rm -rf ~/.claude/skills/planning-enhanced
```

## Updating

To update to latest version:

```bash
cd /home/gyasis/Documents/code/dev-kid
git pull
./scripts/install.sh
```

Skills and commands will be automatically updated in `~/.claude/`.

## Integration Status

✅ **Skills**: Auto-trigger based on file state
✅ **Commands**: Manual slash command invocation
✅ **Git Hooks**: Auto-symlink tasks.md on branch switch
✅ **Memory Bank**: Persistent knowledge across sessions
✅ **Task Watchdog**: Background process monitoring
✅ **Constitution**: Enforcement at checkpoints
✅ **Speckit Integration**: Complete workflow from planning to execution

All components are synchronized and ready for use.

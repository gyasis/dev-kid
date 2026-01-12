# Dev-Kid Quickstart Guide

Get up and running with dev-kid in 5 minutes.

## Installation (2 minutes)

```bash
# Clone and install
git clone https://github.com/yourusername/dev-kid.git
cd dev-kid
./scripts/install.sh

# Verify installation
./scripts/verify-install.sh
```

Expected output:
```
✅ Installation verified successfully!
   Skills: 6 auto-triggering workflows
   Commands: 5 slash commands
```

## Initialize Your Project (1 minute)

```bash
cd your-project
dev-kid init

# Creates:
# ✓ memory-bank/     - Persistent knowledge
# ✓ .claude/         - Context protection
# ✓ Git hooks        - Auto-symlink tasks.md
```

## Choose Your Workflow

### Option A: With Speckit (Recommended) ⭐

Complete planning-to-implementation workflow:

**Step 1: Create Constitution (once per project)**
```bash
/speckit.constitution
```

Creates project coding standards in:
- `.specify/memory/constitution.md`
- `memory-bank/shared/.constitution.md`

**Step 2: Specify Feature**
```bash
/speckit.specify "Add user authentication with OAuth2"
```

Creates:
- Feature branch: `001-user-auth`
- Spec: `.specify/specs/001-user-auth/spec.md`

**Step 3: Generate Tasks**
```bash
/speckit.tasks
```

Creates:
- Tasks: `.specify/specs/001-user-auth/tasks.md`
- Symlink: `tasks.md` → spec folder

**Step 4-7: Execute (Auto or Manual)**

Execute waves automatically or use commands:
```bash
/devkid.orchestrate     # Parallelize tasks
/devkid.execute         # Execute waves
/devkid.checkpoint      # Validate & commit
/devkid.sync-memory     # Update knowledge
```

**Skills auto-trigger** when files are ready, or use slash commands for manual control.

**Switch branches - progress preserved:**
```bash
git checkout 002-payment-flow
# tasks.md auto-relinks → .specify/specs/002-payment-flow/tasks.md
```

---

### Option B: Standalone Dev-Kid

Without speckit - direct task management:

**Step 1: Create tasks.md**
```markdown
# Feature: User Authentication

## Wave 1 - Models
- [ ] T001: Create User model in `models/user.py`
- [ ] T002: Create UserService in `services/user_service.py`

## Wave 2 - API
- [ ] T003: Add /auth/login endpoint
- [ ] T004: Add /auth/register endpoint

## Wave 3 - Tests
- [ ] T005: Test authentication flow
```

**Step 2: Orchestrate**
```bash
dev-kid orchestrate "User Authentication"
```

Creates `execution_plan.json` with parallelized waves.

**Step 3: Execute**
```bash
dev-kid watchdog-start   # Start monitoring
dev-kid execute          # Execute waves
```

Or use slash command:
```bash
/devkid.execute
```

**Step 4: Monitor Progress**
```bash
dev-kid watchdog-report  # View task timing
dev-kid status           # Check overall status
```

---

## Quick Command Reference

### CLI Commands

```bash
dev-kid init                  # Initialize in project
dev-kid orchestrate "Phase"   # Create execution plan
dev-kid execute               # Execute waves
dev-kid checkpoint "Message"  # Create checkpoint
dev-kid sync-memory           # Update memory bank
dev-kid watchdog-start        # Start task monitor
dev-kid status                # Check system status
```

### Slash Commands (Claude Code)

```bash
/devkid.orchestrate      # Parallelize tasks
/devkid.execute          # Execute waves
/devkid.checkpoint       # Validate & commit
/devkid.sync-memory      # Update knowledge
/devkid.workflow         # Show workflow guide
```

### Speckit Commands

```bash
/speckit.constitution    # Create project rules
/speckit.specify "..."   # Create feature spec
/speckit.tasks           # Generate tasks
```

---

## Complete Example Session

Here's a real workflow from start to finish:

```bash
# 1. Install dev-kid (one time)
cd ~/dev-kid && ./scripts/install.sh

# 2. Initialize your project
cd ~/my-project
dev-kid init

# 3. Create constitution (once per project)
# In Claude Code:
/speckit.constitution

# 4. Start new feature
/speckit.specify "Add OAuth2 authentication with Google login"

# Review spec.md, approve

# 5. Generate tasks
/speckit.tasks

# 6. Orchestrate (auto-triggers or manual)
/devkid.orchestrate

# Output:
# 🌊 Wave 1 (PARALLEL_SWARM): 4 tasks
# 🌊 Wave 2 (SEQUENTIAL_MERGE): 3 tasks
# 🌊 Wave 3 (PARALLEL_SWARM): 5 tasks

# 7. Execute (auto-triggers or manual)
/devkid.execute

# Output:
# 🚀 Starting wave-based execution...
# 🐕 Watchdog started
# 🌊 Wave 1 (4 tasks)...
# ✅ T001 complete
# ✅ T002 complete
# ✅ T003 complete
# ✅ T004 complete
# 🔍 Checkpoint Wave 1...
# ✅ Constitution compliant
# 📝 Git commit created
# 🌊 Wave 2 (3 tasks)...

# 8. Work on another feature
git checkout -b 002-payment-flow
/speckit.specify "Add Stripe payment integration"
# Continue workflow...

# 9. Switch back - progress preserved
git checkout 001-user-auth
# tasks.md auto-relinks to 001-user-auth/tasks.md
# Continue where you left off
```

---

## Troubleshooting

### Skills Not Auto-Triggering?

1. Check Claude Code settings:
   - Settings → Skills → Progressive Disclosure → Enabled
2. Restart Claude Code
3. Verify: `ls ~/.claude/skills/*.md`

### Commands Not Showing?

1. Verify: `ls ~/.claude/commands/devkid.*.md`
2. Type `/devkid.` and wait for autocomplete
3. Restart Claude Code if needed

### Git Hook Not Working?

```bash
# Check hook exists and is executable
ls -la .git/hooks/post-checkout
chmod +x .git/hooks/post-checkout

# Test manually
.git/hooks/post-checkout
```

### Tasks Not Marked Complete?

Remember to update tasks.md:
```markdown
- [x] T001: Create User model  # Change [ ] to [x]
```

---

## What's Next?

### Learn More

- **Complete workflow**: `/devkid.workflow`
- **Full documentation**: `cat DEV_KID.md`
- **Architecture**: `docs/architecture/ARCHITECTURE.md`
- **API reference**: `docs/reference/API.md`

### Customize

Edit memory bank files:
- `memory-bank/shared/projectbrief.md` - Project vision
- `memory-bank/shared/.constitution.md` - Coding standards
- `memory-bank/private/{user}/activeContext.md` - Current focus

### Get Help

```bash
dev-kid status           # Check system status
dev-kid watchdog-report  # View task timing
/devkid.workflow         # Show workflow guide
```

---

## Time Savings

Typical dev workflow:

| Without Dev-Kid | With Dev-Kid | Savings |
|----------------|--------------|---------|
| Manual task tracking | Auto-tracked | 15 min/day |
| Sequential execution | Parallelized waves | 30-50% faster |
| Manual checkpoints | Auto-validation | 10 min/wave |
| Context reconstruction | Memory bank | 20 min/session |
| Constitution enforcement | Automatic | 15 min/review |

**Estimated time savings: 2-4 hours per feature**

---

## You're Ready! 🚀

Start with:
1. `/speckit.constitution` - Define your rules
2. `/speckit.specify "Your feature"` - Plan it
3. `/speckit.tasks` - Break it down
4. Let dev-kid orchestrate and execute

The system handles parallelization, validation, checkpointing, and knowledge preservation automatically.

Happy coding!

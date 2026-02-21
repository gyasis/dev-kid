# Quickstart: Integration Sentinel
**Phase 1 Output** | Branch: `001-integration-sentinel` | Date: 2026-02-20

This guide helps a developer get sentinel running end-to-end in a test environment.

---

## Prerequisites

- dev-kid installed (`dev-kid --version`)
- micro-agent installed (`micro-agent --version` or `npx micro-agent --version`)
- Ollama running at `192.168.0.159:11434` with `qwen3-coder:30b` available
- Python 3.11+, git initialized in project

---

## Step 1: Configure Sentinel in dev-kid.yml

Add the sentinel block to your project's `dev-kid.yml`:

```yaml
sentinel:
  enabled: true
  mode: auto   # use "human-gated" to pause on cascade events
  tier1:
    model: qwen3-coder:30b
    ollama_url: http://192.168.0.159:11434
    max_iterations: 5
  tier2:
    model: claude-sonnet-4-20250514
    max_iterations: 10
    max_budget_usd: 2.0
  change_radius:
    max_files: 3
    max_lines: 150
    allow_interface_changes: false
  placeholder:
    fail_on_detect: true
```

To disable sentinel entirely (zero overhead):
```yaml
sentinel:
  enabled: false
```

---

## Step 2: Create tasks.md and Orchestrate

```bash
# Example tasks.md
cat > tasks.md << 'EOF'
- [ ] Implement login endpoint in `src/auth.py`
- [ ] Add JWT validation to `src/middleware.py`
- [ ] Write integration tests in `tests/test_auth.py`
EOF

# Orchestrate → generates execution_plan.json + injects SENTINEL-* tasks
dev-kid orchestrate "Auth Feature"
```

After orchestration, `execution_plan.json` will contain both developer tasks and their sentinel counterparts:
```json
{
  "execution_plan": {
    "waves": [{
      "tasks": [
        {"task_id": "T001", "agent_role": "Developer", ...},
        {"task_id": "SENTINEL-T001", "agent_role": "Sentinel", "dependencies": ["T001"], ...},
        ...
      ]
    }]
  }
}
```

`tasks.md` will have sentinel entries appended:
```markdown
- [ ] SENTINEL-T001: Sentinel validation for T001
- [ ] SENTINEL-T002: Sentinel validation for T002
```

---

## Step 3: Execute Waves

```bash
dev-kid execute "Auth Feature"
```

During execution, when a task is marked `[x]`, the sentinel for that task runs automatically:

```
Wave 1 executing...
  [Developer - T001] Implement login endpoint...
  → T001 marked [x] by agent
  [Sentinel - SENTINEL-T001] Running sentinel pipeline...
    ✓ Placeholder scan: clean
    ✓ Test framework detected: pytest
    → Tier 1: micro-agent (qwen3-coder:30b, 3 iterations)
    ✓ Tests passing
    → Writing manifest: .claude/sentinel/SENTINEL-T001/
  → SENTINEL-T001 marked [x]
  [Developer - T002] Add JWT validation...
  ...
Wave 1 checkpoint: ✅ All tasks complete → git commit
```

---

## Step 4: View Sentinel Output

```bash
# Check manifest for a specific task
cat .claude/sentinel/SENTINEL-T001/manifest.json | python3 -m json.tool

# View the changes sentinel made
cat .claude/sentinel/SENTINEL-T001/diff.patch

# Read the human summary
cat .claude/sentinel/SENTINEL-T001/summary.md
```

---

## Step 5: Check Sentinel Status Dashboard

```bash
dev-kid sentinel-status
```

Output:
```
Sentinel Run History (current session)
────────────────────────────────────────────────────────────────
Task         Tier  Iterations  Files  Lines  Result  Duration
SENTINEL-T001   1       3        1     15    PASS      45s
SENTINEL-T002   1       1        0      0    PASS       8s
SENTINEL-T003   2       8        2     89    PASS     210s
────────────────────────────────────────────────────────────────
Total: 3 runs | 2 Tier 1 only | 1 Tier 2 escalation | 0 failures
```

---

## Common Scenarios

### Sentinel Catches a Placeholder
```
[Sentinel - SENTINEL-T001] Placeholder scan...
  ❌ VIOLATION: src/auth.py:42: matched "TODO" — "# TODO: implement token refresh"
  → Checkpoint BLOCKED. Fix the placeholder and re-run.
```
Fix the code, mark T001 `[ ]` again (uncomplete), then re-run.

### Sentinel Cascades to Pending Tasks
```
[Sentinel - SENTINEL-T002] Radius check...
  ⚠ Budget exceeded: 4 files changed (budget: 3)
  → Cascade analysis: T003 references src/auth.py
  → Annotating T003 with compatibility warning
  [auto mode] Proceeding...
```
Task T003 will now have a `[SENTINEL CASCADE WARNING]` note in tasks.md.

### Ollama Unavailable (Tier 1 Skipped)
```
[Sentinel - SENTINEL-T001] Checking Ollama @ 192.168.0.159:11434... unreachable
  ⚠ Tier 1 skipped (Ollama unreachable) — escalating to Tier 2
  → Tier 2: micro-agent (claude-sonnet-4-20250514)
```

---

## Key File Locations

| File | Purpose |
|------|---------|
| `dev-kid.yml` | Sentinel configuration |
| `execution_plan.json` | Generated plan with SENTINEL-* tasks |
| `tasks.md` | Tasks including SENTINEL-* entries |
| `.claude/sentinel/<ID>/manifest.json` | Structured run result |
| `.claude/sentinel/<ID>/diff.patch` | Exact code changes |
| `.claude/sentinel/<ID>/summary.md` | Context injection text |
| `cli/sentinel/` | Sentinel Python subpackage |

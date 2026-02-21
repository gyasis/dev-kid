# PRD: Integration Sentinel
**Feature**: Per-Task Micro-Agent Test Loop with Cascading Impact Analysis
**Project**: Dev-Kid v2.0
**Status**: Draft
**Date**: 2026-02-20
**Author**: Gyasis + Claude

---

## 1. Executive Summary

Dev-Kid's wave executor currently orchestrates tasks in parallel waves and verifies completion via `[x]` markers in `tasks.md`. However, "completion" today means only that an agent marked its task done — not that the code actually works, integrates correctly, or is free of placeholder implementations.

**Integration Sentinel** closes this gap by injecting sentinel tasks directly into the execution plan at orchestration time. Each sentinel task runs as a fully isolated micro-agent subprocess — no shared context with the main dev-kid session. It uses a local Ollama model (fast, cheap) as the first line of defense, escalates to cloud models only when needed, and enforces a change radius budget to prevent architectural drift.

Critically: **sentinel always emits a Change Manifest** — pass or fail. Because sentinel may modify code across up to 12 iterations before completing, subsequent task agents must know the true state of the codebase, not the state the plan was written against. The manifest records exactly what changed, why, which tests were fixed, and what interfaces shifted. This manifest is injected into every subsequent agent's context before it begins work.

The result: by the time a wave checkpoint is created, every task's output is verified to actually work, the codebase state is documented, and downstream agents are aware of any drift from the original plan.

---

## 2. Problem Statement

### Problem 1: Tasks pass in isolation, nothing integrates

Each task agent writes code scoped to its own assignment. It may pass local unit tests. But it doesn't verify that:
- Its outputs connect correctly to the inputs of downstream tasks
- Its interfaces match what other tasks expect
- Its implementation actually does what the plan intended end-to-end

By the final wave, the system "passes tests" per-task but is functionally broken at the seams.

### Problem 2: Orphan placeholders accumulate silently

Agents frequently emit placeholder implementations as scaffolding and mark the task complete without replacing them:

```python
def process_payment(amount):
    # TODO: implement Stripe integration
    return {"status": "mock_success"}
```

```typescript
export function validateUser(token: string): User {
    return MOCK_USER; // placeholder
}
```

These pass unit tests (because the tests are also mocked). They survive wave checkpoints. They get committed. By the end of execution the delivered output looks complete but is non-functional in production.

### Problem 3: Micro-agent fixes can silently break the plan

Naively plugging in a test-fixing loop creates a new risk: the fixer rewrites a core interface to make one test pass, which silently invalidates the assumptions of 5 pending tasks designed around the original interface. The fix propagates an architectural change with no awareness of the broader plan.

---

## 3. Goals

- **G1**: Automatically run tests after every task completion, before the wave checkpoint
- **G2**: Use a tiered model approach — cheap/local first, cloud escalation only when needed
- **G3**: Detect and block orphan mocks/placeholders from reaching checkpoints
- **G4**: Enforce a change radius budget — minor fixes proceed automatically, architectural changes trigger analysis
- **G5**: When an architectural change is unavoidable, cascade updates to all affected pending tasks and the execution plan
- **G6**: Be configurable — auto mode by default, human-gated mode available
- **G7**: Be transparent — every sentinel action is logged and traceable

## 4. Non-Goals

- **NG1**: Not a replacement for human code review
- **NG2**: Not responsible for writing the original tests — that's the task agent's job
- **NG3**: Not a full CI/CD pipeline — scoped to local test suites only
- **NG4**: Will not rewrite task descriptions beyond what's needed to reflect a cascaded change
- **NG5**: Will not attempt to fix type errors or linting issues unrelated to test failures

---

## 5. Solution Architecture

### 5.1 Core Principle: Plan Injection, Not Runtime Hooks

Sentinel is **not** a hook inside `wave_executor.py`. It is a first-class citizen of the execution plan. The orchestrator injects sentinel tasks directly into `execution_plan.json` at planning time. Wave executor runs them like any other task — it has no special knowledge of sentinel.

Micro-agent runs as a **fully isolated subprocess** with its own context. Zero token bleed into the dev-kid session. Zero coupling to the main execution context.

```
┌─────────────────────────────────────────────────────┐
│  ORCHESTRATION TIME  (orchestrator.py)              │
│                                                     │
│  tasks.md  ──►  dependency analysis                 │
│                        │                            │
│                         ▼                           │
│             sentinel.enabled: true?                 │
│                   │          │                      │
│                  YES         NO                     │
│                   │          │                      │
│                   ▼          ▼                      │
│         inject SENTINEL   normal plan               │
│         tasks after each                            │
│         task in each wave                           │
│                   │                                 │
│                   ▼                                 │
│          execution_plan.json                        │
│          ┌────────────────────────────┐             │
│          │ Wave 1:                    │             │
│          │  TASK-001: Implement auth  │             │
│          │  SENTINEL-001: Verify T001 │ ← injected  │
│          │  TASK-002: User model      │             │
│          │  SENTINEL-002: Verify T002 │ ← injected  │
│          │  checkpoint_after: {}      │             │
│          │ Wave 2:                    │             │
│          │  TASK-003: ...             │             │
│          │  SENTINEL-003: ...         │ ← injected  │
│          └────────────────────────────┘             │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  EXECUTION TIME  (wave_executor.py — UNCHANGED)     │
│                                                     │
│  Runs TASK-001 normally                             │
│  Runs SENTINEL-001 ──► spawns micro-agent subprocess│
│                              │ isolated context     │
│                              ├── Phase 1: Placeholder scan
│                              ├── Phase 2: Tier 1 loop (Ollama)
│                              ├── Phase 2b: Tier 2 escalation
│                              ├── Phase 3: Change radius check
│                              └── Phase 3b: Cascade if needed
│                                                     │
│  Runs TASK-002 normally                             │
│  Runs SENTINEL-002 ──► spawns micro-agent subprocess│
│  ...                                                │
│  Wave Checkpoint (existing, unchanged)              │
└─────────────────────────────────────────────────────┘
```

### 5.2 Sentinel Task Structure in execution_plan.json

```json
{
  "task_id": "SENTINEL-001",
  "type": "sentinel",
  "parent_task": "TASK-001",
  "description": "Integration Sentinel: verify TASK-001 output",
  "strategy": "SEQUENTIAL_MERGE",
  "command": "dev-kid sentinel-run TASK-001",
  "depends_on": ["TASK-001"],
  "sentinel_config": {
    "working_dir": "src/auth/",
    "test_command": null,
    "tier1_model": "qwen3-coder:30b",
    "tier2_model": "claude-sonnet-4-20250514"
  }
}
```

### 5.3 Sentinel Task Execution Flow (Subprocess)

When wave_executor runs a `SENTINEL-*` task, it calls `dev-kid sentinel-run <TASK-ID>`, which:

```
dev-kid sentinel-run TASK-001
            │
            ▼
┌─────────────────────────────┐
│   PHASE 1: Placeholder Scan │  ← scans files modified by TASK-001
└─────────────────────────────┘
            │ clean
            ▼
┌─────────────────────────────┐
│   PHASE 2: Tier 1 Test Loop │  ← qwen3-coder:30b @ Ollama
│   micro-agent subprocess    │    192.168.0.159:11434
│   max 5 iterations          │    isolated context
└─────────────────────────────┘
            │ still failing
            ▼
┌─────────────────────────────┐
│   PHASE 2b: Tier 2 Escalate │  ← claude-sonnet-4-20250514
│   micro-agent subprocess    │    new subprocess, own context
│   max 10 iterations         │
└─────────────────────────────┘
            │ pass
            ▼
┌─────────────────────────────┐
│   PHASE 3: Change Radius    │  ← measure git diff footprint
└─────────────────────────────┘
            │ within budget → done
            ▼
┌─────────────────────────────┐
│   PHASE 3b: Cascade Impact  │  ← only if budget exceeded
│   patches pending tasks     │
└─────────────────────────────┘
```

---

## 6. Component Specifications

### 6.1 Placeholder Scanner (`cli/placeholder_scanner.py`)

Runs before any test loop. Scans files modified by the task agent.

**Detection patterns**:

| Category | Patterns |
|----------|----------|
| Comment markers | `TODO`, `FIXME`, `PLACEHOLDER`, `HACK`, `XXX`, `STUB` |
| Mock function names | `mock_*`, `stub_*`, `fake_*`, `dummy_*` |
| Dead implementations | `pass` (Python), `return None` (where non-None expected), `raise NotImplementedError` |
| Hardcoded test data | Strings matching `test_`, `sample_`, `example_` in production code paths |
| Incomplete returns | Functions returning empty dict `{}`, empty list `[]`, `0`, `""` as sole statement |
| Mock imports | `from unittest.mock import`, `import mock`, `jest.mock(`, `vi.mock(` in non-test files |

**Output**: `PlaceholderReport` with list of violations, file paths, line numbers.

**Behavior**:
- `fail_on_detect: true` (default) → blocks progression, logs violations, requires human resolution
- `fail_on_detect: false` → logs warnings only, proceeds

**Scope**: Only scans files modified by the current task (via `git diff --name-only HEAD`).

---

### 6.2 Integration Sentinel (`cli/integration_sentinel.py`)

Core orchestrator. Invoked by `wave_executor.py` after each task `[x]` marker is confirmed.

**Responsibilities**:
1. Detect test framework (delegates to micro-agent's framework detector)
2. Invoke Tier 1 loop (Ollama)
3. If Tier 1 exhausted → invoke Tier 2 loop (cloud)
4. If both exhausted → halt with `SENTINEL_FAILURE` and report
5. On success → pass results to Change Radius Analyzer

**Micro-agent invocation** (subprocess):

```python
# Tier 1
subprocess.run([
    "npx", "@builder.io/micro-agent", "run",
    "--provider", "ollama",
    "--model", config.tier1.model,
    "--ollama-host", config.tier1.host,
    "--max-iterations", str(config.tier1.max_iterations),
    "--working-dir", task_working_dir,
    "--test-command", detected_test_command,
    "--no-adversarial",          # skip adversarial in Tier 1 (speed)
    "--change-budget", str(config.change_radius.max_lines),
])

# Tier 2 (escalation)
subprocess.run([
    "npx", "@builder.io/micro-agent", "run",
    "--provider", "anthropic",
    "--model", config.tier2.model,
    "--max-iterations", str(config.tier2.max_iterations),
    "--working-dir", task_working_dir,
    "--test-command", detected_test_command,
    "--with-adversarial",        # enable in Tier 2
])
```

**Exit codes**:
- `0` → tests passing, within change radius
- `1` → tests still failing after all tiers
- `2` → tests passing but change radius exceeded (triggers cascade)
- `3` → placeholder violations detected

---

### 6.3 Change Radius Analyzer (`cli/cascade_analyzer.py`)

Runs after a successful test loop. Measures the footprint of changes made.

**Three-axis budget** (combo as agreed):

| Axis | Default Threshold | Definition |
|------|-----------------|------------|
| File radius | ≤ 3 files | Number of files modified beyond the task's primary file |
| Line budget | ≤ 150 lines | Total lines added + removed across all changed files |
| Interface stability | 0 violations | Public function/class signatures must not change |
| Cross-wave boundary | 0 violations | Modified files must not belong to other waves' task scope |

**Interface stability check**:
- Python: AST-diff public function signatures (`def` at module level, class methods)
- TypeScript: Parse exported function/class signatures via regex diff
- Rust: Check `pub fn` / `pub struct` signature changes

**Cross-wave boundary check**:
- Load `execution_plan.json`
- Extract file assignments per task per wave
- Any modified file owned by a task in a *different* wave → boundary violation

**Output**:
```json
{
  "within_budget": false,
  "files_changed": 5,
  "lines_changed": 312,
  "interface_violations": ["src/auth.py::validate_token signature changed"],
  "cross_wave_violations": ["src/db/models.py owned by WAVE-2/TASK-004"],
  "recommendation": "CASCADE_REQUIRED"
}
```

---

### 6.4 Sentinel Change Manifest (`cli/integration_sentinel.py`)

**This is mandatory output on every sentinel run — pass or fail, no exceptions.**

After every sentinel execution (regardless of result), the sentinel emits a structured Change Manifest. This is the primary handoff artifact between a sentinel run and the rest of the wave. It is what allows subsequent task agents to know the true current state of the code — not the state the plan was written against.

**Why mandatory even on fail?**
Because even a *failed* sentinel may have changed code across 12 iterations before giving up. The codebase after failure is not the same as before sentinel ran. Subsequent tasks must know this.

**Manifest written to**: `.claude/sentinel/<TASK-ID>/manifest.json`
**Diff written to**: `.claude/sentinel/<TASK-ID>/diff.patch`
**Summary written to**: `.claude/sentinel/<TASK-ID>/summary.md`

**Manifest schema**:
```json
{
  "task_id": "TASK-001",
  "timestamp": "2026-02-20T14:32:11Z",
  "result": "PASS",
  "tier_used": 2,
  "iterations": {
    "tier1": 5,
    "tier2": 2
  },
  "files_changed": [
    { "file": "src/auth.py", "additions": 34, "deletions": 12 },
    { "file": "src/utils/token.py", "additions": 8, "deletions": 0 }
  ],
  "total_lines_changed": 54,
  "interface_changes": [
    {
      "file": "src/auth.py",
      "symbol": "validate_token",
      "before": "validate_token(token: str) -> bool",
      "after": "validate_token(token: str, strict: bool = False) -> bool"
    }
  ],
  "tests_fixed": [
    "test_auth_invalid_token",
    "test_auth_expiry"
  ],
  "tests_still_failing": [],
  "fix_reason": "Token expiry logic was incomplete — added grace period handling in strict mode",
  "scope_verdict": "MINOR",
  "cascade_required": false,
  "plan_update_required": false
}
```

**Summary (`.claude/sentinel/<TASK-ID>/summary.md`)** — injected into subsequent task context:
```markdown
## SENTINEL NOTE: TASK-001 [PASS — Tier 2, 7 iterations]

**Code was modified during sentinel.** Before writing any code that depends on
TASK-001's output, be aware of the following changes:

### Files Changed
- `src/auth.py` (+34 / -12)
- `src/utils/token.py` (+8 / -0)

### Interface Changes
- `validate_token()` now accepts optional `strict: bool = False` parameter
  - Before: `validate_token(token: str) -> bool`
  - After:  `validate_token(token: str, strict: bool = False) -> bool`

### Why It Changed
Token expiry logic was incomplete. Sentinel added grace period handling.

### Tests Fixed
- `test_auth_invalid_token`
- `test_auth_expiry`

### Action Required
If your task calls `validate_token`, verify you are passing the correct arguments.
```

**Context injection mechanism**:

The `UserPromptSubmit` hook (already in dev-kid) is extended to prepend all sentinel summaries for completed tasks in the current wave into the agent's context before it begins work:

```bash
# .claude/hooks/user-prompt-submit.sh (extended)
# Inject sentinel summaries for this wave's completed tasks
for manifest in .claude/sentinel/*/manifest.json; do
    task_id=$(jq -r '.task_id' "$manifest")
    summary_file=".claude/sentinel/${task_id}/summary.md"
    if [[ -f "$summary_file" ]]; then
        echo "---"
        cat "$summary_file"
    fi
done
```

**On FAIL**: The summary still reports what changed across all iterations, which tests are still failing and why, and what was attempted. This gives the human (or cascade analyzer) full context to understand the failure.

---

### 6.5 Cascade Impact Processor (`cli/cascade_analyzer.py`)

Activated only when `Change Radius Analyzer` returns `CASCADE_REQUIRED`.

**Auto mode** (default):
1. Identify all pending tasks in `tasks.md` that reference affected files or interfaces
2. Append impact note to each affected task description:
   ```
   ⚠️ SENTINEL CASCADE [2026-02-20]: Interface `validate_token` in `src/auth.py`
   was modified during TASK-003 sentinel fix. Signature changed from
   `(token: str) -> bool` to `(token: str, strict: bool = False) -> bool`.
   Verify your implementation is compatible.
   ```
3. Re-run orchestrator to regenerate wave assignments if file ownership changed
4. Log full cascade report to `.claude/sentinel_log.json`
5. Proceed to checkpoint

**Human-gated mode**:
1. Perform same analysis
2. Print full cascade report to stdout
3. **Pause execution** and prompt:
   ```
   ⚠️  SENTINEL: Cascade required for TASK-003 fix.
   Affected tasks: TASK-007, TASK-012, TASK-015

   Options:
     [a] Auto-apply cascade and continue
     [r] Review changes manually before continuing
     [h] Halt execution — I'll fix this myself
   ```
4. Wait for user input

---

## 7. Configuration Schema

Added to `dev-kid.yml` (project-level config):

```yaml
sentinel:
  enabled: true                          # Master switch
  mode: auto                             # "auto" | "human-gated"

  # When to invoke sentinel
  trigger: per_task                      # "per_task" | "per_wave" | "finalization"

  # Tier 1 — Local Ollama (fast, cheap)
  tier1:
    provider: ollama
    model: qwen3-coder:30b
    host: http://192.168.0.159:11434
    max_iterations: 5
    timeout_seconds: 120
    adversarial: false                   # Skip adversarial testing in Tier 1

  # Tier 2 — Cloud escalation (capable, expensive)
  tier2:
    provider: anthropic
    model: claude-sonnet-4-20250514
    max_iterations: 10
    timeout_seconds: 300
    adversarial: true                    # Enable in Tier 2

  # Change radius budget (combo)
  change_radius:
    max_files: 3                         # Files beyond primary task file
    max_lines: 150                       # Total lines added + removed
    block_interface_changes: true        # Public signature changes = cascade
    block_cross_wave_changes: true       # Cross-wave file changes = cascade

  # Placeholder detection
  placeholders:
    enabled: true
    fail_on_detect: true                 # Block checkpoint on violations
    patterns:                            # Additional custom patterns
      - "YOUR_IMPLEMENTATION_HERE"
      - "raise NotImplementedError"
    exclude_paths:                       # Never scan these
      - "tests/"
      - "**/__mocks__/"
      - "**/*.test.*"
      - "**/*.spec.*"

  # Cascade behavior
  cascade:
    auto_update_tasks: true              # Patch task descriptions
    re_orchestrate: true                 # Regenerate wave plan if needed
    log_file: ".claude/sentinel_log.json"
```

---

## 8. Integration Points with Dev-Kid

### 8.1 `wave_executor.py` — Hook point

After detecting `[x]` completion in `tasks.md`, before calling `_git_checkpoint()`:

```python
# Existing flow
if self.verify_wave_completion(wave):
    # NEW: Run sentinel
    sentinel_result = self.run_sentinel(task, wave)
    if sentinel_result.exit_code == 1:
        self._halt(f"Sentinel failed for {task.id}: tests still failing")
    elif sentinel_result.exit_code == 3:
        self._halt(f"Placeholder violations in {task.id}: {sentinel_result.violations}")
    # Existing flow continues
    self._update_progress(wave)
    self._git_checkpoint(wave)
```

### 8.2 New CLI Command: `dev-kid sentinel-status`

Shows current sentinel log:
```
$ dev-kid sentinel-status

INTEGRATION SENTINEL LOG
─────────────────────────────────────────
TASK-001  ✅ Tier 1 passed (3 iterations)  0 placeholders  Δ2 files / Δ47 lines
TASK-002  ✅ Tier 1 passed (1 iteration)   0 placeholders  Δ1 file  / Δ12 lines
TASK-003  ⚠️  Tier 2 required (Tier 1 ×5)  0 placeholders  CASCADE → TASK-007, TASK-012
TASK-004  🔄 In progress...
```

### 8.3 New Skill: `skills/sentinel.sh`

Manual trigger outside wave execution:
```bash
dev-kid sentinel TASK-003          # Run sentinel for specific task
dev-kid sentinel --wave 2          # Run sentinel across all wave 2 tasks
dev-kid sentinel --scan-only       # Placeholder scan only, no test loop
```

### 8.4 Constitution Enhancement

Add rule to `Constitution.md` template:

```markdown
## Output Integrity
- No placeholder implementations in production code paths
- All task outputs must pass integration sentinel before checkpoint
- Mocks permitted only in test files (tests/, __mocks__, *.test.*, *.spec.*)
```

---

## 9. Data Flows

### Sentinel Artifact Directory Structure

```
.claude/
└── sentinel/
    ├── TASK-001/
    │   ├── manifest.json    ← structured machine-readable result
    │   ├── diff.patch       ← exact git diff of all code changes made
    │   └── summary.md       ← human-readable, injected into next task context
    ├── TASK-002/
    │   ├── manifest.json
    │   ├── diff.patch
    │   └── summary.md
    └── TASK-003/
        ├── manifest.json    ← result: FAIL — still contains all attempted changes
        ├── diff.patch       ← diff of what was tried before giving up
        └── summary.md       ← explains what failed and why, for human review
```

**Key rule**: Manifest is written **before** cascade analysis and **before** checkpoint. It is written even if sentinel failed. It is the source of truth for what the codebase looks like after sentinel ran.

### Sentinel Log Schema (`.claude/sentinel_log.json`)

```json
{
  "session_id": "2026-02-20-abc123",
  "entries": [
    {
      "task_id": "TASK-003",
      "timestamp": "2026-02-20T14:32:11Z",
      "placeholder_scan": {
        "violations": 0,
        "files_scanned": 4
      },
      "tier1": {
        "iterations": 5,
        "result": "EXHAUSTED",
        "model": "qwen3-coder:30b",
        "duration_seconds": 87
      },
      "tier2": {
        "iterations": 3,
        "result": "PASSED",
        "model": "claude-sonnet-4-20250514",
        "duration_seconds": 142
      },
      "change_radius": {
        "files_changed": 5,
        "lines_changed": 312,
        "within_budget": false,
        "interface_violations": ["src/auth.py::validate_token"],
        "cross_wave_violations": []
      },
      "cascade": {
        "triggered": true,
        "affected_tasks": ["TASK-007", "TASK-012"],
        "re_orchestrated": false,
        "mode": "auto"
      },
      "final_result": "PASSED_WITH_CASCADE"
    }
  ]
}
```

---

## 10. Acceptance Criteria

### Core Loop
- [ ] Sentinel runs automatically after every `[x]` task completion in `tasks.md`
- [ ] Tier 1 (Ollama/qwen3-coder:30b) always runs before Tier 2
- [ ] Tier 2 only activates after Tier 1 exhausts all iterations
- [ ] Wave executor halts with clear error if both tiers fail
- [ ] `sentinel.enabled: false` in config fully disables the feature

### Placeholder Detection
- [ ] Scanner detects all patterns defined in config
- [ ] Scanner only inspects files modified by the current task
- [ ] Scanner never flags files in `tests/`, `__mocks__`, `*.test.*`, `*.spec.*`
- [ ] Checkpoint is blocked when violations found and `fail_on_detect: true`
- [ ] Violation report includes file path, line number, matched pattern

### Sentinel Change Manifest
- [ ] Manifest written to `.claude/sentinel/<TASK-ID>/manifest.json` on every run (pass OR fail)
- [ ] `diff.patch` captures exact git diff of all changes made during sentinel iterations
- [ ] `summary.md` is human-readable and action-oriented for downstream agents
- [ ] Manifest includes `result`, `tier_used`, `iterations`, `files_changed`, `interface_changes`, `tests_fixed`, `tests_still_failing`, `fix_reason`
- [ ] On FAIL: manifest still records all changes attempted across all iterations
- [ ] Sentinel summaries injected into subsequent task agent context via `UserPromptSubmit` hook
- [ ] `dev-kid sentinel-status` reads manifests, not just the log file

### Change Radius
- [ ] File count tracked correctly across all changed files
- [ ] Line count is additive (insertions + deletions)
- [ ] Interface change detection works for Python, TypeScript, and Rust
- [ ] Cross-wave file ownership check uses `execution_plan.json` as source of truth
- [ ] Changes within budget proceed without cascade

### Cascade
- [ ] Auto mode patches task descriptions and continues without prompting
- [ ] Human-gated mode pauses and presents options before proceeding
- [ ] Cascade log written to `.claude/sentinel_log.json` after every run
- [ ] `dev-kid sentinel-status` displays log in readable format

### Configuration
- [ ] All sentinel settings configurable via `dev-kid.yml`
- [ ] `mode: human-gated` can be set without code changes
- [ ] Custom placeholder patterns addable via config
- [ ] Paths can be excluded from placeholder scanning via config

---

## 11. Implementation Task Breakdown

### Wave 1 — Foundation
- [ ] **T001**: Create `cli/placeholder_scanner.py` — pattern detection scoped to task-modified files only
- [ ] **T002**: Create `cli/integration_sentinel.py` — Tier 1/2 orchestration + micro-agent subprocess invocation
- [ ] **T003**: Inject sentinel tasks into `cli/orchestrator.py` at plan generation time (not wave_executor hook)
- [ ] **T004**: Add sentinel config block to `dev-kid.yml` schema and `cli/config_manager.py`

### Wave 2 — Change Manifest
- [ ] **T005**: Implement Sentinel Change Manifest writer in `cli/integration_sentinel.py`
  - `manifest.json`: structured result schema (pass/fail/iterations/files/interfaces/tests)
  - `diff.patch`: git diff capture of all changes made during sentinel run
  - `summary.md`: human-readable action-oriented note for downstream agents
  - Write manifest on **every** run regardless of pass/fail result
- [ ] **T006**: Extend `UserPromptSubmit` hook to inject sentinel summaries into next task's context
- [ ] **T007**: Implement manifest reader in `dev-kid sentinel-status` command

### Wave 3 — Change Radius & Cascade
- [ ] **T008**: Create `cli/cascade_analyzer.py` — change radius measurement (files, lines, interfaces)
- [ ] **T009**: Implement interface stability diff for Python (AST), TypeScript (regex), Rust (pub fn)
- [ ] **T010**: Implement cross-wave boundary check using `execution_plan.json`
- [ ] **T011**: Implement cascade auto-mode (task description patching + optional re-orchestration)
- [ ] **T012**: Implement cascade human-gated mode (prompt + wait)

### Wave 4 — UX & Observability
- [ ] **T013**: Create `skills/sentinel.sh` manual trigger skill
- [ ] **T014**: Add sentinel rules to `Constitution.md` template
- [ ] **T015**: Write integration tests for sentinel loop (mock micro-agent responses)
- [ ] **T016**: Write integration tests for cascade analyzer (fixture execution plans)
- [ ] **T017**: Write integration tests for manifest writer (verify on pass, fail, and partial runs)

---

## 12. Open Questions

| # | Question | Status |
|---|----------|--------|
| Q1 | Should Tier 1 adversarial testing be enabled for high-risk tasks (e.g., auth, payments)? | Open |
| Q2 | Should sentinel run on wave-level integration tests in addition to per-task tests? | Open — deferred to v2 |
| Q3 | What's the right retry strategy when the Ollama server is unreachable? (skip sentinel vs halt) | Decided: skip with warning, log to sentinel log |
| Q4 | Should cascade patches be presented as a git commit diff for human review? | Open — nice to have |
| Q5 | Should `qwen3-coder-next` (50.2GB) be configurable as an intermediate Tier 1.5? | Open — post-testing |

---

## 13. Future Work (v2)

- **Shared memory vault**: Sentinel learns from successful fixes across projects via ChromaDB
- **Wave-level integration tests**: Run a broader integration test suite after every full wave (not just per task)
- **Sentinel dashboard**: Web UI showing sentinel pass rates, tier escalation frequency, cascade history
- **Pre-task sentinel**: Scan for placeholder risks in task description *before* execution begins
- **Tier 0**: Ultra-fast `qwen2.5-coder:14b` (9GB) pre-flight pass for trivially-fixable failures

---

*Dev-Kid Integration Sentinel PRD v1.0 | 2026-02-20*

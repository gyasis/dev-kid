# Feature Specification: Integration Sentinel

**Feature Branch**: `001-integration-sentinel`
**Created**: 2026-02-20
**Status**: Draft
**Input**: Per-task micro-agent test loop with tiered model escalation, change manifest output, placeholder detection, change radius enforcement, and cascading plan updates for dev-kid wave execution

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tasks Produce Verified, Working Output (Priority: P1)

A developer runs dev-kid wave execution on a feature. Instead of receiving code that "passed" per-task tests but is full of mocks and disconnected seams, every task's output is automatically verified to actually work before the wave checkpoint is committed. The developer gets a git history where each checkpoint represents genuinely functional, integrated code.

**Why this priority**: This is the core value proposition. Without it, the whole sentinel system has no purpose. It eliminates the most painful outcome of autonomous task execution — a "complete" codebase that doesn't actually work.

**Independent Test**: Can be fully tested by running a wave execution with a task that has a known test gap and confirming sentinel catches and fixes it before the checkpoint commit is created.

**Acceptance Scenarios**:

1. **Given** a task is marked `[x]` in tasks.md, **When** the sentinel runs and all tests pass, **Then** the wave checkpoint proceeds normally and a Change Manifest is written to `.claude/sentinel/<TASK-ID>/`
2. **Given** a task is marked `[x]` but its tests fail, **When** the sentinel's Tier 1 loop runs up to 5 iterations, **Then** if tests pass the checkpoint proceeds; if still failing, Tier 2 escalates
3. **Given** both tiers are exhausted and tests still fail, **When** the sentinel completes, **Then** wave execution halts with a clear error, the Change Manifest records all attempted changes, and no checkpoint is created

---

### User Story 2 - Orphan Placeholders Are Caught Before Commit (Priority: P1)

A developer's task agent emits a `# TODO: implement this` or `return MOCK_USER` in production code and marks the task complete. Instead of this silently surviving into the git checkpoint, the placeholder scanner catches it, blocks the checkpoint, and reports exactly where the violation is.

**Why this priority**: Tied for highest priority with Story 1. Placeholder accumulation is the specific failure mode that makes autonomous task execution produce non-functional output at finalization.

**Independent Test**: Can be tested by introducing a known placeholder pattern into task output and confirming checkpoint is blocked with a specific violation report (file, line, pattern).

**Acceptance Scenarios**:

1. **Given** task output contains `# TODO: implement Stripe`, **When** the placeholder scanner runs, **Then** checkpoint is blocked and a report identifies the file, line number, and matched pattern
2. **Given** task output contains mocks only in `tests/` directory, **When** the scanner runs, **Then** no violation is reported and execution proceeds
3. **Given** `fail_on_detect: false` is set in config, **When** a placeholder is found, **Then** a warning is logged but execution continues

---

### User Story 3 - Downstream Task Agents Know What Sentinel Changed (Priority: P2)

After sentinel fixes a task's code across multiple iterations, subsequent task agents in the same wave receive an automatic briefing of what changed — which files were modified, which interfaces shifted, and why. Agents don't write code against a stale understanding of the codebase.

**Why this priority**: Without this, sentinel creates a new problem: it silently changes the code contract that subsequent agents depend on. The Change Manifest injection prevents this and makes the system self-correcting.

**Independent Test**: Can be tested by verifying that a task agent running after a sentinel fix receives the sentinel summary in its context and references the changed interface correctly.

**Acceptance Scenarios**:

1. **Given** sentinel modifies a function signature during fixing, **When** the next task agent begins, **Then** its context includes a sentinel summary noting the signature change and recommending verification
2. **Given** sentinel ran and changed nothing (tests already passed in 1 iteration), **When** the next task agent begins, **Then** a brief "no changes" manifest entry is still written but context injection is minimal
3. **Given** sentinel failed (all tiers exhausted), **When** a human reviews the failure, **Then** the manifest records all code changes attempted across all iterations so the human understands the current code state

---

### User Story 4 - Architectural Changes Cascade to the Plan (Priority: P2)

Sentinel fixes a test by modifying a function signature that other pending tasks depend on. Instead of silently invalidating those tasks, the cascade analyzer detects the impact and automatically appends a compatibility note to each affected task description. In human-gated mode, the developer is shown the impact and asked to approve before proceeding.

**Why this priority**: Prevents sentinel from solving one problem (test failures) by creating another (silent plan invalidation). Keeps the execution plan consistent with the actual code.

**Independent Test**: Can be tested with a fixture execution plan where a known interface change affects two pending tasks, confirming both task descriptions receive cascade notes.

**Acceptance Scenarios**:

1. **Given** sentinel changes a public interface and the change exceeds the radius budget, **When** cascade analysis runs, **Then** all pending tasks referencing that interface receive an appended compatibility warning
2. **Given** `mode: human-gated` in config, **When** a cascade is required, **Then** execution pauses and presents affected tasks with options: auto-apply, review, or halt
3. **Given** sentinel changes stay within the radius budget (≤3 files, ≤150 lines, no interface changes), **When** radius check runs, **Then** no cascade is triggered and execution proceeds directly to checkpoint

---

### User Story 5 - Sentinel Is Configured and Monitored (Priority: P3)

A developer can enable/disable sentinel, switch between auto and human-gated modes, configure model tiers, adjust change radius thresholds, and add custom placeholder patterns — all via `dev-kid.yml` without code changes. They can also run `dev-kid sentinel-status` to see a dashboard of every sentinel run in the current session.

**Why this priority**: Operational control. Without this, the system is a black box. Teams with different risk tolerances need different configurations.

**Independent Test**: Can be tested by toggling `sentinel.enabled: false` and confirming no sentinel tasks appear in the generated execution plan.

**Acceptance Scenarios**:

1. **Given** `sentinel.enabled: false` in config, **When** orchestrator generates a plan, **Then** no `SENTINEL-*` tasks appear in `execution_plan.json`
2. **Given** a completed wave execution, **When** the developer runs `dev-kid sentinel-status`, **Then** a table shows each task, tier used, iterations, files changed, and pass/fail result
3. **Given** a custom placeholder pattern added to config, **When** scanner runs on code containing that pattern, **Then** it is caught as a violation

---

### Edge Cases

- What happens when the Ollama server at `192.168.0.159` is unreachable? → Tier 1 is skipped with a warning logged to the manifest; Tier 2 runs immediately
- What happens if no test framework is detected in the task's working directory? → Sentinel logs a warning, skips the test loop, runs placeholder scan only, and proceeds
- What happens if sentinel itself crashes mid-iteration? → The partial diff is captured to `diff.patch`, the manifest is written with `result: ERROR`, and wave execution halts with the crash log
- What happens if `execution_plan.json` is missing when cascade analysis runs? → Cross-wave boundary check is skipped; file and line radius checks still run
- What happens if a task has no files modified (purely documentation task)? → Placeholder scan scopes to zero files, test loop detects no relevant tests, manifest written with `files_changed: []`, proceeds immediately

---

## Requirements *(mandatory)*

### Functional Requirements

**Sentinel Plan Injection**
- **FR-001**: The orchestrator MUST inject a `SENTINEL-*` task after every task in the execution plan when `sentinel.enabled: true`
- **FR-002**: Sentinel tasks MUST be typed as `"type": "sentinel"` in `execution_plan.json` and run as isolated subprocesses
- **FR-003**: Disabling sentinel (`sentinel.enabled: false`) MUST result in zero `SENTINEL-*` tasks in the generated plan with no other changes to execution behavior

**Placeholder Detection**
- **FR-004**: The placeholder scanner MUST detect violations matching configured patterns in all files modified by the parent task
- **FR-005**: The scanner MUST never flag files in test directories (`tests/`, `__mocks__/`, `*.test.*`, `*.spec.*`)
- **FR-006**: When `fail_on_detect: true`, any placeholder violation MUST block the checkpoint and halt execution with a violation report showing file, line number, and matched pattern

**Tiered Test Loop**
- **FR-007**: Tier 1 (local Ollama model) MUST always run before Tier 2 (cloud model)
- **FR-008**: Tier 2 MUST only activate after Tier 1 exhausts its maximum iteration count
- **FR-009**: Each tier MUST run as a fully isolated subprocess with no shared context from the dev-kid session
- **FR-010**: The test framework MUST be auto-detected from the task's working directory (supporting Python/pytest, TypeScript/Jest/Vitest, Rust/cargo)

**Change Manifest**
- **FR-011**: A Change Manifest MUST be written after every sentinel run regardless of pass or fail result
- **FR-012**: The manifest MUST include: `result`, `tier_used`, `iterations` per tier, `files_changed` with line counts, `interface_changes`, `tests_fixed`, `tests_still_failing`, and `fix_reason`
- **FR-013**: An exact `diff.patch` of all code changes made during sentinel MUST be captured and stored alongside the manifest
- **FR-014**: A human-readable `summary.md` MUST be written and injected into subsequent task agents' context via the `UserPromptSubmit` hook

**Change Radius & Cascade**
- **FR-015**: The change radius analyzer MUST enforce a three-axis budget: file count, total line count, and interface stability
- **FR-016**: Any modification to a public interface (function signature, exported class) MUST be detected and classified as a potential cascade trigger
- **FR-017**: Any modification to a file owned by a task in a different wave (per `execution_plan.json`) MUST be classified as a cross-wave violation
- **FR-018**: In auto cascade mode, affected pending task descriptions MUST be automatically annotated with a compatibility warning
- **FR-019**: In human-gated mode, execution MUST pause and present the affected tasks before proceeding

**Configuration**
- **FR-020**: All sentinel behavior MUST be configurable via `dev-kid.yml` without code changes
- **FR-021**: Custom placeholder patterns MUST be addable via config
- **FR-022**: Paths MUST be excludable from placeholder scanning via config

### Key Entities

- **Sentinel Task**: A plan-injected task of type `sentinel` that runs after a parent task and executes the full sentinel pipeline as an isolated subprocess
- **Change Manifest**: The structured output artifact of every sentinel run; contains result, code changes, interface changes, and test outcomes; always written regardless of pass/fail
- **Placeholder Violation**: A detected occurrence of a forbidden pattern in production code (not test files); blocks checkpoint when `fail_on_detect: true`
- **Change Radius**: The three-axis budget (files, lines, interfaces) that determines whether sentinel's fixes are minor (proceed) or architectural (trigger cascade)
- **Cascade**: The process of annotating pending task descriptions with compatibility warnings when sentinel's fixes exceed the change radius budget

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero placeholder violations (`TODO`, `mock_*`, `NotImplementedError`, etc.) survive to the git checkpoint in any wave execution with sentinel enabled
- **SC-002**: At least 80% of test failures in Tier 1 (local model) are resolved without escalating to Tier 2 (cloud model) for typical minor gaps
- **SC-003**: A Change Manifest is present in `.claude/sentinel/<TASK-ID>/` for 100% of completed sentinel runs (pass and fail)
- **SC-004**: Subsequent task agents demonstrably reference sentinel-reported interface changes in their generated code, reducing integration failures at wave boundaries
- **SC-005**: Sentinel overhead (Tier 1 only, tests already near-passing) adds no more than 3 minutes per task to wave execution time
- **SC-006**: Cascade mode correctly identifies and annotates 100% of pending tasks that reference a changed interface, with zero false negatives in tested scenarios
- **SC-007**: Toggling `sentinel.enabled: false` produces an identical execution plan to a pre-sentinel baseline (no residual sentinel tasks or config bleed)

---

## Assumptions

- Micro-agent (`@builder.io/micro-agent`) is already installed and accessible via `npx` in the project environment
- The Ollama server at `192.168.0.159:11434` with `qwen3-coder:30b` is available and reachable from the machine running dev-kid; if unreachable, Tier 2 activates immediately
- Test frameworks are detectable from standard manifest files (`package.json`, `Cargo.toml`, `pyproject.toml`, etc.) in the task's working directory
- Tasks in `execution_plan.json` have a `files` or `affects` field that maps tasks to their primary files; if absent, cross-wave boundary check is skipped gracefully
- The `UserPromptSubmit` hook mechanism already in dev-kid can be extended to inject per-task sentinel summaries without architectural changes to the hook system
- Sentinel is scoped to fixing minor test gaps only; it is not expected to implement missing features or resolve fundamental architectural mismatches

---

## Dependencies

- `@builder.io/micro-agent` — test loop engine (already in use in micro-agent project)
- `qwen3-coder:30b` on Ollama @ `192.168.0.159:11434` — Tier 1 model (confirmed available)
- `claude-sonnet-4-20250514` via Anthropic API — Tier 2 model
- dev-kid's existing `orchestrator.py`, `wave_executor.py`, `config_manager.py`, and `UserPromptSubmit` hook

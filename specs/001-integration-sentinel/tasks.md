# Tasks: Integration Sentinel

**Input**: Design documents from `/specs/001-integration-sentinel/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story label (US1–US5, maps to spec.md priorities)
- All paths relative to repo root (`/home/gyasis/Documents/code/dev-kid/`)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `cli/sentinel/` subpackage skeleton and test directory structure that all subsequent phases depend on.

- [x] T001 Create `cli/sentinel/` directory and empty `cli/sentinel/__init__.py`
- [x] T002 [P] Create test directories `tests/unit/sentinel/`, `tests/integration/sentinel/fixtures/`, `tests/contract/sentinel/` with `__init__.py` files
- [x] T003 [P] Create integration test fixtures: `tests/integration/sentinel/fixtures/execution_plan_simple.json` (3-task plan), `tests/integration/sentinel/fixtures/tasks_with_placeholder.py` (file with TODO), `tests/integration/sentinel/fixtures/tasks_clean.py` (clean production file)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented. Includes config extension, shared dataclasses, and the two existing-file modifications (orchestrator + wave executor) that wire sentinel into dev-kid's execution pipeline.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T004 Extend `cli/config_manager.py` with full sentinel config block: add 17 new fields to `ConfigSchema` dataclass (sentinel_enabled, sentinel_mode, tier1/tier2 settings, radius budget, placeholder config) plus update `to_dict()`, `from_dict()`, and `validate()` methods per `contracts/config-schema.md`
- [x] T005 [P] Add sentinel config section to `dev-kid.yml` with production defaults (`enabled: true`, `mode: auto`, `tier1.model: qwen3-coder:30b`, `tier1.ollama_url: http://192.168.0.159:11434`, `tier1.max_iterations: 5`, `tier2.model: claude-sonnet-4-20250514`, radius budget 3 files/150 lines, `fail_on_detect: true`)
- [x] T006 Populate `cli/sentinel/__init__.py` with all shared dataclasses: `SentinelResult`, `TierResult`, `ManifestData`, `PlaceholderViolation`, `InterfaceChangeReport`, `ChangeRadiusReport`, `CascadeAnnotation` — matching field definitions in `data-model.md` and all contracts
- [x] T007 [P] Implement `detect_test_command(working_dir: Path) -> Optional[str]` in `cli/sentinel/runner.py`: check for `pyproject.toml`/`setup.py` → `python -m pytest`; `package.json` with vitest/jest → `npx vitest run`/`npm test`; `Cargo.toml` → `cargo test`; return `None` if no framework found
- [x] T008 Modify `cli/orchestrator.py` to inject sentinel tasks post-wave-assignment: after `_assign_waves()`, when `config.sentinel_enabled`, insert `SENTINEL-<task_id>` task (agent_role="Sentinel", dependencies=[task_id], inherits file_locks) after each regular task in each wave; atomically append matching `- [ ] SENTINEL-<task_id>: Sentinel validation for <task_id>` lines to `tasks.md`; when `sentinel.enabled: false` produce identical plan with zero SENTINEL tasks (satisfies FR-001, FR-002, FR-003)
- [x] T009 Modify `cli/wave_executor.py` to route sentinel tasks: in `execute_task()`, check `task.get("agent_role") == "Sentinel"` → call `SentinelRunner(config, project_root).run(task)` → if `result.should_halt_wave` raise `WaveHaltError(result.error_message)` → otherwise mark SENTINEL task `[x]` in tasks.md; import `SentinelRunner` from `cli/sentinel/runner.py`

**Checkpoint**: Foundation ready — all user story phases can now proceed.

---

## Phase 3: User Story 1 — Tasks Produce Verified, Working Output (Priority: P1) 🎯 MVP

**Goal**: Every completed task's output is automatically verified via micro-agent test loop (Tier 1 Ollama → Tier 2 cloud) before the wave checkpoint is committed. Wave halts on exhaustion.

**Independent Test**: Run a wave execution with a task that has a known test gap (fixture in `tests/integration/sentinel/fixtures/`). Confirm sentinel catches the failure and either fixes it (manifest=PASS) or halts wave (manifest=FAIL) without creating a checkpoint commit.

### Implementation for User Story 1

- [x] T010 [US1] Implement Ollama connectivity check in `cli/sentinel/tier_runner.py`: `check_ollama_available(base_url: str) -> bool` using `subprocess.run(['curl', '-sf', f'{base_url}/api/tags'], timeout=5)` — returns False on any exception or non-zero exit
- [x] T011 [US1] Implement `TierRunner.run_tier1(objective, test_cmd, config) -> TierResult` in `cli/sentinel/tier_runner.py`: invoke micro-agent subprocess with `['micro-agent', '--objective', ..., '--test', ..., '--max-iterations', '5', '--simple', '5', '--no-escalate', '--artisan', 'ollama:qwen3-coder:30b']`; set `env={'OLLAMA_BASE_URL': config.sentinel_tier1_ollama_url}`; `timeout=300`; `capture_output=True, text=True, check=False`; if Ollama unavailable skip with warning (return `TierResult(attempted=True, skipped=True)`)
- [x] T012 [P] [US1] Implement `TierRunner.run_tier2(objective, test_cmd, config) -> TierResult` in `cli/sentinel/tier_runner.py`: invoke micro-agent subprocess with `['micro-agent', '--objective', ..., '--test', ..., '--max-iterations', '10', '--artisan', 'claude-sonnet-4-20250514', '--max-budget', '2.0', '--max-duration', '10']`; requires `ANTHROPIC_API_KEY` in env; `timeout=600`
- [ ] T013 [P] [US1] Implement `_parse_micro_agent_output(stdout: str) -> dict` in `cli/sentinel/tier_runner.py`: regex-extract `iterations`, `cost_usd`, `duration_sec` from micro-agent stdout summary block (`Iterations: X total`, `Cost: $X.XXX total`, `Duration: X.Xs`); return zero-values if no match
- [x] T014 [US1] Implement `SentinelRunner.run(task: dict) -> SentinelResult` core pipeline in `cli/sentinel/runner.py`: resolve working dir from task file_locks; call `detect_test_command()`; if no framework log warning and skip test loop; call `TierRunner.run_tier1()` → if FAIL call `TierRunner.run_tier2()` → if still FAIL set `result=FAIL, should_halt_wave=True`; set `result=PASS` on first tier success; return `SentinelResult` (stub out placeholder/manifest/cascade integration points as no-ops for now)
- [x] T015 [P] [US1] Write unit tests for `TierRunner` in `tests/unit/sentinel/test_tier_runner.py`: mock subprocess calls to test Tier 1 success, Tier 1 failure → Tier 2 escalation, Ollama unreachable → skip to Tier 2, Tier 2 success, both tiers exhausted; test output parser with sample stdout
- [x] T016 [US1] Write integration test for US1 acceptance scenarios in `tests/integration/sentinel/test_sentinel_runner.py`: using fixture execution plan, verify (1) PASS path produces result=PASS, (2) FAIL path halts wave and sets should_halt_wave=True, (3) Ollama unreachable triggers Tier 2

**Checkpoint**: US1 complete — tiered test loop works end-to-end. Validate by running a sentinel on a fixture task with intentional test failure.

---

## Phase 4: User Story 2 — Orphan Placeholders Are Caught Before Commit (Priority: P1)

**Goal**: Placeholder scanner detects forbidden patterns (TODO, mock_*, etc.) in production code; blocks checkpoint with file/line/pattern report when `fail_on_detect: true`; skips test directories.

**Independent Test**: Inject `tasks_with_placeholder.py` fixture (contains `# TODO: implement this`) as modified file in a sentinel run. Confirm checkpoint is blocked with a violation report showing file, line, and matched pattern. Confirm `tasks_clean.py` produces zero violations.

### Implementation for User Story 2

- [x] T017 [US2] Implement `PlaceholderScanner` class in `cli/sentinel/placeholder_scanner.py`: `__init__(patterns, exclude_paths)`; `scan(files: list[Path]) -> list[PlaceholderViolation]`; compile patterns as regex; for each non-excluded file read line-by-line and collect violations with 1-based line numbers and ±2 lines context; `is_excluded(file_path)` using glob matching against `ALWAYS_EXCLUDE` union user config; `from_config(config) -> PlaceholderScanner` factory per `contracts/placeholder-scanner.md`
- [ ] T018 [P] [US2] Integrate `PlaceholderScanner` into `SentinelRunner.run()` in `cli/sentinel/runner.py`: call scanner before test loop on files derived from task file_locks; if violations found and `fail_on_detect: true` set `result=FAIL, should_halt_wave=True` immediately (skip test loop); store violations in result for manifest
- [x] T019 [P] [US2] Write unit tests for `PlaceholderScanner` in `tests/unit/sentinel/test_placeholder_scanner.py`: test each built-in pattern matches; test excluded paths (tests/, __mocks__/, *.test.py, *.spec.ts) are never flagged; test `fail_on_detect: false` returns violations but does not halt; test clean file returns empty list

**Checkpoint**: US2 complete — placeholder detection works with independent test using fixtures.

---

## Phase 5: User Story 3 — Downstream Task Agents Know What Sentinel Changed (Priority: P2)

**Goal**: A Change Manifest (manifest.json + diff.patch + summary.md) is always written to `.claude/sentinel/<TASK-ID>/` after every sentinel run (pass AND fail). The summary.md is injected into the next task agent's context via the UserPromptSubmit hook.

**Independent Test**: Run a sentinel that passes after 1 iteration. Verify all three manifest files exist in `.claude/sentinel/SENTINEL-T001/`. Run a sentinel that fails. Verify manifest exists with `result: FAIL`. Verify the next task invocation has sentinel summary in its context (check hook output).

### Implementation for User Story 3

- [x] T022 [US3] Implement `ManifestWriter` class in `cli/sentinel/manifest_writer.py`: `__init__(output_dir: Path)`; `write(data: ManifestData) -> ManifestPaths`; writes `manifest.json` (validated JSON), `diff.patch` (from `git diff HEAD -- <files>`, empty file if no changes), `summary.md` (PASS and FAIL templates from `contracts/change-manifest.md`); creates output dir if not exists; never raises on FAIL result
- [ ] T023 [US3] Integrate `ManifestWriter` into `SentinelRunner.run()` in `cli/sentinel/runner.py`: call after test loop and placeholder scan complete (win or lose); assemble full `ManifestData` from tier results, placeholder violations, files changed (from git diff stats), interface changes, cascade info; write to `.claude/sentinel/<sentinel_id>/`; ensure manifest write happens even in ERROR result path (use try/finally)
- [x] T024 [US3] Extend UserPromptSubmit hook in `.claude/hooks/user-prompt-submit.sh`: after existing git branch/constitution injection, check for latest sentinel `summary.md` in `.claude/sentinel/` for current task context; if found, inject contents into hook output JSON `additionalContext` field; only inject most recent summary (not all)
- [x] T025 [P] [US3] Write unit tests for `ManifestWriter` in `tests/unit/sentinel/test_manifest_writer.py`: test manifest.json written with correct schema; test diff.patch written (empty when no changes); test summary.md written for PASS and FAIL cases; test no exception raised on FAIL result
- [ ] T026 [P] [US3] Write contract test for manifest.json schema in `tests/contract/sentinel/test_manifest_schema.py`: validate all required fields present (result, timestamp, tier_used, tiers, files_changed, interface_changes, tests_fixed, tests_still_failing, radius); validate result is one of PASS/FAIL/ERROR

**Checkpoint**: US3 complete — manifest always written, summary injected into next task context.

---

## Phase 6: User Story 4 — Architectural Changes Cascade to the Plan (Priority: P2)

**Goal**: When sentinel's fixes exceed the change radius budget (>3 files, >150 lines, or interface changes), cascade analysis auto-annotates pending tasks with compatibility warnings. In human-gated mode, execution pauses for approval.

**Independent Test**: Use a fixture execution plan where T002 depends on an interface that T001's sentinel modifies. Confirm T002's description in tasks.md receives a `[SENTINEL CASCADE WARNING]` annotation. Confirm human-gated mode pauses and presents options.

### Implementation for User Story 4

- [x] T027 [US4] Implement `InterfaceDiff.compare(file_path, pre_content, post_content) -> InterfaceChangeReport` in `cli/sentinel/interface_diff.py`: auto-detect language from file extension; Python: use `ast.parse()` + `ast.walk()` to extract public functions/classes, compare pre vs post symbols, classify removed/added/signature-changed; `get_pre_content(file_path, git_ref="HEAD") -> str` via `git show HEAD:{file}` subprocess; return `InterfaceChangeReport` per `contracts/interface-diff.md`
- [x] T028 [P] [US4] Add TypeScript/JavaScript regex detection to `cli/sentinel/interface_diff.py`: compile patterns for `export (async )?function \w+`, `export const \w+ =`, `export (abstract )?class \w+`, `export (default )?interface \w+`; extract symbol names from pre and post content; classify added/removed
- [x] T029 [P] [US4] Add Rust regex detection to `cli/sentinel/interface_diff.py`: compile patterns for `pub (async )?fn \w+`, `pub struct \w+`, `pub trait \w+`, `pub enum \w+`; extract symbol names; classify added/removed
- [x] T030 [US4] Implement `ChangeRadiusEvaluator` in `cli/sentinel/cascade_analyzer.py`: `evaluate(files_changed, interface_reports, execution_plan) -> ChangeRadiusReport`; check three axes: `files_changed_count > config.radius_max_files`, `lines_changed_total > config.radius_max_lines`, `interface_changes_count > 0 and not allow_interface_changes`; detect cross-wave violations by comparing modified files against `execution_plan.json` task file_locks in other waves; return `ChangeRadiusReport` with `budget_exceeded` and `violations` list
- [x] T031 [US4] Implement `CascadeAnalyzer.annotate_tasks(affected_task_ids, sentinel_id, interface_changes) -> list[CascadeAnnotation]` in `cli/sentinel/cascade_analyzer.py`: for each affected pending task (`- [ ]` in tasks.md), find its line in tasks.md and append the cascade warning block (format from `data-model.md`); only target incomplete tasks; write updated tasks.md atomically; return list of applied annotations
- [ ] T032 [US4] Implement human-gated cascade mode in `cli/sentinel/cascade_analyzer.py`: `cascade_human_gated(affected_tasks, sentinel_id)`: print affected tasks with cascade details; prompt user for `[a]uto-apply / [r]eview-and-halt / [h]alt`; if `r` or `h` raise `WaveHaltError` with explanation; if `a` proceed to auto-annotate (call `annotate_tasks`)
- [ ] T033 [US4] Integrate `InterfaceDiff`, `ChangeRadiusEvaluator`, and `CascadeAnalyzer` into `SentinelRunner.run()` in `cli/sentinel/runner.py`: after test loop, for each modified file call `InterfaceDiff.compare()`; call `ChangeRadiusEvaluator.evaluate()`; if `budget_exceeded` and `mode=auto` call `annotate_tasks()`; if `mode=human-gated` call `cascade_human_gated()`; populate cascade fields in `ManifestData`
- [x] T034 [P] [US4] Write unit tests for `InterfaceDiff` in `tests/unit/sentinel/test_interface_diff.py`: test Python AST detects added/removed/changed function; test TypeScript regex detects exported function names; test Rust regex detects pub fn; test unknown file type returns empty report; test SyntaxError returns empty report without raising
- [x] T035 [P] [US4] Write unit tests for `CascadeAnalyzer` in `tests/unit/sentinel/test_cascade_analyzer.py`: test radius budget passes (1 file, 15 lines); test radius exceeded (4 files); test cascade annotates correct pending tasks; test completed tasks `[x]` are not annotated; test human-gated mode raises WaveHaltError on 'h' input

**Checkpoint**: US4 complete — cascade analysis and radius enforcement work with fixture execution plan.

---

## Phase 7: User Story 5 — Sentinel Is Configured and Monitored (Priority: P3)

**Goal**: `dev-kid.yml` controls all sentinel behavior without code changes. `dev-kid sentinel-status` shows a session dashboard. Custom patterns and exclude paths are configurable.

**Independent Test**: (1) Set `sentinel.enabled: false` in dev-kid.yml, run `dev-kid orchestrate`, confirm zero SENTINEL-* tasks in execution_plan.json. (2) Run `dev-kid sentinel-status` after a wave with 2 tasks, confirm table shows 2 SENTINEL runs with tier/iterations/result columns.

### Implementation for User Story 5

- [x] T036 [US5] Add `sentinel-status` command routing in `cli/dev-kid` (Bash): add `sentinel-status)` case to command routing; call `python3 cli/sentinel/status_reporter.py --project-root "$PROJECT_ROOT"`
- [ ] T037 [US5] Implement `cli/sentinel/status_reporter.py`: scan `.claude/sentinel/*/manifest.json` files; parse each manifest; render ASCII table with columns: Task, Sentinel ID, Tier Used, Iterations, Files Changed, Lines Changed, Placeholders, Result, Duration; sort by timestamp; print session totals (total runs, tier1-only count, tier2-escalation count, failure count)
- [ ] T038 [P] [US5] Write integration test for sentinel-disabled scenario in `tests/integration/sentinel/test_injection_round_trip.py`: load config with `sentinel_enabled=False`; run orchestrator on fixture tasks.md; assert zero SENTINEL tasks in resulting execution_plan.json; assert tasks.md unchanged (no SENTINEL lines appended); verify plan is identical to pre-sentinel baseline

**Checkpoint**: US5 complete — full operational control and monitoring verified.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final integration validation, documentation updates, and cleanup.

- [x] T039 [P] Update `CLAUDE.md` sentinel subsystem section: document `cli/sentinel/` module map (runner, tier_runner, placeholder_scanner, interface_diff, manifest_writer, cascade_analyzer, status_reporter), `.claude/sentinel/` runtime output convention, new `sentinel-status` CLI command
- [x] T040 [P] Update `memory-bank/shared/systemPatterns.md` with Integration Sentinel pattern: sentinel task injection flow, manifest-always-written invariant, cascade radius decision tree
- [x] T041 Run quickstart.md end-to-end validation: execute all steps in `quickstart.md` against a real test project initialized with `dev-kid init`; verify sentinel runs, manifest files appear, status dashboard shows correct data; document any deviations
- [ ] T042 [P] Security review of subprocess calls in `cli/sentinel/tier_runner.py`: verify all subprocess inputs are sanitized (objective string, test command, file paths); no shell=True usage; no credential leakage in logged output; no path traversal in manifest output directory

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
  - T004 (config) → T006 (dataclasses) → T007 (test detection) in sequence
  - T005 can run [P] with T004
  - T008 (orchestrator) depends on T006 — run after T006 complete
  - T009 (wave executor) depends on T006 — run after T006 complete
- **US1 (Phase 3)**: Depends on Phase 2 complete; T010→T011→T012[P]/T013[P]→T014→T015[P]→T016
- **US2 (Phase 4)**: Depends on Phase 2 complete; can start parallel to US1 after T014 exists (T018 integrates into runner.py)
- **US3 (Phase 5)**: Depends on US1 complete (manifest captures tier results); T022→T023→T024→T025[P]/T026[P]
- **US4 (Phase 6)**: Depends on US3 complete (interface changes go in manifest); T027→T028[P]/T029[P]→T030→T031→T032→T033→T034[P]/T035[P]
- **US5 (Phase 7)**: Depends on US3 complete (reads manifest files); T036→T037→T038[P]
- **Polish (Phase 8)**: All user stories complete; T039[P]/T040[P] parallel, then T041→T042[P]

### User Story Dependencies

- **US1 (P1)**: No dependency on other stories — start after Phase 2
- **US2 (P1)**: No dependency on other stories — start after Phase 2 (integrate into runner.py after T014 stub exists)
- **US3 (P2)**: Depends on US1 (manifest records tier results)
- **US4 (P2)**: Depends on US3 (cascade results written to manifest)
- **US5 (P3)**: Depends on US3 (status reporter reads manifests)

### Within Each User Story

- Config/dataclasses before classes that use them
- Connectivity checks before subprocess invocations that depend on them
- Core class implementation before integration into SentinelRunner
- Integration into SentinelRunner before integration tests

---

## Parallel Execution Examples

### Phase 2 Parallel Opportunities

```bash
# Run in parallel after T003:
Task "T004 Extend cli/config_manager.py"
Task "T005 Add sentinel config to dev-kid.yml"  # [P]
Task "T007 Implement detect_test_command"        # [P] after T006
Task "T008 Modify cli/orchestrator.py"           # after T006
Task "T009 Modify cli/wave_executor.py"          # after T006
```

### Phase 3 (US1) Parallel Opportunities

```bash
# After T011 complete, run T012 and T013 together:
Task "T012 Implement TierRunner.run_tier2()"     # [P]
Task "T013 Implement _parse_micro_agent_output()" # [P]

# After T014 (SentinelRunner core), run T015 in parallel with T016:
Task "T015 Unit tests for TierRunner"            # [P]
Task "T016 Integration test US1"
```

### Phase 6 (US4) Parallel Opportunities

```bash
# After T027 (Python AST base), run T028 and T029 together:
Task "T028 TypeScript regex detection"           # [P]
Task "T029 Rust regex detection"                 # [P]

# After T033 (integration complete), run unit tests together:
Task "T034 Unit tests for InterfaceDiff"         # [P]
Task "T035 Unit tests for CascadeAnalyzer"       # [P]
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: US1 — Tiered Test Loop
4. Complete Phase 4: US2 — Placeholder Detection
5. **STOP and VALIDATE**: Wave execution catches test failures AND placeholders
6. Demo: Run `dev-kid execute` on a wave with a known issue — confirm sentinel blocks checkpoint

### Incremental Delivery

1. **Foundation + US1** → Core test loop works → Validate with fixture
2. **+ US2** → Placeholders blocked → Validate with `tasks_with_placeholder.py` fixture
3. **+ US3** → Manifests always written → Check `.claude/sentinel/` after any run
4. **+ US4** → Cascade warnings annotate pending tasks → Validate with interface-change fixture
5. **+ US5** → `dev-kid sentinel-status` dashboard → Operational control complete

### Parallel Team Strategy

With two developers after Phase 2 complete:
- **Dev A**: Phase 3 (US1 — tiered test loop) → Phase 5 (US3 — manifests)
- **Dev B**: Phase 4 (US2 — placeholder detection) → Phase 6 (US4 — cascade)
- Both converge on Phase 7 + Polish

---

## Notes

- `[P]` tasks touch different files and have no incomplete dependencies — safe to parallelize
- `[USN]` label maps task to spec.md user story for traceability
- T008 and T009 modify existing files — coordinate with any concurrent development on orchestrator/executor
- The manifest output directory `.claude/sentinel/` should be added to `.gitignore` with exception: committed as part of wave checkpoint (`git add .claude/sentinel/`)
- All subprocess calls in `tier_runner.py` MUST use `check=False`, never `shell=True`
- **Total tasks**: 42 | **US1**: 7 | **US2**: 3 | **US3**: 5 | **US4**: 9 | **US5**: 3 | **Setup/Foundation**: 9 | **Polish**: 4
- **Parallel opportunities**: 18 tasks marked [P]
- **MVP scope**: T001–T016 (Phases 1–3: Foundation + US1 test loop, 16 tasks)

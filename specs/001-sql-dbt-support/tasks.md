# Tasks: SQL Pipeline & dbt Project Support

**Feature**: `001-sql-dbt-support`
**Branch**: `001-sql-dbt-support`
**Input**: `specs/001-sql-dbt-support/` (plan.md, spec.md, data-model.md, contracts/, research.md, quickstart.md)

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User story this task belongs to (US1–US4)
- All file paths are relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create test package skeleton and establish file structure per plan.md.

- [ ] T001 Create test package directories `tests/unit/sql/`, `tests/unit/dbt/`, `tests/integration/` with `__init__.py` in each; confirm `tests/__init__.py` exists

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared SQL utilities needed by US1, US2, and US3 before any story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Create `cli/sentinel/sql_utils.py` with two exported functions: (1) `strip_jinja(sql: str) -> str` — replace `{{ ref('model') }}` → `model`, `{{ source('s','t') }}` → `s__t`, remaining `{{ ... }}` → `1`, `{% ... %}` → `` (empty) using `re.sub` with `re.DOTALL`; (2) `try_import_sqlglot()` — attempts `import sqlglot, sqlglot.expressions as exp`, returns `(sqlglot, exp)` tuple or `(None, None)` with `warnings.warn("sqlglot not installed; falling back to regex")`

**Checkpoint**: `sql_utils.py` importable — user story implementation can now begin.

---

## Phase 3: User Story 1 — SQL Schema Change Safety (Priority: P1) 🎯 MVP

**Goal**: Detect breaking column changes (removals, type narrowing) in SQL migration files between wave start and wave end, and block the checkpoint if any are found.

**Independent Test**: Create a migration removing a column, run `python3 -c "from cli.sentinel.sql_schema_diff import DDLParser; ..."`, verify column removal detected and `is_breaking=True`.

### Implementation

- [ ] T003 [US1] Create `cli/sentinel/sql_schema_diff.py` — implement `ColumnDef` dataclass (`name: str, data_type: str, nullable: bool, is_pk: bool`) and `DDLParser` class with `parse_ddl(sql: str) -> dict[str, list[ColumnDef]]` method: strip Jinja via `sql_utils.strip_jinja()`, try sqlglot `parse_one(sql)` + iterate `ast.find_all(exp.ColumnDef)` extracting name/type/nullable/pk; on ImportError or ParseError fall back to regex `r"(\w+)\s+([\w\(\),\s]+?)(?:\s+NOT NULL|\s+NULL\b|,|\s*\))"`; return `{table_name: [ColumnDef, ...]}`

- [ ] T004 [US1] Add `SchemaSnapshot` class to `cli/sentinel/sql_schema_diff.py` with `capture_pre_wave(wave_id: int, sql_files: list[str], snapshot_dir: str = ".claude/schema_snapshots") -> None`: for each path in sql_files run `subprocess.run(["git", "show", f"HEAD:{path}"], ...)` (empty dict on error = new file); parse with `DDLParser.parse_ddl()`; serialise to `snapshot_dir/wave_{wave_id}_pre.json` as `{file_path: {table: [[col, type, nullable, pk], ...]}}`. Add `Path(snapshot_dir).mkdir(parents=True, exist_ok=True)` guard.

- [ ] T005 [US1] Add `SchemaDiffReport` dataclass (`wave_id: int, has_breaking_changes: bool, changes: list[dict]`) and `SchemaDiff` class to `cli/sentinel/sql_schema_diff.py` with `compare_post_wave(wave_id: int, sql_files: list[str], snapshot_dir: str = ".claude/schema_snapshots") -> SchemaDiffReport`: load pre-wave JSON; parse current file content with DDLParser; for each table compare column sets — `COLUMN_REMOVED` → `is_breaking=True`, `COLUMN_ADDED` → `is_breaking=False`, `TYPE_CHANGED` (narrower: INT→SMALLINT, BIGINT→INT, VARCHAR larger→smaller) → `is_breaking=True`, widening → `is_breaking=False`; populate `affected_models` by scanning `models/**/*.sql` for files referencing both table name and column name

- [ ] T006 [US1] Add `AffectedModelFinder` class to `cli/sentinel/sql_schema_diff.py` with `find_affected(table_name: str, column_name: str, models_dir: str = "models") -> list[str]`: walk `models/**/*.sql`, for each file check if it contains a ref/source to `table_name` AND the bare word `column_name` (word boundary `\b` regex); return list of model base names (no path, no `.sql`)

- [ ] T007 [US1] Modify `cli/sentinel/interface_diff.py`: locate the section that handles file extension routing; add an `elif path.suffix == ".sql":` branch that imports `cli.sentinel.sql_schema_diff` and calls `DDLParser.parse_ddl(path.read_text())`, returning the column dict; this replaces the current Python-AST no-op for `.sql` files

- [ ] T008 [US1] Modify `cli/wave_executor.py`: (1) in `execute_wave()` before agent task dispatch, collect `sql_files = [t.file_path for t in wave.tasks if t.file_path and t.file_path.endswith(".sql")]`; if non-empty call `SchemaSnapshot.capture_pre_wave(wave.wave_id, sql_files)`; (2) in `verify_wave_completion()` call `report = SchemaDiff.compare_post_wave(wave.wave_id, sql_files)`; if `report.has_breaking_changes` raise `WaveCheckpointError` with formatted message listing each breaking change and its `affected_models`

### Tests

- [ ] T009 [P] [US1] Write `tests/unit/sql/test_ddl_parser.py` — 6 test functions: (1) parse `CREATE TABLE orders (id BIGINT NOT NULL PRIMARY KEY, total DECIMAL(10,2) NULL)` → column names `["id","total"]`, types correct, id.is_pk=True; (2) parse Jinja DDL with `{{ ref('x') }}` stripped correctly; (3) `nullable=True` for NULL columns, `nullable=False` for NOT NULL; (4) regex fallback path when sqlglot absent (monkeypatch `sql_utils.try_import_sqlglot` to return None,None); (5) unrecognised DDL → empty dict, no exception; (6) multiple tables in one file → dict with 2 keys

- [ ] T010 [P] [US1] Write `tests/unit/sql/test_schema_diff.py` — 5 test functions using temp snapshot JSON files: (1) `COLUMN_REMOVED` → `is_breaking=True`, column in report `changes`; (2) `COLUMN_ADDED` → `is_breaking=False`; (3) `TYPE_CHANGED` BIGINT→INT → `is_breaking=True`; (4) `TYPE_CHANGED` INT→BIGINT → `is_breaking=False`; (5) no changes → `has_breaking_changes=False`, empty `changes` list

**Checkpoint**: US1 complete — schema diff detects column removals and blocks checkpoint.

---

## Phase 4: User Story 2 — dbt Dependency Wave Planning (Priority: P2)

**Goal**: Parse dbt `ref()` dependency graph from `manifest.json` (or regex fallback) and override wave assignment so upstream models always execute before downstream models.

**Independent Test**: Run `python3 -c "from cli.dbt_graph import DBTGraph; g = DBTGraph(); g.load('.')"` on a project with dbt models; verify stg/dim models get wave=1, fct model gets wave=2.

### Implementation

- [ ] T011 [US2] Create `cli/dbt_graph.py` — implement `DBTModel` dataclass (`name: str, file_path: str, materialization: str, has_description: bool, has_unique_key: bool, upstream: list[str], downstream: list[str], source: str = "manifest"`) and `DBTGraph` class with `load(project_root: str = ".") -> "DBTGraph"`: if `{project_root}/target/manifest.json` exists, parse it — iterate `data["nodes"]` for keys starting with `"model."`, extract `name`, `config.materialized`, `depends_on.nodes` (filter to model-only deps), `description != ""`, presence of `unique_key` in config; else scan `{project_root}/models/**/*.sql` with `REF_PATTERN = re.compile(r'\{\{\s*ref\s*\(\s*[\'"](\w+)[\'"]\s*\)\s*\}\}')` and `CONFIG_PATTERN = re.compile(r"materialized\s*=\s*['\"](\w+)['\"]")`; populate `self.nodes: dict[str, DBTModel]`; set downstream links by inverting upstream lists

- [ ] T012 [US2] Add `DBTTopologicalSort` to `cli/dbt_graph.py` with `assign_waves(task_model_names: list[str], graph: DBTGraph) -> dict[str, int]`: build sub-graph containing only models in `task_model_names`; run iterative level-based topological sort (wave=1 for nodes with no in-scope upstreams, wave=max(upstream waves)+1 otherwise); return `{model_name: wave_number}`

- [ ] T013 [US2] Add `CycleDetector` to `cli/dbt_graph.py` with `detect_cycle(graph: DBTGraph) -> Optional[str]`: DFS with WHITE/GRAY/BLACK colouring; on back-edge found reconstruct cycle path as `"a → b → c → a"` string; return path string or `None` if DAG is acyclic

- [ ] T014 [US2] Modify `cli/orchestrator.py`: after standard file-lock wave grouping, add block: `if Path("dbt_project.yml").exists():` → `graph = DBTGraph().load(".")` → `cycle = CycleDetector.detect_cycle(graph)` → if cycle `sys.exit(f"ERROR: Circular dbt dependency: {cycle}")` → `wave_overrides = DBTTopologicalSort.assign_waves(dbt_task_models, graph)` → remap affected task wave assignments in `execution_plan` using the override dict; tasks not in the dbt graph keep their file-lock-derived wave

### Tests

- [ ] T015 [P] [US2] Write `tests/unit/dbt/test_dbt_graph.py` — 5 test functions: (1) load from synthetic `manifest.json` fixture → correct `nodes` dict with names/materialization/upstream; (2) regex fallback scan synthetic `models/*.sql` files → detects `ref()` deps; (3) `has_description=True` when description is non-empty; (4) `has_unique_key=True` when `unique_key` present in config; (5) both paths produce equivalent graph for same project

- [ ] T016 [P] [US2] Write `tests/unit/dbt/test_dbt_wave_planning.py` — 4 test functions: (1) `stg_orders` + `dim_customers` (no upstream) → wave=1; `fct_orders` (refs both) → wave=2; (2) three independent models → all wave=1; (3) `CycleDetector` returns cycle path string for `a→b→a`; (4) `CycleDetector` returns None for valid DAG

**Checkpoint**: US2 complete — `dev-kid orchestrate` auto-orders dbt model tasks from dependency graph.

---

## Phase 5: User Story 3 — SQL & dbt Constitution Enforcement (Priority: P2)

**Goal**: Scan `.sql` and `.yml` staged files at each wave checkpoint against active constitution rules, blocking if any of the 5 built-in SQL/dbt rules are violated.

**Independent Test**: Create dbt model with `SELECT *`, enable `NO_SELECT_STAR` in `.constitution.md`, run sentinel scan — verify violation reported with file + line number.

### Implementation

- [ ] T017 [US3] Create `cli/sentinel/sql_constitution.py` — implement `ConstitutionViolation` dataclass (`rule: str, file_path: str, line: int, message: str`) and `SQLConstitutionScanner` class with `scan_file(path: str, enabled_rules: list[str]) -> list[ConstitutionViolation]`: read file, strip Jinja via `sql_utils.strip_jinja()`; for `NO_SELECT_STAR`: parse with sqlglot, detect `exp.Star` in any `exp.Select` (fallback regex `r"SELECT\s+\*\s+FROM"`); for `NO_HARDCODED_CREDENTIALS`: apply `CREDENTIAL_PATTERNS = [re.compile(r"(?i)(password|passwd|pwd)\s*=\s*'[^']{4,}'"), re.compile(r"(?i)(api_key|apikey|secret|token)\s*=\s*'[^']{8,}'")]`; for `INCREMENTAL_NEEDS_UNIQUE_KEY`: check `materialized='incremental'` present without `unique_key=` in same config block; for `MIGRATION_NEEDS_ROLLBACK`: only for files in `migrations/` directory — check file contains at least one of `-- rollback`, `-- down`, `-- revert`, `-- undo` (case-insensitive); return violations list with correct line numbers

- [ ] T018 [US3] Add `DBTSchemaYAMLScanner` class to `cli/sentinel/sql_constitution.py` with `scan_yaml(path: str, enabled_rules: list[str]) -> list[ConstitutionViolation]`: load YAML with `yaml.safe_load()` (fall back to line-by-line regex if PyYAML absent); for `MODEL_DESCRIPTION_REQUIRED`: iterate `data.get("models", [])`, flag each model where `description` key absent or empty string; for `INCREMENTAL_NEEDS_UNIQUE_KEY`: check models where `config.materialized == "incremental"` and `config.unique_key` absent; include file path + line number (PyYAML provides line info via `Loader=yaml.Loader`/mark)

- [ ] T019 [US3] Modify `cli/constitution_parser.py`: in the rule-extraction function, add SQL rule names to recognised rule set (`NO_SELECT_STAR`, `MODEL_DESCRIPTION_REQUIRED`, `INCREMENTAL_NEEDS_UNIQUE_KEY`, `NO_HARDCODED_CREDENTIALS`, `MIGRATION_NEEDS_ROLLBACK`); add `scan_sql_file(path, rules) -> list` and `scan_yaml_file(path, rules) -> list` routing functions that delegate to `SQLConstitutionScanner` and `DBTSchemaYAMLScanner` respectively

- [ ] T020 [US3] Modify `cli/sentinel/runner.py`: in the Tier 1 staged-file scan loop, add routing for `.sql` and `.yml` extensions — call `constitution_parser.scan_sql_file(path, active_rules)` for `.sql` files and `constitution_parser.scan_yaml_file(path, active_rules)` for `.yml` files; append violations to the existing violations list; format output as `❌ VIOLATION [{rule}] {file}:{line}\n   {message}`

### Tests

- [ ] T021 [P] [US3] Write `tests/unit/sql/test_sql_constitution.py` — 10 test functions (2 per rule): `NO_SELECT_STAR` violation on `SELECT * FROM t`, pass on `SELECT id FROM t`; `MODEL_DESCRIPTION_REQUIRED` violation on YAML model with no `description:`, pass when description present; `INCREMENTAL_NEEDS_UNIQUE_KEY` violation on `config(materialized='incremental')` without `unique_key`, pass when `unique_key='id'`; `NO_HARDCODED_CREDENTIALS` violation on `PASSWORD = 'secret123'`, pass on parameterised query; `MIGRATION_NEEDS_ROLLBACK` violation on migration file with no rollback marker, pass when `-- rollback` present

**Checkpoint**: US3 complete — constitution rules enforced at checkpoint for all `.sql` and `.yml` files.

---

## Phase 6: User Story 4 — SQL Placeholder Detection (Priority: P3)

**Goal**: Extend the Tier 1 placeholder scanner to detect SQL-specific stubs (`SELECT 1`, `-- TODO`, empty `ref()`) and block the checkpoint.

**Independent Test**: Stage `SELECT 1 AS placeholder` in a `.sql` file, run sentinel scan, verify `SELECT_ONE` violation blocked.

### Implementation

- [ ] T022 [US4] Modify `cli/sentinel/placeholder_scanner.py`: add `SQL_PLACEHOLDER_PATTERNS = {"SELECT_ONE": re.compile(r"^\s*SELECT\s+1\s*(?:AS\s+\w+\s*)?$", re.MULTILINE | re.IGNORECASE), "TODO_COMMENT": re.compile(r"--\s*(TODO|FIXME|STUB|PLACEHOLDER)\b", re.IGNORECASE), "EMPTY_REF": re.compile(r'ref\s*\(\s*[\'\"]{2}\s*\)')}` and `scan_sql_file(path: str) -> list[PlaceholderViolation]` function: read file, iterate each pattern, for each match find line number via `content[:match.start()].count("\n") + 1`, return `PlaceholderViolation(file_path=path, line=line, pattern_type=pattern_name, matched_text=match.group(0).strip())`

- [ ] T023 [US4] Modify `cli/sentinel/runner.py` (Tier 1 scan section): for `.sql` staged files additionally call `placeholder_scanner.scan_sql_file(path)` and append results to violations list; format output as `❌ PLACEHOLDER [{pattern_type}] {file}:{line}\n   Found: {matched_text}`

**Checkpoint**: US4 complete — all SQL placeholder patterns caught by Tier 1 sentinel.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Integration validation and documentation.

- [ ] T024 [P] Write `tests/integration/test_sql_dbt_e2e.py` — one end-to-end test using `tempfile.mkdtemp()` + `git init`: (1) creates `migrations/001_orders.sql` with CREATE TABLE, commits; (2) removes a column (breaking change); (3) creates 3 dbt models (stg, dim, fct with ref()); (4) writes `dbt_project.yml`; (5) runs `orchestrator.py` as subprocess, verifies `execution_plan.json` has stg/dim in wave 1, fct in wave 2; (6) runs schema diff check, verifies `has_breaking_changes=True`; (7) adds `NO_SELECT_STAR` to `.constitution.md`, stages a `SELECT *` model, verifies violation caught; (8) verifies total runtime < 10 seconds

- [ ] T025 [P] Validate all 5 quickstart.md scenarios manually (scenarios 1–5): run each bash block from `specs/001-sql-dbt-support/quickstart.md`, record actual vs expected output, update quickstart.md with actual output if they differ, mark each scenario PASS/FAIL

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — **blocks all user stories**
- **US1 (Phase 3)**: Requires Phase 2; T003→T004→T005→T006 sequential (same file); T007/T008 sequential on different files; T009/T010 parallel with each other
- **US2 (Phase 4)**: Requires Phase 2; T011→T012→T013 sequential (same file); T014 separate file; T015/T016 parallel with each other
- **US3 (Phase 5)**: Requires Phase 2; T017→T018 sequential (same file); T019/T020 separate files; T021 parallel with T019/T020
- **US4 (Phase 6)**: Requires Phase 2; T022→T023 sequential (same file)
- **Polish (Phase 7)**: Depends on US1–US4 completion

### User Story Dependencies

- **US1 (P1)**: No dependency on other user stories
- **US2 (P2)**: No dependency on US1 (different modules)
- **US3 (P2)**: Depends on Phase 2 (`sql_utils.py`); no dependency on US1 or US2
- **US4 (P3)**: No dependency on US1–US3 (extends existing `placeholder_scanner.py`)

### Parallel Opportunities

Within Phase 3 (US1): T009 + T010 can run in parallel after T003–T008 complete
Within Phase 4 (US2): T015 + T016 can run in parallel after T011–T014 complete
Within Phase 5 (US3): T021 can run in parallel with T019 + T020 after T017 + T018 complete
Within Phase 7: T024 + T025 can run in parallel
Cross-story: US1, US2, US3, US4 phases can be worked in parallel by different developers after Phase 2 completes

---

## Parallel Example: US1 Tests

```bash
# After T003–T008 complete, launch test writing in parallel:
Task: "Write tests/unit/sql/test_ddl_parser.py"   # T009
Task: "Write tests/unit/sql/test_schema_diff.py"  # T010
```

## Parallel Example: US2 Tests

```bash
# After T011–T014 complete, launch test writing in parallel:
Task: "Write tests/unit/dbt/test_dbt_graph.py"       # T015
Task: "Write tests/unit/dbt/test_dbt_wave_planning.py" # T016
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (`sql_utils.py`)
3. Complete Phase 3: US1 (sql_schema_diff.py + interface_diff.py + wave_executor.py hooks)
4. **STOP and VALIDATE**: `python3 -m pytest tests/unit/sql/ -q`
5. Breaking schema changes now blocked at checkpoint — MVP delivered

### Incremental Delivery

1. Setup + Foundational → `sql_utils.py` ready
2. US1 → Schema diff blocking at checkpoint (MVP!)
3. US2 → dbt wave ordering from DAG
4. US3 → Constitution enforcement for SQL/dbt files
5. US4 → SQL placeholder detection
6. Each story independently testable; each adds value without breaking prior stories

### Quick Validation Checklist (from quickstart.md)

```bash
# 1. SQL parsing works
python3 -c "from cli.sentinel.sql_schema_diff import DDLParser; print(DDLParser().parse_ddl('CREATE TABLE t (id INT NOT NULL)'))"

# 2. dbt graph detection works
python3 -c "from cli.dbt_graph import DBTGraph; g = DBTGraph(); print(g.load('.'))"

# 3. Constitution rule scan works
python3 -c "from cli.sentinel.sql_constitution import SQLConstitutionScanner; s = SQLConstitutionScanner(); print(s.scan_file('models/test.sql', ['NO_SELECT_STAR']))"

# 4. All tests pass
python3 -m pytest tests/unit/sql/ tests/unit/dbt/ tests/integration/ -q
```

---

## Notes

- Tasks T003–T008 are sequential within US1 (all modify `sql_schema_diff.py` or `wave_executor.py`)
- `sqlglot` is **optional** — every scanner must have a functioning regex fallback path
- `PyYAML` is **optional** — YAML scanner must fall back to line-by-line regex
- Constitution rules are **opt-in** — no SQL rule fires unless listed in `.constitution.md`
- Schema diff compares **git HEAD state** vs current file; no live DB connection required
- dbt graph only activates when `dbt_project.yml` found in project root

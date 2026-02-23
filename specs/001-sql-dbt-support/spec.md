# Feature Specification: SQL Pipeline & dbt Project Support

**Feature Branch**: `001-sql-dbt-support`
**Created**: 2026-02-23
**Status**: Draft

## User Scenarios & Testing *(mandatory)*

### User Story 1 — SQL Schema Change Safety (Priority: P1)

A data engineer modifies a SQL migration or dbt model and runs `dev-kid execute`. The system detects breaking changes — removed columns, renamed tables, dropped constraints — between the before and after state of the SQL files, and blocks the wave checkpoint until the engineer acknowledges or resolves them.

**Why this priority**: Schema regressions in SQL pipelines are silent and destructive. Downstream models, dashboards, and pipelines break without warning. This is the highest-value safety net the system can provide for data teams.

**Independent Test**: Create a migration that removes a column used by a downstream dbt model. Run `dev-kid execute`. Verify the checkpoint is blocked with a clear message naming the broken column and the affected downstream model.

**Acceptance Scenarios**:

1. **Given** a SQL migration that drops a column, **When** the wave checkpoint runs, **Then** the system reports the column removal and the names of any dbt models that reference it.
2. **Given** a SQL migration that renames a table, **When** the wave checkpoint runs, **Then** the system flags all downstream `ref()` or `source()` calls that will break.
3. **Given** a SQL migration with no breaking changes, **When** the wave checkpoint runs, **Then** the system passes and the wave proceeds.
4. **Given** a dbt model with a changed column signature, **When** the wave checkpoint runs, **Then** the system compares the new schema against any downstream selects and reports mismatches.

---

### User Story 2 — dbt Model Dependency Wave Planning (Priority: P2)

A data engineer has a `tasks.md` containing dbt model implementation tasks. When they run `dev-kid orchestrate`, the system reads the dbt project's dependency graph (`ref()` and `source()` calls) and automatically groups tasks so that upstream models are always implemented before downstream ones — without the engineer having to manually declare dependencies.

**Why this priority**: dbt projects have strict DAG execution order. Manually declaring dependencies in tasks.md is error-prone and duplicates information already in the dbt project. Automatic detection eliminates a category of wave ordering mistakes.

**Independent Test**: Create tasks.md with tasks for `stg_orders`, `fct_orders` (which refs `stg_orders`), and `dim_customers` (independent). Run `dev-kid orchestrate`. Verify `stg_orders` and `dim_customers` are in Wave 1 (parallel) and `fct_orders` is in Wave 2.

**Acceptance Scenarios**:

1. **Given** tasks for dbt models where model B refs model A, **When** orchestration runs, **Then** model A's task is placed in an earlier wave than model B's task.
2. **Given** tasks for dbt models with no inter-dependencies, **When** orchestration runs, **Then** all tasks are placed in the same parallel wave.
3. **Given** a project with no dbt models (pure SQL migrations), **When** orchestration runs, **Then** the system falls back to standard file-lock dependency detection.
4. **Given** a circular dependency in the dbt project, **When** orchestration runs, **Then** the system reports the cycle and halts with a clear error.

---

### User Story 3 — SQL & dbt Constitution Enforcement (Priority: P2)

A data engineer configures SQL/dbt-specific quality rules in the project constitution (e.g., no `SELECT *`, all models need descriptions, incremental models need `unique_key`). When `dev-kid execute` runs its wave checkpoints, the system scans staged `.sql` and dbt `.yml` files and blocks the checkpoint if any rules are violated, citing the exact file, line, and rule.

**Why this priority**: Data quality rules for SQL pipelines are well-understood but frequently skipped under time pressure. Automated enforcement at checkpoint time catches them before they reach production.

**Independent Test**: Write a dbt model using `SELECT *` and run `dev-kid execute`. Verify the checkpoint is blocked with a message citing the file name, line number, and rule `NO_SELECT_STAR`.

**Acceptance Scenarios**:

1. **Given** a dbt model using `SELECT *`, **When** the checkpoint runs, **Then** the system blocks with rule `NO_SELECT_STAR` and the file/line reference.
2. **Given** an incremental dbt model missing `unique_key`, **When** the checkpoint runs, **Then** the system blocks with rule `INCREMENTAL_NEEDS_UNIQUE_KEY`.
3. **Given** a dbt model with no description in its `.yml` schema file, **When** the checkpoint runs, **Then** the system blocks with rule `MODEL_DESCRIPTION_REQUIRED`.
4. **Given** a dbt model that satisfies all active constitution rules, **When** the checkpoint runs, **Then** the checkpoint passes and the wave proceeds.

---

### User Story 4 — SQL Placeholder Detection (Priority: P3)

A data engineer accidentally commits a dbt model containing stub code (`SELECT 1 AS placeholder`, `-- TODO: implement`, empty `ref()` stubs). The sentinel's placeholder scan detects these during wave execution and blocks the checkpoint before incomplete code reaches the pipeline.

**Why this priority**: SQL stubs are as dangerous as Python stubs but harder to spot in code review. Automated detection prevents incomplete models from being treated as production-ready.

**Independent Test**: Create a dbt model containing `SELECT 1 AS placeholder`. Run `dev-kid execute`. Verify Tier 1 sentinel scan blocks the checkpoint with the file name and line.

**Acceptance Scenarios**:

1. **Given** a SQL file containing `SELECT 1` with no meaningful projection, **When** the sentinel scans, **Then** it reports a placeholder violation.
2. **Given** a dbt model containing `-- TODO` or `-- FIXME` comments, **When** the sentinel scans, **Then** it reports a placeholder violation.
3. **Given** a dbt model with a `ref('')` stub (empty ref), **When** the sentinel scans, **Then** it reports a placeholder violation.
4. **Given** a complete, production-ready dbt model, **When** the sentinel scans, **Then** no placeholder violations are reported.

---

### Edge Cases

- What happens when a dbt project has hundreds of models but only a few are in tasks.md? System only enforces dependencies for in-scope tasks; the rest of the DAG is ignored.
- How does the system handle SQL files that are not dbt models (raw migrations, seed files)? Schema diff runs; dbt-specific rules are skipped for non-model files.
- What happens when the dbt project has never been compiled (no `manifest.json`)? System falls back to parsing `ref()` calls directly from model source files.
- What if a column is removed but no dbt model references it? The schema diff reports the removal as informational, not blocking, unless a constitution rule requires explicit deprecation steps.
- What happens when `.yml` schema files are missing entirely for a dbt model? `MODEL_DESCRIPTION_REQUIRED` triggers only if that rule is enabled in the constitution.

## Requirements *(mandatory)*

### Functional Requirements

**SQL Schema Diff**
- **FR-001**: System MUST compare column signatures of SQL tables/views before and after a wave to detect breaking changes (removed columns, type changes, renamed columns).
- **FR-002**: System MUST identify which downstream dbt models reference a changed column and include them in the violation report.
- **FR-003**: System MUST treat column removals and type changes as blocking violations; column additions as non-blocking informational notices.

**dbt Dependency Graph**
- **FR-004**: System MUST parse `ref()` and `source()` calls from dbt model files to build an inter-model dependency graph.
- **FR-005**: System MUST use the dependency graph to assign tasks to waves such that upstream model tasks always precede downstream model tasks.
- **FR-006**: System MUST detect circular dependencies in the dbt graph and halt orchestration with a clear error identifying the cycle.
- **FR-007**: When `manifest.json` is absent, system MUST fall back to parsing `ref()` calls directly from `.sql` model source files.

**Constitution Enforcement for SQL/dbt**
- **FR-008**: System MUST scan staged `.sql` and dbt `.yml` schema files for active constitution rule violations at each wave checkpoint.
- **FR-009**: System MUST support the following built-in SQL/dbt constitution rules: `NO_SELECT_STAR`, `MODEL_DESCRIPTION_REQUIRED`, `INCREMENTAL_NEEDS_UNIQUE_KEY`, `NO_HARDCODED_CREDENTIALS`, `MIGRATION_NEEDS_ROLLBACK`.
- **FR-010**: Each constitution violation report MUST include: rule name, file path, line number, and a plain-language explanation.

**SQL Placeholder Detection**
- **FR-011**: System MUST detect SQL placeholder patterns: `SELECT 1` with no meaningful projection, `-- TODO` / `-- FIXME` / `-- STUB` comments, and empty `ref('')` calls.
- **FR-012**: SQL placeholder violations MUST block the wave checkpoint the same as other Tier 1 sentinel violations.

**Speckit Artifacts for SQL Projects**
- **FR-013**: When a speckit plan is generated for a SQL/dbt project, `data-model.md` MUST express entities as DDL-style table definitions (columns, types, constraints).
- **FR-014**: When a speckit plan is generated for a SQL/dbt project, `contracts/` MUST contain SQL DDL schemas rather than API endpoint definitions.

### Key Entities

- **SQL Schema Snapshot**: A point-in-time record of a table or view's column names, data types, and constraints — captured before and after a wave for diff comparison.
- **dbt Model**: A SQL file in a dbt project that selects from other models or sources via `ref()` / `source()` calls. Has a name, dependency list, materialization type, and optional `.yml` description.
- **dbt Dependency Graph**: A directed acyclic graph where nodes are dbt models and edges represent `ref()` relationships. Used to determine wave ordering.
- **SQL Constitution Rule**: A named, configurable quality standard applicable to `.sql` or dbt `.yml` files. Has an identifier, a violation pattern, and a severity level.
- **SQL Placeholder**: A pattern in a SQL file indicating incomplete implementation (`SELECT 1`, `-- TODO`, empty `ref()`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of breaking schema changes (column removals, type changes) in a wave are detected and reported before the checkpoint passes.
- **SC-002**: dbt model task ordering is correct in 100% of orchestration runs — no downstream model task is ever placed in an earlier wave than a task it depends on.
- **SC-003**: All 5 built-in SQL/dbt constitution rules produce zero false negatives on their defined violation patterns when enabled.
- **SC-004**: SQL placeholder detection catches 100% of `SELECT 1` stubs, `-- TODO` comments, and empty `ref()` calls in staged files.
- **SC-005**: A data engineer with an existing dbt project can run `dev-kid orchestrate` and get a correctly wave-ordered plan without manually declaring any dbt dependencies in tasks.md.
- **SC-006**: Wave checkpoint overhead for SQL/dbt validation adds no more than 5 seconds for a project with up to 200 dbt models.

## Assumptions

- dbt model files use the `.sql` extension and live under a `models/` directory (standard dbt layout).
- dbt schema files (`.yml`) follow the standard dbt schema format with `models:` → `columns:` structure.
- SQL migrations follow a file-per-migration convention with sequential numbering or timestamp prefixes.
- `manifest.json` is used when available for faster dependency resolution; raw source parsing is the fallback.
- Constitution rules for SQL are opt-in — enabling them requires adding them to `.constitution.md`. No SQL rules are enforced by default.
- The schema diff compares staged git changes (DDL in files), not a live database connection.

# Data Model: SQL Pipeline & dbt Project Support

**Branch**: `001-sql-dbt-support`
**Date**: 2026-02-23

This feature extends dev-kid's internals. Entities map to new Python modules and state files.

---

## Entity: SQLSchemaSnapshot

Captured before a wave executes. Persisted to disk to survive context compression.

```sql
-- Stored as .claude/schema_snapshots/wave_{N}_pre.json
-- Logical schema:

CREATE TABLE sql_schema_snapshot (
    wave_id       INTEGER      NOT NULL,
    file_path     VARCHAR(512) NOT NULL,
    table_name    VARCHAR(255) NOT NULL,
    column_name   VARCHAR(255) NOT NULL,
    data_type     VARCHAR(128) NOT NULL,
    nullable      BOOLEAN      NOT NULL DEFAULT TRUE,
    is_primary_key BOOLEAN     NOT NULL DEFAULT FALSE,
    captured_at   TIMESTAMP    NOT NULL,
    PRIMARY KEY (wave_id, file_path, table_name, column_name)
);
```

**Relationships**:
- One snapshot per (wave, file, table) combination
- Compared against post-wave state to produce `SQLSchemaDiff`

**State transitions**: `pending` → `captured` → `compared` → `archived`

---

## Entity: SQLSchemaDiff

Result of comparing pre- and post-wave snapshots. Drives checkpoint blocking decisions.

```sql
CREATE TABLE sql_schema_diff (
    wave_id          INTEGER      NOT NULL,
    file_path        VARCHAR(512) NOT NULL,
    table_name       VARCHAR(255) NOT NULL,
    change_type      VARCHAR(32)  NOT NULL,  -- COLUMN_REMOVED | TYPE_CHANGED | TABLE_DROPPED | COLUMN_ADDED | TABLE_ADDED
    column_name      VARCHAR(255),
    old_value        VARCHAR(256),
    new_value        VARCHAR(256),
    is_breaking      BOOLEAN      NOT NULL,
    affected_models  TEXT,                   -- JSON array of downstream dbt model names
    PRIMARY KEY (wave_id, file_path, table_name, change_type, column_name)
);
```

**Breaking rules**:
- `COLUMN_REMOVED` → `is_breaking = TRUE`
- `TYPE_CHANGED` (narrowing) → `is_breaking = TRUE`
- `TABLE_DROPPED` → `is_breaking = TRUE`
- `COLUMN_ADDED`, `TABLE_ADDED`, `TYPE_CHANGED` (widening) → `is_breaking = FALSE`

---

## Entity: DBTModel

Represents a single dbt model parsed from `manifest.json` or raw `.sql` source.

```sql
CREATE TABLE dbt_model (
    model_id          VARCHAR(255) NOT NULL PRIMARY KEY,  -- "model.project.stg_orders"
    model_name        VARCHAR(255) NOT NULL,              -- "stg_orders"
    file_path         VARCHAR(512) NOT NULL,              -- "models/staging/stg_orders.sql"
    materialization   VARCHAR(32)  NOT NULL,              -- table | view | incremental | ephemeral
    has_description   BOOLEAN      NOT NULL DEFAULT FALSE,
    has_unique_key    BOOLEAN      NOT NULL DEFAULT FALSE, -- incremental models only
    source            VARCHAR(16)  NOT NULL DEFAULT 'manifest'  -- manifest | regex_fallback
);
```

---

## Entity: DBTDependencyEdge

Directed edge in the dbt model dependency graph.

```sql
CREATE TABLE dbt_dependency_edge (
    upstream_model_id   VARCHAR(255) NOT NULL,  -- e.g. "model.project.stg_orders"
    downstream_model_id VARCHAR(255) NOT NULL,  -- e.g. "model.project.fct_orders"
    edge_type           VARCHAR(16)  NOT NULL,  -- model | source
    PRIMARY KEY (upstream_model_id, downstream_model_id)
);
```

**Graph properties**:
- Must be a DAG (no cycles)
- Cycle detected → orchestration halts with error naming the cycle path
- Wave assignment uses topological sort: task's wave = max(upstream task waves) + 1

---

## Entity: SQLConstitutionRule

Extends the existing `ConstitutionRule` entity to support SQL/dbt file types.

```sql
CREATE TABLE sql_constitution_rule (
    rule_id      VARCHAR(64)  NOT NULL PRIMARY KEY,
    file_types   VARCHAR(64)  NOT NULL,  -- ".sql" | ".yml" | ".sql,.yml"
    description  TEXT         NOT NULL,
    severity     VARCHAR(16)  NOT NULL DEFAULT 'BLOCKING',  -- BLOCKING | WARNING
    enabled      BOOLEAN      NOT NULL DEFAULT FALSE        -- opt-in
);

-- Seed data (built-in rules):
INSERT INTO sql_constitution_rule VALUES
  ('NO_SELECT_STAR',                '.sql',      'SELECT * is forbidden in production models',            'BLOCKING', FALSE),
  ('MODEL_DESCRIPTION_REQUIRED',    '.yml',      'All dbt models must have a description in schema.yml', 'BLOCKING', FALSE),
  ('INCREMENTAL_NEEDS_UNIQUE_KEY',  '.sql,.yml', 'Incremental models must declare a unique_key',         'BLOCKING', FALSE),
  ('NO_HARDCODED_CREDENTIALS',      '.sql',      'No passwords or API keys in SQL source files',         'BLOCKING', FALSE),
  ('MIGRATION_NEEDS_ROLLBACK',      '.sql',      'Migration files must include a rollback/down section', 'BLOCKING', FALSE);
```

---

## Entity: SQLPlaceholder

A detected stub or incomplete code pattern in a SQL/dbt file.

```sql
CREATE TABLE sql_placeholder (
    file_path     VARCHAR(512) NOT NULL,
    line_number   INTEGER      NOT NULL,
    pattern_type  VARCHAR(32)  NOT NULL,  -- SELECT_ONE | TODO_COMMENT | EMPTY_REF | FIXME_COMMENT
    matched_text  TEXT         NOT NULL,
    PRIMARY KEY (file_path, line_number, pattern_type)
);
```

**Detection patterns**:
| `pattern_type` | Example | Regex |
|----------------|---------|-------|
| `SELECT_ONE` | `SELECT 1` | `^\s*SELECT\s+1\s*$` |
| `TODO_COMMENT` | `-- TODO: implement` | `--\s*(TODO\|FIXME\|STUB\|PLACEHOLDER)` |
| `EMPTY_REF` | `ref('')` | `ref\s*\(\s*['"]{2}\s*\)` |
| `STUB_MODEL` | entire model is `SELECT 1 AS placeholder` | single SELECT with literal only |

---

## Entity Relationships

```
tasks.md tasks
    │
    ├──[file_locks: *.sql]──→ SQLSchemaSnapshot (pre-wave)
    │                                │
    │                         [post-wave compare]
    │                                │
    │                         SQLSchemaDiff
    │                                │
    │                         [is_breaking?] ──→ BLOCK checkpoint
    │
    ├──[file_locks: models/*.sql] ──→ DBTModel
    │                                     │
    │                               DBTDependencyEdge
    │                                     │
    │                               [topological sort]
    │                                     │
    │                               Wave assignment
    │
    └──[checkpoint validation] ──→ SQLConstitutionRule (scan .sql + .yml)
                               ──→ SQLPlaceholder (scan .sql)
```

# Research: SQL Pipeline & dbt Project Support

**Branch**: `001-sql-dbt-support`
**Date**: 2026-02-23
**Status**: Complete — all NEEDS CLARIFICATION resolved

---

## Decision 1: SQL Parsing Library

**Decision**: `sqlglot` (v28.10.1, released February 9 2026)

**Rationale**:
- Full AST parser (recursive descent), not merely a tokenizer like `sqlparse`
- Natively detects `SELECT *` via `expressions.Star` node in AST
- Supports 31 SQL dialects including Snowflake, BigQuery, Postgres, DuckDB — critical for dbt users
- Used by Apache Superset, dbt column lineage tools, and other production data tooling
- Actively maintained (release Feb 2026 confirms ongoing support)
- No transitive dependencies beyond the package itself

**Alternatives considered**:
- `sqlparse` — rejected: tokenizer only, no AST, cannot reliably detect SELECT * or parse CREATE TABLE column types
- `sql-metadata` — rejected: wraps sqlparse, inherits same limitations, primarily for table/column name extraction not DDL analysis
- Regex only — retained as fallback for Jinja-templated dbt SQL (see Decision 3)

**Key API patterns**:
```python
import sqlglot
import sqlglot.expressions as exp

# Parse CREATE TABLE and extract columns
ast = sqlglot.parse_one("CREATE TABLE orders (id INT NOT NULL, total DECIMAL)", dialect="snowflake")
for col in ast.find_all(exp.ColumnDef):
    name = col.name
    dtype = col.args.get("kind")

# Detect SELECT *
for select in ast.find_all(exp.Select):
    has_star = any(isinstance(e, exp.Star) for e in select.expressions)

# Detect hardcoded credentials (regex, not sqlglot — SQL strings aren't secret-aware)
import re
SECRET_PATTERNS = [
    r"(?i)(password|passwd|pwd|api_key|secret|token)\s*=\s*'[^']{6,}'",
    r"(?i)(password|passwd|pwd|api_key|secret|token)\s*=\s*\"[^\"]{6,}\"",
]
```

**dbt Jinja handling**:
dbt SQL files contain `{{ ref('model') }}` and `{{ config(...) }}` Jinja syntax that breaks sqlglot parsing. Standard approach (used by dbt column lineage tooling): strip Jinja tokens before parsing.
```python
import re
def strip_jinja(sql: str) -> str:
    # Replace {{ ref('model') }} → model (bare name, valid SQL table ref)
    sql = re.sub(r"\{\{\s*ref\s*\(\s*['\"](\w+)['\"]\s*\)\s*\}\}", r"\1", sql)
    # Replace {{ source('src', 'tbl') }} → src__tbl
    sql = re.sub(r"\{\{\s*source\s*\(\s*['\"](\w+)['\"],\s*['\"](\w+)['\"]\s*\)\s*\}\}", r"\1__\2", sql)
    # Remove remaining {{ ... }} blocks
    sql = re.sub(r"\{\{.*?\}\}", "1", sql, flags=re.DOTALL)
    sql = re.sub(r"\{%.*?%\}", "", sql, flags=re.DOTALL)
    return sql
```

---

## Decision 2: SQL Schema Snapshot Strategy

**Decision**: Hybrid — `git show HEAD:file` (primary) + disk-persisted JSON snapshot (fallback/durability)

**Rationale**:
- `git show HEAD:file` gives the last committed state cleanly — zero extra overhead, aligns with existing `InterfaceDiff.get_pre_content()` pattern in the sentinel
- JSON snapshots persisted to `.claude/schema_snapshots/` survive context compression (critical for dev-kid's resilience model)
- New files (not yet in HEAD) handled by in-memory capture at wave start
- Column additions are non-blocking; removals and type changes block the checkpoint

**Git command**:
```bash
git show HEAD:migrations/001_orders.sql   # pre-wave committed state
git diff --name-only HEAD -- '*.sql'      # SQL files modified in wave
```

**Snapshot schema** (`.claude/schema_snapshots/wave_{N}_pre.json`):
```json
{
  "migrations/001_orders.sql": {
    "orders": [
      ["id", "INT", false, true],
      ["total", "DECIMAL", true, false]
    ]
  }
}
```

**Breaking vs non-breaking**:
| Change | Classification |
|--------|---------------|
| Column removed | BLOCKING — breaks downstream |
| Column type narrowed (e.g. BIGINT → INT) | BLOCKING |
| Column made NOT NULL | BLOCKING (if data exists) |
| Column added | informational only |
| Column type widened | informational only |
| Table added | informational only |
| Table dropped | BLOCKING |

**Alternatives considered**:
- Live database connection — rejected: requires credentials, environment, breaks offline dev
- Git staging area — rejected: complex parsing, not useful for inter-wave comparison
- Full DDL text diff — rejected: too noisy, hard to reason about semantically

---

## Decision 3: dbt Dependency Graph — manifest.json vs Regex Fallback

**Decision**: `manifest.json` (primary, `target/manifest.json`) with regex fallback when absent

**manifest.json structure** (dbt Core 1.5+):
```
manifest.json
├── nodes: {
│     "model.project.stg_orders": {
│       "name": "stg_orders",
│       "config": { "materialized": "view" },
│       "depends_on": { "nodes": ["model.project.raw_orders"] },
│       "columns": {
│         "order_id": { "name": "order_id", "description": "PK" }
│       }
│     }
│   }
├── parent_map: { "model.X": ["model.Y", "source.Z"] }
└── child_map:  { "model.X": ["model.A", "model.B"] }
```

**Key field paths**:
- Dependencies: `nodes[id].depends_on.nodes[]` (array of upstream node IDs)
- Materialization: `nodes[id].config.materialized` — values: `"table"`, `"view"`, `"incremental"`, `"ephemeral"`
- Column descriptions: `nodes[id].columns[col_name].description`
- Model description: `nodes[id].description`
- File path: `target/manifest.json` (standard dbt project layout)

**Regex fallback** (when `manifest.json` absent):
```python
REF_PATTERN    = re.compile(r"\{\{\s*ref\s*\(\s*['\"](\w+)['\"]\s*\)\s*\}\}")
SOURCE_PATTERN = re.compile(r"\{\{\s*source\s*\(\s*['\"](\w+)['\"],\s*['\"](\w+)['\"]\s*\)\s*\}\}")
CONFIG_PATTERN = re.compile(r"\{\{\s*config\s*\(.*?materialized\s*=\s*['\"](\w+)['\"]\s*.*?\)\s*\}\}", re.DOTALL)
```

**Wave ordering from DAG**:
- Build dependency graph from `depends_on.nodes` (or regex)
- Topological sort → assigns minimum wave number per model
- Only consider tasks in `tasks.md` scope (ignore rest of DAG)
- Circular dependency → halt orchestration with clear error naming the cycle

**Alternatives considered**:
- `dbt ls --select +model` runtime call — rejected: requires dbt installed + compiled project
- dbt Python API — rejected: heavy dependency, version-sensitive

---

## Decision 4: SQL/dbt Constitution Rules Implementation

**Decision**: Extend `constitution_parser.py` with SQL/dbt rule handlers that scan `.sql` and `.yml` files

**5 built-in rules and their detection patterns**:

| Rule ID | File types | Detection |
|---------|-----------|-----------|
| `NO_SELECT_STAR` | `.sql` | sqlglot AST `exp.Star` in SELECT, or regex `SELECT\s+\*\s+FROM` |
| `MODEL_DESCRIPTION_REQUIRED` | `.yml` | YAML `models[].description` is empty or missing |
| `INCREMENTAL_NEEDS_UNIQUE_KEY` | `.sql`, `.yml` | `materialized=incremental` in config + missing `unique_key` |
| `NO_HARDCODED_CREDENTIALS` | `.sql` | Regex on string literals for password/api_key/secret patterns |
| `MIGRATION_NEEDS_ROLLBACK` | `.sql` | File contains UP section but no `-- rollback` / `-- down` marker |

**Hardcoded credential regex** (regex, not sqlglot — secret detection is string-level):
```python
CREDENTIAL_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd)\s*=\s*'[^']{4,}'"),
    re.compile(r"(?i)(api_key|apikey|secret|token)\s*=\s*'[^']{8,}'"),
    re.compile(r"(?i)(password|passwd|pwd)\s*=\s*\"[^\"]{4,}\""),
]
```

---

## Decision 5: Speckit SQL/dbt Artifact Format

**Decision**: Auto-detect project type from file structure; generate DDL-style `data-model.md` and SQL DDL `contracts/` when dbt project detected

**Detection heuristic**: presence of `dbt_project.yml` or `models/` directory → SQL/dbt mode

**data-model.md format** (DDL-style for SQL projects):
```sql
-- Entity: orders
CREATE TABLE orders (
    order_id    BIGINT      NOT NULL PRIMARY KEY,
    customer_id BIGINT      NOT NULL REFERENCES customers(customer_id),
    total       DECIMAL(10,2) NOT NULL,
    status      VARCHAR(20) NOT NULL DEFAULT 'pending',
    created_at  TIMESTAMP   NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**contracts/ format** (SQL DDL schemas instead of OpenAPI):
```sql
-- Contract: stg_orders (staging model)
-- Materialization: view
-- Upstream: source('raw', 'orders')
SELECT
    order_id::BIGINT,
    customer_id::BIGINT,
    total::DECIMAL(10,2),
    status::VARCHAR(20),
    created_at::TIMESTAMP
FROM {{ source('raw', 'orders') }}
```

---

## Summary: Zero-New-External-Dependency Strategy

All SQL/dbt support is implementable with:
- `sqlglot` — single new dependency (pure Python, no C extensions, pip installable)
- `PyYAML` — already present in most Python environments; needed for `.yml` schema parsing
- `re`, `json`, `pathlib`, `subprocess` — standard library only

The `sqlglot` dependency is conditional: falls back gracefully to regex-only if not installed, with a warning. This keeps dev-kid's zero-mandatory-dependency philosophy intact for users who don't need SQL support.

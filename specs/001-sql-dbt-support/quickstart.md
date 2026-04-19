# Quickstart: SQL Pipeline & dbt Project Support

**Branch**: `001-sql-dbt-support`
**Date**: 2026-02-23

Test scenarios for manual and automated validation. Each scenario maps to a user story.

---

## Scenario 1: SQL Schema Change Safety (US1 — P1)

**Goal**: Verify that removing a column from a migration blocks the wave checkpoint.

**Setup**:
```bash
cd /tmp/test-sql-sentinel
git init && dev-kid init

# Create a migration with initial schema
mkdir -p migrations
cat > migrations/001_orders.sql << 'EOF'
CREATE TABLE orders (
    order_id     BIGINT        NOT NULL PRIMARY KEY,
    customer_id  BIGINT        NOT NULL,
    total        DECIMAL(10,2) NOT NULL,
    discount_pct DECIMAL(5,2)  NULL
);
EOF
git add migrations/001_orders.sql && git commit -m "initial migration"
```

**Task**:
```markdown
# tasks.md
- [ ] T001 Update orders table in `migrations/001_orders.sql` — remove discount_pct, add coupon_code
```

**Wave execution**:
```bash
dev-kid orchestrate "Schema Safety Test"
# Manually modify migrations/001_orders.sql: remove discount_pct column
dev-kid execute
```

**Expected result**:
```
⚠️  Schema Breaking Changes Detected in Wave 1:
   migrations/001_orders.sql: orders.discount_pct REMOVED
   Affected downstream models: fct_orders, rpt_revenue_daily

🚫 Checkpoint BLOCKED: 1 breaking schema change(s)
   Review changes and mark tasks [x] only after resolving downstream impact.
```

**Pass criteria**: Checkpoint blocked; `execution_plan.json` wave 1 status = `BLOCKED`.

---

## Scenario 2: dbt Dependency Wave Planning (US2 — P2)

**Goal**: Verify that dbt model dependencies produce correct wave ordering without manual declaration.

**Setup**:
```bash
cd /tmp/test-dbt-wave
git init && dev-kid init
mkdir -p models/staging models/marts

cat > models/staging/stg_orders.sql << 'EOF'
SELECT order_id, customer_id, total
FROM {{ source('raw', 'orders') }}
EOF

cat > models/staging/dim_customers.sql << 'EOF'
SELECT customer_id, name, email
FROM {{ source('raw', 'customers') }}
EOF

cat > models/marts/fct_orders.sql << 'EOF'
SELECT o.order_id, c.name, o.total
FROM {{ ref('stg_orders') }} o
JOIN {{ ref('dim_customers') }} c ON o.customer_id = c.customer_id
EOF
```

**Task**:
```markdown
# tasks.md
- [ ] T001 Implement stg_orders model in `models/staging/stg_orders.sql`
- [ ] T002 Implement dim_customers model in `models/staging/dim_customers.sql`
- [ ] T003 Implement fct_orders model in `models/marts/fct_orders.sql`
```

**Orchestration**:
```bash
dev-kid orchestrate "dbt Wave Test"
cat execution_plan.json | jq '.execution_plan.waves[] | {wave: .wave_id, tasks: [.tasks[].task_id]}'
```

**Expected output**:
```json
{ "wave": 1, "tasks": ["T001", "T002"] }
{ "wave": 2, "tasks": ["T003"] }
```

**Pass criteria**: T001 and T002 in Wave 1 (parallel); T003 in Wave 2.

---

## Scenario 3: SQL Constitution Enforcement — NO_SELECT_STAR (US3 — P2)

**Goal**: Verify that `SELECT *` in a dbt model blocks the checkpoint when rule is enabled.

**Setup**:
```bash
cd /tmp/test-sql-constitution
git init && dev-kid init

# Enable constitution rule
mkdir -p memory-bank/shared
cat > memory-bank/shared/.constitution.md << 'EOF'
# Project Constitution

## SQL Standards
- NO_SELECT_STAR
EOF

cat > models/marts/fct_orders.sql << 'EOF'
SELECT * FROM {{ ref('stg_orders') }}
EOF
git add . && git commit -m "initial"
```

**Wave execution** (agent modifies fct_orders.sql but keeps SELECT *):
```bash
dev-kid orchestrate "Constitution Test"
dev-kid execute
```

**Expected result**:
```
🔍 Sentinel Tier 1: Scanning staged files...
   ❌ VIOLATION [NO_SELECT_STAR] models/marts/fct_orders.sql:1
      SELECT * is forbidden. Explicitly list columns.

🚫 Checkpoint BLOCKED: 1 constitution violation(s)
```

**Pass criteria**: Checkpoint blocked; `NO_SELECT_STAR` violation reported with file + line.

---

## Scenario 4: SQL Placeholder Detection (US4 — P3)

**Goal**: Verify that `SELECT 1` stubs and `-- TODO` comments trigger Tier 1 sentinel.

**Setup**:
```bash
cat > models/staging/stg_orders.sql << 'EOF'
-- TODO: implement staging model
SELECT 1 AS placeholder
EOF
git add models/staging/stg_orders.sql
```

**Wave execution**:
```bash
dev-kid execute
```

**Expected result**:
```
🔍 Sentinel Tier 1: Scanning staged files...
   ❌ PLACEHOLDER [TODO_COMMENT] models/staging/stg_orders.sql:1
      Found: -- TODO: implement staging model
   ❌ PLACEHOLDER [SELECT_ONE] models/staging/stg_orders.sql:2
      Found: SELECT 1 AS placeholder

🚫 Checkpoint BLOCKED: 2 placeholder violation(s)
```

**Pass criteria**: Both violations reported; checkpoint blocked.

---

## Scenario 5: Full dbt Project — End-to-End (Integration)

**Goal**: Verify all components work together on a realistic dbt project with mixed models.

```bash
# Use a real dbt project or the dev-kid integration test fixture
dev-kid orchestrate "Full dbt Integration"
dev-kid execute

# Expected: waves respect dbt DAG, schema diff runs on migrations,
# constitution rules check all .sql + .yml files, placeholders caught
```

**Pass criteria**:
- Wave ordering matches dbt `ref()` graph
- Schema diffs reported at each wave checkpoint
- All enabled constitution rules enforced
- No placeholder code reaches a committed checkpoint
- End-to-end time for 50-model project: < 30 seconds total

---

## Quick Validation Checklist

```bash
# 1. SQL parsing works
python3 -c "from cli.sentinel.sql_schema_diff import DDLParser; print(DDLParser.parse_file('CREATE TABLE t (id INT NOT NULL)'))"

# 2. dbt graph detection works
python3 -c "from cli.dbt_graph import DBTGraph; g = DBTGraph(); print(g.load())"

# 3. Constitution rule scan works
python3 -c "from cli.sentinel.sql_constitution import SQLConstitutionScanner; s = SQLConstitutionScanner(); print(s.scan_file('models/test.sql'))"

# 4. All tests pass
python3 -m pytest tests/unit/sql/ tests/unit/dbt/ tests/integration/ -q
```

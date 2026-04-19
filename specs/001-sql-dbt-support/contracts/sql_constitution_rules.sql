-- Contract: SQL/dbt Constitution Rule Enforcement Interface
-- Module: cli/sentinel/sql_constitution.py  (extends constitution_parser.py)
-- Consumed by: wave_executor.py checkpoint, cli/sentinel/runner.py
-- 2026-02-23

-- ============================================================
-- RULE: NO_SELECT_STAR
-- ============================================================
-- Files scanned: *.sql
-- Detection: sqlglot AST Star node in SELECT (primary)
--            Regex fallback: SELECT\s+\*\s+FROM (when sqlglot unavailable)
-- Jinja-aware: Strip {{ }} tokens before parsing

-- Example violation:
SELECT * FROM {{ ref('stg_orders') }}

-- Violation report:
-- {
--   "rule": "NO_SELECT_STAR",
--   "file": "models/marts/fct_orders.sql",
--   "line": 3,
--   "message": "SELECT * is forbidden. Explicitly list columns to prevent silent schema breakage."
-- }

-- Example passing:
SELECT order_id, customer_id, total FROM {{ ref('stg_orders') }}

-- ============================================================
-- RULE: MODEL_DESCRIPTION_REQUIRED
-- ============================================================
-- Files scanned: models/schema.yml  (dbt schema files)
-- Detection: PyYAML parse → models[].description is empty string or key absent

-- Example violation (schema.yml):
-- models:
--   - name: fct_orders
--     columns:               ← no 'description' key at model level
--       - name: order_id
--         description: PK

-- Violation report:
-- {
--   "rule": "MODEL_DESCRIPTION_REQUIRED",
--   "file": "models/schema.yml",
--   "line": 2,
--   "message": "Model 'fct_orders' has no description. Add a description: field."
-- }

-- Example passing (schema.yml):
-- models:
--   - name: fct_orders
--     description: "Daily order fact table. One row per order."

-- ============================================================
-- RULE: INCREMENTAL_NEEDS_UNIQUE_KEY
-- ============================================================
-- Files scanned: *.sql (dbt model files)
-- Detection: config(materialized='incremental') present AND unique_key absent

-- Example violation:
-- {{ config(materialized='incremental') }}   ← no unique_key
-- SELECT order_id, total FROM {{ ref('stg_orders') }}

-- Violation report:
-- {
--   "rule": "INCREMENTAL_NEEDS_UNIQUE_KEY",
--   "file": "models/marts/fct_orders.sql",
--   "line": 1,
--   "message": "Incremental model 'fct_orders' is missing unique_key. Add unique_key='<column>' to config()."
-- }

-- Example passing:
-- {{ config(materialized='incremental', unique_key='order_id') }}

-- ============================================================
-- RULE: NO_HARDCODED_CREDENTIALS
-- ============================================================
-- Files scanned: *.sql
-- Detection: regex on string literals for credential keywords

-- Patterns (case-insensitive):
--   (password|passwd|pwd)\s*=\s*'[^']{4,}'
--   (api_key|apikey|secret|token)\s*=\s*'[^']{8,}'

-- Example violation:
CREATE USER etl_user PASSWORD = 'supersecret123';

-- Violation report:
-- {
--   "rule": "NO_HARDCODED_CREDENTIALS",
--   "file": "migrations/003_create_etl_user.sql",
--   "line": 1,
--   "message": "Hardcoded credential detected (PASSWORD). Use environment variables or a secrets vault."
-- }

-- ============================================================
-- RULE: MIGRATION_NEEDS_ROLLBACK
-- ============================================================
-- Files scanned: *.sql files in migrations/ directory
-- Detection: File lacks any of: -- rollback, -- down, -- revert, -- undo marker

-- Example violation (no rollback section):
ALTER TABLE orders ADD COLUMN coupon_code VARCHAR(32);

-- Violation report:
-- {
--   "rule": "MIGRATION_NEEDS_ROLLBACK",
--   "file": "migrations/004_add_coupon_code.sql",
--   "line": 1,
--   "message": "Migration missing rollback section. Add '-- rollback' marker followed by the reverse operation."
-- }

-- Example passing:
ALTER TABLE orders ADD COLUMN coupon_code VARCHAR(32);

-- rollback
ALTER TABLE orders DROP COLUMN coupon_code;

-- ============================================================
-- CONSTITUTION.MD ACTIVATION SYNTAX
-- ============================================================
-- Rules are opt-in. To enable in .constitution.md:
--
-- ## SQL Standards
-- - NO_SELECT_STAR
-- - MODEL_DESCRIPTION_REQUIRED
-- - INCREMENTAL_NEEDS_UNIQUE_KEY
--
-- ## Security Standards
-- - NO_HARDCODED_CREDENTIALS
--
-- ## Migration Standards
-- - MIGRATION_NEEDS_ROLLBACK

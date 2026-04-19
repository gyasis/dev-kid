-- Contract: dbt Dependency Graph Interface
-- Module: cli/dbt_graph.py
-- Consumed by: orchestrator.py (wave planning), sentinel/cascade_analyzer.py
-- 2026-02-23

-- ============================================================
-- INPUT CONTRACT: manifest.json (primary source)
-- ============================================================
-- File: target/manifest.json  (dbt Core 1.5+)
-- Detection: file exists → use manifest; absent → use regex fallback

-- Key fields consumed:
--   manifest["nodes"][node_id]["name"]                    → model short name
--   manifest["nodes"][node_id]["config"]["materialized"]  → table|view|incremental|ephemeral
--   manifest["nodes"][node_id]["depends_on"]["nodes"]     → list of upstream node_ids
--   manifest["nodes"][node_id]["description"]             → model-level description
--   manifest["nodes"][node_id]["columns"][col]["description"] → column description
--   manifest["parent_map"][node_id]                       → list of upstream node_ids (precomputed)
--   manifest["child_map"][node_id]                        → list of downstream node_ids (precomputed)

-- ============================================================
-- INPUT CONTRACT: Regex Fallback (manifest.json absent)
-- ============================================================
-- Scans all models/*.sql files for Jinja ref/source/config calls

-- ref() pattern:
--   {{ ref('stg_orders') }}         → upstream: stg_orders
--   {{ ref('stg_orders', v=2) }}    → upstream: stg_orders

-- source() pattern:
--   {{ source('raw', 'orders') }}   → upstream: source__raw__orders

-- config() pattern (for materialization):
--   {{ config(materialized='incremental', unique_key='order_id') }}

-- Regex:
--   REF    = r"\{\{\s*ref\s*\(\s*['\"](\w+)['\"]\s*"
--   SOURCE = r"\{\{\s*source\s*\(\s*['\"](\w+)['\"],\s*['\"](\w+)['\"]\s*\)"
--   CONFIG = r"materialized\s*=\s*['\"](\w+)['\"]"
--   UKEY   = r"unique_key\s*=\s*['\"](\w+)['\"]"

-- ============================================================
-- OUTPUT CONTRACT: DBTGraph object
-- ============================================================
-- {
--   "nodes": {
--     "stg_orders": {
--       "name": "stg_orders",
--       "file_path": "models/staging/stg_orders.sql",
--       "materialization": "view",
--       "has_description": true,
--       "has_unique_key": false,
--       "upstream": [],
--       "downstream": ["fct_orders"]
--     },
--     "fct_orders": {
--       "name": "fct_orders",
--       "file_path": "models/marts/fct_orders.sql",
--       "materialization": "incremental",
--       "has_description": true,
--       "has_unique_key": true,
--       "upstream": ["stg_orders", "dim_customers"],
--       "downstream": ["rpt_revenue_daily"]
--     },
--     "dim_customers": {
--       "name": "dim_customers",
--       "file_path": "models/staging/dim_customers.sql",
--       "materialization": "table",
--       "has_description": false,
--       "has_unique_key": false,
--       "upstream": [],
--       "downstream": ["fct_orders"]
--     }
--   },
--   "topological_order": ["stg_orders", "dim_customers", "fct_orders", "rpt_revenue_daily"],
--   "cycles": []
-- }

-- ============================================================
-- WAVE ASSIGNMENT CONTRACT
-- ============================================================
-- Given tasks.md tasks referencing dbt model files, assign waves:
--
-- Input tasks:
--   T001: Implement stg_orders  → models/staging/stg_orders.sql
--   T002: Implement fct_orders  → models/marts/fct_orders.sql    (depends on stg_orders)
--   T003: Implement dim_customers → models/staging/dim_customers.sql
--
-- Expected wave assignment:
--   Wave 1 (PARALLEL_SWARM): T001 (stg_orders), T003 (dim_customers)
--   Wave 2 (SEQUENTIAL_MERGE): T002 (fct_orders — depends on both Wave 1 models)
--
-- Cycle detection example (would halt orchestration):
--   model_a refs model_b
--   model_b refs model_a
--   → ERROR: "Circular dependency detected: model_a → model_b → model_a"

-- ============================================================
-- CONSTITUTION RULES APPLIED FROM GRAPH
-- ============================================================

-- Rule: MODEL_DESCRIPTION_REQUIRED
-- Triggered when: nodes[model].has_description = false AND rule is enabled in .constitution.md
-- Example violation:
--   dim_customers has no description → block checkpoint

-- Rule: INCREMENTAL_NEEDS_UNIQUE_KEY
-- Triggered when: nodes[model].materialization = 'incremental'
--                 AND nodes[model].has_unique_key = false
-- Example violation:
--   fct_orders is incremental but missing unique_key → block checkpoint

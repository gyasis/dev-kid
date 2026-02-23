-- Contract: SQL Schema Diff Interface
-- Module: cli/sentinel/sql_schema_diff.py
-- Consumed by: wave_executor.py (pre/post wave hooks), constitution_parser.py
-- 2026-02-23

-- ============================================================
-- INPUT CONTRACT: Pre-Wave Snapshot Capture
-- ============================================================
-- Called at wave start, before agent executes tasks
-- Input:  wave_id (int), list of .sql file paths in the wave
-- Output: Snapshot written to .claude/schema_snapshots/wave_{N}_pre.json

-- Snapshot file schema:
-- {
--   "wave_id": 2,
--   "captured_at": "2026-02-23T10:00:00",
--   "files": {
--     "migrations/001_orders.sql": {
--       "orders": [
--         {"name": "order_id",    "type": "BIGINT",       "nullable": false, "pk": true},
--         {"name": "customer_id", "type": "BIGINT",       "nullable": false, "pk": false},
--         {"name": "total",       "type": "DECIMAL(10,2)","nullable": true,  "pk": false}
--       ]
--     }
--   }
-- }

-- ============================================================
-- OUTPUT CONTRACT: Schema Diff Report
-- ============================================================
-- Returned by compare_post_wave(wave_id, sql_files) -> SchemaDiffReport

-- SchemaDiffReport schema:
-- {
--   "wave_id": 2,
--   "has_breaking_changes": true,
--   "changes": [
--     {
--       "file_path": "migrations/001_orders.sql",
--       "table_name": "orders",
--       "change_type": "COLUMN_REMOVED",
--       "column_name": "discount_pct",
--       "old_value": "DECIMAL(5,2)",
--       "new_value": null,
--       "is_breaking": true,
--       "affected_models": ["fct_orders", "rpt_revenue_daily"]
--     },
--     {
--       "file_path": "migrations/001_orders.sql",
--       "table_name": "orders",
--       "change_type": "COLUMN_ADDED",
--       "column_name": "coupon_code",
--       "old_value": null,
--       "new_value": "VARCHAR(32)",
--       "is_breaking": false,
--       "affected_models": []
--     }
--   ]
-- }

-- ============================================================
-- BLOCKING RULES
-- ============================================================
-- Checkpoint is BLOCKED if any change has is_breaking = true
-- Non-breaking changes produce informational output only
-- Wave proceeds only after engineer acknowledges or resolves all blocking changes

-- ============================================================
-- EXAMPLE: DDL that triggers blocking diff
-- ============================================================

-- BEFORE (HEAD):
CREATE TABLE orders (
    order_id     BIGINT        NOT NULL,
    customer_id  BIGINT        NOT NULL,
    total        DECIMAL(10,2) NOT NULL,
    discount_pct DECIMAL(5,2)  NULL,
    PRIMARY KEY (order_id)
);

-- AFTER (wave output) — discount_pct REMOVED → BLOCKING:
CREATE TABLE orders (
    order_id     BIGINT        NOT NULL,
    customer_id  BIGINT        NOT NULL,
    total        DECIMAL(10,2) NOT NULL,
    coupon_code  VARCHAR(32)   NULL,       -- added → non-blocking
    PRIMARY KEY (order_id)
);

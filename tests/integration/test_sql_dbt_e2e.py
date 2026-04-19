"""End-to-end integration tests for SQL schema diff + dbt wave planning.

Tests run in an isolated git repo created in a temp directory so they
never touch the actual dev-kid repository state.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# Add cli/ to path for direct imports
sys.path.insert(0, str(Path(__file__).parents[2] / "cli"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_git(args: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )


def _setup_git_repo(tmp: str) -> None:
    """Initialise a minimal git repo for testing."""
    _run_git(["init", "-b", "main"], tmp)
    _run_git(["config", "user.email", "test@example.com"], tmp)
    _run_git(["config", "user.name", "Test"], tmp)


def _git_commit_all(tmp: str, message: str) -> None:
    _run_git(["add", "."], tmp)
    _run_git(["commit", "-m", message], tmp)


# ---------------------------------------------------------------------------
# E2E test
# ---------------------------------------------------------------------------

def test_sql_dbt_e2e():
    """Full pipeline: schema diff + dbt wave ordering + constitution enforcement."""
    start = time.time()

    with tempfile.TemporaryDirectory() as tmp:
        _setup_git_repo(tmp)

        # ── Step 1: create migration SQL with 2 columns and commit ──────────
        mig_dir = Path(tmp) / "migrations"
        mig_dir.mkdir()
        migration = mig_dir / "001_orders.sql"
        migration.write_text(
            "CREATE TABLE orders (\n"
            "    order_id  BIGINT NOT NULL,\n"
            "    discount  DECIMAL(5,2) NULL\n"
            ");\n",
            encoding="utf-8",
        )
        _git_commit_all(tmp, "feat: add orders migration")

        # ── Step 2: remove 'discount' column (breaking change) ───────────────
        migration.write_text(
            "CREATE TABLE orders (order_id BIGINT NOT NULL);\n",
            encoding="utf-8",
        )
        # Note: NOT committed yet — this is the "post-wave" state

        # Schema diff: capture pre-wave from HEAD, compare to current
        from sentinel.sql_schema_diff import SchemaSnapshot, SchemaDiff

        snap_dir = str(Path(tmp) / ".schema_snaps")
        rel_path = "migrations/001_orders.sql"

        # Switch cwd to the tmp repo so git show HEAD: works
        orig_cwd = os.getcwd()
        try:
            os.chdir(tmp)
            SchemaSnapshot.capture_pre_wave(1, [rel_path], snap_dir)
        finally:
            os.chdir(orig_cwd)

        report = SchemaDiff.compare_post_wave(
            1, [str(migration)], snap_dir
        )

        # (6) Breaking change detected
        assert report.has_breaking_changes is True, (
            f"Expected breaking change from COLUMN_REMOVED; got: {report.changes}"
        )
        removed = [c for c in report.changes if c.change_type == "COLUMN_REMOVED"]
        assert any(c.column_name == "discount" for c in removed), (
            f"Expected 'discount' in removed columns; got {removed}"
        )

        # ── Step 3 + 4: create dbt models and dbt_project.yml ────────────────
        models_dir = Path(tmp) / "models"
        models_dir.mkdir()

        (models_dir / "stg_orders.sql").write_text(
            "SELECT order_id FROM {{ source('raw', 'orders') }}\n",
            encoding="utf-8",
        )
        (models_dir / "dim_customers.sql").write_text(
            "SELECT customer_id FROM {{ source('raw', 'customers') }}\n",
            encoding="utf-8",
        )
        (models_dir / "fct_orders.sql").write_text(
            "SELECT o.order_id FROM {{ ref('stg_orders') }} o\n"
            "JOIN {{ ref('dim_customers') }} c ON o.customer_id = c.customer_id\n",
            encoding="utf-8",
        )
        (Path(tmp) / "dbt_project.yml").write_text(
            "name: 'test_project'\nversion: '1.0.0'\n",
            encoding="utf-8",
        )

        # ── Step 5: verify DBTGraph + wave assignment ────────────────────────
        from dbt_graph import DBTGraph, DBTTopologicalSort, CycleDetector

        graph = DBTGraph().load(tmp)
        assert "stg_orders" in graph.nodes, "stg_orders not found in graph"
        assert "fct_orders" in graph.nodes, "fct_orders not found in graph"

        # Cycle check
        cycle = CycleDetector.detect_cycle(graph)
        assert cycle is None, f"Unexpected cycle detected: {cycle}"

        # Wave assignment: stg/dim should be wave 1, fct wave 2
        all_models = list(graph.nodes.keys())
        waves = DBTTopologicalSort.assign_waves(all_models, graph)

        assert waves.get("stg_orders", 0) < waves.get("fct_orders", 99), (
            f"stg_orders wave {waves.get('stg_orders')} should be < "
            f"fct_orders wave {waves.get('fct_orders')}"
        )
        assert waves.get("dim_customers", 0) < waves.get("fct_orders", 99), (
            f"dim_customers wave {waves.get('dim_customers')} should be < "
            f"fct_orders wave {waves.get('fct_orders')}"
        )

        # ── Step 7: NO_SELECT_STAR constitution rule ─────────────────────────
        from sentinel.sql_constitution import SQLConstitutionScanner

        bad_model = models_dir / "bad_model.sql"
        bad_model.write_text("SELECT * FROM orders;\n", encoding="utf-8")

        scanner = SQLConstitutionScanner()
        violations = scanner.scan_file(str(bad_model), ["NO_SELECT_STAR"])
        assert len(violations) > 0, "Expected NO_SELECT_STAR violation"
        assert violations[0].rule == "NO_SELECT_STAR"

        # Clean model should not trigger violation
        good_model = models_dir / "good_model.sql"
        good_model.write_text("SELECT id, name FROM orders;\n", encoding="utf-8")
        good_violations = scanner.scan_file(str(good_model), ["NO_SELECT_STAR"])
        assert len(good_violations) == 0, f"Unexpected violations: {good_violations}"

        # ── Step 8: runtime check ────────────────────────────────────────────
        elapsed = time.time() - start
        assert elapsed < 10.0, f"E2E test took {elapsed:.1f}s (limit: 10s)"

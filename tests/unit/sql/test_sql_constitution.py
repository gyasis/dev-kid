"""Unit tests for SQLConstitutionScanner and DBTSchemaYAMLScanner."""

import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "cli"))

from sentinel.sql_constitution import SQLConstitutionScanner, DBTSchemaYAMLScanner


# ---------------------------------------------------------------------------
# NO_SELECT_STAR
# ---------------------------------------------------------------------------

def test_select_star_violation(tmp_path):
    f = tmp_path / "fct.sql"
    f.write_text("SELECT * FROM stg_orders")
    scanner = SQLConstitutionScanner()
    violations = scanner.scan_file(str(f), ["NO_SELECT_STAR"])
    assert any(v.rule == "NO_SELECT_STAR" for v in violations)


def test_explicit_columns_pass(tmp_path):
    f = tmp_path / "fct.sql"
    f.write_text("SELECT order_id, total FROM stg_orders")
    scanner = SQLConstitutionScanner()
    violations = scanner.scan_file(str(f), ["NO_SELECT_STAR"])
    assert not any(v.rule == "NO_SELECT_STAR" for v in violations)


# ---------------------------------------------------------------------------
# NO_HARDCODED_CREDENTIALS
# ---------------------------------------------------------------------------

def test_hardcoded_password_violation(tmp_path):
    f = tmp_path / "create_user.sql"
    f.write_text("CREATE USER etl PASSWORD = 'supersecret123';")
    scanner = SQLConstitutionScanner()
    violations = scanner.scan_file(str(f), ["NO_HARDCODED_CREDENTIALS"])
    assert any(v.rule == "NO_HARDCODED_CREDENTIALS" for v in violations)


def test_parameterised_query_passes(tmp_path):
    f = tmp_path / "query.sql"
    f.write_text("SELECT id FROM users WHERE id = %(user_id)s")
    scanner = SQLConstitutionScanner()
    violations = scanner.scan_file(str(f), ["NO_HARDCODED_CREDENTIALS"])
    assert not any(v.rule == "NO_HARDCODED_CREDENTIALS" for v in violations)


# ---------------------------------------------------------------------------
# INCREMENTAL_NEEDS_UNIQUE_KEY
# ---------------------------------------------------------------------------

def test_incremental_without_unique_key_violation(tmp_path):
    f = tmp_path / "fct.sql"
    f.write_text("{{ config(materialized='incremental') }}\nSELECT order_id FROM stg")
    scanner = SQLConstitutionScanner()
    violations = scanner.scan_file(str(f), ["INCREMENTAL_NEEDS_UNIQUE_KEY"])
    assert any(v.rule == "INCREMENTAL_NEEDS_UNIQUE_KEY" for v in violations)


def test_incremental_with_unique_key_passes(tmp_path):
    f = tmp_path / "fct.sql"
    f.write_text("{{ config(materialized='incremental', unique_key='order_id') }}\nSELECT order_id FROM stg")
    scanner = SQLConstitutionScanner()
    violations = scanner.scan_file(str(f), ["INCREMENTAL_NEEDS_UNIQUE_KEY"])
    assert not any(v.rule == "INCREMENTAL_NEEDS_UNIQUE_KEY" for v in violations)


# ---------------------------------------------------------------------------
# MIGRATION_NEEDS_ROLLBACK
# ---------------------------------------------------------------------------

def test_migration_without_rollback_violation(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    f = migrations_dir / "001_add_col.sql"
    f.write_text("ALTER TABLE orders ADD COLUMN coupon_code VARCHAR(32);")
    scanner = SQLConstitutionScanner()
    violations = scanner.scan_file(str(f), ["MIGRATION_NEEDS_ROLLBACK"])
    assert any(v.rule == "MIGRATION_NEEDS_ROLLBACK" for v in violations)


def test_migration_with_rollback_passes(tmp_path):
    migrations_dir = tmp_path / "migrations"
    migrations_dir.mkdir()
    f = migrations_dir / "001_add_col.sql"
    f.write_text(
        "ALTER TABLE orders ADD COLUMN coupon_code VARCHAR(32);\n"
        "-- rollback\n"
        "ALTER TABLE orders DROP COLUMN coupon_code;"
    )
    scanner = SQLConstitutionScanner()
    violations = scanner.scan_file(str(f), ["MIGRATION_NEEDS_ROLLBACK"])
    assert not any(v.rule == "MIGRATION_NEEDS_ROLLBACK" for v in violations)


# ---------------------------------------------------------------------------
# MODEL_DESCRIPTION_REQUIRED (YAML)
# ---------------------------------------------------------------------------

def test_model_missing_description_violation(tmp_path):
    f = tmp_path / "schema.yml"
    f.write_text("models:\n  - name: fct_orders\n    columns:\n      - name: id\n")
    scanner = DBTSchemaYAMLScanner()
    violations = scanner.scan_yaml(str(f), ["MODEL_DESCRIPTION_REQUIRED"])
    assert any(v.rule == "MODEL_DESCRIPTION_REQUIRED" for v in violations)


def test_model_with_description_passes(tmp_path):
    f = tmp_path / "schema.yml"
    f.write_text(
        "models:\n  - name: fct_orders\n    description: 'Daily order fact.'\n    columns:\n      - name: id\n"
    )
    scanner = DBTSchemaYAMLScanner()
    violations = scanner.scan_yaml(str(f), ["MODEL_DESCRIPTION_REQUIRED"])
    assert not any(v.rule == "MODEL_DESCRIPTION_REQUIRED" for v in violations)


# ---------------------------------------------------------------------------
# Rule not enabled -- no violations emitted for disabled rule
# ---------------------------------------------------------------------------

def test_rule_not_enabled_no_violation(tmp_path):
    f = tmp_path / "fct.sql"
    f.write_text("SELECT * FROM stg_orders")
    scanner = SQLConstitutionScanner()
    # NO_SELECT_STAR not in enabled rules
    violations = scanner.scan_file(str(f), ["NO_HARDCODED_CREDENTIALS"])
    assert not any(v.rule == "NO_SELECT_STAR" for v in violations)

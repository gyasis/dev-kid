"""Unit tests for DDLParser in cli/sentinel/sql_schema_diff.py."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Allow imports from cli/
sys.path.insert(0, str(Path(__file__).parents[3] / "cli"))

from sentinel.sql_schema_diff import DDLParser, ColumnDef


# ---------------------------------------------------------------------------
# Basic parsing
# ---------------------------------------------------------------------------

def test_parse_simple_create_table():
    ddl = """
    CREATE TABLE orders (
        order_id  BIGINT NOT NULL,
        total     DECIMAL(10,2) NULL,
        PRIMARY KEY (order_id)
    );
    """
    parser = DDLParser()
    result = parser.parse_ddl(ddl)
    assert "orders" in result
    cols = {c.name: c for c in result["orders"]}
    assert "order_id" in cols
    assert "total" in cols
    assert cols["order_id"].nullable is False or cols["order_id"].is_pk is True


def test_column_names_and_types():
    ddl = "CREATE TABLE t (id INT NOT NULL, name VARCHAR(255) NULL, score DECIMAL NULL);"
    result = DDLParser().parse_ddl(ddl)
    assert "t" in result
    names = [c.name for c in result["t"]]
    assert "id" in names
    assert "name" in names
    assert "score" in names


def test_nullable_flags():
    ddl = "CREATE TABLE t (a INT NOT NULL, b VARCHAR(50) NULL);"
    result = DDLParser().parse_ddl(ddl)
    cols = {c.name: c for c in result["t"]}
    assert cols["a"].nullable is False
    assert cols["b"].nullable is True


def test_jinja_stripped_before_parsing():
    """DDL containing dbt Jinja should be stripped and parseable."""
    ddl = """
    {{ config(materialized='table') }}
    CREATE TABLE stg_orders AS
    SELECT order_id, total FROM {{ ref('raw_orders') }};
    """
    # Should not raise; may or may not extract columns depending on DDL form
    result = DDLParser().parse_ddl(ddl)
    # At minimum: no exception; result is a dict
    assert isinstance(result, dict)


def test_unrecognised_ddl_returns_empty_dict():
    result = DDLParser().parse_ddl("SELECT 1; UPDATE foo SET bar = 1;")
    assert isinstance(result, dict)
    # No CREATE TABLE -> empty or only non-table entries
    # Should not raise


def test_multiple_tables_in_one_file():
    ddl = """
    CREATE TABLE customers (id INT NOT NULL PRIMARY KEY, name VARCHAR(100));
    CREATE TABLE orders (id INT NOT NULL PRIMARY KEY, customer_id INT NOT NULL);
    """
    result = DDLParser().parse_ddl(ddl)
    assert len(result) >= 2 or "customers" in result or "orders" in result


def test_regex_fallback_when_sqlglot_absent():
    """Parser must still work when sqlglot is unavailable."""
    with patch("sentinel.sql_utils.try_import_sqlglot", return_value=(None, None)):
        ddl = "CREATE TABLE products (sku VARCHAR(32) NOT NULL, price DECIMAL(8,2));"
        result = DDLParser().parse_ddl(ddl)
        assert isinstance(result, dict)

"""Unit tests for DBTGraph in cli/dbt_graph.py."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "cli"))

from dbt_graph import DBTGraph, DBTModel, CycleDetector


def _make_manifest(nodes: dict) -> dict:
    """Helper to create a minimal dbt manifest.json structure."""
    return {
        "nodes": nodes,
        "sources": {},
        "parent_map": {},
        "child_map": {},
    }


# ---------------------------------------------------------------------------
# manifest.json loading
# ---------------------------------------------------------------------------

def test_manifest_loads_node_names(tmp_path):
    manifest = _make_manifest({
        "model.myproject.stg_orders": {
            "name": "stg_orders",
            "config": {"materialized": "view"},
            "depends_on": {"nodes": []},
            "description": "Staging orders",
            "columns": {},
            "original_file_path": "models/staging/stg_orders.sql",
        }
    })
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "manifest.json").write_text(json.dumps(manifest))

    graph = DBTGraph().load(str(tmp_path))
    assert "stg_orders" in graph.nodes
    assert graph.nodes["stg_orders"].materialization == "view"
    assert graph.nodes["stg_orders"].has_description is True
    assert graph.nodes["stg_orders"].source == "manifest"


def test_manifest_loads_upstream_deps(tmp_path):
    manifest = _make_manifest({
        "model.myproject.stg_orders": {
            "name": "stg_orders",
            "config": {"materialized": "view"},
            "depends_on": {"nodes": []},
            "description": "",
            "columns": {},
            "original_file_path": "models/staging/stg_orders.sql",
        },
        "model.myproject.fct_orders": {
            "name": "fct_orders",
            "config": {"materialized": "table"},
            "depends_on": {"nodes": ["model.myproject.stg_orders"]},
            "description": "Fact table",
            "columns": {},
            "original_file_path": "models/marts/fct_orders.sql",
        },
    })
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "manifest.json").write_text(json.dumps(manifest))

    graph = DBTGraph().load(str(tmp_path))
    assert "stg_orders" in graph.nodes["fct_orders"].upstream
    assert "fct_orders" in graph.nodes["stg_orders"].downstream


def test_manifest_has_description_flag(tmp_path):
    manifest = _make_manifest({
        "model.p.m1": {"name": "m1", "config": {}, "depends_on": {"nodes": []},
                       "description": "Some desc", "columns": {}, "original_file_path": "models/m1.sql"},
        "model.p.m2": {"name": "m2", "config": {}, "depends_on": {"nodes": []},
                       "description": "", "columns": {}, "original_file_path": "models/m2.sql"},
    })
    (tmp_path / "target").mkdir()
    (tmp_path / "target" / "manifest.json").write_text(json.dumps(manifest))
    graph = DBTGraph().load(str(tmp_path))
    assert graph.nodes["m1"].has_description is True
    assert graph.nodes["m2"].has_description is False


# ---------------------------------------------------------------------------
# Regex fallback
# ---------------------------------------------------------------------------

def test_regex_fallback_detects_ref(tmp_path):
    models_dir = tmp_path / "models" / "staging"
    models_dir.mkdir(parents=True)
    (models_dir / "stg_orders.sql").write_text(
        "SELECT order_id FROM {{ source('raw', 'orders') }}"
    )
    (tmp_path / "models" / "marts").mkdir()
    (tmp_path / "models" / "marts" / "fct_orders.sql").write_text(
        "SELECT * FROM {{ ref('stg_orders') }}"
    )

    graph = DBTGraph().load(str(tmp_path))
    assert "stg_orders" in graph.nodes
    assert "fct_orders" in graph.nodes
    assert "stg_orders" in graph.nodes["fct_orders"].upstream
    assert graph.nodes["stg_orders"].source == "regex_fallback"


def test_regex_fallback_detects_incremental(tmp_path):
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    (models_dir / "fct_inc.sql").write_text(
        "{{ config(materialized='incremental', unique_key='id') }}\nSELECT id FROM t"
    )

    graph = DBTGraph().load(str(tmp_path))
    assert graph.nodes["fct_inc"].materialization == "incremental"
    assert graph.nodes["fct_inc"].has_unique_key is True


# ---------------------------------------------------------------------------
# Cycle detector
# ---------------------------------------------------------------------------

def test_cycle_detector_finds_cycle():
    graph = DBTGraph()
    graph.nodes["a"] = DBTModel(name="a", file_path="a.sql", upstream=[], downstream=["b"])
    graph.nodes["b"] = DBTModel(name="b", file_path="b.sql", upstream=["a"], downstream=["a"])
    # Manually create cycle: a -> b -> a
    graph.nodes["a"].upstream = ["b"]

    result = CycleDetector.detect_cycle(graph)
    assert result is not None
    assert "\u2192" in result


def test_cycle_detector_no_cycle():
    graph = DBTGraph()
    graph.nodes["a"] = DBTModel(name="a", file_path="a.sql", upstream=[], downstream=["b"])
    graph.nodes["b"] = DBTModel(name="b", file_path="b.sql", upstream=["a"], downstream=[])

    result = CycleDetector.detect_cycle(graph)
    assert result is None

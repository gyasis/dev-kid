"""Unit tests for DBTTopologicalSort wave planning in cli/dbt_graph.py."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[3] / "cli"))

from dbt_graph import DBTGraph, DBTModel, DBTTopologicalSort, CycleDetector


def _make_graph(nodes_spec: dict) -> DBTGraph:
    """Create a DBTGraph from a simple {name: [upstream_names]} spec."""
    graph = DBTGraph()
    for name, upstream_list in nodes_spec.items():
        graph.nodes[name] = DBTModel(
            name=name,
            file_path=f"models/{name}.sql",
            upstream=upstream_list,
        )
    # Populate downstream by inverting upstream edges
    graph._populate_downstream()
    return graph


# ---------------------------------------------------------------------------
# Wave assignment
# ---------------------------------------------------------------------------

def test_independent_models_get_wave_1():
    graph = _make_graph({"stg_orders": [], "dim_customers": []})
    waves = DBTTopologicalSort.assign_waves(["stg_orders", "dim_customers"], graph)
    assert waves["stg_orders"] == 1
    assert waves["dim_customers"] == 1


def test_dependent_model_gets_wave_2():
    graph = _make_graph({
        "stg_orders": [],
        "dim_customers": [],
        "fct_orders": ["stg_orders", "dim_customers"],
    })
    waves = DBTTopologicalSort.assign_waves(
        ["stg_orders", "dim_customers", "fct_orders"], graph
    )
    assert waves["stg_orders"] == 1
    assert waves["dim_customers"] == 1
    assert waves["fct_orders"] == 2


def test_three_level_chain():
    graph = _make_graph({
        "raw": [],
        "stg": ["raw"],
        "mart": ["stg"],
    })
    waves = DBTTopologicalSort.assign_waves(["raw", "stg", "mart"], graph)
    assert waves["raw"] < waves["stg"] < waves["mart"]


def test_model_not_in_graph_gets_wave_1():
    graph = _make_graph({"known": []})
    waves = DBTTopologicalSort.assign_waves(["known", "unknown_model"], graph)
    assert waves["unknown_model"] == 1


def test_empty_task_list():
    graph = _make_graph({"a": [], "b": ["a"]})
    waves = DBTTopologicalSort.assign_waves([], graph)
    assert waves == {}


# ---------------------------------------------------------------------------
# Cycle detection
# ---------------------------------------------------------------------------

def test_cycle_detection_returns_path():
    graph = _make_graph({"a": ["b"], "b": ["a"]})
    result = CycleDetector.detect_cycle(graph)
    assert result is not None
    assert "a" in result
    assert "b" in result


def test_no_cycle_returns_none():
    graph = _make_graph({"a": [], "b": ["a"], "c": ["b"]})
    assert CycleDetector.detect_cycle(graph) is None

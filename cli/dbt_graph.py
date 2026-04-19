"""
dbt Dependency Graph

Builds a dbt model dependency graph from target/manifest.json (primary source)
or by scanning models/**/*.sql for ref()/source()/config() Jinja calls (fallback).

Used by orchestrator.py to produce dbt-aware wave ordering: upstream models always
execute in an earlier wave than their downstream dependents.

Components:
  DBTModel           — a single dbt model node (name, file, materialization, deps)
  DBTGraph           — container for all nodes; loaded from manifest or regex scan
  DBTTopologicalSort — assigns wave numbers via Kahn's algorithm
  CycleDetector      — DFS cycle detection; returns cycle path string on error
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Regex patterns (used when manifest.json is absent)
# ---------------------------------------------------------------------------

_REF_PATTERN = re.compile(r"\{\{\s*ref\s*\(\s*['\"](\w+)['\"]\s*\)\s*\}\}")
_SOURCE_PATTERN = re.compile(
    r"\{\{\s*source\s*\(\s*['\"](\w+)['\"],\s*['\"](\w+)['\"]\s*\)\s*\}\}"
)
_CONFIG_PATTERN = re.compile(
    r"\{\{\s*config\s*\(.*?materialized\s*=\s*['\"](\w+)['\"].*?\)\s*\}\}",
    re.DOTALL,
)
_UNIQUE_KEY_PATTERN = re.compile(r"unique_key\s*=\s*['\"](\w+)['\"]")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class DBTModel:
    """A single dbt model node."""
    name: str
    file_path: str
    materialization: str = "view"       # table | view | incremental | ephemeral
    has_description: bool = False
    has_unique_key: bool = False
    upstream: list[str] = field(default_factory=list)      # model names only
    downstream: list[str] = field(default_factory=list)
    source: str = "manifest"            # "manifest" | "regex_fallback"


class DBTGraph:
    """Container for all dbt model nodes and their dependency edges."""

    def __init__(self) -> None:
        self.nodes: dict[str, DBTModel] = {}

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def load(self, project_root: str = ".") -> "DBTGraph":
        """Load the dependency graph for the dbt project at project_root.

        Tries target/manifest.json first; falls back to scanning models/**/*.sql.

        Args:
            project_root: Path to the dbt project root directory.

        Returns:
            self (for chaining).
        """
        root = Path(project_root)
        manifest_path = root / "target" / "manifest.json"

        if manifest_path.exists():
            self._load_from_manifest(manifest_path)
        else:
            self._load_from_regex(root)

        self._populate_downstream()
        return self

    def _load_from_manifest(self, manifest_path: Path) -> None:
        """Parse target/manifest.json (dbt Core 1.5+ schema)."""
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return

        nodes_data: dict = data.get("nodes", {})

        for node_id, node in nodes_data.items():
            if not node_id.startswith("model."):
                continue

            name: str = node.get("name", "")
            if not name:
                continue

            config: dict = node.get("config", {})
            materialization: str = config.get("materialized", "view")
            description: str = node.get("description", "")
            has_description: bool = bool(description and description.strip())

            # unique_key can be in config or at top level
            has_unique_key: bool = bool(
                config.get("unique_key") or node.get("unique_key")
            )

            # Upstream model names (filter to model.* refs, strip project prefix)
            depends_on: list[str] = node.get("depends_on", {}).get("nodes", [])
            upstream_names: list[str] = []
            for dep_id in depends_on:
                if dep_id.startswith("model."):
                    parts = dep_id.split(".")
                    if len(parts) >= 3:
                        upstream_names.append(parts[-1])

            file_path: str = node.get("original_file_path", f"models/{name}.sql")

            self.nodes[name] = DBTModel(
                name=name,
                file_path=file_path,
                materialization=materialization,
                has_description=has_description,
                has_unique_key=has_unique_key,
                upstream=upstream_names,
                source="manifest",
            )

    def _load_from_regex(self, project_root: Path) -> None:
        """Scan models/**/*.sql for Jinja ref/source/config calls."""
        models_dir = project_root / "models"
        if not models_dir.exists():
            return

        for sql_file in sorted(models_dir.rglob("*.sql")):
            name = sql_file.stem
            try:
                content = sql_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            # Upstream refs
            upstream_names: list[str] = list(dict.fromkeys(
                m.group(1) for m in _REF_PATTERN.finditer(content)
            ))

            # Materialization
            config_m = _CONFIG_PATTERN.search(content)
            materialization = config_m.group(1) if config_m else "view"

            # unique_key
            has_unique_key = bool(_UNIQUE_KEY_PATTERN.search(content))

            rel_path = str(sql_file.relative_to(project_root))

            self.nodes[name] = DBTModel(
                name=name,
                file_path=rel_path,
                materialization=materialization,
                has_description=False,   # can't know without schema.yml
                has_unique_key=has_unique_key,
                upstream=upstream_names,
                source="regex_fallback",
            )

    def _populate_downstream(self) -> None:
        """Populate downstream lists by inverting upstream edges."""
        # Clear existing downstream lists
        for node in self.nodes.values():
            node.downstream = []

        for name, node in self.nodes.items():
            for upstream_name in node.upstream:
                if upstream_name in self.nodes:
                    self.nodes[upstream_name].downstream.append(name)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def get_file_to_model_map(self) -> dict[str, str]:
        """Return a mapping of file_path → model_name."""
        return {node.file_path: node.name for node in self.nodes.values()}


# ---------------------------------------------------------------------------
# Topological sort (wave assignment)
# ---------------------------------------------------------------------------

class DBTTopologicalSort:
    """Assigns wave numbers to tasks based on the dbt dependency graph."""

    @staticmethod
    def assign_waves(
        task_model_names: list[str],
        graph: DBTGraph,
    ) -> dict[str, int]:
        """Assign wave numbers so that upstream models always precede downstream ones.

        Only models present in task_model_names are considered. Models not in the
        graph are assigned wave 1.

        Uses a level-based BFS (similar to Kahn's algorithm).

        Args:
            task_model_names: Names of dbt models corresponding to tasks.md tasks.
            graph: Loaded DBTGraph.

        Returns:
            Dict mapping model_name → wave_number (1-based).
        """
        in_scope: set[str] = set(task_model_names)

        # Build in-scope sub-graph adjacency and in-degree
        in_degree: dict[str, int] = {name: 0 for name in in_scope}
        adjacency: dict[str, list[str]] = {name: [] for name in in_scope}

        for name in in_scope:
            node = graph.nodes.get(name)
            if node is None:
                continue
            for up in node.upstream:
                if up in in_scope:
                    adjacency[up].append(name)
                    in_degree[name] = in_degree.get(name, 0) + 1

        wave_assignment: dict[str, int] = {}
        current_wave = 1
        queue = [n for n in in_scope if in_degree[n] == 0]

        while queue:
            for name in queue:
                wave_assignment[name] = current_wave
            next_queue: list[str] = []
            for name in queue:
                for downstream in adjacency.get(name, []):
                    in_degree[downstream] -= 1
                    if in_degree[downstream] == 0:
                        next_queue.append(downstream)
            queue = next_queue
            current_wave += 1

        # Assign wave 1 to any model not reached (disconnected from graph)
        for name in in_scope:
            wave_assignment.setdefault(name, 1)

        return wave_assignment


# ---------------------------------------------------------------------------
# Cycle detector
# ---------------------------------------------------------------------------

class CycleDetector:
    """Detects cycles in a dbt dependency graph using DFS."""

    WHITE = 0  # unvisited
    GRAY = 1   # in current DFS path
    BLACK = 2  # fully processed

    @classmethod
    def detect_cycle(cls, graph: DBTGraph) -> Optional[str]:
        """Run DFS cycle detection across the full graph.

        Args:
            graph: Loaded DBTGraph.

        Returns:
            A human-readable cycle path string (e.g. "a → b → c → a") if a
            cycle exists, or None if the graph is acyclic.
        """
        color: dict[str, int] = {name: cls.WHITE for name in graph.nodes}
        parent: dict[str, Optional[str]] = {name: None for name in graph.nodes}

        def dfs(node: str) -> Optional[str]:
            color[node] = cls.GRAY
            for downstream in graph.nodes[node].downstream:
                if downstream not in color:
                    continue  # node not in graph — skip
                if color[downstream] == cls.GRAY:
                    # Cycle found — reconstruct path
                    cycle_path: list[str] = [downstream, node]
                    current: str = node
                    while True:
                        p = parent.get(current)
                        if p is None or p == downstream:
                            break
                        current = p
                        cycle_path.append(current)
                    cycle_path.append(downstream)
                    cycle_path.reverse()
                    return " → ".join(cycle_path)
                if color[downstream] == cls.WHITE:
                    parent[downstream] = node
                    cycle = dfs(downstream)
                    if cycle:
                        return cycle
            color[node] = cls.BLACK
            return None

        for node in list(graph.nodes):
            if color[node] == cls.WHITE:
                cycle = dfs(node)
                if cycle:
                    return cycle

        return None

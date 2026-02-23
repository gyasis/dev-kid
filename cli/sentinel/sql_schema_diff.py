"""
Integration Sentinel — SQL Schema Diff

Detects breaking schema changes in SQL DDL files between wave start (pre-state
captured from git HEAD) and wave end (current file content).

Components:
  DDLParser         — parse CREATE TABLE DDL → column signatures (sqlglot + regex fallback)
  SchemaSnapshot    — capture pre-wave state; persist to .claude/schema_snapshots/
  SchemaDiff        — compare pre/post snapshots; classify changes as breaking/non-breaking
  AffectedModelFinder — given a removed column, find downstream dbt models that reference it
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .sql_utils import strip_jinja, try_import_sqlglot


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ColumnDef:
    """Represents a single column in a table schema."""
    name: str
    data_type: str
    nullable: bool = True
    is_pk: bool = False


@dataclass
class SchemaChange:
    """Represents a single schema change between pre- and post-wave states."""
    file_path: str
    table_name: str
    change_type: str          # COLUMN_REMOVED | COLUMN_ADDED | TYPE_CHANGED | TABLE_DROPPED | TABLE_ADDED
    column_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    is_breaking: bool = False
    affected_models: list[str] = field(default_factory=list)


@dataclass
class SchemaDiffReport:
    """Result of comparing pre- and post-wave SQL schema snapshots."""
    wave_id: int
    has_breaking_changes: bool
    changes: list[SchemaChange] = field(default_factory=list)

    def format_blocking_message(self) -> str:
        """Format a human-readable message for blocking checkpoint output."""
        lines = [f"⚠️  Schema Breaking Changes Detected in Wave {self.wave_id}:"]
        for c in self.changes:
            if c.is_breaking:
                affected = (
                    f"\n   Affected downstream models: {', '.join(c.affected_models)}"
                    if c.affected_models else ""
                )
                lines.append(
                    f"   {c.file_path}: {c.table_name}.{c.column_name} {c.change_type}"
                    + affected
                )
        lines.append(
            f"\n🚫 Checkpoint BLOCKED: {sum(1 for c in self.changes if c.is_breaking)} "
            "breaking schema change(s)\n"
            "   Review changes and mark tasks [x] only after resolving downstream impact."
        )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# DDL Parser
# ---------------------------------------------------------------------------

# Regex fallback for CREATE TABLE column extraction
_COL_REGEX = re.compile(
    r"""
    ^\s*
    (\w+)                           # column name
    \s+
    ([\w]+(?:\s*\(\s*[\d,\s]+\))?)  # data type (optionally with precision)
    (?:\s+(NOT\s+NULL|NULL))?       # nullable
    (?:\s+.*)?                      # other constraints
    \s*,?\s*$
    """,
    re.VERBOSE | re.IGNORECASE,
)

_TABLE_NAME_REGEX = re.compile(
    # Captures the fully-qualified name (e.g. mydb.myschema.orders or just orders)
    r"CREATE\s+(?:TABLE|VIEW)\s+(?:IF\s+NOT\s+EXISTS\s+)?((?:\w+\.)*\w+)",
    re.IGNORECASE,
)

_PRIMARY_KEY_REGEX = re.compile(r"\bPRIMARY\s+KEY\b", re.IGNORECASE)


def _is_narrowing_type_change(old_type: str, new_type: str) -> bool:
    """Return True if changing from old_type to new_type is a narrowing (breaking) change."""
    narrowing_pairs = [
        ("bigint", "int"), ("bigint", "smallint"), ("bigint", "tinyint"),
        ("int", "smallint"), ("int", "tinyint"),
        ("decimal", "int"), ("numeric", "int"),
        ("double", "float"), ("double precision", "float"),
        ("text", "varchar"), ("text", "char"),
    ]
    old_norm = old_type.lower().split("(")[0].strip()
    new_norm = new_type.lower().split("(")[0].strip()

    # Check if precision is shrinking for same base type (e.g. VARCHAR(100) → VARCHAR(50))
    if old_norm == new_norm and "(" in old_type and "(" in new_type:
        try:
            old_prec = int(re.search(r"\((\d+)", old_type).group(1))  # type: ignore
            new_prec = int(re.search(r"\((\d+)", new_type).group(1))  # type: ignore
            return new_prec < old_prec
        except (AttributeError, ValueError):
            pass

    return (old_norm, new_norm) in narrowing_pairs


class DDLParser:
    """Parse CREATE TABLE / CREATE VIEW DDL into column signatures.

    Uses sqlglot AST when available; falls back to regex for basic DDL.
    Strips Jinja tokens before parsing (for dbt model files).
    """

    def parse_ddl(self, sql: str) -> dict[str, list[ColumnDef]]:
        """Parse DDL SQL and return a dict of table_name → [ColumnDef, ...].

        Args:
            sql: SQL string (may contain Jinja tokens which will be stripped).

        Returns:
            Dict mapping table name to list of ColumnDef objects.
            Returns empty dict on parse failure rather than raising.
        """
        cleaned = strip_jinja(sql)
        sqlglot_mod, exp = try_import_sqlglot()

        if sqlglot_mod is not None:
            return self._parse_with_sqlglot(cleaned, sqlglot_mod, exp)
        return self._parse_with_regex(cleaned)

    @staticmethod
    def _parse_with_sqlglot(sql: str, sqlglot_mod: object, exp: object) -> dict[str, list[ColumnDef]]:
        """Parse using sqlglot AST."""
        result: dict[str, list[ColumnDef]] = {}
        try:
            statements = sqlglot_mod.parse(sql)  # type: ignore[attr-defined]
            for stmt in statements:
                if stmt is None:
                    continue
                # Find CREATE TABLE nodes
                create_nodes = list(stmt.find_all(exp.Create))  # type: ignore[attr-defined]
                for create in create_nodes:
                    table_node = create.find(exp.Table)  # type: ignore[attr-defined]
                    if table_node is None:
                        continue
                    # Build fully-qualified name (catalog.schema.table) preserving all parts
                    _parts = [
                        p for p in [
                            getattr(table_node, "catalog", None),
                            getattr(table_node, "db", None),
                            table_node.name,
                        ] if p
                    ]
                    table_name = ".".join(_parts)
                    if not table_name:
                        continue
                    cols: list[ColumnDef] = []
                    for col_def in create.find_all(exp.ColumnDef):  # type: ignore[attr-defined]
                        name = col_def.name
                        type_node = col_def.args.get("kind")
                        dtype = str(type_node) if type_node else "UNKNOWN"
                        # Detect NOT NULL constraint
                        not_null = any(
                            isinstance(c, exp.NotNullColumnConstraint)  # type: ignore[attr-defined]
                            for c in col_def.find_all(exp.ColumnConstraint)  # type: ignore[attr-defined]
                        )
                        # Detect PRIMARY KEY constraint
                        is_pk = any(
                            isinstance(c, exp.PrimaryKeyColumnConstraint)  # type: ignore[attr-defined]
                            for c in col_def.find_all(exp.ColumnConstraint)  # type: ignore[attr-defined]
                        )
                        cols.append(ColumnDef(
                            name=name,
                            data_type=dtype,
                            nullable=not not_null,
                            is_pk=is_pk,
                        ))
                    if cols:
                        result[table_name] = cols
        except Exception:
            pass
        return result

    @staticmethod
    def _parse_with_regex(sql: str) -> dict[str, list[ColumnDef]]:
        """Fallback regex parser for basic CREATE TABLE DDL."""
        result: dict[str, list[ColumnDef]] = {}

        # Split on CREATE TABLE / CREATE VIEW boundaries
        blocks = re.split(r"(?=CREATE\s+(?:TABLE|VIEW)\b)", sql, flags=re.IGNORECASE)

        for block in blocks:
            if not block.strip():
                continue
            m = _TABLE_NAME_REGEX.search(block)
            if not m:
                continue
            table_name = m.group(1)

            # Extract the parenthesised column list
            paren_match = re.search(r"\((.+)\)", block, re.DOTALL)
            if not paren_match:
                continue

            body = paren_match.group(1)
            # Find PRIMARY KEY column list if table-level
            pk_cols: set[str] = set()
            pk_table = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", body, re.IGNORECASE)
            if pk_table:
                pk_cols = {c.strip().strip('"\'`') for c in pk_table.group(1).split(",")}

            cols: list[ColumnDef] = []
            # Split on commas that are NOT inside parentheses (e.g. DECIMAL(10,2))
            _parts: list[str] = []
            _depth = 0
            _cur: list[str] = []
            for _ch in body:
                if _ch == '(':
                    _depth += 1
                    _cur.append(_ch)
                elif _ch == ')':
                    _depth -= 1
                    _cur.append(_ch)
                elif _ch == ',' and _depth == 0:
                    _parts.append(''.join(_cur))
                    _cur = []
                else:
                    _cur.append(_ch)
            if _cur:
                _parts.append(''.join(_cur))
            for raw_line in _parts:
                raw_line = raw_line.strip()
                # Skip constraint lines
                if re.match(r"(?:PRIMARY\s+KEY|FOREIGN\s+KEY|UNIQUE|INDEX|KEY|CONSTRAINT)\b",
                            raw_line, re.IGNORECASE):
                    continue
                m2 = _COL_REGEX.match(raw_line)
                if not m2:
                    continue
                col_name = m2.group(1)
                dtype = m2.group(2).strip()
                nullable_str = (m2.group(3) or "").upper()
                nullable = "NOT NULL" not in nullable_str
                is_pk = col_name in pk_cols or bool(_PRIMARY_KEY_REGEX.search(raw_line))
                cols.append(ColumnDef(name=col_name, data_type=dtype, nullable=nullable, is_pk=is_pk))

            if cols:
                result[table_name] = cols

        return result


# ---------------------------------------------------------------------------
# Schema Snapshot
# ---------------------------------------------------------------------------

class SchemaSnapshot:
    """Captures and persists pre-wave SQL schema state."""

    DEFAULT_SNAPSHOT_DIR = ".claude/schema_snapshots"

    @classmethod
    def capture_pre_wave(
        cls,
        wave_id: int,
        sql_files: list[str],
        snapshot_dir: str = DEFAULT_SNAPSHOT_DIR,
    ) -> None:
        """Capture SQL schema state before wave execution and persist to disk.

        For each SQL file, reads the version committed at HEAD (git show HEAD:{path}).
        New files (not in HEAD) are recorded as empty schema.

        Args:
            wave_id: Current wave number.
            sql_files: List of .sql file paths (relative to repo root).
            snapshot_dir: Directory to write snapshot JSON files.
        """
        import time as _time

        snapshot_path = Path(snapshot_dir)
        snapshot_path.mkdir(parents=True, exist_ok=True)

        parser = DDLParser()
        snapshot: dict = {}

        for file_path in sql_files:
            result = subprocess.run(
                ["git", "show", f"HEAD:{file_path}"],
                capture_output=True, text=True, check=False, timeout=15,
            )
            if result.returncode != 0:
                # New file not yet committed — empty pre-state
                snapshot[file_path] = {}
                continue

            tables = parser.parse_ddl(result.stdout)
            snapshot[file_path] = {
                table_name: [
                    [col.name, col.data_type, col.nullable, col.is_pk]
                    for col in cols
                ]
                for table_name, cols in tables.items()
            }

        out_file = snapshot_path / f"wave_{wave_id}_pre.json"
        out_file.write_text(
            json.dumps({"wave_id": wave_id, "captured_at": _time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "files": snapshot}, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load_pre_wave(cls, wave_id: int, snapshot_dir: str = DEFAULT_SNAPSHOT_DIR) -> dict:
        """Load a previously captured pre-wave snapshot.

        Returns empty dict if snapshot not found.
        """
        snap_file = Path(snapshot_dir) / f"wave_{wave_id}_pre.json"
        if not snap_file.exists():
            return {}
        try:
            data = json.loads(snap_file.read_text(encoding="utf-8"))
            return data.get("files", {})
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# Schema Diff
# ---------------------------------------------------------------------------

class SchemaDiff:
    """Compares pre-wave and post-wave SQL schema snapshots."""

    @classmethod
    def compare_post_wave(
        cls,
        wave_id: int,
        sql_files: list[str],
        snapshot_dir: str = SchemaSnapshot.DEFAULT_SNAPSHOT_DIR,
    ) -> SchemaDiffReport:
        """Compare current file content against pre-wave snapshot.

        Args:
            wave_id: Wave ID (used to load the matching pre-wave snapshot).
            sql_files: List of .sql file paths that were part of this wave.
            snapshot_dir: Directory containing snapshot JSON files.

        Returns:
            SchemaDiffReport with all changes classified.
        """
        pre_snapshot = SchemaSnapshot.load_pre_wave(wave_id, snapshot_dir)
        parser = DDLParser()
        changes: list[SchemaChange] = []

        for file_path in sql_files:
            current_content = Path(file_path).read_text(encoding="utf-8") if Path(file_path).exists() else ""
            post_tables = parser.parse_ddl(current_content)
            # Lookup snapshot entry: try exact key first, then basename fallback
            _snap_entry = pre_snapshot.get(file_path)
            if _snap_entry is None:
                _basename = Path(file_path).name
                for _key, _val in pre_snapshot.items():
                    if Path(_key).name == _basename:
                        _snap_entry = _val
                        break
            pre_tables: dict = {
                tbl: [ColumnDef(c[0], c[1], c[2], c[3]) for c in cols]
                for tbl, cols in (_snap_entry or {}).items()
            }

            # Detect dropped tables
            for tbl in pre_tables:
                if tbl not in post_tables:
                    changes.append(SchemaChange(
                        file_path=file_path, table_name=tbl,
                        change_type="TABLE_DROPPED", is_breaking=True,
                        affected_models=AffectedModelFinder.find_affected(tbl, ""),
                    ))

            # Detect added tables
            for tbl in post_tables:
                if tbl not in pre_tables:
                    changes.append(SchemaChange(
                        file_path=file_path, table_name=tbl,
                        change_type="TABLE_ADDED", is_breaking=False,
                    ))
                    continue

                pre_cols = {c.name: c for c in pre_tables[tbl]}
                post_cols = {c.name: c for c in post_tables[tbl]}

                # Removed columns (breaking)
                for col_name, col in pre_cols.items():
                    if col_name not in post_cols:
                        affected = AffectedModelFinder.find_affected(tbl, col_name)
                        changes.append(SchemaChange(
                            file_path=file_path, table_name=tbl,
                            change_type="COLUMN_REMOVED", column_name=col_name,
                            old_value=col.data_type, new_value=None,
                            is_breaking=True, affected_models=affected,
                        ))

                # Added columns (non-breaking)
                for col_name, col in post_cols.items():
                    if col_name not in pre_cols:
                        changes.append(SchemaChange(
                            file_path=file_path, table_name=tbl,
                            change_type="COLUMN_ADDED", column_name=col_name,
                            old_value=None, new_value=col.data_type,
                            is_breaking=False,
                        ))

                # Type changes
                for col_name in pre_cols:
                    if col_name in post_cols:
                        old_t = pre_cols[col_name].data_type
                        new_t = post_cols[col_name].data_type
                        if old_t.lower() != new_t.lower():
                            is_breaking = _is_narrowing_type_change(old_t, new_t)
                            changes.append(SchemaChange(
                                file_path=file_path, table_name=tbl,
                                change_type="TYPE_CHANGED", column_name=col_name,
                                old_value=old_t, new_value=new_t,
                                is_breaking=is_breaking,
                            ))

        has_breaking = any(c.is_breaking for c in changes)
        return SchemaDiffReport(wave_id=wave_id, has_breaking_changes=has_breaking, changes=changes)


# ---------------------------------------------------------------------------
# Affected Model Finder
# ---------------------------------------------------------------------------

class AffectedModelFinder:
    """Scans dbt model files to find downstream models referencing a column."""

    @staticmethod
    def find_affected(table_name: str, column_name: str, models_dir: str = "models") -> list[str]:
        """Return model names that reference table_name and column_name.

        Args:
            table_name: Name of the table/model whose column was changed.
            column_name: Name of the removed/changed column (empty → any column).
            models_dir: Directory containing dbt model .sql files.

        Returns:
            List of model base names (without .sql extension).
        """
        models_path = Path(models_dir)
        if not models_path.exists():
            return []

        table_ref_pattern = re.compile(
            rf"""(?:ref\s*\(\s*['"]({re.escape(table_name)})['"]\s*\)|"""
            rf"""source\s*\(\s*['"][^'"]+['"]\s*,\s*['"]{re.escape(table_name)}['"]\s*\))""",
            re.IGNORECASE,
        )
        col_pattern = re.compile(rf"\b{re.escape(column_name)}\b", re.IGNORECASE) if column_name else None

        affected: list[str] = []
        for sql_file in models_path.rglob("*.sql"):
            try:
                content = sql_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if not table_ref_pattern.search(content):
                continue
            if col_pattern and not col_pattern.search(content):
                continue
            affected.append(sql_file.stem)

        return affected

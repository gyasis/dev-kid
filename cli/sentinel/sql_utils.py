"""
SQL Utilities — Shared helpers for SQL/dbt parsing.

Used by sql_schema_diff, sql_constitution, and dbt_graph modules.
"""

from __future__ import annotations

import re
import warnings
from typing import Any, Optional, Tuple


# ---------------------------------------------------------------------------
# Jinja stripping
# ---------------------------------------------------------------------------

_REF_PATTERN = re.compile(r"\{\{\s*ref\s*\(\s*['\"](\w+)['\"]\s*\)\s*\}\}", re.DOTALL)
_SOURCE_PATTERN = re.compile(
    r"\{\{\s*source\s*\(\s*['\"](\w+)['\"],\s*['\"](\w+)['\"]\s*\)\s*\}\}", re.DOTALL
)
_JINJA_BLOCK = re.compile(r"\{\{.*?\}\}", re.DOTALL)
_JINJA_TAG = re.compile(r"\{%.*?%\}", re.DOTALL)


def strip_jinja(sql: str) -> str:
    """Replace Jinja template tokens with valid SQL placeholders.

    Transformations (in order):
      1. {{ ref('model') }}         → model
      2. {{ source('src', 'tbl') }} → src__tbl
      3. Remaining {{ ... }}        → 1
      4. {% ... %}                  → (removed)

    Args:
        sql: Raw dbt SQL that may contain Jinja syntax.

    Returns:
        SQL string with Jinja replaced by syntactically valid SQL tokens.
    """
    sql = _REF_PATTERN.sub(lambda m: m.group(1), sql)
    sql = _SOURCE_PATTERN.sub(lambda m: f"{m.group(1)}__{m.group(2)}", sql)
    sql = _JINJA_BLOCK.sub("1", sql)
    sql = _JINJA_TAG.sub("", sql)
    return sql


# ---------------------------------------------------------------------------
# Optional sqlglot import
# ---------------------------------------------------------------------------

def try_import_sqlglot() -> Tuple[Optional[Any], Optional[Any]]:
    """Attempt to import sqlglot and its expressions module.

    Returns:
        (sqlglot_module, expressions_module) tuple, or (None, None) if not installed.
        Emits a single UserWarning when sqlglot is unavailable.
    """
    try:
        import sqlglot
        import sqlglot.expressions as exp
        return sqlglot, exp
    except ImportError:
        warnings.warn(
            "sqlglot is not installed; SQL parsing falls back to regex. "
            "Install with: pip install sqlglot",
            UserWarning,
            stacklevel=3,
        )
        return None, None

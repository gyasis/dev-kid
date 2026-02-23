"""
Integration Sentinel — SQL/dbt Constitution Scanner

Scans .sql and .yml files for active constitution rule violations at wave checkpoints.

Built-in rules (all opt-in via .constitution.md):
  NO_SELECT_STAR               — SELECT * forbidden in production models
  MODEL_DESCRIPTION_REQUIRED   — all dbt models must have a description in schema.yml
  INCREMENTAL_NEEDS_UNIQUE_KEY — incremental models must declare unique_key
  NO_HARDCODED_CREDENTIALS     — no passwords/API keys in SQL source
  MIGRATION_NEEDS_ROLLBACK     — migration files must include a rollback section

Components:
  SQLConstitutionScanner  — scans .sql files
  DBTSchemaYAMLScanner    — scans dbt .yml schema files
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .sql_utils import strip_jinja, try_import_sqlglot


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SQLViolation:
    """A single constitution rule violation in a SQL or YAML file."""
    rule: str
    file_path: str
    line: int
    message: str

    def format(self) -> str:
        return f"❌ VIOLATION [{self.rule}] {self.file_path}:{self.line}\n   {self.message}"


# ---------------------------------------------------------------------------
# Credential patterns (regex — no AST needed for secret detection)
# ---------------------------------------------------------------------------

_CREDENTIAL_PATTERNS: list[re.Pattern] = [
    re.compile(r"(?i)(password|passwd|pwd)\s*=\s*'[^']{4,}'"),
    re.compile(r"(?i)(api_key|apikey|secret|token)\s*=\s*'[^']{8,}'"),
    re.compile(r'(?i)(password|passwd|pwd)\s*=\s*"[^"]{4,}"'),
    re.compile(r'(?i)(api_key|apikey|secret|token)\s*=\s*"[^"]{8,}"'),
]

# SELECT * detection regex (fallback when sqlglot unavailable)
_SELECT_STAR_REGEX = re.compile(r"\bSELECT\s+\*\s+FROM\b", re.IGNORECASE)

# Incremental config detection
_INCREMENTAL_PATTERN = re.compile(r"materialized\s*=\s*['\"]incremental['\"]", re.IGNORECASE)
_UNIQUE_KEY_PATTERN = re.compile(r"unique_key\s*=", re.IGNORECASE)

# Rollback marker detection
_ROLLBACK_MARKERS = re.compile(
    r"(?:--\s*(?:rollback|down|revert|undo))", re.IGNORECASE
)


def _line_of(content: str, char_offset: int) -> int:
    """Return 1-based line number for a character offset in content."""
    return content[:char_offset].count("\n") + 1


# ---------------------------------------------------------------------------
# SQL file scanner
# ---------------------------------------------------------------------------

class SQLConstitutionScanner:
    """Scans .sql files for active SQL constitution rule violations."""

    def scan_file(self, path: str, enabled_rules: list[str]) -> list[SQLViolation]:
        """Scan a .sql file for violations of the enabled rules.

        Args:
            path: Path to the .sql file.
            enabled_rules: List of rule IDs that are active in the constitution.

        Returns:
            List of SQLViolation objects (empty = clean).
        """
        file_path = Path(path)
        if not file_path.exists():
            return []

        try:
            raw_content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        violations: list[SQLViolation] = []

        if "NO_SELECT_STAR" in enabled_rules:
            violations.extend(self._check_no_select_star(raw_content, path))

        if "NO_HARDCODED_CREDENTIALS" in enabled_rules:
            violations.extend(self._check_no_hardcoded_credentials(raw_content, path))

        if "INCREMENTAL_NEEDS_UNIQUE_KEY" in enabled_rules:
            violations.extend(self._check_incremental_unique_key(raw_content, path))

        if "MIGRATION_NEEDS_ROLLBACK" in enabled_rules:
            violations.extend(self._check_migration_rollback(raw_content, path))

        return violations

    # ------------------------------------------------------------------
    # Rule implementations
    # ------------------------------------------------------------------

    def _check_no_select_star(self, content: str, path: str) -> list[SQLViolation]:
        violations: list[SQLViolation] = []
        cleaned = strip_jinja(content)
        sqlglot_mod, exp = try_import_sqlglot()

        if sqlglot_mod is not None:
            try:
                statements = sqlglot_mod.parse(cleaned)  # type: ignore[attr-defined]
                for stmt in statements:
                    if stmt is None:
                        continue
                    for select in stmt.find_all(exp.Select):  # type: ignore[attr-defined]
                        for expr in select.expressions:
                            if isinstance(expr, exp.Star):  # type: ignore[attr-defined]
                                # Find approximate line by searching raw content
                                m = re.search(r"\bSELECT\s+\*", content, re.IGNORECASE)
                                line = _line_of(content, m.start()) if m else 1
                                violations.append(SQLViolation(
                                    rule="NO_SELECT_STAR", file_path=path, line=line,
                                    message="SELECT * is forbidden. Explicitly list columns to prevent silent schema breakage.",
                                ))
                return violations
            except Exception:
                pass  # fall through to regex

        # Regex fallback
        for m in _SELECT_STAR_REGEX.finditer(content):
            violations.append(SQLViolation(
                rule="NO_SELECT_STAR", file_path=path,
                line=_line_of(content, m.start()),
                message="SELECT * is forbidden. Explicitly list columns to prevent silent schema breakage.",
            ))
        return violations

    def _check_no_hardcoded_credentials(self, content: str, path: str) -> list[SQLViolation]:
        violations: list[SQLViolation] = []
        for pattern in _CREDENTIAL_PATTERNS:
            for m in pattern.finditer(content):
                keyword = m.group(1).upper()
                violations.append(SQLViolation(
                    rule="NO_HARDCODED_CREDENTIALS", file_path=path,
                    line=_line_of(content, m.start()),
                    message=f"Hardcoded credential detected ({keyword}). Use environment variables or a secrets vault.",
                ))
        return violations

    def _check_incremental_unique_key(self, content: str, path: str) -> list[SQLViolation]:
        if not _INCREMENTAL_PATTERN.search(content):
            return []
        if _UNIQUE_KEY_PATTERN.search(content):
            return []
        m = _INCREMENTAL_PATTERN.search(content)
        line = _line_of(content, m.start()) if m else 1
        model_name = Path(path).stem
        return [SQLViolation(
            rule="INCREMENTAL_NEEDS_UNIQUE_KEY", file_path=path, line=line,
            message=f"Incremental model '{model_name}' is missing unique_key. Add unique_key='<column>' to config().",
        )]

    def _check_migration_rollback(self, content: str, path: str) -> list[SQLViolation]:
        # Only applies to files in a migrations/ directory
        if "migrations" not in str(path).replace("\\", "/"):
            return []
        if _ROLLBACK_MARKERS.search(content):
            return []
        return [SQLViolation(
            rule="MIGRATION_NEEDS_ROLLBACK", file_path=path, line=1,
            message="Migration missing rollback section. Add '-- rollback' marker followed by the reverse operation.",
        )]


# ---------------------------------------------------------------------------
# dbt YAML schema scanner
# ---------------------------------------------------------------------------

class DBTSchemaYAMLScanner:
    """Scans dbt schema .yml files for MODEL_DESCRIPTION_REQUIRED and INCREMENTAL_NEEDS_UNIQUE_KEY."""

    def scan_yaml(self, path: str, enabled_rules: list[str]) -> list[SQLViolation]:
        """Scan a dbt schema .yml file for active rule violations.

        Args:
            path: Path to the .yml file.
            enabled_rules: List of active rule IDs.

        Returns:
            List of SQLViolation objects.
        """
        file_path = Path(path)
        if not file_path.exists():
            return []

        try:
            raw_content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        violations: list[SQLViolation] = []

        # Try PyYAML first; fall back to regex line scanning
        data = self._load_yaml(raw_content)

        if data is not None:
            violations.extend(self._check_yaml_parsed(data, path, raw_content, enabled_rules))
        else:
            violations.extend(self._check_yaml_regex(raw_content, path, enabled_rules))

        return violations

    # ------------------------------------------------------------------
    # YAML loading
    # ------------------------------------------------------------------

    @staticmethod
    def _load_yaml(content: str) -> Optional[dict]:
        """Attempt to load YAML; return None if PyYAML unavailable or parse error."""
        try:
            import yaml
            return yaml.safe_load(content)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Parsed YAML checks
    # ------------------------------------------------------------------

    def _check_yaml_parsed(
        self, data: dict, path: str, raw_content: str, enabled_rules: list[str]
    ) -> list[SQLViolation]:
        violations: list[SQLViolation] = []
        models: list[dict] = []
        if isinstance(data, dict):
            models = data.get("models", []) or []

        for model in models:
            if not isinstance(model, dict):
                continue
            name = model.get("name", "<unnamed>")
            description = model.get("description", "")

            if "MODEL_DESCRIPTION_REQUIRED" in enabled_rules:
                if not description or not str(description).strip():
                    # Find approximate line in raw YAML for the model name
                    m = re.search(rf"- name:\s*{re.escape(name)}", raw_content)
                    line = _line_of(raw_content, m.start()) if m else 1
                    violations.append(SQLViolation(
                        rule="MODEL_DESCRIPTION_REQUIRED", file_path=path, line=line,
                        message=f"Model '{name}' has no description. Add a description: field.",
                    ))

            if "INCREMENTAL_NEEDS_UNIQUE_KEY" in enabled_rules:
                config = model.get("config", {}) or {}
                if config.get("materialized") == "incremental" and not config.get("unique_key"):
                    m = re.search(rf"- name:\s*{re.escape(name)}", raw_content)
                    line = _line_of(raw_content, m.start()) if m else 1
                    violations.append(SQLViolation(
                        rule="INCREMENTAL_NEEDS_UNIQUE_KEY", file_path=path, line=line,
                        message=f"Incremental model '{name}' is missing unique_key in schema.yml config.",
                    ))

        return violations

    # ------------------------------------------------------------------
    # Regex fallback YAML checks
    # ------------------------------------------------------------------

    def _check_yaml_regex(
        self, content: str, path: str, enabled_rules: list[str]
    ) -> list[SQLViolation]:
        """Minimal regex-based YAML scanning when PyYAML is unavailable."""
        violations: list[SQLViolation] = []
        lines = content.splitlines()

        model_name_pattern = re.compile(r"^\s*-\s+name:\s+(\S+)")
        description_pattern = re.compile(r"^\s+description:\s*\S+")
        materialized_pattern = re.compile(r"materialized:\s*['\"]?incremental['\"]?")
        unique_key_pattern = re.compile(r"unique_key:")

        i = 0
        while i < len(lines):
            m = model_name_pattern.match(lines[i])
            if m:
                model_name = m.group(1)
                line_no = i + 1
                # Look ahead for description within next ~10 lines
                block_end = min(i + 15, len(lines))
                block = lines[i:block_end]
                block_text = "\n".join(block)

                if "MODEL_DESCRIPTION_REQUIRED" in enabled_rules:
                    if not description_pattern.search(block_text):
                        violations.append(SQLViolation(
                            rule="MODEL_DESCRIPTION_REQUIRED", file_path=path, line=line_no,
                            message=f"Model '{model_name}' has no description. Add a description: field.",
                        ))

                if "INCREMENTAL_NEEDS_UNIQUE_KEY" in enabled_rules:
                    if (materialized_pattern.search(block_text)
                            and not unique_key_pattern.search(block_text)):
                        violations.append(SQLViolation(
                            rule="INCREMENTAL_NEEDS_UNIQUE_KEY", file_path=path, line=line_no,
                            message=f"Incremental model '{model_name}' is missing unique_key.",
                        ))
            i += 1

        return violations

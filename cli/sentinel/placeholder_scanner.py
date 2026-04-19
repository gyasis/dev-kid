"""
Integration Sentinel — Placeholder Scanner

Detects forbidden placeholder patterns (TODO, mock_*, stub_*, etc.) in
production code files. Test directories are always excluded.

Invoked by SentinelRunner.run() before the micro-agent test loop.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from . import PlaceholderViolation, SentinelConfig


# Built-in patterns that signal unfinished production code
DEFAULT_PATTERNS: list[str] = [
    r'\bTODO\b',
    r'\bFIXME\b',
    r'\bHACK\b',
    r'\bXXX\b',
    r'\bNOTIMPLEMENTED\b',
    r'\bNotImplementedError\b',
    r'\bmock_\w+',
    r'\bstub_\w+',
    r'\bPLACEHOLDER\b',
    r'MOCK_\w+',
    r'return None  # (?:implement|TODO)',
    r'raise NotImplementedError',
    r'pass  # (?:implement|TODO|stub)',
]

# Paths that are ALWAYS excluded — cannot be overridden
ALWAYS_EXCLUDE: list[str] = [
    'tests/',
    '__mocks__/',
    r'(?:^|/)test_[^/]+\.py$',  # pytest-style prefix: test_auth.py
    r'.*\.test\.py$',
    r'.*\.spec\.py$',
    r'.*\.test\.ts$',
    r'.*\.spec\.ts$',
    r'.*\.test\.js$',
    r'.*\.spec\.js$',
    r'.*\.test\.tsx$',
    r'.*\.spec\.tsx$',
]

# Context lines to include above/below each match
CONTEXT_RADIUS = 2

# SQL-specific placeholder patterns
SQL_PLACEHOLDER_PATTERNS: dict[str, re.Pattern] = {
    "SELECT_ONE": re.compile(
        r"^\s*SELECT\s+1\s*(?:AS\s+\w+\s*)?$",
        re.MULTILINE | re.IGNORECASE,
    ),
    "TODO_COMMENT": re.compile(
        r"--\s*(TODO|FIXME|STUB|PLACEHOLDER)\b",
        re.IGNORECASE,
    ),
    "EMPTY_REF": re.compile(
        r"ref\s*\(\s*['\"][\s]*['\"]\s*\)",
        re.IGNORECASE,
    ),
}


@dataclass
class SQLPlaceholderViolation:
    """A SQL-specific placeholder pattern violation."""

    file_path: str
    line_number: int
    pattern_type: str
    matched_text: str


class PlaceholderScanner:
    """Scans files for forbidden placeholder patterns."""

    def __init__(self, patterns: list[str], exclude_paths: list[str]) -> None:
        """Initialise scanner.

        Args:
            patterns: Additional regex patterns beyond DEFAULT_PATTERNS.
            exclude_paths: Additional glob/regex paths beyond ALWAYS_EXCLUDE.
        """
        all_patterns = DEFAULT_PATTERNS + patterns
        self._compiled = [re.compile(p) for p in all_patterns]
        self._pattern_strings = all_patterns
        self._exclude_paths = ALWAYS_EXCLUDE + exclude_paths

    def scan(self, files: list[Path]) -> list[PlaceholderViolation]:
        """Scan the given files for placeholder violations.

        Rules:
        - Only files explicitly listed are scanned.
        - Files matching any exclude pattern are skipped.
        - Line numbers are 1-based.
        - Context includes ±CONTEXT_RADIUS surrounding lines.

        Args:
            files: File paths to scan.

        Returns:
            List of PlaceholderViolation objects (empty = clean).
        """
        from . import PlaceholderViolation

        violations: list[PlaceholderViolation] = []

        for file_path in files:
            if self.is_excluded(file_path):
                continue
            if not file_path.exists() or not file_path.is_file():
                continue

            try:
                text = file_path.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue

            lines = text.splitlines()
            for line_idx, line in enumerate(lines):
                for pattern, pattern_str in zip(self._compiled, self._pattern_strings):
                    match = pattern.search(line)
                    if match:
                        # Collect ±CONTEXT_RADIUS lines
                        start = max(0, line_idx - CONTEXT_RADIUS)
                        end = min(len(lines), line_idx + CONTEXT_RADIUS + 1)
                        context = lines[start:end]

                        violations.append(PlaceholderViolation(
                            file_path=str(file_path),
                            line_number=line_idx + 1,
                            matched_pattern=pattern_str,
                            matched_text=match.group(0),
                            context_lines=context,
                        ))
                        break  # One violation per line (first match wins)

        return violations

    def is_excluded(self, file_path: Path) -> bool:
        """Return True if this file should be skipped during scanning.

        Matches against ALWAYS_EXCLUDE union user-configured paths using
        both prefix matching (for directories like 'tests/') and regex.
        """
        path_str = str(file_path)
        # Normalise to forward slashes
        path_str = path_str.replace('\\', '/')

        for excl in self._exclude_paths:
            # Directory prefix match (e.g. 'tests/')
            if excl.endswith('/'):
                if path_str.startswith(excl) or ('/' + excl) in path_str:
                    return True
                continue

            # Regex match (patterns starting with .* or containing regex chars)
            if excl.startswith('.*') or any(c in excl for c in r'$^+?{}[]()\\'):
                try:
                    if re.search(excl, path_str):
                        return True
                except re.error:
                    pass
                continue

            # Plain glob / fnmatch
            if fnmatch.fnmatch(path_str, excl) or fnmatch.fnmatch(Path(path_str).name, excl):
                return True

        return False

    @classmethod
    def from_config(cls, config: 'SentinelConfig') -> 'PlaceholderScanner':
        """Factory: merge built-in patterns with config patterns.

        Args:
            config: A ConfigSchema instance with sentinel_ attributes.

        Returns:
            Configured PlaceholderScanner instance.
        """
        extra_patterns = getattr(config, 'sentinel_placeholder_patterns', []) or []
        extra_excludes = getattr(config, 'sentinel_placeholder_exclude_paths', []) or []
        return cls(patterns=extra_patterns, exclude_paths=extra_excludes)


def scan_sql_file(path: str) -> list[SQLPlaceholderViolation]:
    """Scan a SQL file for SQL-specific placeholder patterns.

    Unlike the general PlaceholderScanner, this function is SQL-aware
    and handles SQL comment syntax (--) correctly.

    Args:
        path: Path to the .sql file to scan.

    Returns:
        List of SQLPlaceholderViolation objects (empty = clean).
    """
    file_path = Path(path)
    if not file_path.exists():
        return []

    try:
        content = file_path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return []

    violations: list[SQLPlaceholderViolation] = []

    for pattern_name, pattern in SQL_PLACEHOLDER_PATTERNS.items():
        for m in pattern.finditer(content):
            line_number = content[:m.start()].count('\n') + 1
            violations.append(SQLPlaceholderViolation(
                file_path=path,
                line_number=line_number,
                pattern_type=pattern_name,
                matched_text=m.group(0).strip(),
            ))

    return violations

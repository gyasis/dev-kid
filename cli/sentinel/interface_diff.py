"""
Integration Sentinel — Interface Diff

Compares the public API surface of a file before and after a micro-agent run.
Supports Python (AST), TypeScript/JavaScript (regex), and Rust (regex).

Invoked by SentinelRunner.run() after the micro-agent run completes.
"""

from __future__ import annotations

import ast
import re
import subprocess
import warnings
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cli.sentinel import InterfaceChangeReport

# ---------------------------------------------------------------------------
# TypeScript / JavaScript patterns
# ---------------------------------------------------------------------------
TS_PATTERNS: list[str] = [
    r'export\s+(?:async\s+)?function\s+(\w+)',
    r'export\s+const\s+(\w+)\s*=',
    r'export\s+(?:abstract\s+)?class\s+(\w+)',
    r'export\s+(?:default\s+)?interface\s+(\w+)',
    r'export\s+type\s+(\w+)',
]
_TS_COMPILED = [re.compile(p) for p in TS_PATTERNS]

# ---------------------------------------------------------------------------
# Rust patterns
# ---------------------------------------------------------------------------
RUST_PATTERNS: list[str] = [
    r'pub\s+(?:async\s+)?fn\s+(\w+)',
    r'pub\s+struct\s+(\w+)',
    r'pub\s+trait\s+(\w+)',
    r'pub\s+enum\s+(\w+)',
]
_RUST_COMPILED = [re.compile(p) for p in RUST_PATTERNS]


class InterfaceDiff:
    """Compares public API surface between two versions of a file."""

    # Map file extensions to a language label
    _EXT_MAP: dict[str, str] = {
        '.py': 'python',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.rs': 'rust',
    }

    def compare(
        self,
        file_path: Path,
        pre_content: str,
        post_content: str,
    ) -> 'InterfaceChangeReport':
        """Compare public API between pre-run and post-run file content.

        Args:
            file_path: Path to the file (used only for extension detection).
            pre_content: File content before the micro-agent run.
            post_content: File content after the micro-agent run.

        Returns:
            InterfaceChangeReport — never raises.
        """
        from cli.sentinel import InterfaceChangeReport

        ext = Path(file_path).suffix.lower()
        language = self._EXT_MAP.get(ext, 'unknown')

        empty_report = InterfaceChangeReport(
            file_path=str(file_path),
            language=language,
            breaking_changes=[],
            non_breaking_changes=[],
            modified_signatures=[],
            is_breaking=False,
            detection_method='none',
        )

        if language == 'python':
            return self._compare_python(str(file_path), pre_content, post_content, empty_report)
        elif language in ('typescript', 'javascript'):
            return self._compare_ts_js(str(file_path), language, pre_content, post_content, empty_report)
        elif language == 'rust':
            return self._compare_rust(str(file_path), pre_content, post_content, empty_report)

        return empty_report

    # ------------------------------------------------------------------
    # Language-specific comparison
    # ------------------------------------------------------------------

    def _compare_python(
        self,
        file_path: str,
        pre: str,
        post: str,
        base: 'InterfaceChangeReport',
    ) -> 'InterfaceChangeReport':
        """Python AST-based comparison."""
        from cli.sentinel import InterfaceChangeReport

        try:
            pre_syms = _extract_python_symbols(pre)
        except SyntaxError:
            warnings.warn(f"SyntaxError in pre-content of {file_path}; skipping diff")
            return base

        try:
            post_syms = _extract_python_symbols(post)
        except SyntaxError:
            warnings.warn(f"SyntaxError in post-content of {file_path}; skipping diff")
            return base

        breaking: list[str] = []
        non_breaking: list[str] = []
        modified_sigs: list[dict] = []

        # Check removed symbols (breaking)
        for name, sig in pre_syms['functions'].items():
            if name not in post_syms['functions']:
                breaking.append(name)
            elif post_syms['functions'][name] != sig:
                modified_sigs.append({
                    'name': name,
                    'old_sig': sig,
                    'new_sig': post_syms['functions'][name],
                })

        for name in pre_syms['classes']:
            if name not in post_syms['classes']:
                breaking.append(name)

        # Check added symbols (non-breaking)
        for name in post_syms['functions']:
            if name not in pre_syms['functions']:
                non_breaking.append(name)

        for name in post_syms['classes']:
            if name not in pre_syms['classes']:
                non_breaking.append(name)

        is_breaking = bool(breaking or modified_sigs)

        return InterfaceChangeReport(
            file_path=file_path,
            language='python',
            breaking_changes=breaking,
            non_breaking_changes=non_breaking,
            modified_signatures=modified_sigs,
            is_breaking=is_breaking,
            detection_method='ast',
        )

    def _compare_ts_js(
        self,
        file_path: str,
        language: str,
        pre: str,
        post: str,
        base: 'InterfaceChangeReport',
    ) -> 'InterfaceChangeReport':
        """TypeScript/JavaScript regex-based comparison."""
        from cli.sentinel import InterfaceChangeReport

        pre_syms = _extract_ts_symbols(pre)
        post_syms = _extract_ts_symbols(post)

        breaking = [s for s in pre_syms if s not in post_syms]
        non_breaking = [s for s in post_syms if s not in pre_syms]
        is_breaking = bool(breaking)

        return InterfaceChangeReport(
            file_path=file_path,
            language=language,
            breaking_changes=breaking,
            non_breaking_changes=non_breaking,
            modified_signatures=[],  # regex cannot detect signature changes
            is_breaking=is_breaking,
            detection_method='regex',
        )

    def _compare_rust(
        self,
        file_path: str,
        pre: str,
        post: str,
        base: 'InterfaceChangeReport',
    ) -> 'InterfaceChangeReport':
        """Rust regex-based comparison."""
        from cli.sentinel import InterfaceChangeReport

        pre_syms = _extract_rust_symbols(pre)
        post_syms = _extract_rust_symbols(post)

        breaking = [s for s in pre_syms if s not in post_syms]
        non_breaking = [s for s in post_syms if s not in pre_syms]
        is_breaking = bool(breaking)

        return InterfaceChangeReport(
            file_path=file_path,
            language='rust',
            breaking_changes=breaking,
            non_breaking_changes=non_breaking,
            modified_signatures=[],
            is_breaking=is_breaking,
            detection_method='regex',
        )

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_pre_content(file_path: str, git_ref: str = 'HEAD') -> str:
        """Get file content at the given git ref.

        Args:
            file_path: Relative path from repo root.
            git_ref: Git reference (commit, branch, tag). Defaults to HEAD.

        Returns:
            File content as a string, or '' if the file didn't exist at that ref.
        """
        try:
            result = subprocess.run(
                ['git', 'show', f'{git_ref}:{file_path}'],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            return result.stdout if result.returncode == 0 else ''
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return ''


# ---------------------------------------------------------------------------
# Symbol extraction helpers
# ---------------------------------------------------------------------------

def _extract_python_symbols(content: str) -> dict:
    """Parse public functions and classes from Python source via AST."""
    tree = ast.parse(content)
    functions: dict[str, str] = {}
    classes: dict[str, list[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                sig = ast.unparse(node).split('\n')[0]
                functions[node.name] = sig
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith('_'):
                classes[node.name] = [ast.unparse(b) for b in node.bases]

    return {'functions': functions, 'classes': classes}


def _extract_ts_symbols(content: str) -> set[str]:
    """Extract exported symbol names from TypeScript/JavaScript source."""
    symbols: set[str] = set()
    for pattern in _TS_COMPILED:
        for m in pattern.finditer(content):
            symbols.add(m.group(1))
    return symbols


def _extract_rust_symbols(content: str) -> set[str]:
    """Extract public symbol names from Rust source."""
    symbols: set[str] = set()
    for pattern in _RUST_COMPILED:
        for m in pattern.finditer(content):
            symbols.add(m.group(1))
    return symbols


# ---------------------------------------------------------------------------
# Add TypeScript/JavaScript detection (T028 requirement)
# ---------------------------------------------------------------------------

def add_ts_patterns(additional_patterns: list[str]) -> None:
    """Extend TS_PATTERNS with additional patterns (used in tests/customisation)."""
    global _TS_COMPILED
    _TS_COMPILED = [re.compile(p) for p in TS_PATTERNS + additional_patterns]

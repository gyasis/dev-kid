"""
Unit tests for cli/sentinel/interface_diff.py

Tests:
  - Python AST: detects added, removed, and signature-changed functions
  - TypeScript regex: detects exported function names
  - Rust regex: detects pub fn
  - Unknown file type returns empty report (no exception)
  - SyntaxError in Python content returns empty report (no exception)
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.sentinel.interface_diff import InterfaceDiff


DIFF = InterfaceDiff()


# ---------------------------------------------------------------------------
# Python AST
# ---------------------------------------------------------------------------

class TestPythonAST:
    def test_added_function_is_non_breaking(self):
        pre = "def foo(): pass\n"
        post = "def foo(): pass\ndef bar(): pass\n"
        report = DIFF.compare(Path("src/module.py"), pre, post)

        assert report.language == "python"
        assert report.detection_method == "ast"
        assert "bar" in report.non_breaking_changes
        assert report.is_breaking is False

    def test_removed_function_is_breaking(self):
        pre = "def foo(): pass\ndef bar(): pass\n"
        post = "def foo(): pass\n"
        report = DIFF.compare(Path("src/module.py"), pre, post)

        assert "bar" in report.breaking_changes
        assert report.is_breaking is True

    def test_signature_changed_is_in_modified_signatures(self):
        pre = "def foo(x): pass\n"
        post = "def foo(x, y): pass\n"
        report = DIFF.compare(Path("src/module.py"), pre, post)

        assert len(report.modified_signatures) == 1
        assert report.modified_signatures[0]["name"] == "foo"

    def test_private_functions_excluded(self):
        pre = "def _private(): pass\n"
        post = ""
        report = DIFF.compare(Path("src/module.py"), pre, post)

        assert "_private" not in report.breaking_changes
        assert "_private" not in report.non_breaking_changes

    def test_syntax_error_returns_empty_report(self):
        pre = "def foo(): pass\n"
        post = "def foo(: invalid syntax\n"
        # Should not raise
        report = DIFF.compare(Path("src/module.py"), pre, post)

        assert report.detection_method == "none"
        assert report.is_breaking is False
        assert report.breaking_changes == []


# ---------------------------------------------------------------------------
# TypeScript / JavaScript regex
# ---------------------------------------------------------------------------

class TestTypeScriptRegex:
    def test_exported_function_detected(self):
        pre = ""
        post = "export function authenticate(user: string): boolean { return false; }\n"
        report = DIFF.compare(Path("src/auth.ts"), pre, post)

        assert report.language == "typescript"
        assert report.detection_method == "regex"
        assert "authenticate" in report.non_breaking_changes

    def test_removed_export_is_breaking(self):
        pre = "export function login(): void {}\n"
        post = ""
        report = DIFF.compare(Path("src/auth.ts"), pre, post)

        assert "login" in report.breaking_changes
        assert report.is_breaking is True

    def test_async_export_function(self):
        pre = ""
        post = "export async function fetchData(): Promise<void> {}\n"
        report = DIFF.compare(Path("src/api.ts"), pre, post)

        assert "fetchData" in report.non_breaking_changes

    def test_exported_interface_detected(self):
        pre = ""
        post = "export interface User { id: number; name: string; }\n"
        report = DIFF.compare(Path("src/types.ts"), pre, post)

        assert "User" in report.non_breaking_changes

    def test_js_extension_works(self):
        pre = "export function greet() {}\n"
        post = "export function greet() {}\nexport function bye() {}\n"
        report = DIFF.compare(Path("src/helpers.js"), pre, post)

        assert report.language == "javascript"
        assert "bye" in report.non_breaking_changes


# ---------------------------------------------------------------------------
# Rust regex
# ---------------------------------------------------------------------------

class TestRustRegex:
    def test_pub_fn_detected(self):
        pre = ""
        post = "pub fn authenticate(user: &str) -> bool { false }\n"
        report = DIFF.compare(Path("src/auth.rs"), pre, post)

        assert report.language == "rust"
        assert report.detection_method == "regex"
        assert "authenticate" in report.non_breaking_changes

    def test_removed_pub_fn_is_breaking(self):
        pre = "pub fn login() {}\n"
        post = ""
        report = DIFF.compare(Path("src/auth.rs"), pre, post)

        assert "login" in report.breaking_changes
        assert report.is_breaking is True

    def test_pub_struct_detected(self):
        pre = ""
        post = "pub struct User { pub id: u32 }\n"
        report = DIFF.compare(Path("src/models.rs"), pre, post)

        assert "User" in report.non_breaking_changes

    def test_async_fn_detected(self):
        pre = ""
        post = "pub async fn fetch() -> Result<(), Error> { Ok(()) }\n"
        report = DIFF.compare(Path("src/api.rs"), pre, post)

        assert "fetch" in report.non_breaking_changes


# ---------------------------------------------------------------------------
# Unknown file type
# ---------------------------------------------------------------------------

class TestUnknownFileType:
    def test_unknown_extension_returns_empty_report(self):
        report = DIFF.compare(Path("config.toml"), "old", "new")

        assert report.language == "unknown"
        assert report.detection_method == "none"
        assert report.breaking_changes == []
        assert report.non_breaking_changes == []
        assert report.is_breaking is False

    def test_no_extension_returns_empty_report(self):
        report = DIFF.compare(Path("Makefile"), "old", "new")

        assert report.is_breaking is False

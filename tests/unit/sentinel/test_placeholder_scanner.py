"""
Unit tests for cli/sentinel/placeholder_scanner.py

Tests:
  - Each built-in pattern matches correctly
  - Excluded paths (tests/, __mocks__/, *.test.py, *.spec.ts) are never flagged
  - fail_on_detect=false: violations returned but caller decides (scanner just returns list)
  - Clean file → empty violation list
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.sentinel.placeholder_scanner import PlaceholderScanner


def _make_scanner(extra_patterns=None, extra_excludes=None):
    return PlaceholderScanner(
        patterns=extra_patterns or [],
        exclude_paths=extra_excludes or [],
    )


def _tmp_file(content: str, name: str = "src/target.py") -> Path:
    """Write content to a real temp file and return its path."""
    tmp = Path(tempfile.mktemp(suffix=Path(name).suffix))
    tmp.write_text(content, encoding='utf-8')
    return tmp


# ---------------------------------------------------------------------------
# Built-in pattern matching
# ---------------------------------------------------------------------------

class TestBuiltinPatterns:
    def test_todo_detected(self):
        f = _tmp_file("x = 1  # TODO: implement this\n")
        scanner = _make_scanner()
        violations = scanner.scan([f])
        assert len(violations) >= 1
        f.unlink()

    def test_fixme_detected(self):
        f = _tmp_file("# FIXME: broken logic\n")
        scanner = _make_scanner()
        violations = scanner.scan([f])
        assert any('FIXME' in v.matched_pattern for v in violations)
        f.unlink()

    def test_not_implemented_error_detected(self):
        f = _tmp_file("raise NotImplementedError('not done')\n")
        scanner = _make_scanner()
        violations = scanner.scan([f])
        assert len(violations) >= 1
        f.unlink()

    def test_mock_underscore_detected(self):
        f = _tmp_file("def mock_payment(): pass\n")
        scanner = _make_scanner()
        violations = scanner.scan([f])
        assert any('mock_' in v.matched_pattern for v in violations)
        f.unlink()

    def test_stub_underscore_detected(self):
        f = _tmp_file("stub_result = None\n")
        scanner = _make_scanner()
        violations = scanner.scan([f])
        assert any('stub_' in v.matched_pattern for v in violations)
        f.unlink()

    def test_clean_file_returns_empty(self):
        f = _tmp_file("def add(a, b):\n    return a + b\n")
        scanner = _make_scanner()
        violations = scanner.scan([f])
        assert violations == []
        f.unlink()


# ---------------------------------------------------------------------------
# Excluded paths
# ---------------------------------------------------------------------------

class TestExcludedPaths:
    def test_tests_dir_excluded(self):
        scanner = _make_scanner()
        assert scanner.is_excluded(Path("tests/test_auth.py")) is True

    def test_mocks_dir_excluded(self):
        assert _make_scanner().is_excluded(Path("__mocks__/auth.js")) is True

    def test_test_py_suffix_excluded(self):
        assert _make_scanner().is_excluded(Path("test_auth.py")) is True

    def test_spec_ts_excluded(self):
        scanner = _make_scanner()
        # These use regex patterns in ALWAYS_EXCLUDE
        assert scanner.is_excluded(Path("auth.spec.ts")) is True
        assert scanner.is_excluded(Path("auth.test.ts")) is True

    def test_production_file_not_excluded(self):
        scanner = _make_scanner()
        assert scanner.is_excluded(Path("src/auth.py")) is False
        assert scanner.is_excluded(Path("cli/runner.py")) is False


# ---------------------------------------------------------------------------
# fail_on_detect semantics (scanner always returns the list; caller decides)
# ---------------------------------------------------------------------------

class TestFailOnDetect:
    def test_violations_returned_regardless(self):
        """Scanner always returns violations; caller decides to halt or not."""
        f = _tmp_file("# TODO: implement\n")
        scanner = _make_scanner()
        violations = scanner.scan([f])
        # Scanner returns violations regardless — caller uses fail_on_detect
        assert len(violations) >= 1
        f.unlink()


# ---------------------------------------------------------------------------
# from_config factory
# ---------------------------------------------------------------------------

class TestFromConfig:
    def test_merges_custom_patterns(self):
        cfg = MagicMock()
        cfg.sentinel_placeholder_patterns = ['CUSTOM_STUB']
        cfg.sentinel_placeholder_exclude_paths = []

        scanner = PlaceholderScanner.from_config(cfg)
        f = _tmp_file("x = CUSTOM_STUB\n")
        violations = scanner.scan([f])
        assert len(violations) >= 1
        f.unlink()

    def test_merges_custom_excludes(self):
        cfg = MagicMock()
        cfg.sentinel_placeholder_patterns = []
        cfg.sentinel_placeholder_exclude_paths = ['vendor/']

        scanner = PlaceholderScanner.from_config(cfg)
        assert scanner.is_excluded(Path("vendor/lib.py")) is True


# ---------------------------------------------------------------------------
# Context lines
# ---------------------------------------------------------------------------

class TestContextLines:
    def test_context_included(self):
        content = "\n".join([
            "line 1",
            "line 2",
            "# TODO: fix this",  # Line 3
            "line 4",
            "line 5",
        ]) + "\n"
        f = _tmp_file(content)
        scanner = _make_scanner()
        violations = scanner.scan([f])
        assert len(violations) >= 1
        assert violations[0].line_number == 3
        # Should have context lines
        assert len(violations[0].context_lines) > 1
        f.unlink()

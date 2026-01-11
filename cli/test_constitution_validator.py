#!/usr/bin/env python3
"""
Test suite for Constitution.validate_output() method

Tests comprehensive file validation including:
- Type hints validation
- Docstring validation
- Hardcoded secrets detection
- Test coverage checks
"""

import pytest
import tempfile
from pathlib import Path
from constitution_parser import Constitution, ConstitutionViolation


@pytest.fixture
def temp_constitution():
    """Create a temporary constitution file for testing"""
    constitution_content = """
# Test Constitution

## Code Standards
- All functions must have type hints
- All public functions and classes must have docstrings

## Testing Standards
- All code must have test coverage
- Test files must contain test functions

## Security Standards
- No hardcoded secrets (API keys, passwords, tokens)
- Use environment variables for sensitive data
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(constitution_content)
        constitution_path = f.name

    constitution = Constitution(constitution_path)
    yield constitution

    # Cleanup
    Path(constitution_path).unlink()


class TestValidateOutput:
    """Test validate_output() method"""

    def test_validate_output_with_nonexistent_files(self, temp_constitution):
        """validate_output should skip non-existent files"""
        violations = temp_constitution.validate_output([
            '/tmp/nonexistent_file.py',
            '/tmp/another_missing.py'
        ])

        assert len(violations) == 0, "Should not report violations for missing files"

    def test_validate_output_with_non_python_files(self, temp_constitution):
        """validate_output should skip non-Python files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is a text file")
            txt_file = f.name

        try:
            violations = temp_constitution.validate_output([txt_file])
            assert len(violations) == 0, "Should not validate non-Python files"
        finally:
            Path(txt_file).unlink()

    def test_validate_output_returns_structured_violations(self, temp_constitution):
        """validate_output should return ConstitutionViolation objects"""
        # Create a Python file with violations
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def bad_function():
    return 42
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should have violations
            assert len(violations) > 0, "Should detect violations"

            # Check structure
            for violation in violations:
                assert isinstance(violation, ConstitutionViolation)
                assert hasattr(violation, 'file')
                assert hasattr(violation, 'line')
                assert hasattr(violation, 'rule')
                assert hasattr(violation, 'message')
                assert violation.file == py_file
        finally:
            Path(py_file).unlink()


class TestTypeHintsValidation:
    """Test type hints validation"""

    def test_detects_missing_return_type_hint(self, temp_constitution):
        """Should detect functions without return type hints"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def function_without_return_type(x: int):
    return x * 2
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should find violation
            type_hint_violations = [v for v in violations if v.rule == "TYPE_HINTS_REQUIRED"]
            assert len(type_hint_violations) > 0, "Should detect missing return type hint"

            # Check message
            assert any("return type hint" in v.message.lower() for v in type_hint_violations)
        finally:
            Path(py_file).unlink()

    def test_detects_missing_parameter_type_hints(self, temp_constitution):
        """Should detect parameters without type hints"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def function_with_untyped_param(x, y: int) -> int:
    return x + y
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should find violation for parameter 'x'
            param_violations = [v for v in violations if "parameter" in v.message.lower()]
            assert len(param_violations) > 0, "Should detect missing parameter type hint"
        finally:
            Path(py_file).unlink()

    def test_allows_properly_typed_functions(self, temp_constitution):
        """Should not flag functions with proper type hints"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def properly_typed_function(x: int, y: str) -> bool:
    '''Check something'''
    return len(y) > x
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should not have type hint violations
            type_hint_violations = [v for v in violations if v.rule == "TYPE_HINTS_REQUIRED"]
            assert len(type_hint_violations) == 0, "Should not flag properly typed function"
        finally:
            Path(py_file).unlink()

    def test_skips_private_methods(self, temp_constitution):
        """Should not check type hints on private methods"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def _private_function(x):
    return x * 2

def __dunder_method__(self):
    return "test"
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should not flag private methods
            type_hint_violations = [v for v in violations if v.rule == "TYPE_HINTS_REQUIRED"]
            assert len(type_hint_violations) == 0, "Should skip private methods"
        finally:
            Path(py_file).unlink()


class TestDocstringValidation:
    """Test docstring validation"""

    def test_detects_missing_function_docstring(self, temp_constitution):
        """Should detect functions without docstrings"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def function_without_docstring(x: int) -> int:
    return x * 2
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should find docstring violation
            docstring_violations = [v for v in violations if v.rule == "DOCSTRINGS_REQUIRED"]
            assert len(docstring_violations) > 0, "Should detect missing docstring"
            assert any("function" in v.message.lower() for v in docstring_violations)
        finally:
            Path(py_file).unlink()

    def test_detects_missing_class_docstring(self, temp_constitution):
        """Should detect classes without docstrings"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
class MyClass:
    def method(self) -> None:
        pass
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should find docstring violation
            docstring_violations = [v for v in violations if v.rule == "DOCSTRINGS_REQUIRED"]
            assert len(docstring_violations) > 0, "Should detect missing class docstring"
        finally:
            Path(py_file).unlink()

    def test_allows_functions_with_docstrings(self, temp_constitution):
        """Should not flag functions with docstrings"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def documented_function(x: int) -> int:
    '''This function has a docstring'''
    return x * 2
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should not have docstring violations
            docstring_violations = [v for v in violations if v.rule == "DOCSTRINGS_REQUIRED"]
            assert len(docstring_violations) == 0, "Should not flag documented function"
        finally:
            Path(py_file).unlink()

    def test_skips_private_functions_and_classes(self, temp_constitution):
        """Should not check docstrings on private entities"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
def _private_function(x: int) -> int:
    return x * 2

class _PrivateClass:
    pass
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should not flag private entities
            docstring_violations = [v for v in violations if v.rule == "DOCSTRINGS_REQUIRED"]
            assert len(docstring_violations) == 0, "Should skip private entities"
        finally:
            Path(py_file).unlink()


class TestHardcodedSecretsDetection:
    """Test hardcoded secrets detection"""

    def test_detects_hardcoded_password(self, temp_constitution):
        """Should detect hardcoded passwords"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
password = "secret123"
api_key = "abc123xyz"
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should find secret violations
            secret_violations = [v for v in violations if v.rule == "NO_HARDCODED_SECRETS"]
            assert len(secret_violations) >= 1, "Should detect hardcoded secrets"
        finally:
            Path(py_file).unlink()

    def test_allows_environment_variable_usage(self, temp_constitution):
        """Should not flag environment variable usage"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import os
password = os.getenv("PASSWORD")
api_key = os.environ.get("API_KEY")
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should not have secret violations
            secret_violations = [v for v in violations if v.rule == "NO_HARDCODED_SECRETS"]
            assert len(secret_violations) == 0, "Should not flag env var usage"
        finally:
            Path(py_file).unlink()

    def test_allows_empty_or_none_values(self, temp_constitution):
        """Should not flag empty or None values"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
password = None
api_key = ""
token = ''
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should not have secret violations
            secret_violations = [v for v in violations if v.rule == "NO_HARDCODED_SECRETS"]
            assert len(secret_violations) == 0, "Should not flag empty/None values"
        finally:
            Path(py_file).unlink()

    def test_skips_comments(self, temp_constitution):
        """Should not flag secrets in comments"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
# password = "test123"
# This is a comment about api_key usage
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should not have secret violations
            secret_violations = [v for v in violations if v.rule == "NO_HARDCODED_SECRETS"]
            assert len(secret_violations) == 0, "Should skip comments"
        finally:
            Path(py_file).unlink()


class TestTestCoverageValidation:
    """Test coverage validation"""

    def test_detects_empty_test_file(self, temp_constitution):
        """Should detect test files with no test functions"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', prefix='test_', delete=False) as f:
            f.write("""
# Empty test file
pass
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should find test coverage violation
            coverage_violations = [v for v in violations if v.rule == "TEST_COVERAGE_REQUIRED"]
            assert len(coverage_violations) > 0, "Should detect empty test file"
        finally:
            Path(py_file).unlink()

    def test_detects_missing_test_file(self, temp_constitution):
        """Should detect Python files without corresponding test files"""
        # Create a temporary directory
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            # Create a Python file without a test
            module_file = Path(temp_dir) / "module.py"
            module_file.write_text("""
def function(x: int) -> int:
    '''Test function'''
    return x * 2
""")

            violations = temp_constitution.validate_output([str(module_file)])

            # Should find test coverage violation
            coverage_violations = [v for v in violations if v.rule == "TEST_COVERAGE_REQUIRED"]
            assert len(coverage_violations) > 0, "Should detect missing test file"
            assert any("No test file found" in v.message for v in coverage_violations)
        finally:
            shutil.rmtree(temp_dir)

    def test_allows_file_with_adjacent_test(self, temp_constitution):
        """Should not flag files with adjacent test files"""
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            # Create module and test files
            module_file = Path(temp_dir) / "module.py"
            module_file.write_text("""
def function(x: int) -> int:
    '''Test function'''
    return x * 2
""")

            test_file = Path(temp_dir) / "test_module.py"
            test_file.write_text("""
def test_function() -> None:
    '''Test the function'''
    assert True
""")

            violations = temp_constitution.validate_output([str(module_file)])

            # Should not have test coverage violations
            coverage_violations = [v for v in violations if v.rule == "TEST_COVERAGE_REQUIRED"
                                  and "No test file found" in v.message]
            assert len(coverage_violations) == 0, "Should not flag file with test"
        finally:
            shutil.rmtree(temp_dir)

    def test_skips_special_files(self, temp_constitution):
        """Should skip __init__.py, setup.py, and other special files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.name = f.name.replace('.py', '__init__.py')
            f.write("""
# __init__.py file
""")
            py_file = f.name

        try:
            violations = temp_constitution.validate_output([py_file])

            # Should not have test coverage violations
            coverage_violations = [v for v in violations if v.rule == "TEST_COVERAGE_REQUIRED"
                                  and "No test file found" in v.message]
            assert len(coverage_violations) == 0, "Should skip special files"
        finally:
            if Path(py_file).exists():
                Path(py_file).unlink()


class TestMultipleFilesValidation:
    """Test validation of multiple files"""

    def test_validates_multiple_files(self, temp_constitution):
        """Should validate multiple files and aggregate violations"""
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            # Create multiple Python files with violations
            file1 = Path(temp_dir) / "file1.py"
            file1.write_text("""
def bad_function():
    return 42
""")

            file2 = Path(temp_dir) / "file2.py"
            file2.write_text("""
password = "secret123"
""")

            violations = temp_constitution.validate_output([
                str(file1),
                str(file2)
            ])

            # Should have violations from both files
            assert len(violations) > 0, "Should find violations in multiple files"

            # Check violations are from different files
            files_with_violations = set(v.file for v in violations)
            assert len(files_with_violations) > 1, "Should have violations from multiple files"
        finally:
            shutil.rmtree(temp_dir)

    def test_handles_mixed_valid_and_invalid_files(self, temp_constitution):
        """Should handle mix of valid and invalid files"""
        import tempfile
        import shutil

        temp_dir = tempfile.mkdtemp()
        try:
            # Create good file
            good_file = Path(temp_dir) / "good.py"
            good_file.write_text("""
def good_function(x: int) -> int:
    '''This is documented and typed'''
    return x * 2
""")

            # Create bad file
            bad_file = Path(temp_dir) / "bad.py"
            bad_file.write_text("""
def bad_function():
    return 42
""")

            violations = temp_constitution.validate_output([
                str(good_file),
                str(bad_file)
            ])

            # Should only have violations from bad file
            bad_file_violations = [v for v in violations if v.file == str(bad_file)]
            good_file_violations = [v for v in violations if v.file == str(good_file)]

            assert len(bad_file_violations) > 0, "Should have violations from bad file"
            # Note: good_file might have test coverage violations, so we check for specific rules
            type_hint_violations = [v for v in good_file_violations if v.rule == "TYPE_HINTS_REQUIRED"]
            assert len(type_hint_violations) == 0, "Should not have type hint violations in good file"
        finally:
            shutil.rmtree(temp_dir)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

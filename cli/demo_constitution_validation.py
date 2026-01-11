#!/usr/bin/env python3
"""
Demonstration of Constitution.validate_output() comprehensive validation

This script demonstrates the enhanced validation capabilities:
- Type hints validation
- Docstring validation
- Hardcoded secrets detection
- Test coverage checks
"""

import tempfile
from pathlib import Path
from constitution_parser import Constitution


def create_sample_files():
    """Create sample Python files with various violations"""
    temp_dir = Path(tempfile.mkdtemp())

    # File 1: Missing type hints
    (temp_dir / "no_type_hints.py").write_text("""
def calculate_total(items):
    return sum(items)

def format_name(first, last):
    return f"{first} {last}"
""")

    # File 2: Missing docstrings
    (temp_dir / "no_docstrings.py").write_text("""
class Calculator:
    def add(self, x: int, y: int) -> int:
        return x + y

def multiply(x: int, y: int) -> int:
    return x * y
""")

    # File 3: Hardcoded secrets
    (temp_dir / "hardcoded_secrets.py").write_text("""
# Bad: hardcoded credentials
API_KEY = "abc123xyz"
password = "secret123"
token = "bearer_xyz789"

# Good: environment variables
import os
safe_api_key = os.getenv("API_KEY")
safe_password = os.environ.get("PASSWORD")
""")

    # File 4: Missing test file
    (temp_dir / "untested_module.py").write_text("""
def important_function(x: int) -> int:
    '''This function needs tests'''
    return x * 2
""")

    # File 5: Empty test file
    (temp_dir / "test_empty.py").write_text("""
# This test file has no tests
pass
""")

    # File 6: Perfect file
    (temp_dir / "test_perfect.py").write_text("""
def test_something() -> None:
    '''Test that verifies something works'''
    assert True
""")

    (temp_dir / "perfect.py").write_text("""
def well_written_function(x: int, y: str) -> bool:
    '''
    Check if string length exceeds threshold

    Args:
        x: Integer threshold
        y: String to check

    Returns:
        True if string length > threshold
    '''
    return len(y) > x
""")

    return temp_dir


def demonstrate_validation():
    """Demonstrate comprehensive validation"""
    print("=" * 70)
    print("Constitution Validator - Comprehensive Validation Demo")
    print("=" * 70)

    # Create sample constitution
    constitution_content = """
# Demo Constitution

## Code Standards
- All functions must have type hints
- All public functions and classes must have docstrings
- Follow PEP 8 style guidelines

## Testing Standards
- All code must have test coverage
- Test files must contain test functions
- Maintain >80% code coverage

## Security Standards
- No hardcoded secrets (API keys, passwords, tokens)
- Use environment variables for sensitive data
- Never commit credentials to version control
"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(constitution_content)
        constitution_path = f.name

    constitution = Constitution(constitution_path)
    temp_dir = create_sample_files()

    print(f"\nConstitution loaded from: {constitution_path}")
    print(f"Sample files created in: {temp_dir}\n")

    # Validate all files
    all_files = [str(f) for f in temp_dir.glob("*.py")]
    violations = constitution.validate_output(all_files)

    print(f"Validated {len(all_files)} Python files")
    print(f"Found {len(violations)} total violations\n")

    # Group violations by rule
    from collections import defaultdict
    violations_by_rule = defaultdict(list)
    for violation in violations:
        violations_by_rule[violation.rule].append(violation)

    # Display violations by rule
    for rule, rule_violations in sorted(violations_by_rule.items()):
        print(f"\n{rule} ({len(rule_violations)} violations)")
        print("-" * 70)

        for v in rule_violations[:5]:  # Show first 5 of each type
            file_name = Path(v.file).name
            print(f"  📄 {file_name}:{v.line}")
            print(f"     {v.message}\n")

        if len(rule_violations) > 5:
            print(f"  ... and {len(rule_violations) - 5} more\n")

    # Show files without violations
    files_with_violations = set(v.file for v in violations)
    clean_files = [f for f in all_files if f not in files_with_violations]

    if clean_files:
        print(f"\n✅ Clean Files ({len(clean_files)})")
        print("-" * 70)
        for f in clean_files:
            print(f"  • {Path(f).name}")

    # Demonstrate specific validation features
    print("\n" + "=" * 70)
    print("Validation Features Demonstrated")
    print("=" * 70)

    features = [
        ("Type Hints", "TYPE_HINTS_REQUIRED"),
        ("Docstrings", "DOCSTRINGS_REQUIRED"),
        ("Hardcoded Secrets", "NO_HARDCODED_SECRETS"),
        ("Test Coverage", "TEST_COVERAGE_REQUIRED")
    ]

    for feature_name, rule_name in features:
        count = len([v for v in violations if v.rule == rule_name])
        status = "✅ PASS" if count == 0 else f"❌ {count} violations"
        print(f"  {feature_name:.<40} {status}")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    total_files = len(all_files)
    files_with_issues = len(files_with_violations)
    files_clean = len(clean_files)

    print(f"  Total files validated: {total_files}")
    print(f"  Files with violations: {files_with_issues} ({files_with_issues/total_files*100:.1f}%)")
    print(f"  Clean files: {files_clean} ({files_clean/total_files*100:.1f}%)")
    print(f"  Total violations: {len(violations)}")
    print(f"  Unique violation types: {len(violations_by_rule)}")

    # Cleanup
    Path(constitution_path).unlink()
    import shutil
    shutil.rmtree(temp_dir)

    print("\n✅ Demonstration complete!\n")


if __name__ == '__main__':
    demonstrate_validation()

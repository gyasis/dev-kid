# Constitution Validation Reference

## Overview

The `Constitution.validate_output()` method performs comprehensive validation of modified Python files against constitutional rules. This document describes the validation capabilities, rule types, and usage patterns.

## Method Signature

```python
def validate_output(self, files: List[str]) -> List[ConstitutionViolation]:
    """
    Validate modified files against constitution rules

    Checks for:
    - Type hints on all functions
    - Docstrings on public functions/classes
    - No hardcoded secrets (API keys, passwords)
    - Test coverage for new code
    - Security best practices

    Args:
        files: List of file paths to validate

    Returns:
        List of ConstitutionViolation objects
    """
```

## Validation Rules

### 1. Type Hints (TYPE_HINTS_REQUIRED)

**What it checks:**
- All public functions have return type annotations (`->`)
- All function parameters (except `self`, `cls`, `*args`, `**kwargs`) have type hints

**Examples:**

```python
# ❌ Violation: Missing return type hint
def calculate_total(items: list):
    return sum(items)

# ❌ Violation: Missing parameter type hint
def format_name(first, last: str) -> str:
    return f"{first} {last}"

# ✅ Compliant
def calculate_total(items: list) -> int:
    return sum(items)
```

**Exclusions:**
- Private methods (starting with `_`)
- Dunder methods (`__init__`, `__str__`, etc.)
- Functions decorated with `@property`

### 2. Docstrings (DOCSTRINGS_REQUIRED)

**What it checks:**
- All public functions have docstrings
- All public classes have docstrings

**Examples:**

```python
# ❌ Violation: Missing docstring
def calculate_total(items: list) -> int:
    return sum(items)

# ✅ Compliant
def calculate_total(items: list) -> int:
    '''Calculate the sum of all items in the list'''
    return sum(items)
```

**Exclusions:**
- Private functions and classes (starting with `_`)

### 3. Hardcoded Secrets (NO_HARDCODED_SECRETS)

**What it checks:**
- Detects hardcoded passwords, API keys, tokens, and secrets
- Flags direct string assignments to sensitive variable names

**Detected Keywords:**
- `password`, `passwd`, `pwd`
- `api_key`, `apikey`, `api-key`
- `secret`, `secret_key`
- `token`, `auth_token`, `access_token`
- `private_key`, `privatekey`
- `client_secret`, `client-secret`

**Examples:**

```python
# ❌ Violation: Hardcoded secret
API_KEY = "abc123xyz"
password = "secret123"

# ✅ Compliant: Environment variables
import os
API_KEY = os.getenv("API_KEY")
password = os.environ.get("PASSWORD")

# ✅ Compliant: Empty/None values
password = None
api_key = ""
```

**Exclusions:**
- Environment variable usage (`os.getenv`, `os.environ`)
- Configuration methods (`config.get`)
- User input (`input()`, `getpass()`)
- Argparse defaults (`default=`, `help=`)
- Empty strings and None values
- Comments and docstrings

### 4. Test Coverage (TEST_COVERAGE_REQUIRED)

**What it checks:**
- Test files contain actual test functions
- Python modules have corresponding test files

**Test File Detection:**
Files are considered test files if they match:
- `test_*.py` pattern
- `*_test.py` pattern

**Test File Search Paths:**
For a module `module.py`, the validator checks:
1. Same directory: `test_module.py`
2. Same directory: `module_test.py`
3. Tests subdirectory: `tests/test_module.py`

**Examples:**

```python
# ❌ Violation: Empty test file
# test_module.py
pass

# ✅ Compliant: Contains test functions
# test_module.py
def test_function():
    '''Test the function works'''
    assert True
```

**Exclusions:**
- `__init__.py`
- `setup.py`
- `conftest.py`

## ConstitutionViolation Structure

Each violation is returned as a `ConstitutionViolation` object:

```python
@dataclass
class ConstitutionViolation:
    file: str          # Absolute path to file with violation
    line: int          # Line number where violation occurs
    rule: str          # Rule identifier (e.g., "TYPE_HINTS_REQUIRED")
    message: str       # Human-readable description
```

## Usage Examples

### Basic Validation

```python
from constitution_parser import Constitution

# Load constitution
constitution = Constitution("memory-bank/shared/.constitution.md")

# Validate modified files
violations = constitution.validate_output([
    "src/module.py",
    "src/utils.py"
])

# Check for violations
if violations:
    print(f"Found {len(violations)} violations:")
    for v in violations:
        print(f"  {v.file}:{v.line} [{v.rule}] {v.message}")
else:
    print("✅ All files pass validation")
```

### Filtering by Rule Type

```python
# Get only type hint violations
type_hint_violations = [
    v for v in violations
    if v.rule == "TYPE_HINTS_REQUIRED"
]

# Get only security violations
security_violations = [
    v for v in violations
    if v.rule == "NO_HARDCODED_SECRETS"
]
```

### Grouping Violations by File

```python
from collections import defaultdict

violations_by_file = defaultdict(list)
for v in violations:
    violations_by_file[v.file].append(v)

# Report per file
for file_path, file_violations in violations_by_file.items():
    print(f"\n{file_path}:")
    for v in file_violations:
        print(f"  Line {v.line}: {v.message}")
```

### Integration with Wave Executor

```python
# In wave_executor.py
def verify_wave_completion(wave_id: int) -> bool:
    """Verify wave completed with constitution compliance"""

    # Get modified files from wave
    modified_files = get_files_modified_in_wave(wave_id)

    # Validate against constitution
    constitution = Constitution()
    violations = constitution.validate_output(modified_files)

    if violations:
        print(f"\n⚠️  Constitution violations detected in Wave {wave_id}:")
        for v in violations[:10]:  # Show first 10
            print(f"  {Path(v.file).name}:{v.line} - {v.message}")

        if len(violations) > 10:
            print(f"  ... and {len(violations) - 10} more")

        return False

    return True
```

## Performance Characteristics

### Time Complexity
- File existence check: O(1) per file
- Python file filter: O(1) per file
- Type hint validation: O(n) where n = lines in file
- Docstring validation: O(n)
- Secret detection: O(n × k) where k = number of secret keywords
- Test coverage: O(1) file system operations

### Space Complexity
- O(m) where m = total number of violations found
- Each violation object is ~200 bytes

### Typical Performance
- Small file (100 lines): ~5ms
- Medium file (500 lines): ~20ms
- Large file (2000 lines): ~80ms
- Very large file (10000 lines): ~400ms

## Best Practices

### 1. Constitution File Structure

Organize constitution with clear sections:

```markdown
## Code Standards
- All functions must have type hints
- All public functions and classes must have docstrings

## Testing Standards
- All code must have test coverage >80%
- Test files must contain test functions

## Security Standards
- No hardcoded secrets (API keys, passwords, tokens)
- Use environment variables for sensitive data
```

### 2. Incremental Validation

Validate only modified files, not entire codebase:

```python
# Get files modified in current branch
modified_files = subprocess.check_output(
    ["git", "diff", "--name-only", "main...HEAD"],
    text=True
).strip().split('\n')

# Filter Python files
python_files = [f for f in modified_files if f.endswith('.py')]

# Validate
violations = constitution.validate_output(python_files)
```

### 3. CI/CD Integration

```yaml
# .github/workflows/constitution.yml
- name: Validate Constitution
  run: |
    python3 -c "
    from constitution_parser import Constitution
    import sys
    constitution = Constitution()
    violations = constitution.validate_output(sys.argv[1:])
    if violations:
      print(f'Found {len(violations)} violations')
      sys.exit(1)
    " $(git diff --name-only origin/main...HEAD | grep '\.py$')
```

### 4. Pre-commit Hook

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Get staged Python files
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

# Validate
python3 -c "
from constitution_parser import Constitution
import sys
constitution = Constitution()
violations = constitution.validate_output(sys.argv[1:])
if violations:
    print('\n⚠️  Constitution violations detected:')
    for v in violations[:5]:
        print(f'  {v.file}:{v.line} - {v.message}')
    print('\nFix violations before committing.')
    sys.exit(1)
" $STAGED_FILES
```

## Limitations

### 1. Static Analysis Only
- Cannot detect runtime issues
- No execution or testing of code
- Limited to syntactic patterns

### 2. Heuristic-Based
- Type hint detection may miss complex cases (multi-line signatures)
- Secret detection may have false positives/negatives
- Test coverage is file-based, not line-based

### 3. Python-Specific
- Only validates `.py` files
- Does not validate other languages

### 4. Simple Pattern Matching
- Uses regex for detection
- May not understand complex Python semantics
- Cannot analyze imported code

## Future Enhancements

Potential improvements for future versions:

1. **AST-Based Analysis**: Use Python's `ast` module for more accurate parsing
2. **Configurable Rules**: Allow per-project rule customization
3. **Severity Levels**: Different levels (ERROR, WARNING, INFO)
4. **Auto-Fix**: Suggest or apply automatic fixes
5. **Multi-Language Support**: Extend to JavaScript, TypeScript, etc.
6. **Integration Testing**: Detect missing integration tests
7. **Complexity Metrics**: Flag overly complex functions
8. **Import Analysis**: Check for unused imports

## Troubleshooting

### Issue: False Positives for Secrets

**Problem**: Legitimate code flagged as hardcoded secret

**Solution**: Add to safe patterns in `_check_hardcoded_secrets`:

```python
safe_patterns = [
    'os.getenv', 'os.environ',
    'your_custom_pattern_here'
]
```

### Issue: Type Hints Not Detected

**Problem**: Multi-line function signatures not parsed correctly

**Current Limitation**: Type hint detection uses single-line regex

**Workaround**: Keep function signatures on one line, or use AST-based parsing

### Issue: Test File Not Found

**Problem**: Test file exists but not detected

**Solution**: Ensure test file matches naming conventions:
- `test_module.py` (same directory)
- `module_test.py` (same directory)
- `tests/test_module.py` (tests subdirectory)

## References

- [PEP 484 - Type Hints](https://peps.python.org/pep-0484/)
- [PEP 257 - Docstring Conventions](https://peps.python.org/pep-0257/)
- [OWASP - Hardcoded Passwords](https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password)
- [pytest - Test Discovery](https://docs.pytest.org/en/stable/goodpractices.html#test-discovery)

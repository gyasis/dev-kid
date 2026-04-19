# Contract: PlaceholderScanner
**Module**: `cli/sentinel/placeholder_scanner.py`
**Invoked by**: `SentinelRunner.run()` before the test loop

---

## Interface

```python
class PlaceholderScanner:
    def __init__(self, patterns: list[str], exclude_paths: list[str]): ...

    def scan(self, files: list[Path]) -> list[PlaceholderViolation]:
        """
        Scan list of file paths for forbidden placeholder patterns.

        Rules:
        - Patterns are compiled as regex (case-sensitive by default)
        - Files matching any exclude_path glob are skipped entirely
        - Only files in the provided list are scanned (never the full repo)
        - Line numbers are 1-based

        Returns:
            List of PlaceholderViolation (empty = no violations found)
        """

    def is_excluded(self, file_path: Path) -> bool:
        """Return True if this file should never be scanned."""

    @classmethod
    def from_config(cls, config: SentinelConfig) -> 'PlaceholderScanner':
        """Factory: merges built-in patterns with config patterns."""
```

## PlaceholderViolation

```python
@dataclass
class PlaceholderViolation:
    file_path: str          # Relative path from project root
    line_number: int        # 1-based
    matched_pattern: str    # The regex pattern string
    matched_text: str       # The actual matched text
    context_lines: list[str]  # ±2 surrounding lines
```

## Scan Behavior

| Input | Expected Output |
|-------|----------------|
| Production file with `# TODO: implement this` | One violation: file, line, pattern=`\bTODO\b` |
| Test file `tests/test_auth.py` with `# TODO` | No violation (excluded by path) |
| Mock file `__mocks__/auth.js` with `mock_user` | No violation (excluded by path) |
| File with `*.spec.ts` pattern with `stub_fn` | No violation (excluded by glob) |
| `fail_on_detect: false` config | Violations returned but caller treats as warning |
| File with `NotImplementedError` in `src/auth.py` | One violation |
| Clean file (no patterns) | Empty list |

## Built-in Excluded Paths (cannot be overridden to remove)

```python
ALWAYS_EXCLUDE = [
    'tests/',
    '__mocks__/',
    r'.*\.test\.py$',
    r'.*\.spec\.py$',
    r'.*\.test\.ts$',
    r'.*\.spec\.ts$',
    r'.*\.test\.js$',
    r'.*\.spec\.js$',
    r'.*\.test\.tsx$',
    r'.*\.spec\.tsx$',
]
```

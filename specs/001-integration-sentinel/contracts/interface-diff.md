# Contract: InterfaceDiff
**Module**: `cli/sentinel/interface_diff.py`
**Invoked by**: `SentinelRunner.run()` after micro-agent run completes

---

## Interface

```python
class InterfaceDiff:
    def compare(self, file_path: Path, pre_content: str, post_content: str) -> InterfaceChangeReport:
        """
        Compare public API surface between pre-run and post-run file content.

        Language is auto-detected from file extension:
          .py → Python AST (ast module)
          .ts, .tsx, .js, .jsx → TypeScript/JavaScript regex
          .rs → Rust regex

        Returns:
            InterfaceChangeReport for this file
        """

    @staticmethod
    def get_pre_content(file_path: str, git_ref: str = "HEAD") -> str:
        """Get file content at git ref. Returns '' if file didn't exist."""
```

## InterfaceChangeReport

```python
@dataclass
class InterfaceChangeReport:
    file_path: str
    language: str                   # "python" | "typescript" | "rust" | "unknown"
    breaking_changes: list[str]     # Removed or renamed public symbols
    non_breaking_changes: list[str] # Added public symbols
    modified_signatures: list[dict] # [{name, old_sig, new_sig}] — changed args/return type
    is_breaking: bool               # True if breaking_changes or modified_signatures non-empty
    detection_method: str           # "ast" | "regex" | "none"
```

## Detection Logic

### Python (.py)
```python
import ast

def _extract_python_symbols(content: str) -> dict:
    tree = ast.parse(content)
    functions = {}
    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                # First line of ast.unparse gives signature
                sig = ast.unparse(node).split('\n')[0]
                functions[node.name] = sig
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith('_'):
                classes[node.name] = [ast.unparse(b) for b in node.bases]
    return {'functions': functions, 'classes': classes}
```

### TypeScript/JavaScript (.ts, .tsx, .js, .jsx)
```python
TS_PATTERNS = [
    r'export\s+(?:async\s+)?function\s+(\w+)',
    r'export\s+const\s+(\w+)\s*=',
    r'export\s+(?:abstract\s+)?class\s+(\w+)',
    r'export\s+(?:default\s+)?interface\s+(\w+)',
    r'export\s+type\s+(\w+)',
]
```

### Rust (.rs)
```python
RUST_PATTERNS = [
    r'pub\s+(?:async\s+)?fn\s+(\w+)',
    r'pub\s+struct\s+(\w+)',
    r'pub\s+trait\s+(\w+)',
    r'pub\s+enum\s+(\w+)',
]
```

## Breaking Change Classification

| Change | Classification |
|--------|---------------|
| Function removed from public API | Breaking |
| Class removed | Breaking |
| Function signature changed (args, return type) | Breaking (Python AST) / Non-breaking (regex — signature not captured) |
| Function added | Non-breaking |
| Class added | Non-breaking |
| File extension not recognized | `detection_method="none"`, no changes detected |
| SyntaxError in Python file | `detection_method="none"`, no changes detected, warning logged |

## Invariants

1. Returns a valid `InterfaceChangeReport` for every file (never raises)
2. `is_breaking` is always derived from `breaking_changes` + `modified_signatures` being non-empty
3. For unknown file types: `breaking_changes=[]`, `non_breaking_changes=[]`, `is_breaking=False`

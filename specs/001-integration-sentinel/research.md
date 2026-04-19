# Research: Integration Sentinel
**Phase 0 Output** | Branch: `001-integration-sentinel` | Date: 2026-02-20

---

## Research Agents Dispatched

| Task | Topic | Status |
|------|-------|--------|
| ae75fe5 | micro-agent CLI flags, Ollama config, subprocess pattern | Complete |
| a94ef10 | dev-kid orchestrator injection points, data structures, config | Complete |
| a400911 | Python AST interface diffing, TypeScript/Rust regex, git patches | Complete |

---

## Decision 1: micro-agent CLI Invocation

### Decision
Use the `micro-agent` CLI's **run command** (`ma` alias) with `--objective`, `--test`, `--max-iterations`, `--simple`, and `--no-escalate` flags. Invoke as isolated subprocess via `subprocess.run()` with `capture_output=True, text=True, check=False`.

### Rationale
- The `run.ts` command is the active Ralph Loop 2026 implementation (not the legacy `cli.ts`)
- Exit codes are clean binary: 0 = success, 1 = failure
- `--simple N` limits to fast simple mode; `--no-escalate` prevents cloud escalation in Tier 1
- `check=False` allows graceful error handling without raising exceptions

### Alternatives Considered
- Importing micro-agent as a library: Not supported; it's a CLI-only tool
- Using `npx micro-agent`: Works but slower startup; prefer direct binary after install
- Using `--full` for Tier 1: Too expensive; Tier 1 must be fast local-only

### Exact Subprocess Invocation (Tier 1 — Ollama)
```python
result = subprocess.run(
    [
        'micro-agent',
        '--objective', f'Fix failing tests for task {task_id}',
        '--test', detected_test_command,
        '--max-iterations', '5',
        '--simple', '5',
        '--no-escalate',
        '--artisan', 'ollama:qwen3-coder:30b',
    ],
    cwd=task_working_dir,
    capture_output=True,
    text=True,
    timeout=300,        # 5 minutes per Tier 1 run
    env={**os.environ, 'OLLAMA_BASE_URL': 'http://192.168.0.159:11434'},
    check=False
)
```

### Exact Subprocess Invocation (Tier 2 — Cloud)
```python
result = subprocess.run(
    [
        'micro-agent',
        '--objective', f'Fix failing tests for task {task_id} (Tier 1 exhausted)',
        '--test', detected_test_command,
        '--max-iterations', '10',
        '--artisan', 'claude-sonnet-4-20250514',
        '--max-budget', '2.0',
        '--max-duration', '10',
    ],
    cwd=task_working_dir,
    capture_output=True,
    text=True,
    timeout=600,        # 10 minutes per Tier 2 run
    env={**os.environ, 'ANTHROPIC_API_KEY': api_key},
    check=False
)
```

### Output Parsing (Text-Based, No JSON)
```python
import re

def parse_micro_agent_output(stdout: str) -> dict:
    iterations = 0
    cost = 0.0
    duration = 0.0
    for line in stdout.splitlines():
        if 'Iterations:' in line and 'total' in line:
            m = re.search(r'(\d+)\s+total', line)
            if m: iterations = int(m.group(1))
        if 'Cost:' in line and 'total' in line:
            m = re.search(r'\$([0-9.]+)\s+total', line)
            if m: cost = float(m.group(1))
        if 'Duration:' in line:
            m = re.search(r'([0-9.]+)s', line)
            if m: duration = float(m.group(1))
    return {'iterations': iterations, 'cost': cost, 'duration': duration}
```

---

## Decision 2: Ollama Server Configuration

### Decision
Set `OLLAMA_BASE_URL=http://192.168.0.159:11434` in subprocess environment. No API key required. Use `qwen3-coder:30b` as Tier 1 model (confirmed available, 18.6GB MoE Q4_K_M, ~3.3B active params).

### Rationale
- `qwen3-coder:30b` is the newest Qwen3 generation, MoE architecture means only ~3.3B params active at inference — extremely fast for local
- 18.6GB fits comfortably in 56GB system RAM
- Ollama SDK in micro-agent reads `OLLAMA_BASE_URL` env var; no other config needed
- No API key is required for Ollama (confirmed in provider-router.ts: `return undefined`)

### Connectivity Check Pattern
```python
def check_ollama_available(base_url: str = 'http://192.168.0.159:11434') -> bool:
    try:
        result = subprocess.run(
            ['curl', '-sf', f'{base_url}/api/tags'],
            capture_output=True, timeout=5, check=False
        )
        return result.returncode == 0
    except Exception:
        return False
```

### Fallback Strategy
If Ollama unreachable at sentinel start: skip Tier 1, log warning to manifest, proceed directly to Tier 2. This satisfies spec edge case: "Tier 1 is skipped with a warning logged to the manifest; Tier 2 runs immediately."

---

## Decision 3: Sentinel Task Injection Architecture

### Decision
Inject sentinel tasks directly into `execution_plan.json` **after orchestrator.py generates the plan** and **before wave_executor.py runs**. Sentinel tasks get `agent_role: "Sentinel"` and a unique `task_id` prefix `SENTINEL-`. Corresponding `- [ ] SENTINEL-XXX: ...` entries are appended to `tasks.md` so checkpoint verification passes.

### Rationale
- Orchestrator renumbers all tasks to T001, T002... — injecting pre-orchestration is destructive
- Post-orchestration injection preserves wave structure and task IDs
- `agent_role: "Sentinel"` provides clean routing hook in wave_executor.py
- Tasks MUST exist in tasks.md or `verify_wave_completion()` halts execution (confirmed in executor research)
- This pattern requires zero changes to orchestrator.py internals

### Injection Point in Wave Executor
```python
# In wave_executor.py execute_wave():
def execute_task(self, task: Dict) -> None:
    if task.get("agent_role") == "Sentinel":
        self._execute_sentinel_task(task)
        return
    # ... existing watchdog registration code ...
```

### CRITICAL: tasks.md Sync Requirement
For every `SENTINEL-XXX` task in `execution_plan.json`, a matching line MUST be added:
```markdown
- [ ] SENTINEL-T001: Sentinel validation for task T001
```
This must be done atomically with the execution_plan.json injection, before wave execution begins.

### Injection Code Pattern
```python
def inject_sentinel_tasks(plan_path: str, tasks_md_path: str) -> None:
    with open(plan_path) as f:
        plan = json.load(f)

    new_waves = []
    sentinel_tasks_md = []

    for wave in plan['execution_plan']['waves']:
        new_tasks = []
        for task in wave['tasks']:
            new_tasks.append(task)
            # Inject sentinel after each regular task
            sentinel_id = f"SENTINEL-{task['task_id']}"
            sentinel_task = {
                "task_id": sentinel_id,
                "agent_role": "Sentinel",
                "instruction": f"Run sentinel validation for {task['task_id']}: test loop, placeholder scan, manifest write",
                "file_locks": task.get("file_locks", []),
                "constitution_rules": [],
                "completion_handshake": f"Upon completion, mark {sentinel_id} [x] in tasks.md",
                "dependencies": [task['task_id']]
            }
            new_tasks.append(sentinel_task)
            sentinel_tasks_md.append(
                f"- [ ] {sentinel_id}: Sentinel validation for {task['task_id']}"
            )
        wave['tasks'] = new_tasks
        new_waves.append(wave)

    plan['execution_plan']['waves'] = new_waves
    with open(plan_path, 'w') as f:
        json.dump(plan, f, indent=2)

    # Append sentinel tasks to tasks.md
    with open(tasks_md_path, 'a') as f:
        f.write('\n<!-- Sentinel tasks (auto-generated) -->\n')
        f.write('\n'.join(sentinel_tasks_md) + '\n')
```

---

## Decision 4: Test Framework Auto-Detection

### Decision
Detect test framework by scanning the task's working directory for standard manifest files. Priority order: `pyproject.toml` / `setup.py` → pytest; `package.json` with jest/vitest → Jest/Vitest; `Cargo.toml` → cargo test. Fall back to the project root if task has no dedicated working directory.

### Detection Code
```python
def detect_test_command(working_dir: Path) -> Optional[str]:
    # Python: pytest
    if (working_dir / 'pyproject.toml').exists() or (working_dir / 'setup.py').exists():
        return 'python -m pytest'

    # JavaScript: check package.json
    pkg_json = working_dir / 'package.json'
    if pkg_json.exists():
        import json
        pkg = json.loads(pkg_json.read_text())
        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
        scripts = pkg.get('scripts', {})
        if 'vitest' in deps:
            return 'npx vitest run'
        if 'jest' in deps:
            return scripts.get('test', 'npx jest')
        if 'test' in scripts:
            return f"npm test"

    # Rust: cargo
    if (working_dir / 'Cargo.toml').exists():
        return 'cargo test'

    return None  # No framework detected; sentinel skips test loop
```

### No Test Framework Fallback
Per spec edge case: "Sentinel logs a warning, skips the test loop, runs placeholder scan only, and proceeds."

---

## Decision 5: Interface Stability Diffing

### Decision
Use Python `ast` module for Python files, regex patterns for TypeScript/JavaScript and Rust. Compare function signatures before and after micro-agent run using `git show HEAD:{file}` for the pre-run snapshot and direct file read for the post-run state.

### Python AST Approach
```python
import ast
import subprocess
from pathlib import Path

def extract_python_interfaces(content: str) -> dict:
    """Extract public function/class signatures from Python source."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {'functions': [], 'classes': []}

    functions = []
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith('_'):
                sig = ast.unparse(node).split('\n')[0]  # first line only
                functions.append({'name': node.name, 'signature': sig})
        elif isinstance(node, ast.ClassDef):
            if not node.name.startswith('_'):
                classes.append({'name': node.name, 'bases': [ast.unparse(b) for b in node.bases]})
    return {'functions': functions, 'classes': classes}

def get_pre_run_content(file_path: str) -> str:
    """Get file content before micro-agent modified it (HEAD state)."""
    result = subprocess.run(
        ['git', 'show', f'HEAD:{file_path}'],
        capture_output=True, text=True
    )
    return result.stdout if result.returncode == 0 else ''
```

### TypeScript Detection (Regex)
```python
TS_EXPORT_PATTERNS = [
    r'export\s+(?:async\s+)?function\s+(\w+)\s*\(',
    r'export\s+const\s+(\w+)\s*=\s*(?:async\s+)?\(',
    r'export\s+(?:abstract\s+)?class\s+(\w+)',
    r'export\s+(?:default\s+)?interface\s+(\w+)',
]
```

### Rust Detection (Regex)
```python
RUST_PUB_PATTERNS = [
    r'pub\s+(?:async\s+)?fn\s+(\w+)\s*\(',
    r'pub\s+struct\s+(\w+)',
    r'pub\s+trait\s+(\w+)',
    r'pub\s+enum\s+(\w+)',
]
```

### Interface Change Classification
```python
def classify_interface_change(pre: dict, post: dict) -> dict:
    """Determine if interface change triggers cascade."""
    pre_names = {f['name'] for f in pre.get('functions', [])}
    post_names = {f['name'] for f in post.get('functions', [])}

    return {
        'removed': list(pre_names - post_names),      # Breaking
        'added': list(post_names - pre_names),        # Non-breaking
        'changed': [],   # Would need arg comparison for full detection
        'is_breaking': bool(pre_names - post_names)
    }
```

---

## Decision 6: Git Patch Capture

### Decision
Capture exact diff after micro-agent run using `git diff HEAD -- <files>` (unstaged changes) written to `diff.patch`. For committed changes, use `git diff HEAD~1 HEAD`.

### Pattern
```python
def capture_diff_patch(output_path: Path, files: list[str]) -> bool:
    cmd = ['git', 'diff', 'HEAD', '--'] + files
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.stdout:
        output_path.write_text(result.stdout)
        return True
    return False
```

---

## Decision 7: Change Manifest Schema

### Decision
Manifest lives at `.claude/sentinel/<TASK-ID>/manifest.json` (structured), `diff.patch` (exact diff), and `summary.md` (human-readable injection text). Always written regardless of pass/fail.

### manifest.json Schema
```json
{
  "task_id": "T003",
  "sentinel_id": "SENTINEL-T003",
  "result": "PASS|FAIL|ERROR",
  "timestamp": "2026-02-20T14:32:00Z",
  "tier_used": 1,
  "tiers": {
    "tier1": {
      "attempted": true,
      "iterations": 3,
      "cost_usd": 0.0,
      "duration_sec": 45.2,
      "final_status": "PASS"
    },
    "tier2": {
      "attempted": false,
      "reason": "tier1_succeeded"
    }
  },
  "placeholder_violations": [],
  "files_changed": [
    {"path": "src/auth.py", "lines_added": 12, "lines_removed": 3}
  ],
  "interface_changes": {
    "breaking": [],
    "non_breaking": ["add_user"]
  },
  "tests_fixed": ["test_auth_login", "test_auth_logout"],
  "tests_still_failing": [],
  "fix_reason": "Added missing return statement in authenticate()",
  "cascade_triggered": false,
  "radius": {
    "files_changed": 1,
    "lines_changed": 15,
    "budget_exceeded": false
  }
}
```

---

## Decision 8: Config Schema Extension

### Decision
Add `sentinel` section to `dev-kid.yml` / `ConfigSchema` dataclass. Defaults match spec requirements (enabled, auto cascade, Tier 1 = local Ollama).

### New Config Fields
```python
# ConfigSchema additions:
sentinel_enabled: bool = True
sentinel_mode: str = "auto"         # "auto" | "human-gated"
sentinel_tier1_model: str = "qwen3-coder:30b"
sentinel_tier1_ollama_url: str = "http://192.168.0.159:11434"
sentinel_tier1_max_iterations: int = 5
sentinel_tier2_model: str = "claude-sonnet-4-20250514"
sentinel_tier2_max_iterations: int = 10
sentinel_tier2_max_budget: float = 2.0
sentinel_radius_max_files: int = 3
sentinel_radius_max_lines: int = 150
sentinel_radius_allow_interface_changes: bool = False
sentinel_placeholder_fail_on_detect: bool = True
sentinel_placeholder_patterns: list = ["TODO", "FIXME", "HACK", "NotImplementedError", r"mock_\w+", r"stub_\w+", "PLACEHOLDER", "pass  # implement"]
sentinel_placeholder_exclude_paths: list = ["tests/", "__mocks__/", "*.test.*", "*.spec.*"]
```

### dev-kid.yml Example
```yaml
sentinel:
  enabled: true
  mode: auto   # auto | human-gated
  tier1:
    model: qwen3-coder:30b
    ollama_url: http://192.168.0.159:11434
    max_iterations: 5
  tier2:
    model: claude-sonnet-4-20250514
    max_iterations: 10
    max_budget_usd: 2.0
  change_radius:
    max_files: 3
    max_lines: 150
    allow_interface_changes: false
  placeholder:
    fail_on_detect: true
    patterns:
      - "TODO"
      - "FIXME"
      - "NotImplementedError"
      - "mock_\\w+"
      - "stub_\\w+"
    exclude_paths:
      - "tests/"
      - "__mocks__/"
      - "*.test.*"
      - "*.spec.*"
```

---

## Resolved Clarifications

| Topic | Resolved To | Source |
|-------|-------------|--------|
| micro-agent CLI binary | `micro-agent` (run command, dist/cli.mjs) | ae75fe5 |
| Ollama config mechanism | `OLLAMA_BASE_URL` env var, no API key | ae75fe5 |
| micro-agent exit codes | 0 = pass, 1 = fail (binary only) | ae75fe5 |
| Injection point | Post-orchestration execution_plan.json + tasks.md sync | a94ef10 |
| Task ID format | Sentinel prefix: `SENTINEL-T001` | a94ef10 |
| tasks.md sync required | Yes — checkpoint verification requires matching [x] entries | a94ef10 |
| Python interface detection | `ast.parse()` + `ast.walk()` + `ast.unparse()` | a400911 |
| TypeScript/Rust detection | Regex on `export function/class/interface` and `pub fn/struct/trait` | a400911 |
| Patch capture | `git diff HEAD -- <files>` → `diff.patch` | a400911 |
| Config extension | New `sentinel` block in ConfigSchema dataclass + to_dict/from_dict | a94ef10 |

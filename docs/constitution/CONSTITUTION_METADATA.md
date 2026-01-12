# Constitution Metadata Feature

## Overview

The orchestrator now supports **constitution metadata** in tasks.md. Constitution rules are AI-enforced behavioral constraints that guide agent execution during task completion.

## Feature Implementation

### Task Dataclass Extension

The `Task` dataclass in `orchestrator.py` now includes:

```python
@dataclass
class Task:
    id: str
    description: str
    agent_role: str = "Developer"
    file_locks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    constitution_rules: List[str] = field(default_factory=list)  # NEW
    completed: bool = False
```

### Extraction Logic

**Location**: `cli/orchestrator.py` → `_process_task()` method (lines 91-97)

**Regex Pattern**: `r'- \*\*Constitution\*\*: (.+)'`

**Implementation**:
```python
# Extract constitution rules from subsequent lines
constitution_rules = []
full_text = '\n'.join(task_lines)
constitution_match = re.search(r'- \*\*Constitution\*\*: (.+)', full_text, re.MULTILINE)
if constitution_match:
    rules_str = constitution_match.group(1)
    constitution_rules = [r.strip() for r in rules_str.split(',')]
```

### Execution Plan Integration

Constitution rules are now included in `execution_plan.json`:

```json
{
  "task_id": "T001",
  "agent_role": "Developer",
  "instruction": "Task description",
  "file_locks": ["file.py"],
  "constitution_rules": ["no-shortcuts", "verify-implementation"],  // NEW
  "completion_handshake": "...",
  "dependencies": []
}
```

## Usage in tasks.md

### Basic Syntax

```markdown
- [ ] Task description
  - **Constitution**: rule1, rule2, rule3
```

### Examples

**Example 1: Code Quality Rules**
```markdown
- [ ] Implement user authentication in `auth.py`
  - **Constitution**: write-tests-first, verify-edge-cases, run-linter
```

**Example 2: Security-Focused Task**
```markdown
- [ ] Add password reset functionality
  - **Constitution**: security-audit, no-plaintext-passwords, rate-limit-checks
```

**Example 3: Performance Optimization**
```markdown
- [ ] Optimize database query performance
  - **Constitution**: benchmark-before-after, maintain-accuracy, document-changes
```

### Multiple Tasks with Different Constitutions

```markdown
- [ ] Task 1: Quick prototype
  - **Constitution**: move-fast, iterate-quickly

- [ ] Task 2: Production-critical bug fix
  - **Constitution**: test-thoroughly, verify-rollback, monitor-metrics

- [ ] Task 3: Documentation update
  - **Constitution**: clarity-first, include-examples
```

## Behavior & Edge Cases

### Tested Scenarios

| Scenario | Behavior | Example |
|----------|----------|---------|
| Multiple rules | Extracted as array | `rule1, rule2, rule3` → `["rule1", "rule2", "rule3"]` |
| Single rule | Extracted as 1-element array | `single-rule` → `["single-rule"]` |
| Rules with spaces | Trimmed correctly | `rule, rule two with spaces` → `["rule", "rule two with spaces"]` |
| No constitution | Empty array | (none) → `[]` |
| Empty value | Empty array | `- **Constitution**:` → `[]` |
| Completed task `[x]` | Still extracted | Works normally |

### Test Coverage

Run unit tests with:
```bash
python3 cli/test_constitution_extraction.py
```

**Test Suite**:
- `test_basic_constitution_extraction()` - Multiple rules
- `test_single_constitution_rule()` - Single rule
- `test_constitution_with_spaces()` - Space handling
- `test_no_constitution_metadata()` - Missing metadata
- `test_empty_constitution()` - Empty value
- `test_completed_task_with_constitution()` - Completed tasks
- `test_constitution_in_execution_plan()` - JSON output
- `test_multiple_tasks_mixed_constitutions()` - Mixed configurations

## Integration with Wave Executor

The wave executor (`wave_executor.py`) will read `constitution_rules` from the execution plan and enforce them during task execution. Future implementation will include:

1. **Pre-execution validation**: Check if constitution rules are recognized
2. **Mid-execution monitoring**: Verify compliance during task execution
3. **Post-execution verification**: Confirm all rules were followed

## Constitution Rule Catalog

### Recommended Rules

**Code Quality**:
- `write-tests-first` - TDD approach
- `verify-edge-cases` - Test boundary conditions
- `run-linter` - Static analysis before commit
- `document-changes` - Update docs with code

**Security**:
- `security-audit` - Manual security review
- `no-plaintext-passwords` - Encryption required
- `rate-limit-checks` - Prevent abuse
- `audit-logging` - Track sensitive operations

**Performance**:
- `benchmark-before-after` - Measure impact
- `maintain-accuracy` - No correctness regression
- `profile-hotspots` - Identify bottlenecks

**Process**:
- `no-shortcuts` - Follow full implementation
- `verify-implementation` - Validate against spec
- `test-before-commit` - All tests pass
- `run-real-tests` - Integration tests, not just unit

## File Locations

| File | Purpose |
|------|---------|
| `cli/orchestrator.py` | Constitution extraction logic |
| `cli/test_constitution_extraction.py` | Unit tests |
| `CONSTITUTION_METADATA.md` | This documentation |
| `execution_plan.json` | Output with constitution_rules |

## Dependencies

**SPECKIT-004** depends on:
- ✅ SPECKIT-001: Task dataclass with constitution_rules field

**Future Dependencies**:
- SPECKIT-005: Wave executor enforcement logic
- SPECKIT-006: Constitution rule validation

## Implementation Status

- ✅ Task dataclass extended with `constitution_rules`
- ✅ Regex extraction implemented in `_process_task()`
- ✅ Execution plan JSON includes `constitution_rules`
- ✅ Unit tests for all edge cases
- ✅ Documentation complete
- ⬜ Wave executor enforcement (future)
- ⬜ Rule validation system (future)

## Completion Handshake

**SPECKIT-004**: Constitution metadata extraction is now complete. The parse_task() function extracts constitution rules using regex pattern `r'- \*\*Constitution\*\*: (.+)'` and stores them in `task.constitution_rules` list. All tests pass.

# Data Model: Integration Sentinel
**Phase 1 Output** | Branch: `001-integration-sentinel` | Date: 2026-02-20

---

## Entities

### 1. SentinelTask
A plan-injected task of type `"Sentinel"` that runs the full sentinel pipeline as an isolated subprocess after its parent developer task completes.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string | Format: `SENTINEL-<parent_task_id>` (e.g., `SENTINEL-T003`) |
| `agent_role` | string | Always `"Sentinel"` |
| `instruction` | string | Human-readable sentinel objective |
| `file_locks` | string[] | Same file locks as parent task (inherits to prevent wave conflicts) |
| `constitution_rules` | string[] | Always `[]` (sentinel self-governs) |
| `completion_handshake` | string | Instructions to mark `[x]` in tasks.md on completion |
| `dependencies` | string[] | Always contains parent task_id |
| `parent_task_id` | string | ID of the developer task this sentinel validates |

**Relationships**:
- One SentinelTask per developer Task (1:1)
- SentinelTask depends on its parent developer Task (always in same wave, sequential)
- SentinelTask produces exactly one ChangeManifest

**State Transitions**:
```
PENDING → IN_PROGRESS → PASSED (manifest written, checkpoint proceeds)
                     → FAILED (manifest written, wave halts)
                     → ERROR (manifest written with result=ERROR, wave halts)
```

---

### 2. ChangeManifest
The structured artifact of every sentinel run. Always written regardless of pass or fail. Lives in `.claude/sentinel/<TASK-ID>/`.

**manifest.json Schema**:
```json
{
  "task_id": "T003",
  "sentinel_id": "SENTINEL-T003",
  "result": "PASS",
  "timestamp": "2026-02-20T14:32:00Z",
  "tier_used": 1,
  "tiers": {
    "tier1": {
      "attempted": true,
      "ollama_url": "http://192.168.0.159:11434",
      "model": "qwen3-coder:30b",
      "iterations": 3,
      "cost_usd": 0.0,
      "duration_sec": 45.2,
      "final_status": "PASS",
      "error_messages": []
    },
    "tier2": {
      "attempted": false,
      "reason": "tier1_succeeded",
      "model": null,
      "iterations": 0,
      "cost_usd": 0.0,
      "duration_sec": 0.0,
      "final_status": null,
      "error_messages": []
    }
  },
  "placeholder_violations": [],
  "files_changed": [
    {
      "path": "src/auth.py",
      "lines_added": 12,
      "lines_removed": 3,
      "net_change": 9
    }
  ],
  "interface_changes": {
    "breaking": [],
    "non_breaking": ["add_user"],
    "is_breaking": false
  },
  "tests_fixed": ["test_auth_login", "test_auth_logout"],
  "tests_still_failing": [],
  "fix_reason": "Added missing return statement in authenticate()",
  "cascade_triggered": false,
  "cascade_tasks_annotated": [],
  "radius": {
    "files_changed_count": 1,
    "lines_changed_total": 15,
    "interface_changes_count": 1,
    "budget_files": 3,
    "budget_lines": 150,
    "budget_exceeded": false
  }
}
```

**Files** (all in `.claude/sentinel/<TASK-ID>/`):
| File | Format | Purpose |
|------|--------|---------|
| `manifest.json` | JSON | Structured result data |
| `diff.patch` | Unified diff | Exact code changes (empty if no changes) |
| `summary.md` | Markdown | Human-readable injection text for next task context |

**Relationships**:
- One ChangeManifest per SentinelTask (1:1)
- ChangeManifest.summary.md is injected into next task agent context

---

### 3. PlaceholderViolation
A detected occurrence of a forbidden pattern in production code (not test files). Blocks the checkpoint when `fail_on_detect: true`.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Relative path from project root |
| `line_number` | int | 1-based line number |
| `matched_pattern` | string | The regex/string pattern that matched |
| `matched_text` | string | The actual text that matched |
| `context` | string | ±2 lines of surrounding context |

**Built-in Patterns** (configurable):
```python
DEFAULT_PATTERNS = [
    r'\bTODO\b',
    r'\bFIXME\b',
    r'\bHACK\b',
    r'\bXXX\b',
    r'\bNOTIMPLEMENTED\b',
    r'\bNotImplementedError\b',
    r'\bmock_\w+',
    r'\bstub_\w+',
    r'\bPLACEHOLDER\b',
    r'MOCK_\w+',
    r'return None  # (implement|TODO)',
    r'raise NotImplementedError',
    r'pass  # (implement|TODO|stub)',
]
```

**Excluded Paths** (never flagged):
```python
DEFAULT_EXCLUDES = [
    'tests/',
    '__mocks__/',
    '*.test.py',
    '*.spec.py',
    '*.test.ts',
    '*.spec.ts',
    '*.test.js',
    '*.spec.js',
]
```

**Relationships**:
- Zero or more PlaceholderViolations detected per SentinelTask run
- Violations stored in `ChangeManifest.placeholder_violations[]`

---

### 4. ChangeRadius
The three-axis budget that determines whether sentinel's fixes are minor (proceed) or architectural (trigger cascade).

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `files_changed_count` | int | — | Number of distinct files modified |
| `lines_changed_total` | int | — | Sum of added + removed lines across all files |
| `interface_changes_count` | int | — | Number of public API surface changes detected |
| `budget_files` | int | 3 | Configurable max file count |
| `budget_lines` | int | 150 | Configurable max line count |
| `allow_interface_changes` | bool | false | Whether interface changes trigger cascade |
| `cross_wave_files` | string[] | [] | Files owned by tasks in different waves |
| `budget_exceeded` | bool | — | True if any axis exceeds budget |
| `violations` | string[] | [] | Which axes exceeded: `["files", "lines", "interface", "cross_wave"]` |

**Budget Exceeded Conditions** (any one triggers cascade):
1. `files_changed_count > budget_files`
2. `lines_changed_total > budget_lines`
3. `interface_changes_count > 0` AND `allow_interface_changes == false`
4. Any modified file is in `cross_wave_files` (owned by a different wave's tasks)

---

### 5. CascadeAnnotation
A compatibility warning appended to a pending task's description when sentinel's changes exceed the radius budget.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `target_task_id` | string | Task whose description receives the warning |
| `sentinel_id` | string | Sentinel that triggered the cascade |
| `changed_files` | string[] | Files sentinel modified that the target task may depend on |
| `interface_changes` | string[] | Interface names that changed |
| `warning_text` | string | Markdown annotation appended to task description |
| `applied_at` | string | ISO 8601 timestamp |

**Warning Text Format** (appended to tasks.md task line):
```markdown
  > **[SENTINEL CASCADE WARNING - 2026-02-20T14:32:00Z]**
  > Sentinel for T003 modified: `src/auth.py` (interface change: `authenticate()` signature changed).
  > Verify your implementation against the updated interface before marking complete.
  > See: `.claude/sentinel/SENTINEL-T003/summary.md`
```

**Relationships**:
- One CascadeAnnotation per affected pending task per sentinel run (N:1 sentinel → cascade, 1:N cascade → affected tasks)

---

### 6. SentinelConfig
Runtime configuration for all sentinel behavior. Loaded from `dev-kid.yml` via `ConfigSchema`.

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | `true` | Toggle sentinel globally |
| `mode` | string | `"auto"` | `"auto"` \| `"human-gated"` |
| `tier1.model` | string | `"qwen3-coder:30b"` | Ollama model for Tier 1 |
| `tier1.ollama_url` | string | `"http://192.168.0.159:11434"` | Ollama server URL |
| `tier1.max_iterations` | int | 5 | Max Tier 1 micro-agent cycles |
| `tier2.model` | string | `"claude-sonnet-4-20250514"` | Cloud model for Tier 2 |
| `tier2.max_iterations` | int | 10 | Max Tier 2 micro-agent cycles |
| `tier2.max_budget_usd` | float | 2.0 | Cost ceiling for Tier 2 |
| `radius.max_files` | int | 3 | File count budget axis |
| `radius.max_lines` | int | 150 | Line count budget axis |
| `radius.allow_interface_changes` | bool | `false` | Interface changes trigger cascade |
| `placeholder.fail_on_detect` | bool | `true` | Block checkpoint on placeholder found |
| `placeholder.patterns` | string[] | (built-in list) | Additional patterns to detect |
| `placeholder.exclude_paths` | string[] | (built-in list) | Paths to skip |

---

## State Transitions

```
Wave N begins
    ↓
Task T003 executes (agent marks [x] in tasks.md)
    ↓
SENTINEL-T003 begins
    ├── Placeholder scan → violations? → FAIL (if fail_on_detect)
    ├── Test detection → framework found?
    │   ├── NO → skip test loop, scan-only
    │   └── YES → Tier 1 loop (≤5 iterations)
    │       ├── PASS → write manifest (PASS), proceed
    │       └── FAIL → Tier 2 loop (≤10 iterations)
    │           ├── PASS → write manifest (PASS), proceed
    │           └── FAIL → write manifest (FAIL), HALT wave
    ├── Radius check → budget exceeded?
    │   ├── NO → proceed to checkpoint
    │   └── YES → Cascade analysis
    │       ├── mode=auto → annotate pending tasks, proceed
    │       └── mode=human-gated → pause, present diff, await approval
    └── Manifest written → summary.md injected via UserPromptSubmit hook
    ↓
SENTINEL-T003 marks [x] in tasks.md
    ↓
Checkpoint proceeds (git commit)
```

---

## Validation Rules

1. `manifest.result` MUST be set to `PASS`, `FAIL`, or `ERROR` — never omitted
2. `diff.patch` MUST exist even if empty (zero-byte file signals "no changes")
3. `summary.md` MUST exist and contain at minimum the result line
4. A SentinelTask MUST have a matching `- [ ] SENTINEL-XXX: ...` line in `tasks.md` at injection time
5. PlaceholderViolations in test directories (`tests/`, `__mocks__/`, `*.test.*`) MUST NOT be reported
6. Tier 2 MUST NOT activate unless Tier 1 completes its maximum iterations with a non-zero exit code
7. CascadeAnnotations MUST only target tasks with status `pending` (not `[x]` completed tasks)

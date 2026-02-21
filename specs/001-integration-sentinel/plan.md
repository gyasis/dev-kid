# Implementation Plan: Integration Sentinel

**Branch**: `001-integration-sentinel` | **Date**: 2026-02-20 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-integration-sentinel/spec.md`

## Summary

Integration Sentinel adds a per-task micro-agent test-and-fix loop to dev-kid's wave execution pipeline. After each task completes (`[x]` in tasks.md), a `SENTINEL-*` task runs as an isolated subprocess invoking micro-agent with a tiered model strategy: Tier 1 uses local Ollama `qwen3-coder:30b` for fast iteration (≤5 cycles), Tier 2 escalates to cloud `claude-sonnet-4-20250514` only if Tier 1 fails. A Change Manifest (manifest.json + diff.patch + summary.md) is always written to `.claude/sentinel/<TASK-ID>/` and injected into the next task agent's context via the existing `UserPromptSubmit` hook. Sentinel tasks are injected into `execution_plan.json` post-orchestration; cascading architectural warnings auto-annotate pending tasks when changes exceed a configurable radius budget.

## Technical Context

**Language/Version**: Python 3.11 (existing dev-kid codebase), Node.js 20+ (micro-agent runtime)
**Primary Dependencies**: micro-agent CLI (`@builder.io/micro-agent`), Ollama SDK (internal to micro-agent), Python `ast` stdlib, `subprocess`, `json`, `pathlib`, `re`
**Storage**: `.claude/sentinel/<TASK-ID>/` directory tree (flat files: manifest.json, diff.patch, summary.md); dev-kid.yml for config; execution_plan.json for plan injection
**Testing**: pytest (Python sentinel modules), integration tests against fixture execution plans
**Target Platform**: Linux server (Ubuntu 22.04+), same environment as dev-kid
**Project Type**: Single project (extends existing dev-kid cli/ Python modules)
**Performance Goals**: Tier 1 only (tests near-passing) adds ≤3 minutes per task overhead (SC-005); Tier 1 process timeout 300s, Tier 2 timeout 600s
**Constraints**: ≤3 files, ≤150 lines default radius budget; Ollama server reachability checked before each Tier 1 run; no shared context between micro-agent subprocess and main session
**Scale/Scope**: Per-task (each task in execution_plan.json gets one sentinel); number of sentinels = number of tasks in wave plan

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

No project constitution file exists at `memory-bank/shared/.constitution.md` (template only). Applying dev-kid's own architectural principles from CLAUDE.md and systemPatterns.md:

| Gate | Status | Evidence |
|------|--------|---------|
| **No silent failures** | PASS | Manifest always written (pass AND fail); ERROR result type for crashes |
| **Verification-gated progression** | PASS | Sentinel tasks require [x] in tasks.md same as regular tasks; checkpoint blocks if absent |
| **Subprocess isolation** | PASS | micro-agent runs as isolated subprocess, no shared context with session |
| **Git-centric checkpoints** | PASS | Sentinel runs before checkpoint commit; manifest committed alongside wave |
| **Idempotent operations** | PASS | Sentinel re-run safe; manifest overwritten, not appended |
| **Zero external dependencies** (stdlib only) | CONDITIONAL | Sentinel Python module uses only stdlib; micro-agent is pre-existing dependency declared in spec |
| **O(n²) or better complexity** | PASS | Sentinel injection is O(n) over task list |
| **Fail-safe** | PASS | On Tier 2 exhaustion: wave halts with manifest record, no checkpoint created |

**Post-design re-check**: No new violations introduced in Phase 1 design. Complexity justified: micro-agent is the agreed external dependency (already in use in micro-agent project); no new architectural patterns required beyond existing subprocess + file I/O.

## Project Structure

### Documentation (this feature)

```text
specs/001-integration-sentinel/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output ✓
├── data-model.md        # Phase 1 output ✓
├── quickstart.md        # Phase 1 output ✓
├── contracts/           # Phase 1 output ✓
│   ├── sentinel-runner.md
│   ├── placeholder-scanner.md
│   ├── change-manifest.md
│   ├── interface-diff.md
│   └── config-schema.md
└── tasks.md             # Phase 2 output (/speckit.tasks — not created by /speckit.plan)
```

### Source Code (repository root)

```text
cli/
├── orchestrator.py          # MODIFY: add --sentinel flag, post-inject sentinels
├── wave_executor.py         # MODIFY: route agent_role=="Sentinel" to sentinel handler
├── config_manager.py        # MODIFY: add sentinel block to ConfigSchema
└── sentinel/                # NEW: sentinel subsystem
    ├── __init__.py
    ├── runner.py            # SentinelRunner: orchestrates full sentinel pipeline
    ├── placeholder_scanner.py  # PlaceholderScanner: detect forbidden patterns
    ├── interface_diff.py    # InterfaceDiff: Python AST + TS/Rust regex diffing
    ├── manifest_writer.py   # ManifestWriter: write manifest.json + diff.patch + summary.md
    ├── cascade_analyzer.py  # CascadeAnalyzer: detect impact, annotate tasks
    └── tier_runner.py       # TierRunner: manage Tier 1/Tier 2 micro-agent subprocess calls

tests/
├── unit/
│   └── sentinel/
│       ├── test_placeholder_scanner.py
│       ├── test_interface_diff.py
│       ├── test_manifest_writer.py
│       ├── test_cascade_analyzer.py
│       └── test_tier_runner.py
├── integration/
│   └── sentinel/
│       ├── test_sentinel_runner.py          # Full pipeline on fixture task
│       ├── test_injection_round_trip.py     # Plan inject → verify tasks.md sync
│       └── fixtures/
│           ├── execution_plan_simple.json
│           ├── tasks_with_placeholder.py
│           └── tasks_clean.py
└── contract/
    └── sentinel/
        └── test_manifest_schema.py          # Validate manifest.json schema

.claude/
└── sentinel/                # Runtime output (gitignored individually, committed via wave checkpoint)
    └── <TASK-ID>/
        ├── manifest.json
        ├── diff.patch
        └── summary.md
```

**Structure Decision**: Single project (Option 1). Integration Sentinel is a subsystem inside existing `cli/` Python package. New code lives in `cli/sentinel/` subpackage. No new top-level directories. Test structure mirrors source. Runtime output in `.claude/sentinel/` follows existing `.claude/` conventions.

## Complexity Tracking

No constitution violations requiring justification. All design decisions stay within existing dev-kid architectural patterns.

| Potential Concern | Resolution |
|-------------------|-----------|
| External subprocess (micro-agent) | Pre-existing declared dependency; spec explicitly requires it |
| `.claude/sentinel/` runtime directory | Follows existing `.claude/` convention; no new storage layer |
| New Python subpackage `cli/sentinel/` | 6 modules, single responsibility each; justified by feature scope |

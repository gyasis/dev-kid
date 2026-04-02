---
name: devkid.sentinel-status
description: Show sentinel run history — task results, tiers used, costs, pass/fail/skip status
---

# Dev-Kid Sentinel Status

Shows the history of sentinel validation runs with results per task.

## What This Does

1. Reads all sentinel manifests from `.claude/sentinel/`
2. Displays ASCII table with: task ID, tier used, iterations, files changed, result, cost
3. Shows PASS, FAIL, SKIP, and ERROR results distinctly

## Usage

```bash
/devkid.sentinel-status
```

## Execution

```bash
#!/bin/bash
set -e

echo "🛡️  Sentinel Run History"
echo ""
dev-kid sentinel-status
```

## Example Output

```
 Task     | Tier          | Iter | Files | Result | Cost
----------|---------------|------|-------|--------|-------
 T001     | local-quick   |    3 |     2 | PASS   | $0.00
 T002     | azure-budget  |    5 |     1 | PASS   | $0.12
 T003     | -             |    0 |     0 | SKIP   | $0.00
 T004     | azure-mid     |    8 |     3 | FAIL   | $0.45
```

## When To Use

- After `/devkid.execute` — review what sentinel found
- When investigating test failures
- To check cost of sentinel runs
- To see which tasks were SKIPped (no test command or provider unavailable)

## Result Meanings

| Result | Meaning |
|--------|---------|
| PASS   | Tests passed (micro-agent fixed any issues) |
| FAIL   | All tiers exhausted, tests still failing — manual fix needed |
| SKIP   | No test command found, task not testable yet, or no providers available |
| ERROR  | Sentinel infrastructure error (non-fatal, wave continued) |

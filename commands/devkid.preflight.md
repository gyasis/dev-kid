---
name: devkid.preflight
description: Run dev-kid sentinel-health preflight check (provider readiness, .env sourcing, no execute)
---

# Dev-Kid Preflight

Standalone preflight check — verifies sentinel provider readiness without running any wave executor. Use this to confirm your project is ready BEFORE invoking `/devkid.execute` for the first time.

## What This Does

1. Auto-sources `.env` from project root if present (most commonly a symlink to `~/dev/.env` or similar)
2. Runs `dev-kid sentinel-health` to check provider status (Ollama / Anthropic / Google / OpenAI)
3. Reports tier readiness count (e.g. `8/8 tiers ready`) and lists any missing API keys
4. Exits 0 if all providers ready, exit 1 if any missing
5. Does NOT invoke wave executor — purely a check

For the full preflight + execute flow, use `/devkid.execute` (preflight is built in there).

## Usage

```bash
/devkid.preflight
```

## Execution

```bash
#!/bin/bash
set -e

if ! command -v dev-kid &>/dev/null; then
    echo "❌ dev-kid CLI not on PATH. Install dev-kid first."
    exit 2
fi

dev-kid preflight
```

## Output Example

```
===============================================
  dev-kid Preflight: provider readiness check
===============================================
  Tiers ready : 8/8
  Missing keys: (none)
  Mode        : preflight only (no execute)
===============================================

✅ All providers ready
```

## When to Use

- **First-time project setup**: confirm everything is wired before `/devkid.execute`
- **After modifying `.env`**: verify new keys are picked up
- **CI debugging**: see exactly what providers the runner sees
- **Before a long execute run**: don't burn 30 minutes finding out at task 47 that OpenAI was missing

## Related

- `/devkid.init-check` — full setup validation (preflight + tasks.md + execution_plan + hooks + ...)
- `/devkid.execute` — runs preflight + waves + sentinel
- `/devkid.sentinel-health` — raw sentinel-health output

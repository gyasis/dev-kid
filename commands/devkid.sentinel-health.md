---
name: devkid.sentinel-health
description: Check sentinel provider health — Ollama models, Azure endpoints, API keys, per-tier readiness
---

# Dev-Kid Sentinel Health

Validates all sentinel providers and model endpoints BEFORE execution. Run this to see what will work and what won't.

## What This Does

1. Checks micro-agent CLI is installed
2. Validates each provider: Ollama, Azure OpenAI, Anthropic, Google, OpenAI
3. Checks per-tier readiness against ralph-tiers.json (Ollama model existence, API keys)
4. Reports usable tier count and warnings

## Usage

```bash
/devkid.sentinel-health
```

## Execution

```bash
#!/bin/bash
set -e

echo "🛡️  Sentinel Provider Health Check"
echo ""
dev-kid sentinel-health
```

## Example Output

```
Sentinel enabled : yes
Ollama URL       : http://localhost:11434
Tiers file       : ralph-tiers.json

  micro-agent CLI

Providers:
    Ollama          http://localhost:11434
    Azure OpenAI    https://admin-....services.ai.azure.com
    Anthropic       ANTHROPIC_API_KEY
    Google          GOOGLE_API_KEY
    OpenAI          OPENAI_API_KEY

Per-tier readiness:
    local-quick
    local-heavy
    azure-budget
    azure-mid
    azure-reasoning
    azure-heavy
    azure-max

7/7 tiers ready

Sentinel will run -- at least one tier is ready
```

## When To Use

- Before `/devkid.execute` — verify providers are ready
- After environment changes (new API keys, Ollama model pulls)
- When sentinel reports SKIP — diagnose why
- Debugging test loop failures

## Configuration

Tier definitions: `~/.dev-kid/ralph-tiers.json` (machine level) or `ralph-tiers.json` (project level)
Sentinel config: `dev-kid.yml` under `sentinel:` section

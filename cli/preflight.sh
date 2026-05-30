#!/usr/bin/env bash
# cli/preflight.sh — dev-kid preflight gate for standalone CLI use
#
# Auto-sources project-local .env, runs sentinel-health, presents an
# interactive menu when providers are missing, requires explicit y/N
# confirmation before invoking dev-kid execute.
#
# Invoked by:
#   - `dev-kid preflight`         (standalone preflight check, no execute)
#   - `dev-kid execute` (default — calls preflight first unless --no-preflight)
#   - Claude Code slash command `/devkid.execute` (via the CLI dispatch)
#
# Usage:
#   bash cli/preflight.sh                       # default: just preflight (no execute)
#   bash cli/preflight.sh --execute             # preflight then execute
#   bash cli/preflight.sh --execute --yes       # bypass confirmation (CI only)
#   bash cli/preflight.sh --execute orchestrate # preflight then run other subcommand

set -uo pipefail

# Resolve project root (where preflight is invoked from, NOT where the script lives)
PROJECT_ROOT="$(pwd)"

# Auto-source .env if present in project root
if [[ -f "$PROJECT_ROOT/.env" ]]; then
    set -a
    # shellcheck disable=SC1091
    source "$PROJECT_ROOT/.env" 2>/dev/null
    set +a
fi

# Parse args
RUN_AFTER=false
NON_INTERACTIVE=false
DEVKID_CMD=""
declare -a DEVKID_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --execute)
            RUN_AFTER=true
            shift
            ;;
        --yes|-y)
            NON_INTERACTIVE=true
            shift
            ;;
        --help|-h)
            sed -n '2,16p' "${BASH_SOURCE[0]}" | sed 's/^# \?//'
            exit 0
            ;;
        *)
            if [[ -z "$DEVKID_CMD" ]]; then
                DEVKID_CMD="$1"
            else
                DEVKID_ARGS+=("$1")
            fi
            shift
            ;;
    esac
done
[[ -z "$DEVKID_CMD" ]] && DEVKID_CMD="execute"

# Spec 002 audit fix #11 — preflight result cache.
# Avoid re-prompting on every wave re-entry. Cache for 30 min in .devkid/.
PREFLIGHT_CACHE_DIR="$PROJECT_ROOT/.devkid"
PREFLIGHT_CACHE_FILE="$PREFLIGHT_CACHE_DIR/.preflight-ok"
PREFLIGHT_CACHE_TTL_SEC=1800   # 30 min

if [[ -f "$PREFLIGHT_CACHE_FILE" ]] && [[ "$RUN_AFTER" == "true" ]]; then
    cache_mtime=$(stat -c %Y "$PREFLIGHT_CACHE_FILE" 2>/dev/null || echo 0)
    now=$(date +%s)
    age=$(( now - cache_mtime ))
    if [[ $age -lt $PREFLIGHT_CACHE_TTL_SEC ]]; then
        # Verify the cache matches the current env-hash (simple sentinel check)
        cached_hash=$(cat "$PREFLIGHT_CACHE_FILE" 2>/dev/null || echo "")
        env_hash=$(echo "${ANTHROPIC_API_KEY:-}${OPENAI_API_KEY:-}${GOOGLE_API_KEY:-}${OLLAMA_BASE_URL:-}" | md5sum | cut -d' ' -f1)
        if [[ "$cached_hash" == "$env_hash" ]]; then
            echo "✓ preflight cached (age ${age}s, TTL ${PREFLIGHT_CACHE_TTL_SEC}s) — skipping re-check"
            exec dev-kid "$DEVKID_CMD" "${DEVKID_ARGS[@]}"
        fi
    fi
fi

# Spec 002 audit fix #4 — short-circuit when sentinel is disabled.
# Provider keys are ONLY needed by the sentinel micro-agent. If the project
# has `sentinel.enabled: false` in dev-kid.yml, the keys are irrelevant and
# the preflight provider gate is over-strict (this was the user's #1 friction).
SENTINEL_ENABLED="true"
if [[ -f "$PROJECT_ROOT/dev-kid.yml" ]]; then
    SENTINEL_ENABLED=$(python3 -c "
import sys
try:
    import yaml
    c = yaml.safe_load(open('$PROJECT_ROOT/dev-kid.yml')) or {}
    v = (c.get('sentinel') or {}).get('enabled', True)
    print('true' if v is True else 'false' if v is False else 'true')
except Exception:
    print('true')  # safe default — gate stays on if yaml broken
" 2>/dev/null || echo "true")
fi

if [[ "$SENTINEL_ENABLED" == "false" ]]; then
    echo "==============================================="
    echo "  dev-kid Preflight: sentinel disabled"
    echo "  → skipping provider readiness check"
    echo "  → dev-kid.yml has sentinel.enabled: false"
    echo "==============================================="
    if [[ "$RUN_AFTER" == "true" ]]; then
        exec dev-kid "$DEVKID_CMD" "${DEVKID_ARGS[@]}"
    else
        echo "✅ Preflight passes (sentinel disabled — no providers required)"
        exit 0
    fi
fi

# Spec 002 audit fix #10 — non-TTY auto-yes (scripts/cron/agents don't have stdin).
# Only fires when --yes was NOT explicitly passed AND we don't have a TTY.
# Preserves interactive behavior for human terminal use.
if [[ "$NON_INTERACTIVE" == "false" ]] && [[ ! -t 0 ]]; then
    NON_INTERACTIVE=true
    echo "  (non-TTY detected — auto-enabling --yes; pass --no-preflight to fully bypass)" >&2
fi

# Run sentinel-health, capture output
if ! command -v dev-kid &>/dev/null; then
    echo "❌ dev-kid CLI not on PATH. Install dev-kid first." >&2
    exit 2
fi
HEALTH_OUTPUT="$(dev-kid sentinel-health 2>&1)"

# Parse readiness counters
TIERS_READY=$(echo "$HEALTH_OUTPUT" | grep -oE '[0-9]+/[0-9]+ tiers ready' | head -1 | awk -F'/' '{print $1}')
TIERS_TOTAL=$(echo "$HEALTH_OUTPUT" | grep -oE '[0-9]+/[0-9]+ tiers ready' | head -1 | awk -F'[/ ]' '{print $2}')
mapfile -t MISSING_PROVIDERS < <(echo "$HEALTH_OUTPUT" | grep -E "^\s+❌\s+(Anthropic|OpenAI|Google|Ollama)" | awk '{print $2}')

# Banner
echo "==============================================="
echo "  dev-kid Preflight: provider readiness check"
echo "==============================================="
echo "  Tiers ready : ${TIERS_READY:-?}/${TIERS_TOTAL:-?}"
echo "  Missing keys: ${MISSING_PROVIDERS[*]:-(none)}"
if [[ "$RUN_AFTER" == "true" ]]; then
    echo "  Will run    : dev-kid $DEVKID_CMD ${DEVKID_ARGS[*]}"
else
    echo "  Mode        : preflight only (no execute)"
fi
echo "==============================================="
echo

ALL_READY=false
if [[ "${TIERS_READY:-0}" == "${TIERS_TOTAL:-0}" ]] && [[ ${#MISSING_PROVIDERS[@]} -eq 0 ]]; then
    ALL_READY=true
fi

# If preflight-only mode, just report and exit
if [[ "$RUN_AFTER" == "false" ]]; then
    if [[ "$ALL_READY" == "true" ]]; then
        echo "✅ All providers ready"
        exit 0
    else
        echo "⚠️  Some providers missing — see menu options below if you want to proceed:"
        echo "    1. Source ~/.env or project .env (if you have keys elsewhere)"
        echo "    2. Add keys to ~/.bashrc and re-source"
        echo "    3. Continue with reduced tiers (if dev-kid permits)"
        exit 1
    fi
fi

# Non-interactive (--yes): POLL-AND-USE, don't block.
# Proceed as long as >=1 tier is usable (escalation just has fewer rungs).
# Only HARD-BLOCK when 0 tiers are ready (genuinely nothing to run).
# WARN — louder the more tiers we're skipping — so reduced capability is visible.
# (Origin: gentle-eye dogfood 2026-05-26 — old gate demanded 100% tiers + zero
#  missing providers, blocking an 11/13-ready run over absent optional keys.)
if [[ "$NON_INTERACTIVE" == "true" ]]; then
    _ready="${TIERS_READY:-0}"
    _total="${TIERS_TOTAL:-0}"
    if [[ "$ALL_READY" == "true" ]]; then
        echo "All providers ready. --yes flag set, proceeding..."
    elif [[ "$_ready" -ge 1 ]]; then
        _skipped=$(( _total - _ready ))
        # Warn proportionally: half-or-more tiers unavailable = loud warning.
        if [[ "$_total" -gt 0 ]] && [[ $(( _ready * 2 )) -lt "$_total" ]]; then
            echo "⚠️  WARNING: only ${_ready}/${_total} tiers ready — skipping ${_skipped} (majority)." >&2
            echo "    Proceeding on reduced tiers; escalation depth is limited." >&2
            [[ ${#MISSING_PROVIDERS[@]} -gt 0 ]] && echo "    Missing: ${MISSING_PROVIDERS[*]}" >&2
        else
            echo "ℹ️  ${_ready}/${_total} tiers ready (skipping ${_skipped}). --yes set, proceeding on ready tiers." >&2
            [[ ${#MISSING_PROVIDERS[@]} -gt 0 ]] && echo "    Missing (non-blocking): ${MISSING_PROVIDERS[*]}" >&2
        fi
    else
        echo "❌ --yes flag passed but ZERO tiers are ready (0/${_total})." >&2
        echo "   Nothing to run. Source provider keys or fix ollama_url, then retry." >&2
        echo "   (At least one tier — e.g. all-local — must be reachable.)" >&2
        exit 1
    fi
    # Cache success so subsequent waves don't re-check.
    mkdir -p "$PREFLIGHT_CACHE_DIR" 2>/dev/null && \
        echo "$(echo "${ANTHROPIC_API_KEY:-}${OPENAI_API_KEY:-}${GOOGLE_API_KEY:-}${OLLAMA_BASE_URL:-}" | md5sum | cut -d' ' -f1)" > "$PREFLIGHT_CACHE_FILE"
    exec dev-kid "$DEVKID_CMD" "${DEVKID_ARGS[@]}"
fi

# Interactive: confirm even when all providers ready
if [[ "$ALL_READY" == "true" ]]; then
    echo "All providers ready. About to run: dev-kid $DEVKID_CMD ${DEVKID_ARGS[*]}"
    echo
    read -r -p "Proceed? (y/N): " confirm
    if [[ "${confirm,,}" == "y" || "${confirm,,}" == "yes" ]]; then
        # Cache the success so subsequent waves don't re-prompt
        mkdir -p "$PREFLIGHT_CACHE_DIR" 2>/dev/null && \
            echo "$(echo "${ANTHROPIC_API_KEY:-}${OPENAI_API_KEY:-}${GOOGLE_API_KEY:-}${OLLAMA_BASE_URL:-}" | md5sum | cut -d' ' -f1)" > "$PREFLIGHT_CACHE_FILE"
        exec dev-kid "$DEVKID_CMD" "${DEVKID_ARGS[@]}"
    else
        echo "Aborted by user. No dev-kid command was run."
        exit 0
    fi
fi

# Interactive: providers missing — show menu
echo "Some providers are NOT ready. Choose how to proceed:"
echo
PS3="Selection: "
options=(
    "Source ~/dev/.env (or other env file path) into THIS shell and retry"
    "Continue with currently ready tiers (${TIERS_READY:-?}/${TIERS_TOTAL:-?})"
    "Abort — do nothing"
    "Show full sentinel-health output again"
)
select opt in "${options[@]}"; do
    case $REPLY in
        1)
            read -r -p "Path to env file [~/dev/.env]: " env_path
            env_path="${env_path:-$HOME/dev/.env}"
            env_path="${env_path/#\~/$HOME}"
            if [[ -f "$env_path" ]]; then
                set -a
                # shellcheck disable=SC1090
                source "$env_path"
                set +a
                echo "Sourced $env_path. Re-checking..."
                # Re-exec preflight with same args
                exec "${BASH_SOURCE[0]}" --execute "$DEVKID_CMD" "${DEVKID_ARGS[@]}"
            else
                echo "ERROR: $env_path not found."
            fi
            ;;
        2)
            echo "Proceeding with reduced tiers..."
            exec dev-kid "$DEVKID_CMD" "${DEVKID_ARGS[@]}"
            ;;
        3)
            echo "Aborted. No dev-kid command was run."
            exit 0
            ;;
        4)
            echo
            echo "$HEALTH_OUTPUT"
            echo
            ;;
        *)
            echo "Invalid selection. Pick 1-4."
            ;;
    esac
done

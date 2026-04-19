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

# Non-interactive bypass for CI
if [[ "$NON_INTERACTIVE" == "true" ]]; then
    if [[ "$ALL_READY" == "true" ]]; then
        echo "All providers ready. --yes flag set, proceeding..."
        exec dev-kid "$DEVKID_CMD" "${DEVKID_ARGS[@]}"
    else
        echo "❌ --yes flag passed but providers not ready (${TIERS_READY:-?}/${TIERS_TOTAL:-?})." >&2
        echo "   Refusing to proceed in non-interactive mode with reduced tiers." >&2
        exit 1
    fi
fi

# Interactive: confirm even when all providers ready
if [[ "$ALL_READY" == "true" ]]; then
    echo "All providers ready. About to run: dev-kid $DEVKID_CMD ${DEVKID_ARGS[*]}"
    echo
    read -r -p "Proceed? (y/N): " confirm
    if [[ "${confirm,,}" == "y" || "${confirm,,}" == "yes" ]]; then
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

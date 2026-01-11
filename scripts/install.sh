#!/usr/bin/env bash
# Dev-Kid Installation Script

set -e

VERSION="2.0.0"
INSTALL_DIR="${1:-$HOME/.dev-kid}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🚀 Installing dev-kid v$VERSION to: $INSTALL_DIR"
echo ""

# Check dependencies
echo "🔍 Checking dependencies..."

MISSING_DEPS=()

# Check for required commands
check_command() {
    if ! command -v "$1" &> /dev/null; then
        MISSING_DEPS+=("$1")
        echo -e "   ${RED}✗${NC} $1 - not found"
        return 1
    else
        echo -e "   ${GREEN}✓${NC} $1 - found"
        return 0
    fi
}

# Required dependencies
check_command "bash"
check_command "git"
check_command "python3"
check_command "jq"

# Check Python version (need 3.7+)
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 7 ]; then
        echo -e "   ${GREEN}✓${NC} python3 version $PYTHON_VERSION (>= 3.7)"
    else
        echo -e "   ${RED}✗${NC} python3 version $PYTHON_VERSION (need >= 3.7)"
        MISSING_DEPS+=("python3>=3.7")
    fi
fi

# Check optional but recommended
if ! command -v sed &> /dev/null; then
    echo -e "   ${YELLOW}⚠${NC}  sed - not found (recommended)"
fi

if ! command -v grep &> /dev/null; then
    echo -e "   ${YELLOW}⚠${NC}  grep - not found (recommended)"
fi

# Exit if missing required dependencies
if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Missing required dependencies:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "   - $dep"
    done
    echo ""
    echo "Installation instructions:"
    echo ""
    echo "  Ubuntu/Debian:"
    echo "    sudo apt-get update"
    echo "    sudo apt-get install -y git python3 jq"
    echo ""
    echo "  macOS:"
    echo "    brew install git python3 jq"
    echo ""
    echo "  Fedora/RHEL:"
    echo "    sudo dnf install -y git python3 jq"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ All dependencies satisfied${NC}"
echo ""

# Create install directory
mkdir -p "$INSTALL_DIR"

# Get script directory (where install.sh lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Copy files
echo "   Copying files..."
cp -r "$PROJECT_ROOT/cli" "$INSTALL_DIR/"
cp -r "$PROJECT_ROOT/skills" "$INSTALL_DIR/"
cp -r "$PROJECT_ROOT/scripts" "$INSTALL_DIR/"
cp -r "$PROJECT_ROOT/templates" "$INSTALL_DIR/"
cp "$PROJECT_ROOT/DEV_KID.md" "$INSTALL_DIR/"

# Make executables
chmod +x "$INSTALL_DIR/cli/dev-kid"
chmod +x "$INSTALL_DIR/cli"/*.py
chmod +x "$INSTALL_DIR/skills"/*.sh

# Create symlink in PATH
echo "   Creating symlink..."
if [ -w "/usr/local/bin" ]; then
    ln -sf "$INSTALL_DIR/cli/dev-kid" /usr/local/bin/dev-kid
else
    sudo ln -sf "$INSTALL_DIR/cli/dev-kid" /usr/local/bin/dev-kid
fi

# Create skills directory for Claude Code
echo "   Installing skills to Claude Code..."
mkdir -p "$HOME/.claude/skills/planning-enhanced"

# Copy skills to Claude Code skills directory
cp "$INSTALL_DIR/skills"/*.sh "$HOME/.claude/skills/planning-enhanced/"

# Copy task watchdog
cp "$INSTALL_DIR/cli/task_watchdog.py" "$HOME/.claude/skills/planning-enhanced/"

echo "✅ Installation complete!"
echo ""
echo "Quick start:"
echo "  cd your-project"
echo "  dev-kid init          # Initialize dev-kid"
echo "  dev-kid status        # Check status"
echo ""
echo "Documentation:"
echo "  cat $INSTALL_DIR/DEV_KID.md"
echo ""
echo "Task Watchdog:"
echo "  dev-kid watchdog-start    # Start background task monitor"
echo "  dev-kid watchdog-report   # View task timing report"

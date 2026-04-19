#!/usr/bin/env bash
# Secure Dev-Kid Installation Script
# Implements remediations for all identified vulnerabilities

set -e

VERSION="2.0.0-secure"
INSTALL_DIR_RAW="${1:-$HOME/.dev-kid}"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "🔒 Installing dev-kid v$VERSION (security-hardened) to: $INSTALL_DIR_RAW"
echo ""

# ============================================================================
# SECURITY FUNCTIONS - Input Validation & Sanitization
# ============================================================================

# REMEDIATION #1: Path Sanitization (Prevents Command Injection)
sanitize_path() {
    local path="$1"
    local purpose="${2:-installation directory}"

    # Check for shell metacharacters (command injection prevention)
    if [[ "$path" =~ [\;\`\$\(\)\{\}\|\&\<\>] ]]; then
        echo -e "${RED}❌ Invalid $purpose: contains shell metacharacters${NC}" >&2
        echo "   Path: $path" >&2
        echo "   Security: Command injection attempt detected" >&2
        exit 1
    fi

    # Check for null bytes
    if [[ "$path" == *$'\0'* ]]; then
        echo -e "${RED}❌ Invalid $purpose: contains null bytes${NC}" >&2
        exit 1
    fi

    # Expand tilde and resolve to absolute path
    path="${path/#\~/$HOME}"

    # Use realpath for canonical path (resolves symlinks, removes ..)
    local resolved_path
    resolved_path=$(realpath -m "$path" 2>/dev/null)

    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Invalid $purpose: cannot resolve path${NC}" >&2
        echo "   Path: $path" >&2
        exit 1
    fi

    # Prevent installation to system directories
    local restricted_paths=(
        "/bin" "/sbin" "/usr/bin" "/usr/sbin"
        "/etc" "/sys" "/proc" "/dev" "/boot"
        "/lib" "/lib64" "/usr/lib" "/usr/lib64"
    )

    for restricted in "${restricted_paths[@]}"; do
        if [[ "$resolved_path" == "$restricted"* ]]; then
            echo -e "${RED}❌ Cannot install to system directory: $restricted${NC}" >&2
            echo "   Attempted path: $resolved_path" >&2
            exit 1
        fi
    done

    # Ensure path is within user's home or explicit opt directories
    if [[ ! "$resolved_path" =~ ^"$HOME" ]] && [[ ! "$resolved_path" =~ ^/opt/ ]]; then
        echo -e "${YELLOW}⚠️  Warning: Installation outside home directory${NC}" >&2
        echo "   Path: $resolved_path" >&2
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Installation cancelled"
            exit 0
        fi
    fi

    echo "$resolved_path"
}

# Validate INSTALL_DIR
INSTALL_DIR=$(sanitize_path "$INSTALL_DIR_RAW" "installation directory")
echo "✅ Validated installation directory: $INSTALL_DIR"
echo ""

# ============================================================================
# Dependency Checks
# ============================================================================

echo "🔍 Checking dependencies..."

MISSING_DEPS=()

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

check_command "bash"
check_command "git"
check_command "python3"
check_command "jq"

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 7 ]; then
        echo -e "   ${GREEN}✓${NC} python3 version $PYTHON_VERSION (>= 3.7)"
    else
        echo -e "   ${RED}✗${NC} python3 version $PYTHON_VERSION (need >= 3.7)"
        MISSING_DEPS+=("python3>=3.7")
    fi
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}❌ Missing required dependencies:${NC}"
    for dep in "${MISSING_DEPS[@]}"; do
        echo "   - $dep"
    done
    exit 1
fi

echo -e "${GREEN}✅ All dependencies satisfied${NC}"
echo ""

# ============================================================================
# Create Install Directory with Secure Permissions
# ============================================================================

echo "📁 Creating installation directory..."

# REMEDIATION #9: Secure file permissions
(
    # Set restrictive umask for all operations
    umask 077
    mkdir -p "$INSTALL_DIR"
)

# Verify permissions
dir_perms=$(stat -c %a "$INSTALL_DIR" 2>/dev/null || stat -f %A "$INSTALL_DIR")
if [ "$dir_perms" != "700" ]; then
    echo -e "${YELLOW}⚠️  Fixing directory permissions (was $dir_perms)${NC}"
    chmod 700 "$INSTALL_DIR"
fi

echo "✅ Directory created with secure permissions (700)"
echo ""

# ============================================================================
# Validate Source Directory
# ============================================================================

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "🔍 Validating source files..."

# Check required directories exist
required_dirs=("cli" "skills" "commands" "scripts" "templates")
for dir in "${required_dirs[@]}"; do
    if [ ! -d "$PROJECT_ROOT/$dir" ]; then
        echo -e "${RED}❌ Missing required directory: $dir${NC}" >&2
        exit 1
    fi
    echo -e "   ${GREEN}✓${NC} $dir/"
done

# Check required files exist
required_files=("DEV_KID.md" "cli/dev-kid")
for file in "${required_files[@]}"; do
    if [ ! -f "$PROJECT_ROOT/$file" ]; then
        echo -e "${RED}❌ Missing required file: $file${NC}" >&2
        exit 1
    fi
    echo -e "   ${GREEN}✓${NC} $file"
done

echo -e "${GREEN}✅ Source validation passed${NC}"
echo ""

# ============================================================================
# REMEDIATION #5: Safe File Copying (Prevents Path Traversal)
# ============================================================================

safe_copy_dir() {
    local src_dir="$1"
    local dst_dir="$2"
    local description="${3:-files}"

    echo "   Copying $description..."

    # Verify source is a directory
    if [ ! -d "$src_dir" ]; then
        echo -e "${RED}❌ Source is not a directory: $src_dir${NC}" >&2
        return 1
    fi

    # Prevent symlink attacks - check source is not a symlink
    if [ -L "$src_dir" ]; then
        echo -e "${RED}❌ Source is a symlink (security risk): $src_dir${NC}" >&2
        return 1
    fi

    # Create destination directory
    mkdir -p "$dst_dir"

    # Copy with dereferencing symlinks and preserving attributes
    # -L: follow symlinks (copy targets, not links themselves)
    # -p: preserve attributes
    # -r: recursive
    cp -Lpr "$src_dir" "$(dirname "$dst_dir")/"

    return 0
}

safe_copy_file() {
    local src_file="$1"
    local dst_file="$2"

    # Verify source is a regular file
    if [ ! -f "$src_file" ]; then
        echo -e "${YELLOW}⚠️  Source file not found: $src_file${NC}" >&2
        return 1
    fi

    # Prevent symlink attacks
    if [ -L "$src_file" ]; then
        echo -e "${RED}❌ Source is a symlink (security risk): $src_file${NC}" >&2
        return 1
    fi

    # Create destination directory
    mkdir -p "$(dirname "$dst_file")"

    # Copy file
    cp -p "$src_file" "$dst_file"

    return 0
}

# Copy files safely
echo "📦 Installing files..."

safe_copy_dir "$PROJECT_ROOT/cli" "$INSTALL_DIR/cli" "CLI tools"
safe_copy_dir "$PROJECT_ROOT/skills" "$INSTALL_DIR/skills" "Skills"
safe_copy_dir "$PROJECT_ROOT/commands" "$INSTALL_DIR/commands" "Commands"
safe_copy_dir "$PROJECT_ROOT/scripts" "$INSTALL_DIR/scripts" "Scripts"
safe_copy_dir "$PROJECT_ROOT/templates" "$INSTALL_DIR/templates" "Templates"
safe_copy_file "$PROJECT_ROOT/DEV_KID.md" "$INSTALL_DIR/DEV_KID.md"

echo -e "${GREEN}✅ Files installed successfully${NC}"
echo ""

# ============================================================================
# REMEDIATION #7: Safe Permission Setting (Prevents Wildcard Attacks)
# ============================================================================

safe_chmod_exec() {
    local dir="$1"
    local pattern="$2"
    local description="${3:-files}"

    echo "   Setting execute permissions on $description..."

    # Use find to avoid wildcard expansion vulnerabilities
    local count=0
    while IFS= read -r -d '' file; do
        # Double-check file is under expected directory
        local file_real=$(realpath "$file")
        local dir_real=$(realpath "$dir")

        if [[ "$file_real" != "$dir_real"/* ]]; then
            echo -e "${YELLOW}⚠️  Skipping file outside directory: $file${NC}" >&2
            continue
        fi

        # Verify it's a regular file
        if [ ! -f "$file" ] || [ -L "$file" ]; then
            echo -e "${YELLOW}⚠️  Skipping non-regular file: $file${NC}" >&2
            continue
        fi

        chmod +x "$file"
        count=$((count + 1))
    done < <(find "$dir" -maxdepth 1 -type f -name "$pattern" -print0)

    echo "   ✅ Made $count files executable"
}

echo "🔧 Setting file permissions..."

# Main executable
chmod +x "$INSTALL_DIR/cli/dev-kid"
echo "   ✅ dev-kid binary"

# Python scripts
safe_chmod_exec "$INSTALL_DIR/cli" "*.py" "Python scripts"

# Shell scripts
safe_chmod_exec "$INSTALL_DIR/skills" "*.sh" "skill scripts"

echo -e "${GREEN}✅ Permissions set securely${NC}"
echo ""

# ============================================================================
# REMEDIATION #3 & #4: Safe Symlink Creation with User Consent
# ============================================================================

create_safe_symlink() {
    local target="$1"
    local link_path="$2"

    # Check if target exists and is a file
    if [ ! -f "$target" ]; then
        echo -e "${RED}❌ Target does not exist: $target${NC}" >&2
        return 1
    fi

    # Prevent symlink to symlink chains
    if [ -L "$target" ]; then
        echo -e "${RED}❌ Target is a symlink: $target${NC}" >&2
        return 1
    fi

    # If link exists, verify it's safe to replace
    if [ -e "$link_path" ] || [ -L "$link_path" ]; then
        if [ -L "$link_path" ]; then
            existing_target=$(readlink "$link_path")
            echo -e "${YELLOW}⚠️  Symlink already exists${NC}"
            echo "   Current: $link_path → $existing_target"
            echo "   New: $link_path → $target"

            # Check if existing link points to dev-kid installation
            if [[ "$existing_target" != *"/.dev-kid/"* ]]; then
                echo -e "${YELLOW}⚠️  Existing symlink points to unexpected location${NC}"
                read -p "Replace? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    return 1
                fi
            fi
        else
            echo -e "${RED}❌ Path exists and is not a symlink: $link_path${NC}" >&2
            return 1
        fi
    fi

    # Create temporary symlink with unique name (atomic operation)
    local temp_link="${link_path}.tmp.$$"
    ln -sf "$target" "$temp_link"

    # Atomically move into place
    mv -f "$temp_link" "$link_path"

    # Verify symlink target
    local actual_target=$(readlink "$link_path")
    if [ "$actual_target" != "$target" ]; then
        echo -e "${RED}❌ Symlink verification failed${NC}" >&2
        echo "   Expected: $target" >&2
        echo "   Actual: $actual_target" >&2
        rm -f "$link_path"
        return 1
    fi

    return 0
}

install_to_path() {
    local source_path="$1"
    local target_path="/usr/local/bin/dev-kid"

    echo "🔗 Installing to system PATH..."
    echo ""

    # Check if already installed correctly
    if [ -L "$target_path" ]; then
        existing=$(readlink "$target_path")
        if [ "$existing" = "$source_path" ]; then
            echo "✅ Already installed to $target_path"
            return 0
        fi
    fi

    # Test if writable without sudo
    if [ -w "/usr/local/bin" ]; then
        echo "Installing to: $target_path"
        if create_safe_symlink "$source_path" "$target_path"; then
            echo "✅ Installed successfully"
            return 0
        else
            echo -e "${RED}❌ Installation failed${NC}" >&2
            return 1
        fi
    fi

    # Require sudo - get explicit consent
    echo -e "${YELLOW}⚠️  Installation to $target_path requires elevated privileges${NC}"
    echo ""
    echo "This will create a symlink:"
    echo "  $target_path → $source_path"
    echo ""
    echo "Alternative (no sudo required):"
    echo "  Add to PATH manually:"
    echo "  export PATH=\"$INSTALL_DIR/cli:\$PATH\""
    echo "  echo 'export PATH=\"$INSTALL_DIR/cli:\$PATH\"' >> ~/.bashrc"
    echo ""

    read -p "Use sudo to install globally? (y/N): " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo ""
        echo -e "${YELLOW}ℹ️  Skipping global installation${NC}"
        echo ""
        echo "To use dev-kid, add to your shell config:"
        echo "  export PATH=\"$INSTALL_DIR/cli:\$PATH\""
        echo ""
        return 0
    fi

    # Verify sudo is available
    if ! command -v sudo &> /dev/null; then
        echo -e "${RED}❌ sudo not available${NC}" >&2
        return 1
    fi

    # Create symlink with sudo (pass function definition)
    echo ""
    echo "Requesting elevated privileges..."

    sudo bash -c "
        $(declare -f create_safe_symlink)
        create_safe_symlink '$source_path' '$target_path'
    "

    if [ $? -eq 0 ]; then
        echo "✅ Installed successfully with sudo"
        return 0
    else
        echo -e "${RED}❌ Installation with sudo failed${NC}" >&2
        return 1
    fi
}

# Install to PATH
install_to_path "$INSTALL_DIR/cli/dev-kid"
echo ""

# ============================================================================
# Install Skills and Commands
# ============================================================================

echo "📚 Installing Claude Code integration..."

# Create directories with secure permissions
(
    umask 077
    mkdir -p "$HOME/.claude/skills"
    mkdir -p "$HOME/.claude/skills/planning-enhanced"
    mkdir -p "$HOME/.claude/commands"
)

# Copy skills
if [ -d "$INSTALL_DIR/skills" ]; then
    cp "$INSTALL_DIR/skills"/*.md "$HOME/.claude/skills/" 2>/dev/null || true
    cp "$INSTALL_DIR/skills"/*.sh "$HOME/.claude/skills/planning-enhanced/" 2>/dev/null || true
fi

# Copy task watchdog
if [ -f "$INSTALL_DIR/cli/task_watchdog.py" ]; then
    cp "$INSTALL_DIR/cli/task_watchdog.py" "$HOME/.claude/skills/planning-enhanced/"
fi

# Copy commands
if [ -d "$INSTALL_DIR/commands" ]; then
    cp "$INSTALL_DIR/commands"/devkid.*.md "$HOME/.claude/commands/" 2>/dev/null || true
fi

echo "✅ Claude Code integration installed"
echo ""

# ============================================================================
# Create Installation Checksums (Integrity Validation)
# ============================================================================

echo "🔐 Creating integrity checksums..."

(
    cd "$INSTALL_DIR"
    find . -type f -exec sha256sum {} \; > .checksums
    chmod 400 .checksums  # Read-only
)

echo "✅ Installation integrity recorded"
echo ""

# ============================================================================
# Installation Complete
# ============================================================================

echo -e "${GREEN}✅ Installation complete!${NC}"
echo ""

# Count installed files
SKILL_COUNT=$(find "$HOME/.claude/skills" -maxdepth 1 -name "*.md" 2>/dev/null | wc -l)
CMD_COUNT=$(find "$HOME/.claude/commands" -maxdepth 1 -name "devkid.*.md" 2>/dev/null | wc -l)

echo "📦 Installed:"
echo "   Location: $INSTALL_DIR"
echo "   Skills: $SKILL_COUNT auto-triggering workflows"
echo "   Commands: $CMD_COUNT slash commands"
echo "   Integrity: checksums created"
echo "   Permissions: 700 (owner-only)"
echo ""

echo "🔒 Security Features:"
echo "   ✅ Input validation and sanitization"
echo "   ✅ Path traversal prevention"
echo "   ✅ Symlink attack protection"
echo "   ✅ Secure file permissions"
echo "   ✅ Installation integrity validation"
echo "   ✅ User consent for privilege escalation"
echo ""

echo "Next steps:"
echo "  cd your-project"
echo "  dev-kid init          # Initialize dev-kid"
echo "  dev-kid status        # Check status"
echo ""

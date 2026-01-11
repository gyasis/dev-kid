# Dependencies

This document lists all dependencies required to install and run dev-kid.

## Required Dependencies

These dependencies **must** be installed for dev-kid to function:

### 1. Bash
- **Version**: 4.0 or higher
- **Used for**: Main CLI, all skill scripts, installation scripts
- **Check**: `bash --version`

### 2. Git
- **Version**: 2.0 or higher
- **Used for**: Checkpointing, version control, activity logging
- **Check**: `git --version`

### 3. Python 3
- **Version**: 3.7 or higher (3.9+ recommended)
- **Used for**: Task orchestration, wave execution, task watchdog
- **Check**: `python3 --version`
- **Packages**: All standard library (no external packages needed)
  - `json`
  - `pathlib`
  - `datetime`
  - `typing`
  - `dataclasses` (Python 3.7+)

### 4. jq
- **Version**: 1.5 or higher
- **Used for**: JSON parsing in bash scripts (recall.sh, status checks)
- **Check**: `jq --version`

## Recommended Dependencies

These are not strictly required but provide better functionality:

### 1. sed
- **Used for**: Template variable substitution in init.sh
- **Check**: `sed --version`
- **Fallback**: Manual template editing if not available

### 2. grep
- **Used for**: File searching, pattern matching in various scripts
- **Check**: `grep --version`
- **Fallback**: Some features may be limited

## Installation Instructions

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y bash git python3 jq sed grep
```

### macOS
```bash
# Using Homebrew
brew install bash git python3 jq gnu-sed grep

# Note: macOS ships with BSD sed/grep, GNU versions recommended
```

### Fedora/RHEL/CentOS
```bash
sudo dnf install -y bash git python3 jq sed grep
```

### Arch Linux
```bash
sudo pacman -S bash git python jq sed grep
```

### Alpine Linux
```bash
apk add bash git python3 jq sed grep
```

## Verification

The installation script (`scripts/install.sh`) automatically checks for all required dependencies and will:

1. ✅ Verify each dependency is installed
2. ✅ Check Python version is 3.7 or higher
3. ⚠️  Warn about missing recommended dependencies
4. ❌ Exit with instructions if required dependencies are missing

### Manual Verification

You can manually verify dependencies before installation:

```bash
# Check all required dependencies
for cmd in bash git python3 jq; do
    if command -v $cmd &> /dev/null; then
        echo "✓ $cmd: $(command -v $cmd)"
    else
        echo "✗ $cmd: not found"
    fi
done

# Check Python version
python3 -c 'import sys; print(f"Python {sys.version_info.major}.{sys.version_info.minor}")'

# Check Python standard library modules
python3 -c 'import json, pathlib, datetime, typing, dataclasses; print("✓ All Python modules available")'
```

## Runtime Dependencies

### File System
- **Write access** to:
  - `$HOME/.dev-kid/` (installation directory)
  - `/usr/local/bin/` (or sudo access for symlink)
  - `$HOME/.claude/skills/` (for Claude Code integration)
  - Project directories where dev-kid is initialized

### Git Repository
- **Optional**: Project must be a git repository (or dev-kid will initialize one)
- **Git hooks**: dev-kid installs a post-commit hook (requires write access to `.git/hooks/`)

## Python Standard Library Usage

Dev-kid uses **only** Python standard library modules:

```python
# orchestrator.py
import json
from pathlib import Path
from typing import List, Dict, Set
from dataclasses import dataclass, field
from collections import defaultdict

# wave_executor.py
import json
from pathlib import Path
from typing import Dict, List
import subprocess

# task_watchdog.py
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
```

**No `pip install` required!** ✅

## System Requirements

### Operating System
- ✅ Linux (any distribution)
- ✅ macOS 10.15 (Catalina) or higher
- ✅ Windows WSL2 (Ubuntu/Debian)
- ⚠️  Windows native (Git Bash required, limited testing)

### Disk Space
- **Installation**: ~2 MB
- **Per-project**: ~100 KB (Memory Bank + Context Protection)
- **Session snapshots**: ~10 KB per snapshot

### Memory
- **CLI**: < 10 MB
- **Task Watchdog**: < 20 MB (background process)
- **Orchestrator**: < 50 MB (during wave generation)

## Troubleshooting

### "jq: command not found"

**Problem**: jq is not installed

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install jq

# macOS
brew install jq

# Fedora/RHEL
sudo dnf install jq
```

### "python3: No module named 'dataclasses'"

**Problem**: Python version < 3.7

**Solution**:
```bash
# Check Python version
python3 --version

# Upgrade Python (Ubuntu/Debian)
sudo apt-get install python3.9

# macOS
brew install python@3.9
```

### Permission denied: /usr/local/bin/dev-kid

**Problem**: No write access to /usr/local/bin

**Solution**: Installation script will use `sudo` automatically, or specify custom install location:
```bash
./scripts/install.sh ~/bin
# Then add ~/bin to your PATH
export PATH="$HOME/bin:$PATH"
```

### Git not found

**Problem**: Git is not installed

**Solution**:
```bash
# Ubuntu/Debian
sudo apt-get install git

# macOS
xcode-select --install  # or: brew install git

# Fedora/RHEL
sudo dnf install git
```

## Dependency-Free Features

The following dev-kid features work **without** additional dependencies:

- ✅ Memory Bank file structure
- ✅ Context Protection files
- ✅ Manual task tracking in tasks.md
- ✅ Session snapshots (manual)

These features **require** dependencies:

- Git → Checkpointing, activity logging
- Python → Task orchestration, watchdog
- jq → Session recall, status checks

## Future Considerations

### Potential Optional Dependencies

These are **not currently used** but may be added in future versions:

- `watch` - Real-time monitoring (alternative: polling)
- `tput` - Advanced terminal formatting (alternative: ANSI codes)
- `column` - Table formatting (alternative: manual formatting)
- `fzf` - Interactive selection (alternative: numbered menus)

All future dependencies will:
1. Be **optional** with graceful degradation
2. Have clear installation instructions
3. Be checked by install.sh
4. Have documented alternatives

## Continuous Integration

The dependency check in `install.sh` ensures:
- ✅ Consistent environment across users
- ✅ Clear error messages with solutions
- ✅ Platform-specific installation instructions
- ✅ Version compatibility verification

---

**Last updated**: 2025-01-05
**Dev-kid version**: 2.0.0

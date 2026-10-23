#!/usr/bin/env python3
"""sentinel_toggle — single source of truth for "is the integration sentinel enabled?"

Rule (shared by `dev-kid sentinel-health`, the wave executor's checkpoint
Step 2b, and cli/preflight.sh): the sentinel is ON only when the project's
dev-kid.yml has `sentinel.enabled` set to something other than
false/0/no/off. No dev-kid.yml, no `sentinel:` block, or no `enabled:` key
all mean OFF.

CLI: `python3 sentinel_toggle.py [project_root]` prints `true` or `false`.
"""
import sys
from pathlib import Path

_FALSY = ("false", "0", "no", "off")


def _parse_lines(text: str) -> bool:
    """Fallback parser (no PyYAML): mirrors the historic sentinel-health scan."""
    enabled = False
    in_sentinel = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("sentinel:"):
            in_sentinel = True
        elif in_sentinel:
            if s.startswith("enabled:"):
                v = s.split(":", 1)[1].split("#")[0].strip().strip("\"'").lower()
                enabled = v not in _FALSY
            elif s and not s.startswith("#") and ":" in s and not line.startswith(" "):
                break
    return enabled


def is_sentinel_enabled(project_root=".") -> bool:
    yml = Path(project_root) / "dev-kid.yml"
    try:
        text = yml.read_text(encoding="utf-8")
    except OSError:
        return False
    try:
        import yaml  # type: ignore[import]

        data = yaml.safe_load(text) or {}
        block = data.get("sentinel") if isinstance(data, dict) else None
        if not isinstance(block, dict) or "enabled" not in block:
            return False
        v = block["enabled"]
        if isinstance(v, str):
            return v.strip().lower() not in _FALSY
        return bool(v)
    except Exception:
        return _parse_lines(text)


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    print("true" if is_sentinel_enabled(root) else "false")

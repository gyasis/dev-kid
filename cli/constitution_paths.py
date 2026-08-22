"""
Single source of truth for locating a project's constitution.

Previously six call sites each hardcoded "memory-bank/shared/.constitution.md"
while init_check.py probed three locations. The result was that `init-check`
reported PASS ("constitution at .specify/memory/constitution.md") while
`execute` reported "Constitution file not found" for the same repo — a
validator and a runtime disagreeing about the same fact.

memory-bank/ is NOT required. Installs without one resolve to the SpecKit
location or a repo-root constitution.md.
"""

from pathlib import Path
from typing import Optional

# Probed in order. memory-bank stays first so existing projects that have one
# keep their current behaviour exactly; everything after it is what makes a
# memory-bank optional rather than mandatory.
CANDIDATE_PATHS = (
    "memory-bank/shared/.constitution.md",  # dev-kid legacy layout
    ".specify/memory/constitution.md",      # SpecKit layout
    "constitution.md",                      # plain repo root
)


def resolve_constitution_path(file_path=None, root=None) -> Path:
    """First existing candidate, else the SpecKit path as the default.

    The default is deliberately NOT the memory-bank path: a project without a
    constitution should be told to create the SpecKit one, not to invent a
    memory-bank directory it does not otherwise need.
    """
    if file_path is not None:
        return Path(file_path)
    base = Path(root) if root else Path(".")
    for cand in CANDIDATE_PATHS:
        if (base / cand).exists():
            return base / cand
    return base / CANDIDATE_PATHS[1]


def find_constitution(root=None) -> Optional[Path]:
    """Existing constitution path, or None. Never invents a location."""
    base = Path(root) if root else Path(".")
    for cand in CANDIDATE_PATHS:
        if (base / cand).exists():
            return base / cand
    return None

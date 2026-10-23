#!/usr/bin/env python3
"""Canonical, collision-proof task-ID + tasks.md line matching.

THE single source of truth for "match a `tasks.md` line ↔ a plan task" (issue
#11 / #12). Every ad-hoc matcher in the codebase (`] {tid} ` substring,
`"[x]" in line`, `instruction in line`) is replaced by the anchored,
marker-aware primitives here.

Why this exists
---------------
`orchestrate` historically renumbered tasks to **internal sequential IDs**
(`T001..TNN`, plain document-order count) while the **authored ID** (e.g.
`T020`) survived only inside the instruction text and in `tasks.md`. For any
spec with non-contiguous authored IDs (`T010, T020, T030…`) the internal ID
string-collided with a *different* authored line, so resume false-skipped
undone waves and checkpoints false-passed. The cure (issue option A) is to
make the **authored ID the ID** and match lines with an **anchored** regex
that reads the checkbox capture group — never an unanchored substring and
never `"[x]" in line`.
"""

from __future__ import annotations

import re
from typing import NamedTuple, Optional

# Anchored task-line matcher. Leading whitespace is allowed so indented
# sub-bullets parse. The checkbox mark is a capture group — completeness is
# read from `mark`, NEVER from `"[x]" in line` (which matches `[x]` anywhere
# in a description: `arr[x]`, a glob, a markdown ref).
_TASK_LINE_RE = re.compile(r"^\s*-\s*\[(?P<mark>[ xX])\]\s*(?P<rest>.*)$")

# A leading authored task id at the very start of the post-checkbox text:
# `T020 ...`, `T20: ...` or `T025a ...`. Anchored to the start of `rest` so it can only be
# THE task's own id, not a `T0xx` mentioned later in the description.
#
# Task id grammar: `T` + digits + an OPTIONAL single letter subtask suffix
# (Spec Kit writes `T025a` as a subtask of `T025`). The suffix must touch the
# digits and the id must end at a non-word char (`(?![A-Za-z0-9_])`, not `\b`
# alone), so `T025ab` is NOT an id. A suffix is matched in either case but
# canon_id() LOWERCASES it: `T025A` == `T025a`, and `T025` != `T025a`.
ID_PATTERN = r"T\d+[a-zA-Z]?(?![A-Za-z0-9_])"
_LEADING_ID_RE = re.compile(rf"^(?P<id>{ID_PATTERN})")

# Any T-id anywhere (used by canon_id and dependency clause scanning).
_ANY_ID_RE = re.compile(rf"(?<![A-Za-z0-9_])({ID_PATTERN})")


def canon_id(raw: str) -> str:
    """Normalize a task id to canonical `T###` (zero-padded to 3 digits).

    Makes `T20`, `T020`, and `t20` all compare equal, so the authored line,
    the dependency clause, and the plan task all share ONE namespace.

    Non-`T` ids (e.g. `SENTINEL-T001`) are returned stripped/unchanged — the
    numeric part of a sentinel id must NOT be re-interpreted as a bare `T###`
    (that would collide a sentinel with a real task).
    """
    if not raw:
        return ""
    raw = raw.strip()
    if raw.upper().startswith("T"):
        m = re.match(r"[Tt](\d+)([a-zA-Z]?)$", raw)
        if m:
            return f"T{int(m.group(1)):03d}{m.group(2).lower()}"
    return raw


def task_sort_key(tid: str) -> tuple:
    """Numeric sort key: T025 < T025a < T025b < T026 (non-task ids sort last)."""
    m = re.match(r"[Tt](\d+)([a-zA-Z]?)$", (tid or "").strip())
    if not m:
        return (1, 0, tid or "")
    return (0, int(m.group(1)), m.group(2).lower())


class ParsedLine(NamedTuple):
    """Result of parsing one tasks.md line as a checklist task."""

    complete: bool  # checkbox is [x] / [X]
    authored_id: Optional[str]  # canonical leading T-id, or None if the line has none
    rest: str  # text after the checkbox, stripped (still includes the id, if any)


def parse_task_line(line: str) -> Optional[ParsedLine]:
    """Parse a single line as `- [ ]`/`- [x]` task. Returns None if not a task.

    Anchored and marker-aware: leading whitespace allowed (indented bullets),
    completeness read from the checkbox group, authored id read only from the
    START of the post-checkbox text.
    """
    m = _TASK_LINE_RE.match(line)
    if not m:
        return None
    complete = m.group("mark").lower() == "x"
    rest = m.group("rest").strip()
    idm = _LEADING_ID_RE.match(rest)
    authored = canon_id(idm.group("id")) if idm else None
    return ParsedLine(complete=complete, authored_id=authored, rest=rest)


def find_task_line(
    content: str,
    *,
    authored_id: str = "",
    task_id: str = "",
    instruction: str = "",
) -> Optional[ParsedLine]:
    """Find the tasks.md line for a plan task. Returns the ParsedLine or None.

    Match priority (each step is ANCHORED — no bare substring that could flip
    a different-numbered or already-checked line):

    1. SENTINEL tasks (`task_id` starts with ``SENTINEL``) — match the line
       whose post-checkbox text begins with that exact sentinel id.
    2. Authored-id tasks — match the line whose leading authored id equals the
       task's canonical authored id. This is the precise, collision-proof path
       used by every labelled (SpecKit-style) spec.
    3. Unlabelled tasks (lightweight mode, no `T###` in the line) — match the
       line whose post-checkbox text equals / starts with the instruction.
    """
    canon_authored = canon_id(authored_id) if authored_id else ""
    is_sentinel = task_id.startswith("SENTINEL")
    instr = (instruction or "").strip()

    fallback: Optional[ParsedLine] = None
    for line in content.split("\n"):
        parsed = parse_task_line(line)
        if parsed is None:
            continue

        if is_sentinel:
            if parsed.rest.startswith(task_id):
                return parsed
            continue

        if canon_authored:
            if parsed.authored_id == canon_authored:
                return parsed
            continue

        # Unlabelled (synthetic-id) task: match by anchored instruction text.
        if instr and parsed.authored_id is None:
            if parsed.rest == instr or parsed.rest.startswith(instr):
                return parsed
            if fallback is None and instr in parsed.rest:
                fallback = parsed  # weakest signal — only if nothing better

    return fallback

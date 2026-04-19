"""Regression tests for permissive task-line parser in cli/sentinel_run.py.

Background
----------
Before this fix, sentinel_run.py used a strict regex that REQUIRED a colon
after the task ID:
    `^\\s*-\\s*\\[[x ]\\]\\s+T\\d{1,4}\\s*:\\s*(.+)$`

This rejected the speckit-canonical task format (`- [ ] T001 description`) and
silently returned "no tasks found" — even though the orchestrator parser at
orchestrator.py:102 happily accepted that exact format via `line.startswith("- [ ]")`.

The two parsers were structurally inconsistent: sentinel-run's standalone
commands (--list, --pending, T001 lookup) couldn't see any tasks that
orchestrate had already enqueued, leading to 5+ hours of confused debugging
for downstream consumers (PromptChain 011-agentic-prompt-builder, 2026-04-19).

This test suite locks in the permissive parser so it can't regress.
"""
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.sentinel_run import find_task_in_tasks_md, list_tasks_in_md


def _write_tmp_tasks_md(content: str) -> Path:
    """Write content to a NamedTemporaryFile and return its Path."""
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
    f.write(content)
    f.close()
    return Path(f.name)


# ============================================================================
# list_tasks_in_md — must accept BOTH formats
# ============================================================================


def test_list_tasks_accepts_speckit_canonical_no_colon():
    """`- [ ] T001 description` (no colon) must be parsed."""
    p = _write_tmp_tasks_md(
        "- [ ] T001 First task\n"
        "- [ ] T002 Second task\n"
    )
    rows = list_tasks_in_md(p)
    assert len(rows) == 2
    assert rows[0][0] == "T001"
    assert rows[1][0] == "T002"
    assert "First task" in rows[0][2]
    assert "Second task" in rows[1][2]


def test_list_tasks_accepts_colon_prefixed():
    """`- [ ] T001: description` (with colon) must STILL be parsed (backward compat)."""
    p = _write_tmp_tasks_md(
        "- [ ] T001: First task\n"
        "- [ ] T002: Second task\n"
    )
    rows = list_tasks_in_md(p)
    assert len(rows) == 2
    assert rows[0][0] == "T001"
    assert "First task" in rows[0][2]


def test_list_tasks_accepts_speckit_with_tags():
    """`- [ ] T001 [P] [US1] description` must be parsed (real speckit output)."""
    p = _write_tmp_tasks_md(
        "- [ ] T001 [P] [US1] First parallel task\n"
        "- [ ] T002 [US2] Second tagged task\n"
    )
    rows = list_tasks_in_md(p)
    assert len(rows) == 2
    assert rows[0][0] == "T001"
    assert "[P]" in rows[0][2]
    assert "[US1]" in rows[0][2]


def test_list_tasks_handles_mixed_formats_in_same_file():
    """Mixed colon and no-colon lines must both be parsed."""
    p = _write_tmp_tasks_md(
        "- [ ] T001 Speckit canonical task\n"
        "- [ ] T002: Colon-prefixed task\n"
        "- [ ] T003 [P] Tagged speckit task\n"
        "- [ ] T004: [P] Tagged colon-prefixed task\n"
    )
    rows = list_tasks_in_md(p)
    assert len(rows) == 4
    assert [r[0] for r in rows] == ["T001", "T002", "T003", "T004"]


def test_list_tasks_normalizes_short_ids():
    """T1 / T01 / T001 must all normalize to T001 (zero-padded)."""
    p = _write_tmp_tasks_md(
        "- [ ] T1 Short ID\n"
        "- [ ] T01 Two-digit ID\n"
        "- [ ] T001 Full ID\n"
    )
    rows = list_tasks_in_md(p)
    assert [r[0] for r in rows] == ["T001", "T001", "T001"]


def test_list_tasks_skips_sentinel_tasks():
    """SENTINEL-T### lines must be filtered out (managed by injection)."""
    p = _write_tmp_tasks_md(
        "- [ ] T001 Real task\n"
        "- [ ] SENTINEL-T001 Sentinel validation\n"
        "- [ ] T002 Another real task\n"
    )
    rows = list_tasks_in_md(p)
    # Note: regex captures `SENTINEL` in the (T\d) group only if the SENTINEL prefix
    # is followed by digits, but we explicitly filter SENTINEL- in code. The regex
    # itself only matches `T\d{1,4}`, not `SENTINEL-T\d`, so SENTINEL lines are
    # not even matched. Real tasks remain.
    real_ids = [r[0] for r in rows]
    assert "T001" in real_ids
    assert "T002" in real_ids
    # SENTINEL line shouldn't appear with literal SENTINEL prefix
    assert not any("SENTINEL" in r[0] for r in rows)


def test_list_tasks_distinguishes_checked_from_unchecked():
    """`- [x]` is checked, `- [ ]` is unchecked."""
    p = _write_tmp_tasks_md(
        "- [ ] T001 Pending\n"
        "- [x] T002 Done\n"
    )
    rows = list_tasks_in_md(p)
    assert len(rows) == 2
    is_checked = {r[0]: r[1] for r in rows}
    assert is_checked["T001"] is False
    assert is_checked["T002"] is True


def test_list_tasks_filter_by_completion_state():
    """include_checked=False / include_unchecked=False filters work."""
    p = _write_tmp_tasks_md(
        "- [ ] T001 Pending\n"
        "- [x] T002 Done\n"
    )
    only_pending = list_tasks_in_md(p, include_checked=False, include_unchecked=True)
    assert [r[0] for r in only_pending] == ["T001"]
    only_done = list_tasks_in_md(p, include_checked=True, include_unchecked=False)
    assert [r[0] for r in only_done] == ["T002"]


def test_list_tasks_returns_empty_for_no_tasks_md():
    """Missing file returns empty list (no exception)."""
    rows = list_tasks_in_md(Path("/tmp/this-file-does-not-exist-xyz.md"))
    assert rows == []


def test_list_tasks_extracts_file_locks_from_backticked_paths():
    """Backticked paths in the description are extracted as file_locks."""
    p = _write_tmp_tasks_md(
        "- [ ] T001 Edit `src/foo.py` and `tests/test_foo.py`\n"
    )
    rows = list_tasks_in_md(p)
    assert len(rows) == 1
    file_locks = rows[0][3]
    assert "src/foo.py" in file_locks
    assert "tests/test_foo.py" in file_locks


# ============================================================================
# find_task_in_tasks_md — single-task lookup must accept BOTH formats
# ============================================================================


def test_find_task_speckit_canonical_form():
    """find_task('T001') against `- [ ] T001 description` returns the instruction."""
    p = _write_tmp_tasks_md("- [ ] T001 The first task\n")
    instruction, file_locks = find_task_in_tasks_md(p, "T001")
    assert instruction == "The first task"
    assert file_locks == []


def test_find_task_colon_prefixed_form():
    """find_task('T001') against `- [ ] T001: description` (legacy) returns instruction."""
    p = _write_tmp_tasks_md("- [ ] T001: The first task\n")
    instruction, file_locks = find_task_in_tasks_md(p, "T001")
    assert instruction == "The first task"


def test_find_task_with_tags_in_description():
    """`- [ ] T001 [P] [US1] desc` returns the entire description including tags."""
    p = _write_tmp_tasks_md("- [ ] T001 [P] [US1] Tagged task\n")
    instruction, _ = find_task_in_tasks_md(p, "T001")
    assert "[P]" in instruction
    assert "[US1]" in instruction


def test_find_task_returns_none_for_missing_id():
    """Looking up an ID that doesn't exist returns (None, [])."""
    p = _write_tmp_tasks_md("- [ ] T001 First task\n")
    instruction, file_locks = find_task_in_tasks_md(p, "T999")
    assert instruction is None
    assert file_locks == []


def test_find_task_does_not_match_id_substring():
    """Looking up T001 must NOT match T0011 or T1001 (word boundary required)."""
    p = _write_tmp_tasks_md(
        "- [ ] T0011 Should not match\n"
        "- [ ] T001 Should match\n"
    )
    instruction, _ = find_task_in_tasks_md(p, "T001")
    assert instruction == "Should match"


def test_find_task_extracts_file_locks_from_description():
    """Backticked file paths in the description get extracted as file_locks."""
    p = _write_tmp_tasks_md(
        "- [ ] T001 Edit `cli/foo.py` and update `README.md`\n"
    )
    instruction, file_locks = find_task_in_tasks_md(p, "T001")
    assert "cli/foo.py" in file_locks
    assert "README.md" in file_locks

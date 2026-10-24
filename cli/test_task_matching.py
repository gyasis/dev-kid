#!/usr/bin/env python3
"""Regression tests for the task-ID collision fix (issues #11 / #12).

Covers the #11 minimal repro plus each enumerated defect (1–7) and the
core `task_matching` primitives.
"""

import sys
from pathlib import Path

import pytest

# Make the cli/ modules importable regardless of pytest's rootdir.
sys.path.insert(0, str(Path(__file__).parent))

from orchestrator import TaskOrchestrator  # noqa: E402
from task_matching import (  # noqa: E402
    canon_id,
    find_task_line,
    parse_task_line,
)
from wave_executor import WaveExecutor  # noqa: E402


def _executor_for(tasks_path: Path) -> WaveExecutor:
    """A WaveExecutor with no __init__ side effects, pointed at tasks_path."""
    ex = object.__new__(WaveExecutor)
    ex.tasks_file = tasks_path
    return ex


def _orchestrate(tmp_path: Path, content: str) -> TaskOrchestrator:
    tasks = tmp_path / "tasks.md"
    tasks.write_text(content, encoding="utf-8")
    orch = TaskOrchestrator(str(tasks))
    orch.parse_tasks()
    return orch


# --------------------------------------------------------------------------
# task_matching primitives
# --------------------------------------------------------------------------


def test_canon_id_normalizes():
    assert canon_id("T20") == "T020"
    assert canon_id("T020") == "T020"
    assert canon_id("t5") == "T005"
    assert canon_id("SENTINEL-T001") == "SENTINEL-T001"  # not re-interpreted
    assert canon_id("") == ""


def test_parse_task_line_reads_checkbox_not_substring():
    # `[x]` inside the description must NOT make an unchecked task complete.
    p = parse_task_line("- [ ] T030: fix arr[x] indexing")
    assert p is not None
    assert p.complete is False
    assert p.authored_id == "T030"


def test_parse_task_line_indented():
    p = parse_task_line("    - [x] T040: nested")
    assert p is not None and p.complete is True and p.authored_id == "T040"


def test_parse_task_line_non_task():
    assert parse_task_line("## Wave 2: notes") is None
    assert parse_task_line("plain text") is None


# --------------------------------------------------------------------------
# #11 minimal repro — gapped IDs must not collide
# --------------------------------------------------------------------------

GAPPED = """- [x] T010 [US1] recency default — DONE
- [ ] T020 [US2] context window — NOT DONE
"""


def test_repro_gapped_ids_no_false_complete(tmp_path):
    """The exact #11 repro: undone T020 must report (found, NOT complete)."""
    content = GAPPED
    ex = _executor_for(tmp_path / "tasks.md")

    # Plan task as Option-A orchestrate now emits it: authored_id is first-class.
    t020 = {"task_id": "T020", "authored_id": "T020", "instruction": "T020 [US2] context window"}
    t010 = {"task_id": "T010", "authored_id": "T010", "instruction": "T010 [US1] recency default"}

    assert ex._find_task_state(content, t020) == (True, False)
    assert ex._find_task_state(content, t010) == (True, True)


def test_repro_via_find_task_line(tmp_path):
    parsed = find_task_line(GAPPED, authored_id="T020", task_id="T020")
    assert parsed is not None and parsed.complete is False
    parsed = find_task_line(GAPPED, authored_id="T010", task_id="T010")
    assert parsed is not None and parsed.complete is True


def test_orchestrate_gapped_uses_authored_ids(tmp_path):
    orch = _orchestrate(tmp_path, GAPPED)
    ids = {t.id for t in orch.tasks}
    assert ids == {"T010", "T020"}  # authored, NOT renumbered T001/T002
    by_id = {t.id: t for t in orch.tasks}
    assert by_id["T010"].completed is True
    assert by_id["T020"].completed is False
    assert by_id["T020"].authored_id == "T020"


# --------------------------------------------------------------------------
# defect #3 — "[x]" in line must not false-pass the checkpoint gate
# --------------------------------------------------------------------------


def test_defect3_bracket_x_in_description_not_complete(tmp_path):
    content = "- [ ] T030: handle arr[x] slicing\n"
    ex = _executor_for(tmp_path / "tasks.md")
    task = {"task_id": "T030", "authored_id": "T030", "instruction": "T030: handle arr[x] slicing"}
    assert ex._find_task_state(content, task) == (True, False)


# --------------------------------------------------------------------------
# defect #4 — parser must not flag a task completed for "[x]" in its text
# --------------------------------------------------------------------------


def test_defect4_parser_bracket_x_not_completed(tmp_path):
    orch = _orchestrate(tmp_path, "- [ ] T030: handle arr[x] slicing\n")
    assert orch.tasks[0].completed is False


# --------------------------------------------------------------------------
# defect #5 — indented sub-bullets parse as tasks
# --------------------------------------------------------------------------


def test_defect5_indented_subbullets_parsed(tmp_path):
    content = "- [ ] T010: parent\n  - [ ] T011: indented child\n"
    orch = _orchestrate(tmp_path, content)
    ids = {t.id for t in orch.tasks}
    assert "T011" in ids


# --------------------------------------------------------------------------
# defect #6 — empty wave is NOT vacuously complete
# --------------------------------------------------------------------------


def test_defect6_empty_wave_not_complete(tmp_path):
    (tmp_path / "tasks.md").write_text("- [ ] T010: x\n", encoding="utf-8")
    ex = _executor_for(tmp_path / "tasks.md")
    assert ex._wave_already_complete([]) is False


# --------------------------------------------------------------------------
# defect #7 — multi-predecessor inline deps keep every id
# --------------------------------------------------------------------------


def test_defect7_multi_predecessor_inline_deps(tmp_path):
    orch = TaskOrchestrator(str(tmp_path / "tasks.md"))
    deps = orch._extract_dependencies("T050: do thing after T1, T10, T20")
    assert deps == ["T001", "T010", "T020"]


# --------------------------------------------------------------------------
# defect #2 — mark-complete flips the RIGHT checkbox (authored id), once
# --------------------------------------------------------------------------


def test_defect2_mark_complete_correct_checkbox(tmp_path):
    tasks = tmp_path / "tasks.md"
    tasks.write_text(GAPPED, encoding="utf-8")
    ex = _executor_for(tasks)
    ex._mark_task_complete(
        {"task_id": "T020", "authored_id": "T020", "instruction": "T020 [US2] context window"}
    )
    out = tasks.read_text(encoding="utf-8")
    assert "- [x] T010" in out  # untouched (already done)
    assert "- [x] T020" in out  # now flipped
    assert "- [ ] T020" not in out


# --------------------------------------------------------------------------
# SENTINEL tasks match by their exact injected id
# --------------------------------------------------------------------------


def test_sentinel_match(tmp_path):
    content = "- [ ] SENTINEL-T001: Sentinel validation for T001\n- [x] T001: real task\n"
    ex = _executor_for(tmp_path / "tasks.md")
    task = {
        "task_id": "SENTINEL-T001",
        "instruction": "Sentinel validation for T001",
        "authored_id": "",
    }
    found, complete = ex._find_task_state(content, task)
    assert found is True and complete is False  # sentinel line still [ ]


# --------------------------------------------------------------------------
# #12 item 3 — duplicate authored ids fail fast
# --------------------------------------------------------------------------


def test_duplicate_authored_ids_exit(tmp_path):
    content = "- [ ] T010: first\n- [ ] T010: dup\n"
    tasks = tmp_path / "tasks.md"
    tasks.write_text(content, encoding="utf-8")
    orch = TaskOrchestrator(str(tasks))
    with pytest.raises(SystemExit):
        orch.parse_tasks()


# --------------------------------------------------------------------------
# Lightweight (unlabelled) tasks match by anchored instruction text
# --------------------------------------------------------------------------


def test_unlabelled_tasks_match_by_instruction(tmp_path):
    content = "- [x] implement the auth module\n- [ ] write the docs page\n"
    ex = _executor_for(tmp_path / "tasks.md")
    done = {"task_id": "T001", "authored_id": "", "instruction": "implement the auth module"}
    todo = {"task_id": "T002", "authored_id": "", "instruction": "write the docs page"}
    assert ex._find_task_state(content, done) == (True, True)
    assert ex._find_task_state(content, todo) == (True, False)


# --------------------------------------------------------------------------
# Subtask ids (T025a) + ordinal-fallback collisions
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("T25a", "T025a"),
        ("t25a", "T025a"),
        ("T025A", "T025a"),
        ("T020", "T020"),
        ("T25", "T025"),
        ("SENTINEL-T001", "SENTINEL-T001"),
    ],
)
def test_canon_id_suffix(raw, expected):
    assert canon_id(raw) == expected


def test_suffixed_and_plain_ids_differ():
    assert canon_id("T025") != canon_id("T025a")


@pytest.mark.parametrize(
    "line,expected",
    [
        ("- [ ] T025a: sub", "T025a"),
        ("- [ ] T025a sub", "T025a"),
        ("- [x] T025 parent", "T025"),
        ("- [ ] T025A: upper", "T025a"),
        ("- [ ] T025ab: two letters", None),
        ("- [ ] T025a_x: underscore", None),
        ("- [ ] plain text", None),
    ],
)
def test_parse_task_line_suffix(line, expected):
    assert parse_task_line(line).authored_id == expected


def test_task_sort_key_order():
    from task_matching import task_sort_key

    ids = ["T026", "T025b", "T025", "T025a", "T100"]
    assert sorted(ids, key=task_sort_key) == ["T025", "T025a", "T025b", "T026", "T100"]


def test_find_task_line_suffix_isolated():
    content = "- [ ] T025: parent\n- [x] T025a: sub\n"
    got = find_task_line(content, authored_id="T025a")
    assert got.complete is True and got.rest.startswith("T025a")
    got = find_task_line(content, authored_id="T025")
    assert got.complete is False and got.rest.startswith("T025:")


_SUBTASK_MD = """# Tasks
- [ ] T001: setup `a.py`
- [ ] T002: models `b.py`
- [ ] T003 [P] docs `c.md`
- [ ] T025: parent `d.py`
- [ ] T025a: sub of parent, after T025, blocks T030 `e.py`
- [ ] T028: other `f.py`
- [ ] T028a: needs T028 and T025a `g.py`
- [ ] T030: tail `h.py`
- [ ] T041a: orphan subtask `i.py`
"""


def _parse(tmp_path, content):
    tasks = tmp_path / "tasks.md"
    tasks.write_text(content, encoding="utf-8")
    orch = TaskOrchestrator(str(tasks))
    orch.parse_tasks()
    return orch


def test_orchestrator_reads_suffixed_ids(tmp_path):
    orch = _parse(tmp_path, _SUBTASK_MD)
    assert [t.id for t in orch.tasks] == [
        "T001", "T002", "T003", "T025", "T025a", "T028", "T028a", "T030", "T041a",
    ]
    graph = orch.analyze_dependencies()
    assert "T025a" in graph["T028a"]
    assert "T028" in graph["T028a"]
    assert "T025" in graph["T025a"]
    assert "T025a" in graph["T030"]


def test_dependency_phrase_forms(tmp_path):
    md = (
        "- [ ] T024: a `a.py`\n"
        "- [ ] T025a: b -> uses T024 -> T025a `b.py`\n"
        "- [ ] T026: c `c.py`\n"
        "\n## Dependencies\nT026 depends on T025a\nT025a blocks T027\n"
        "- [ ] T027: d `d.py`\n"
    )
    orch = _parse(tmp_path, md)
    graph = orch.analyze_dependencies()
    assert "T025a" in graph["T026"]


def test_unlabelled_fallback_never_collides_with_authored(tmp_path):
    # Suffixed lines at ordinal positions equal to real authored ids (the
    # regression: positions 1.. mapped onto T001/T002/... authored below).
    md = (
        "- [ ] T001a: sub one `a.py`\n"
        "- [ ] T002a: sub two `b.py`\n"
        "- [ ] unlabelled work `c.py`\n"
        "- [ ] T001: real one `d.py`\n"
        "- [ ] T002: real two `e.py`\n"
        "- [ ] T003: real three `f.py`\n"
    )
    orch = _parse(tmp_path, md)  # must not SystemExit on duplicates
    ids = [t.id for t in orch.tasks]
    assert len(ids) == len(set(ids))
    assert ids[:2] == ["T001a", "T002a"]
    assert ids[2] not in {"T001", "T002", "T003"}
    assert ids[3:] == ["T001", "T002", "T003"]


def test_lightweight_all_unlabelled_ids_contiguous(tmp_path):
    orch = _parse(tmp_path, "- [ ] one `a.py`\n- [ ] two `b.py`\n- [ ] three `c.py`\n")
    assert [t.id for t in orch.tasks] == ["T001", "T002", "T003"]


def test_executor_marks_suffix_line_only(tmp_path):
    content = "- [ ] T025: parent\n- [ ] T025a: sub\n- [x] unlabelled thing\n"
    ex = _executor_for(tmp_path / "tasks.md")
    sub = {"task_id": "T025a", "authored_id": "T025a", "instruction": "T025a: sub"}
    parent = {"task_id": "T025", "authored_id": "T025", "instruction": "T025: parent"}
    assert ex._find_task_state(content, sub) == (True, False)
    assert ex._find_task_state(content, parent) == (True, False)
    # legacy plan without authored_id: derived from instruction text
    legacy = {"task_id": "T002", "authored_id": "", "instruction": "T025a: sub"}
    assert ex._authored_id_for(legacy) == "T025a"
    # unlabelled still matched by instruction (find_task_line step 3)
    unl = {"task_id": "T003", "authored_id": "", "instruction": "unlabelled thing"}
    assert ex._find_task_state(content, unl) == (True, True)


# --------------------------------------------------------------------------
# Continuation lines: a dependency on the second or later line of a task
# (Spec Kit wraps long task text with an indent) must still create an edge.
# --------------------------------------------------------------------------


def test_dependency_on_continuation_line_is_honored(tmp_path):
    orch = _orchestrate(
        tmp_path,
        "## Phase 1\n\n"
        "- [ ] T001 Edit `a.py`.\n"
        "- [ ] T002 Edit `b.py`. This task text is long and wraps\n"
        "  onto a second line. Needs T001 first.\n"
        "  Verify: `python3 -m pytest -q`\n",
    )
    by_id = {t.id: t for t in orch.tasks}
    assert set(by_id) == {"T001", "T002"}
    assert by_id["T002"].dependencies == ["T001"]
    graph = orch.analyze_dependencies()
    assert "T001" in graph["T002"]


def test_continuation_dependency_orders_waves(tmp_path):
    orch = _orchestrate(
        tmp_path,
        "## Phase 1\n\n"
        "- [ ] T001 [P] Edit `a.py`.\n"
        "- [ ] T002 [P] Edit `b.py` and wrap\n"
        "  the text. Needs T001 and\n"
        "  more words first.\n",
    )
    orch.create_waves()
    waves = [[t["task_id"] for t in w.tasks] for w in orch.waves]
    assert waves == [["T001"], ["T002"]]


def test_unindented_text_after_task_is_not_continuation(tmp_path):
    orch = _orchestrate(
        tmp_path,
        "- [ ] T001 Edit `a.py`.\n"
        "Needs T009 first.\n",
    )
    assert orch.tasks[0].dependencies == []

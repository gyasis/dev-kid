"""
Unit tests for cli/sentinel/cascade_analyzer.py

Tests:
  - ChangeRadiusEvaluator: budget passes (1 file, 15 lines)
  - ChangeRadiusEvaluator: budget exceeded (4 files)
  - CascadeAnalyzer.annotate_tasks: annotates correct pending tasks
  - CascadeAnalyzer.annotate_tasks: does NOT annotate completed [x] tasks
  - CascadeAnalyzer.cascade_human_gated: raises WaveHaltError on 'h' input
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.sentinel.cascade_analyzer import (
    CascadeAnalyzer,
    ChangeRadiusEvaluator,
    WaveHaltError,
)
from cli.sentinel import InterfaceChangeReport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_config(max_files=3, max_lines=150, allow_interface=False):
    cfg = MagicMock()
    cfg.sentinel_radius_max_files = max_files
    cfg.sentinel_radius_max_lines = max_lines
    cfg.sentinel_radius_allow_interface_changes = allow_interface
    return cfg


def _make_interface_report(file_path="src/auth.py", breaking=None, non_breaking=None):
    return InterfaceChangeReport(
        file_path=file_path,
        language="python",
        breaking_changes=breaking or [],
        non_breaking_changes=non_breaking or [],
        modified_signatures=[],
        is_breaking=bool(breaking),
        detection_method="ast",
    )


def _empty_plan():
    return {"execution_plan": {"waves": []}}


# ---------------------------------------------------------------------------
# ChangeRadiusEvaluator
# ---------------------------------------------------------------------------

class TestChangeRadiusEvaluator:
    def test_within_budget_passes(self):
        config = _make_config()
        evaluator = ChangeRadiusEvaluator(config)

        files_changed = [{"path": "src/auth.py", "lines_added": 8, "lines_removed": 7}]
        report = evaluator.evaluate(files_changed, [], _empty_plan())

        assert report.budget_exceeded is False
        assert report.violations == []
        assert report.files_changed_count == 1
        assert report.lines_changed_total == 15

    def test_too_many_files_exceeds_budget(self):
        config = _make_config(max_files=3)
        evaluator = ChangeRadiusEvaluator(config)

        files_changed = [
            {"path": f"src/file{i}.py", "lines_added": 1, "lines_removed": 0}
            for i in range(4)
        ]
        report = evaluator.evaluate(files_changed, [], _empty_plan())

        assert report.budget_exceeded is True
        assert "files" in report.violations

    def test_too_many_lines_exceeds_budget(self):
        config = _make_config(max_lines=150)
        evaluator = ChangeRadiusEvaluator(config)

        files_changed = [{"path": "src/big.py", "lines_added": 100, "lines_removed": 60}]
        report = evaluator.evaluate(files_changed, [], _empty_plan())

        assert report.budget_exceeded is True
        assert "lines" in report.violations

    def test_interface_change_triggers_cascade_when_not_allowed(self):
        config = _make_config(allow_interface=False)
        evaluator = ChangeRadiusEvaluator(config)

        iface_report = _make_interface_report(non_breaking=["add_user"])
        report = evaluator.evaluate([], [iface_report], _empty_plan())

        assert report.budget_exceeded is True
        assert "interface" in report.violations

    def test_interface_change_ok_when_allowed(self):
        config = _make_config(allow_interface=True)
        evaluator = ChangeRadiusEvaluator(config)

        iface_report = _make_interface_report(non_breaking=["add_user"])
        report = evaluator.evaluate([], [iface_report], _empty_plan())

        assert "interface" not in report.violations

    def test_cross_wave_conflict_detected(self):
        config = _make_config()
        evaluator = ChangeRadiusEvaluator(config)

        plan = {
            "execution_plan": {
                "waves": [{
                    "wave_id": 2,
                    "tasks": [{
                        "task_id": "T010",
                        "file_locks": ["src/auth.py"],
                    }]
                }]
            }
        }
        files_changed = [{"path": "src/auth.py", "lines_added": 1, "lines_removed": 0}]
        report = evaluator.evaluate(files_changed, [], plan)

        assert "cross_wave" in report.violations


# ---------------------------------------------------------------------------
# CascadeAnalyzer.annotate_tasks
# ---------------------------------------------------------------------------

class TestAnnotateTasks:
    def _tasks_md(self, content: str) -> Path:
        f = Path(tempfile.mktemp(suffix=".md"))
        f.write_text(content, encoding='utf-8')
        return f

    def test_annotates_pending_task(self):
        content = (
            "- [ ] T010 [US1] Implement auth in src/auth.py\n"
            "- [x] T009 Already done\n"
        )
        f = self._tasks_md(content)
        analyzer = CascadeAnalyzer()
        iface = _make_interface_report()

        annotations = analyzer.annotate_tasks(["T010"], "SENTINEL-T001", [iface], f)

        updated = f.read_text(encoding='utf-8')
        f.unlink()

        assert len(annotations) == 1
        assert annotations[0].target_task_id == "T010"
        assert "SENTINEL CASCADE WARNING" in updated

    def test_does_not_annotate_completed_task(self):
        content = "- [x] T010 [US1] Already done\n"
        f = self._tasks_md(content)
        analyzer = CascadeAnalyzer()

        annotations = analyzer.annotate_tasks(["T010"], "SENTINEL-T001", [], f)

        updated = f.read_text(encoding='utf-8')
        f.unlink()

        assert len(annotations) == 0
        assert "CASCADE WARNING" not in updated

    def test_no_match_for_unknown_task_id(self):
        content = "- [ ] T020 Some other task\n"
        f = self._tasks_md(content)
        analyzer = CascadeAnalyzer()

        annotations = analyzer.annotate_tasks(["T999"], "SENTINEL-T001", [], f)
        f.unlink()

        assert len(annotations) == 0

    def test_multiple_pending_tasks_annotated(self):
        content = (
            "- [ ] T010 task A\n"
            "- [ ] T011 task B\n"
        )
        f = self._tasks_md(content)
        analyzer = CascadeAnalyzer()

        annotations = analyzer.annotate_tasks(["T010", "T011"], "SENTINEL-T001", [], f)
        f.unlink()

        assert len(annotations) == 2


# ---------------------------------------------------------------------------
# CascadeAnalyzer.cascade_human_gated
# ---------------------------------------------------------------------------

class TestCascadeHumanGated:
    def test_h_input_raises_wave_halt_error(self):
        analyzer = CascadeAnalyzer()

        with patch("builtins.input", return_value="h"):
            try:
                analyzer.cascade_human_gated(["T010"], "SENTINEL-T001")
                assert False, "WaveHaltError expected"
            except WaveHaltError:
                pass

    def test_r_input_raises_wave_halt_error(self):
        analyzer = CascadeAnalyzer()

        with patch("builtins.input", return_value="r"), \
             patch.object(analyzer, "annotate_tasks", return_value=[]):
            try:
                analyzer.cascade_human_gated(["T010"], "SENTINEL-T001", [])
                assert False, "WaveHaltError expected"
            except WaveHaltError:
                pass

    def test_a_input_does_not_raise(self):
        analyzer = CascadeAnalyzer()

        with patch("builtins.input", return_value="a"):
            # Should not raise
            analyzer.cascade_human_gated(["T010"], "SENTINEL-T001")

    def test_eof_input_raises_wave_halt_error(self):
        analyzer = CascadeAnalyzer()

        with patch("builtins.input", side_effect=EOFError):
            try:
                analyzer.cascade_human_gated(["T010"], "SENTINEL-T001")
                assert False, "WaveHaltError expected"
            except WaveHaltError:
                pass

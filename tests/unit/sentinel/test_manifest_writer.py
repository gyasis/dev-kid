"""
Unit tests for cli/sentinel/manifest_writer.py

Tests:
  - manifest.json written with correct required fields
  - diff.patch written (empty bytes when no files)
  - summary.md written for PASS and FAIL cases
  - No exception raised on FAIL result
  - Output directory created if it does not exist
"""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.sentinel.manifest_writer import ManifestWriter
from cli.sentinel import ManifestData, ManifestPaths, TierResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_data(
    *,
    result: str = "PASS",
    tier_used: int = 1,
    task_id: str = "T001",
    sentinel_id: str = "SENTINEL-T001",
    files_changed: list | None = None,
) -> ManifestData:
    ts = datetime.now(timezone.utc).isoformat()
    t1 = TierResult(attempted=True, final_status=result, iterations=2, cost_usd=0.0, duration_sec=10.5)
    return ManifestData(
        task_id=task_id,
        sentinel_id=sentinel_id,
        result=result,
        timestamp=ts,
        tier_used=tier_used,
        tier1_result=t1,
        files_changed=files_changed or [],
    )


def _tmp_dir() -> Path:
    d = Path(tempfile.mkdtemp())
    return d


# ---------------------------------------------------------------------------
# manifest.json schema
# ---------------------------------------------------------------------------

class TestManifestJson:
    REQUIRED_FIELDS = {
        "task_id", "sentinel_id", "result", "timestamp", "tier_used",
        "tiers", "files_changed", "interface_changes",
        "cascade_triggered", "cascade_tasks_annotated", "radius",
    }

    def test_required_fields_present(self):
        out = _tmp_dir() / "SENTINEL-T001"
        writer = ManifestWriter(out)
        data = _make_data()
        paths = writer.write(data)

        manifest = json.loads(paths.manifest_json.read_text())
        for field in self.REQUIRED_FIELDS:
            assert field in manifest, f"Missing field: {field}"

    def test_result_field_value(self):
        out = _tmp_dir() / "SENTINEL-T002"
        writer = ManifestWriter(out)
        paths = writer.write(_make_data(result="PASS"))
        manifest = json.loads(paths.manifest_json.read_text())
        assert manifest["result"] == "PASS"

    def test_result_fail_value(self):
        out = _tmp_dir() / "SENTINEL-T003"
        writer = ManifestWriter(out)
        paths = writer.write(_make_data(result="FAIL"))
        manifest = json.loads(paths.manifest_json.read_text())
        assert manifest["result"] == "FAIL"

    def test_tier_used_stored(self):
        out = _tmp_dir() / "SENTINEL-T004"
        writer = ManifestWriter(out)
        paths = writer.write(_make_data(tier_used=2))
        manifest = json.loads(paths.manifest_json.read_text())
        assert manifest["tier_used"] == 2

    def test_valid_json_written(self):
        out = _tmp_dir() / "SENTINEL-T005"
        writer = ManifestWriter(out)
        paths = writer.write(_make_data())
        # Should not raise
        content = paths.manifest_json.read_text()
        parsed = json.loads(content)
        assert isinstance(parsed, dict)

    def test_files_changed_stored(self):
        out = _tmp_dir() / "SENTINEL-T006"
        writer = ManifestWriter(out)
        fc = [{"path": "src/auth.py", "lines_added": 5, "lines_removed": 2}]
        paths = writer.write(_make_data(files_changed=fc))
        manifest = json.loads(paths.manifest_json.read_text())
        assert len(manifest["files_changed"]) == 1
        assert manifest["files_changed"][0]["path"] == "src/auth.py"


# ---------------------------------------------------------------------------
# diff.patch
# ---------------------------------------------------------------------------

class TestDiffPatch:
    def test_empty_files_writes_empty_patch(self):
        out = _tmp_dir() / "SENTINEL-T007"
        writer = ManifestWriter(out)
        patch_path = writer.write_diff_patch([])
        assert patch_path.exists()
        assert patch_path.read_bytes() == b''

    def test_patch_file_written_even_on_git_failure(self):
        out = _tmp_dir() / "SENTINEL-T008"
        writer = ManifestWriter(out)
        # Simulate git not available
        with patch("subprocess.run", side_effect=FileNotFoundError("git not found")):
            patch_path = writer.write_diff_patch(["src/auth.py"])
        assert patch_path.exists()
        assert patch_path.read_text() == ''

    def test_patch_file_written_on_timeout(self):
        import subprocess
        out = _tmp_dir() / "SENTINEL-T009"
        writer = ManifestWriter(out)
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30)):
            patch_path = writer.write_diff_patch(["src/auth.py"])
        assert patch_path.exists()

    def test_patch_captures_git_output(self):
        out = _tmp_dir() / "SENTINEL-T010"
        writer = ManifestWriter(out)
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "--- a/src/auth.py\n+++ b/src/auth.py\n@@ -1 +1 @@\n-old\n+new\n"
        with patch("subprocess.run", return_value=mock_result):
            patch_path = writer.write_diff_patch(["src/auth.py"])
        content = patch_path.read_text()
        assert "--- a/src/auth.py" in content


# ---------------------------------------------------------------------------
# summary.md
# ---------------------------------------------------------------------------

class TestSummaryMd:
    def test_pass_summary_contains_pass(self):
        out = _tmp_dir() / "SENTINEL-T011"
        writer = ManifestWriter(out)
        paths = writer.write(_make_data(result="PASS"))
        content = paths.summary_md.read_text()
        assert "PASS" in content

    def test_fail_summary_contains_wave_halted(self):
        out = _tmp_dir() / "SENTINEL-T012"
        writer = ManifestWriter(out)
        paths = writer.write(_make_data(result="FAIL"))
        content = paths.summary_md.read_text()
        assert "WAVE HALTED" in content or "FAIL" in content

    def test_summary_contains_sentinel_id(self):
        out = _tmp_dir() / "SENTINEL-T013"
        writer = ManifestWriter(out)
        data = _make_data(sentinel_id="SENTINEL-T999")
        paths = writer.write(data)
        content = paths.summary_md.read_text()
        assert "SENTINEL-T999" in content

    def test_summary_contains_tier(self):
        out = _tmp_dir() / "SENTINEL-T014"
        writer = ManifestWriter(out)
        paths = writer.write(_make_data(tier_used=2))
        content = paths.summary_md.read_text()
        assert "2" in content

    def test_summary_is_markdown(self):
        out = _tmp_dir() / "SENTINEL-T015"
        writer = ManifestWriter(out)
        paths = writer.write(_make_data())
        content = paths.summary_md.read_text()
        assert "##" in content  # Has markdown headings


# ---------------------------------------------------------------------------
# No exception on FAIL
# ---------------------------------------------------------------------------

class TestNoExceptionOnFail:
    def test_fail_result_does_not_raise(self):
        out = _tmp_dir() / "SENTINEL-FAIL"
        writer = ManifestWriter(out)
        data = _make_data(result="FAIL")
        # Should not raise any exception
        paths = writer.write(data)
        assert paths.manifest_json.exists()
        assert paths.summary_md.exists()

    def test_error_result_does_not_raise(self):
        out = _tmp_dir() / "SENTINEL-ERROR"
        writer = ManifestWriter(out)
        data = _make_data(result="ERROR")
        paths = writer.write(data)
        manifest = json.loads(paths.manifest_json.read_text())
        assert manifest["result"] == "ERROR"


# ---------------------------------------------------------------------------
# Output directory creation
# ---------------------------------------------------------------------------

class TestOutputDirCreation:
    def test_creates_nested_directory(self):
        base = Path(tempfile.mkdtemp())
        out = base / "deep" / "nested" / "SENTINEL-T001"
        writer = ManifestWriter(out)
        data = _make_data()
        paths = writer.write(data)
        assert out.exists()
        assert paths.manifest_json.exists()

    def test_returns_manifest_paths_type(self):
        out = _tmp_dir() / "SENTINEL-T002"
        writer = ManifestWriter(out)
        paths = writer.write(_make_data())
        assert isinstance(paths, ManifestPaths)
        assert isinstance(paths.manifest_json, Path)
        assert isinstance(paths.diff_patch, Path)
        assert isinstance(paths.summary_md, Path)

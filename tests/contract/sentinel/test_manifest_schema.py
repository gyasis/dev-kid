"""
Contract tests for manifest.json schema

Validates that every field required by contracts/change-manifest.md is present
and that result is one of the valid values.

Tests:
  - All required top-level fields present
  - result field is one of PASS/FAIL/ERROR
  - tiers sub-object has tier1 and tier2 keys
  - tiers.tier1 / tiers.tier2 have required keys
  - Numeric fields are numeric (not strings)
"""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cli.sentinel.manifest_writer import ManifestWriter
from cli.sentinel import ManifestData, TierResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUIRED_TOP_LEVEL = {
    "task_id",
    "sentinel_id",
    "result",
    "timestamp",
    "tier_used",
    "tiers",
    "placeholder_violations",
    "files_changed",
    "interface_changes",
    "tests_fixed",
    "tests_still_failing",
    "fix_reason",
    "cascade_triggered",
    "cascade_tasks_annotated",
    "radius",
}

REQUIRED_TIER_KEYS = {
    "attempted",
    "skipped",
    "model",
    "ollama_url",
    "iterations",
    "cost_usd",
    "duration_sec",
    "final_status",
    "error_messages",
}

VALID_RESULTS = {"PASS", "FAIL", "ERROR"}


def _build_manifest(result: str = "PASS", tier_used: int = 1) -> dict:
    """Write a manifest and return the parsed JSON."""
    out = Path(tempfile.mkdtemp()) / "SENTINEL-T001"
    writer = ManifestWriter(out)
    t1 = TierResult(
        attempted=True,
        final_status=result if tier_used == 1 else None,
        iterations=3,
        cost_usd=0.123,
        duration_sec=45.6,
        model="qwen3-coder:30b",
    )
    t2 = TierResult(
        attempted=(tier_used == 2),
        final_status=result if tier_used == 2 else None,
        iterations=5 if tier_used == 2 else 0,
        cost_usd=0.856 if tier_used == 2 else 0.0,
        duration_sec=95.2 if tier_used == 2 else 0.0,
        model="claude-sonnet-4-20250514" if tier_used == 2 else None,
    )
    data = ManifestData(
        task_id="T001",
        sentinel_id="SENTINEL-T001",
        result=result,
        timestamp=datetime.now(timezone.utc).isoformat(),
        tier_used=tier_used,
        tier1_result=t1,
        tier2_result=t2,
        files_changed=[{"path": "src/auth.py", "lines_added": 5, "lines_removed": 2}],
        tests_fixed=["test_login"],
        tests_still_failing=[],
        fix_reason="Added missing token validation",
        cascade_triggered=False,
    )
    paths = writer.write(data)
    return json.loads(paths.manifest_json.read_text())


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------

class TestRequiredFields:
    def test_all_required_top_level_fields_present(self):
        manifest = _build_manifest()
        missing = REQUIRED_TOP_LEVEL - set(manifest.keys())
        assert not missing, f"Missing required fields: {missing}"

    def test_tiers_has_tier1_and_tier2(self):
        manifest = _build_manifest()
        assert "tier1" in manifest["tiers"]
        assert "tier2" in manifest["tiers"]

    def test_tier1_has_required_keys(self):
        manifest = _build_manifest()
        tier1 = manifest["tiers"]["tier1"]
        missing = REQUIRED_TIER_KEYS - set(tier1.keys())
        assert not missing, f"tier1 missing keys: {missing}"

    def test_tier2_has_required_keys(self):
        manifest = _build_manifest()
        tier2 = manifest["tiers"]["tier2"]
        missing = REQUIRED_TIER_KEYS - set(tier2.keys())
        assert not missing, f"tier2 missing keys: {missing}"


# ---------------------------------------------------------------------------
# Result validation
# ---------------------------------------------------------------------------

class TestResultField:
    def test_result_pass_valid(self):
        manifest = _build_manifest(result="PASS")
        assert manifest["result"] in VALID_RESULTS

    def test_result_fail_valid(self):
        manifest = _build_manifest(result="FAIL")
        assert manifest["result"] in VALID_RESULTS

    def test_result_error_valid(self):
        manifest = _build_manifest(result="ERROR")
        assert manifest["result"] in VALID_RESULTS

    def test_result_is_string(self):
        manifest = _build_manifest()
        assert isinstance(manifest["result"], str)


# ---------------------------------------------------------------------------
# Numeric field types
# ---------------------------------------------------------------------------

class TestNumericFields:
    def test_tier_used_is_int(self):
        manifest = _build_manifest(tier_used=1)
        assert isinstance(manifest["tier_used"], int)

    def test_tier1_iterations_is_int(self):
        manifest = _build_manifest()
        assert isinstance(manifest["tiers"]["tier1"]["iterations"], int)

    def test_tier1_cost_usd_is_float(self):
        manifest = _build_manifest()
        assert isinstance(manifest["tiers"]["tier1"]["cost_usd"], (int, float))

    def test_tier1_duration_sec_is_float(self):
        manifest = _build_manifest()
        assert isinstance(manifest["tiers"]["tier1"]["duration_sec"], (int, float))


# ---------------------------------------------------------------------------
# Array fields
# ---------------------------------------------------------------------------

class TestArrayFields:
    def test_files_changed_is_list(self):
        manifest = _build_manifest()
        assert isinstance(manifest["files_changed"], list)

    def test_tests_fixed_is_list(self):
        manifest = _build_manifest()
        assert isinstance(manifest["tests_fixed"], list)

    def test_tests_still_failing_is_list(self):
        manifest = _build_manifest()
        assert isinstance(manifest["tests_still_failing"], list)

    def test_cascade_tasks_annotated_is_list(self):
        manifest = _build_manifest()
        assert isinstance(manifest["cascade_tasks_annotated"], list)

    def test_placeholder_violations_is_list(self):
        manifest = _build_manifest()
        assert isinstance(manifest["placeholder_violations"], list)


# ---------------------------------------------------------------------------
# Tier 2 escalation scenario
# ---------------------------------------------------------------------------

class TestTier2Escalation:
    def test_tier2_escalation_manifest_valid(self):
        manifest = _build_manifest(result="PASS", tier_used=2)
        assert manifest["tier_used"] == 2
        tier2 = manifest["tiers"]["tier2"]
        assert tier2["attempted"] is True
        assert tier2["iterations"] > 0
        assert manifest["result"] == "PASS"

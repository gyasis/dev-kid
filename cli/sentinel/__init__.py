"""
cli/sentinel/ — Integration Sentinel shared dataclasses

All sentinel modules import these dataclasses from here.

===========================================================================
SENTINEL CHECKPOINT PRINCIPLES (general — read before changing checkpoint logic)
===========================================================================
Hard-won from the gentle-eye Rust dogfood (2026-05-28). Full rationale:
docs/architecture/SENTINEL_ORCHESTRATOR_REWORK_2026-05-28.md.

P1 — A checkpoint validates a REAL, COMPLETE, COMPILABLE artifact, never a stub.
   Placing a sentinel on a skeleton/stub/placeholder makes it gate on something
   that *cannot* pass → the wave halts on a non-bug. Mark checkpoints (`[S]`) only
   where a genuine, self-consistent file exists whose dependencies are already
   green ("safely fixable in isolation"). This is predicate B.

P2 — Intelligence in the AUTHOR, mechanism in the ORCHESTRATOR.
   The task-authoring agent knows which outputs are real+complete file-points and
   MARKS them (`[S]`). The orchestrator stays a dumb gather-and-mark process: it
   reads the marker and places the sentinel — it does NOT try to infer
   compilability itself. Keep that split.

P3 — Attribute errors to their ORIGIN, not the artifact under repair.
   A single-file fixer (ma-loop) must never mangle a correct file A to chase an
   error that actually lives in dependency B. Parse the compiler's structured
   output (rustc `--message-format=json` primary span) to find the originating
   file; if it isn't the file under repair, the agent fixes the ORIGIN and
   re-tests — it does not "fix" the symptom at the call site.

P4 — Whole-suite vs per-unit gating is a DELIBERATE choice.
   If the checkpoint test is whole-crate / whole-suite (`cargo check` on the whole
   crate), intermediate checkpoints can't pass until the suite is complete. Pick
   one on purpose: (a) gate only at completion, (b) make the test per-unit, or
   (c) let P3 attribution build-forward the missing units (the failing checkpoint
   routes fixes into the unbuilt dependencies). Don't place intermediate
   whole-suite checkpoints and expect them to pass green on a partial tree.
===========================================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Tier results
# ---------------------------------------------------------------------------


@dataclass
class TierResult:
    """Result of running one tier of the micro-agent test loop."""

    attempted: bool = False
    skipped: bool = False
    tier_name: str = ""  # e.g. "local-quick", "azure-heavy"
    tier_index: int = -1  # 0-based index in the tiers list
    model: str | None = None
    ollama_url: str | None = None
    iterations: int = 0
    cost_usd: float = 0.0
    duration_sec: float = 0.0
    final_status: str | None = None  # "PASS" | "FAIL" | None
    error_messages: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return self.final_status == "PASS"

    @property
    def failed(self) -> bool:
        return self.final_status == "FAIL"


# ---------------------------------------------------------------------------
# Sentinel result
# ---------------------------------------------------------------------------


@dataclass
class SentinelResult:
    """Final result returned by SentinelRunner.run()."""

    task_id: str
    sentinel_id: str
    result: str = "PASS"  # "PASS" | "FAIL" | "ERROR" | "SKIP"
    should_halt_wave: bool = False
    error_message: str = ""
    tier_used: int = 0
    tier_name_used: str = ""  # e.g. "azure-heavy"
    # N-tier results list (used when tiers_file is configured)
    tier_results: list[TierResult] = field(default_factory=list)
    # Legacy fields — populated for backward compat with manifest writer
    tier1_result: TierResult = field(default_factory=TierResult)
    tier2_result: TierResult = field(default_factory=TierResult)
    placeholder_violations: list = field(default_factory=list)
    files_changed: list[dict] = field(default_factory=list)
    interface_reports: list = field(default_factory=list)
    cascade_triggered: bool = False
    cascade_tasks_annotated: list[str] = field(default_factory=list)
    manifest_paths: object | None = None


# ---------------------------------------------------------------------------
# Placeholder violation
# ---------------------------------------------------------------------------


@dataclass
class PlaceholderViolation:
    """A detected placeholder pattern in a production file."""

    file_path: str
    line_number: int  # 1-based
    matched_pattern: str  # Regex pattern string that matched
    matched_text: str  # Actual text that matched
    context_lines: list[str] = field(default_factory=list)  # ±2 surrounding lines


# ---------------------------------------------------------------------------
# Interface change report
# ---------------------------------------------------------------------------


@dataclass
class InterfaceChangeReport:
    """Public API surface changes between two file versions."""

    file_path: str
    language: str  # "python" | "typescript" | "javascript" | "rust" | "unknown"
    breaking_changes: list[str] = field(default_factory=list)  # Removed/renamed symbols
    non_breaking_changes: list[str] = field(default_factory=list)  # Added symbols
    modified_signatures: list[dict] = field(
        default_factory=list
    )  # [{name, old_sig, new_sig}]
    is_breaking: bool = False
    detection_method: str = "none"  # "ast" | "regex" | "none"


# ---------------------------------------------------------------------------
# Change radius report
# ---------------------------------------------------------------------------


@dataclass
class ChangeRadiusReport:
    """Three-axis budget evaluation result."""

    files_changed_count: int = 0
    lines_changed_total: int = 0
    interface_changes_count: int = 0
    budget_files: int = 3
    budget_lines: int = 150
    allow_interface_changes: bool = False
    cross_wave_files: list[str] = field(default_factory=list)
    budget_exceeded: bool = False
    violations: list[str] = field(
        default_factory=list
    )  # ["files", "lines", "interface", "cross_wave"]


# ---------------------------------------------------------------------------
# Cascade annotation
# ---------------------------------------------------------------------------


@dataclass
class CascadeAnnotation:
    """A compatibility warning appended to a pending task."""

    target_task_id: str
    sentinel_id: str
    changed_files: list[str] = field(default_factory=list)
    interface_changes: list[str] = field(default_factory=list)
    warning_text: str = ""
    applied_at: str = ""  # ISO 8601 timestamp


# ---------------------------------------------------------------------------
# Manifest data and paths
# ---------------------------------------------------------------------------


@dataclass
class ManifestData:
    """Full data for writing a Change Manifest."""

    task_id: str
    sentinel_id: str
    result: str  # "PASS" | "FAIL" | "ERROR" | "SKIP"
    timestamp: str  # ISO 8601
    tier_used: int
    tier1_result: TierResult = field(default_factory=TierResult)
    tier2_result: TierResult = field(default_factory=TierResult)
    placeholder_violations: list = field(default_factory=list)
    files_changed: list[dict] = field(
        default_factory=list
    )  # [{path, lines_added, lines_removed}]
    interface_changes: dict = field(
        default_factory=dict
    )  # {breaking:[], non_breaking:[], is_breaking: bool}
    tests_fixed: list[str] = field(default_factory=list)
    tests_still_failing: list[str] = field(default_factory=list)
    fix_reason: str = ""
    cascade_triggered: bool = False
    cascade_tasks_annotated: list[str] = field(default_factory=list)
    radius: dict = field(default_factory=dict)


@dataclass
class ManifestPaths:
    """Absolute paths to the three manifest files."""

    manifest_json: Path
    diff_patch: Path
    summary_md: Path


# ---------------------------------------------------------------------------
# Type alias for config (avoids circular import with config_manager)
# ---------------------------------------------------------------------------
# Consumers use: from cli.sentinel import SentinelConfig
# The actual type is cli.config_manager.ConfigSchema; we alias it here for
# consistent naming across sentinel modules.

try:
    from ..config_manager import ConfigSchema as SentinelConfig  # type: ignore[attr-defined]
except ImportError:
    SentinelConfig = object  # type: ignore[misc,assignment]

__all__ = [
    "TierResult",
    "SentinelResult",
    "PlaceholderViolation",
    "InterfaceChangeReport",
    "ChangeRadiusReport",
    "CascadeAnnotation",
    "ManifestData",
    "ManifestPaths",
    "SentinelConfig",
]

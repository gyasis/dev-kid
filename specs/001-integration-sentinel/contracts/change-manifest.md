# Contract: ManifestWriter
**Module**: `cli/sentinel/manifest_writer.py`
**Invoked by**: `SentinelRunner.run()` after all pipeline stages complete

---

## Interface

```python
class ManifestWriter:
    def __init__(self, output_dir: Path): ...
        """
        output_dir: .claude/sentinel/<SENTINEL-ID>/
        Created if it doesn't exist.
        """

    def write(self, data: ManifestData) -> ManifestPaths:
        """
        Write all three manifest artifacts atomically.

        Outputs:
            output_dir/manifest.json   — structured data
            output_dir/diff.patch      — exact diff (empty file if no changes)
            output_dir/summary.md      — human-readable text for context injection

        Returns:
            ManifestPaths with absolute paths to all three files
        Raises:
            IOError if output_dir cannot be created or files cannot be written
        """

    def write_diff_patch(self, files: list[str]) -> Path:
        """
        Capture current unstaged + staged diff for the given files.
        Runs: git diff HEAD -- <files>
        Writes to output_dir/diff.patch.
        Returns path to patch file.
        """

    def write_summary_md(self, data: ManifestData) -> Path:
        """
        Generate human-readable summary for context injection.
        Returns path to summary.md.
        """
```

## ManifestData

```python
@dataclass
class ManifestData:
    task_id: str
    sentinel_id: str
    result: str                          # PASS | FAIL | ERROR
    timestamp: str                       # ISO 8601
    tier_used: int                       # 1 or 2
    tier1_result: TierResult
    tier2_result: TierResult
    placeholder_violations: list         # list[PlaceholderViolation]
    files_changed: list[dict]            # [{path, lines_added, lines_removed}]
    interface_changes: dict              # {breaking: [], non_breaking: [], is_breaking: bool}
    tests_fixed: list[str]
    tests_still_failing: list[str]
    fix_reason: str                      # parsed from micro-agent output
    cascade_triggered: bool
    cascade_tasks_annotated: list[str]   # task IDs that received warnings
    radius: dict                         # ChangeRadius fields
```

## summary.md Format

```markdown
## Sentinel Report: SENTINEL-T003 — PASS

**Task**: T003 | **Tier**: 1 | **Result**: PASS
**Time**: 2026-02-20 14:32:00 | **Duration**: 45.2s | **Cost**: $0.00

### Changes Made
- `src/auth.py` — 12 added, 3 removed

### Tests Fixed
- `test_auth_login`, `test_auth_logout`

### Interface Changes
- Non-breaking: `add_user` (new function added)

### Cascade
No cascade triggered (radius within budget: 1 file, 15 lines, 1 non-breaking interface change).

### Action Required
None — tests pass. Review the diff at `.claude/sentinel/SENTINEL-T003/diff.patch` if needed.
```

## FAIL Summary Format

```markdown
## Sentinel Report: SENTINEL-T003 — FAIL

**Task**: T003 | **Tier**: 2 (Tier 1 exhausted) | **Result**: FAIL
**Time**: 2026-02-20 14:45:00 | **Duration**: 312s | **Cost**: $1.23

### Tests Still Failing
- `test_payment_process`: AssertionError: expected 200, got 500

### Changes Attempted (see diff.patch for details)
- `src/payment.py` — 8 added, 2 removed
- `src/stripe_client.py` — 3 added, 0 removed

### ⚠ WAVE HALTED
This sentinel run exhausted both tiers without passing tests. Manual intervention required.
Review the full change history in `.claude/sentinel/SENTINEL-T003/`.
```

## Invariants (must always hold)

1. `manifest.json` is valid JSON (validated before write)
2. `diff.patch` always exists (zero-byte if no changes)
3. `summary.md` always exists (minimum: result header line)
4. All three files written before `ManifestPaths` returned (atomic from caller's perspective)
5. Writing manifest NEVER raises on FAIL result (always completes)

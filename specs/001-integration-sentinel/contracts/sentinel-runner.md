# Contract: SentinelRunner
**Module**: `cli/sentinel/runner.py`
**Invoked by**: `cli/wave_executor.py` when `task["agent_role"] == "Sentinel"`

---

## Interface

```python
class SentinelRunner:
    def __init__(self, config: SentinelConfig, project_root: Path): ...

    def run(self, task: dict) -> SentinelResult:
        """
        Execute the full sentinel pipeline for a given sentinel task dict.

        Pipeline order:
          1. Resolve working directory and affected files from parent task
          2. PlaceholderScanner: scan files for forbidden patterns
          3. Test framework detection
          4. TierRunner.run_tier1() → if FAIL → TierRunner.run_tier2()
          5. InterfaceDiff: compare pre/post interface stability
          6. ChangeRadius: compute radius axes, detect violations
          7. CascadeAnalyzer: annotate pending tasks (if radius exceeded)
          8. ManifestWriter: write manifest.json + diff.patch + summary.md
          9. Mark SENTINEL-<task_id> as [x] in tasks.md

        Returns:
            SentinelResult with result=PASS|FAIL|ERROR
        """
```

## SentinelResult

```python
@dataclass
class SentinelResult:
    sentinel_id: str               # "SENTINEL-T003"
    parent_task_id: str            # "T003"
    result: str                    # "PASS" | "FAIL" | "ERROR"
    manifest_path: Path            # .claude/sentinel/SENTINEL-T003/manifest.json
    should_halt_wave: bool         # True if result is FAIL or ERROR
    cascade_triggered: bool        # True if radius exceeded and cascade ran
    error_message: Optional[str]   # Set only for result=ERROR
```

## Error Handling

| Condition | Behavior |
|-----------|----------|
| Ollama unreachable | Skip Tier 1, log warning, proceed to Tier 2 |
| No test framework detected | Skip test loop, run placeholder scan only, result=PASS |
| micro-agent crashes (exit -1) | Set result=ERROR, write manifest with error details, halt wave |
| tasks.md not writable | Raise RuntimeError (hard failure, wave halts) |
| manifest directory not creatable | Raise RuntimeError (hard failure, wave halts) |
| Both tiers exhausted | Set result=FAIL, write manifest, return should_halt_wave=True |

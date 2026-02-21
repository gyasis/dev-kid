# Contract: SentinelConfig (ConfigSchema Extension)
**Module**: `cli/config_manager.py` (modification)
**New Fields in ConfigSchema dataclass**

---

## New ConfigSchema Fields

```python
@dataclass
class ConfigSchema:
    # ... existing fields unchanged ...

    # Sentinel: master toggle
    sentinel_enabled: bool = True

    # Sentinel: operation mode
    sentinel_mode: str = "auto"  # "auto" | "human-gated"

    # Sentinel: Tier 1 (local Ollama)
    sentinel_tier1_model: str = "qwen3-coder:30b"
    sentinel_tier1_ollama_url: str = "http://192.168.0.159:11434"
    sentinel_tier1_max_iterations: int = 5

    # Sentinel: Tier 2 (cloud)
    sentinel_tier2_model: str = "claude-sonnet-4-20250514"
    sentinel_tier2_max_iterations: int = 10
    sentinel_tier2_max_budget_usd: float = 2.0
    sentinel_tier2_max_duration_min: int = 10

    # Sentinel: change radius
    sentinel_radius_max_files: int = 3
    sentinel_radius_max_lines: int = 150
    sentinel_radius_allow_interface_changes: bool = False

    # Sentinel: placeholder scanner
    sentinel_placeholder_fail_on_detect: bool = True
    sentinel_placeholder_patterns: list = field(default_factory=list)   # appended to built-ins
    sentinel_placeholder_exclude_paths: list = field(default_factory=list)  # appended to built-ins
```

## to_dict() Addition

```python
def to_dict(self) -> Dict[str, Any]:
    return {
        # ... existing sections ...
        "sentinel": {
            "enabled": self.sentinel_enabled,
            "mode": self.sentinel_mode,
            "tier1": {
                "model": self.sentinel_tier1_model,
                "ollama_url": self.sentinel_tier1_ollama_url,
                "max_iterations": self.sentinel_tier1_max_iterations,
            },
            "tier2": {
                "model": self.sentinel_tier2_model,
                "max_iterations": self.sentinel_tier2_max_iterations,
                "max_budget_usd": self.sentinel_tier2_max_budget_usd,
                "max_duration_min": self.sentinel_tier2_max_duration_min,
            },
            "change_radius": {
                "max_files": self.sentinel_radius_max_files,
                "max_lines": self.sentinel_radius_max_lines,
                "allow_interface_changes": self.sentinel_radius_allow_interface_changes,
            },
            "placeholder": {
                "fail_on_detect": self.sentinel_placeholder_fail_on_detect,
                "patterns": self.sentinel_placeholder_patterns,
                "exclude_paths": self.sentinel_placeholder_exclude_paths,
            }
        }
    }
```

## from_dict() Addition

```python
@classmethod
def from_dict(cls, data: Dict[str, Any]) -> 'ConfigSchema':
    # ... existing parsing ...
    sentinel = data.get("sentinel", {})
    tier1 = sentinel.get("tier1", {})
    tier2 = sentinel.get("tier2", {})
    radius = sentinel.get("change_radius", {})
    placeholder = sentinel.get("placeholder", {})

    return cls(
        # ... existing args ...
        sentinel_enabled=sentinel.get("enabled", True),
        sentinel_mode=sentinel.get("mode", "auto"),
        sentinel_tier1_model=tier1.get("model", "qwen3-coder:30b"),
        sentinel_tier1_ollama_url=tier1.get("ollama_url", "http://192.168.0.159:11434"),
        sentinel_tier1_max_iterations=tier1.get("max_iterations", 5),
        sentinel_tier2_model=tier2.get("model", "claude-sonnet-4-20250514"),
        sentinel_tier2_max_iterations=tier2.get("max_iterations", 10),
        sentinel_tier2_max_budget_usd=tier2.get("max_budget_usd", 2.0),
        sentinel_tier2_max_duration_min=tier2.get("max_duration_min", 10),
        sentinel_radius_max_files=radius.get("max_files", 3),
        sentinel_radius_max_lines=radius.get("max_lines", 150),
        sentinel_radius_allow_interface_changes=radius.get("allow_interface_changes", False),
        sentinel_placeholder_fail_on_detect=placeholder.get("fail_on_detect", True),
        sentinel_placeholder_patterns=placeholder.get("patterns", []),
        sentinel_placeholder_exclude_paths=placeholder.get("exclude_paths", []),
    )
```

## validate() Addition

```python
def validate(self) -> tuple[bool, List[str]]:
    issues = []
    # ... existing validations ...

    if self.sentinel_mode not in ("auto", "human-gated"):
        issues.append(f"sentinel.mode must be 'auto' or 'human-gated', got: {self.sentinel_mode!r}")

    if self.sentinel_tier1_max_iterations < 1:
        issues.append("sentinel.tier1.max_iterations must be >= 1")

    if self.sentinel_tier2_max_budget_usd <= 0:
        issues.append("sentinel.tier2.max_budget_usd must be > 0")

    if self.sentinel_radius_max_files < 1:
        issues.append("sentinel.change_radius.max_files must be >= 1")

    if self.sentinel_radius_max_lines < 1:
        issues.append("sentinel.change_radius.max_lines must be >= 1")

    return len(issues) == 0, issues
```

## dev-kid.yml Example

```yaml
sentinel:
  enabled: true
  mode: auto

  tier1:
    model: qwen3-coder:30b
    ollama_url: http://192.168.0.159:11434
    max_iterations: 5

  tier2:
    model: claude-sonnet-4-20250514
    max_iterations: 10
    max_budget_usd: 2.0
    max_duration_min: 10

  change_radius:
    max_files: 3
    max_lines: 150
    allow_interface_changes: false

  placeholder:
    fail_on_detect: true
    patterns:
      - "CUSTOM_STUB"
    exclude_paths:
      - "vendor/"
```

## Behavior When sentinel.enabled = false

- `orchestrator.py` skips all sentinel task injection
- Zero `SENTINEL-*` tasks appear in `execution_plan.json`
- Zero `SENTINEL-*` lines added to `tasks.md`
- Execution plan identical to pre-sentinel baseline (SC-007)

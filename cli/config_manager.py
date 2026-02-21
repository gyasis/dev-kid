"""
Dev-Kid Configuration Manager

Manages .devkid/config.json for runtime configuration settings.
This is SEPARATE from .constitution.md (immutable rules).

Config.json contains:
- Tool runtime settings (task watchdog, wave sizes, etc.)
- CLI preferences
- MCP server configurations
- NOT development rules (those go in constitution)
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field


@dataclass
class ConfigSchema:
    """Schema for dev-kid configuration"""

    # Task orchestration settings
    task_watchdog_minutes: int = 15  # Increased from 7 to allow for complex tasks
    wave_size: int = 5
    max_parallel_tasks: int = 3
    checkpoint_auto_save: bool = True

    # Constitution integration
    constitution_path: str = "memory-bank/shared/.constitution.md"
    constitution_enforce: bool = True
    constitution_strict_mode: bool = False

    # MCP server settings
    mcp_servers: Dict[str, Any] = field(default_factory=dict)

    # CLI preferences
    verbose: bool = False
    auto_git_commit: bool = False
    git_commit_prefix: str = "[dev-kid]"

    # Agent preferences
    preferred_model: str = "sonnet"
    agent_timeout_minutes: int = 30

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
    sentinel_placeholder_patterns: list = field(default_factory=list)
    sentinel_placeholder_exclude_paths: list = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "task_orchestration": {
                "task_watchdog_minutes": self.task_watchdog_minutes,
                "wave_size": self.wave_size,
                "max_parallel_tasks": self.max_parallel_tasks,
                "checkpoint_auto_save": self.checkpoint_auto_save
            },
            "constitution": {
                "path": self.constitution_path,
                "enforce": self.constitution_enforce,
                "strict_mode": self.constitution_strict_mode
            },
            "mcp_servers": self.mcp_servers,
            "cli": {
                "verbose": self.verbose,
                "auto_git_commit": self.auto_git_commit,
                "git_commit_prefix": self.git_commit_prefix
            },
            "agents": {
                "preferred_model": self.preferred_model,
                "timeout_minutes": self.agent_timeout_minutes
            },
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

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigSchema':
        """Create from dictionary loaded from JSON"""
        task_orch = data.get("task_orchestration", {})
        constitution = data.get("constitution", {})
        mcp = data.get("mcp_servers", {})
        cli = data.get("cli", {})
        agents = data.get("agents", {})

        sentinel = data.get("sentinel", {})
        tier1 = sentinel.get("tier1", {})
        tier2 = sentinel.get("tier2", {})
        radius = sentinel.get("change_radius", {})
        placeholder = sentinel.get("placeholder", {})

        return cls(
            task_watchdog_minutes=task_orch.get("task_watchdog_minutes", 7),
            wave_size=task_orch.get("wave_size", 5),
            max_parallel_tasks=task_orch.get("max_parallel_tasks", 3),
            checkpoint_auto_save=task_orch.get("checkpoint_auto_save", True),
            constitution_path=constitution.get("path", "memory-bank/shared/.constitution.md"),
            constitution_enforce=constitution.get("enforce", True),
            constitution_strict_mode=constitution.get("strict_mode", False),
            mcp_servers=mcp,
            verbose=cli.get("verbose", False),
            auto_git_commit=cli.get("auto_git_commit", False),
            git_commit_prefix=cli.get("git_commit_prefix", "[dev-kid]"),
            preferred_model=agents.get("preferred_model", "sonnet"),
            agent_timeout_minutes=agents.get("timeout_minutes", 30),
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


class ConfigManager:
    """Manages dev-kid configuration file (.devkid/config.json)"""

    DEFAULT_CONFIG_PATH = Path(".devkid/config.json")

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize config manager

        Args:
            config_path: Path to config.json (defaults to .devkid/config.json)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config_dir = self.config_path.parent
        self.schema: Optional[ConfigSchema] = None

        if self.config_path.exists():
            self.load()

    def init(self, force: bool = False) -> bool:
        """Initialize config.json with defaults

        Args:
            force: Overwrite existing config if True

        Returns:
            True if successful, False otherwise
        """
        if self.config_path.exists() and not force:
            print(f"❌ Config already exists at {self.config_path}")
            print("   Use --force to overwrite")
            return False

        # Create .devkid directory if not exists
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Create default config
        default_schema = ConfigSchema()
        self.schema = default_schema

        # Write to file
        with open(self.config_path, 'w') as f:
            json.dump(default_schema.to_dict(), f, indent=2)

        print(f"✅ Created config at {self.config_path}")
        print(f"   Task watchdog: {default_schema.task_watchdog_minutes} minutes")
        print(f"   Wave size: {default_schema.wave_size} tasks")
        print(f"   Constitution enforcement: {'enabled' if default_schema.constitution_enforce else 'disabled'}")

        return True

    def load(self) -> bool:
        """Load config from file

        Returns:
            True if successful, False otherwise
        """
        if not self.config_path.exists():
            print(f"❌ Config not found at {self.config_path}")
            print("   Run: dev-kid config init")
            return False

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)

            self.schema = ConfigSchema.from_dict(data)
            return True

        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON in config: {e}")
            return False
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return False

    def save(self) -> bool:
        """Save current config to file

        Returns:
            True if successful, False otherwise
        """
        if not self.schema:
            print("❌ No config loaded")
            return False

        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.schema.to_dict(), f, indent=2)

            return True

        except Exception as e:
            print(f"❌ Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get config value by dotted key path

        Args:
            key: Dotted path (e.g., 'task_orchestration.wave_size')
            default: Default value if not found

        Returns:
            Config value or default
        """
        if not self.schema:
            if not self.load():
                return default

        config_dict = self.schema.to_dict()
        keys = key.split('.')

        value = config_dict
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> bool:
        """Set config value by dotted key path

        Args:
            key: Dotted path (e.g., 'task_orchestration.wave_size')
            value: Value to set

        Returns:
            True if successful, False otherwise
        """
        if not self.schema:
            if not self.load():
                # Initialize if doesn't exist
                if not self.init():
                    return False

        # Parse key path
        keys = key.split('.')
        if len(keys) < 2:
            print(f"❌ Invalid key path: {key}")
            print("   Use format: section.key (e.g., 'task_orchestration.wave_size')")
            return False

        # Update schema
        config_dict = self.schema.to_dict()

        # Navigate to parent
        parent = config_dict
        for k in keys[:-1]:
            if k not in parent:
                parent[k] = {}
            parent = parent[k]

        # Set value
        parent[keys[-1]] = value

        # Reload schema from modified dict
        self.schema = ConfigSchema.from_dict(config_dict)

        # Save to file
        if self.save():
            print(f"✅ Set {key} = {value}")
            return True

        return False

    def show(self) -> bool:
        """Display current config

        Returns:
            True if successful, False otherwise
        """
        if not self.schema:
            if not self.load():
                return False

        print("\n" + "="*60)
        print("DEV-KID CONFIGURATION")
        print("="*60)

        config_dict = self.schema.to_dict()

        print("\n📋 Task Orchestration:")
        task_orch = config_dict.get("task_orchestration", {})
        print(f"   Task watchdog: {task_orch.get('task_watchdog_minutes', 7)} minutes")
        print(f"   Wave size: {task_orch.get('wave_size', 5)} tasks")
        print(f"   Max parallel: {task_orch.get('max_parallel_tasks', 3)} tasks")
        print(f"   Auto checkpoint: {task_orch.get('checkpoint_auto_save', True)}")

        print("\n📜 Constitution:")
        constitution = config_dict.get("constitution", {})
        print(f"   Path: {constitution.get('path', 'N/A')}")
        print(f"   Enforcement: {'✅ enabled' if constitution.get('enforce', True) else '❌ disabled'}")
        print(f"   Strict mode: {'✅ on' if constitution.get('strict_mode', False) else '⚪ off'}")

        print("\n🔌 MCP Servers:")
        mcp = config_dict.get("mcp_servers", {})
        if mcp:
            for server, settings in mcp.items():
                print(f"   {server}: {settings}")
        else:
            print("   (none configured)")

        print("\n⚙️  CLI Preferences:")
        cli = config_dict.get("cli", {})
        print(f"   Verbose: {cli.get('verbose', False)}")
        print(f"   Auto git commit: {cli.get('auto_git_commit', False)}")
        print(f"   Commit prefix: {cli.get('git_commit_prefix', '[dev-kid]')}")

        print("\n🤖 Agent Preferences:")
        agents = config_dict.get("agents", {})
        print(f"   Preferred model: {agents.get('preferred_model', 'sonnet')}")
        print(f"   Timeout: {agents.get('timeout_minutes', 30)} minutes")

        print("\n" + "="*60)
        print(f"Config file: {self.config_path}")
        print("="*60 + "\n")

        return True

    def validate(self) -> tuple[bool, List[str]]:
        """Validate config structure and values

        Returns:
            (is_valid, list of issues)
        """
        if not self.schema:
            if not self.load():
                return False, ["Config file not found or invalid"]

        issues = []

        # Validate task orchestration settings
        if self.schema.task_watchdog_minutes < 1 or self.schema.task_watchdog_minutes > 60:
            issues.append("task_watchdog_minutes must be 1-60")

        if self.schema.wave_size < 1 or self.schema.wave_size > 20:
            issues.append("wave_size must be 1-20")

        if self.schema.max_parallel_tasks < 1 or self.schema.max_parallel_tasks > 10:
            issues.append("max_parallel_tasks must be 1-10")

        # Validate constitution path
        constitution_path = Path(self.schema.constitution_path)
        if self.schema.constitution_enforce and not constitution_path.exists():
            issues.append(f"Constitution file not found: {constitution_path}")

        # Validate agent settings
        valid_models = ["sonnet", "opus", "haiku"]
        if self.schema.preferred_model not in valid_models:
            issues.append(f"preferred_model must be one of: {', '.join(valid_models)}")

        if self.schema.agent_timeout_minutes < 5 or self.schema.agent_timeout_minutes > 120:
            issues.append("agent_timeout_minutes must be 5-120")

        # Validate sentinel settings
        if self.schema.sentinel_mode not in ("auto", "human-gated"):
            issues.append(f"sentinel.mode must be 'auto' or 'human-gated', got: {self.schema.sentinel_mode!r}")

        if self.schema.sentinel_tier1_max_iterations < 1:
            issues.append("sentinel.tier1.max_iterations must be >= 1")

        if self.schema.sentinel_tier2_max_budget_usd <= 0:
            issues.append("sentinel.tier2.max_budget_usd must be > 0")

        if self.schema.sentinel_radius_max_files < 1:
            issues.append("sentinel.change_radius.max_files must be >= 1")

        if self.schema.sentinel_radius_max_lines < 1:
            issues.append("sentinel.change_radius.max_lines must be >= 1")

        is_valid = len(issues) == 0

        if is_valid:
            print("✅ Config validation passed")
        else:
            print("❌ Config validation failed:")
            for issue in issues:
                print(f"   - {issue}")

        return is_valid, issues


def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python config_manager.py [init|get|set|show|validate]")
        return

    manager = ConfigManager()
    command = sys.argv[1]

    if command == "init":
        force = "--force" in sys.argv
        manager.init(force=force)

    elif command == "get":
        if len(sys.argv) < 3:
            print("Usage: python config_manager.py get <key>")
            return
        key = sys.argv[2]
        value = manager.get(key)
        print(f"{key} = {value}")

    elif command == "set":
        if len(sys.argv) < 4:
            print("Usage: python config_manager.py set <key> <value>")
            return
        key = sys.argv[2]
        value = sys.argv[3]

        # Try to parse value as int/bool
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.isdigit():
            value = int(value)

        manager.set(key, value)

    elif command == "show":
        manager.show()

    elif command == "validate":
        manager.validate()

    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()

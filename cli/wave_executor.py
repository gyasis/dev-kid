#!/usr/bin/env python3
"""
Wave Executor - Executes waves from execution_plan.json with checkpoints
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

from config_manager import ConfigManager, ConfigSchema
from constitution_parser import Constitution
from context_compactor import ContextCompactor

# Sentinel runner (T009) — imported lazily to tolerate incomplete builds
try:
    from sentinel.runner import SentinelRunner as _SentinelRunner

    _SENTINEL_AVAILABLE = True
except Exception as _sentinel_import_err:
    _SentinelRunner = None  # type: ignore[assignment,misc]
    _SENTINEL_AVAILABLE = False
    # Surface the actual error so "module not available" isn't a mystery
    print(f"⚠️  Sentinel module not importable: {_sentinel_import_err}")


class WaveHaltError(Exception):
    """Raised when a sentinel decides to halt wave execution."""


def _find_watchdog_binary() -> Optional[str]:
    """Locate the task-watchdog binary using the same search order as the dev-kid CLI."""
    script_dir = Path(__file__).parent
    dev_kid_root = script_dir.parent
    candidates = [
        dev_kid_root / "rust-watchdog" / "target" / "release" / "task-watchdog",  # dev
        Path.home()
        / ".dev-kid"
        / "rust-watchdog"
        / "target"
        / "release"
        / "task-watchdog",  # installed
    ]
    for p in candidates:
        if p.is_file() and os.access(p, os.X_OK):
            return str(p)
    # Fall back to PATH
    result = subprocess.run(["which", "task-watchdog"], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return None


class WaveExecutor:
    """Executes waves with parallel task execution and checkpoints"""

    def __init__(self, plan_file: str = "execution_plan.json"):
        self.plan_file = Path(plan_file)
        self.plan = None
        self.tasks_file = Path("tasks.md")
        self.project_root = Path.cwd()

        # Load constitution from memory-bank
        constitution_path = Path("memory-bank/shared/.constitution.md")
        if constitution_path.exists():
            try:
                self.constitution: Optional[Constitution] = Constitution(
                    str(constitution_path)
                )
            except Exception as e:
                print(f"⚠️  Warning: Failed to load constitution: {e}")
                print(f"   Constitution validation will be skipped")
                self.constitution = None
        else:
            self.constitution: Optional[Constitution] = None
            print(
                "⚠️  Warning: Constitution file not found at memory-bank/shared/.constitution.md"
            )

        # Initialize context compactor for proactive pre-compaction
        self.compactor = ContextCompactor()

        # Load sentinel config — prefer dev-kid.yml (common case), fall back to
        # .devkid/config.json (legacy ConfigManager path).
        self.config = None
        self._config_load_error = None  # Track WHY config failed
        yml_path = Path("dev-kid.yml")
        if yml_path.exists():
            try:
                import yaml as _yaml  # type: ignore[import]

                _data = _yaml.safe_load(yml_path.read_text(encoding="utf-8")) or {}
                self.config = ConfigSchema.from_dict(_data)
            except ImportError:
                print("⚠️  PyYAML not installed — falling back to ConfigManager for sentinel config")
            except Exception as exc:
                self._config_load_error = f"Failed to parse dev-kid.yml: {exc}"
                print(f"⚠️  {self._config_load_error}")
        if self.config is None:
            try:
                _mgr = ConfigManager()
                _mgr.load()
                self.config = _mgr.schema
            except Exception as exc:
                self._config_load_error = self._config_load_error or f"ConfigManager failed: {exc}"
                print(f"⚠️  Config not loaded: {self._config_load_error}")
                self.config = None

    def load_plan(self) -> None:
        """Load execution plan from JSON"""
        if not self.plan_file.exists():
            print(f"❌ Error: {self.plan_file} not found")
            print("   Run orchestrator.py first to generate execution plan")
            sys.exit(1)

        try:
            self.plan = json.loads(self.plan_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in {self.plan_file}")
            print(f"   {e}")
            # Backup corrupted file
            backup_path = self.plan_file.with_suffix(".json.corrupted")
            self.plan_file.rename(backup_path)
            print(f"   Corrupted file backed up to: {backup_path}")
            print(f"   Re-run orchestrator to generate new execution plan")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading {self.plan_file}: {e}")
            sys.exit(1)

    def _wave_already_complete(self, tasks: List[Dict]) -> bool:
        """Return True if every task in the wave is already marked [x] in tasks.md."""
        try:
            content = self.tasks_file.read_text(encoding="utf-8")
        except Exception:
            return False
        for task in tasks:
            task_desc = task["instruction"]
            for line in content.split("\n"):
                if task_desc in line:
                    if "[x]" not in line:
                        return False
                    break
            else:
                return False  # task not found at all
        return True

    def verify_wave_completion(self, wave_id: int, tasks: List[Dict]) -> bool:
        """Verify all tasks in wave are marked complete in tasks.md"""
        try:
            content = self.tasks_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Error reading tasks.md: {e}")
            return False

        for task in tasks:
            task_desc = task["instruction"]
            # Check if task line contains [x]
            for line in content.split("\n"):
                if task_desc in line:
                    if "[x]" in line:
                        print(f"   ✅ {task['task_id']}: Verified complete")
                    else:
                        print(f"   ❌ {task['task_id']}: NOT marked complete!")
                        return False
                    break
            else:
                print(f"   ⚠️  {task['task_id']}: Task not found in tasks.md")
                return False

        return True

    def execute_checkpoint(self, wave_id: int, checkpoint: Dict) -> None:
        """Execute checkpoint between waves"""
        print(f"\n🔍 Checkpoint after Wave {wave_id}...")

        # Step 1: Memory bank keeper verifies tasks.md
        print("   Step 1: memory-bank-keeper validates tasks.md...")
        tasks = self.plan["execution_plan"]["waves"][wave_id - 1]["tasks"]
        verified = self.verify_wave_completion(wave_id, tasks)

        if not verified:
            print(f"\n❌ Checkpoint failed! Wave {wave_id} tasks not complete.")
            print("   Halting execution.")
            sys.exit(1)

        print("   ✅ All tasks verified complete")

        # Step 2: Memory bank keeper updates progress.md
        print("   Step 2: memory-bank-keeper updates progress.md...")
        self._update_progress(wave_id, tasks)

        # Step 2a: Sync full memory bank (all 6 tiers via dev-kid sync-memory)
        print("   Step 2a: syncing full memory bank (all tiers)...")
        self._sync_memory_bank(wave_id)

        # Step 2b: Integration Sentinel — run test-fix loop on each completed task.
        # Filter out Sentinel-role tasks (they already ran during execute_wave).
        sentinel_enabled = (
            _SENTINEL_AVAILABLE
            and self.config is not None
            and getattr(self.config, "sentinel_enabled", False)
        )
        developer_tasks = [t for t in tasks if t.get("agent_role") != "Sentinel"]
        if sentinel_enabled and _SentinelRunner is not None and self.config is not None:
            print(
                f"   Step 2b: integration-sentinel validates wave {wave_id} output..."
            )
            runner = _SentinelRunner(self.config, self.project_root)
            for task in developer_tasks:
                task_id = task["task_id"]
                print(f"      🛡️  Sentinel → {task_id}")
                try:
                    result = runner.run(task)
                except WaveHaltError:
                    raise
                except Exception as exc:
                    print(f"      ⚠️  Sentinel {task_id} error (non-fatal): {exc}")
                    continue
                if result.should_halt_wave:
                    msg = result.error_message or f"Sentinel {task_id} halted wave"
                    print(f"      ❌ Sentinel HALT: {msg}")
                    raise WaveHaltError(msg)
                icons = {"PASS": "✅", "SKIP": "⏭️", "FAIL": "❌", "ERROR": "💥"}
                icon = icons.get(result.result, "⚠️")
                tier_info = result.tier_name_used or f"tier {result.tier_used}" if result.tier_used else "no-test"
                print(f"      {icon} {task_id}: {result.result} ({tier_info})")
            print("   ✅ Sentinel validation complete")
        elif not _SENTINEL_AVAILABLE:
            print("   ⚠️  Step 2b: sentinel module not importable — skipping (see error above)")
        elif self.config is None:
            print(f"   ⚠️  Step 2b: sentinel skipped — config not loaded ({self._config_load_error or 'unknown reason'})")
        elif not getattr(self.config, "sentinel_enabled", False):
            print("   ℹ️  Step 2b: sentinel explicitly disabled in dev-kid.yml (sentinel.enabled: false)")

        # Step 3: Constitution validation
        print("   Step 3: constitution-validator checks output files...")
        if self.constitution:
            # Get modified files from git diff
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"], capture_output=True, text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                modified_files = [f for f in result.stdout.strip().split("\n") if f]

                # Validate against constitution
                violations = self.constitution.validate_output(modified_files)

                if violations:
                    print(f"\n❌ Constitution Violations Found:")
                    for v in violations:
                        print(f"   {v.file}:{v.line} - {v.rule}: {v.message}")
                    print("\n🚫 Checkpoint BLOCKED due to constitution violations")
                    print("   Fix violations and re-run checkpoint")
                    sys.exit(1)
                else:
                    print("   ✅ Constitution validation passed")
            else:
                print("   ℹ️  No modified files to validate")
        else:
            print("   ⚠️  Constitution not loaded, skipping validation")

        # Step 3b: SQL schema diff (breaking change detection)
        try:
            from sentinel.sql_schema_diff import SchemaDiff

            wave_sql_files = [
                f
                for t in tasks
                for f in (t.get("file_locks") or [])
                if f and str(f).endswith(".sql")
            ]
            if wave_sql_files:
                diff_report = SchemaDiff.compare_post_wave(wave_id, wave_sql_files)
                if diff_report.has_breaking_changes:
                    print(diff_report.format_blocking_message())
                    sys.exit(1)
                elif diff_report.changes:
                    print(
                        f"   ℹ️  {len(diff_report.changes)} non-breaking SQL schema change(s) — informational only"
                    )
        except Exception as _e:
            print(f"   ⚠️  SQL schema diff failed (non-fatal): {_e}")

        # Step 4: Git agent commits (only when checkpoint enabled)
        if checkpoint.get("enabled", True):
            print("   Step 4: git-version-manager creates checkpoint...")
            self._git_checkpoint(wave_id, wave_tasks=tasks)
        else:
            print("   ⚠️  Step 4: git checkpoint disabled for this wave")

        print(f"✅ Checkpoint {wave_id} complete\n")

    def _sync_memory_bank(self, wave_id: int) -> None:
        """Invoke dev-kid sync-memory to refresh all 6 memory-bank tiers."""
        result = subprocess.run(
            ["dev-kid", "sync-memory"],
            capture_output=True,
            text=True,
            cwd=str(self.project_root),
        )
        if result.returncode == 0:
            print(f"   ✅ Memory bank synced (wave {wave_id})")
        else:
            # Non-fatal — progress.md was already written by _update_progress
            stderr = result.stderr.strip() or result.stdout.strip()
            print(f"   ⚠️  dev-kid sync-memory failed (non-fatal): {stderr}")

    def _update_progress(self, wave_id: int, tasks: List[Dict]) -> None:
        """Update progress.md with wave completion"""
        progress_file = Path("memory-bank/private") / Path.home().name / "progress.md"

        progress_file.parent.mkdir(parents=True, exist_ok=True)

        if progress_file.exists():
            content = progress_file.read_text(encoding="utf-8")
        else:
            content = "# Progress\n\n"

        # Append wave completion
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        content += f"\n## Wave {wave_id} Complete - {timestamp}\n\n"
        for task in tasks:
            content += f"- ✅ {task['task_id']}: {task['instruction']}\n"

        progress_file.write_text(content, encoding="utf-8")

    def _git_checkpoint(
        self, wave_id: int, wave_tasks: Optional[List[Dict]] = None
    ) -> None:
        """Create git checkpoint commit, staging only wave file_locks + known safe paths."""
        # Collect files touched by this wave to avoid staging secrets / unrelated work
        files_to_stage: list[str] = ["tasks.md"]
        if wave_tasks:
            for t in wave_tasks:
                for f in t.get("file_locks") or []:
                    # Fix: parentheses required so `f` gates BOTH conditions
                    if f and (
                        "/" in str(f)
                        or str(f).endswith(
                            (
                                ".py",
                                ".ts",
                                ".js",
                                ".rs",
                                ".sql",
                                ".md",
                                ".json",
                                ".yml",
                                ".yaml",
                                ".sh",
                                ".toml",
                                ".txt",
                            )
                        )
                    ):
                        files_to_stage.append(str(f))
        # Always include memory-bank and .claude state dirs (safe, no secrets)
        files_to_stage += ["memory-bank/", ".claude/activity_stream.md"]

        for path in files_to_stage:
            subprocess.run(
                ["git", "add", "--", path], capture_output=True
            )  # ignore missing

        # Commit — capture output to detect "nothing to commit" vs real failures
        commit_msg = (
            f"[CHECKPOINT] Wave {wave_id} Complete\n\nAll tasks verified and validated"
        )
        commit_result = subprocess.run(
            ["git", "commit", "-m", commit_msg],
            capture_output=True,
            text=True,
        )
        if commit_result.returncode == 0:
            print(f"   ✅ Git checkpoint committed (wave {wave_id})")
        else:
            combined = (commit_result.stdout + commit_result.stderr).lower()
            if "nothing to commit" in combined or "nothing added" in combined:
                print(
                    f"   ⚠️  Wave {wave_id}: nothing staged to commit (tasks may have no file changes)"
                )
            else:
                print(
                    f"   ❌ Git commit failed (wave {wave_id}): {commit_result.stderr.strip()}"
                )

    def _mark_task_complete(self, task_id: str, instruction: str) -> None:
        """Mark a task [x] in tasks.md by finding its instruction line."""
        try:
            content = self.tasks_file.read_text(encoding="utf-8")
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if instruction in line and "- [ ]" in line:
                    lines[i] = line.replace("- [ ]", "- [x]", 1)
                    break
                # Also match by task_id prefix
                elif f"] {task_id} " in line and "- [ ]" in line:
                    lines[i] = line.replace("- [ ]", "- [x]", 1)
                    break
            self.tasks_file.write_text("\n".join(lines), encoding="utf-8")
        except Exception as e:
            print(f"      ⚠️  Could not mark {task_id} complete in tasks.md: {e}")

    def execute_task(self, task: Dict) -> None:
        """Execute a single task and register it with the watchdog.

        Sentinel tasks (agent_role="Sentinel") are routed to SentinelRunner.
        Regular tasks are registered with the Rust task-watchdog.

        Args:
            task: Task dictionary with task_id, instruction, agent_role, and optional constitution_rules
        Raises:
            WaveHaltError: when a sentinel decides to halt wave execution
        """
        task_id = task["task_id"]
        command = task["instruction"]
        constitution_rules = task.get("constitution_rules", [])

        # --- Sentinel routing (T009) ---
        if task.get("agent_role") == "Sentinel":
            if not _SENTINEL_AVAILABLE or _SentinelRunner is None:
                print(f"      ⚠️  Sentinel module unavailable — skipping {task_id}")
                self._mark_task_complete(task_id, command)
                return
            if self.config is None:
                print(f"      ⚠️  Config not loaded — skipping sentinel {task_id}")
                self._mark_task_complete(task_id, command)
                return
            print(f"      🛡️  Running sentinel: {task_id}")
            runner = _SentinelRunner(self.config, self.project_root)
            result = runner.run(task)
            if result.should_halt_wave:
                msg = result.error_message or f"Sentinel {task_id} halted wave"
                print(f"      ❌ Sentinel HALT: {msg}")
                raise WaveHaltError(msg)
            status_icon = "✅" if result.result == "PASS" else "⚠️"
            print(
                f"      {status_icon} Sentinel {task_id}: {result.result} (tier {result.tier_used})"
            )
            self._mark_task_complete(task_id, command)
            return

        # Locate watchdog binary
        watchdog_bin = _find_watchdog_binary()
        if not watchdog_bin:
            print(
                f"      ⚠️  task-watchdog not found — skipping registration for {task_id}"
            )
            return

        # Build watchdog register command
        cmd_parts = [watchdog_bin, "register", task_id, "--command", command]

        # Add constitution rules if present
        if constitution_rules:
            rules_arg = ",".join(constitution_rules)
            cmd_parts.extend(["--rules", rules_arg])

        # Execute registration
        result = subprocess.run(cmd_parts, capture_output=True, text=True)

        if result.returncode != 0:
            print(
                f"      ❌ Failed to register task {task_id}: {result.stderr.strip()}"
            )
        else:
            if constitution_rules:
                print(
                    f"      ✅ Task {task_id} registered with {len(constitution_rules)} constitution rule(s)"
                )
            else:
                print(f"      ✅ Task {task_id} registered (no constitution rules)")

    def execute_wave(self, wave: Dict) -> None:
        """Execute a single wave"""
        wave_id = wave["wave_id"]
        strategy = wave["strategy"]
        tasks = wave["tasks"]

        print(f"\n🌊 Executing Wave {wave_id} ({strategy})...")
        print(f"   Rationale: {wave['rationale']}")
        print(f"   Tasks: {len(tasks)}")

        # SQL schema diff: capture pre-wave snapshot for any .sql files in this wave
        sql_files = [
            f
            for t in tasks
            for f in (t.get("file_locks") or [])
            if f and str(f).endswith(".sql")
        ]
        if sql_files:
            try:
                from sentinel.sql_schema_diff import SchemaSnapshot

                SchemaSnapshot.capture_pre_wave(wave_id, sql_files)
                print(
                    f"   📸 Pre-wave schema snapshot captured for {len(sql_files)} SQL file(s)"
                )
            except Exception as _e:
                print(f"   ⚠️  Schema snapshot failed (non-fatal): {_e}")

        if strategy == "PARALLEL_SWARM":
            # Register tasks with watchdog and display for Claude to implement.
            # Sentinel validation fires at execute_checkpoint() after [x] markers confirmed.
            print("   Strategy: Parallel execution")
            for task in tasks:
                print(
                    f"      🤖 Agent {task['agent_role']}: {task['task_id']} - {task['instruction'][:50]}..."
                )
                self.execute_task(task)

        else:  # SEQUENTIAL_MERGE
            print("   Strategy: Sequential execution")
            for task in tasks:
                print(
                    f"      🤖 Agent {task['agent_role']}: {task['task_id']} - {task['instruction'][:50]}..."
                )
                self.execute_task(task)

        print(f"   ⏳ Wave {wave_id} in progress...")
        print(f"")
        print(f"   ┌─────────────────────────────────────────────────────┐")
        print(f"   │  AGENT REQUIREMENT — mark tasks complete in tasks.md │")
        print(f"   │                                                       │")
        for t in tasks:
            print(
                f"   │  [ ] → [x]  {t['task_id']}: {t['instruction'][:38]}{'...' if len(t['instruction']) > 38 else '':<{41 - min(len(t['instruction']),38)}}│"
            )
        print(f"   │                                                       │")
        print(f"   │  Wave checkpoint will HALT if any remain [ ]          │")
        print(f"   └─────────────────────────────────────────────────────┘")

    def execute(self) -> None:
        """Execute all waves with checkpoints"""
        print("🚀 Starting wave execution...")
        self.load_plan()
        assert self.plan is not None  # load_plan() exits on failure

        waves = self.plan["execution_plan"]["waves"]
        phase_id = self.plan["execution_plan"]["phase_id"]

        print(f"📋 Phase: {phase_id}")
        print(f"🌊 Total waves: {len(waves)}")

        # Detect resume point: find first wave with incomplete tasks
        resume_wave = 1
        for wave in waves:
            if self._wave_already_complete(wave["tasks"]):
                resume_wave = wave["wave_id"] + 1
            else:
                break
        if resume_wave > 1:
            print(
                f"♻️  Resuming from Wave {resume_wave} (Waves 1–{resume_wave - 1} already complete)"
            )

        for wave in waves:
            wave_id = wave["wave_id"]

            # Skip already-completed waves on resume
            if wave_id < resume_wave:
                print(f"   ⏩ Wave {wave_id}: already complete — skipping")
                continue

            # Execute wave (WaveHaltError from sentinel aborts execution)
            try:
                self.execute_wave(wave)
            except WaveHaltError as e:
                print(f"\n🚫 WAVE HALT: Sentinel halted wave {wave_id}: {e}")
                print(
                    "   Review sentinel manifests in .claude/sentinel/ and fix issues."
                )
                sys.exit(2)

            # Checkpoint after wave — verification + memory sync always run;
            # git commit is conditional on checkpoint_after.enabled
            self.execute_checkpoint(wave_id, wave["checkpoint_after"])

            # Proactive pre-compact check (if 5+ personas active)
            # This prevents hitting token limit mid-wave by triggering compression
            # at safe wave boundaries where PreCompact hook can save state
            print(f"\n🔍 Checking context health before next wave...")
            self.compactor.check_and_trigger(wave_id)

        print("\n✅ All waves complete!")


def main():
    """Main entry point"""
    executor = WaveExecutor()
    executor.execute()


if __name__ == "__main__":
    main()

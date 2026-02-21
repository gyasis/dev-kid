#!/usr/bin/env python3
"""
Wave Executor - Executes waves from execution_plan.json with checkpoints
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import time
from constitution_parser import Constitution
from context_compactor import ContextCompactor
from config_manager import ConfigManager

# Sentinel runner (T009) — imported lazily to tolerate incomplete builds
try:
    from sentinel.runner import SentinelRunner as _SentinelRunner
    _SENTINEL_AVAILABLE = True
except ImportError:
    _SentinelRunner = None  # type: ignore[assignment,misc]
    _SENTINEL_AVAILABLE = False


class WaveHaltError(Exception):
    """Raised when a sentinel decides to halt wave execution."""


def _find_watchdog_binary() -> Optional[str]:
    """Locate the task-watchdog binary using the same search order as the dev-kid CLI."""
    script_dir = Path(__file__).parent
    dev_kid_root = script_dir.parent
    candidates = [
        dev_kid_root / "rust-watchdog" / "target" / "release" / "task-watchdog",  # dev
        Path.home() / ".dev-kid" / "rust-watchdog" / "target" / "release" / "task-watchdog",  # installed
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
                self.constitution: Optional[Constitution] = Constitution(str(constitution_path))
            except Exception as e:
                print(f"⚠️  Warning: Failed to load constitution: {e}")
                print(f"   Constitution validation will be skipped")
                self.constitution = None
        else:
            self.constitution: Optional[Constitution] = None
            print("⚠️  Warning: Constitution file not found at memory-bank/shared/.constitution.md")

        # Initialize context compactor for proactive pre-compaction
        self.compactor = ContextCompactor()

        # Load sentinel config
        try:
            self.config = ConfigManager().load()
        except Exception:
            self.config = None

    def load_plan(self) -> None:
        """Load execution plan from JSON"""
        if not self.plan_file.exists():
            print(f"❌ Error: {self.plan_file} not found")
            print("   Run orchestrator.py first to generate execution plan")
            sys.exit(1)

        try:
            self.plan = json.loads(self.plan_file.read_text(encoding='utf-8'))
        except json.JSONDecodeError as e:
            print(f"❌ Error: Invalid JSON in {self.plan_file}")
            print(f"   {e}")
            # Backup corrupted file
            backup_path = self.plan_file.with_suffix('.json.corrupted')
            self.plan_file.rename(backup_path)
            print(f"   Corrupted file backed up to: {backup_path}")
            print(f"   Re-run orchestrator to generate new execution plan")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error reading {self.plan_file}: {e}")
            sys.exit(1)

    def verify_wave_completion(self, wave_id: int, tasks: List[Dict]) -> bool:
        """Verify all tasks in wave are marked complete in tasks.md"""
        try:
            content = self.tasks_file.read_text(encoding='utf-8')
        except Exception as e:
            print(f"❌ Error reading tasks.md: {e}")
            return False

        for task in tasks:
            task_desc = task['instruction']
            # Check if task line contains [x]
            for line in content.split('\n'):
                if task_desc in line:
                    if '[x]' in line:
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
        tasks = self.plan['execution_plan']['waves'][wave_id - 1]['tasks']
        verified = self.verify_wave_completion(wave_id, tasks)

        if not verified:
            print(f"\n❌ Checkpoint failed! Wave {wave_id} tasks not complete.")
            print("   Halting execution.")
            sys.exit(1)

        print("   ✅ All tasks verified complete")

        # Step 2: Memory bank keeper updates progress.md
        print("   Step 2: memory-bank-keeper updates progress.md...")
        self._update_progress(wave_id, tasks)

        # Step 3: Constitution validation
        print("   Step 3: constitution-validator checks output files...")
        if self.constitution:
            # Get modified files from git diff
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True, text=True
            )

            if result.returncode == 0 and result.stdout.strip():
                modified_files = [f for f in result.stdout.strip().split('\n') if f]

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

        # Step 4: Git agent commits
        print("   Step 4: git-version-manager creates checkpoint...")
        self._git_checkpoint(wave_id)

        print(f"✅ Checkpoint {wave_id} complete\n")

    def _update_progress(self, wave_id: int, tasks: List[Dict]) -> None:
        """Update progress.md with wave completion"""
        progress_file = Path("memory-bank/private") / Path.home().name / "progress.md"

        if progress_file.exists():
            content = progress_file.read_text()
        else:
            content = "# Progress\n\n"

        # Append wave completion
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        content += f"\n## Wave {wave_id} Complete - {timestamp}\n\n"
        for task in tasks:
            content += f"- ✅ {task['task_id']}: {task['instruction']}\n"

        progress_file.write_text(content)

    def _git_checkpoint(self, wave_id: int) -> None:
        """Create git checkpoint commit"""
        # Stage all changes
        subprocess.run(['git', 'add', '.'], check=True)

        # Commit
        commit_msg = f"[CHECKPOINT] Wave {wave_id} Complete\n\nAll tasks verified and validated"
        subprocess.run(['git', 'commit', '-m', commit_msg], check=False)  # Don't fail if nothing to commit

    def _mark_task_complete(self, task_id: str, instruction: str) -> None:
        """Mark a task [x] in tasks.md by finding its instruction line."""
        try:
            content = self.tasks_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if instruction in line and '- [ ]' in line:
                    lines[i] = line.replace('- [ ]', '- [x]', 1)
                    break
                # Also match by task_id prefix
                elif f'] {task_id} ' in line and '- [ ]' in line:
                    lines[i] = line.replace('- [ ]', '- [x]', 1)
                    break
            self.tasks_file.write_text('\n'.join(lines), encoding='utf-8')
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
            print(f"      {status_icon} Sentinel {task_id}: {result.result} (tier {result.tier_used})")
            self._mark_task_complete(task_id, command)
            return

        # Locate watchdog binary
        watchdog_bin = _find_watchdog_binary()
        if not watchdog_bin:
            print(f"      ⚠️  task-watchdog not found — skipping registration for {task_id}")
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
            print(f"      ❌ Failed to register task {task_id}: {result.stderr.strip()}")
        else:
            if constitution_rules:
                print(f"      ✅ Task {task_id} registered with {len(constitution_rules)} constitution rule(s)")
            else:
                print(f"      ✅ Task {task_id} registered (no constitution rules)")

    def execute_wave(self, wave: Dict) -> None:
        """Execute a single wave"""
        wave_id = wave['wave_id']
        strategy = wave['strategy']
        tasks = wave['tasks']

        print(f"\n🌊 Executing Wave {wave_id} ({strategy})...")
        print(f"   Rationale: {wave['rationale']}")
        print(f"   Tasks: {len(tasks)}")

        if strategy == "PARALLEL_SWARM":
            # Execute tasks in parallel (simulated - in real system, spawn agents)
            print("   Strategy: Parallel execution")
            for task in tasks:
                print(f"      🤖 Agent {task['agent_role']}: {task['task_id']} - {task['instruction'][:50]}...")
                # Register task with watchdog
                self.execute_task(task)
                # In real system: spawn agent with task
                # For now: just print

        else:  # SEQUENTIAL_MERGE
            print("   Strategy: Sequential execution")
            for task in tasks:
                print(f"      🤖 Agent {task['agent_role']}: {task['task_id']} - {task['instruction'][:50]}...")
                # Register task with watchdog
                self.execute_task(task)
                # In real system: execute task sequentially

        print(f"   ⏳ Wave {wave_id} in progress...")
        print(f"   ℹ️  Agents must mark tasks complete in tasks.md before wave ends")

    def execute(self) -> None:
        """Execute all waves with checkpoints"""
        print("🚀 Starting wave execution...")
        self.load_plan()

        waves = self.plan['execution_plan']['waves']
        phase_id = self.plan['execution_plan']['phase_id']

        print(f"📋 Phase: {phase_id}")
        print(f"🌊 Total waves: {len(waves)}")

        for wave in waves:
            wave_id = wave['wave_id']

            # Execute wave (WaveHaltError from sentinel aborts execution)
            try:
                self.execute_wave(wave)
            except WaveHaltError as e:
                print(f"\n🚫 WAVE HALT: Sentinel halted wave {wave_id}: {e}")
                print("   Review sentinel manifests in .claude/sentinel/ and fix issues.")
                sys.exit(2)

            # Checkpoint after wave
            if wave['checkpoint_after']['enabled']:
                self.execute_checkpoint(wave_id, wave['checkpoint_after'])
            else:
                print(f"   ⏭️  Skipping checkpoint (disabled)")

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

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Wave Executor - Executes waves from execution_plan.json with checkpoints
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
import time
from constitution_parser import Constitution

class WaveExecutor:
    """Executes waves with parallel task execution and checkpoints"""

    def __init__(self, plan_file: str = "execution_plan.json"):
        self.plan_file = Path(plan_file)
        self.plan = None
        self.tasks_file = Path("tasks.md")

        # Load constitution from memory-bank
        constitution_path = Path("memory-bank/shared/.constitution.md")
        if constitution_path.exists():
            self.constitution: Optional[Constitution] = Constitution(str(constitution_path))
        else:
            self.constitution: Optional[Constitution] = None
            print("⚠️  Warning: Constitution file not found at memory-bank/shared/.constitution.md")

    def load_plan(self) -> None:
        """Load execution plan from JSON"""
        if not self.plan_file.exists():
            print(f"❌ Error: {self.plan_file} not found")
            print("   Run orchestrator.py first to generate execution plan")
            sys.exit(1)

        self.plan = json.loads(self.plan_file.read_text())

    def verify_wave_completion(self, wave_id: int, tasks: List[Dict]) -> bool:
        """Verify all tasks in wave are marked complete in tasks.md"""
        content = self.tasks_file.read_text()

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

        # Step 3: Git agent commits
        print("   Step 3: git-version-manager creates checkpoint...")
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
                # In real system: spawn agent with task
                # For now: just print

        else:  # SEQUENTIAL_MERGE
            print("   Strategy: Sequential execution")
            for task in tasks:
                print(f"      🤖 Agent {task['agent_role']}: {task['task_id']} - {task['instruction'][:50]}...")
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

            # Execute wave
            self.execute_wave(wave)

            # Checkpoint after wave
            if wave['checkpoint_after']['enabled']:
                self.execute_checkpoint(wave_id, wave['checkpoint_after'])
            else:
                print(f"   ⏭️  Skipping checkpoint (disabled)")

        print("\n✅ All waves complete!")

def main():
    """Main entry point"""
    executor = WaveExecutor()
    executor.execute()

if __name__ == '__main__':
    main()

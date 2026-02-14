#!/usr/bin/env python3
"""
Task Watchdog - Monitors running tasks and survives context compression

Key Features:
1. Tracks task start/end times
2. Runs as background process (not token-dependent)
3. Checks every 5 minutes for running tasks
4. Warns if tasks exceed 7-minute guideline (investigate what's happening)
5. Records completion times
6. Survives context compression

Task Timing Guidelines:
- Tasks should complete within 15 minutes (guideline)
- After 15 minutes: Check to investigate what's going on
- Task process continues until marked complete (doesn't auto-stop)
"""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys

class TaskWatchdog:
    """Monitors task execution and prevents loss during context compression"""

    def __init__(self, state_file: str = ".claude/task_timers.json"):
        self.state_file = Path(state_file)
        self.tasks_file = Path("tasks.md")
        self.state: Dict = {}
        self.check_interval = 300  # 5 minutes

    def load_state(self) -> None:
        """Load task timer state from disk"""
        if self.state_file.exists():
            try:
                self.state = json.loads(self.state_file.read_text(encoding='utf-8'))
            except json.JSONDecodeError as e:
                print(f"⚠️  Warning: Corrupted watchdog state file")
                print(f"   Error: {e}")
                # Backup corrupted state
                backup_path = self.state_file.with_suffix('.json.corrupted')
                if self.state_file.exists():
                    import shutil
                    shutil.copy(self.state_file, backup_path)
                    print(f"   Corrupted state backed up to: {backup_path}")
                # Reset to empty state
                self.state = {
                    "running_tasks": {},
                    "completed_tasks": {},
                    "warnings": []
                }
                print(f"   Watchdog state reset. Previous tasks may be lost.")
            except Exception as e:
                print(f"❌ Error loading watchdog state: {e}")
                self.state = {
                    "running_tasks": {},
                    "completed_tasks": {},
                    "warnings": []
                }
        else:
            self.state = {
                "running_tasks": {},
                "completed_tasks": {},
                "warnings": []
            }

    def save_state(self) -> None:
        """Persist state to disk (survives context compression)"""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            # Atomic write: write to temp file, then rename
            temp_file = self.state_file.with_suffix('.tmp')
            temp_file.write_text(json.dumps(self.state, indent=2), encoding='utf-8')
            temp_file.rename(self.state_file)
        except Exception as e:
            print(f"⚠️  Warning: Failed to save watchdog state: {e}")
            # Don't crash, just log the error
            pass

    def start_task(self, task_id: str, description: str) -> None:
        """Start timer for a task"""
        now = datetime.now().isoformat()

        self.state["running_tasks"][task_id] = {
            "description": description,
            "started_at": now,
            "last_checked": now,
            "status": "running"
        }

        print(f"⏱️  Started timer for {task_id}: {description}")
        self.save_state()

    def complete_task(self, task_id: str) -> None:
        """Complete a task and record timing"""
        if task_id not in self.state["running_tasks"]:
            print(f"⚠️  Warning: Task {task_id} not found in running tasks")
            return

        task = self.state["running_tasks"].pop(task_id)
        started = datetime.fromisoformat(task["started_at"])
        completed = datetime.now()
        duration = (completed - started).total_seconds()

        self.state["completed_tasks"][task_id] = {
            "description": task["description"],
            "started_at": task["started_at"],
            "completed_at": completed.isoformat(),
            "duration_seconds": duration,
            "duration_human": self._format_duration(duration)
        }

        print(f"✅ Completed {task_id} in {self._format_duration(duration)}")
        self.save_state()

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable form"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            return f"{int(seconds / 60)}m {int(seconds % 60)}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"

    def check_tasks(self) -> None:
        """Check for forgotten/lost/overdue tasks"""
        now = datetime.now()
        warnings = []

        # Update tasks.md status
        self._sync_with_tasks_md()

        # Check running tasks
        for task_id, task in list(self.state["running_tasks"].items()):
            started = datetime.fromisoformat(task["started_at"])
            last_checked = datetime.fromisoformat(task["last_checked"])
            duration = (now - started).total_seconds()

            # Update last checked
            task["last_checked"] = now.isoformat()

            # Check if task exceeds 15-minute guideline
            if duration > 900:  # 15 minutes
                warning = {
                    "type": "exceeds_guideline",
                    "task_id": task_id,
                    "description": task["description"],
                    "duration": self._format_duration(duration),
                    "timestamp": now.isoformat(),
                    "message": "Task exceeds 15-minute guideline - investigate what's happening"
                }
                warnings.append(warning)
                print(f"⚠️  {task_id} running for {self._format_duration(duration)} (exceeds 15-min guideline)")
                print(f"   → Investigate: {task['description']}")

            # Check if task might be stalled (> 15 min since last check)
            time_since_check = (now - last_checked).total_seconds()
            if time_since_check > 900:  # 15 minutes
                warning = {
                    "type": "possibly_stalled",
                    "task_id": task_id,
                    "description": task["description"],
                    "time_since_check": self._format_duration(time_since_check),
                    "timestamp": now.isoformat(),
                    "message": "No activity detected - task may be stalled"
                }
                warnings.append(warning)
                print(f"⚠️  {task_id} may be stalled (no check for {self._format_duration(time_since_check)})")

        self.state["warnings"] = warnings
        self.save_state()

    def _sync_with_tasks_md(self) -> None:
        """Synchronize with tasks.md to detect completed tasks"""
        if not self.tasks_file.exists():
            return

        content = self.tasks_file.read_text()

        # Check each running task to see if it's marked done in tasks.md
        for task_id, task in list(self.state["running_tasks"].items()):
            description = task["description"]

            # Look for this task in tasks.md
            for line in content.split('\n'):
                if description in line and '[x]' in line:
                    # Task is marked complete!
                    print(f"✅ Detected completion of {task_id} in tasks.md")
                    self.complete_task(task_id)
                    break

    def run_watchdog(self, duration_minutes: int = None) -> None:
        """Run watchdog in continuous mode"""
        print(f"🐕 Task Watchdog started (checking every 5 minutes)")
        print(f"   State file: {self.state_file}")
        print(f"   Press Ctrl+C to stop\n")

        iterations = 0
        max_iterations = None if duration_minutes is None else (duration_minutes * 60) // self.check_interval

        try:
            while True:
                self.load_state()
                print(f"\n🔍 Watchdog check #{iterations + 1} - {datetime.now().strftime('%H:%M:%S')}")
                self.check_tasks()

                print(f"   Running tasks: {len(self.state['running_tasks'])}")
                print(f"   Completed tasks: {len(self.state['completed_tasks'])}")
                print(f"   Warnings: {len(self.state['warnings'])}")

                iterations += 1
                if max_iterations and iterations >= max_iterations:
                    print(f"\n✅ Watchdog completed {iterations} checks")
                    break

                print(f"\n💤 Next check in 5 minutes...")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print(f"\n\n🛑 Watchdog stopped by user")
            print(f"   Completed {iterations} checks")
            sys.exit(0)

    def report(self) -> None:
        """Generate task timing report"""
        self.load_state()

        print("📊 Task Timing Report")
        print("=" * 60)

        # Running tasks
        if self.state["running_tasks"]:
            print(f"\n⏱️  Running Tasks ({len(self.state['running_tasks'])})")
            for task_id, task in self.state["running_tasks"].items():
                started = datetime.fromisoformat(task["started_at"])
                duration = (datetime.now() - started).total_seconds()
                print(f"  {task_id}: {task['description']}")
                print(f"    Started: {started.strftime('%Y-%m-%d %H:%M')}")
                print(f"    Duration: {self._format_duration(duration)}")

        # Completed tasks
        if self.state["completed_tasks"]:
            print(f"\n✅ Completed Tasks ({len(self.state['completed_tasks'])})")
            total_time = 0
            for task_id, task in self.state["completed_tasks"].items():
                print(f"  {task_id}: {task['description']}")
                print(f"    Duration: {task['duration_human']}")
                total_time += task["duration_seconds"]

            print(f"\n  Total time: {self._format_duration(total_time)}")
            avg_time = total_time / len(self.state["completed_tasks"])
            print(f"  Average time per task: {self._format_duration(avg_time)}")

        # Warnings
        if self.state["warnings"]:
            print(f"\n⚠️  Active Warnings ({len(self.state['warnings'])})")
            for warning in self.state["warnings"]:
                print(f"  {warning['type']}: {warning['task_id']}")
                print(f"    {warning['description']}")

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Task Watchdog - Monitor task execution")
    parser.add_argument('command', choices=['start', 'complete', 'check', 'report', 'run'],
                       help='Command to execute')
    parser.add_argument('--task-id', help='Task ID (for start/complete)')
    parser.add_argument('--description', help='Task description (for start)')
    parser.add_argument('--duration', type=int, help='Duration in minutes (for run)')

    args = parser.parse_args()

    watchdog = TaskWatchdog()
    watchdog.load_state()

    if args.command == 'start':
        if not args.task_id or not args.description:
            print("❌ Error: --task-id and --description required for start")
            sys.exit(1)
        watchdog.start_task(args.task_id, args.description)

    elif args.command == 'complete':
        if not args.task_id:
            print("❌ Error: --task-id required for complete")
            sys.exit(1)
        watchdog.complete_task(args.task_id)

    elif args.command == 'check':
        watchdog.check_tasks()

    elif args.command == 'report':
        watchdog.report()

    elif args.command == 'run':
        watchdog.run_watchdog(args.duration)

if __name__ == '__main__':
    main()

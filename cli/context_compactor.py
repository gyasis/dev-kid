#!/usr/bin/env python3
"""
Context Compactor - Proactively triggers PreCompact between waves

Detects when 5+ personas/agents are active and triggers pre-compaction
to avoid hitting token limit mid-wave. This ensures:
- State saved at safe wave boundaries
- PreCompact hook fires with full context
- Debugging possible before compression
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime


class ContextCompactor:
    """Manages proactive context compression between waves"""

    def __init__(self):
        self.agent_state_file = Path('.claude/AGENT_STATE.json')
        self.activity_stream = Path('.claude/activity_stream.md')
        self.system_bus = Path('.claude/system_bus.json')
        self.persona_threshold = 5  # Trigger pre-compact if 5+ personas active

    def count_active_personas(self) -> int:
        """Count active personas/agents from AGENT_STATE.json"""
        if not self.agent_state_file.exists():
            return 0

        try:
            with open(self.agent_state_file) as f:
                state = json.load(f)

            agents = state.get('agents', {})
            active_count = 0

            for _, agent_data in agents.items():
                status = agent_data.get('status', 'idle')
                if status in ['active', 'running', 'in_progress']:
                    active_count += 1

            return active_count

        except (json.JSONDecodeError, KeyError) as e:
            print(f"⚠️  Warning: Failed to count personas: {e}")
            return 0

    def detect_task_tool_usage(self) -> int:
        """Count active personas from Task tool usage (alternative detection)"""
        # Check activity_stream for recent Task tool invocations
        if not self.activity_stream.exists():
            return 0

        try:
            content = self.activity_stream.read_text()
            # Count unique subagent types in recent activity (last 20 lines)
            lines = content.split('\n')[-20:]
            personas = set()

            for line in lines:
                if 'subagent_type' in line or 'Task tool' in line:
                    # Extract persona name from line
                    for keyword in ['python-pro', 'sql-pro', 'debugger', 'frontend-developer',
                                   'backend-architect', 'data-scientist', 'security-auditor',
                                   'performance-engineer', 'test-automator', 'deployment-engineer']:
                        if keyword in line.lower():
                            personas.add(keyword)

            return len(personas)

        except Exception as e:
            print(f"⚠️  Warning: Failed to detect Task tool usage: {e}")
            return 0

    def should_precompact(self) -> tuple[bool, int, str]:
        """
        Determine if pre-compaction should be triggered

        Returns:
            (should_compact, persona_count, reason)
        """
        # Check AGENT_STATE.json first
        state_count = self.count_active_personas()

        # Check Task tool usage as alternative
        task_count = self.detect_task_tool_usage()

        # Use max of both detection methods
        persona_count = max(state_count, task_count)

        if persona_count >= self.persona_threshold:
            reason = f"{persona_count} personas active (threshold: {self.persona_threshold})"
            return (True, persona_count, reason)

        return (False, persona_count, "Below threshold")

    def trigger_precompact(self, wave_id: int, persona_count: int) -> bool:
        """
        Trigger pre-compaction by running PreCompact hook

        Args:
            wave_id: Current wave ID
            persona_count: Number of active personas detected

        Returns:
            True if successful, False otherwise
        """
        precompact_hook = Path('.claude/hooks/pre-compact.sh')

        if not precompact_hook.exists():
            print(f"⚠️  PreCompact hook not found at {precompact_hook}")
            return False

        print(f"\n🔄 Proactive Pre-Compact Triggered")
        print(f"   Wave: {wave_id}")
        print(f"   Active personas: {persona_count}")
        print(f"   Reason: Multi-agent coordination requires context management")

        # Log to activity stream
        self._log_to_activity_stream(wave_id, persona_count)

        # Update system bus
        self._update_system_bus(wave_id, persona_count)

        # Run PreCompact hook
        try:
            # Prepare event data for hook
            event_data = {
                "event": "ProactivePreCompact",
                "wave_id": wave_id,
                "persona_count": persona_count,
                "timestamp": datetime.now().isoformat(),
                "trigger": "multi_persona_detection"
            }

            # Execute hook
            result = subprocess.run(
                [str(precompact_hook)],
                input=json.dumps(event_data),
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                print(f"   ✅ Pre-compact successful")
                print(f"   💾 State backed up before potential compression")
                return True
            else:
                print(f"   ⚠️  Pre-compact hook returned: {result.returncode}")
                print(f"   {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print(f"   ❌ Pre-compact hook timed out")
            return False
        except Exception as e:
            print(f"   ❌ Failed to trigger pre-compact: {e}")
            return False

    def _log_to_activity_stream(self, wave_id: int, persona_count: int) -> None:
        """Log proactive pre-compact to activity stream"""
        if not self.activity_stream.exists():
            return

        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"\n### {timestamp} - Proactive Pre-Compact\n"
            log_entry += f"- Wave: {wave_id}\n"
            log_entry += f"- Active personas: {persona_count}\n"
            log_entry += f"- Trigger: Multi-agent coordination detected\n"
            log_entry += f"- Action: State backup initiated before potential compression\n"

            with open(self.activity_stream, 'a') as f:
                f.write(log_entry)

        except Exception as e:
            print(f"⚠️  Warning: Failed to log to activity stream: {e}")

    def _update_system_bus(self, wave_id: int, persona_count: int) -> None:
        """Update system bus with pre-compact event"""
        if not self.system_bus.exists():
            return

        try:
            with open(self.system_bus) as f:
                bus = json.load(f)

            bus['events'].append({
                'timestamp': datetime.now().isoformat(),
                'agent': 'context-compactor',
                'event_type': 'proactive_precompact',
                'wave_id': wave_id,
                'persona_count': persona_count,
                'trigger': 'multi_persona_detection'
            })

            with open(self.system_bus, 'w') as f:
                json.dump(bus, f, indent=2)

        except Exception as e:
            print(f"⚠️  Warning: Failed to update system bus: {e}")

    def check_and_trigger(self, wave_id: int) -> None:
        """
        Check if pre-compaction needed and trigger if so

        Call this between waves in wave_executor.py

        Args:
            wave_id: Current wave ID (for logging)
        """
        should_compact, persona_count, _ = self.should_precompact()

        if should_compact:
            self.trigger_precompact(wave_id, persona_count)
        else:
            # Only log if personas detected but below threshold
            if persona_count > 0:
                print(f"   ℹ️  {persona_count} personas active (threshold: {self.persona_threshold}) - no pre-compact needed")


def main():
    """CLI entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Context Compactor")
    parser.add_argument('command', choices=['check', 'trigger', 'count'],
                       help='Command to execute')
    parser.add_argument('--wave-id', type=int, default=0,
                       help='Wave ID for trigger command')

    args = parser.parse_args()

    compactor = ContextCompactor()

    if args.command == 'check':
        should, count, reason = compactor.should_precompact()
        print(f"Should pre-compact: {should}")
        print(f"Persona count: {count}")
        print(f"Reason: {reason}")

    elif args.command == 'trigger':
        compactor.trigger_precompact(args.wave_id, 5)

    elif args.command == 'count':
        count = compactor.count_active_personas()
        print(f"Active personas: {count}")


if __name__ == '__main__':
    main()

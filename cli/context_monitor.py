#!/usr/bin/env python3
"""
Context Budget Monitor - Track and warn about Ralph smart zone limits
"""

import sys
from pathlib import Path

# Ralph smart zone thresholds (for 200K Claude context window)
OPTIMAL_TOKENS = 60000    # 30% - stay here!
WARNING_TOKENS = 80000    # 40% - warning zone
CRITICAL_TOKENS = 100000  # 50% - must finalize

def estimate_context_usage() -> int:
    """
    Estimate current context usage in tokens.
    
    Approximation: 1 token ≈ 4 characters for English text
    """
    total_chars = 0
    
    # Activity stream (main context accumulator)
    activity_stream = Path(".claude/activity_stream.md")
    if activity_stream.exists():
        total_chars += activity_stream.stat().st_size
    
    # Active stack (current focus)
    active_stack = Path(".claude/active_stack.md")
    if active_stack.exists():
        total_chars += active_stack.stat().st_size
    
    # Approximate tokens (1 token ≈ 4 chars)
    estimated_tokens = total_chars // 4
    
    return estimated_tokens

def get_zone_info(tokens: int) -> dict:
    """Get zone classification for token count"""
    if tokens < OPTIMAL_TOKENS:
        return {
            'zone': 'smart',
            'level': 'optimal',
            'percentage': int((tokens / 200000) * 100),
            'status': '✅',
            'message': 'Optimal - stay in smart zone',
            'action': 'Continue normally'
        }
    elif tokens < WARNING_TOKENS:
        return {
            'zone': 'smart',
            'level': 'warning',
            'percentage': int((tokens / 200000) * 100),
            'status': '⚠️',
            'message': 'Approaching dumb zone threshold',
            'action': 'Consider micro-checkpoint soon'
        }
    elif tokens < CRITICAL_TOKENS:
        return {
            'zone': 'dumb',
            'level': 'critical',
            'percentage': int((tokens / 200000) * 100),
            'status': '🚨',
            'message': 'In dumb zone - quality degraded',
            'action': 'FINALIZE NOW: dev-kid finalize && dev-kid recall'
        }
    else:
        return {
            'zone': 'dumb',
            'level': 'severe',
            'percentage': int((tokens / 200000) * 100),
            'status': '❌',
            'message': 'Deep in dumb zone - severe degradation',
            'action': 'STOP WORK - dev-kid finalize IMMEDIATELY'
        }

def check_context_budget(verbose: bool = False) -> dict:
    """Check current context budget and return zone info"""
    tokens = estimate_context_usage()
    zone_info = get_zone_info(tokens)
    
    if verbose:
        print(f"📊 Context Budget Status")
        print(f"")
        print(f"   Estimated tokens: {tokens:,} / 200,000 ({zone_info['percentage']}%)")
        print(f"   Zone: {zone_info['status']} {zone_info['zone'].upper()} ZONE - {zone_info['level']}")
        print(f"   Message: {zone_info['message']}")
        print(f"")
        print(f"   Thresholds:")
        print(f"   - Optimal: <{OPTIMAL_TOKENS:,} tokens (30%)")
        print(f"   - Warning: <{WARNING_TOKENS:,} tokens (40%)")
        print(f"   - Critical: <{CRITICAL_TOKENS:,} tokens (50%)")
        print(f"")
        print(f"   Recommended action: {zone_info['action']}")
    
    return {
        'tokens': tokens,
        **zone_info
    }

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Monitor context budget for Ralph smart zone optimization"
    )
    parser.add_argument('--check', action='store_true',
                       help='Check context budget and exit with code')
    parser.add_argument('--warn-only', action='store_true',
                       help='Only exit with error if in dumb zone')
    
    args = parser.parse_args()
    
    result = check_context_budget(verbose=True)
    
    # Exit codes:
    # 0 = optimal
    # 1 = warning (approaching threshold)
    # 2 = critical (in dumb zone)
    # 3 = severe (deep in dumb zone)
    
    if args.check:
        level = result['level']
        if level == 'optimal':
            sys.exit(0)
        elif level == 'warning':
            sys.exit(0 if args.warn_only else 1)
        elif level == 'critical':
            sys.exit(2)
        else:  # severe
            sys.exit(3)
    
    sys.exit(0)

if __name__ == "__main__":
    main()

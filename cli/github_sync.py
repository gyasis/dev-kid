#!/usr/bin/env python3
"""
GitHub Issue Sync for dev-kid
Syncs tasks.md to GitHub issues for crash recovery and external state tracking.
"""

import json
import subprocess
import sys
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Task:
    """Task representation from tasks.md"""
    id: str
    description: str
    completed: bool
    file_paths: List[str]
    dependencies: List[str]
    issue_number: Optional[int] = None

def parse_tasks_md(tasks_file: Path = Path("tasks.md")) -> List[Task]:
    """Parse tasks.md into Task objects"""
    if not tasks_file.exists():
        print(f"❌ tasks.md not found at {tasks_file}")
        sys.exit(1)
    
    tasks = []
    content = tasks_file.read_text()
    
    # Match: - [ ] TASK-001: Description affecting `file.py`
    pattern = r'^- \[([ x])\] ([A-Z]+-\d+): (.+)$'
    
    for line in content.split('\n'):
        match = re.match(pattern, line)
        if match:
            completed = match.group(1) == 'x'
            task_id = match.group(2)
            description = match.group(3)
            
            # Extract file paths (backtick-enclosed)
            file_paths = re.findall(r'`([^`]+)`', description)
            
            # Extract dependencies (after T123, depends on T456)
            deps = re.findall(r'(?:after|depends on) ([A-Z]+-\d+)', description)
            
            tasks.append(Task(
                id=task_id,
                description=description,
                completed=completed,
                file_paths=file_paths,
                dependencies=deps
            ))
    
    return tasks

def get_existing_issues() -> Dict[str, int]:
    """Get existing GitHub issues created by dev-kid"""
    try:
        result = subprocess.run(
            ['gh', 'issue', 'list', '--label', 'dev-kid', '--json', 'number,title'],
            capture_output=True,
            text=True,
            check=True
        )
        issues = json.loads(result.stdout)
        
        # Map task ID to issue number
        mapping = {}
        for issue in issues:
            # Extract TASK-001 from title
            match = re.search(r'([A-Z]+-\d+)', issue['title'])
            if match:
                mapping[match.group(1)] = issue['number']
        
        return mapping
    except subprocess.CalledProcessError:
        print("⚠️  Warning: Could not fetch GitHub issues (gh CLI not authenticated?)")
        return {}

def create_github_issue(task: Task, wave_id: Optional[int] = None) -> Optional[int]:
    """Create a GitHub issue for a task"""
    title = f"{task.id}: {task.description[:60]}..."
    
    # Build issue body
    body = f"""## Task Details

**ID**: {task.id}
**Status**: {'✅ Completed' if task.completed else '⏳ Pending'}
**Wave**: {wave_id or 'TBD'}

### Description
{task.description}

### Affected Files
"""
    
    if task.file_paths:
        for fp in task.file_paths:
            body += f"- `{fp}`\n"
    else:
        body += "_No files specified_\n"
    
    if task.dependencies:
        body += f"\n### Dependencies\n"
        for dep in task.dependencies:
            body += f"- Depends on #{dep}\n"
    
    body += "\n---\n_Created by dev-kid for wave-based execution and crash recovery_"
    
    try:
        result = subprocess.run(
            ['gh', 'issue', 'create', 
             '--title', title,
             '--body', body,
             '--label', 'dev-kid',
             '--label', 'wave' if wave_id else 'pending'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # Extract issue number from URL
        url = result.stdout.strip()
        issue_num = int(url.split('/')[-1])
        print(f"   ✅ Created issue #{issue_num} for {task.id}")
        return issue_num
    
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Failed to create issue for {task.id}: {e.stderr}")
        return None

def sync_tasks_to_issues(dry_run: bool = False):
    """Sync tasks.md to GitHub issues"""
    print("📋 Syncing tasks.md to GitHub issues...")
    print("")
    
    # Parse tasks
    tasks = parse_tasks_md()
    print(f"   Found {len(tasks)} tasks in tasks.md")
    
    # Get existing issues
    existing = get_existing_issues()
    print(f"   Found {len(existing)} existing dev-kid issues")
    print("")
    
    # Load execution plan if exists (to get wave assignments)
    wave_assignments = {}
    exec_plan_path = Path("execution_plan.json")
    if exec_plan_path.exists():
        with open(exec_plan_path) as f:
            plan = json.load(f)
            for wave in plan['execution_plan']['waves']:
                wave_id = wave['wave_id']
                for task in wave['tasks']:
                    wave_assignments[task['id']] = wave_id
    
    # Sync tasks
    created = 0
    skipped = 0
    
    for task in tasks:
        if task.id in existing:
            print(f"   ⏭️  Skipping {task.id} (issue #{existing[task.id]} exists)")
            skipped += 1
            continue
        
        if dry_run:
            print(f"   [DRY RUN] Would create issue for {task.id}")
        else:
            wave_id = wave_assignments.get(task.id)
            if create_github_issue(task, wave_id):
                created += 1
    
    print("")
    print(f"✅ Sync complete:")
    print(f"   Created: {created}")
    print(f"   Skipped: {skipped}")
    print(f"   Total: {len(tasks)}")

def close_completed_issues():
    """Close GitHub issues for completed tasks"""
    print("🔒 Closing completed issues...")
    print("")
    
    tasks = parse_tasks_md()
    existing = get_existing_issues()
    
    closed = 0
    for task in tasks:
        if task.completed and task.id in existing:
            issue_num = existing[task.id]
            try:
                subprocess.run(
                    ['gh', 'issue', 'close', str(issue_num),
                     '--comment', f"✅ Task {task.id} completed via dev-kid"],
                    check=True,
                    capture_output=True
                )
                print(f"   ✅ Closed issue #{issue_num} for {task.id}")
                closed += 1
            except subprocess.CalledProcessError:
                print(f"   ❌ Failed to close issue #{issue_num}")
    
    print("")
    print(f"✅ Closed {closed} completed issues")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Sync tasks.md to GitHub issues")
    parser.add_argument('action', choices=['sync', 'close', 'wave'],
                       help='sync: Create issues for new tasks, close: Close completed tasks, wave: Show issues for a wave')
    parser.add_argument('wave_id', nargs='?', type=int,
                       help='Wave number (required for wave action)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would happen without making changes')

    args = parser.parse_args()

    if args.action == 'sync':
        sync_tasks_to_issues(dry_run=args.dry_run)
    elif args.action == 'close':
        if args.dry_run:
            print("❌ --dry-run not supported for close action")
            sys.exit(1)
        close_completed_issues()
    elif args.action == 'wave':
        if not args.wave_id:
            print("❌ Wave ID required: dev-kid gh-wave <wave_id>")
            sys.exit(1)
        show_wave_issues(args.wave_id)

if __name__ == "__main__":
    main()

def show_wave_issues(wave_id: int):
    """Show GitHub issues for a specific wave"""
    exec_plan_path = Path("execution_plan.json")
    if not exec_plan_path.exists():
        print("❌ execution_plan.json not found")
        sys.exit(1)
    
    with open(exec_plan_path) as f:
        plan = json.load(f)
    
    # Find wave
    wave = None
    for w in plan['execution_plan']['waves']:
        if w['wave_id'] == wave_id:
            wave = w
            break
    
    if not wave:
        print(f"❌ Wave {wave_id} not found")
        sys.exit(1)
    
    print(f"📋 GitHub Issues for Wave {wave_id}")
    print("")
    
    # Get existing issues
    existing = get_existing_issues()
    
    # Show issues for this wave's tasks
    for task in wave['tasks']:
        task_id = task['id']
        if task_id in existing:
            issue_num = existing[task_id]
            print(f"   #{issue_num}: {task_id} - {task['description'][:50]}...")
        else:
            print(f"   ⚠️  {task_id} - No issue (run gh-sync)")
    
    print("")
    print(f"   Total: {len(wave['tasks'])} tasks in wave {wave_id}")

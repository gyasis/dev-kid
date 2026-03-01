#!/usr/bin/env python3
"""
Deep Lake → S3 one-way sync with full backup before any upload.

Uses AWS credentials from default chain (~/.aws/credentials or env vars).
Never uploads without creating a timestamped full backup first (prevents data loss).

Usage:
  export DEEPLAKE_LOCAL_PATH="/path/to/local/dataset"
  export DEEPLAKE_S3_URI="s3://your-bucket/dataset_name"
  # Optional: export DEEPLAKE_BACKUP_DIR="$HOME/deeplake_backups"

  # First time: full copy to S3 (and backup)
  python3 scripts/deeplake_s3_sync.py --first-time

  # Later: backup + delta push (only new commits)
  python3 scripts/deeplake_s3_sync.py

  # Backup only (no S3)
  python3 scripts/deeplake_s3_sync.py --backup-only
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


def _env(name: str, default: str | None = None) -> str:
    v = os.environ.get(name, default)
    if v is None or v == "":
        return ""
    return v.strip()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backup Deep Lake dataset and sync to S3 (one-way, deltas after first copy)."
    )
    parser.add_argument(
        "--first-time",
        action="store_true",
        help="Do initial full copy to S3 (then use without this for delta push).",
    )
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Only create local backup; do not touch S3.",
    )
    parser.add_argument(
        "--local-path",
        default=_env("DEEPLAKE_LOCAL_PATH"),
        help="Local Deep Lake dataset path (default: DEEPLAKE_LOCAL_PATH).",
    )
    parser.add_argument(
        "--s3-uri",
        default=_env("DEEPLAKE_S3_URI"),
        help="S3 URI, e.g. s3://bucket/dataset (default: DEEPLAKE_S3_URI).",
    )
    parser.add_argument(
        "--backup-dir",
        default=_env("DEEPLAKE_BACKUP_DIR", os.path.expanduser("~/deeplake_backups")),
        help="Directory for timestamped backups (default: DEEPLAKE_BACKUP_DIR or ~/deeplake_backups).",
    )
    args = parser.parse_args()

    local_path = (args.local_path or "").strip()
    s3_uri = (args.s3_uri or "").strip()
    backup_dir = (args.backup_dir or "").strip() or os.path.expanduser("~/deeplake_backups")

    if not local_path or not Path(local_path).exists():
        print("❌ DEEPLAKE_LOCAL_PATH must point to an existing local dataset.", file=sys.stderr)
        print("   Set env or use --local-path.", file=sys.stderr)
        return 1

    if not args.backup_only and not s3_uri:
        print("❌ DEEPLAKE_S3_URI is required for sync (or use --backup-only).", file=sys.stderr)
        return 1

    if not s3_uri.startswith("s3://"):
        print("❌ DEEPLAKE_S3_URI must be like s3://bucket/dataset_name", file=sys.stderr)
        return 1

    try:
        import deeplake
    except ImportError:
        print("❌ deeplake not installed. Install with: pip install deeplake", file=sys.stderr)
        return 1

    # 1) Full backup (always, before any S3 write)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"deeplake_backup_{timestamp}")
    Path(backup_dir).mkdir(parents=True, exist_ok=True)
    print(f"📦 Backup: {local_path} → {backup_path}")
    try:
        deeplake.copy(src=local_path, dst=backup_path)
        print(f"✅ Backup done: {backup_path}")
    except Exception as e:
        print(f"❌ Backup failed: {e}", file=sys.stderr)
        return 1

    if args.backup_only:
        return 0

    # 2) Sync to S3
    if args.first_time:
        print(f"📤 First-time copy: {local_path} → {s3_uri}")
        try:
            deeplake.copy(src=local_path, dst=s3_uri)
            print("✅ First-time copy to S3 done.")
        except Exception as e:
            print(f"❌ Copy to S3 failed: {e}", file=sys.stderr)
            return 1
    else:
        print(f"📤 Delta push: {local_path} → {s3_uri}")
        try:
            ds = deeplake.open(local_path)
            ds.push(s3_uri)
            print("✅ Delta push to S3 done.")
        except Exception as e:
            print(f"❌ Push to S3 failed: {e}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

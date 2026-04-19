#!/usr/bin/env python3
"""
Moved: Deep Lake → S3 sync script now lives in the deeplakeclaude project.

  ~/Documents/code/deeplakeclaude/scripts/deeplake_s3_sync.py

Run from that directory after setting DEEPLAKE_LOCAL_PATH and DEEPLAKE_S3_URI.
See ~/Documents/code/deeplakeclaude/README.md
"""
from __future__ import annotations

import sys


def main() -> int:
    print(
        "ℹ️  deeplake_s3_sync.py moved to:\n"
        "   ~/Documents/code/deeplakeclaude/scripts/deeplake_s3_sync.py\n"
        "   See ~/Documents/code/deeplakeclaude/README.md",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

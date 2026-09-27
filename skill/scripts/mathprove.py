#!/usr/bin/env python3
"""Stable v9 entrypoint; intentionally independent of unreviewed legacy runtime."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_v9.cli import main
if __name__ == "__main__":
    raise SystemExit(main())

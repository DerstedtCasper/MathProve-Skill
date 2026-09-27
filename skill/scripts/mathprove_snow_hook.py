#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime_v9.snow_hooks import main

if __name__ == "__main__":
    raise SystemExit(main())

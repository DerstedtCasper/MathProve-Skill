#!/usr/bin/env python3
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
runpy.run_path(str(ROOT / "skill" / "scripts" / "mathprove_v8_pseudotest.py"), run_name="__main__")

import runpy
import sys
from pathlib import Path


def run(script_name: str) -> None:
    target = Path(__file__).resolve().parents[1] / "skill" / "scripts" / script_name
    if not target.exists():
        raise SystemExit(f"missing target script: {target}")
    script_dir = str(target.parent)
    skill_root = str(target.parents[1])
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    if skill_root not in sys.path:
        sys.path.insert(0, skill_root)
    runpy.run_path(str(target), run_name="__main__")

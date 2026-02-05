"""Expose skill scripts for import-based tests."""
from importlib import import_module
from pathlib import Path
import sys

_SKILL_SCRIPTS = Path(__file__).resolve().parents[2] / "skill" / "scripts"
if str(_SKILL_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SKILL_SCRIPTS))

problem_router = import_module("problem_router")
step_router = import_module("step_router")

__all__ = ["problem_router", "step_router"]

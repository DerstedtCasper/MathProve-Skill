import json
import os
import pathlib
import subprocess
import tempfile


def _repo_root() -> pathlib.Path:
    return pathlib.Path(__file__).resolve().parents[1]


def test_check_routes_missing_sympy():
    repo = _repo_root()
    script_path = repo / "scripts" / "check_routes.py"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        fake = temp_dir / "sympy.py"
        fake.write_text("raise ImportError('blocked')\n", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = str(temp_dir)
        proc = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        assert proc.returncode == 2
        data = json.loads(proc.stdout)
        assert data["status"] == "user_action_required"
        assert any(m.get("route") == "sympy" for m in data.get("missing", []))


def test_magi_veto_stops_steps_generation():
    repo = _repo_root()
    script_path = repo / "scripts" / "magi_plan.py"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        steps_out = temp_dir / "steps.json"
        draft_out = temp_dir / "draft.md"
        proc = subprocess.run(
            [
                "python",
                str(script_path),
                "--problem",
                "force veto test",
                "--force-veto",
                "--steps-out",
                str(steps_out),
                "--draft",
                str(draft_out),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 2
        data = json.loads(proc.stdout)
        assert data["status"] == "user_action_required"
        payload = json.loads(steps_out.read_text(encoding="utf-8"))
        steps = payload.get("steps") or []
        assert all(step.get("status") != "passed" for step in steps)

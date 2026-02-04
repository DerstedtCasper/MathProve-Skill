"""验证草稿写入逻辑。"""
import json
import pathlib
import subprocess
import tempfile


def test_draft_logger_append():
    with tempfile.TemporaryDirectory() as temp_dir:
        draft_path = pathlib.Path(temp_dir) / "draft.md"
        step = {
            "id": "S1",
            "goal": "验证恒等式",
            "difficulty": "easy",
            "route": "sympy",
            "status": "passed",
            "evidence_digest": "tests",
            "notes": "ok",
        }
        script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "draft_logger.py"
        cmd = [
            "python",
            str(script_path),
            "--draft",
            str(draft_path),
            "--step-json",
            json.dumps(step, ensure_ascii=False),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        assert proc.returncode == 0
        content = draft_path.read_text(encoding="utf-8")
        assert "S1" in content


def test_draft_logger_rejects_unverified_by_default():
    with tempfile.TemporaryDirectory() as temp_dir:
        draft_path = pathlib.Path(temp_dir) / "draft.md"
        step = {
            "id": "S1",
            "goal": "未验证步骤不应进入草稿",
            "difficulty": "easy",
            "route": "sympy",
            "status": "pending",
            "evidence_digest": "tests",
            "notes": "ok",
        }
        script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "draft_logger.py"
        cmd = [
            "python",
            str(script_path),
            "--draft",
            str(draft_path),
            "--step-json",
            json.dumps(step, ensure_ascii=False),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        assert proc.returncode != 0



def test_draft_logger_rejects_missing_evidence():
    with tempfile.TemporaryDirectory() as temp_dir:
        draft_path = pathlib.Path(temp_dir) / "draft.md"
        step = {
            "id": "S1",
            "goal": "????????",
            "difficulty": "easy",
            "route": "sympy",
            "status": "passed",
            "notes": "ok",
        }
        script_path = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "draft_logger.py"
        cmd = [
            "python",
            str(script_path),
            "--draft",
            str(draft_path),
            "--step-json",
            json.dumps(step, ensure_ascii=False),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        assert proc.returncode != 0

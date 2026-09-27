import importlib.util
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from helpers import WorkspaceCase
from runtime_v9.snow_hooks import command_for, dispatch, merge_rules

spec = importlib.util.spec_from_file_location("install_snow_hooks", Path(__file__).resolve().parents[1] / "scripts/install_snow_hooks.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
install = module.install


class SnowHookTests(WorkspaceCase):
    def test_inactive_project_is_silent(self):
        with tempfile.TemporaryDirectory() as empty:
            code, output, error = dispatch("onSessionStart", {"cwd": empty, "sessionId": "s"}, "cli")
        self.assertEqual((code, output, error), (0, None, None))

    def test_session_start_injects_bound_run_metadata(self):
        self.store.bind("snow-session", "r")
        code, output, error = dispatch("onSessionStart", {"cwd": str(self.root), "sessionId": "snow-session"}, "cli")
        self.assertEqual((code, error), (0, None))
        self.assertIn("r", output["additionalContext"])
        self.assertNotIn("For every natural number", output["additionalContext"])

    def test_cli_blocks_direct_state_edit_without_terminating_session(self):
        event = {"cwd": str(self.root), "toolName": "filesystem-edit", "args": {"filePath": ".mathprove/state.sqlite3"}}
        code, output, error = dispatch("beforeToolCall", event, "cli")
        self.assertEqual(code, 1)
        self.assertIsNone(output)
        self.assertIn("controller", error)

    def test_app_blocks_direct_state_edit(self):
        event = {"cwd": str(self.root), "toolName": "filesystem-edit", "args": {"filePath": ".mathprove/state.sqlite3"}}
        code, output, error = dispatch("beforeToolCall", event, "app")
        self.assertEqual(code, 2)
        self.assertIsNone(output)
        self.assertIn("controller", error)

    def test_terminal_self_review_is_blocked(self):
        event = {"cwd": str(self.root), "toolName": "terminal-execute", "args": json.dumps({"command": "python mathprove.py review r --human-ack"})}
        code, _, error = dispatch("beforeToolCall", event, "cli")
        self.assertEqual(code, 1)
        self.assertIn("Human review", error)

    @unittest.skipUnless(os.name == "nt", "Windows PowerShell exit-code smoke")
    def test_windows_app_command_preserves_block_exit_code(self):
        script = Path(__file__).resolve().parents[1] / "skill/scripts/mathprove_snow_hook.py"
        command = command_for(script, "beforeToolCall", "app", sys.executable)
        event = {"cwd": str(self.root), "toolName": "filesystem-edit", "args": {"filePath": ".mathprove/state.sqlite3"}}
        result = subprocess.run(command, input=json.dumps(event), text=True, capture_output=True, shell=True, timeout=10)
        self.assertEqual(result.returncode, 2, result.stderr)

    def test_neutral_tool_keeps_host_permission_decision(self):
        event = {"cwd": str(self.root), "toolName": "filesystem-edit", "args": {"filePath": "notes.md"}}
        self.assertEqual(dispatch("beforeToolCall", event, "cli"), (0, None, None))

    def test_stop_creates_checkpoint_for_bound_run(self):
        self.store.bind("snow-session", "r")
        code, _, error = dispatch("onStop", {"cwd": str(self.root), "sessionId": "snow-session"}, "cli")
        self.assertEqual((code, error), (0, None))
        self.assertTrue(list((self.root / ".mathprove/checkpoints").glob("r-*.json")))

    def test_rule_merge_preserves_other_hooks_and_is_idempotent(self):
        other = {"description": "existing", "hooks": [{"type": "command", "command": "echo existing", "enabled": True}]}
        first = merge_rules([other], "beforeToolCall", Path("C:/skill/scripts/mathprove_snow_hook.py"), "cli", "C:/Python/python.exe")
        second = merge_rules(first, "beforeToolCall", Path("C:/skill/scripts/mathprove_snow_hook.py"), "cli", "C:/Python/python.exe")
        self.assertEqual(len(second), 2)
        self.assertEqual(second[0], other)
        self.assertTrue(second[1]["hooks"][0]["enabled"])
        self.assertEqual(second[1]["matcher"], "filesystem-*,terminal-execute")

    def test_installer_preserves_existing_cli_and_app_rules(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            cli_dir = base / "cli-hooks"
            cli_dir.mkdir()
            existing = {"beforeToolCall": [{"description": "other", "hooks": [{"type": "command", "command": "echo other", "enabled": True}]}]}
            (cli_dir / "beforeToolCall.json").write_text(json.dumps(existing), encoding="utf-8")
            db_path = base / "snowapp.db"
            with closing(sqlite3.connect(db_path)) as db:
                db.execute("CREATE TABLE system_settings (id TEXT PRIMARY KEY, setting_name TEXT NOT NULL, setting_code TEXT NOT NULL UNIQUE, setting_value TEXT NOT NULL, created_at TEXT, updated_at TEXT)")
                db.execute("INSERT INTO system_settings (id,setting_name,setting_code,setting_value) VALUES (?,?,?,?)", ("x", "Hooks config", "hooks_global", json.dumps(existing)))
                db.commit()
            skill_script = base / "mathprove_snow_hook.py"
            skill_script.write_text("# test fixture", encoding="utf-8")
            backup_dir = base / "backups"
            preview = install(cli_dir, db_path, skill_script, backup_dir, sys.executable, apply=False)
            self.assertFalse(preview["applied"])
            self.assertEqual(json.loads((cli_dir / "beforeToolCall.json").read_text(encoding="utf-8")), existing)
            first = install(cli_dir, db_path, skill_script, backup_dir, sys.executable, apply=True)
            second = install(cli_dir, db_path, skill_script, backup_dir, sys.executable, apply=True)
            self.assertTrue(first["applied"])
            self.assertFalse(second["changed"])
            cli = json.loads((cli_dir / "beforeToolCall.json").read_text(encoding="utf-8"))
            self.assertEqual(cli["beforeToolCall"][0], existing["beforeToolCall"][0])
            self.assertEqual(len(cli["beforeToolCall"]), 2)
            with closing(sqlite3.connect(db_path)) as db:
                app = json.loads(db.execute("SELECT setting_value FROM system_settings WHERE setting_code='hooks_global'").fetchone()[0])
            self.assertEqual(app["beforeToolCall"][0], existing["beforeToolCall"][0])
            self.assertEqual(len(app["beforeToolCall"]), 2)
            self.assertTrue(list(backup_dir.glob("*/snowapp.db")))

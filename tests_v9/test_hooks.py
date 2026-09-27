import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from helpers import WorkspaceCase, RESEARCH
from runtime_v9.hooks import handle, EVENTS

SCRIPT=Path(__file__).resolve().parents[1]/'skill/scripts/mathprove_hook.py'

class HookTests(WorkspaceCase):
    def payload(self,event,**kw):return {"session_id":"s","cwd":str(self.root),"hook_event_name":event,**kw}
    def test_all_lifecycle_outputs_are_json(self):
        for event in EVENTS:
            with self.subTest(event=event):
                result=handle(self.payload(event),event,self.root)
                json.dumps(result)
                self.assertIsInstance(result,dict)
    def test_hook_context_does_not_inject_task_text(self):
        self.store.add_task("r","t","prover","UNTRUSTED_INSTRUCTION secret context")
        out=handle(self.payload("SessionStart"),"SessionStart",self.root)
        self.assertNotIn("UNTRUSTED_INSTRUCTION",json.dumps(out))
        self.assertIn("spec_hash",json.dumps(out))
    def test_session_ambiguity_does_not_guess(self):
        self.store.create_run("r2",RESEARCH)
        self.assertIn("unambiguous",json.dumps(handle(self.payload("SessionStart"),"SessionStart",self.root)))
    def test_pretool_denies_direct_database_write(self):
        p=self.payload("PreToolUse",tool_name="Write",tool_input={"file_path":".mathprove/state.sqlite3"})
        self.assertEqual(handle(p,"PreToolUse",self.root)['hookSpecificOutput']['permissionDecision'],'deny')
    def test_pretool_handles_patch_paths_from_subdir(self):
        (self.root/'sub').mkdir()
        p=self.payload("PreToolUse",cwd=str(self.root/'sub'),tool_name="apply_patch",tool_input={"command":"*** Begin Patch\n*** Update File: ../.mathprove/state.sqlite3\n*** End Patch"})
        self.assertEqual(handle(p,"PreToolUse",self.root)['hookSpecificOutput']['permissionDecision'],'deny')
    def test_pretool_never_grants_permission(self):
        p=self.payload("PreToolUse",tool_name="Bash",tool_input={"command":"echo hello"})
        self.assertEqual(handle(p,"PreToolUse",self.root),{})
    def test_pretool_denies_accidental_self_review(self):
        p=self.payload("PreToolUse",tool_name="Bash",tool_input={"command":"python mathprove.py review r --human-ack"})
        self.assertEqual(handle(p,"PreToolUse",self.root)['hookSpecificOutput']['permissionDecision'],'deny')
    def test_tool_success_does_not_advance_gates(self):
        p=self.payload("PostToolUse",tool_name="Bash",tool_input={"command":"lake build"},tool_response={"exit_code":0},tool_use_id="one")
        handle(p,"PostToolUse",self.root)
        self.assertIsNone(self.store.status("r")['last_accepted_stage'])
    def test_posttool_deduplicates_without_logging_secrets(self):
        p=self.payload("PostToolUse",tool_name="Bash",tool_input={"command":"API_KEY=secret123 echo x"},tool_response="private paper",tool_use_id="same")
        before=self.store.audit_events()['events'];handle(p,"PostToolUse",self.root);handle(p,"PostToolUse",self.root)
        self.assertEqual(self.store.audit_events()['events'],before+1)
        logs=json.dumps(self.store.memory("r"));self.assertNotIn("secret123",logs);self.assertNotIn("private paper",logs)
    def test_stop_allows_unresolved_work_after_checkpoint(self):
        out=handle(self.payload("Stop"),"Stop",self.root)
        self.assertEqual(out,{});self.assertTrue(list((self.root/'.mathprove/checkpoints').glob('*.json')))
    def test_lifecycle_does_not_invoke_compiler(self):
        with patch("runtime_v9.runner.verify",side_effect=AssertionError("No compiler in hook")):
            for event in EVENTS:handle(self.payload(event),event,self.root)
    def invoke(self,event,value):
        return subprocess.run([sys.executable,str(SCRIPT),'--root',str(self.root),'--event',event],input=value,text=True,capture_output=True,timeout=10)
    def test_real_subprocess_stdout_is_exact_json(self):
        p=self.invoke('SessionStart',json.dumps(self.payload('SessionStart')))
        self.assertEqual(p.returncode,0);self.assertEqual(p.stderr,'');self.assertIn('hookSpecificOutput',json.loads(p.stdout))
    def test_invalid_json_pretool_fails_closed(self):
        p=self.invoke('PreToolUse','not json')
        self.assertEqual(json.loads(p.stdout)['hookSpecificOutput']['permissionDecision'],'deny');self.assertNotIn('not json',p.stderr)
    def test_duplicate_json_keys_rejected(self):
        p=self.invoke('PreToolUse','{"session_id":"a","session_id":"b"}')
        self.assertEqual(json.loads(p.stdout)['hookSpecificOutput']['permissionDecision'],'deny')
    def test_stop_failure_never_infinite_blocks(self):
        # Unknown explicit run reliably exercises the error path, not a mocked hook output.
        args=[sys.executable,str(SCRIPT),'--root',str(self.root),'--event','Stop','--run','missing']
        for active in (False,True):
            p=subprocess.run(args,input=json.dumps(self.payload('Stop',stop_hook_active=active)),text=True,capture_output=True,timeout=10)
            out=json.loads(p.stdout)
            self.assertEqual(out.get('decision')=='block',not active)

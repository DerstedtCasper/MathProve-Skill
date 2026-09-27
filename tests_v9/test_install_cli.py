import base64
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import tomllib
import unittest
from helpers import WorkspaceCase, RESEARCH
from runtime_v9.core import ROLES, ProtocolError
from runtime_v9.cli import packet, export_review
from runtime_v9.install import install, merge_hooks, agent_config, TAG, hook_group

BASE=Path(__file__).resolve().parents[1]
SKILL=BASE/'skill'
CLI=SKILL/'scripts/mathprove.py'

class InstallTests(WorkspaceCase):
    def test_install_idempotent_and_no_global_configuration(self):
        first=install(SKILL,self.root);second=install(SKILL,self.root)
        self.assertTrue(first['changed_paths']);self.assertEqual(second['changed_paths'],[])
        self.assertFalse((self.root/'.codex/config.toml').exists())
    def test_dry_run_does_not_write_skill(self):
        install(SKILL,self.root,dry_run=True)
        self.assertFalse((self.root/'.agents').exists())
    def test_existing_hooks_preserved(self):
        p=self.root/'.codex/hooks.json';p.parent.mkdir()
        custom={"hooks":{"Stop":[{"hooks":[{"type":"command","command":"echo my-hook","statusMessage":"mine"}]}]},"description":"keep"}
        p.write_text(json.dumps(custom), encoding="utf-8");result=install(SKILL,self.root)
        actual=json.loads(p.read_text(encoding="utf-8"));self.assertEqual(actual['hooks']['Stop'][0],custom['hooks']['Stop'][0]);self.assertEqual(actual['description'],'keep');self.assertTrue(result['backup'])
    def test_mixed_group_preserves_unrelated_handler(self):
        old={"hooks":{"Stop":[{"hooks":[{"type":"command","command":"mathprove_hook.py old","statusMessage":TAG+'old'},{"type":"command","command":"keep"}]}]}}
        value=merge_hooks(old,self.root,self.root/'skill')
        self.assertEqual(value['hooks']['Stop'][0]['hooks'],[{"type":"command","command":"keep"}])
    def test_modified_agent_requires_upgrade(self):
        install(SKILL,self.root);p=self.root/'.codex/agents/mp_prover.toml';p.write_text('custom config', encoding="utf-8")
        with self.assertRaises(ProtocolError):install(SKILL,self.root)
        result=install(SKILL,self.root,upgrade=True);self.assertTrue(result['backup']);self.assertNotEqual(p.read_text(encoding="utf-8"),'custom config')
    def test_symlink_destination_refused(self):
        other=self.root/'other';other.mkdir();self.symlink_or_skip(self.root/'.codex', other, target_is_directory=True)
        with self.assertRaises(ProtocolError):install(SKILL,self.root)
    def test_nine_configs_use_current_toml_schema(self):
        for role in ROLES:
            with self.subTest(role=role):
                value=tomllib.loads(agent_config(SKILL,role));self.assertEqual(value['name'],'mp_'+role);self.assertIn('description',value);self.assertIn('developer_instructions',value);self.assertNotIn('model',value)
    def test_shared_prompts_are_generated_consistently(self):
        for role in ROLES:
            self.assertEqual((BASE/f'integrations/codex/agents/mp_{role}.toml').read_text(encoding="utf-8"),agent_config(SKILL,role))
    def test_installed_hook_runs_from_subdirectory_with_spaces(self):
        install(SKILL,self.root);sub=self.root/'sub directory';sub.mkdir();config=json.loads((self.root/'.codex/hooks.json').read_text(encoding="utf-8"));command=config['hooks']['SessionStart'][-1]['hooks'][0]['command']
        p=subprocess.run(shlex.split(command),cwd=sub,input=json.dumps({"session_id":"s","cwd":str(sub),"hook_event_name":"SessionStart"}),capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('run=r',json.dumps(json.loads(p.stdout)))
    def test_windows_command_escapes_apostrophes_without_shell_interpolation(self):
        root=self.root/"a'$x";handler=hook_group(root,root/'skill','Stop')['hooks'][0]
        encoded=handler['commandWindows'].split()[-1];script=base64.b64decode(encoded).decode('utf-16le')
        self.assertIn("a''$x",script);self.assertTrue(script.startswith("& '"))
    @unittest.skipUnless(os.name=='nt','Native Windows hook execution not available in this Linux delivery environment')
    def test_native_windows_hook(self):
        install(SKILL,self.root);config=json.loads((self.root/'.codex/hooks.json').read_text(encoding="utf-8"));command=config['hooks']['SessionStart'][-1]['hooks'][0]['commandWindows']
        p=subprocess.run(command,input=json.dumps({"session_id":"s","cwd":str(self.root),"hook_event_name":"SessionStart"}),capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('hookSpecificOutput',json.loads(p.stdout))

class CLITests(WorkspaceCase):
    def invoke(self,*args):
        return subprocess.run([sys.executable,str(CLI),'--root',str(self.root),*args],capture_output=True,text=True,timeout=10)
    def test_cli_status_json(self):
        p=self.invoke('status','r');self.assertEqual(p.returncode,0);self.assertEqual(json.loads(p.stdout)['run_id'],'r')
    def test_rejected_gate_exit_status(self):
        p=self.invoke('gate','r','release');self.assertEqual(p.returncode,2);self.assertFalse(json.loads(p.stdout)['accepted'])
    def test_doctor_does_not_fabricate_host_verification(self):
        p=self.invoke('doctor');self.assertFalse(json.loads(p.stdout)['capabilities']['live_host_compatibility_verified'])
    def test_invalid_input_is_json_error(self):
        p=self.invoke('status','missing');self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,'');self.assertIn('error',json.loads(p.stderr))
    def test_cli_claim_submit_with_private_token_file(self):
        self.store.add_task('r','t','prover','x');claim=json.loads(self.invoke('claim','r','--owner','w').stdout)
        self.artifact('claim.private.json',claim);self.artifact('result.json',self.result(claim))
        p=self.invoke('finish','r','t','--owner','w','--token-file','claim.private.json','--result','result.json');self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(json.loads(p.stdout)['state'],'done')
    def test_packet_excludes_lease_token(self):
        self.store.add_task('r','t','prover','x');claim=self.store.claim('r','w')
        self.assertNotIn(claim['lease_token'],json.dumps(packet(self.store,'r','t')))
    def test_blind_packet_omits_informal_statement_and_advocacy(self):
        spec={**RESEARCH,'mode':'formal','lean':{'project':'lean','module':'Demo','declaration':'Demo.target','expected_type':'True'}}
        self.store.revise('r',spec,'formal');self.store.add_task('r','a','auditor','ADVOCACY prove this is correct')
        result=json.dumps(packet(self.store,'r','a',blind=True));self.assertNotIn(RESEARCH['statement'],result);self.assertNotIn('ADVOCACY',result)
    def test_review_export_omits_db_and_tokens(self):
        import zipfile
        self.through_verify();out=export_review(self.store,'r','WORKSPACE/review.zip')
        with zipfile.ZipFile(out['path']) as z:
            self.assertFalse(any('sqlite' in n for n in z.namelist()));self.assertIn('review.json',z.namelist());self.assertNotIn('lease_token',z.read('review.json').decode())
    def test_export_refuses_stale_evidence(self):
        self.evidence('candidate','x');self.artifact('candidate.json','changed')
        with self.assertRaises(ProtocolError):export_review(self.store,'r','review.zip')
    def test_export_will_not_overwrite(self):
        export_review(self.store,'r','review.zip')
        with self.assertRaises(ProtocolError):export_review(self.store,'r','review.zip')

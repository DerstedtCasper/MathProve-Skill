"""Mocked runner tests exercise orchestration, not Lean correctness.

The optional real smoke test is skipped unless explicitly opted in and lake exists.
No synthetic successful receipt is distributed as an example proof certificate.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from helpers import WorkspaceCase, RESEARCH
from runtime_v9.core import ProtocolError, digest, file_hash
from runtime_v9.runner import (verify, verify_current_receipt, parse_axioms, lock_errors,
                               strip_comments_strings, static_flags, source_inventory,
                               run_process, compiled_inventory)

FORMAL={**RESEARCH,"mode":"formal","lean":{"project":"lean","module":"Demo","declaration":"Demo.target","expected_type":"∀ n : Nat, n = n"}}

class RunnerTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.project=self.root/'lean';self.project.mkdir()
        self.artifact('lean/lean-toolchain','leanprover/lean4:v4.19.0\n')
        self.artifact('lean/lakefile.toml','name = "demo"\ndefaultTargets = ["Demo"]\n[[lean_lib]]\nname = "Demo"\n')
        self.artifact('lean/lake-manifest.json',{"version":"1.1.0","packagesDir":".lake/packages","packages":[],"name":"demo","lakeDir":".lake"})
        self.artifact('lean/Demo.lean','namespace Demo\ntheorem target (n : Nat) : n = n := rfl\nend Demo\n')
        self.store.revise('r',FORMAL,'formal fixture')
        self.fake_lean=self.artifact('fixture-tools/lean','MOCK executable identity, not real Lean')
        self.fake_lake=self.artifact('fixture-tools/lake','MOCK executable identity, not real Lake')
    def mocked_run(self,axioms='',exit_code=0,mutation=None):
        def which(name):return str(self.fake_lake) if name=='lake' else shutil.which(name)
        def output(argv,cwd,timeout=20):
            if '--version' in argv:return 'Lean (version 4.19.0, mock fixture)'
            return str(self.fake_lean)
        def process(argv,cwd,log,timeout):
            if 'build' in argv:
                artifact=cwd/'.lake/build/lib/lean/Demo.olean';artifact.parent.mkdir(parents=True,exist_ok=True);artifact.write_text('MOCK ARTIFACT, NOT A LEAN PROOF')
                log.write_text('MOCK build stdout\n')
                if mutation:mutation(cwd)
            else:
                name=Path(argv[-1]).stem
                log.write_text(f"'{name}' depends on axioms: [{axioms}]\n" if axioms else f"'{name}' does not depend on any axioms\n")
            return {"argv":argv,"exit_code":exit_code,"timed_out":False,"elapsed_seconds":0.0,"log_sha256":file_hash(log)}
        with patch('runtime_v9.runner.shutil.which',side_effect=which),patch('runtime_v9.runner._command_output',side_effect=output),patch('runtime_v9.runner.run_process',side_effect=process):
            return verify(self.store,'r',acknowledge=True,timeout=30)
    def receipt(self):
        with self.store.connect() as c:
            e=c.execute("SELECT object_path FROM evidence WHERE kind='lean_replay' ORDER BY created DESC LIMIT 1").fetchone()
            return json.loads((self.root/e[0]).read_text(encoding="utf-8"))
    def test_pinned_zero_dependency_project_valid(self):
        self.assertEqual(lock_errors(self.project),[])
    def test_unpinned_toolchain_rejected(self):
        self.artifact('lean/lean-toolchain','leanprover/lean4:stable')
        self.assertTrue(lock_errors(self.project))
    def test_unpinned_dependency_rejected(self):
        self.artifact('lean/lake-manifest.json',{"packages":[{"name":"mathlib","type":"git","url":"https://github.com/leanprover-community/mathlib4","rev":"main"}]})
        self.assertTrue(lock_errors(self.project))
    def test_path_dependency_rejected(self):
        self.artifact('lean/lake-manifest.json',{"packages":[{"name":"local","type":"path","dir":"../x"}]})
        self.assertTrue(lock_errors(self.project))
    def test_unsafe_dependency_name_rejected(self):
        self.artifact('lean/lake-manifest.json',{"packages":[{"name":"../x","type":"git","url":"https://example.invalid/x","rev":"a"*40}]})
        self.assertTrue(lock_errors(self.project))
    def test_comments_and_strings_do_not_trigger_static_flags(self):
        self.artifact('lean/Demo.lean','/- sorry /- axiom nested -/ -/\n-- admit\ndef text := "sorry"\n')
        self.assertEqual(static_flags(self.project,source_inventory(self.project)),[])
    def test_sorry_and_unsafe_rejected(self):
        self.artifact('lean/Demo.lean','theorem x : True := by sorry\nunsafe def x := 1\n')
        self.assertEqual(len(static_flags(self.project,source_inventory(self.project))),2)
    def test_source_symlink_rejected(self):
        self.symlink_or_skip(self.project/'link.lean', self.project/'Demo.lean')
        with self.assertRaises(ProtocolError):source_inventory(self.project)
    def test_axiom_output_must_be_unique(self):
        with self.assertRaises(ProtocolError):parse_axioms("'a' depends on axioms: []\n'a' does not depend on any axioms",'a')
    def test_unknown_axiom_output_rejected(self):
        with self.assertRaises(ProtocolError):parse_axioms('looks proved','a')
    def test_standard_axiom_parse(self):
        self.assertEqual(parse_axioms("'a' depends on axioms: [propext, Classical.choice, Quot.sound]",'a'),['Classical.choice','Quot.sound','propext'])
    def test_build_requires_operator_consent(self):
        with self.assertRaises(ProtocolError):verify(self.store,'r',acknowledge=False)
    def test_missing_lake_never_produces_success(self):
        with patch('runtime_v9.runner.shutil.which',return_value=None),self.assertRaises(ProtocolError):verify(self.store,'r',acknowledge=True)
        self.assertFalse(any(e['kind']=='lean_replay' for e in self.store.status('r')['evidence']))
    def test_mock_pipeline_binds_target_and_provenance(self):
        result=self.mocked_run();self.assertEqual(result['result'],'checked_local')
        rec=self.receipt();self.assertEqual(verify_current_receipt(self.root,FORMAL,rec),[])
        audit=(self.root/rec['audit_source']['path']).read_text(encoding="utf-8")
        self.assertIn('set_option autoImplicit false',audit);self.assertIn(FORMAL['lean']['expected_type'],audit);self.assertIn('@Demo.target',audit)
        self.assertTrue(rec['compiled_artifacts']);self.assertIn('Not attested',rec['dependency_rebuild_guarantee'])
    def test_mock_sorry_axiom_fails(self):
        self.assertEqual(self.mocked_run(axioms='sorryAx')['result'],'failed')
    def test_mock_nonzero_exit_fails(self):
        self.assertEqual(self.mocked_run(exit_code=1)['result'],'failed')
    def test_mock_build_mutation_fails(self):
        self.assertEqual(self.mocked_run(mutation=lambda p:(p/'unexpected.txt').write_text('added input'))['result'],'failed')
    def test_mock_original_changes_during_build_fail(self):
        self.assertEqual(self.mocked_run(mutation=lambda p:self.artifact('lean/Demo.lean','changed'))['result'],'failed')
    def test_receipt_stales_when_original_source_changes(self):
        self.mocked_run();rec=self.receipt();self.artifact('lean/Demo.lean','changed')
        self.assertTrue(verify_current_receipt(self.root,FORMAL,rec))
    def test_receipt_stales_when_compiled_artifact_changes(self):
        self.mocked_run();rec=self.receipt();name=next(iter(rec['compiled_artifacts']));(self.root/rec['replay_project']/name).write_text('changed')
        self.assertTrue(verify_current_receipt(self.root,FORMAL,rec))
    def test_receipt_stales_when_binary_changes(self):
        self.mocked_run();rec=self.receipt();self.fake_lean.write_text('changed executable')
        self.assertTrue(verify_current_receipt(self.root,FORMAL,rec))
    def test_receipt_stales_when_log_changes(self):
        self.mocked_run();rec=self.receipt();(self.root/rec['logs'][0]['path']).write_text('edited log')
        self.assertTrue(verify_current_receipt(self.root,FORMAL,rec))
    def test_latest_failed_mock_replay_blocks_formal_gate(self):
        self.through_formal_refutation();self.mocked_run();self.assertTrue(self.store.gate('r','verify')['accepted']);self.mocked_run(axioms='sorryAx')
        self.assertFalse(self.store.gate('r','verify')['accepted'])
    def through_formal_refutation(self):
        self.spec_review();self.plan();self.evidence('candidate','fixture only');self.refutation()
        for stage in ('spec','plan','candidate','refutation'):self.assertTrue(self.store.gate('r',stage)['accepted'])
    def test_timeout_kills_real_local_process(self):
        log=self.root/'timeout.log';result=run_process([sys.executable,'-c','import time; time.sleep(10)'],self.root,log,1)
        self.assertTrue(result['timed_out']);self.assertNotEqual(result['exit_code'],0)
    @unittest.skipUnless(os.environ.get('MATHPROVE_RUN_LEAN_SMOKE')=='1' and shutil.which('lake'), 'Real Lean smoke requires lake and explicit MATHPROVE_RUN_LEAN_SMOKE=1; not run in this delivery environment')
    def test_live_lean_opt_in(self):
        result=verify(self.store,'r',acknowledge=True,timeout=600)
        self.assertEqual(result['result'],'checked_local',result)

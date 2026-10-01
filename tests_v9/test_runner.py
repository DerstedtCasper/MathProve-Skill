"""Runner orchestration tests; mocked compilation is not a Lean proof."""
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

from helpers import WorkspaceCase, RESEARCH
from runtime_v9.core import ProtocolError
from runtime_v9.runner import (
    verify, verify_current_receipt, parse_axioms, lock_errors, static_flags,
    source_inventory, run_process, compiled_inventory, verifier_fingerprint,
    dependency_attestations,
)

FORMAL = {
    **RESEARCH,
    "mode": "formal",
    "lean": {
        "project": "lean", "module": "Demo", "declaration": "Demo.target",
        "expected_type": "∀ n : Nat, n = n",
    },
}


class RunnerTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.project = self.root / 'lean'
        self.project.mkdir()
        self.artifact('lean/lean-toolchain', 'leanprover/lean4:stable\n')
        self.artifact('lean/lakefile.toml', 'name = "demo"\ndefaultTargets = ["Demo"]\n[[lean_lib]]\nname = "Demo"\n')
        self.artifact('lean/Demo.lean', 'namespace Demo\ntheorem target (n : Nat) : n = n := rfl\nend Demo\n')
        self.store.revise('r', FORMAL, 'formal fixture')
        self.fake_lake = self.artifact('fixture-tools/lake', 'MOCK Lake')
        self.calls = []

    def mocked_run(self, axioms='', exit_code=0, mutation=None, acknowledge=False,
                   target_exit_code=None, axiom_output=None, timed_out=False):
        def output(argv, cwd, timeout=20):
            return 'Lake version mock' if argv[-2:] == ['lake', '--version'] or argv[1:] == ['--version'] else 'Lean (version nightly, mock fixture)'

        def process(argv, cwd, log, timeout):
            self.calls.append((argv, cwd))
            code = exit_code
            if 'build' in argv:
                artifact = cwd / '.lake/build/lib/lean/Demo.olean'
                artifact.parent.mkdir(parents=True, exist_ok=True)
                artifact.write_text('MOCK ARTIFACT, NOT A LEAN PROOF')
                log.write_text('MOCK build stdout\n')
                if mutation:
                    mutation(cwd)
            else:
                if target_exit_code is not None:
                    code = target_exit_code
                name = Path(argv[-1]).stem
                text = f"'{name}' depends on axioms: [{axioms}]\n" if axioms else f"'{name}' does not depend on any axioms\n"
                log.write_text(axiom_output if axiom_output is not None else text)
            return {"argv": argv, "exit_code": code, "timed_out": timed_out, "elapsed_seconds": 0.0}

        with patch('runtime_v9.runner.shutil.which', return_value=str(self.fake_lake)) as which, \
             patch('runtime_v9.runner._command_output', side_effect=output), \
             patch('runtime_v9.runner.run_process', side_effect=process):
            result = verify(self.store, 'r', acknowledge=acknowledge, timeout=30)
            which.assert_called_once_with('lake')
            return result

    def receipt(self):
        with self.store.connect() as c:
            row = c.execute("SELECT object_path FROM evidence WHERE kind='lean_replay' ORDER BY created DESC LIMIT 1").fetchone()
        return json.loads((self.root / row[0]).read_text(encoding='utf-8'))

    def test_arbitrary_toolchains_and_missing_manifest_accepted(self):
        for toolchain in ('leanprover/lean4:stable', 'leanprover/lean4:nightly', 'local-lean', 'leanprover/lean4:v4.99.0'):
            with self.subTest(toolchain=toolchain):
                self.artifact('lean/lean-toolchain', toolchain)
                self.assertEqual(lock_errors(self.project), [])
        (self.project / 'lean-toolchain').unlink()
        self.assertEqual(lock_errors(self.project), [])

    def test_only_lake_configuration_is_required(self):
        (self.project / 'lakefile.toml').unlink()
        self.assertTrue(lock_errors(self.project))
        self.artifact('lean/lakefile.lean', 'import Lake\nopen Lake DSL\npackage demo\n')
        self.assertEqual(lock_errors(self.project), [])

    def test_main_and_path_dependencies_accepted_without_git(self):
        packages = [
            {"name": "mathlib", "type": "git", "url": "https://github.com/leanprover-community/mathlib4", "rev": "main"},
            {"name": "local", "type": "path", "dir": "../local"},
        ]
        self.artifact('lean/lake-manifest.json', {"packages": packages})
        with patch('runtime_v9.runner._command_output', side_effect=AssertionError('No dependency Git commands')):
            self.assertEqual(lock_errors(self.project), [])
            self.assertEqual(dependency_attestations(self.project), packages)

    def test_dependency_metadata_is_optional(self):
        self.assertEqual(dependency_attestations(self.project), [])

    def test_comments_and_strings_do_not_trigger_static_flags(self):
        self.artifact('lean/Demo.lean', '/- sorry /- axiom nested -/ -/\n-- admit\ndef text := "sorry"\n')
        self.assertEqual(static_flags(self.project, source_inventory(self.project)), [])

    def test_static_scan_reports_only_sorry_admit_and_axiom(self):
        self.artifact('lean/Demo.lean', 'theorem x : True := by sorry\ntheorem y : True := by admit\naxiom z : True\nunsafe def a := 1\nmacro "x" : term => `(True)\nelab "foo" : term => pure (.const ``True [])\nexample : True := by native_decide\n#eval 1\n')
        flags = static_flags(self.project, source_inventory(self.project))
        self.assertEqual(len(flags), 3)
        for token, flag in zip(('sorry', 'admit', 'axiom'), flags):
            self.assertIn(token, flag)

    def test_unrelated_sorry_is_advisory_not_a_build_blocker(self):
        self.artifact('lean/Other.lean', 'example : True := by sorry\n')
        self.assertEqual(self.mocked_run()['result'], 'checked_local')
        self.assertTrue(self.receipt()['static_flags'])

    def test_source_inventory_records_paths_not_hashes(self):
        inventory = source_inventory(self.project)
        self.assertEqual(inventory['Demo.lean'], 'Demo.lean')
        self.artifact('lean/Demo.lean', 'changed')
        self.assertEqual(source_inventory(self.project), inventory)
        self.assertEqual(verifier_fingerprint(), {"version": verifier_fingerprint()['version']})

    def test_source_file_symlinks_are_not_blanket_rejected(self):
        self.symlink_or_skip(self.project / 'link.lean', self.project / 'Demo.lean')
        self.assertIn('link.lean', source_inventory(self.project))

    def test_compiled_inventory_is_path_metadata_only(self):
        self.artifact('lean/.lake/build/Demo.olean', 'old artifact')
        self.assertEqual(compiled_inventory(self.project)['.lake/build/Demo.olean'], '.lake/build/Demo.olean')

    def test_axiom_output_must_be_unique(self):
        with self.assertRaises(ProtocolError):
            parse_axioms("'a' depends on axioms: []\n'a' does not depend on any axioms", 'a')

    def test_unknown_axiom_output_rejected(self):
        with self.assertRaises(ProtocolError):
            parse_axioms('looks proved', 'a')

    def test_standard_axiom_parse(self):
        self.assertEqual(parse_axioms("'a' depends on axioms: [propext, Classical.choice, Quot.sound]", 'a'), ['Classical.choice', 'Quot.sound', 'propext'])

    def test_acknowledge_false_does_not_block_verification(self):
        self.assertEqual(self.mocked_run(acknowledge=False)['result'], 'checked_local')

    def test_missing_lake_never_produces_success(self):
        with patch('runtime_v9.runner.shutil.which', return_value=None), self.assertRaises(ProtocolError):
            verify(self.store, 'r', acknowledge=False)
        self.assertFalse(any(e['kind'] == 'lean_replay' for e in self.store.status('r')['evidence']))

    def test_mock_pipeline_binds_target_and_reuses_original_project(self):
        cache = self.artifact('lean/.lake/packages/local/cache.txt', 'reuse me')
        result = self.mocked_run()
        self.assertEqual(result['result'], 'checked_local')
        rec = self.receipt()
        self.assertEqual(verify_current_receipt(self.root, FORMAL, rec), [])
        self.assertEqual(rec['spec'], FORMAL)
        self.assertEqual(rec['spec_hash'], self.store.status('r')['spec_hash'])
        self.assertEqual(rec['expected_type'], FORMAL['lean']['expected_type'])
        self.assertTrue(all(cwd == self.project for _, cwd in self.calls))
        self.assertEqual(self.calls[0][0][1:], ['build'])
        self.assertEqual(self.calls[1][0][1:3], ['env', 'lean'])
        audit = (self.root / rec['audit_source']['path']).read_text(encoding='utf-8')
        self.assertIn('set_option autoImplicit false', audit)
        self.assertIn(FORMAL['lean']['expected_type'], audit)
        self.assertIn('@Demo.target', audit)
        self.assertEqual(cache.read_text(), 'reuse me')
        self.assertNotIn('sha256', json.dumps(rec))
        self.assertNotIn('source_hash', rec)
        self.assertIn('lean_version', rec['toolchain'])
        self.assertIn('lake_version', rec['toolchain'])

    def test_compatibility_spec_hash_is_taken_from_store_status(self):
        status = self.store.status('r')
        with patch.object(self.store, 'status', return_value={**status, 'spec_hash': 'revision-test-2'}):
            self.assertEqual(self.mocked_run()['result'], 'checked_local')
        self.assertEqual(self.receipt()['spec_hash'], 'revision-test-2')

    def test_mock_sorry_axiom_fails_and_is_distinguished(self):
        self.assertEqual(self.mocked_run(axioms='sorryAx')['result'], 'failed')
        rec = self.receipt()
        self.assertEqual(rec['axioms'], ['sorryAx'])
        self.assertEqual(rec['proof_status'], 'sorry')
        self.assertTrue(rec['target_type_checked'])

    def test_mock_direct_axiom_fails_and_is_distinguished(self):
        self.assertEqual(self.mocked_run(axioms='Demo.assumption')['result'], 'failed')
        self.assertEqual(self.receipt()['proof_status'], 'unexpected_axioms')

    def test_standard_axioms_accepted(self):
        self.assertEqual(self.mocked_run(axioms='propext, Classical.choice, Quot.sound')['result'], 'checked_local')

    def test_mock_nonzero_build_exit_is_retained(self):
        self.assertEqual(self.mocked_run(exit_code=7)['result'], 'failed')
        self.assertEqual(self.receipt()['commands'][0]['exit_code'], 7)
        self.assertEqual(len(self.calls), 1)

    def test_mock_wrong_target_type_exit_is_retained(self):
        self.assertEqual(self.mocked_run(target_exit_code=1)['result'], 'failed')
        self.assertEqual(self.receipt()['commands'][1]['exit_code'], 1)
        self.assertFalse(self.receipt()['target_type_checked'])

    def test_mock_timeout_never_produces_success(self):
        self.assertEqual(self.mocked_run(timed_out=True)['result'], 'failed')

    def test_mock_missing_axiom_report_never_produces_success(self):
        self.assertEqual(self.mocked_run(axiom_output='no axiom report')['result'], 'failed')

    def test_build_source_iteration_is_not_hash_rejected(self):
        self.assertEqual(self.mocked_run(mutation=lambda p: (p / 'Demo.lean').write_text('changed'))['result'], 'checked_local')

    def test_new_goal_during_build_is_not_committed(self):
        changed = {**FORMAL, 'lean': {**FORMAL['lean'], 'expected_type': 'True'}}
        with self.assertRaises(ProtocolError):
            self.mocked_run(mutation=lambda p: self.store.revise('r', changed, 'new goal during compile'))
        self.assertFalse(any(e['kind'] == 'lean_replay' for e in self.store.status('r')['evidence']))

    def test_receipt_survives_source_binary_artifact_and_version_changes(self):
        self.mocked_run()
        rec = self.receipt()
        self.artifact('lean/Demo.lean', 'changed')
        self.artifact('lean/lean-toolchain', 'leanprover/lean4:nightly')
        self.artifact('lean/.lake/build/lib/lean/Demo.olean', 'changed artifact')
        self.fake_lake.unlink()
        rec['verifier'] = {'version': 'old'}
        self.assertEqual(verify_current_receipt(self.root, FORMAL, rec), [])

    def test_receipt_does_not_hash_log_contents(self):
        self.mocked_run()
        rec = self.receipt()
        (self.root / rec['logs'][0]['path']).write_text('edited log')
        self.assertEqual(verify_current_receipt(self.root, FORMAL, rec), [])

    def test_receipt_requires_logs_and_successful_command_results(self):
        self.mocked_run()
        rec = self.receipt()
        bad = {**rec, 'commands': [{**x, 'exit_code': 1} for x in rec['commands']]}
        self.assertTrue(verify_current_receipt(self.root, FORMAL, bad))
        (self.root / rec['logs'][0]['path']).unlink()
        self.assertTrue(verify_current_receipt(self.root, FORMAL, rec))

    def test_receipt_rejects_new_goal_text_and_expected_type(self):
        self.mocked_run()
        rec = self.receipt()
        for changed in ({**FORMAL, 'statement': 'A different mathematical statement'}, {**FORMAL, 'lean': {**FORMAL['lean'], 'expected_type': 'True'}}):
            with self.subTest(changed=changed):
                self.assertTrue(verify_current_receipt(self.root, changed, rec))

    def test_legacy_receipt_uses_audit_target_not_old_hashes(self):
        self.mocked_run()
        rec = self.receipt()
        for key in ('spec', 'expected_type', 'build_succeeded', 'proof_status'):
            rec.pop(key, None)
        rec.update(fresh_build=True, spec_hash='uninterpreted-old-digest', source_hash='ignored', compiled_artifacts={'old': 'ignored'})
        errors = verify_current_receipt(self.root, FORMAL, rec)
        self.assertEqual(errors, ['Legacy receipt lacks mathematical goal text; rerun Lean verification'])
        changed = {**FORMAL, 'lean': {**FORMAL['lean'], 'expected_type': 'True'}}
        self.assertTrue(any('does not match' in e for e in verify_current_receipt(self.root, changed, rec)))
        rec.pop('audit_source')
        self.assertTrue(any('no readable' in e for e in verify_current_receipt(self.root, FORMAL, rec)))

    def test_legacy_receipt_cannot_certify_changed_statement_with_same_lean_type(self):
        self.mocked_run()
        rec = self.receipt()
        rec.pop('spec')
        changed = {**FORMAL, 'statement': 'A different statement with the same Lean configuration'}
        self.assertTrue(verify_current_receipt(self.root, changed, rec))

    def test_latest_failed_mock_replay_blocks_formal_gate(self):
        self.spec_review()
        self.plan()
        self.evidence('candidate', 'fixture only')
        self.refutation()
        for stage in ('spec', 'plan', 'candidate', 'refutation'):
            self.assertTrue(self.store.gate('r', stage)['accepted'])
        self.mocked_run()
        self.assertTrue(self.store.gate('r', 'verify')['accepted'])
        self.mocked_run(axioms='sorryAx')
        self.assertFalse(self.store.gate('r', 'verify')['accepted'])

    def test_local_python_process_uses_spaced_cwd_without_container_discovery(self):
        cwd = self.root / 'local execution with spaces'
        cwd.mkdir()
        log = cwd / 'local process.log'
        argv = [sys.executable, '-c', 'from pathlib import Path; print(Path.cwd())']
        with patch('runtime_v9.runner.shutil.which', side_effect=AssertionError('No container discovery for local execution')):
            result = run_process(argv, cwd, log, 10)
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(result['timed_out'])
        output = log.read_text().strip()
        self.assertEqual(Path(output), cwd)
        self.assertEqual(log.read_text(), str(cwd) + '\n')
        self.assertEqual(result['log_path'], str(log))
        self.assertEqual(result['argv'], argv)

    def test_run_process_preserves_exit_code_and_log_without_hash(self):
        log = self.root / 'process.log'
        result = run_process([sys.executable, '-c', 'print("actual output"); raise SystemExit(3)'], self.root, log, 10)
        self.assertEqual(result['exit_code'], 3)
        self.assertFalse(result['timed_out'])
        self.assertIn('actual output', log.read_text())
        self.assertNotIn('sha256', json.dumps(result))

    def test_timeout_kills_real_local_process(self):
        log = self.root / 'timeout.log'
        result = run_process([sys.executable, '-c', 'import time; time.sleep(10)'], self.root, log, 1)
        self.assertTrue(result['timed_out'])
        self.assertNotEqual(result['exit_code'], 0)

    @unittest.skipUnless(os.environ.get('MATHPROVE_RUN_LEAN_SMOKE') == '1' and shutil.which('lake'), 'Real Lean smoke requires lake and explicit MATHPROVE_RUN_LEAN_SMOKE=1')
    def test_live_lean_opt_in(self):
        result = verify(self.store, 'r', acknowledge=False, timeout=600)
        self.assertEqual(result['result'], 'checked_local', result)

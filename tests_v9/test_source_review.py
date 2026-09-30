"""Research and integration regressions; no source-version acceptance or live Lean."""
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from helpers import WorkspaceCase
from runtime_v9.comath_adapter import (PROFILES, READ_TOOLS, OPERATOR_TOOLS,
                                        operator_config, profile_binding, render_profile)
from runtime_v9.install import hook_group
from runtime_v9.hooks import EVENTS
BASE = Path(__file__).resolve().parents[1]
source = BASE/'skill/runtime/proof_factory_v8.py'
spec = importlib.util.spec_from_file_location('audit_legacy_v8',source)
v8 = importlib.util.module_from_spec(spec);sys.modules[spec.name]=v8;spec.loader.exec_module(v8)

class LegacyRegressionTests(unittest.TestCase):
    def node(self,name,deps=()):return dict(line_id=name,formal_target=name,obligation='test',depends_on=list(deps))
    def candidate(self,name,stage):
        return v8.CandidateEvidence(name,stage,v8.AgentRole.AUDITOR,artifact_paths=['x'],no_sorry=True)
    def test_mixed_stage_rejected(self):
        with self.assertRaisesRegex(ValueError,'exactly one stage'):
            v8.select_candidate([self.candidate('a',v8.Stage.FINAL_AUDIT),self.candidate('b',v8.Stage.SKELETON)])
    def test_duplicate_candidate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError,'unique'):
            v8.select_candidate([self.candidate('a',v8.Stage.SKELETON)]*2)
    def test_invalid_thresholds_rejected(self):
        for value in (float('nan'),float('inf'),-0.1,1.1,True,'0.72'):
            with self.subTest(value=value),self.assertRaises(ValueError):v8.select_candidate([],threshold=value)
    def test_nonfinite_scores_are_zero_not_full_credit(self):
        for value in (float('nan'),float('inf'),-float('inf')):self.assertEqual(v8.clamp01(value),0)
    def test_demo_still_selects_compiled_patch(self):
        d=v8.demo_decision();self.assertTrue(d.accepted);self.assertEqual(d.selected_candidate_id,'compiled_patch')
    def test_two_node_cycle_rejected(self):
        ok,errors=v8.validate_line_map([self.node('a',['b']),self.node('b',['a'])]);self.assertFalse(ok);self.assertIn('cyclic dependency in line map',errors)
    def test_self_cycle_rejected(self):self.assertFalse(v8.validate_line_map([self.node('a',['a'])])[0])
    def test_unknown_dependency_rejected(self):self.assertFalse(v8.validate_line_map([self.node('a',['missing'])])[0])
    def test_explicit_external_dependency_allowed_but_not_verified(self):
        self.assertTrue(v8.validate_line_map([self.node('a',['external'])],external_dependencies=['external'])[0])
    def test_invalid_dependencies_rejected(self):
        for deps in ('bad',{},[None]):
            node=self.node('a');node['depends_on']=deps
            self.assertFalse(v8.validate_line_map([node])[0])
    def test_duplicate_line_rejected(self):self.assertFalse(v8.validate_line_map([self.node('a'),self.node('a')])[0])
    def test_large_dag_no_recursion_limit(self):
        nodes=[self.node(str(i),[str(i-1)] if i else []) for i in range(2500)]
        self.assertTrue(v8.validate_line_map(nodes)[0])
    def test_only_boolean_true_permits_legacy_termination(self):
        for value in ('false','true',1,[],None,False):self.assertFalse(v8.termination_allowed({'final_audit_approved':value})[0])
        self.assertTrue(v8.termination_allowed({'final_audit_approved':True})[0])
    def test_sorry_remains_skeleton_only(self):
        self.assertTrue(v8.lean_static_audit('theorem t : True := by sorry',v8.Stage.SKELETON)[0])
        self.assertFalse(v8.lean_static_audit('theorem t : True := by sorry',v8.Stage.FINAL_AUDIT)[0])

class AdapterRegressionTests(unittest.TestCase):
    def test_actual_comath_roster_not_portable_aliases(self):
        self.assertEqual(set(PROFILES),{'coordinator','librarian','computation','proof-route','formalization','reviewer','graph-builder','security-auditor','math-integrity-auditor'})
    def test_hyphen_ids_and_underscore_roles_preserved(self):
        self.assertEqual(profile_binding('proof-route')['role'],'proof_route')
    def test_profiles_have_no_authority_or_live_claim(self):
        for profile in PROFILES:
            b=profile_binding(profile);self.assertFalse(b['source_pinned']);self.assertTrue(b['historical_reference_only']);self.assertEqual(b['proof_authority'],'none');self.assertFalse(b['may_mutate_trusted_state']);self.assertFalse(b['installed'])
    def test_profiles_rely_on_current_service_not_source_pins(self):
        text=render_profile('formalization','Exact assumptions and Lean compilation.')
        self.assertIn('not a version requirement',text)
        self.assertIn('current service',text)
        self.assertIn('Exact assumptions and Lean compilation.',text)
    def test_legacy_git_blob_interface_does_not_read_or_hash_files(self):
        from runtime_v9.comath_adapter import git_blob
        with patch.object(Path,'read_bytes',side_effect=AssertionError('no source hashing')):
            self.assertIsNone(git_blob(Path('absent-source.ts')))
    def test_generated_profiles_match_sources(self):
        method=(BASE/'skill/assets/v9/research-method.md').read_text(encoding="utf-8")
        for profile in PROFILES:self.assertEqual((BASE/f'integrations/comath/profiles/{profile}.md').read_text(encoding="utf-8"),render_profile(profile,method))
    def test_portable_drafts_are_marked_retired(self):
        for path in (BASE/'integrations/comath/prompts').glob('*.md'):self.assertIn('do not install',path.read_text(encoding="utf-8"))
    def test_mcp_default_is_read_only_and_tokens_not_embedded(self):
        with patch.dict('os.environ',{'COMATH_OPERATOR_TOKEN':'SECRET_TEST_VALUE'}):
            text=operator_config(Path(tempfile.gettempdir())/'space name'/'facade.js')
        c=tomllib.loads(text)['mcp_servers']['comath_operator']
        self.assertEqual(c['enabled_tools'],list(READ_TOOLS));self.assertNotIn('SECRET_TEST_VALUE',text);self.assertNotIn('env',c)
        self.assertEqual(c['default_tools_approval_mode'],'prompt')
    def test_mcp_operator_exposes_request_not_host_approval(self):
        c=tomllib.loads(operator_config(Path(tempfile.gettempdir())/'facade.js','operator'))['mcp_servers']['comath_operator']
        self.assertEqual(c['enabled_tools'],list(OPERATOR_TOOLS));self.assertIn('research_intake_request_approval',c['enabled_tools'])
        self.assertFalse(any(x.endswith('_approve') or 'ticket' in x or 'worker_' in x for x in c['enabled_tools']))
    def test_invalid_access_rejected(self):
        with self.assertRaises(ValueError):operator_config(Path(tempfile.gettempdir())/'facade.js','host')
    def test_relative_mcp_path_rejected(self):
        with self.assertRaises(ValueError):operator_config(Path('facade.js'))
    def test_context_limit_only_on_context_emitting_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for event in EVENTS:
                h=hook_group(root,root/'skill',event)['hooks'][0]
                self.assertEqual('additionalContextLimit' in h,event in ('SessionStart','SubagentStart'))

class CoMathConfigTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('comath_config',BASE/'scripts/comath_codex_config.py')
        self.config=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.config)
    def invoke(self,root):
        stdout=io.StringIO();stderr=io.StringIO()
        with patch.object(sys,'argv',['comath_codex_config.py','--comath-root',str(root)]),patch('sys.stdout',stdout),patch('sys.stderr',stderr):
            code=self.config.main()
        return code,stdout.getvalue(),stderr.getvalue()
    def test_current_source_with_existing_entry_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);entry=root/'services/comathd/dist/control/research-mcp-facade.js'
            entry.parent.mkdir(parents=True);entry.write_text('current facade')
            src=root/'services/comathd/src/control/research-mcp-facade.ts'
            src.parent.mkdir(parents=True);src.write_text('updated source, not a fixed blob')
            code,text,error=self.invoke(root)
            self.assertEqual(code,0,error)
            self.assertEqual(tomllib.loads(text)['mcp_servers']['comath_operator']['args'],[str(entry.resolve())])
    def test_built_entry_does_not_require_source_checkout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);entry=root/'services/comathd/dist/control/research-mcp-facade.js'
            entry.parent.mkdir(parents=True);entry.write_text('current facade')
            code,text,error=self.invoke(root)
            self.assertEqual(code,0,error);self.assertIn('current service',text)
    def test_missing_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            code,text,error=self.invoke(Path(tmp))
            self.assertEqual(code,2);self.assertEqual(text,'');self.assertIn('entry',error)

class OverlayPreconditionTests(unittest.TestCase):
    def fixture(self,root):
        spec=importlib.util.spec_from_file_location('audit_overlay',BASE/'scripts/apply_v9_overlay.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        src=root/'src';dst=root/'dst';src.mkdir();dst.mkdir()
        (src/'legacy.py').write_text('new');(dst/'legacy.py').write_text('old')
        manifest={'schema':'mathprove.overlay.v9','files':{'legacy.py':'obsolete file hash'},'upstream_file_preconditions':{'legacy.py':['obsolete upstream blob']}}
        (src/'RELEASE-MANIFEST.json').write_text(json.dumps(manifest));return m,src,dst
    def test_legacy_preconditions_do_not_block_changed_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=self.fixture(Path(tmp));(dst/'legacy.py').write_text('user changes')
            with patch.object(m.shutil,'which',return_value=None):result=m.apply_overlay(src,dst,apply=True)
            self.assertEqual((dst/'legacy.py').read_text(),'new')
            self.assertEqual((Path(result['backup'])/'legacy.py').read_text(),'user changes')
    def test_byte_identical_reapply_has_no_writes_or_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=self.fixture(Path(tmp))
            with patch.object(m.shutil,'which',return_value=None):
                m.apply_overlay(src,dst,apply=True);result=m.apply_overlay(src,dst,apply=True)
            self.assertEqual(result['files'],[]);self.assertIsNone(result['backup'])
            self.assertEqual((dst/'legacy.py').read_text(),'new')
    def test_missing_legacy_destination_can_be_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=self.fixture(Path(tmp));(dst/'legacy.py').unlink()
            with patch.object(m.shutil,'which',return_value=None):m.apply_overlay(src,dst,apply=True)
            self.assertEqual((dst/'legacy.py').read_text(),'new')

class GitPreservationTests(unittest.TestCase):
    def apply_with_status(self,m,src,dst,status,*,returncode=0):
        from subprocess import CompletedProcess
        # Exercise protection logic without invoking Git or changing a repository.
        def result(args,**kwargs):
            if 'rev-parse' in args:return CompletedProcess(args,0,str(dst),'')
            return CompletedProcess(args,returncode,status,'')
        with patch.object(m.shutil,'which',return_value='git'),patch.object(m.subprocess,'run',side_effect=result):
            return m.apply_overlay(src,dst,apply=True)
    def test_unstaged_target_edit_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=OverlayPreconditionTests().fixture(Path(tmp));(dst/'legacy.py').write_text('local edit')
            with self.assertRaises(m.ProtocolError):self.apply_with_status(m,src,dst,' M legacy.py\n')
            self.assertEqual((dst/'legacy.py').read_text(),'local edit')
    def test_staged_target_edit_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=OverlayPreconditionTests().fixture(Path(tmp));(dst/'legacy.py').write_text('local edit')
            with self.assertRaises(m.ProtocolError):self.apply_with_status(m,src,dst,'M  legacy.py\n')
            self.assertEqual((dst/'legacy.py').read_text(),'local edit')
    def test_unrelated_changes_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=OverlayPreconditionTests().fixture(Path(tmp));(dst/'notes.txt').write_text('private notes')
            result=self.apply_with_status(m,src,dst,'')
            self.assertEqual(result['git_dirty_check'],'planned_destinations_clean');self.assertEqual((dst/'notes.txt').read_text(),'private notes')
            self.assertEqual((dst/'legacy.py').read_text(),'new')
    def test_untracked_target_conflict_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=OverlayPreconditionTests().fixture(Path(tmp));(src/'new.py').write_text('overlay');(dst/'new.py').write_text('user draft')
            p=src/'RELEASE-MANIFEST.json';data=json.loads(p.read_text());data['files']['new.py']='obsolete hash';p.write_text(json.dumps(data))
            with self.assertRaises(m.ProtocolError):self.apply_with_status(m,src,dst,'?? new.py\n')
            self.assertEqual((dst/'new.py').read_text(),'user draft')
    def test_failed_git_inspection_preserves_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=OverlayPreconditionTests().fixture(Path(tmp))
            with self.assertRaisesRegex(m.ProtocolError,'Could not inspect'):self.apply_with_status(m,src,dst,'',returncode=1)
            self.assertEqual((dst/'legacy.py').read_text(),'old')

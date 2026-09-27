"""Regression tests for source-audit changes. No Lean or live Codex is simulated."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch
from helpers import WorkspaceCase
from runtime_v9.comath_adapter import (PROFILES, READ_TOOLS, OPERATOR_TOOLS, COMATH_COMMIT,
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
            b=profile_binding(profile);self.assertEqual(b['source_commit'],COMATH_COMMIT);self.assertEqual(b['proof_authority'],'none');self.assertFalse(b['may_mutate_trusted_state']);self.assertFalse(b['installed'])
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

class OverlayPreconditionTests(unittest.TestCase):
    def fixture(self,root):
        spec=importlib.util.spec_from_file_location('audit_overlay',BASE/'scripts/apply_v9_overlay.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        src=root/'src';dst=root/'dst';src.mkdir();dst.mkdir()
        (src/'legacy.py').write_text('new');(dst/'legacy.py').write_text('old')
        from runtime_v9.comath_adapter import git_blob
        manifest={'schema':'mathprove.overlay.v9','files':{'legacy.py':m.file_hash(src/'legacy.py')},'upstream_file_preconditions':{'legacy.py':[git_blob(dst/'legacy.py')]}}
        (src/'RELEASE-MANIFEST.json').write_text(json.dumps(manifest));return m,src,dst
    def test_source_divergence_rejected_before_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=self.fixture(Path(tmp));(dst/'legacy.py').write_text('user changes')
            with self.assertRaises(m.ProtocolError):m.apply_overlay(src,dst,apply=True)
            self.assertEqual((dst/'legacy.py').read_text(),'user changes');self.assertFalse((dst/'RELEASE-MANIFEST.json').exists())
    def test_pinned_source_and_idempotent_reapply_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=self.fixture(Path(tmp));m.apply_overlay(src,dst,apply=True);m.apply_overlay(src,dst,apply=True)
            self.assertEqual((dst/'legacy.py').read_text(),'new')
    def test_missing_pinned_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst=self.fixture(Path(tmp));(dst/'legacy.py').unlink()
            with self.assertRaises(m.ProtocolError):m.apply_overlay(src,dst,apply=True)

class GitPreservationTests(unittest.TestCase):
    def setup_repo(self,root):
        import subprocess
        m,src,dst=OverlayPreconditionTests().fixture(root)
        # Remove per-file pin here: this group isolates general dirty-worktree protection.
        p=src/'RELEASE-MANIFEST.json';data=json.loads(p.read_text());data.pop('upstream_file_preconditions');p.write_text(json.dumps(data))
        def git(*args):
            return subprocess.run(['git','-C',str(dst),*args],capture_output=True,text=True,check=True)
        git('init','-q');git('add','legacy.py');git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','fixture')
        return m,src,dst,git
    def test_unstaged_target_edit_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst,git=self.setup_repo(Path(tmp));(dst/'legacy.py').write_text('local edit')
            with self.assertRaises(m.ProtocolError):m.apply_overlay(src,dst,apply=True)
            self.assertEqual((dst/'legacy.py').read_text(),'local edit')
    def test_staged_target_edit_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst,git=self.setup_repo(Path(tmp));(dst/'legacy.py').write_text('local edit');git('add','legacy.py')
            with self.assertRaises(m.ProtocolError):m.apply_overlay(src,dst,apply=True)
    def test_unrelated_changes_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst,git=self.setup_repo(Path(tmp));(dst/'notes.txt').write_text('private notes')
            result=m.apply_overlay(src,dst,apply=True)
            self.assertEqual(result['git_dirty_check'],'planned_destinations_clean');self.assertEqual((dst/'notes.txt').read_text(),'private notes')
    def test_untracked_target_conflict_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            m,src,dst,git=self.setup_repo(Path(tmp));(src/'new.py').write_text('overlay');(dst/'new.py').write_text('user draft')
            p=src/'RELEASE-MANIFEST.json';data=json.loads(p.read_text());data['files']['new.py']=m.file_hash(src/'new.py');p.write_text(json.dumps(data))
            with self.assertRaises(m.ProtocolError):m.apply_overlay(src,dst,apply=True)
            self.assertEqual((dst/'new.py').read_text(),'user draft')

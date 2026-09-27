import concurrent.futures
import json
from pathlib import Path
import sqlite3
import time
from unittest.mock import patch
from helpers import WorkspaceCase, RESEARCH
from runtime_v9.core import ProtocolError, Store, STAGES, digest, safe_path, strict_json, validate_plan, validate_spec

class StateTests(WorkspaceCase):
    def test_init_idempotent(self):
        self.assertEqual(Store(self.root,create=True).status("r")["revision"],1)
    def test_duplicate_run_rejected(self):
        with self.assertRaises(ProtocolError): self.store.create_run("r",RESEARCH)
    def test_spec_revision_invalidates_lease(self):
        self.store.add_task("r","t","prover","x"); lease=self.store.claim("r","w")
        self.store.revise("r",{**RESEARCH,"statement":"New statement"},"change")
        with self.assertRaises(ProtocolError): self.finish_lease(lease)
        self.assertEqual(self.store.status("r")["revision"],2)
        self.assertEqual(self.store.status("r")["tasks"],[])
    def test_unchanged_revision_rejected(self):
        with self.assertRaises(ProtocolError): self.store.revise("r",RESEARCH,"not a change")
    def test_identifier_rejects_traversal(self):
        for name in ("../x","x/y","x y","", "x"*65):
            with self.subTest(name=name), self.assertRaises(ProtocolError): self.store.add_task("r",name,"prover","x")
    def test_unknown_role_rejected(self):
        with self.assertRaises(ProtocolError): self.store.add_task("r","t","oracle","x")
    def test_missing_dependency_rejected(self):
        with self.assertRaises(ProtocolError): self.store.add_task("r","t","prover","x",["missing"])
    def test_dependency_readiness(self):
        self.store.add_task("r","a","prover","x"); self.store.add_task("r","b","prover","y",["a"])
        with self.assertRaises(ProtocolError): self.store.claim("r","w","b")
        a=self.store.claim("r","w","a");self.finish_lease(a)
        self.assertEqual(self.store.claim("r","w","b")["task_id"],"b")
    def test_concurrent_claim_cap_and_uniqueness(self):
        for i in range(12): self.store.add_task("r",f"t{i}","prover","x")
        def claim(i):
            try: return Store(self.root).claim("r",f"w{i}")
            except ProtocolError: return None
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool: results=list(pool.map(claim,range(12)))
        winners=[r for r in results if r]
        self.assertEqual(len(winners),2); self.assertEqual(len({x['task_id'] for x in winners}),2)
        self.assertTrue(self.store.audit_events()["consistent"])
    def test_wrong_owner_rejected(self):
        self.store.add_task("r","t","prover","x"); a=self.store.claim("r","w")
        with self.assertRaises(ProtocolError): self.finish_lease(a,owner="another")
    def test_wrong_token_rejected(self):
        self.store.add_task("r","t","prover","x"); a=self.store.claim("r","w"); a['lease_token']='invalid'
        with self.assertRaises(ProtocolError): self.finish_lease(a)
    def test_expired_result_rejected_reap_reclaims(self):
        self.store.add_task("r","t","prover","x")
        with patch("runtime_v9.core.time.time",return_value=100): a=self.store.claim("r","w",ttl=1)
        with patch("runtime_v9.core.time.time",return_value=102):
            with self.assertRaises(ProtocolError): self.finish_lease(a)
            self.store.reap("r"); b=self.store.claim("r","w")
        self.assertNotEqual(a['lease_token'],b['lease_token']); self.assertNotEqual(a['work_dir'],b['work_dir'])
    def test_heartbeat_does_not_count_attempt(self):
        self.store.add_task("r","t","prover","x"); a=self.store.claim("r","w")
        self.store.heartbeat("r","t","w",a['lease_token'])
        self.assertEqual(self.store.status("r")['attempts_used'],1)
    def test_per_task_retry_cap(self):
        self.store.add_task("r","t","prover","x")
        for _ in range(3): self.finish_lease(self.store.claim("r","w"),"no_progress")
        self.assertEqual(self.store.status("r")['tasks'][0]['state'],'blocked')
        with self.assertRaises(ProtocolError): self.store.claim("r","w")
    def test_global_budget_explicit_raise(self):
        self.store.resume("r",budget_attempts=1);self.store.add_task("r","t","prover","x")
        self.finish_lease(self.store.claim("r","w"),"no_progress")
        with self.assertRaises(ProtocolError): self.store.claim("r","w")
        self.store.resume("r",budget_attempts=2);self.store.claim("r","w")
    def test_pause_blocks_finish_and_claim(self):
        self.store.add_task("r","t","prover","x");a=self.store.claim("r","w");self.store.pause("r","review")
        with self.assertRaises(ProtocolError): self.finish_lease(a)
        with self.assertRaises(ProtocolError): self.store.claim("r","w")
    def test_self_report_proved_rejected(self):
        self.store.add_task("r","t","prover","x");a=self.store.claim("r","w")
        with self.assertRaises(ProtocolError): self.finish_lease(a,"proved")
    def test_result_outside_lease_rejected(self):
        self.artifact("outside.txt","x");self.store.add_task("r","t","prover","x");a=self.store.claim("r","w")
        with self.assertRaises(ProtocolError): self.finish_lease(a,artifacts=["outside.txt"])
    def test_stale_task_output_blocks_dependencies(self):
        self.store.add_task("r","a","prover","x");self.store.add_task("r","b","prover","y",["a"])
        a=self.store.claim("r","w");path=a['work_dir']+'/proof.txt';self.artifact(path,"initial");self.finish_lease(a,artifacts=[path]);self.artifact(path,"changed")
        with self.assertRaises(ProtocolError): self.store.claim("r","w","b")
    def test_invalidation_cascades_and_opens_issue(self):
        self.store.add_task("r","a","prover","x");self.store.add_task("r","b","prover","y",["a"])
        self.finish_lease(self.store.claim("r","w","a"));self.store.claim("r","w","b")
        value=self.store.invalidate_task("r","a","invalid intermediate result")
        self.assertEqual(value['cancelled'],['a','b']);self.assertEqual(len(self.store.status("r")['open_issues']),1)
    def test_refuted_outcome_opens_issue(self):
        self.store.add_task("r","t","refuter","x");self.finish_lease(self.store.claim("r","w"),"refuted")
        self.assertEqual(len(self.store.status("r")['open_issues']),1)
    def test_session_binding_is_not_global(self):
        self.store.create_run("r2",RESEARCH); self.assertIsNone(self.store.session_run("unknown"))
        self.store.bind("s1","r"); self.store.bind("s2","r2")
        self.assertEqual(self.store.session_run("s1"),"r");self.assertEqual(self.store.session_run("s2"),"r2")
    def test_checkpoint_excludes_tokens(self):
        self.store.add_task("r","t","prover","x");a=self.store.claim("r","w");cp=self.store.checkpoint("r")
        self.assertNotIn(a['lease_token'],(self.root/cp['path']).read_text(encoding="utf-8"))
    def test_event_corruption_detected(self):
        with self.store.connect() as c: c.execute("UPDATE events SET payload='{}' WHERE seq=1")
        self.assertFalse(self.store.audit_events()['consistent'])
    def test_memory_literal_query(self):
        self.store.issue("r","special 100% evidence")
        self.assertEqual(len(self.store.memory("r","100%")),1)
        self.assertEqual(self.store.memory("r","' OR 1=1 --"),[])

class GateTests(WorkspaceCase):
    def test_gate_cannot_skip(self):
        self.assertFalse(self.store.gate("r","release")['accepted'])
    def test_gate_needs_spec_review(self):
        self.assertFalse(self.store.gate("r","spec")['accepted'])
    def test_spec_review_binds_hash(self):
        self.evidence("spec_review",{"spec_hash":"old","statement_match":True,"assumptions_checked":True,"reviewer":"x","issues":[]})
        self.assertFalse(self.store.gate("r","spec")['accepted'])
    def test_research_gate_does_not_certify_proof(self):
        self.through_verify();snapshot=self.store.status("r")['snapshot']
        self.store.review("r","human-fixture","test only",snapshot,acknowledge=True)
        self.assertTrue(self.store.gate("r","release")['accepted'])
        self.assertEqual(self.store.status("r")['status'],'reviewed_research')
    def test_release_requires_explicit_human_record(self):
        self.through_verify();self.assertFalse(self.store.gate("r","release")['accepted'])
    def test_review_without_ack_rejected(self):
        self.through_verify()
        with self.assertRaises(ProtocolError): self.store.review("r","agent","x",self.store.status("r")['snapshot'],acknowledge=False)
    def test_new_evidence_stales_human_review(self):
        self.through_verify();snap=self.store.status("r")['snapshot'];self.store.review("r","human","x",snap,acknowledge=True)
        self.evidence("note","new finding")
        self.assertFalse(self.store.gate("r","release")['accepted'])
    def test_wrong_snapshot_review_rejected(self):
        self.through_verify()
        with self.assertRaises(ProtocolError): self.store.review("r","human","x","old",acknowledge=True)
    def test_source_artifact_drift_rejected(self):
        self.through_verify();self.artifact("candidate.json","changed")
        self.assertFalse(self.store.gate("r","verify")['accepted'])
    def test_withdraw_preserves_history_and_allows_replacement(self):
        self.through_verify()
        old=next(e for e in self.store.status("r")['evidence'] if e['kind']=='candidate')
        self.artifact("candidate.json","changed");self.store.withdraw("r",old['id'],"superseded");self.evidence("candidate","new",name="candidate2.txt")
        self.assertTrue((self.root/old['object_path']).exists());self.assertTrue(self.store.gate("r","verify")['accepted'])
    def test_object_hash_tamper_rejected(self):
        self.spec_review();path=self.store.status("r")['evidence'][0]['object_path'];self.artifact(path,"corrupt")
        self.assertFalse(self.store.gate("r","spec")['accepted'])
    def test_adverse_evidence_veto_and_explicit_resolution(self):
        self.through_verify();self.evidence("counterexample_candidate","possible issue")
        self.assertFalse(self.store.gate("r","candidate")['accepted'])
        issue=self.store.status("r")['open_issues'][0]['id'];ev=self.evidence("note","candidate violates n natural")['evidence_id'];self.store.resolve("r",issue,ev)
        self.assertTrue(self.store.gate("r","candidate")['accepted'])
    def test_resolution_goes_stale(self):
        self.through_verify();issue=self.store.issue("r","issue")['issue_id'];ev=self.evidence("note","resolution")['evidence_id'];self.store.resolve("r",issue,ev);self.artifact("note.json","changed")
        self.assertFalse(self.store.gate("r","verify")['accepted'])
    def test_imported_lean_receipt_rejected(self):
        self.artifact("fake.json",{"result":"checked_local"})
        with self.assertRaises(ProtocolError):self.store.add_evidence("r","lean_replay","fake.json","mathprove.runner.v9")
    def test_unfinished_task_veto(self):
        self.through_verify();self.store.add_task("r","t","prover","open task")
        self.assertFalse(self.store.gate("r","verify")['accepted'])
    def test_check_does_not_mutate_gate_history(self):
        self.spec_review(); before=self.store.audit_events()['events'];self.store.gate("r","spec",record=False)
        self.assertEqual(self.store.audit_events()['events'],before);self.assertIsNone(self.store.status("r")['last_accepted_stage'])
    def test_gate_rechecks_previous_requirements(self):
        self.through_verify();self.artifact("spec_review.json",{})
        self.assertFalse(self.store.gate("r","verify")['accepted'])

class ValidationTests(WorkspaceCase):
    def test_traversal_rejected(self):
        with self.assertRaises(ProtocolError):safe_path(self.root,"../escape")
    def test_symlink_even_inside_root_rejected(self):
        self.artifact("source","x"); self.symlink_or_skip(self.root/'link', self.root/'source')
        with self.assertRaises(ProtocolError):safe_path(self.root,"link")
    def test_json_duplicate_keys_rejected(self):
        p=self.artifact("bad.json",'{"a":1,"a":2}')
        with self.assertRaises(ProtocolError):strict_json(p)
    def test_json_nan_rejected(self):
        p=self.artifact("bad.json",'{"a":NaN}')
        with self.assertRaises(ProtocolError):strict_json(p)
    def test_dag_cycle_rejected(self):
        plan={"spec_hash":"h","target":"a","nodes":[{"id":"a","statement":"a","depends_on":["b"]},{"id":"b","statement":"b","depends_on":["a"]}],"literature":{"not_needed_reason":"fixture"}}
        self.assertTrue(any("Cyclic" in e for e in validate_plan(plan,"h")))
    def test_malformed_dag_target_rejected_without_crash(self):
        self.assertTrue(validate_plan({"spec_hash":"h","target":[],"nodes":[{"id":"a","statement":"a"}]},"h"))
    def test_unchecked_source_rejected(self):
        self.assertTrue(validate_plan({"spec_hash":"h","target":"a","nodes":[{"id":"a","statement":"a"}],"literature":{"sources":[{"title":"invented","checked":False}]}},"h"))
    def test_lean_type_command_injection_rejected(self):
        for typ in ('True\naxiom bad : False','True; #eval 1','by sorry','True -- comment'):
            with self.subTest(typ=typ),self.assertRaises(ProtocolError):validate_spec({**RESEARCH,"mode":"formal","lean":{"project":"lean","module":"Demo","declaration":"Demo.goal","expected_type":typ}})

class AdditionalInvariantTests(WorkspaceCase):
    def test_refuted_dependency_is_not_ready(self):
        self.store.add_task('r','a','prover','x');self.store.add_task('r','b','prover','y',['a'])
        self.finish_lease(self.store.claim('r','w','a'),'refuted')
        with self.assertRaises(ProtocolError):self.store.claim('r','w','b')
    def test_empty_evidence_rejected(self):
        self.artifact('empty.txt',' \n')
        with self.assertRaises(ProtocolError):self.store.add_evidence('r','candidate','empty.txt')
    def test_task_result_context_cap(self):
        self.store.add_task('r','t','prover','x');a=self.store.claim('r','w');result=self.result(a);result['dump']='x'*70000
        with self.assertRaises(ProtocolError):self.store.finish('r','t','w',a['lease_token'],result)
    def test_checkpoint_is_bounded_and_marks_truncation(self):
        for i in range(130):self.store.add_task('r',f't{i}','prover','x')
        path=self.store.checkpoint('r')['path'];value=json.loads((self.root/path).read_text(encoding="utf-8"))
        self.assertEqual(len(value['tasks']),128);self.assertEqual(value['counts']['tasks'],130);self.assertTrue(value['truncated'])

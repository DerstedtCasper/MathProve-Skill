from pathlib import Path
import json
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skill"))
from runtime_v9.core import Store, digest

RESEARCH = {"mode": "research", "statement": "For every natural number n, n equals itself.", "assumptions": [], "symbols": {"n": "natural number"}}

class WorkspaceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="mathprove test ")
        self.root = Path(self.temp.name)
        self.store = Store(self.root, create=True)
        self.store.create_run("r", RESEARCH)
    def tearDown(self):
        self.temp.cleanup()
    def artifact(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value) if not isinstance(value,str) else value, encoding="utf-8")
        return p
    def symlink_or_skip(self, link, target, *, target_is_directory=False):
        try:
            link.symlink_to(target, target_is_directory=target_is_directory)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                self.skipTest("symlink creation is unavailable for this account")
            raise
    def evidence(self, kind, value, name=None):
        p = self.artifact(name or (kind + ".json"), value)
        return self.store.add_evidence("r", kind, p)
    def spec_review(self):
        return self.evidence("spec_review", {"spec_hash": self.store.status("r")["spec_hash"], "statement_match": True, "assumptions_checked": True, "reviewer": "test-fixture", "issues": []})
    def plan(self):
        return self.evidence("plan", {"spec_hash": self.store.status("r")["spec_hash"], "target": "goal", "nodes": [{"id": "goal", "statement": "Reflexivity", "depends_on": []}], "literature": {"not_needed_reason": "Elementary fixture, no novelty claim"}})
    def refutation(self):
        return self.evidence("refutation", {"spec_hash": self.store.status("r")["spec_hash"], "reviewer": "test-fixture", "tests": [{"hypothesis": "n is natural", "method": "logical inspection", "result": "reflexivity", "evidence": "candidate.json"}], "limitations": ["Protocol fixture, not an independent mathematical review"], "unresolved_counterexamples": []})
    def through_verify(self):
        self.spec_review(); self.plan(); self.evidence("candidate", "Fixture candidate, NOT a formal certificate"); self.refutation(); self.evidence("integration", "Fixture informal integration; no formal claim")
        for stage in ("spec", "plan", "candidate", "refutation", "verify"):
            self.assertTrue(self.store.gate("r", stage)["accepted"])
    def result(self, lease, outcome="candidate", artifacts=None):
        return {"task_id":lease["task_id"], "spec_hash":lease["spec_hash"], "outcome":outcome, "summary":"fixture", "next_action":"review", "artifacts":artifacts or []}
    def finish_lease(self, lease, outcome="candidate", artifacts=None, owner="w"):
        return self.store.finish("r", lease["task_id"], owner, lease["lease_token"], self.result(lease,outcome,artifacts))

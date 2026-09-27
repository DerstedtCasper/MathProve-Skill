"""Run observations against the exact pinned upstream source; no Lean/network calls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from threading import Barrier, Lock
from unittest.mock import patch

EXPECTED = '6f362d40efd0cd2a183f2ceb70889b84d46f7f97'

def load(path):
    raw = path.read_bytes()
    git_sha = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if git_sha != EXPECTED:
        raise ValueError('Refusing to label different source as the reviewed upstream revision')
    spec = importlib.util.spec_from_file_location('upstream_mathprove_v8', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module, git_sha

def observe(path):
    m, git_sha = load(path)
    def high(cid, stage, **kw):
        fields = dict(claim='Test-only claim, never submitted', artifact_paths=['missing.lean'],
                      tool_logs=['missing.log'], lean_passed=True, no_sorry=True,
                      dependency_closure=1, refutation_coverage=1, evidence_coverage=1,
                      maintainability=1, restartability=1, novelty=1)
        fields.update(kw)
        return m.CandidateEvidence(cid, stage, m.AgentRole.AUDITOR, **fields)
    fake = m.select_candidate([high('synthetic',m.Stage.FINAL_AUDIT)]).to_dict()
    mixed = m.select_candidate([high('rejected-final',m.Stage.FINAL_AUDIT,lean_passed=False),
                                high('skeleton',m.Stage.SKELETON,lean_passed=False,no_sorry=False)]).to_dict()
    def node(name, deps):
        return dict(line_id=name, formal_target=name, obligation='test', depends_on=deps)
    cycle = m.validate_line_map([node('A',['B']),node('B',['A'])])
    missing = m.validate_line_map([node('A',['absent'])])
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp); index=root/'index.json'; index.write_text('{"shards": []}')
        barrier, lock = Barrier(2), Lock()
        original_read, original_write = Path.read_text, m.write_json
        def after_read(self,*a,**kw):
            value=original_read(self,*a,**kw)
            if self==index: barrier.wait(timeout=5)
            return value
        def serial_write(target, value):
            with lock: return original_write(target,value)
        with patch.object(Path,'read_text',new=after_read), patch.object(m,'write_json',new=serial_write):
            with ThreadPoolExecutor(max_workers=2) as pool:
                tasks=[pool.submit(m.write_context_shard,root,m.Stage.PROBLEM_LOCK,'note',s,s) for s in ('one','two')]
                for task in tasks: task.result(timeout=10)
        counts=dict(shard_files=len(list((root/'shards').glob('*.md'))),
                    indexed_shards=len(json.loads(index.read_text())['shards']))
    return dict(source_git_blob=git_sha, live_lean_invoked=False,
                fabricated_evidence_selector=fake, mixed_stage_selector=mixed,
                two_node_cycle_validated=cycle, missing_dependency_validated=missing,
                nan_clamped=m.clamp01(float('nan')),
                string_false_termination=m.termination_allowed({'final_audit_approved':'false'}),
                controlled_two_writer_index=counts,
                scope='function-level observations, not an end-to-end final_audit.py bypass')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);a=p.parse_args()
    print(json.dumps(observe(a.source),indent=2,ensure_ascii=False,allow_nan=False))

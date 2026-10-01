"""Research workflow must not be blocked by artifact hashes or repeat approvals."""
import json
from pathlib import Path
from unittest.mock import patch
from helpers import WorkspaceCase


class ResearchWorkflowTests(WorkspaceCase):
    def test_skill_entries_allow_local_execution_without_container_prerequisites(self):
        skill = Path(__file__).resolve().parents[1] / 'skill'
        rules = (
            'Local execution is the default and is allowed.',
            'Do not require Docker, Podman, a virtual machine, or a container sandbox as a prerequisite.',
            'Host permissions remain unchanged.',
        )
        for entry in ('SKILL.md', 'agent.md', 'references/v9/operations.md'):
            with self.subTest(entry=entry):
                text = (skill / entry).read_text(encoding='utf-8')
                for rule in rules:
                    self.assertIn(rule, text)

    def test_editing_a_registered_note_does_not_make_it_stale(self):
        evidence = self.evidence('note', 'first draft')
        self.artifact('note.json', 'improved draft')
        status = self.store.status('r')
        self.assertIsNone(next(item for item in status['evidence'] if item['id'] == evidence['evidence_id'])['stale'])

    def test_task_artifact_iteration_does_not_block_its_dependent(self):
        self.store.add_task('r', 'a', 'prover', 'first lemma')
        self.store.add_task('r', 'b', 'prover', 'next lemma', ['a'])
        lease = self.store.claim('r', 'worker', 'a')
        name = lease['work_dir'] + '/proof.txt'
        self.artifact(name, 'first proof draft')
        self.finish_lease(lease, owner='worker', artifacts=[name])
        self.artifact(name, 'improved proof draft')
        self.assertEqual(self.store.claim('r', 'worker', 'b')['task_id'], 'b')

    def test_research_release_does_not_require_human_snapshot_ack(self):
        self.through_verify()
        self.assertTrue(self.store.gate('r', 'release')['accepted'])

    def test_review_is_a_note_without_an_extra_permission_flag(self):
        self.through_verify()
        snapshot = self.store.status('r')['snapshot']
        self.assertEqual(self.store.review('r', 'reviewer', 'checked mathematical argument', snapshot, acknowledge=False)['reviewed_snapshot'], snapshot)

    def test_state_operations_do_not_compute_file_hashes(self):
        with patch('runtime_v9.core.file_hash', side_effect=AssertionError('File hashing is not a research gate')):
            evidence = self.evidence('note', 'research notes')
            self.assertIsNone(self.store.status('r')['evidence'][0]['stale'])
            self.assertTrue(evidence['evidence_id'])

    def test_new_runs_use_revision_identifiers_instead_of_hashes(self):
        status = self.store.status('r')
        self.assertEqual(status['spec_hash'], 'r:1')
        self.assertEqual(status['spec_revision'], 'r:1')

    def test_event_log_is_not_a_hash_chain(self):
        with self.store.connect() as connection:
            connection.execute("UPDATE events SET payload='{}' WHERE seq=1")
        report = self.store.audit_events()
        self.assertTrue(report['consistent'])
        self.assertFalse(report['hash_verification'])


if __name__ == '__main__':
    import unittest
    unittest.main()

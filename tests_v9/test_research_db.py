"""Portable dependency checks and real, reopen-based TriviumDB conformance."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from helpers import WorkspaceCase, RESEARCH
from runtime_v9.core import ProtocolError
from runtime_v9.cli import execute, parser

BASE = Path(__file__).resolve().parents[1]
CLI = BASE / 'skill/scripts/mathprove.py'
try:
    importlib.import_module('triviumdb')
except (ImportError, OSError, RuntimeError):
    NATIVE_AVAILABLE = False
else:
    NATIVE_AVAILABLE = True


class DependencyTests(WorkspaceCase):
    def adapter(self):
        return importlib.import_module('runtime_v9.research_db')

    def test_dependency_declaration_is_unpinned(self):
        self.assertEqual((BASE / 'skill/requirements-db.txt').read_text(encoding='utf-8'), 'triviumdb\n')

    def test_missing_extension_has_install_instruction_and_cause(self):
        module = self.adapter()
        failure = ModuleNotFoundError('No module named triviumdb')
        with patch.object(module.importlib, 'import_module', side_effect=failure):
            with self.assertRaisesRegex(ProtocolError, 'python -m pip install -r skill/requirements-db.txt') as caught:
                module.ResearchDB(self.root).initialize(3)
        self.assertIs(caught.exception.__cause__, failure)
        self.assertFalse((self.root / '.mathprove/research-db.json').exists())

    def test_doctor_reports_failed_import_without_writing(self):
        module = self.adapter()
        before = sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*'))
        for error in (ImportError('missing'), OSError('DLL load failed'), RuntimeError('native unavailable')):
            with self.subTest(error=type(error).__name__), patch.object(module.importlib, 'import_module', side_effect=error):
                report = execute(parser().parse_args(['--root', str(self.root), 'doctor']))
                self.assertFalse(report['research_database']['dependency']['importable'])
                self.assertIn(str(error), report['research_database']['dependency']['error'])
                self.assertIn('version', report['research_database']['dependency'])
                self.assertIn('state_initialized', report)
        self.assertEqual(before, sorted(p.relative_to(self.root).as_posix() for p in self.root.rglob('*')))

    def test_doctor_uninitialized_root_does_not_create_workspace(self):
        fresh = self.root / 'fresh'
        fresh.mkdir()
        report = execute(parser().parse_args(['--root', str(fresh), 'doctor']))
        self.assertFalse(report['research_database']['initialized'])
        self.assertEqual(list(fresh.iterdir()), [])

    def test_doctor_does_not_open_database(self):
        module = self.adapter()
        self.artifact('.mathprove/research-db.json', {'schema': module.SCHEMA, 'dim': 3})
        self.artifact('.mathprove/research.tdb', 'not a database')
        with patch.object(module.ResearchDB, '_open', side_effect=AssertionError('doctor opened database')):
            report = module.probe(self.root)
        self.assertTrue(report['initialized'])
        self.assertEqual(report['dim'], 3)

    def test_ordinary_commands_do_not_import_extension(self):
        original = importlib.import_module
        def guarded(name, *args, **kwargs):
            if name == 'triviumdb':
                raise AssertionError('ordinary command imported triviumdb')
            return original(name, *args, **kwargs)
        with patch('importlib.import_module', side_effect=guarded):
            result = execute(parser().parse_args(['--root', str(self.root), 'status', 'r']))
        self.assertEqual(result['run_id'], 'r')

    def test_native_open_failure_is_protocol_error(self):
        module = self.adapter()
        self.artifact('.mathprove/research-db.json', {'schema': module.SCHEMA, 'dim': 3})
        self.artifact('.mathprove/research.tdb', 'fixture')
        failure = OSError('unreadable native file')
        with patch.object(module.importlib, 'import_module') as imported:
            imported.return_value.TriviumDB.side_effect = failure
            with self.assertRaisesRegex(ProtocolError, 'unreadable native file') as caught:
                module.ResearchDB(self.root).get('r', 1)
        self.assertIs(caught.exception.__cause__, failure)

    def test_native_operation_and_close_failures_keep_causes(self):
        module = self.adapter()
        self.artifact('.mathprove/research-db.json', {'schema': module.SCHEMA, 'dim': 3})
        self.artifact('.mathprove/research.tdb', 'fixture')
        for method in ('get_payload', 'close'):
            failure = RuntimeError(method + ' failed')
            with self.subTest(method=method), patch.object(module.importlib, 'import_module') as imported:
                native = imported.return_value.TriviumDB.return_value
                native.dim.return_value = 3
                native.get_payload.return_value = {'run_id': 'r', 'spec_revision': 'r:1', 'payload': '{}'}
                native.get_edges.return_value = []
                getattr(native, method).side_effect = failure
                with self.assertRaises(ProtocolError) as caught:
                    module.ResearchDB(self.root).get('r', 1)
                self.assertIs(caught.exception.__cause__, failure)
                native.close.assert_called_once()

    def test_missing_dependency_cli_is_json_exit2(self):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        from runtime_v9.cli import main
        module = self.adapter()
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(module.importlib, 'import_module', side_effect=ModuleNotFoundError('missing triviumdb')), redirect_stdout(stdout), redirect_stderr(stderr):
            code = main(['--root', str(self.root), 'db-init', '--dim', '3'])
        self.assertEqual(code, 2)
        self.assertEqual(stdout.getvalue(), '')
        error = json.loads(stderr.getvalue())
        self.assertEqual(error['error'], 'ProtocolError')
        self.assertIn('python -m pip install -r skill/requirements-db.txt', error['message'])

    def test_initial_root_and_workspace_must_exist(self):
        module = self.adapter()
        with self.assertRaises(ProtocolError):
            module.ResearchDB(self.root / 'missing')
        fresh = self.root / 'fresh'
        fresh.mkdir()
        with self.assertRaises(ProtocolError):
            module.ResearchDB(fresh)
        self.assertEqual(list(fresh.iterdir()), [])

    def test_parser_exposes_database_commands(self):
        cases = [('db-init', '--dim', '3'), ('db-put', 'r', '--record', 'record.json'),
                 ('db-get', 'r', '1'), ('db-query', 'r'), ('db-link', 'r', '1', '2')]
        for args in cases:
            with self.subTest(args=args):
                self.assertEqual(parser().parse_args(args).command, args[0])


@unittest.skipUnless(NATIVE_AVAILABLE, 'triviumdb native extension is not importable')
class NativeResearchDBTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.module = importlib.import_module('runtime_v9.research_db')
        self.db = self.module.ResearchDB(self.root)

    def initialize(self):
        return self.db.initialize(3)

    def put(self, payload=None, run='r'):
        return self.db.put(run, {'vector': [1, 0, 0], 'payload': payload or {'text': 'Lemma Alpha'}})['node_id']

    def invoke(self, *args):
        return subprocess.run([sys.executable, str(CLI), '--root', str(self.root), *args], capture_output=True, text=True, timeout=30)

    def test_initialization_idempotent_and_dimension_immutable(self):
        self.initialize()
        node = self.put()
        self.initialize()
        self.assertEqual(self.db.get('r', node)['payload']['text'], 'Lemma Alpha')
        with self.assertRaisesRegex(ProtocolError, 'dim'):
            self.db.initialize(4)
        config = json.loads((self.root / '.mathprove/research-db.json').read_text(encoding='utf-8'))
        self.assertEqual(config, {'schema': self.module.SCHEMA, 'dim': 3})

    def test_dimension_bounds(self):
        for dim in (0, -1, 65537, True, 3.0):
            with self.subTest(dim=dim), self.assertRaises(ProtocolError):
                self.db.initialize(dim)
        self.assertFalse((self.root / '.mathprove/research.tdb').exists())

    def test_uninitialized_operations_refused(self):
        for operation in (lambda: self.put(), lambda: self.db.get('r', 1), lambda: self.db.query('r'), lambda: self.db.link('r', 1, 2)):
            with self.assertRaises(ProtocolError):
                operation()
        self.assertFalse((self.root / '.mathprove/research.tdb').exists())

    def test_missing_data_is_not_recreated(self):
        self.initialize()
        path = self.root / '.mathprove/research.tdb'
        path.unlink()
        for operation in (self.initialize, lambda: self.put(), lambda: self.db.query('r')):
            with self.assertRaises(ProtocolError):
                operation()
            self.assertFalse(path.exists())

    def test_orphan_data_is_not_adopted(self):
        self.initialize()
        (self.root / '.mathprove/research-db.json').unlink()
        with self.assertRaises(ProtocolError):
            self.initialize()

    def test_invalid_config_refused(self):
        self.initialize()
        for value in ({'schema': 'unknown', 'dim': 3}, {'schema': self.module.SCHEMA, 'dim': True}, [], {'schema': self.module.SCHEMA, 'dim': 0}):
            self.artifact('.mathprove/research-db.json', value)
            with self.subTest(value=value), self.assertRaises(ProtocolError):
                self.db.query('r')
        self.artifact('.mathprove/research-db.json', '{broken')
        with self.assertRaises(ProtocolError):
            self.db.query('r')

    def test_actual_database_dimension_checked(self):
        self.initialize()
        self.artifact('.mathprove/research-db.json', {'schema': self.module.SCHEMA, 'dim': 4})
        with self.assertRaises(ProtocolError):
            self.db.query('r')

    def test_vector_validation(self):
        self.initialize()
        for vector in ([1, 0], [True, 0, 0], [float('nan'), 0, 0], [float('inf'), 0, 0], ['1', 0, 0], (1, 0, 0), [10**1000, 0, 0]):
            with self.subTest(vector=repr(vector)), self.assertRaises(ProtocolError):
                self.db.put('r', {'vector': vector, 'payload': {}})
        self.assertEqual(self.db.query('r'), [])

    def test_payload_and_record_validation(self):
        self.initialize()
        for record in ([], {}, {'vector': [1, 0, 0], 'payload': []}, {'vector': [1, 0, 0], 'payload': {'x': object()}}, {'vector': [1, 0, 0], 'payload': {'nested': [float('nan')]}}, {'vector': [1, 0, 0], 'payload': {'x': float('inf')}}):
            with self.subTest(record=repr(record)), self.assertRaises(ProtocolError):
                self.db.put('r', record)
        self.assertEqual(self.db.query('r'), [])

    def test_arbitrary_precision_payload_integers_survive_native_reopen(self):
        self.initialize()
        numbers = [2**64 + 1, -(2**63) - 1, 10**200 + 123]
        payload = {'numbers': numbers, 'nested': [{'n': numbers[0]}, {'values': numbers}], 'n': numbers[0]}
        node = self.put(payload)
        fetched = self.module.ResearchDB(self.root).get('r', node)
        self.assertEqual(fetched['payload'], payload)
        for value in fetched['payload']['numbers']:
            self.assertIs(type(value), int)
        native = importlib.import_module('triviumdb').TriviumDB(str(self.root / '.mathprove/research.tdb'), dim=3, access_mode='read_only')
        try:
            stored = native.get_payload(node)
            self.assertIsInstance(stored['payload'], str)
            self.assertEqual(json.loads(stored['payload']), payload)
            self.assertEqual(stored['run_id'], 'r')
            self.assertEqual(stored['spec_revision'], self.store.status('r')['spec_revision'])
        finally:
            native.close()

    def test_query_matches_original_text_recursively(self):
        self.initialize()
        self.store.create_run('other', RESEARCH)
        first = self.put({'text': r'a"b\c', 'nested': [{'value': 'Straße "数学"\\路径'}], 'quoted"key': None})
        second = self.put({'nested': [[r'a"b\c']], 'number': 42, 'flag': True, 'empty': []})
        empty = self.put({'empty': {}})
        self.put({'text': r'a"b\c'}, run='other')
        for query in ('a"b', r'b\c'):
            with self.subTest(query=query):
                self.assertEqual([x['node_id'] for x in self.db.query('r', query)], sorted([first, second]))
                self.assertEqual([x['node_id'] for x in self.db.query('r', query, 1)], [first])
        for query in ('STRASSE', '"数学"', r'\路径', 'quoted"key', 'null'):
            with self.subTest(query=query):
                self.assertEqual([x['node_id'] for x in self.db.query('r', query)], [first])
        for query in ('42', 'TRUE'):
            with self.subTest(query=query):
                self.assertEqual([x['node_id'] for x in self.db.query('r', query)], [second])
        self.assertEqual([x['node_id'] for x in self.db.query('r', '')], [first, second, empty])
        self.assertEqual(self.db.query('r', r'a\"b'), [])

    def test_malformed_encoded_payload_is_protocol_error(self):
        self.initialize()
        values = ['{broken', '[]', '{"n":NaN}', '{"n":Infinity}', '{"n":1e999}', '{"n":1,"n":2}', {'n': 1}]
        for value in values:
            with self.subTest(value=value):
                native = importlib.import_module('triviumdb').TriviumDB(str(self.root / '.mathprove/research.tdb'), dim=3)
                try:
                    node = native.insert([1, 0, 0], {'run_id': 'r', 'spec_revision': 'r:1', 'payload': value})
                finally:
                    native.close()
                with self.assertRaises(ProtocolError):
                    self.db.get('r', node)
        with self.assertRaises(ProtocolError):
            self.db.query('r')

    def test_json_serializable_payload_is_stored_as_json(self):
        self.initialize()
        payload = {1: 'Alpha', 'tuple': (1, 2)}
        saved = self.db.put('r', {'vector': [1, 0, 0], 'payload': payload})
        self.assertEqual(self.db.get('r', saved['node_id'])['payload'], json.loads(json.dumps(payload)))
        self.assertEqual(self.db.query('r', 'Alpha')[0]['node_id'], saved['node_id'])

    def test_write_close_reopen_preserves_context_and_real_vector(self):
        self.initialize()
        payload = {'text': 'Lemma', 'run_id': 'other', 'spec_revision': 'spoof'}
        record = {'vector': [1, 2, 3], 'payload': payload, 'run_id': 'other', 'spec_revision': 'spoof'}
        saved = self.db.put('r', record)
        self.assertEqual(saved['run_id'], 'r')
        self.assertEqual(saved['spec_revision'], self.store.status('r')['spec_revision'])
        fetched = self.module.ResearchDB(self.root).get('r', saved['node_id'])
        self.assertEqual(fetched['payload'], payload)
        self.assertEqual(fetched['context'], {'run_id': 'r', 'spec_revision': saved['spec_revision']})
        native = importlib.import_module('triviumdb').TriviumDB(str(self.root / '.mathprove/research.tdb'), dim=3, access_mode='read_only')
        try:
            self.assertEqual(native.get(saved['node_id']).vector, [1, 2, 3])
        finally:
            native.close()

    def test_cross_run_and_missing_nodes_refused(self):
        self.initialize()
        self.store.create_run('other', RESEARCH)
        first = self.put()
        second = self.put(run='other')
        for operation in (lambda: self.db.get('other', first), lambda: self.db.get('r', second), lambda: self.db.get('r', 999999), lambda: self.db.link('r', first, second), lambda: self.db.link('r', first, 999999), lambda: self.db.link('r', 999999, first), lambda: self.put(run='missing')):
            with self.assertRaises(ProtocolError):
                operation()
        self.assertEqual([x['node_id'] for x in self.db.query('r')], [first])

    def test_stable_case_insensitive_literal_query_and_limits(self):
        self.initialize()
        self.store.create_run('other', RESEARCH)
        ids = [self.put({'text': 'Alpha " OR 1=1 --'}), self.put({'text': 'ALPHA'}), self.put({'text': 'Beta'})]
        self.put({'text': 'Alpha'}, run='other')
        self.assertEqual([x['node_id'] for x in self.db.query('r', 'aLpHa')], sorted(ids[:2]))
        self.assertEqual([x['node_id'] for x in self.db.query('r', 'OR 1=1 --')], ids[:1])
        self.assertEqual([x['node_id'] for x in self.db.query('r', '', 1)], ids[:1])
        for limit in (0, 101, True, 1.5):
            with self.subTest(limit=limit), self.assertRaises(ProtocolError):
                self.db.query('r', '', limit)

    def test_relationship_persists_after_reopen(self):
        self.initialize()
        first, second = self.put(), self.put({'text': 'Beta'})
        self.db.link('r', first, second, 'uses')
        fetched = self.module.ResearchDB(self.root).get('r', first)
        self.assertIn({'target_id': second, 'label': 'uses', 'weight': 1.0}, fetched['edges'])
        for label in ('', ' ', 'x' * 201, 'line\nbreak'):
            with self.subTest(label=label), self.assertRaises(ProtocolError):
                self.db.link('r', first, second, label)

    def test_historical_revision_remains_research_not_evidence(self):
        self.initialize()
        node = self.put()
        old_revision = self.store.status('r')['spec_revision']
        self.store.revise('r', {**RESEARCH, 'statement': 'New statement'}, 'change')
        self.assertEqual(self.db.get('r', node)['context']['spec_revision'], old_revision)
        self.assertNotEqual(old_revision, self.store.status('r')['spec_revision'])
        self.assertEqual(self.store.status('r')['evidence'], [])
        self.assertFalse(self.store.gate('r', 'release', record=False)['accepted'])

    def test_doctor_reports_actual_dependency_without_opening(self):
        self.initialize()
        with patch.object(self.module.ResearchDB, '_open', side_effect=AssertionError('opened')):
            report = self.module.probe(self.root)
        self.assertTrue(report['dependency']['importable'])
        self.assertTrue(report['dependency']['available'])
        self.assertTrue(report['dependency']['version'])
        self.assertTrue(report['initialized'])

    def test_native_corrupt_file_error_is_not_success(self):
        self.initialize()
        (self.root / '.mathprove/research.tdb').write_bytes(b'corrupt native data')
        with self.assertRaises(ProtocolError) as caught:
            self.db.query('r')
        self.assertIsNotNone(caught.exception.__cause__)

    def test_cli_database_roundtrip_and_json_exit2(self):
        p = self.invoke('db-init', '--dim', '3')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.artifact('record.json', {'vector': [1, 0, 0], 'payload': {'text': 'CLI Alpha'}})
        p = self.invoke('db-put', 'r', '--record', 'record.json')
        self.assertEqual(p.returncode, 0, p.stderr)
        node = json.loads(p.stdout)['node_id']
        p = self.invoke('db-get', 'r', str(node))
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)['payload']['text'], 'CLI Alpha')
        p = self.invoke('db-query', 'r', '--query', 'alpha')
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)[0]['node_id'], node)
        p = self.invoke('db-link', 'r', str(node), str(node), '--label', 'related')
        self.assertEqual(p.returncode, 0, p.stderr)
        for args in (('db-init', '--dim', '4'), ('db-get', 'r', '999999'), ('db-query', 'r', '--limit', '0'), ('db-put', 'r', '--record', '../outside.json')):
            p = self.invoke(*args)
            self.assertEqual(p.returncode, 2, p.stderr)
            self.assertEqual(p.stdout, '')
            self.assertEqual(json.loads(p.stderr)['error'], 'ProtocolError')
        self.artifact('bad.json', {'vector': [True, 0, 0], 'payload': {}})
        p = self.invoke('db-put', 'r', '--record', 'bad.json')
        self.assertEqual(p.returncode, 2)
        self.assertEqual(json.loads(p.stderr)['error'], 'ProtocolError')

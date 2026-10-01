"""Local TriviumDB research records; SQLite remains the workflow state store."""
from __future__ import annotations

from contextlib import contextmanager
import importlib
from importlib import metadata, util
import json
import math
from numbers import Real
from pathlib import Path

from .core import ProtocolError, Store, atomic_write, json_object, safe_path, strict_json

SCHEMA = 'mathprove.research-db.v9'
CONFIG = '.mathprove/research-db.json'
DATA = '.mathprove/research.tdb'
NATIVE_ERRORS = (OSError, RuntimeError, ValueError, TypeError, OverflowError)
INSTALL = 'python -m pip install -r skill/requirements-db.txt'


def _matches(value, query: str) -> bool:
    if not query:
        return True
    if isinstance(value, str):
        return query in value.casefold()
    if isinstance(value, dict):
        return any(_matches(key, query) or _matches(item, query) for key, item in value.items())
    if isinstance(value, list):
        return any(_matches(item, query) for item in value)
    return query in json.dumps(value, allow_nan=False).casefold()


def _dimension(dim: int) -> int:
    if isinstance(dim, bool) or not isinstance(dim, int) or not 1 <= dim <= 65536:
        raise ProtocolError('Research database dim must be an integer in 1..65536')
    return dim


def _config(root: Path) -> dict:
    try:
        value = strict_json(safe_path(root, CONFIG, exists=True))
    except (OSError, ValueError, TypeError) as exc:
        raise ProtocolError(f'Invalid research database config: {exc}') from exc
    if not isinstance(value, dict) or value.get('schema') != SCHEMA:
        raise ProtocolError('Unsupported research database config schema')
    _dimension(value.get('dim'))
    return value


def _dependency():
    try:
        return importlib.import_module('triviumdb')
    except (ImportError, OSError, RuntimeError) as exc:
        raise ProtocolError(f'TriviumDB dependency is not importable: {exc}; install locally with {INSTALL}') from exc


def probe(root: str | Path) -> dict:
    """Inspect dependency and config only; never create state or open native data."""
    root = Path(root).expanduser().resolve()
    dependency = {'available': False, 'importable': False, 'version': None, 'error': None}
    try:
        dependency['available'] = util.find_spec('triviumdb') is not None
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        dependency['error'] = str(exc)
    try:
        dependency['version'] = metadata.version('triviumdb')
    except metadata.PackageNotFoundError:
        pass
    try:
        _dependency()
    except ProtocolError as exc:
        dependency['error'] = str(exc)
    else:
        dependency['available'] = True
        dependency['importable'] = True
        dependency['error'] = None
    result = {'dependency': dependency, 'config_exists': False, 'data_exists': False,
              'initialized': False, 'dim': None, 'error': None}
    try:
        result['config_exists'] = safe_path(root, CONFIG).is_file()
        result['data_exists'] = safe_path(root, DATA).is_file()
        if result['config_exists']:
            result['dim'] = _config(root)['dim']
        result['initialized'] = result['config_exists'] and result['data_exists'] and result['dim'] is not None
    except (ProtocolError, OSError) as exc:
        result['error'] = str(exc)
    return result


class ResearchDB:
    def __init__(self, root: str | Path):
        self.store = Store(root)
        self.root = self.store.root
        self.config = safe_path(self.root, CONFIG)
        self.path = safe_path(self.root, DATA)

    def _settings(self) -> dict:
        config = safe_path(self.root, CONFIG)
        if not config.is_file():
            raise ProtocolError('Research database not initialized; run db-init --dim N first')
        value = _config(self.root)
        if not safe_path(self.root, DATA).is_file():
            raise ProtocolError('Research database data path is missing; refusing implicit rebuild')
        return value

    @contextmanager
    def _open(self, dim: int, *, write: bool = False):
        module = _dependency()
        db = None
        try:
            db = module.TriviumDB(str(safe_path(self.root, DATA, exists=True)), dim=dim,
                                  access_mode='read_write' if write else 'read_only',
                                  auto_build_quiver=write)
            if db.dim() != dim:
                raise ProtocolError('Research database dim does not match config')
            yield db
        except NATIVE_ERRORS as exc:
            raise ProtocolError(f'TriviumDB operation failed: {exc}') from exc
        finally:
            if db is not None:
                try:
                    db.close()
                except NATIVE_ERRORS as exc:
                    raise ProtocolError(f'TriviumDB close failed: {exc}') from exc

    def initialize(self, dim: int) -> dict:
        dim = _dimension(dim)
        config = safe_path(self.root, CONFIG)
        path = safe_path(self.root, DATA)
        if config.exists():
            settings = self._settings()
            if settings['dim'] != dim:
                raise ProtocolError('Research database dim cannot change after initialization')
            with self._open(dim):
                pass
        else:
            if path.exists():
                raise ProtocolError('Research database data exists without config; refusing overwrite')
            module = _dependency()
            db = None
            try:
                db = module.TriviumDB(str(path), dim=dim)
                if db.dim() != dim:
                    raise ProtocolError('Research database dim does not match requested dim')
            except NATIVE_ERRORS as exc:
                raise ProtocolError(f'TriviumDB initialization failed: {exc}') from exc
            finally:
                if db is not None:
                    try:
                        db.close()
                    except NATIVE_ERRORS as exc:
                        raise ProtocolError(f'TriviumDB close failed: {exc}') from exc
            try:
                atomic_write(config, json.dumps({'schema': SCHEMA, 'dim': dim}) + '\n')
            except OSError as exc:
                raise ProtocolError(f'Research database config write failed: {exc}') from exc
        return {'schema': SCHEMA, 'dim': dim, 'path': DATA, 'initialized': True}

    def _record(self, record: dict, dim: int) -> tuple[list[float], dict]:
        if not isinstance(record, dict):
            raise ProtocolError('Research record must be an object with vector and payload')
        vector = record.get('vector')
        if not isinstance(vector, list) or len(vector) != dim:
            raise ProtocolError('Research vector must be a list of length dim')
        try:
            if any(isinstance(x, bool) or not isinstance(x, Real) or not math.isfinite(x) for x in vector):
                raise ProtocolError('Research vector elements must be finite non-bool real numbers')
            vector = [float(x) for x in vector]
        except (OverflowError, ValueError, TypeError) as exc:
            raise ProtocolError(f'Invalid research vector: {exc}') from exc
        payload = record.get('payload')
        if not isinstance(payload, dict):
            raise ProtocolError('Research payload must be an object')
        try:
            # Native conversion is not JSON serialization (e.g. tuples become null).
            payload = json.loads(json.dumps(payload, allow_nan=False))
        except (ValueError, TypeError, OverflowError, RecursionError) as exc:
            raise ProtocolError(f'Research payload must be finite JSON: {exc}') from exc
        return vector, payload

    def put(self, run: str, record: dict) -> dict:
        settings = self._settings()
        revision = self.store.status(run)['spec_revision']
        vector, payload = self._record(record, settings['dim'])
        # Keep arbitrary-precision numbers out of native JSON numeric conversion.
        stored = {'run_id': run, 'spec_revision': revision,
                  'payload': json.dumps(payload, ensure_ascii=False, allow_nan=False)}
        with self._open(settings['dim'], write=True) as db:
            node_id = db.insert(vector, stored)
        return {'node_id': node_id, 'run_id': run, 'spec_revision': revision}

    def _node(self, db, run: str, node_id: int) -> dict:
        if isinstance(node_id, bool) or not isinstance(node_id, int) or node_id < 0:
            raise ProtocolError('Research node_id must be a nonnegative integer')
        stored = db.get_payload(node_id)
        if stored is None:
            raise ProtocolError('Unknown research node')
        if not isinstance(stored, dict) or stored.get('run_id') != run:
            raise ProtocolError('Research node does not belong to this run')
        if not isinstance(stored.get('payload'), str) or not isinstance(stored.get('spec_revision'), str):
            raise ProtocolError('Malformed research node context or payload')
        try:
            payload = json.loads(stored['payload'], object_pairs_hook=json_object,
                                 parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f'Invalid JSON {value}')))
            json.dumps(payload, allow_nan=False)
        except (ValueError, TypeError, OverflowError, RecursionError) as exc:
            raise ProtocolError(f'Malformed research node JSON payload: {exc}') from exc
        if not isinstance(payload, dict):
            raise ProtocolError('Research node JSON payload must be an object')
        return {'node_id': node_id, 'context': {'run_id': run, 'spec_revision': stored['spec_revision']},
                'payload': payload}

    def get(self, run: str, node_id: int) -> dict:
        settings = self._settings()
        self.store.status(run)
        with self._open(settings['dim']) as db:
            result = self._node(db, run, node_id)
            result['edges'] = [{'target_id': edge.target_id, 'label': edge.label, 'weight': edge.weight}
                               for edge in db.get_edges(node_id)]
        return result

    def query(self, run: str, query: str = '', limit: int = 20) -> list[dict]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ProtocolError('Research query limit must be an integer in 1..100')
        if not isinstance(query, str):
            raise ProtocolError('Research query must be literal text')
        settings = self._settings()
        self.store.status(run)
        results = []
        with self._open(settings['dim']) as db:
            for node_id in sorted(db.all_node_ids()):
                stored = db.get_payload(node_id)
                if not isinstance(stored, dict) or stored.get('run_id') != run:
                    continue
                result = self._node(db, run, node_id)
                if _matches(result['payload'], query.casefold()):
                    results.append(result)
                    if len(results) == limit:
                        break
        return results

    def link(self, run: str, source_id: int, target_id: int, label: str = 'related') -> dict:
        if not isinstance(label, str) or not label.strip() or len(label) > 200 or any(not ch.isprintable() for ch in label):
            raise ProtocolError('Research link label must be nonempty printable text of at most 200 characters')
        settings = self._settings()
        self.store.status(run)
        with self._open(settings['dim'], write=True) as db:
            self._node(db, run, source_id)
            self._node(db, run, target_id)
            db.link(source_id, target_id, label=label, weight=1.0)
        return {'run_id': run, 'source_id': source_id, 'target_id': target_id, 'label': label}

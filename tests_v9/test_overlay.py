import importlib.util
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
from helpers import WorkspaceCase
from runtime_v9.core import ProtocolError

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('overlay',BASE/'scripts/apply_v9_overlay.py')
overlay=importlib.util.module_from_spec(spec);spec.loader.exec_module(overlay)

class OverlayTests(WorkspaceCase):
    def setUp(self):
        super().setUp()
        self.git_patch=patch.object(overlay.shutil,'which',return_value=None)
        self.git_patch.start();self.addCleanup(self.git_patch.stop)
    def fixture(self):
        source=self.root/'new';source.mkdir();(source/'README.md').write_text('new README');(source/'new.py').write_text('new code')
        target=self.root/'old';target.mkdir();(target/'README.md').write_text('original README');(target/'legacy.py').write_text('untouched legacy')
        manifest={'schema':'mathprove.overlay.v9','files':{name:'obsolete legacy hash' for name in ('README.md','new.py')}}
        (source/'RELEASE-MANIFEST.json').write_text(json.dumps(manifest))
        return source,target
    def test_default_dry_run_leaves_original_unchanged(self):
        source,target=self.fixture();overlay.apply_overlay(source,target)
        self.assertEqual((target/'README.md').read_text(),'original README');self.assertFalse((target/'new.py').exists())
    def test_apply_preserves_unobserved_legacy_and_backup(self):
        source,target=self.fixture();result=overlay.apply_overlay(source,target,apply=True)
        self.assertEqual((target/'legacy.py').read_text(),'untouched legacy');self.assertEqual((target/'README.md').read_text(),'new README')
        self.assertEqual((Path(result['backup'])/'README.md').read_text(),'original README')
    def test_legacy_manifest_hash_is_ignored(self):
        source,target=self.fixture();(source/'new.py').write_bytes(b'current source\x00\xff')
        overlay.apply_overlay(source,target,apply=True)
        self.assertEqual((target/'new.py').read_bytes(),b'current source\x00\xff')
    def test_hashless_file_list_supported(self):
        source,target=self.fixture()
        (source/'RELEASE-MANIFEST.json').write_text(json.dumps({'schema':'mathprove.overlay.v9','files':['README.md','new.py']}))
        overlay.apply_overlay(source,target,apply=True)
        self.assertEqual((target/'new.py').read_text(),'new code')
    def test_identical_bytes_skip_copy_even_with_stale_hash(self):
        source,target=self.fixture();(target/'README.md').write_bytes((source/'README.md').read_bytes())
        result=overlay.apply_overlay(source,target,apply=True)
        self.assertNotIn('README.md',result['files']);self.assertIsNone(result['backup'])
    def test_missing_source_rejected_before_writes(self):
        source,target=self.fixture();(source/'new.py').unlink()
        with self.assertRaises(ProtocolError):overlay.apply_overlay(source,target,apply=True)
        self.assertEqual((target/'README.md').read_text(),'original README')
    def test_destination_directory_rejected_before_writes(self):
        source,target=self.fixture();(target/'new.py').mkdir()
        with self.assertRaises(ProtocolError):overlay.apply_overlay(source,target,apply=True)
        self.assertEqual((target/'README.md').read_text(),'original README')
    def test_invalid_file_list_entries_rejected(self):
        source,target=self.fixture()
        for files in ('new.py',[None],[42],['']):
            with self.subTest(files=files):
                (source/'RELEASE-MANIFEST.json').write_text(json.dumps({'schema':'mathprove.overlay.v9','files':files}))
                with self.assertRaises(ProtocolError):overlay.apply_overlay(source,target,apply=True)
        self.assertEqual((target/'README.md').read_text(),'original README')
    def test_empty_overlay_still_copies_manifest_only_once(self):
        source,target=self.fixture()
        (source/'RELEASE-MANIFEST.json').write_text(json.dumps({'schema':'mathprove.overlay.v9','files':[]}))
        result=overlay.apply_overlay(source,target,apply=True)
        self.assertEqual(result['files'],['RELEASE-MANIFEST.json'])
        with patch.object(overlay,'atomic_write',side_effect=AssertionError('unexpected write')):
            result=overlay.apply_overlay(source,target,apply=True)
        self.assertEqual(result['files'],[]);self.assertIsNone(result['backup'])
    def test_duplicate_list_paths_backup_original_only_once(self):
        source,target=self.fixture()
        (source/'RELEASE-MANIFEST.json').write_text(json.dumps({'schema':'mathprove.overlay.v9','files':['README.md','README.md']}))
        result=overlay.apply_overlay(source,target,apply=True)
        self.assertEqual(result['files'].count('README.md'),1)
        self.assertEqual((Path(result['backup'])/'README.md').read_text(),'original README')
    def test_no_changes_does_not_inspect_unrelated_git_state(self):
        source,target=self.fixture();overlay.apply_overlay(source,target,apply=True)
        with patch.object(overlay.shutil,'which',return_value='git'),patch.object(overlay.subprocess,'run',side_effect=AssertionError('no planned writes')):
            result=overlay.apply_overlay(source,target,apply=True)
        self.assertEqual(result['files'],[]);self.assertIsNone(result['backup'])
    def test_destination_symlink_rejected(self):
        source,target=self.fixture();self.symlink_or_skip(target/'new.py', target/'legacy.py')
        with self.assertRaises(ProtocolError):overlay.apply_overlay(source,target,apply=True)
    def test_manifest_traversal_rejected(self):
        source,target=self.fixture();(source/'RELEASE-MANIFEST.json').write_text(json.dumps({'schema':'mathprove.overlay.v9','files':{'../escape':'bad'}}))
        with self.assertRaises(ProtocolError):overlay.apply_overlay(source,target,apply=True)
    def test_failed_copy_rolls_back_already_written_files(self):
        source,target=self.fixture();real=overlay.atomic_write
        def fail(path,data):
            if path==target/'new.py':raise OSError('injected write failure')
            return real(path,data)
        with patch.object(overlay,'atomic_write',side_effect=fail),self.assertRaises(OSError):overlay.apply_overlay(source,target,apply=True)
        self.assertEqual((target/'README.md').read_text(),'original README')

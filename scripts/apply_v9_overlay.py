#!/usr/bin/env python3
"""Apply only manifest-listed files. No upstream deletion or legacy-state migration."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
import sys
import uuid
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skill"))
from runtime_v9.core import ProtocolError, atomic_write, file_hash, safe_path, strict_json


def apply_overlay(source: Path, target: Path, *, apply: bool = False) -> dict:
    source=source.resolve();target=target.resolve()
    if source==target:raise ProtocolError("Do not apply the overlay onto itself")
    if not target.is_dir():raise ProtocolError("Target repository must be an existing directory")
    manifest=strict_json(source/'RELEASE-MANIFEST.json')
    if manifest.get('schema')!='mathprove.overlay.v9' or not isinstance(manifest.get('files'),dict):raise ProtocolError("Invalid release manifest")
    operations=[]
    # Pinned upstream edits are not ordinary generated files. Refuse a divergent
    # target before any write rather than covering up a user/local modification.
    for rel, allowed in manifest.get('upstream_file_preconditions', {}).items():
        dst = safe_path(target, rel)
        if not isinstance(allowed, list) or not all(isinstance(h, str) and len(h) == 40 for h in allowed):
            raise ProtocolError("Invalid upstream precondition: " + rel)
        if not dst.is_file():
            raise ProtocolError("Missing pinned upstream file: " + rel)
        data = dst.read_bytes()
        current = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
        desired = manifest['files'].get(rel)
        if current not in allowed and (desired is None or file_hash(dst) != desired):
            raise ProtocolError("Pinned upstream file differs; preserve your changes and merge the supplied patch manually: " + rel)
    # Validate every supplied byte and destination BEFORE touching the target.
    for rel, expected in manifest['files'].items():
        src=safe_path(source,rel,exists=True);dst=safe_path(target,rel)
        if not src.is_file() or file_hash(src)!=expected:raise ProtocolError("Overlay file hash mismatch: "+rel)
        if dst.exists() and not dst.is_file():raise ProtocolError("Destination is not a file: "+rel)
        if not dst.exists() or file_hash(dst)!=expected:operations.append((rel,src,dst))
    # Copy manifest too, while preserving its previous version for rollback.
    manifest_dst=safe_path(target,'RELEASE-MANIFEST.json')
    if manifest_dst.exists() and not manifest_dst.is_file():raise ProtocolError("Manifest destination is not a file")
    operations.append(('RELEASE-MANIFEST.json',source/'RELEASE-MANIFEST.json',manifest_dst))
    result={"apply":apply,"target":str(target),"files":[x[0] for x in operations],"deletions":[],
            "legacy_state_migrated":False,"upstream_full_source_audited":False,
            "warning":"Review git diff before committing. Do not commit backups, state or lease-token files."}
    git = shutil.which("git")
    result["git_dirty_check"] = "git_unavailable" if git is None else "not_a_git_repository"
    if git:
        check = subprocess.run([git, "-C", str(target), "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        if check.returncode == 0:
            status = subprocess.run([git, "-C", str(target), "status", "--porcelain=v1", "--untracked-files=all", "--"] +
                                    [rel for rel, _, _ in operations], capture_output=True, text=True, timeout=10)
            if status.returncode != 0:
                raise ProtocolError("Could not inspect local Git changes; no files were written")
            if status.stdout.strip():
                raise ProtocolError("Some overlay destinations have local staged, unstaged, or untracked changes. Preserve/review them and merge manually; no files were written")
            result["git_dirty_check"] = "planned_destinations_clean"
    if not apply:return result
    backup=safe_path(target,'.mathprove-v9-overlay-backups/'+uuid.uuid4().hex)
    changed=[]
    try:
        for rel,src,dst in operations:
            old=dst.read_bytes() if dst.is_file() else None
            if old is not None:atomic_write(safe_path(target,backup/rel),old)
            atomic_write(dst,src.read_bytes());changed.append((dst,old))
    except BaseException:
        for dst,old in reversed(changed):
            if old is None:dst.unlink(missing_ok=True)
            else:atomic_write(dst,old)
        raise
    result['backup']=str(backup) if backup.exists() else None
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--target',required=True)
    flags=p.add_mutually_exclusive_group();flags.add_argument('--apply',action='store_true');flags.add_argument('--dry-run',action='store_true')
    a=p.parse_args()
    try:
        print(json.dumps(apply_overlay(Path(__file__).resolve().parents[1],Path(a.target),apply=a.apply),ensure_ascii=False,indent=2));return 0
    except (ProtocolError,OSError,ValueError,subprocess.SubprocessError) as e:
        print(json.dumps({'error':str(e)},ensure_ascii=False),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())

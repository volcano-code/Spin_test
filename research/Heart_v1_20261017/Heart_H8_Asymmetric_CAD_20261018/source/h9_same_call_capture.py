"""W3: preserve a REAL Cherchi same-call material packet before costly audits.

An `unverified-*` archive is a forensic checkpoint, NEVER a qualified sample.
Only the producer, *after* strict native geometry/moment/branch checks, may
promote it to `side-*`. The independent four-packet audit intentionally ignores
all `unverified-*` files. No surrogate/backend fallback is implemented.
"""
from __future__ import annotations

import gzip
import fcntl
from contextlib import contextmanager
from hashlib import sha256
import json
import os
import stat
from pathlib import Path
import tempfile

SIDES = ('left-coarse', 'left-near', 'right-near', 'right-coarse')
BACKEND = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'


class CaptureRejected(ValueError):
    pass


def need(value, reason):
    if not value:
        raise CaptureRejected(reason)


def digest(path):
    h = sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def key(index, side):
    need(type(index) is int and 0 <= index < len(SIDES) and side == SIDES[index],
         'WRONG_NATIVE_SIDE_CAPTURE_IDENTITY')
    return f'{index:02d}-{side}'


def _atomic_write_json(path, document):
    """Publish a complete JSON as a new durable name; never replace evidence.

    A preflight exists() check cannot protect against a concurrent writer. The
    hard-link itself provides POSIX O_EXCL-like new-name semantics. Its target
    must be an ordinary temporary file in the same filesystem.
    """
    path = Path(path)
    if os.path.lexists(path):
        raise FileExistsError('CAPTURE_METADATA_ALREADY_EXISTS_DO_NOT_OVERWRITE')
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf8', dir=path.parent,
                                         prefix='.' + path.name + '.', suffix='.tmp',
                                         delete=False) as stream:
            temp = Path(stream.name)
            json.dump(document, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        linked = False
        try:
            os.link(temp, path)
            linked = True
            _sync_directory(path.parent)
        except OSError:
            # Only unlink a destination created by THIS writer. If another
            # producer won the name race, its file must remain untouched.
            if linked:
                path.unlink(missing_ok=True)
                try:
                    _sync_directory(path.parent)
                except OSError:
                    pass
            raise
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def capture_same_call(output, *, index, side, coefficients, material, backend_identity):
    """Archive engine.validate_same_call_material(...) output BEFORE native audit.

    This does NOT attest to real execution: caller must independently guarantee
    the engine was invoked. Merely supplying a fixture never certifies a run.
    """
    path = Path(output)
    need(path.is_dir(), 'CAPTURE_OUTPUT_DIRECTORY_MISSING')
    identity = key(index, side)
    need(type(coefficients) is list and len(coefficients) == 10
         and type(material) is dict and material.get('quadric_coefficients') == coefficients,
         'NEW_NATIVE_CAPTURE_QUADRIC_IDENTITY_MISMATCH')
    need(isinstance(backend_identity, str) and backend_identity.startswith(BACKEND)
         and material.get('boolean_backend_identity') == backend_identity
         and material.get('material_proof', {}).get('schema') == 'cherchi-same-call-material-v1',
         'NEW_NATIVE_CAPTURE_PROVENANCE_UNVERIFIED')
    raw_path = path / f'unverified-{identity}.json.gz'
    manifest_path = path / f'unverified-{identity}.json'
    final_path = path / f'side-{identity}.json.gz'
    final_meta = path / f'side-{identity}.json'
    need(not any(os.path.lexists(x) for x in (raw_path, manifest_path, final_path, final_meta)),
         'NATIVE_MATERIAL_CAPTURE_ALREADY_EXISTS_DO_NOT_OVERWRITE')
    # Serialize before opening a checkpoint file so failed JSON serialization
    # cannot leave an invalid material with a valid-looking capture manifest.
    payload = json.dumps(material, sort_keys=True, separators=(',', ':'),
                         ensure_ascii=False, allow_nan=False).encode('utf8')
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=path, prefix='.capture-',
                                         suffix='.tmp', delete=False) as stream:
            temp = Path(stream.name)
            with gzip.GzipFile(fileobj=stream, mode='wb', filename='', mtime=0,
                               compresslevel=5) as gzip_stream:
                gzip_stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        # A parallel producer cannot overwrite a packet after our precheck.
        # If a power loss occurs after this exclusive link but before the
        # manifest, only an UNVERIFIED orphan remains, never a qualified side.
        os.link(temp, raw_path)
        _sync_directory(path)
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
    proof = {'schema': 'heart-h9-unverified-same-call-checkpoint-v1',
             'index': index, 'side': side, 'coefficients': coefficients,
             'backend_identity': backend_identity,
             'status': 'UNVERIFIED_PACKET_PRESERVED_BEFORE_EXACT_BOUNDARY_AUDIT',
             'archive_sha256': digest(raw_path), 'material_json_sha256': sha256(payload).hexdigest(),
             'strict_native_boundary_certified': False,
             'independent_fraction_moments_certified': False,
             'newton_admitted': False, 'final_heart_obj_produced': False}
    _atomic_write_json(manifest_path, proof)
    return proof


def _sync_directory(folder):
    """Persist directory-entry transitions on the Linux W3 native runner."""
    fd = os.open(folder, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def _exclusive_promotion_lease(output, identity):
    """Serialize all promotions for one side across Linux processes.

    Never unlink the lease file: unlink/recreate permits two simultaneous
    locks on different inodes. flock is automatically released on crash.
    Using O_NOFOLLOW and inode checks prevents accepting a renamed lock path.
    """
    folder = Path(output)
    lock = folder / f'.h9-promotion-{identity}.lock'
    flags = os.O_RDWR | os.O_CREAT | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(lock, flags, 0o600)
    acquired = False
    try:
        stat_fd = os.fstat(descriptor)
        stat_path = os.lstat(lock)
        need(stat.S_ISREG(stat_fd.st_mode)
             and stat_fd.st_ino == stat_path.st_ino
             and stat_fd.st_dev == stat_path.st_dev
             and stat_fd.st_uid == os.getuid(),
             'UNTRUSTED_OR_REPLACED_H9_PROMOTION_LEASE')
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        acquired = True
        stat_again = os.lstat(lock)
        need(stat.S_ISREG(stat_again.st_mode)
             and stat_again.st_ino == stat_fd.st_ino
             and stat_again.st_dev == stat_fd.st_dev,
             'H9_PROMOTION_LEASE_NAME_REPLACED_WHILE_WAITING')
        yield
    finally:
        if acquired:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def promote_after_full_audit(output, capture, side_metadata):
    """One-owner durable publication; crash-safe recovery still supported."""
    need(type(capture) is dict and capture.get('schema') ==
         'heart-h9-unverified-same-call-checkpoint-v1', 'INVALID_CAPTURE_MANIFEST')
    identity = key(capture.get('index'), capture.get('side'))
    with _exclusive_promotion_lease(output, identity):
        return _promote_after_full_audit_locked(output, capture, side_metadata)


def _promote_after_full_audit_locked(output, capture, side_metadata):
    """Commit a verified packet without ever moving away its last forensic copy.

    A verified `side-*.json.gz` without its `side-*.json` is NOT a qualified
    packet. Keep the unverified gzip + manifest in place until the complete
    pair is durable. Use a hard link, not os.replace(pending, final), so an
    interrupted side metadata write cannot destroy the capture checkpoint.
    All paths live in the same W3 output directory/filesystem.
    """
    path = Path(output)
    need(type(capture) is dict and capture.get('schema') ==
         'heart-h9-unverified-same-call-checkpoint-v1', 'INVALID_CAPTURE_MANIFEST')
    index, side = capture.get('index'), capture.get('side')
    identity = key(index, side)
    pending = path / f'unverified-{identity}.json.gz'
    manifest_path = path / f'unverified-{identity}.json'
    final = path / f'side-{identity}.json.gz'
    final_metadata = path / f'side-{identity}.json'
    need(not os.path.lexists(final_metadata), 'VALIDATED_NATIVE_PACKET_ALREADY_PRESENT')
    need(manifest_path.is_file() and pending.is_file(), 'UNVERIFIED_SAME_CALL_PACKET_NOT_FOUND')
    # is_file() follows a symlink. Only plain capture files owned by this W3
    # output directory may be upgraded to a production side.
    need(stat.S_ISREG(os.lstat(manifest_path).st_mode)
         and stat.S_ISREG(os.lstat(pending).st_mode),
         'SAME_CALL_CAPTURE_SYMLINK_OR_NONREGULAR_FILE')
    need(json.loads(manifest_path.read_text(encoding='utf8')) == capture
         and digest(pending) == capture['archive_sha256'],
         'CAPTURE_MANIFEST_OR_ARCHIVE_SHA_DRIFT')
    need(type(side_metadata) is dict and side_metadata.get('index') == index
         and side_metadata.get('side') == side
         and side_metadata.get('q') == capture['coefficients']
         and side_metadata.get('material_sha256') == capture['archive_sha256']
         and side_metadata.get('native_geometry_valid') is True,
         'UNVALIDATED_OR_MISMATCHED_NATIVE_SIDE_METADATA')
    # If an earlier process crashed after the hard link but before metadata,
    # only an inode-identical *regular-file* orphan may be removed for retry.
    # A foreign file/symlink, even with identical contents, is never replaced.
    if final.exists() or final.is_symlink():
        source_st, orphan_st = os.stat(pending), os.lstat(final)
        need(stat.S_ISREG(orphan_st.st_mode)
             and source_st.st_dev == orphan_st.st_dev
             and source_st.st_ino == orphan_st.st_ino,
             'FOREIGN_ORPHAN_NATIVE_SIDE_PACKET_DO_NOT_OVERWRITE')
        final.unlink()
        _sync_directory(path)
    # Do not consume the only unverified forensic copy before metadata is
    # written and fsync'ed. Both links initially reference identical gzip bytes.
    # os.link is atomic and fails rather than overwriting an existing side.
    linked = False
    metadata_committed = False
    try:
        os.link(pending, final)
        linked = True
        # The file is hard-linked, but content can still change if an outside
        # writer mutated the source inode between precheck and publication.
        # Recheck the actual final bytes before publishing its metadata.
        need(digest(final) == capture['archive_sha256'],
             'PROMOTED_NATIVE_GZIP_BYTES_CHANGED_BEFORE_METADATA')
        _atomic_write_json(final_metadata, side_metadata)
        metadata_committed = True
        _sync_directory(path)
    except (OSError, ValueError, TypeError):
        # Never remove another writer's metadata if exclusive publication
        # lost a name race. _atomic_write_json cleans up its own failed link.
        # A successfully published metadata name is ours to roll back.
        if metadata_committed:
            final_metadata.unlink(missing_ok=True)
        if linked:
            final.unlink(missing_ok=True)
        raise
    # After the durable pair exists, forensic cleanup is best-effort only.
    # A cleanup failure must NOT remove or invalidate the completed evidence.
    cleanup_errors = []
    for stale in (manifest_path, pending):
        try:
            stale.unlink()
        except OSError as exc:
            cleanup_errors.append(f'{stale.name}:{type(exc).__name__}')
    try:
        _sync_directory(path)
    except OSError as exc:
        # The completed pair was durably linked and fsync'ed above. An error
        # syncing *optional forensic cleanup* must not relabel it as absent.
        cleanup_errors.append(f'directory_sync:{type(exc).__name__}')
    return {'side': side, 'material_sha256': capture['archive_sha256'],
            'archive': str(final), 'complete_material_metadata': str(final_metadata),
            'forensic_cleanup_incomplete': bool(cleanup_errors),
            'forensic_cleanup_errors': cleanup_errors,
            'newton_admitted': False}

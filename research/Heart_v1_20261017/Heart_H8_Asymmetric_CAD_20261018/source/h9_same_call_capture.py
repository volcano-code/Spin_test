"""W3: preserve a REAL Cherchi same-call material packet before costly audits.

An `unverified-*` archive is a forensic checkpoint, NEVER a qualified sample.
Only the producer, *after* strict native geometry/moment/branch checks, may
promote it to `side-*`. The independent four-packet audit intentionally ignores
all `unverified-*` files. No surrogate/backend fallback is implemented.
"""
from __future__ import annotations

import gzip
from hashlib import sha256
import json
import os
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
    path = Path(path)
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
        os.replace(temp, path)
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
    need(not any(x.exists() for x in (raw_path, manifest_path, final_path, final_meta)),
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
        os.replace(temp, raw_path)
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


def promote_after_full_audit(output, capture, side_metadata):
    """Finalize only a complete producer audit; incomplete captures stay distinct."""
    path = Path(output)
    need(type(capture) is dict and capture.get('schema') ==
         'heart-h9-unverified-same-call-checkpoint-v1', 'INVALID_CAPTURE_MANIFEST')
    index, side = capture.get('index'), capture.get('side')
    identity = key(index, side)
    pending = path / f'unverified-{identity}.json.gz'
    manifest_path = path / f'unverified-{identity}.json'
    final = path / f'side-{identity}.json.gz'
    final_metadata = path / f'side-{identity}.json'
    need(not final.exists() and not final_metadata.exists(), 'VALIDATED_NATIVE_PACKET_ALREADY_PRESENT')
    need(manifest_path.is_file() and pending.is_file(), 'UNVERIFIED_SAME_CALL_PACKET_NOT_FOUND')
    need(json.loads(manifest_path.read_text(encoding='utf8')) == capture
         and digest(pending) == capture['archive_sha256'],
         'CAPTURE_MANIFEST_OR_ARCHIVE_SHA_DRIFT')
    need(type(side_metadata) is dict and side_metadata.get('index') == index
         and side_metadata.get('side') == side
         and side_metadata.get('q') == capture['coefficients']
         and side_metadata.get('material_sha256') == capture['archive_sha256']
         and side_metadata.get('native_geometry_valid') is True,
         'UNVALIDATED_OR_MISMATCHED_NATIVE_SIDE_METADATA')
    # Preserve the same compressed bytes, rather than reserializing the same-call
    # packet *after* the original engine/material objects may have been mutated.
    os.replace(pending, final)
    _atomic_write_json(final_metadata, side_metadata)
    manifest_path.unlink()
    return {'side': side, 'material_sha256': capture['archive_sha256'],
            'archive': str(final), 'complete_material_metadata': str(final_metadata),
            'newton_admitted': False}

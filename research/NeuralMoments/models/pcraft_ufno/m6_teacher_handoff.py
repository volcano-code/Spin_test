"""Read-only W0/W2 readiness audit; NO native label is admitted by this file.

W0 MomentContractV1 structural validity is not an independent exact Cherchi
material certificate. W2's legacy `q` denotes NATIVE matrix-entry c, not the
W0 monomial q=Bc. W2's latest manifest has zero real native teacher records.
A supplied label is *never* promoted for training on self-asserted proofs.

A future trusted signed material/native audit must explicitly certify:
- authenticated exact Boolean F/D/retained geometry and density/frame,
- independent retained r and fixed r with a separate immutable source,
- topology-/branch-stable derivative neighborhood and derivative coordinate,
- immutable model/evaluator/checkpoint hashes, train-val-test identity split.
"""
from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

SOURCE_SHA = '0bcc187b3005478baa586a6d6f450e73811ca342'
W0_PIN = 'f30d2ece1d14051b29b30d85655928a3bf412567'
W2_PIN = 'c2628ea75a8680910557855896e7317f92567756'
W0_VALIDATOR_GIT_BLOB = 'fe5f71e7cb2b6c6ad45f48c49ab4042f797a113e'
W0_MOMENTS_GIT_BLOB = '7f844fadc02b8f02c8560b5180e29bac78332ab4'


class AdmissionBlocked(ValueError):
    pass


def _valid_sha(s):
    return type(s) is str and len(s)==64 and all(k in '0123456789abcdef' for k in s)


def gate_teacher_manifest(manifest: dict) -> dict:
    """Fail-closed even on forged `NATIVE_VERIFIED` and a positive sample count.

    The *currently pinned* W2 pre-W0 schema is never automatically trusted;
    changing its count fields or status does not create teacher observations.
    """
    if type(manifest) is not dict:
        raise AdmissionBlocked('manifest must be a JSON object')
    blockers=[]
    if manifest.get('schema')=='w2-cherchi-teacher-v1-pre-w0':
        blockers.append('W2 schema is pre-W0; q denotes native c, not monomial Bc')
    else:
        blockers.append('unknown W2 label schema; independent contract review required')
    if type(manifest.get('native_teacher_runs')) is not int or manifest['native_teacher_runs']<1:
        blockers.append('no positive count of native teacher executions')
    if type(manifest.get('training_samples')) is not int or manifest['training_samples']<1:
        blockers.append('no positive count of training samples')
    if manifest.get('pending_dependency'):
        blockers.append('W0 upstream dependency is still pending')
    if manifest.get('status')!='NATIVE_VERIFIED':
        blockers.append('native verified status missing')
    blockers.append('independent F/D material proof and per-label W0/J-neighborhood audit not supplied')
    return {'training_admissible':False,'blocked_reasons':blockers,
            'manifest_schema':manifest.get('schema'),
            'observed_native_runs':manifest.get('native_teacher_runs'),
            'observed_training_samples':manifest.get('training_samples'),
            'W0_PIN':W0_PIN,'W2_PIN':W2_PIN,
            'claim':'NO_CHERCHI_DATA_TRAINING_AND_NO_NATIVE_SPEEDUP'}


def _git_blob_sha(contents: bytes) -> str:
    return hashlib.sha1(b'blob '+str(len(contents)).encode('ascii')+b'\0'+contents).hexdigest()


def inspect_w0_candidate(record: dict, *, external_w0_validator_path: str | Path) -> dict:
    """Run the *actual* pinned W0 semantic validator on an untrusted record.

    Requires W0's Python package available on import path (e.g. after a
    reviewed code merge). Pins both W0 validator and its moment_coordinates
    dependency to their exact known Git blob SHA before invoking it. A valid
    W0 numerical record still has ZERO permission to enter real-teacher
    training: independent native F/D material and derivative-neighborhood
    proof must be checked through a separate trusted execution pipeline.
    """
    path=Path(external_w0_validator_path).resolve()
    if not path.is_file():
        raise AdmissionBlocked('pinned W0 semantic validator not present')
    if _git_blob_sha(path.read_bytes())!=W0_VALIDATOR_GIT_BLOB:
        raise AdmissionBlocked('W0 validator Git blob mismatch; no promotion')
    coordinates=path.with_name('moment_coordinates.py')
    if (not coordinates.is_file() or
            _git_blob_sha(coordinates.read_bytes())!=W0_MOMENTS_GIT_BLOB):
        raise AdmissionBlocked('W0 moment coordinate implementation mismatch')
    try:
        validator=importlib.import_module('research.NeuralMoments.contracts.validate_contract_v1')
    except ImportError as error:
        raise AdmissionBlocked('official W0 validator package is not importable') from error
    loaded_path=Path(validator.__file__).resolve()
    if loaded_path!=path:
        raise AdmissionBlocked('loaded W0 validator is not the pinned source file')
    try:
        official=validator.validate_record(record)
    except (TypeError,ValueError,KeyError,OverflowError) as error:
        raise AdmissionBlocked('official W0 semantic validator rejected record') from error
    if (not isinstance(official,dict) or official.get('structural_valid') is not True or
        official.get('safe_for_training_without_external_native_proof') is not False):
        raise AdmissionBlocked('W0 semantic validator output not in permitted untrusted state')
    return {'pinned_W0_validator_blob':W0_VALIDATOR_GIT_BLOB,
            'pinned_W0_coordinates_blob':W0_MOMENTS_GIT_BLOB,
            'source_sha':SOURCE_SHA,
            'record_sha256':official.get('canonical_sha256'),
            'w0_semantically_validated':True,
            'jacobian_mode':official.get('jacobian_mode'),
            'geometry_native_certified':False,'training_admissible':False,
            'reason':'W0 structural validation succeeded; native F/D seal and derivative-neighborhood proof still required'}


def require_teacher_admission(manifest: dict) -> None:
    report=gate_teacher_manifest(manifest)
    raise AdmissionBlocked('W6 M6: real W2 training disabled: '+'; '.join(report['blocked_reasons']))


def record_handoff(path: str | Path) -> dict:
    with open(path,encoding='utf-8') as stream:
        manifest=json.load(stream)
    return gate_teacher_manifest(manifest)

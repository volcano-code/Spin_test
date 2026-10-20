"""W0 M17: W5 migration reference, strictly excluded W2 v2 record preview.

All source bytes and scientific certificates must be independently established.
This adapter NEVER releases native r/J, teacher data, train/val/test, or Newton.
W2's legacy payload.q is native c, whereas polynomial_q is B*c.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import re
import struct

from .cross_window_interface_m16 import audit_pinned, RELATIVE, PINS, blob_sha1, strict_json

W2_V2 = 'w2-cherchi-teacher-v2-pre-w0'
NATIVE_ORDER = 'CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY'.split(',')
RAW_ORDER = 'm,x,y,z,xx,yy,zz,yz,xz,xy'.split(',')
TOTAL_POLICY = 'r_total=r_F+r_D;J_total=J_D;fixed_never_in_r_D'
NATIVE_CONVENTION = 'NATIVE_MATRIX_ENTRIES_C10_POLYNOMIAL_Q_EQUALS_BC_V1'
SHA = re.compile('[a-f0-9]{64}\\Z')


class MigrationRejected(ValueError):
    pass


def need(condition, reason):
    if not condition:
        raise MigrationRejected(reason)


def canonical(value):
    return json.dumps(value, separators=(',', ':'), sort_keys=True, allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode('utf-8')).hexdigest()


def vector10(value, name):
    need(type(value) is list and len(value) == 10 and
         all(type(x) in (float, int) and math.isfinite(x) for x in value),
         'INVALID_RAW_NATIVE_VECTOR:' + name)
    vector = [float(x) for x in value]
    need(all(math.isfinite(x) for x in vector), 'NONFINITE_NATIVE_COEFFICIENT')
    return vector


def identity_equal(a, b):
    return all(struct.pack('!d', x) == struct.pack('!d', y)
               for x, y in zip(a, b))


def signed_ray_tokens(c):
    c = vector10(c, 'native_c')
    pivot = max(range(10), key=lambda i: abs(c[i]))
    need(c[pivot] != 0, 'DEGENERATE_QUADRIC')
    denominator = Fraction.from_float(abs(c[pivot]))
    tokens = []
    for value in c:
        ratio = Fraction.from_float(value) / denominator
        tokens.append(f'{ratio.numerator}/{ratio.denominator}')
    return tokens


def archived_v2_preview(envelope, *, expected_native_c, expected_model_sha256,
                        expected_module_sha256, expected_geometry_sha256):
    """Check a v2 EXCLUDED envelope only; all evidence remains non-training.

    This is not a signature verification or native Boolean/material authority.
    All expected SHA values MUST be independently frozen by the caller.
    """
    need(type(envelope) is dict and set(envelope) == {'payload','payload_sha256','identity'},
         'V2_ENVELOPE_FIELDS_INVALID')
    p, identity = envelope['payload'], envelope['identity']
    need(type(p) is dict and type(identity) is dict, 'V2_ENVELOPE_OBJECTS_MISSING')
    need(p.get('schema') == W2_V2, 'V2_SCHEMA_REQUIRED')
    try:
        verified_payload_digest = digest(p)
    except (ValueError, TypeError, OverflowError) as exc:
        raise MigrationRejected('V2_PAYLOAD_NOT_STRICT_JSON') from exc
    need(type(envelope['payload_sha256']) is str and
         SHA.fullmatch(envelope['payload_sha256']) and
         envelope['payload_sha256'] == verified_payload_digest, 'V2_PAYLOAD_SHA_INCORRECT')
    need(set(identity) == {'q_sha256','geometry_sha256','model_sha256','native_module_sha256'},
         'V2_IDENTITY_FIELDS_INVALID')
    for key, expected in [('model_sha256',expected_model_sha256),
                          ('native_module_sha256',expected_module_sha256),
                          ('geometry_sha256',expected_geometry_sha256)]:
        need(type(expected) is str and SHA.fullmatch(expected) and
             identity.get(key) == expected, 'V2_EXTERNAL_PIN_MISSING_OR_DIFFERENT:' + key)
    need(p.get('model_sha256') == expected_model_sha256 and
         p.get('native_module_sha256') == expected_module_sha256 and
         type(p.get('geometry')) is dict and digest(p['geometry']) == expected_geometry_sha256,
         'V2_SOURCE_GEOMETRY_UNBOUND')
    raw_c = vector10(p.get('native_c'), 'native_c')
    expected = vector10(expected_native_c, 'expected_native_c')
    need(identity_equal(raw_c,expected), 'V2_ORIGINAL_C_BYTES_NOT_PRESERVED')
    need(identity.get('q_sha256') == digest(raw_c), 'V2_RAW_C_IDENTITY_SHA_CHANGED')
    need(identity_equal(raw_c,vector10(p.get('q'), 'legacy_q')),
         'V2_LEGACY_Q_IS_NOT_NATIVE_C')
    polynomial = [v * (2 if i >= 7 else 1) for i,v in enumerate(raw_c)]
    need(identity_equal(polynomial,vector10(p.get('polynomial_q'), 'polynomial_q')),
         'V2_MONOMIAL_CROSS_TERM_B_MAPPING_INCORRECT')
    need(p.get('native_c_order') == NATIVE_ORDER and p.get('order') == RAW_ORDER and
         p.get('coefficient_convention') == NATIVE_CONVENTION and
         p.get('total_policy') == TOTAL_POLICY,
         'V2_NATIVE_COEFFICIENT_OR_FIXED_POLICY_CHANGED')
    need(p.get('split') == 'excluded' and p.get('J_D') is None and
         p.get('derivative_status') in ('UNKNOWN', 'INVALID') and
         p.get('derivative_contract') is None,
         'V2_ARCHIVED_SAMPLE_MUST_REMAIN_EXCLUDED')
    need(p.get('topology_status') in ('FAILED','VALID','OBSERVED_DISCRETE_MAP') and
         type(p.get('exact_proof')) is dict,
         'V2_TOPOLOGY_OR_PROOF_FIELDS_INVALID')
    if p['topology_status'] == 'FAILED':
        need(p.get('r_D') is None and p.get('r_F') is None and
             p.get('derivative_status') == 'INVALID',
             'V2_FAILED_MATERIAL_MOMENTS_FORGED')
    for key in ('r_D', 'r_F'):
        if p.get(key) is not None:
            vector10(p[key], key)
    density = p.get('density')
    need(type(density) in (float,int) and math.isfinite(density) and density > 0,
         'V2_DENSITY_INVALID')
    norm = math.sqrt(sum(x*x for x in raw_c))
    tokens = signed_ray_tokens(raw_c)
    return {
        'schema':'W0_M17_READ_ONLY_V2_MIGRATION_PREVIEW_V1',
        'status':'W2_V2_ARCHIVE_DIAGNOSTIC_ONLY_NO_RELEASE',
        'raw_binary64_sha256':sha256(struct.pack('!10d',*raw_c)).hexdigest(),
        'signed_exact_projective_ray_sha256':digest(tokens),
        'native_c_unit_compatible_w0':abs(norm-1.0) <= 1e-12,
        'cross_terms_doubled_correctly':True,
        'original_c_never_normalized':True,
        'source_provenance_independently_certified':False,
        'saved_native_material_certified':False,
        'full_J_D_training_targets':None,
        'training_admitted':False,
    }


def _load_pinned_w5(root):
    path = root / RELATIVE['w5_contract_gate']
    need(path.is_file() and not path.is_symlink() and
         blob_sha1(path.read_bytes()) == PINS['w5_contract_gate'],
         'W5_SOURCE_PIN_CHANGED')
    spec = importlib.util.spec_from_file_location('_frozen_w5_runtime_m17', path)
    need(spec is not None and spec.loader is not None,'W5_IMPORT_LOADER_UNAVAILABLE')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def audit_legacy_runtime(root=None):
    """Execute exact reviewed W5 snapshot against an adversarial W0 record.

    The intentionally incompatible record establishes a concrete false-positive
    in the old W5 *structural parser*, never a W5 training release claim.
    """
    from .validate_contract_v1 import validate_record, ContractError
    folder = Path(root) if root is not None else Path(__file__).resolve().parent
    pinned = audit_pinned(folder)
    sample_path = folder / 'sample_contract_v1.json'
    need(sample_path.is_file() and not sample_path.is_symlink(), 'MISSING_W0_SAMPLE_FIXTURE')
    fixture = strict_json(sample_path.read_bytes())
    fixture['coefficients']['c'] = [1.0 + 4.0e-10] + [0.0]*9
    try:
        validate_record(fixture)
        w0_accepts = True
    except ContractError:
        w0_accepts = False
    consumer = _load_pinned_w5(folder)
    try:
        consumer.check_w0_contract(fixture)
        w5_accepts = True
    except consumer.AdmissionError:
        w5_accepts = False
    need(w5_accepts and not w0_accepts,
         'W5_OLD_PARSER_EXPECTED_DRIFT_NO_LONGER_PRESENT_REVIEW_MIGRATION')
    need(pinned['training_admissible'] is False and
         pinned['w5_legacy_expected_schema'] == 'w2-cherchi-teacher-v1-pre-w0',
         'W5_SOURCE_PRECONDITION_CHANGED')
    return {
        'schema':'W0_M17_ACTUAL_W5_RUNTIME_COMPATIBILITY_V1',
        'w5_frozen_source_git_blob':PINS['w5_contract_gate'],
        'w0_frozen_source_git_blob':PINS['w0_validator'],
        'actual_w5_legacy_parser_accepts_nonunit_w0_record':w5_accepts,
        'actual_w0_strict_validator_accepts_same_record':w0_accepts,
        'native_c_norm_deviation_in_counterexample':4.0e-10,
        'w5_requires_explicit_v2_implementation':True,
        'W5_real_teacher_training_authorized':False,
        'training_admitted':False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--output',required=True,type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError('M17_OUTPUT_MUST_BE_NEW')
    report = audit_legacy_runtime()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as fp:
        json.dump(report,fp,indent=2,sort_keys=True,allow_nan=False)
        fp.write('\n')
    print('W0_M17_LEGACY_W5_STRUCTURAL_FALSE_POSITIVE_OBSERVED_NO_RELEASE')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())

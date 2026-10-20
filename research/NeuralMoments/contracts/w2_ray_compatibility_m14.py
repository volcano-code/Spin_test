"""W0 M14: byte-faithful, read-only W2 M12 / W0 M13 signed-ray reconciliation.

This is a *historical diagnostic contract*, deliberately separate from
MomentContractV1: a raw (possibly non-unit) Cherchi coefficient is not a
normalized new native evaluation. Even a perfect 81-point crosswalk never
certifies a continuous derivative, Newton terminal, or training sample.

Recompute the source from the genuine pinned H8f zip, then independently form
signed positive exact-rational rays and compare the entire Git-blob aggregate
published for the genuine W2 M12 81-row ledger. No W2 code is imported.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import struct

import numpy as np

from .archived_raw_c_m13 import (
    RawCRejected, audit_real_h8f_81, ARCHIVE_SHA256, UNIT_TOL,
    binary64_digest,
)

SCHEMA = 'W0_M14_ARCHIVED_SIGNED_RAY_COMPATIBILITY_V1'
W2_SCHEMA = 'w2-m12-exact-positive-projective-ray-v1'
W2_LEDGER_GIT_BLOB = '2d4cf4aae1368e22e760803d9bfe49479125ac4b'
W2_LEDGER_SHA256 = '255769c4401a89449ef864bf0ef72ec99403d0085b5eb04891512dfe2daab473'
# This Git blob is over JSON.stringify([[index, raw canonical SHA256,
# signed exact-ray SHA256, original same-call gzip SHA256,
# original-c satisfies W0 unit rule, display is on exact same rational ray], ...]).
# Independently computed directly from W2's exact Git blob and reconciled
# with 81 authentic W0 M13 original c/gzip identities on 2026-10-20.
W2_ALL81_CROSSWALK_GIT_BLOB = '051a9bb7149ff63af92d7018019165face426f52'
EXPECTED_UNIT_INDICES = (0,21,22,23,24,61,62,63,64,69,70,71,72,77,78,79,80)
HEX64 = re.compile(r'^[0-9a-f]{64}$')


class M14Rejected(ValueError):
    pass


def require(value, reason):
    if not value:
        raise M14Rejected(reason)


def strict_json(content: bytes):
    def object_pairs(items):
        obj = {}
        for key, value in items:
            require(key not in obj, 'DUPLICATE_JSON_KEY:'+str(key))
            obj[key] = value
        return obj
    def invalid_constant(token):
        raise M14Rejected('NONFINITE_JSON_TOKEN:'+token)
    try:
        return json.loads(content, object_pairs_hook=object_pairs,
                          parse_constant=invalid_constant)
    except (ValueError, UnicodeError, TypeError) as exc:
        if isinstance(exc, M14Rejected):
            raise
        raise M14Rejected('INVALID_JSON_BYTES') from exc


def canonical(data):
    return json.dumps(data, separators=(',', ':'), sort_keys=True,
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def git_blob(data: bytes):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()


def sha(data: bytes):
    return hashlib.sha256(data).hexdigest()


def float_vector(c):
    require(type(c) is list and len(c) == 10 and
            all(type(v) in (int,float) for v in c),
            'NATIVE_C_MUST_CONTAIN_TEN_NUMBERS_NO_BOOLEAN')
    try:
        a=np.array(c,dtype=np.float64)
    except (OverflowError,ValueError,TypeError) as exc:
        raise M14Rejected('CANNOT_REPRESENT_NATIVE_C_BINARY64') from exc
    require(np.isfinite(a).all() and np.any(a != 0.0),
            'ZERO_OR_NONFINITE_NATIVE_C')
    norm = float(np.linalg.norm(a))
    require(math.isfinite(norm) and norm>0.0, 'NONREPRESENTABLE_NATIVE_C_NORM')
    return a,norm


def fraction_token(x: Fraction):
    return f'{x.numerator}/{x.denominator}'


def exact_ray(c):
    """Exact positive-ray equality of original *binary64 rationals*, not floats.

    Dividing a nonunit native coefficient by its floating norm generally
    changes its exact rational ray; never substitute display into native c/J.
    """
    x,norm = float_vector(c)
    native=[float(v) for v in x]
    pivot=max(range(10),key=lambda i:abs(native[i]))  # first max on ties
    positive=abs(native[pivot]); require(positive>0,'NONPOSITIVE_PIVOT')
    rational_scale=Fraction.from_float(positive)
    tokens=[fraction_token(Fraction.from_float(v)/rational_scale)
            for v in native]
    compatible=abs(norm-1.)<=UNIT_TOL
    display=native.copy() if compatible else (x/norm).tolist()
    display_array,display_norm=float_vector(display)
    require(abs(display_norm-1.)<=UNIT_TOL, 'W0_DISPLAY_NOT_UNIT_LENGTH')
    # Compare ratios in Q, not rounded binary64 tolerances.
    display_pivot=Fraction.from_float(abs(float(display_array[pivot])))
    require(display_pivot>0,'DISPLAY_PIVOT_LOST')
    on_exact_ray=all(fraction_token(Fraction.from_float(float(v))/display_pivot)==token
                     for v,token in zip(display,tokens))
    return {
        'original_binary64_c':native,
        'original_binary64_sha256':binary64_digest(native),
        'original_c_canonical_sha256':sha(canonical(native)),
        'positive_max_abs_pivot':pivot,
        'positive_scale_binary64_hex':positive.hex(),
        'signed_exact_ratio_tokens':tokens,
        'exact_positive_ray_sha256':sha(canonical(tokens)),
        'w0_original_c_unit_compatible':compatible,
        'w0_display_unit_c_only':display,
        'w0_display_is_original_source_bytes':struct.pack('!10d',*display)==struct.pack('!10d',*native),
        'display_exact_rational_ray_matches_source':on_exact_ray,
        'monomial_q_from_original_c':[float(v*(2 if i>=7 else 1)) for i,v in enumerate(native)],
        'native_sample_reevaluated':False,
        'archived_Jc_reparameterized':False,
        'derivative_J_D':None,
        'training_admissible':False,
    }


def _read_w2_official_bytes(path):
    """Only exactly the W2 M12 Git blob, never a lookalike JSON fixture."""
    p=Path(path)
    require(p.is_file() and not p.is_symlink() and 0<p.stat().st_size<=300_000,
            'W2_LEDGER_MISSING_UNSAFE_OR_OVERSIZED')
    data=p.read_bytes()
    require(sha(data)==W2_LEDGER_SHA256 and git_blob(data)==W2_LEDGER_GIT_BLOB,
            'W2_M12_FULL_LEDGER_IS_NOT_THE_REVIEWED_GIT_BLOB')
    a=strict_json(data)
    require(type(a) is dict and a.get('schema')==W2_SCHEMA and
            a.get('historical_workflow_conclusion')=='failure' and
            a.get('total_archived_points')==81 and
            a.get('distinct_exact_positive_rays')==81 and
            a.get('original_norm_unit_compatible_count')==17 and
            a.get('original_norm_nonunit_count')==64 and
            a.get('training_samples_admitted')==0 and
            a.get('all_derivative_J_D') is None,
            'W2_M12_PROMOTED_OR_UNSUPPORTED_LABEL_SEMANTICS')
    certs=a.get('certificates')
    require(type(certs) is list and len(certs)==81,
            'W2_M12_81_CERTIFICATES_REQUIRED')
    return certs


def reconcile_m13(report, *, w2_certificates=None):
    """Review pinned archive-derived W0 raw-c ledger against W2 M12.

    With no local W2 file, the SHA1 *aggregate* independently pinned from
    the official W2 Git blob still compares all 81 original identities;
    `w2_full_original_loaded_locally` correctly remains False.
    """
    require(type(report) is dict and report.get('schema')==
            'W0_M13_ARCHIVED_RAW_NATIVE_COEFFICIENT_DIAGNOSTIC_V1',
            'M13_SOURCE_REPORT_REQUIRED')
    require(report.get('archive_sha256')==ARCHIVE_SHA256 and
            report.get('original_workflow_conclusion')=='failure' and
            report.get('source_archived_workflow_run')==39123384402 and
            report.get('sample_count')==81 and
            report.get('v1_unit_c_compatible_count')==17 and
            report.get('v1_nonunit_c_count')==64 and
            report.get('v1_schema_unmodified') is True and
            report.get('raw_c_replaced_with_normalized_values') is False and
            report.get('newton_admitted') is False and
            report.get('training_admissible') is False and
            report.get('J_D') is None,
            'M13_ORIGINAL_FAILED_SOURCE_NOT_PINNED')
    original=report.get('rows')
    require(type(original) is list and len(original)==81,
            'M13_FULL_81_SOURCE_ROWS_REQUIRED')
    if w2_certificates is not None:
        require(type(w2_certificates) is list and len(w2_certificates)==81,
                'W2_FULL_81_CERTIFICATES_REQUIRED')
    compared=[]; crosswalk=[]; unit=[]; display_exact=0
    for i,rec in enumerate(original):
        require(type(rec) is dict and type(rec.get('index')) is int and
                rec['index']==i and rec.get('release_native_Jc') is False and
                rec.get('training_admissible') is False,
                'FORGED_OR_REORDERED_M13_SOURCE_ROW')
        generated=exact_ray(rec.get('raw_native_c'))
        require(generated['original_binary64_sha256']==rec.get('native_binary64_sha256') and
                rec.get('unit_norm_compatible_v1') is generated['w0_original_c_unit_compatible'] and
                rec.get('polynomial_q_from_raw_c')==generated['monomial_q_from_original_c'] and
                type(rec.get('source_material_gzip_sha256')) is str and
                HEX64.fullmatch(rec['source_material_gzip_sha256']),
                'M13_NATIVE_RAW_C_SOURCE_GZIP_OR_B_MAPPING_DRIFT')
        flags=[i,generated['original_c_canonical_sha256'],
               generated['exact_positive_ray_sha256'],
               rec['source_material_gzip_sha256'],
               generated['w0_original_c_unit_compatible'],
               generated['display_exact_rational_ray_matches_source']]
        crosswalk.append(flags)
        if generated['w0_original_c_unit_compatible']:unit.append(i)
        display_exact+=int(generated['display_exact_rational_ray_matches_source'])
        if w2_certificates is not None:
            src=w2_certificates[i]
            require(type(src) is dict and type(src.get('index')) is int and src['index']==i and
                    src.get('archived_native_c_sha256')==flags[1] and
                    src.get('exact_positive_ray_sha256')==flags[2] and
                    src.get('archived_material_gzip_sha256')==flags[3] and
                    src.get('w0_native_unit_rule_already_satisfied') is flags[4] and
                    src.get('w0_display_exactly_same_binary64_rational_ray') is flags[5] and
                    src.get('archived_native_c')==generated['original_binary64_c'] and
                    src.get('exact_positive_ray_ratio_tokens')==generated['signed_exact_ratio_tokens'] and
                    src.get('derivative_J_D') is None and src.get('training_admitted') is False,
                    'W2_M12_PINNED_ROW_MISMATCH:'+str(i))
        compared.append({'index':i,
                         'raw_native_c_sha256':generated['original_binary64_sha256'],
                         'signed_projective_ray_sha256':flags[2],
                         'original_material_gzip_sha256':flags[3],
                         'v1_native_unit_compatible':flags[4],
                         'unit_display_rationally_identical':flags[5],
                         'native_c_replaced':False,
                         'J_D':None,
                         'training_admissible':False})
    require(unit==list(EXPECTED_UNIT_INDICES), 'H8F_17_UNIT_INDEXES_DRIFT')
    require(len({row[2] for row in crosswalk})==81,
            'SIGNED_EXACT_RAY_IDENTITY_COLLISION')
    require(display_exact==17, 'W2_DISPLAY_IDENTITY_RULE_DRIFT')
    root=git_blob(json.dumps(crosswalk,separators=(',',':'),ensure_ascii=True).encode('ascii'))
    require(root==W2_ALL81_CROSSWALK_GIT_BLOB,
            'W2_M12_ORIGINAL_81_RAY_AND_MATERIAL_PROVENANCE_DISAGREES')
    require(original[60]['raw_native_c'][7]==3e-6 and
            compared[60]['v1_native_unit_compatible'] is False and
            generated['native_sample_reevaluated'] is False,
            'H8F_POINT60_HISTORIC_EVENT_OR_PROVENANCE_DRIFT')
    return {
      'schema':SCHEMA,'status':'81_ARCHIVED_EXACT_SIGNED_RAYS_AND_NATIVE_MATERIAL_SHA_CROSSCHECKED',
      'source_archive_sha256':ARCHIVE_SHA256,
      'original_ci_status':'failure','historical_run':39123384402,
      'w2_m12_ledger_git_blob_sha1':W2_LEDGER_GIT_BLOB,
      'w2_m12_ledger_sha256':W2_LEDGER_SHA256,
      'w2_all81_crosswalk_git_blob_sha1':root,
      'w2_full_original_loaded_locally':w2_certificates is not None,
      'sample_count':81,'unit_c_samples':len(unit),
      'nonunit_c_samples':81-len(unit),
      'unit_sample_indices':unit,
      'different_signed_positive_rays':len({r[2] for r in crosswalk}),
      'original_binary64_unit_display_same_rational_ray':display_exact,
      'nonunit_binary64_display_same_rational_ray':0,
      'point60_raw_c7':original[60]['raw_native_c'][7],
      'point60_monomial_q7':original[60]['polynomial_q_from_raw_c'][7],
      'raw_archived_r_J_never_assigned_to_display_vector':True,
      'MomentContractV1_changed':False,
      'new_native_evaluations':0,
      'derivative_J_D':None,
      'newton_admitted':False,'training_admissible':False,
      'rows':compared,
    }


def audit_archived_h8f(archive, *, w2_full_ledger=None):
    data=audit_real_h8f_81(archive)   # pins genuine ZIP and all 81 gzip bytes
    return reconcile_m13(data,w2_certificates=(
        _read_w2_official_bytes(w2_full_ledger) if w2_full_ledger else None))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--original-h8f-zip',required=True)
    parser.add_argument('--w2-m12-ledger',help='Optional exact SHA-pinned W2 JSON file')
    parser.add_argument('--output',required=True)
    a=parser.parse_args(argv)
    target=Path(a.output)
    if target.exists():raise FileExistsError('M14_NEVER_OVERWRITE_EXISTING_EVIDENCE')
    result=audit_archived_h8f(a.original_h8f_zip,w2_full_ledger=a.w2_m12_ledger)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf8') as stream:
        json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
    print(result['status'],result['sample_count'],'released:',result['training_admissible'])
    return 0


if __name__=='__main__':
    raise SystemExit(main())

"""W2 M13: immutable exact positive-projective handoff for W0 review.

This is a mathematical certificate of polynomial scaling for historical native
binary64 coefficients. It is not a Cherchi/Boolean/solid/Jacobian/Newton run,
not a trusted W0 verifier, and never authorizes any training data export.

Runtime dependencies: W2 M10 consumer gate and M12 signed-ray adapter, both
read-only. W3 and W0 are never modified or executed by this program.
"""
from __future__ import annotations

import argparse
import gzip
from fractions import Fraction
from functools import reduce
import hashlib
import json
import math
from math import gcd, lcm
from pathlib import Path
from zipfile import ZipFile

try:
    from . import w2_consumer_gate as gate
    from . import w2_projective_ray_m12 as m12
except ImportError:
    import w2_consumer_gate as gate
    import w2_projective_ray_m12 as m12

SCHEMA = 'w2-m13-projective-ray-handoff-v1'
C_ORDER = 'CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY'
Q_MAPPING = 'q=Bc;Bdiag=1,1,1,1,1,1,1,2,2,2'
RAW_SOURCE_SHA256 = gate.CANDIDATE_SHA256
HISTORIC_RUN_ID = gate.RUN_ID
ALLOWED_INDEXES = tuple(range(81))
SAMPLE_POINTS = (
    (Fraction(0), Fraction(0), Fraction(0)),
    (Fraction(1), Fraction(0), Fraction(0)),
    (Fraction(0), Fraction(1), Fraction(0)),
    (Fraction(0), Fraction(0), Fraction(1)),
    (Fraction(1), Fraction(1), Fraction(1)),
    (Fraction(1, 2), Fraction(-1, 4), Fraction(3, 5)),
    (Fraction(-2, 3), Fraction(5, 7), Fraction(-11, 13)),
)


class M13Rejected(gate.GateRejected):
    pass


def require(value, code):
    if not value:
        raise M13Rejected(code)


def rational_token(value):
    return str(value.numerator) + '/' + str(value.denominator)


def read_rational(token):
    require(type(token) is str and token.count('/') == 1,
            'INVALID_EXACT_RATIONAL_TOKEN')
    a, b = token.split('/')
    require(a.lstrip('-').isdigit() and b.isdigit() and int(b)>0,
            'NONPOSITIVE_OR_INVALID_EXACT_RATIONAL')
    return Fraction(int(a), int(b))


def exact_binary64_vector(raw):
    c = gate._real10(raw, 'EXACT_NATIVE_C')
    # Frozen JSON stores some exactly representable zeros as integer 0.
    # Convert representable integral tokens through float64, without claiming
    # that arbitrary large JSON integers are lossless native coefficients.
    require(all(type(x) is not int or abs(x) <= 2**53 for x in c),
            'UNREPRESENTABLE_JSON_INTEGER_IN_NATIVE_C')
    return tuple(Fraction.from_float(float(x)) for x in c)


def exact_native_polynomial(values, xyz):
    """W0 native symmetric-entry convention: off-diagonals are doubled."""
    require(len(values) == 10 and len(xyz) == 3,
            'INVALID_EXACT_POLYNOMIAL_SHAPE')
    x,y,z = xyz
    basis = (Fraction(1), x, y, z, x*x, y*y, z*z,
             2*y*z, 2*x*z, 2*x*y)
    return sum((ci*bi for ci,bi in zip(values,basis)),Fraction(0))


def primitive_positive_ray(raw_c):
    """Factor a *stored binary64* c exactly as positive rational times a
    primitive signed integer 10-vector, without changing saved coefficients.

    c_i = a * n_i, a > 0 rational, gcd(|n_i|)=1. The sign of n is retained,
    hence c and -c are *not* the same positive ray. Both matrices are binary64
    source values. The integer tuple itself is never passed into Cherchi.
    """
    c = exact_binary64_vector(raw_c)
    require(any(c), 'ZERO_PROJECTIVE_RAY')
    denominator = math.lcm(*(v.denominator for v in c))
    numerators = [v.numerator * (denominator // v.denominator) for v in c]
    divisor = reduce(gcd, (abs(x) for x in numerators), 0)
    require(divisor > 0, 'ZERO_PROJECTIVE_RAY')
    primitive = tuple(x//divisor for x in numerators)
    factor = Fraction(divisor,denominator)
    require(factor>0 and reduce(gcd, (abs(x) for x in primitive), 0)==1,
            'NONPRIMITIVE_RAY')
    require(all(factor*n == v for n,v in zip(primitive,c)),
            'RAY_RECONSTRUCTION_FAILED')
    m12_record = m12.ray_certificate(list(raw_c))
    pivot = m12_record['positive_max_abs_pivot']
    exact_pivot = abs(c[pivot])
    derived = [v/exact_pivot for v in c]
    require([rational_token(v) for v in derived] ==
            m12_record['exact_positive_ray_ratio_tokens'],
            'M12_EXACT_RAY_IDENTITY_MISMATCH')
    # Algebraic identity tested both coefficient-wise and at rational probes.
    raw_q=tuple(ci*(2 if i>=7 else 1) for i,ci in enumerate(c))
    integer_q=tuple(Fraction(n*(2 if i>=7 else 1)) for i,n in enumerate(primitive))
    require(all(u==factor*v for u,v in zip(raw_q,integer_q)),
            'EXACT_C_TO_Q_SCALING_MISMATCH')
    probe_results=[]
    for xyz in SAMPLE_POINTS:
        p_raw=exact_native_polynomial(c,xyz)
        p_integer=exact_native_polynomial(primitive,xyz)
        require(p_raw == factor*p_integer,
                'EXACT_POSITIVE_SCALING_PROBE_MISMATCH')
        probe_results.append(dict(xyz=[rational_token(x) for x in xyz],
             raw_value=rational_token(p_raw),
             positive_integer_ray_value=rational_token(p_integer),
             sign_consistent=(p_raw==0 and p_integer==0) or
                 (p_raw>0)==(p_integer>0),
             exact_factor_relation=True))
    require(all(row['sign_consistent'] for row in probe_results),
            'PROJECTIVE_RETAINED_SIGN_MISMATCH')
    # Stable hash includes W0's order and a *positive-only* convention.
    identity=dict(schema='w2-m13-exact-primitive-positive-ray-v1',
         c_order=C_ORDER, q_mapping=Q_MAPPING,
         primitive_signed_integer_c=[str(x) for x in primitive],
         require_positive_scale=True)
    exact_ray_sha=gate.sha256(gate.canonical(identity).encode())
    return {
        'schema':'w2-m13-algebraic-certificate-v1',
        'raw_native_c_sha256':m12_record['archived_native_c_sha256'],
        'm12_ray_sha256':m12_record['exact_positive_ray_sha256'],
        'positive_primitive_ray_sha256':exact_ray_sha,
        'positive_primitive_ray_identity':identity,
        'exact_raw_c_equals_positive_scale_times_integer_ray':True,
        'exact_positive_scale':rational_token(factor),
        'exact_native_c_tokens':[rational_token(x) for x in c],
        'exact_monomial_q_tokens':[rational_token(x) for x in raw_q],
        'exact_positive_scale_probes':probe_results,
        'raw_archived_c_unit_compatible':m12_record['w0_native_unit_rule_already_satisfied'],
        'unit_display_is_exact_same_binary64_ray':
            m12_record['w0_display_exactly_same_binary64_rational_ray'],
        'unit_display_is_not_a_new_native_evaluation':True,
        'native_boolean_material_proof_from_this_certificate':False,
        'certified_continuous_neighborhood':False,
        'derivative_J_D':None,
        'training_admitted':False,
    }


def review_m13(candidate_path,manifest_path,archive_path,*,index=60,
               w0_schema_path=None,w3_stage11_path=None):
    """Real H8f ZIP SHA and one focus packet rebind; 81-ray algebra, no release."""
    require(type(index) is int and index in ALLOWED_INDEXES,
            'INVALID_PROJECTIVE_FOCUS_INDEX')
    require(archive_path is not None, 'H8F_REAL_ARCHIVE_REQUIRED_FOR_M13')
    # M10 and M12 already performed the 81-material archived full rebind and
    # recorded that prior evidence. Re-hashing the full original ZIP and then
    # rechecking the selected *same-call* packet is independently useful without
    # re-parsing all 81 large gzip JSON materials for every algebraic audit.
    # Always distinguish this one-packet recheck from a fresh full 81 rebind.
    previous=m12.review_m12(candidate_path,manifest_path,
              archive_path=None,index=index,
              w0_schema_path=w0_schema_path,w3_stage11_path=w3_stage11_path)
    require(previous['m10_rebind_status']==
            'PINNED_M9_INDEX_ONLY_DERIVATIVES_BLOCKED',
            'M12_INDEX_ONLY_SOURCE_REJECTED')
    require(previous['total_archived_points']==81 and
            previous['projected_native_evaluations_performed']==0 and
            previous['training_samples_admitted']==0 and
            previous['full_continuous_neighborhood_certified'] is False,
            'UNAUTHENTICATED_PREVIOUS_MILESTONE')
    candidate=gate.decode_json(gate._read(candidate_path,max_bytes=500_000,
                              pinned_sha256=RAW_SOURCE_SHA256))
    require(candidate['source']['run_id']==HISTORIC_RUN_ID and
            candidate['source']['upstream_workflow_conclusion']=='failure',
            'HISTORICAL_WORKFLOW_CONCLUSION_CHANGED')
    full=[]
    distinct=set()
    for row,prior in zip(candidate['samples'],previous['certificates']):
        require(row['index']==prior['index'] and row['index']==len(full),
                'M12_CANDIDATE_ORDER_CHANGED')
        proof=primitive_positive_ray(row['native_c'])
        require(proof['m12_ray_sha256']==prior['exact_positive_ray_sha256'] and
                proof['raw_native_c_sha256']==prior['archived_native_c_sha256'],
                'M12_ORIGINAL_C_IDENTITY_CHANGED')
        require(row['J_D'] is None and row['split']=='excluded' and
                row['training_admitted'] is False and
                row['derivative_status']=='UNKNOWN_NOT_CERTIFIED',
                'UNAUTHORIZED_DERIVATIVE_RELEASE')
        require(proof['positive_primitive_ray_sha256'] not in distinct,
                'DUPLICATE_M13_PROJECTIVE_RAY')
        distinct.add(proof['positive_primitive_ray_sha256'])
        full.append(dict(index=row['index'],
                  same_call_material_gzip_sha256=row['same_call_material_gzip_sha256'],
                  original_constructive_status=row['finite_feature_status'],
                  **proof))
    require(len(full)==81 and len(distinct)==81,
            'INCOMPLETE_81_PROJECTIVE_RAYS')
    unit=[row['index'] for row in full if row['raw_archived_c_unit_compatible']]
    require(len(unit)==17 and len(full)-len(unit)==64 and
            unit==previous['original_unit_compatible_indices'],
            'W0_UNIT_C_CLASSIFICATION_CHANGED')
    point60=full[60]
    require(point60['index']==60 and
            point60['original_constructive_status']==gate.CHANGED and
            point60['raw_archived_c_unit_compatible'] is False and
            previous['point60_observed_constructor_change_preserved'] is True,
            'H8F_POINT60_EVENT_ORIGINAL_STATUS_LOST')
    archive=Path(archive_path)
    require(archive.is_file() and not archive.is_symlink() and
            gate._hash_file(archive)==gate.ARCHIVE_SHA256,
            'M13_H8F_SOURCE_ARCHIVE_SHA_MISMATCH')
    with ZipFile(archive) as z:
        raw_request=gate._read_zip_member(z,
            'artifacts/h8-request/prepared-request.json',10_000_000)
        require(gate.sha256(raw_request)==gate.REQUEST_SHA256,
                'M13_FROZEN_REQUEST_CHANGED')
        frozen=gate.decode_json(raw_request)
        if not isinstance(frozen,dict):
            raise M13Rejected('M13_FROZEN_REQUEST_INVALID')
        head=f'artifacts/h8f-all81-points/point-{index:03d}'
        compressed=gate._read_zip_member(z,head+'-material.json.gz',5_000_000)
        point=gate.decode_json(gate._read_zip_member(z,head+'.json',200_000))
    raw_row=candidate['samples'][index]
    require(gate.sha256(compressed)==raw_row['same_call_material_gzip_sha256']
            ==point['exact_same_call_material_archive_sha256'],
            'M13_FOCUS_SAME_CALL_GZIP_SHA_MISMATCH')
    material=gate.decode_json(gzip.decompress(compressed))
    require(material['quadric_coefficients']==raw_row['native_c'] and
            point['coefficients']==raw_row['native_c'] and
            material['geometry_hash']==raw_row['geometry_hash'] and
            material['topology_hash']==raw_row['topology_hash'],
            'M13_FOCUS_PACKET_IDENTITY_MISMATCH')
    require(material['variable_raw_moments']==raw_row['r_D'] and
            gate.sha256(gate.canonical(material['moment_jacobian']).encode())
            ==raw_row['jacobian_attachment_sha256'],
            'M13_FOCUS_ARCHIVED_NUMERICS_MISMATCH')
    require(max(abs(a-b-c) for a,b,c in zip(material['raw_moments'],
            raw_row['r_D'],raw_row['r_F']))<=1e-10,
            'M13_FOCUS_FIXED_MOMENT_DOUBLE_COUNT')
    preview=m12.w0_unsampled_unit_preview(raw_row,previous['focus'],
                                           frozen,material.get('boolean_operation'))
    require(preview is not None and preview['moments']['status']=='NOT_RUN' and
            preview['moments']['variable_r'] is None and
            preview['moments']['total_r'] is None and
            preview['jacobian']['values'] is None and
            preview['jacobian']['derivative_defined'] is False,
            'W0_PREVIEW_MUST_REMAIN_NOT_RUN')
    w3=previous['w3_stage11_observation']
    require(not w3.get('certified',False) and
            previous['w0_legacy_gate_supports_v2'] is False,
            'UNVERIFIED_W0_OR_W3_PROMOTION')
    return {
        'schema':SCHEMA,
        'status':'EXACT_PRIMITIVE_PROJECTIVE_HANDOFF_AWAITING_INDEPENDENT_W0_ADOPTION',
        'source':previous['source'],
        'archived_real_cherchi_materials_rebound_this_run':1,
        'historical_M10_81_rebound_evidence_observed':'W2_M10_PRIOR_RESULT_NOT_REEXECUTED',
        'historical_workflow_conclusion':'failure',
        'raw_native_c_unmodified':True,
        'native_c_order':C_ORDER,
        'monomial_mapping':Q_MAPPING,
        'arithmetic_model':'EXACT_BINARY64_AS_RATIONAL_NO_RENORMALIZATION',
        'signed_rays_compared':81,
        'distinct_positive_primitive_rays':len(distinct),
        'w0_unit_c_input_compatible':len(unit),
        'nonunit_native_c_input_cases':81-len(unit),
        'finite_numeric_moments_previous_verification':True,
        'algebraic_projective_factor_rechecked':True,
        'selected_same_call_material_sha_verified':True,
        'w0_structural_schema_observation':previous['w0_schema_observation'],
        'w3_stage11_observation':w3,
        'w0_projective_protocol_officially_adopted':False,
        'independent_native_continuity_proved':False,
        'new_native_calls':0,
        'native_newton_accepted':False,
        'all_derivative_J_D':None,
        'training_admitted_count':0,
        'focus_index':index,
        'focus_original':previous['focus']['archived_native_c'],
        'focus_w0_structural_preview_only_not_run':preview,
        'focus_preview_is_original_native_sample':False,
        'point60_constructive_feature_change':True,
        'records':full,
    }


def export_training(*args,**kwargs):
    raise M13Rejected('M13_PROJECTIVE_HANDOFF_NEVER_AUTHORIZES_JACOBIAN_TRAINING')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',required=True)
    p.add_argument('--manifest',required=True)
    p.add_argument('--archive',required=True)
    p.add_argument('--w0-schema')
    p.add_argument('--w3-stage11')
    p.add_argument('--index',type=int,default=60)
    p.add_argument('--output',required=True)
    a=p.parse_args(argv)
    try:
        result=review_m13(a.candidate,a.manifest,a.archive,index=a.index,
            w0_schema_path=a.w0_schema,w3_stage11_path=a.w3_stage11)
        code=0
    except (M13Rejected,m12.M12Rejected,gate.GateRejected,ValueError,
            TypeError,KeyError,FileNotFoundError) as error:
        result={'schema':SCHEMA,'status':'REJECTED','error':str(error),
                'all_derivative_J_D':None,'training_admitted_count':0}
        code=2
    gate._write_exclusive(a.output,result)
    print(gate.canonical({'status':result['status'],
          'training_admitted_count':0,
          'signed_rays_compared':result.get('signed_rays_compared')}))
    return code


if __name__=='__main__':
    raise SystemExit(main())

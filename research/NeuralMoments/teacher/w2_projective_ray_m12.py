"""W2-M12: exact positive-projective-ray identity of archived native c values.

Scientific boundary: projective-equivalent *polynomials* need not yield
bitwise-identical native triangulations, source branches, moments or Jacobians.
No native evaluation or training release is performed by this module.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
from zipfile import ZipFile

import numpy as np

try:
    from . import w2_consumer_gate as pinned
except ImportError:
    import w2_consumer_gate as pinned

SCHEMA = 'w2-m12-exact-positive-projective-ray-v1'
UNIT_TOL = 1e-12  # W0's structural native-c acceptance rule, not a numerical truth threshold.
W0_SCHEMA_BLOB = '52c2cfa54567d7dc2164c4b9eb56e8385c0ee1dc'
W0_V1_ONLY_GATE_BLOB = 'b42ec6d9b389675123250d79f9cc9efb1b658c07'
W3_STAGE11_BLOB = '342b5e6968ba029c2af389de8de4a394543f422e'

class M12Rejected(pinned.GateRejected):
    pass


def need(condition, code):
    if not condition:
        raise M12Rejected(code)


def git_blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def exact_ratio_token(q):
    return str(q.numerator) + '/' + str(q.denominator)


def ray_certificate(c):
    """Exact positive-ray signature of the *stored* binary64 native coefficients.

    Max-absolute pivot is always positive, and its sign is retained in its
    resulting ratio. Thus c and -c have DIFFERENT projective identities.
    """
    raw = pinned._real10(c, 'NATIVE_C')
    norm = float(np.linalg.norm(np.asarray(raw, dtype=np.float64)))
    need(math.isfinite(norm) and norm > 0, 'DEGENERATE_OR_UNREPRESENTABLE_NATIVE_C')
    pivot = max(range(10), key=lambda i: abs(raw[i]))
    scale = abs(float(raw[pivot]))
    need(math.isfinite(scale) and scale > 0, 'POSITIVE_PROJECTIVE_SCALE_REQUIRED')
    exact_scale = Fraction.from_float(scale)
    ratios = [Fraction.from_float(float(x))/exact_scale for x in raw]
    tokens = [exact_ratio_token(value) for value in ratios]
    signed_ray_sha = pinned.sha256(pinned.canonical(tokens).encode('utf-8'))
    already_unit = abs(norm-1) <= UNIT_TOL
    # A W0-*display* at unit norm: if input already satisfies W0, keep the
    # exact original coefficient bytes; else dividing by norm rounds binary64.
    display = [float(x) for x in raw] if already_unit else (
        np.asarray(raw, dtype=np.float64)/norm).tolist()
    display_norm = float(np.linalg.norm(np.asarray(display)))
    need(math.isfinite(display_norm) and abs(display_norm-1) <= UNIT_TOL,
         'W0_UNIT_NORM_DISPLAY_NUMERICAL_FAILURE')
    displayed_ray = [Fraction.from_float(float(x))/Fraction.from_float(
        abs(float(display[pivot]))) for x in display]
    exact_same_as_raw = all(x == y for x,y in zip(displayed_ray,ratios))
    # A display rounded to float may not represent the *exact same rational*
    # ray; preserve the separate exact tokens and forbid claiming same-call.
    if not already_unit:
        need(not (display == raw), 'UNEXPECTED_UNCHANGED_NON_UNIT_VECTOR')
    return {
        'archived_native_c': list(raw),
        'archived_native_c_sha256':pinned.sha256(pinned.canonical(raw).encode()),
        'positive_max_abs_pivot':pivot,
        'positive_max_abs_scale_binary64_hex':scale.hex(),
        'exact_positive_ray_ratio_tokens':tokens,
        'exact_positive_ray_sha256':signed_ray_sha,
        'original_norm_deviation':abs(norm-1.0),
        'w0_native_unit_rule_already_satisfied':already_unit,
        'w0_unit_display_only_c':display,
        'w0_unit_display_sha256':pinned.sha256(pinned.canonical(display).encode()),
        'w0_unit_display_norm_deviation':abs(display_norm-1),
        'w0_display_is_original_archived_native_c':display == raw,
        'w0_display_exactly_same_binary64_rational_ray':exact_same_as_raw,
        'monomial_q_from_archived_native_c':[float(x*(2 if i>=7 else 1)) for i,x in enumerate(raw)],
        'projective_equivalence_scope':'EXACT_ALGEBRAIC_ZERO_SET_ONLY_NOT_NATIVE_EVALUATION',
        'derivative_J_D':None,'training_admitted':False,
    }


def _optional_pinned_json(path, expected_git_blob_sha, label):
    if path is None:
        return {'observed':False,'certified':False,'reason':label+'_NOT_SUPPLIED'}
    file=Path(path)
    need(file.is_file() and not file.is_symlink(), label+'_FILE_MISSING_OR_LINK')
    raw=file.read_bytes()
    need(git_blob(raw)==expected_git_blob_sha, label+'_GIT_BLOB_DRIFT')
    return {'observed':True,'certified':False,'git_blob_sha1':expected_git_blob_sha,
            'body':pinned.decode_json(raw)}


def _load_frozen_request(archive):
    with ZipFile(archive) as z:
        raw=pinned._read_zip_member(z, 'artifacts/h8-request/prepared-request.json',10_000_000)
    need(pinned.sha256(raw)==pinned.REQUEST_SHA256,'REQUEST_SHA_DRIFT')
    req=pinned.decode_json(raw)
    need(req.get('schema')=='spin-heart-h8-faster-preparation-v1',
         'UNSUPPORTED_FROZEN_REQUEST_SCHEMA')
    return req


def w0_unsampled_unit_preview(original_row, projected_certificate, frozen, operation):
    """A W0-shaped NOT_RUN *display*, never a new observed Cherchi sample.

    Numerical r_D from the original raw-c evaluation is intentionally NOT
    injected into this display; that would fabricate a unit-c native packet.
    """
    need(operation in ('intersection','subtraction'), 'UNVERIFIED_BOOLEAN_OPERATION')
    evidence=frozen['evidence']; request=frozen['request']; src=evidence['source_sha256']
    need(all(isinstance(src.get(k),str) and len(src[k])==64 for k in
             ('initial_top.obj','fixed_shell.obj','design_domain.obj')),
         'FROZEN_SOURCE_ASSET_HASHES_MISSING')
    # The retained side is intentionally UNKNOWN without the original exact
    # material side proof; W0 preview requires the side. The finite historical
    # packet is read only after the complete original archive is rebound.
    return {
        'schema':'MomentContractV1','source_sha':pinned.SOURCE_SHA,
        'geometry':{
            'original_sha256':src['initial_top.obj'],
            'fixed_F_sha256':src['fixed_shell.obj'],
            'design_D_sha256':src['design_domain.obj'],
            'frame':{'kind':'INPUT_NORMALIZED_TARGET_V1',
                'length_original_per_normalized':float(request['original_units_per_normalized_unit']),
                'density_original_per_normalized':float(evidence['density_kg_m3']),
                'origin_original':[0.,0.,0.]},
            'density':float(request['material_density']),
            'fixed_r_computed_once':True},
        'coefficients':{'c':projected_certificate['w0_unit_display_only_c'],
            'order':'CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY',
            'positive_scale_equivalent':True,'negative_sign_equivalent':False,
            'retained_side':'BETA_POSITIVE' if operation=='intersection' else 'BETA_NEGATIVE',
            'cross_mapping':'q=Bc;Bdiag=1,1,1,1,1,1,1,2,2,2'},
        'moments':{'order':'M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY',
            'fixed_r':list(original_row['r_F']),
            'variable_r':None,'total_r':None,
            'status':'NOT_RUN','independent_geometry_evidence':False},
        'jacobian':{'type':'UNAVAILABLE','derivative_defined':False,
            'values':None,'native_tangent_basis':None,
            'hessian_rule':'ONLY_IF_SMOOTH_AMBIENT_CHECK_Jc_B_INVERSE'},
        'error':{'truth_kind':'NONE',
            'length_ref':float(request['original_units_per_normalized_unit']),
            'density_ref':float(evidence['density_kg_m3']),
            'metric':'ABSOLUTE_PER_COMPONENT_DIVIDED_BY_RHO_L3_L4_L5',
            'threshold_policy':'PER_CASE_PREDECLARED_NO_UNIVERSAL_1_PERCENT',
            'certifies_proof':False},
    }


def review_m12(candidate_path,manifest_path,*,archive_path=None,index=60,
               w0_schema_path=None,w3_stage11_path=None):
    need(type(index) is int and 0<=index<81,'INVALID_SAMPLE_INDEX')
    trusted=pinned.review(candidate_path,manifest_path,archive_path=archive_path)
    need(trusted['status'] in ('PINNED_M9_INDEX_ONLY_DERIVATIVES_BLOCKED',
         'ARCHIVED_81_MATERIALS_REBOUND_DERIVATIVES_BLOCKED'),
         'PARENT_W2_M10_GATE_NOT_PASSED')
    candidate=pinned.decode_json(pinned._read(candidate_path,max_bytes=500_000,
                                                pinned_sha256=pinned.CANDIDATE_SHA256))
    row_certificates=[]
    ray_set=set()
    pass_indices=[]
    for row in candidate['samples']:
        cert=ray_certificate(row['native_c'])
        need(cert['monomial_q_from_archived_native_c']==row['polynomial_q'],
             'RAW_C_Q_CROSS_MAPPING_DRIFT')
        need(cert['exact_positive_ray_sha256'] not in ray_set,
             'DUPLICATE_POSITIVE_RAY_IN_HISTORICAL_SAMPLES')
        ray_set.add(cert['exact_positive_ray_sha256'])
        if cert['w0_native_unit_rule_already_satisfied']:
            pass_indices.append(row['index'])
        row_certificates.append({
            'index':row['index'],
            'archived_material_gzip_sha256':row['same_call_material_gzip_sha256'],
            'finite_feature_status':row['finite_feature_status'],
            'same_call_raw_c_not_replaced':True,
            **cert})
    need(pass_indices==[0,21,22,23,24,61,62,63,64,69,70,71,72,77,78,79,80],
         'H8F_W0_NATIVE_NORM_COMPATIBILITY_DRIFT')
    need(row_certificates[60]['finite_feature_status']==pinned.CHANGED and
         row_certificates[60]['archived_native_c'][7]==3e-6 and
         not row_certificates[60]['w0_native_unit_rule_already_satisfied'],
         'POINT60_CONSTRUCTIVE_CHANGE_OR_NORM_UNSAFE')
    w0=_optional_pinned_json(w0_schema_path,W0_SCHEMA_BLOB,'W0_SCHEMA')
    if w0['observed']:
        need(w0['body'].get('title')=='MomentContractV1' and
             w0['body']['properties']['coefficients']['properties']['cross_mapping']['const']==
             'q=Bc;Bdiag=1,1,1,1,1,1,1,2,2,2',
             'W0_SCHEMA_SEMANTIC_MISMATCH')
    w3=_optional_pinned_json(w3_stage11_path,W3_STAGE11_BLOB,'W3_STAGE11')
    if w3['observed']:
        b=w3['body']
        need(b['historical_workflow_run_id']==pinned.RUN_ID and
             b['historical_workflow_run_conclusion']=='failure' and
             b['new_cherchi_native_calls']==0 and b['new_real_native_side_count']==0 and
             b['newton_admitted'] is False and b['heart_final_obj_produced'] is False,
             'W3_STAGE11_NOT_AUTHENTICATED_OR_FALSE_NATIVE_UPGRADE')
    for status in (w0,w3):
        status.pop('body',None)
    focus=row_certificates[index]
    frozen=_load_frozen_request(archive_path) if archive_path is not None else None
    if frozen is not None:
        with ZipFile(archive_path) as z:
            compressed=pinned._read_zip_member(z,
              f'artifacts/h8f-all81-points/point-{index:03d}-material.json.gz',5_000_000)
        need(pinned.sha256(compressed)==candidate['samples'][index]['same_call_material_gzip_sha256'],
             'W0_PREVIEW_PACKET_SHA_MISMATCH')
        import gzip
        material=pinned.decode_json(gzip.decompress(compressed))
        need(material.get('quadric_coefficients')==candidate['samples'][index]['native_c'],
             'W0_PREVIEW_PACKET_NATIVE_C_MISMATCH')
        preview=w0_unsampled_unit_preview(candidate['samples'][index],focus,frozen,
                                          material.get('boolean_operation'))
    else:
        preview=None
    return {
       'schema':SCHEMA,'status':'EXACT_POSITIVE_RAY_IDENTITIES_AUDITED_NO_NATIVE_PROMOTION',
       'source':trusted['source'],'historical_workflow_conclusion':'failure',
       'm10_rebind_status':trusted['status'],
       'w0_schema_observation':w0,'w0_legacy_gate_supports_v2':False,
       'w3_stage11_observation':w3,'projective_method':
           'EXACT_BINARY64_POSITIVE_MAXABS_PIVOT_SIGNED_RATIOS_V1',
       'total_archived_points':len(row_certificates),
       'original_norm_unit_compatible_count':len(pass_indices),
       'original_norm_nonunit_count':81-len(pass_indices),
       'original_unit_compatible_indices':pass_indices,
       'distinct_exact_positive_rays':len(ray_set),
       'projective_algebra_equivalence_certified':True,
       'identical_native_evaluation_or_geometry_certified':False,
       'projected_native_evaluations_performed':0,
       'all_derivative_J_D':None,'training_samples_admitted':0,
       'focus_index':index,'focus':focus,
       'focus_w0_unsampled_unit_display_preview':preview,
       'focus_w0_preview_is_native_result':False,
       'full_continuous_neighborhood_certified':False,
       'point60_observed_constructor_change_preserved':True,
       'certificates':row_certificates,
    }


def export_training(*args,**kwargs):
    raise M12Rejected('M12_PROJECTIVE_RAY_PREVIEW_CANNOT_RELEASE_TRAINING')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',required=True);p.add_argument('--manifest',required=True)
    p.add_argument('--archive');p.add_argument('--index',type=int,default=60)
    p.add_argument('--w0-schema');p.add_argument('--w3-stage11')
    p.add_argument('--output',required=True)
    a=p.parse_args(argv)
    try:
        result=review_m12(a.candidate,a.manifest,archive_path=a.archive,
                  index=a.index,w0_schema_path=a.w0_schema,w3_stage11_path=a.w3_stage11)
        code=0
    except (M12Rejected,pinned.GateRejected,ValueError,KeyError,FileNotFoundError) as error:
        result={'schema':SCHEMA,'status':'REJECTED','error':str(error),
                'all_derivative_J_D':None,'training_samples_admitted':0}
        code=2
    pinned._write_exclusive(a.output,result)
    print(pinned.canonical({'status':result['status'],
        'training_samples_admitted':0,'original_norm_nonunit_count':
        result.get('original_norm_nonunit_count')}))
    return code


if __name__=='__main__':
    raise SystemExit(main())

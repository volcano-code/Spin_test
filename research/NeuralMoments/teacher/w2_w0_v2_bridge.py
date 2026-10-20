"""W2 M11: read-only compatibility handoff to W0 MomentContractV1.

Two distinct identities are NEVER conflated:
  (1) W2 archived H8f 81 finite-point physical moments (exactly pinned);
  (2) W0's unit-native-c / complete geometry / independent release contract.

Provides optional W0 *structural diagnostic* records for physically reverified,
archived and unit-norm compatible cases only. It never releases a Jacobian,
certifies the continuous neighborhood, or writes a train/val/test split.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from zipfile import ZipFile
import numpy as np

try:
    from . import w2_consumer_gate as existing
except ImportError:
    import w2_consumer_gate as existing

W0_SCHEMA_BLOB_SHA1 = '52c2cfa54567d7dc2164c4b9eb56e8385c0ee1dc'
W0_LEGACY_GATE_BLOB_SHA1 = 'b42ec6d9b389675123250d79f9cc9efb1b658c07'
W0_M9_HANDOFF_BLOB_SHA1 = '5f95bdeeb9f6b5bd9156aa796d3b72f9f1649de7'
W3_STAGE9_REPORT_BLOB_SHA1 = 'ec6995c2b60cb5158d94f79a783a60d9ad64f23d'
W3_POINT60_CERT_BLOB_SHA1 = '213d0d7f7bfec6ffa293cfd735556d8b10316601'
SOURCE_SHA = existing.SOURCE_SHA
C_ORDER = 'CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY'
R_ORDER = 'M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY'
B_MAPPING = 'q=Bc;Bdiag=1,1,1,1,1,1,1,2,2,2'
LABEL_V2 = 'w2-cherchi-teacher-v2-pre-w0'
_HEX64 = re.compile(r'^[a-f0-9]{64}$')


class BridgeRejected(existing.GateRejected):
    pass


def require(condition, code):
    if not condition:
        raise BridgeRejected(code)


def _git_blob_bytes(raw):
    header=b'blob '+str(len(raw)).encode('ascii')+b'\0'
    return hashlib.sha1(header+raw).hexdigest()


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pinned_w0_schema(path):
    if path is None:
        return {'observed': False, 'reason': 'W0_SCHEMA_NOT_SUPPLIED_IN_W2_BRANCH',
                'expected_git_blob_sha1': W0_SCHEMA_BLOB_SHA1}
    raw=Path(path).read_bytes()
    require(_git_blob_bytes(raw)==W0_SCHEMA_BLOB_SHA1,'W0_SCHEMA_BLOB_SHA_CHANGED')
    obj=existing.decode_json(raw)
    require(obj.get('title')=='MomentContractV1' and
            obj['properties']['coefficients']['properties']['cross_mapping']['const']==B_MAPPING and
            obj['properties']['source_sha']['const']==SOURCE_SHA,
            'W0_SCHEMA_CONTRACT_MISMATCH')
    return {'observed':True,'verified_git_blob_sha1':W0_SCHEMA_BLOB_SHA1}


def _pinned_w3_status(path):
    if path is None:
        return {'observed':False, 'native_event_certified':False,
                'reason':'W3_STAGE9_REPORT_NOT_SUPPLIED'}
    raw=Path(path).read_bytes()
    require(_git_blob_bytes(raw)==W3_STAGE9_REPORT_BLOB_SHA1,'W3_STAGE9_BLOB_SHA_CHANGED')
    report=existing.decode_json(raw)
    require(report['historical_actions_run_id']==existing.RUN_ID and
            report['historical_actions_conclusion']=='failure' and
            report['new_native_cherchi_calls']==0 and
            report['new_native_four_point_material_archives']==0 and
            report['qualified_continuous_neighborhood'] is False and
            report['accepted_newton_step_observed'] is False and
            report['newton_admitted'] is False and
            report['original_heart_obj_produced'] is False,
            'W3_STAGE9_UNVERIFIED_OR_UPGRADED')
    return {'observed':True,'verified_git_blob_sha1':W3_STAGE9_REPORT_BLOB_SHA1,
            'native_event_certified':False, 'accepted_newton_step':False,
            'original_real_new_native_calls':0,
            'reason':'W3_CONDITIONAL_ANALYTIC_EVENT_ONLY_NO_NEW_NATIVE_SIDES'}


def _validate_w2_v2_one(label, *, expected_native_c, expected_model_sha256,
                           expected_module_sha256, expected_geometry_sha256):
    """Fail-closed W2 v2 envelope structural check, NEVER native proof.

    Requires independent expected values, not identities copied from label.
    This is a separate v2 entrypoint; W0's currently observed W2 gate is v1-only.
    """
    require(type(label) is dict and set(label)=={'payload','payload_sha256','identity'},
            'W2_V2_ENVELOPE_FIELDS_INVALID')
    p=label['payload']; identity=label['identity']
    require(type(p) is dict and p.get('schema')==LABEL_V2,
            'W2_V2_SCHEMA_REQUIRED')
    for name in ('payload_sha256',):
        require(type(label[name]) is str and _HEX64.fullmatch(label[name]),
                'INVALID_W2_ENVELOPE_SHA')
    require(hashlib.sha256(existing.canonical(p).encode()).hexdigest()==label['payload_sha256'],
            'W2_V2_PAYLOAD_DIGEST_MISMATCH')
    require(type(identity) is dict and set(identity)=={
        'q_sha256','geometry_sha256','model_sha256','native_module_sha256'},
        'W2_V2_IDENTITY_KEYS_INVALID')
    for attr,value in (('model_sha256',expected_model_sha256),
                       ('native_module_sha256',expected_module_sha256),
                       ('geometry_sha256',expected_geometry_sha256)):
        require(type(value) is str and _HEX64.fullmatch(value) and
                identity[attr]==value, 'W2_V2_EXTERNAL_IDENTITY_MISMATCH:'+attr)
    require(p['model_sha256']==expected_model_sha256 and
            p['native_module_sha256']==expected_module_sha256 and
            hashlib.sha256(existing.canonical(p['geometry']).encode()).hexdigest()==expected_geometry_sha256,
            'W2_V2_PAYLOAD_EXTERNAL_IDENTITY_MISMATCH')
    c=existing._real10(p.get('native_c'),'NATIVE_C')
    expected_c=existing._real10(expected_native_c,'EXPECTED_NATIVE_C')
    existing._equal10(c,expected_c,'PINNED_NATIVE_C')
    existing._equal10(p.get('q'),c,'W2_LEGACY_Q_IS_NATIVE_C')
    existing._equal10(p.get('polynomial_q'),
                      [x*(2 if i>=7 else 1) for i,x in enumerate(c)],
                      'MONOMIAL_Q_EQUALS_B_C')
    require(p.get('order')==['m','x','y','z','xx','yy','zz','yz','xz','xy'] and
            p.get('native_c_order')==C_ORDER.split(',') and
            p.get('coefficient_convention')==
            'NATIVE_MATRIX_ENTRIES_C10_POLYNOMIAL_Q_EQUALS_BC_V1',
            'W2_V2_C_AND_R_ORDERS_INCOMPATIBLE')
    require(p.get('total_policy')=='r_total=r_F+r_D;J_total=J_D;fixed_never_in_r_D',
            'W2_V2_FIXED_COUNTING_POLICY_CHANGED')
    require(hashlib.sha256(existing.canonical(c).encode()).hexdigest()==identity['q_sha256'],
            'W2_V2_NATIVE_C_SHA_MISMATCH')
    require(p.get('split')=='excluded' and p.get('J_D') is None and
            p.get('derivative_status') in ('UNKNOWN','INVALID') and
            p.get('derivative_contract') is None,
            'W2_V2_DERIVATIVE_PROMOTION_DENIED')
    require(type(p.get('exact_proof')) is dict, 'W2_V2_EXACT_PROOF_FIELDS_MISSING')
    for k in ('r_D','r_F'):
        if p.get(k) is not None:existing._real10(p[k],k)
    require(p.get('topology_status') in ('FAILED','VALID','OBSERVED_DISCRETE_MAP'),
            'W2_V2_TOPOLOGY_STATUS_INVALID')
    if p['topology_status']=='FAILED':
        require(p['r_D'] is None and p['r_F'] is None and
                p['derivative_status']=='INVALID',
                'W2_V2_FAILED_MATERIAL_FABRICATED')
    require(type(p.get('stage_seconds')) is dict and all(
        type(k) is str and type(v) in (int,float) and math.isfinite(v) and v>=0
        for k,v in p['stage_seconds'].items()),'W2_V2_INVALID_STAGE_TIMES')
    require(p.get('peak_rss_bytes') is None or
            (type(p['peak_rss_bytes']) is int and p['peak_rss_bytes']>=0),
            'W2_V2_INVALID_MEMORY')
    require(type(p.get('density')) in (int,float) and
            math.isfinite(p['density']) and p['density']>0, 'W2_V2_INVALID_DENSITY')
    # Claimed native=True and W0_SHA in user content are never authentication.
    return {'schema':'w2-m11-v2-identity-preflight-v1',
            'native_c':list(c),'polynomial_q':[x*(2 if i>=7 else 1) for i,x in enumerate(c)],
            'variable_r':p['r_D'],'fixed_r':p['r_F'],
            'w0_unit_native_c':abs(float(np.linalg.norm(np.asarray(c)))-1)<=1e-12,
            'native_material_certified':False, 'derivative_J_D':None,
            'training_admitted':False, 'status':'STRUCTURAL_V2_ONLY_NOT_NATIVE_CERTIFICATION',
            'blocked_reasons':['W0_V2_INDEPENDENT_VALIDATOR_NOT_CONNECTED',
                               'NATIVE_MATERIAL_AND_CONTINUOUS_STRATUM_NOT_AUTHENTICATED']}


def _read_archive_request(archive_path):
    path=Path(archive_path)
    require(path.is_file() and not path.is_symlink() and
            existing._hash_file(path)==existing.ARCHIVE_SHA256,
            'W0_ARCHIVE_MISSING_OR_UNTRUSTED')
    with ZipFile(path) as z:
        raw=existing._read_zip_member(z,'artifacts/h8-request/prepared-request.json',10_000_000)
    require(hashlib.sha256(raw).hexdigest()==existing.REQUEST_SHA256,
            'W0_ORIGINAL_REQUEST_SHA_MISMATCH')
    frozen=existing.decode_json(raw)
    require(frozen.get('schema')=='spin-heart-h8-faster-preparation-v1',
            'FROZEN_H8_REQUEST_SCHEMA_MISMATCH')
    src=frozen['evidence']['source_sha256']
    require(all(type(src.get(k)) is str and _HEX64.fullmatch(src[k])
                for k in ('initial_top.obj','fixed_shell.obj','design_domain.obj')),
            'FROZEN_H8_SOURCE_FILE_SHA_MISSING')
    req=frozen['request']
    return frozen


def _read_archive_material(archive_path,index):
    with ZipFile(archive_path) as z:
        name=f'artifacts/h8f-all81-points/point-{index:03d}-material.json.gz'
        packed=existing._read_zip_member(z,name,5_000_000)
        data=gzip.decompress(packed)
        require(len(data)<20_000_000,'ARCHIVED_MATERIAL_TOO_LARGE')
    return existing.decode_json(data)


def _w0_diagnostic_record(row, archive, frozen):
    """W0-schema-shaped physical moment diagnostic; NEVER a released label.

    Only called after M10 has independently rebound all 81 material blobs.
    The original native c is never normalized or rewritten.
    """
    c=row['native_c']
    require(abs(float(np.linalg.norm(np.asarray(c)))-1)<=1e-12,
            'RAW_NATIVE_C_NOT_W0_UNIT_NORM_NO_SILENT_RENORMALIZATION')
    m=_read_archive_material(archive,row['index'])
    require(m.get('quadric_coefficients')==c and
            m.get('geometry_hash')==row['geometry_hash'] and
            m.get('topology_hash')==row['topology_hash'],
            'ARCHIVED_MATERIAL_DRIFT_DURING_DIAGNOSTIC')
    op=m.get('boolean_operation')
    require(op in ('intersection','subtraction'), 'CHERCHI_BOOLEAN_SIDE_UNKNOWN')
    e=frozen['evidence']; request=frozen['request']; src=e['source_sha256']
    require(request['material_density']>0 and
            request['original_units_per_normalized_unit']>0 and
            e['density_kg_m3']>0, 'W0_FRAME_UNVERIFIED')
    rf=row['r_F']; rd=row['r_D']
    return {
        'schema':'MomentContractV1','source_sha':SOURCE_SHA,
        'geometry':{'original_sha256':src['initial_top.obj'],
                    'fixed_F_sha256':src['fixed_shell.obj'],
                    'design_D_sha256':src['design_domain.obj'],
                    'frame':{'kind':'INPUT_NORMALIZED_TARGET_V1',
                             'length_original_per_normalized':float(request['original_units_per_normalized_unit']),
                             'density_original_per_normalized':float(e['density_kg_m3']),
                             'origin_original':[0.,0.,0.]},
                    'density':float(request['material_density']),
                    'fixed_r_computed_once':True},
        'coefficients':{'c':list(c),'order':C_ORDER,
                        'positive_scale_equivalent':True,'negative_sign_equivalent':False,
                        'retained_side':'BETA_POSITIVE' if op=='intersection' else 'BETA_NEGATIVE',
                        'cross_mapping':B_MAPPING},
        'moments':{'order':R_ORDER,'fixed_r':list(rf),'variable_r':list(rd),
                   'total_r':[a+b for a,b in zip(rf,rd)],
                   'status':'NATIVE_VERIFIED','independent_geometry_evidence':True},
        'jacobian':{'type':'UNAVAILABLE','derivative_defined':False,
                    'values':None,'native_tangent_basis':None,
                    'hessian_rule':'ONLY_IF_SMOOTH_AMBIENT_CHECK_Jc_B_INVERSE'},
        'error':{'truth_kind':'INDEPENDENT_NATIVE_SEAL',
                 'length_ref':float(request['original_units_per_normalized_unit']),
                 'density_ref':float(e['density_kg_m3']),
                 'metric':'ABSOLUTE_PER_COMPONENT_DIVIDED_BY_RHO_L3_L4_L5',
                 'threshold_policy':'PER_CASE_PREDECLARED_NO_UNIVERSAL_1_PERCENT',
                 'certifies_proof':False}}


def review_m11(candidate_path, manifest_path, *, archive_path=None, index=0,
               w0_schema_path=None, w3_report_path=None):
    require(type(index) is int and 0<=index<81,'INVALID_M11_POINT_INDEX')
    w0_status=_pinned_w0_schema(w0_schema_path)
    w3_status=_pinned_w3_status(w3_report_path)
    gate=existing.review(candidate_path,manifest_path,archive_path=archive_path)
    candidate=existing.decode_json(existing._read(candidate_path,max_bytes=500_000,
                                                    pinned_sha256=existing.CANDIDATE_SHA256))
    rows=candidate['samples']
    norms=[float(np.linalg.norm(np.asarray(r['native_c'],dtype=np.float64))) for r in rows]
    unit=[i for i,n in enumerate(norms) if abs(n-1.)<=1e-12]
    # Hard numerical contract regression from actual historical c vectors.
    require(len(unit)==17 and len(norms)==81,
            'H8F_NATIVE_C_UNIT_SPHERE_COMPATIBILITY_DRIFT')
    row=rows[index]
    preview={'native_c':list(row['native_c']),
             'polynomial_q':[c*(2 if j>=7 else 1) for j,c in enumerate(row['native_c'])],
             'r_F':list(row['r_F']),'r_D':list(row['r_D']),
             'r_total':[a+b for a,b in zip(row['r_F'],row['r_D'])],
             'w0_coefficient_order':C_ORDER,'w0_moment_order':R_ORDER,
             'finite_symbolic_status':row['finite_feature_status'],
             'derivative_J_D':None,'training_admitted':False}
    record=None
    if archive_path is not None and index in unit:
        frozen=_read_archive_request(archive_path)
        record=_w0_diagnostic_record(row,archive_path,frozen)
        # No W0 V2 verifier is present in W2; schema-shaped != authenticated.
    gaps=['W0_V2_SIGNED_AND_INDEPENDENT_PHYSICAL_PROVENANCE_VALIDATOR_NOT_INTEGRATED',
          'W3_REAL_ONE_SIDED_NATIVE_CROSSING_EVIDENCE_NOT_YET_ADMITTED',
          'NO_ACCEPTED_AND_INDEPENDENTLY_SEALED_NEWTON_TERMINAL',
          'SAVED_M9_JACOBIAN_PROVENANCE_NOT_CONTINUOUS_NEIGHBORHOOD']
    if index not in unit:gaps.append('RAW_NATIVE_C_NOT_W0_UNIT_NORM_DO_NOT_NORMALIZE_ARCHIVE')
    if archive_path is None:gaps.append('ORIGINAL_CHERCHI_MATERIAL_NOT_OPENED_THIS_REVIEW')
    if not w0_status['observed']:gaps.append('W0_SCHEMA_NOT_BYTE_PINNED_THIS_REVIEW')
    return {'schema':'w2-m11-w0-v2-handoff-v1',
            'status':'READ_ONLY_W0_STRUCTURAL_PREVIEW_NO_TRAINING_ADMISSION',
            'w2_historical_rebind':gate['status'],
            'source':gate['source'],'requested_index':index,
            'w0_schema':w0_status,'w3_latest':w3_status,
            'unit_c_compatibility':{'count_pass':len(unit),'count_fail':81-len(unit),
                                    'passing_indices':unit,
                                    'max_absolute_norm_deviation':max(abs(n-1.) for n in norms),
                                    'requested_norm':norms[index],
                                    'requested_unit_compatible':index in unit,
                                    'prohibits_renormalizing_saved_c':True},
            'coordinate_mapping_only':preview,
            'w0_structural_diagnostic_record':record,
            'w0_diagnostic_record_is_release':False,
            'w0_schema_structural_validation_performed':False,
            'formal_w0_v2_label_issued':False,
            'derivative_training_samples':0,'train_split':None,
            'source_scientific_gaps':gaps,
            'point60_changed_feature_is_not_smooth':True}


def export_training(*args,**kwargs):
    raise BridgeRejected('M11_MOMENTCONTRACTV1_V2_TRAINING_RELEASE_BLOCKED')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--candidate',required=True)
    p.add_argument('--manifest',required=True)
    p.add_argument('--archive')
    p.add_argument('--index',type=int,default=0)
    p.add_argument('--w0-schema')
    p.add_argument('--w3-report')
    p.add_argument('--output',required=True)
    args=p.parse_args(argv)
    try:
        result=review_m11(args.candidate,args.manifest,archive_path=args.archive,
                          index=args.index,w0_schema_path=args.w0_schema,
                          w3_report_path=args.w3_report)
        if os.path.lexists(args.output):
            raise BridgeRejected('REFUSE_OVERWRITE_EXISTING_M11_EVIDENCE')
        existing._write_exclusive(args.output,result)
        print(existing.canonical({'status':result['status'],
            'requested_index':args.index,
            'unit_norm_pass':result['unit_c_compatibility']['count_pass'],
            'training_admitted':False}))
        return 0
    except (BridgeRejected,existing.GateRejected,ValueError,FileNotFoundError) as e:
        print(existing.canonical({'status':'REJECTED','error':str(e)}))
        return 2


if __name__=='__main__':
    sys.exit(main())

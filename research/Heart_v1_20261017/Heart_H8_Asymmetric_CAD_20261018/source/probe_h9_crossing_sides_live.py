"""W3 H9: serial, guarded, actual Cherchi Boolean sampling around exact proxy root.

Four fresh q[7] values: surrogate root +/- 1e-7 and +/- 1e-8.
All other coefficients are frozen. The routine does not run Newton, does not
substitute offline samples, and never grants smooth-stratum admission.

For safety, run only after the pinned Cherchi + GMP + core native extensions
have been compiled on an adequately provisioned, isolated machine.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import time
import traceback
import zipfile

from h9_same_call_capture import capture_same_call, promote_after_full_audit
from certify_h9_interior_edge_crossing import (
    SOURCE_IDS, DESIGN_IDS, archival_data, exact_line_witness, qvec,
    solve as offline_solve, need, sha, REQUEST_SHA,
)

BACKEND_PREFIX='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'
EXACT_AUDIT_REQUIRED=(
    'boundary_valid','closed','edge_manifold','vertex_manifold',
    'consistently_oriented','component_orientations_valid',
    'self_intersection_completed','self_intersection_free'
)


def native_plan(certificate):
    """Deterministic four real q samples on the model root's two sides."""
    need(certificate.get('schema')=='heart-h9-native-endpoints-and-conditional-interior-event-v1'
         and certificate.get('conditional_analytic_interior_edge_crossing_certified') is True
         and certificate.get('native_production_continuity_or_topology_certified') is False
         and certificate.get('actual_in_between_native_boolean_samples_evaluated')==0
         and certificate.get('newton_admitted') is False,
         'NOT_CERTIFIED_OFFLINE_PROXY_EVENT_CONTRACT')
    lo,hi=map(Q,certificate['surrogate_root_exact_interval'])
    need(Q('1.5e-6')<lo<hi<Q('3e-6'), 'UNEXPECTED_SURROGATE_ROOT_INTERVAL')
    center=(lo+hi)/2
    # Coarse and near roots, but never so close that archived normal
    # seed uncertainty (approx 1e-16 in c7) dominates.
    points=[(center-Q('1e-7'),'left-coarse'),
            (center-Q('1e-8'),'left-near'),
            (center+Q('1e-8'),'right-near'),
            (center+Q('1e-7'),'right-coarse')]
    need(all(Q('1.5e-6')<v<Q('3e-6') for v,_ in points),'PROBE_POINT_OUTSIDE_EVIDENCE_BRACKET')
    return [{'index':i,'side':side,'c7':float(v),'distance_from_proxy_root':str(v-center),
             'expected_proxy_event_sign':1 if side.startswith('left') else -1}
            for i,(v,side) in enumerate(points)]


def load_native_or_reject():
    try:
        import numpy as np
        import _make_it_stand as native
        import _cherchi_core_boolean as boolean
        import _cherchi_rational_moments as arithmetic
        from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
        from probe_h8_native_cherchi import request_from_frozen
        from verify_h8_exact_moments import independent_ten_raw_moments
        from audit_h9_branch_decision import load_point
        from h7_planar_patch import compare_observations, observe_packet
    except ImportError as e:
        raise RuntimeError('REAL_PINNED_NATIVE_CHERCHI_MISSING_NO_SURROGATE_FALLBACK') from e
    return (np,native,boolean,arithmetic,InProcessCherchiEvaluator,
            request_from_frozen,independent_ten_raw_moments,load_point,
            compare_observations,observe_packet)


def run(artifact:Path,certificate_path:Path,output:Path):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    report={'schema':'heart-h9-crossing-sides-live-v1',
            'status':'INCOMPLETE_NO_NEWTON',
            'new_real_native_calls':0,'finished_indices':[],
            'historical_run_id':39123384402,'historical_run_conclusion':'failure',
            'newton_admitted':False,'actual_accepted_step':False,
            'final_heart_obj_produced':False,'actual_smooth_neighborhood_certified':False}
    stage='READ_AND_INDEPENDENTLY_VERIFY_FROZEN_EVIDENCE'
    try:
        old_request,old_report,old_samples=archival_data(artifact)
        proof=offline_solve(artifact)
        saved=json.loads(Path(certificate_path).read_bytes())
        need(saved==proof,'CERTIFICATE_CONTENT_DIFFERS_FROM_RECOMPUTED_REAL_ARCHIVE_PROOF')
        plan=native_plan(proof)
        report['plan']=plan
        report['source_archive_sha256']=proof['artifact_sha256']
        report['certified_analytic_proxy_root']=proof['surrogate_root_exact_interval']
        stage='IMPORT_REAL_PINNED_NATIVE_CHERCHI'
        (np,native,boolean,arithmetic,InProcessCherchiEvaluator,
         request_from_frozen,independent_ten_raw_moments,load_point,
         compare_observations,observe_packet)=load_native_or_reject()
        report['binary_hashes']={key:sha256(Path(mod.__file__).read_bytes()).hexdigest()
                                 for key,mod in {'core':native,'boolean':boolean,'arithmetic':arithmetic}.items()}
        report['native_binary_identical_to_h8f']={
            'core':report['binary_hashes']['core']==old_report['actual_native_sha256'],
            'boolean':report['binary_hashes']['boolean']==old_report['actual_cherchi_sha256'],
            'arithmetic':report['binary_hashes']['arithmetic']==old_report['actual_arithmetic_sha256']}
        with tempfile.TemporaryDirectory(prefix='heart-h9-frozen-request-') as temp, zipfile.ZipFile(artifact) as z:
            frozen=z.read('artifacts/h8-request/prepared-request.json')
            need(sha(frozen)==REQUEST_SHA,'FROZEN_REQUEST_CHANGED')
            request_path=Path(temp)/'prepared-request.json'
            request_path.write_bytes(frozen)
            request,settings,_=request_from_frozen(request_path)
            _,left_material,left_obs=load_point(z,59,old_request['request'])
            _,right_material,right_obs=load_point(z,60,old_request['request'])
            engine=InProcessCherchiEvaluator(request,settings,
                normalization={'origin':[0.,0.,0.],'L':1.},
                rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',
                fixed_boundary_reuse=False,integral_profile='EXACT_GMP_V1',
                branch_identity_policy='SOURCE_FEATURE_BRANCH_V2')
            need(engine.backend_identity.startswith(BACKEND_PREFIX),'NOT_PINNED_CHERCHI_BACKEND')
            base_q=np.asarray(old_report['target_q'],dtype=np.float64)
            need(base_q.shape==(10,) and np.isfinite(base_q).all(),'INVALID_FROZEN_BASE_QUADRIC')
            design=[qvec(old_request['request']['design_vertices'][i]) for i in DESIGN_IDS]
            results=[]
            for item in plan:
                stage=f"REAL_CHERCHI_INPROCESS_CALL_{item['index']}"
                start=time.perf_counter()
                q=base_q.copy();q[7]=item['c7']
                need(all(q[j]==base_q[j] for j in range(10) if j!=7),
                     'NON_EVENT_COEFFICIENT_CHANGED')
                value=engine(q)
                material=engine.material(q)
                engine.validate_same_call_material(material,q,request)
                # Preserve this real same-call packet immediately. Strict boundary,
                # Fraction integration, and exact branch checks below may fail or
                # time out. Until they pass, it remains `unverified-*` and MUST
                # NOT count as a completed new native sample.
                stage=f"PRESERVE_UNVERIFIED_TRUE_SAME_CALL_PACKET_{item['index']}"
                capture=capture_same_call(output,index=item['index'],side=item['side'],
                    coefficients=q.tolist(),material=material,
                    backend_identity=value['boolean_backend_identity'])
                need(value['boolean_backend_identity'].startswith(BACKEND_PREFIX),
                     'NEW_NATIVE_BACKEND_MISMATCH')
                stage=f"STRICT_EXACT_NATIVE_BOUNDARY_{item['index']}"
                coordinates=material['variable_rational_vertices']
                faces=np.asarray(material['variable_faces'],dtype=np.int32)
                facts=dict(native.audit_exact_rational_triangle_boundary(
                    coordinates,faces,'AnyNonzero'))
                need(all(facts.get(k) is True for k in EXACT_AUDIT_REQUIRED)
                     and not facts.get('intersecting_pairs')
                     and not facts.get('degenerate_faces')
                     and not facts.get('intersection_error'),
                     'STRICT_NATIVE_EXACT_BOUNDARY_FAILED')
                stage=f"INDEPENDENT_EXACT_TEN_MOMENT_CHECK_{item['index']}"
                independently=independent_ten_raw_moments(coordinates,faces.tolist())
                ten=np.asarray([float(x) for x in independently],dtype=np.float64)
                reported=np.asarray(value['variable_raw_moments'],dtype=np.float64)
                jac=np.asarray(value['moment_jacobian'],dtype=np.float64)
                need(ten.shape==(10,) and reported.shape==(10,) and jac.shape==(10,10)
                     and np.isfinite(ten).all() and np.isfinite(reported).all()
                     and np.isfinite(jac).all(),'MOMENTS_OR_JACOBIAN_INVALID')
                scaled_error=float(np.max(np.abs(ten-reported)/np.maximum(1.,np.abs(reported))))
                need(scaled_error<=1e-10,'INDEPENDENT_NEW_REAL_MOMENT_DISAGREEMENT')
                stage=f"REAL_NATIVE_EXACT_BRANCH_PROVENANCE_{item['index']}"
                mproof=material['material_proof']
                need(mproof['schema']=='cherchi-same-call-material-v1','MISSING_SAME_CALL_MATERIAL_PROOF')
                packet={'backend':'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1',
                        'exact_vertices':mproof['exact_vertices'],
                        'faces':material['variable_faces'],
                        'construction_records':mproof['construction_records']}
                observation=observe_packet(packet,old_request['request']['design_vertices'],
                    old_request['request']['design_faces'],material['quadric_source_vertices'],
                    material['quadric_source_faces'])
                compare_left=compare_observations(left_obs,observation)
                compare_right=compare_observations(right_obs,observation)
                source=[qvec(material['quadric_source_vertices'][i]) for i in SOURCE_IDS]
                segment=exact_line_witness(*source,*design)
                need(0<segment['source_segment_parameter']<1
                     and 0<segment['design_segment_parameter']<1,
                     'NEW_NATIVE_EDGE_PROJECTION_NOT_INTERIOR')
                det_sign=(segment['determinant']>0)-(segment['determinant']<0)
                stage=f"ARCHIVE_NEW_REAL_SAME_CALL_MATERIAL_{item['index']}"
                name=f"side-{item['index']:02d}-{item['side']}"
                # The exact already-captured gzip bytes are only promoted
                # after all native geometry, mass and provenance gates pass.
                fact={**item,'q':q.tolist(),'newton_admitted':False,
                      'actual_accepted_step':False,
                      'native_event_sign':det_sign,
                      'agrees_with_analytic_proxy_sign':det_sign==item['expected_proxy_event_sign'],
                      'native_source_param':float(segment['source_segment_parameter']),
                      'native_design_param':float(segment['design_segment_parameter']),
                      'native_moment_jacobian_column7':jac[:,7].tolist(),
                      'independent_ten_mass_moments':ten.tolist(),
                      'independent_scaled_moment_error':scaled_error,
                      'native_geometry_valid':True,
                      'native_source_triangles_match_left':material['quadric_source_faces']==left_material['quadric_source_faces'],
                      'native_source_triangles_match_right':material['quadric_source_faces']==right_material['quadric_source_faces'],
                      'symbolic_vs_left':compare_left,
                      'symbolic_vs_right':compare_right,
                      'native_material_geometry_hash':material['geometry_hash'],
                      'native_feature_branch_hash':material['topology_hash'],
                      'material_sha256':capture['archive_sha256'],
                      'vertex_count':len(coordinates),'face_count':len(faces),
                      'elapsed_seconds':time.perf_counter()-start}
                promote_after_full_audit(output,capture,fact)
                results.append(fact)
                report['new_real_native_calls']+=1
                report['finished_indices'].append(item['index'])
                print('H9_REAL_NATIVE_SIDE_PROBE',item['index'],item['side'],
                      det_sign,compare_left['status'],compare_right['status'],flush=True)
        report['all_native_event_signs_match_proxy']=all(r['agrees_with_analytic_proxy_sign'] for r in results)
        report['all_native_source_connectivity_stable']=all(
             r['native_source_triangles_match_left'] and r['native_source_triangles_match_right'] for r in results)
        report['status']='FOUR_FRESH_REAL_SAMPLES_EVALUATED_NOT_SMOOTH_OR_NEWTON_CERTIFIED'
        (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        return report
    except Exception as error:
        report.update(status='FAILED_NO_NEWTON_ADMISSION',failed_stage=stage,
                      error=f'{type(error).__name__}: {error}',
                      traceback=traceback.format_exc(),newton_admitted=False)
        (output/'failure.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--certificate',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();run(a.artifact,a.certificate,a.output)


if __name__=='__main__':main()

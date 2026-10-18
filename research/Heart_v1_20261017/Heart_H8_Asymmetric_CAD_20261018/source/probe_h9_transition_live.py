"""Opt-in REAL native Cherchi microprobe of archived sample-60 edge event.

Requires the same pinned H8f native dependencies. Never uses a fake geometry
fallback and NEVER approves Newton based on finite samples. Serial CPU only.
No GitHub workflow changes or automatic full native compilation.
"""
from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import tempfile
import time
import traceback
import zipfile

from audit_h9_branch_decision import (
    BACKEND, REQUEST_PATH, digest, exact_point, det4, fraction_witness,
    load_point, require
)
from locate_h9_transition import locate, DESIGN_EDGE, SOURCE_EDGE

AUDIT_KEYS = ('boundary_valid','closed','edge_manifold','vertex_manifold',
              'consistently_oriented','component_orientations_valid',
              'self_intersection_completed','self_intersection_free')


def module_digest(module):
    return sha256(Path(module.__file__).read_bytes()).hexdigest()


def safe_failure(out: Path, report: dict, stage: str, error: BaseException):
    report.update(status='FAILED_NO_NEWTON_ADMISSION', failed_stage=stage,
                  error=f'{type(error).__name__}: {error}',
                  newton_admitted=False, traceback=traceback.format_exc())
    (out/'failure.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')


def live_probe(artifact: Path, output: Path):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    report=dict(schema='heart-h9-native-microprobe-v1',status='INCOMPLETE',
                provenance='REAL_NATIVE_CHERCHI_ONLY_NO_SYNTHETIC_BACKEND',
                native_calls_completed=0, completed_indices=[],newton_admitted=False,
                continuous_smooth_neighborhood_proven=False,
                final_heart_obj_produced=False)
    stage='VERIFY_FROZEN_EVENT_BRACKET'
    try:
        bracket=locate(artifact)
        delta=sorted(bracket['live_probe_candidate_c7'])
        require(len(delta)==4 and len(set(delta))==4 and
                all(1.5e-6 < d < 3e-6 and math.isfinite(d) for d in delta),
                'INVALID_INTERIOR_PROBE_COORDINATES')
        stage='LOAD_NATIVE_CHERCHI_BINARY'
        try:
            import numpy as np
            import _make_it_stand as native
            import _cherchi_core_boolean as boolean
            import _cherchi_rational_moments as arithmetic
            from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
            from probe_h8_native_cherchi import request_from_frozen
            from verify_h8_exact_moments import independent_ten_raw_moments
            from h7_planar_patch import observe_packet, compare_observations
        except ImportError as error:
            raise RuntimeError('REAL_NATIVE_CHERCHI_DEPENDENCIES_UNAVAILABLE_NO_FALLBACK') from error
        report.update(actual_native_sha256=module_digest(native),
                      actual_cherchi_sha256=module_digest(boolean),
                      actual_arithmetic_sha256=module_digest(arithmetic),
                      frozen_81_point_artifact_sha256=bracket['artifact_zip_sha256'],
                      planned_c7=delta)
        with zipfile.ZipFile(artifact) as z, tempfile.TemporaryDirectory(prefix='h9-frozen-request-') as temp:
            request_path=Path(temp)/'prepared-request.json'
            frozen_bytes=z.read(REQUEST_PATH)
            require(digest(frozen_bytes)==bracket['request_sha256'],'FROZEN_REQUEST_CHANGED')
            request_path.write_bytes(frozen_bytes)
            document=json.loads(frozen_bytes)
            request,settings,_=request_from_frozen(request_path)
            p59,m59,obs59=load_point(z,59,document['request'])
            p60,m60,obs60=load_point(z,60,document['request'])
            _,_,baseline=load_point(z,0,document['request'])
            engine=InProcessCherchiEvaluator(request,settings,normalization={'origin':[0.,0.,0.],'L':1.},
                rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',fixed_boundary_reuse=False,
                integral_profile='EXACT_GMP_V1',branch_identity_policy='SOURCE_FEATURE_BRANCH_V2')
            require(engine.backend_identity.startswith(BACKEND),'UNPINNED_NATIVE_CHERCHI_BACKEND')
            base_q=np.asarray(json.loads(z.read('artifacts/h8f-all81-points/report.json'))['target_q'],dtype=np.float64)
            require(base_q.shape==(10,) and np.isfinite(base_q).all(),'INVALID_BASE_Q')
            design=document['request']['design_vertices']
            design_edge=[exact_point(design[j]) for j in DESIGN_EDGE]
            for i,c7 in enumerate(delta):
                stage=f'REAL_CHERCHI_SAMPLE_{i}'
                start=time.perf_counter()
                q=base_q.copy(); q[7]=c7
                value=engine(q)
                material=engine.material(q)
                engine.validate_same_call_material(material,q,request)
                require(str(value.get('boolean_backend_identity','')).startswith(BACKEND),
                        'UNPINNED_RESULT_BACKEND')
                stage=f'EXACT_NATIVE_AUDIT_{i}'
                coords=material['variable_rational_vertices']
                faces=np.asarray(material['variable_faces'],dtype=np.int32)
                audit=dict(native.audit_exact_rational_triangle_boundary(coords,faces,'AnyNonzero'))
                require(all(audit.get(k) is True for k in AUDIT_KEYS)
                        and not audit.get('intersecting_pairs') and not audit.get('degenerate_faces')
                        and not audit.get('intersection_error'), 'STRICT_RATIONAL_MATERIAL_BOUNDARY_REJECTED')
                stage=f'INDEPENDENT_EXACT_TEN_MOMENTS_{i}'
                moments=independent_ten_raw_moments(coords,faces.tolist())
                independent=np.asarray([float(x) for x in moments],dtype=np.float64)
                reported=np.asarray(value['variable_raw_moments'],dtype=np.float64)
                jac=np.asarray(value['moment_jacobian'],dtype=np.float64)
                require(independent.shape==(10,) and reported.shape==(10,)
                        and jac.shape==(10,10) and np.isfinite(jac).all()
                        and np.isfinite(independent).all() and np.isfinite(reported).all(),
                        'INVALID_NEW_NATIVE_MOMENTS_OR_JACOBIAN')
                moment_err=float(np.max(np.abs(reported-independent)/np.maximum(1.,np.abs(reported))))
                require(moment_err<=1e-10, 'NEW_NATIVE_EXACT_MOMENT_INDEPENDENT_CHECK_FAILED')
                stage=f'SYMBOLIC_FEATURE_AND_EDGE_EVENT_{i}'
                proof=material['material_proof']
                require(proof['schema']=='cherchi-same-call-material-v1','NO_REAL_CONSTRUCTION_RECORDS')
                packet={'backend':'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1',
                        'exact_vertices':proof['exact_vertices'], 'faces':material['variable_faces'],
                        'construction_records':proof['construction_records']}
                observation=observe_packet(packet,design,document['request']['design_faces'],
                                           material['quadric_source_vertices'],material['quadric_source_faces'])
                relation59=compare_observations(obs59,observation)
                relation60=compare_observations(obs60,observation)
                relation_base=compare_observations(baseline,observation)
                source=[exact_point(material['quadric_source_vertices'][j]) for j in SOURCE_EDGE]
                determinant=det4(source[0],source[1],design_edge[0],design_edge[1])
                require(determinant!=0,'EXACT_EVENT_ON_SAMPLE_REQUIRES_SEPARATE_DEGENERACY_AUDIT')
                stage=f'ARCHIVE_SAME_CALL_REAL_MATERIAL_{i}'
                name=f'probe-{i:02d}'
                archive=output/(name+'-material.json.gz')
                with gzip.open(archive,'wt',encoding='utf-8') as out:
                    json.dump(material,out,sort_keys=True,allow_nan=False)
                saved=dict(index=i,c7=float(c7),q=q.tolist(),
                    native_boundary_passed=True,independent_moment_max_scaled_error=moment_err,
                    independent_variable_ten_moments=independent.tolist(),
                    moment_jacobian_column7=jac[:,7].tolist(),
                    edge_event_exact_determinant=fraction_witness(determinant),
                    semantic_comparison_to_base=relation_base,
                    semantic_comparison_to_left_sample59=relation59,
                    semantic_comparison_to_right_sample60=relation60,
                    vertex_count=len(coords),face_count=len(faces),
                    material_archive_sha256=sha256(archive.read_bytes()).hexdigest(),
                    feature_branch_hash=value['topology_hash'],
                    material_geometry_hash=value['geometry_hash'],
                    elapsed_seconds=time.perf_counter()-start,
                    newton_admitted=False)
                (output/(name+'.json')).write_text(json.dumps(saved,indent=2,allow_nan=False)+'\n')
                report['native_calls_completed']+=1
                report['completed_indices'].append(i)
                print('H9_REAL_CHERCHI_MICROPROBE',i,c7,relation_base['status'],flush=True)
        report.update(status='FOUR_NEW_REAL_NATIVE_POINTS_FINITE_ONLY_NOT_NEWTON',
                      actual_continuous_event_localized=False,
                      qualified_branch_neighborhood=False,
                      newton_admitted=False)
        (output/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        return report
    except Exception as error:
        safe_failure(output,report,stage,error)
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    live_probe(args.artifact,args.output)

if __name__=='__main__':
    main()

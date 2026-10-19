"""W0 M9: independent review of the real, FAILED H8f 81-point Cherchi ZIP.

Read-only, SHA-pinned. Verifies all 81 raw same-call packets and source
combinatorics; exact Fraction moments can run for focus points or all 81.
No smooth neighborhood, material partition, author CAD or Newton certification.

From repository root:
  python -m research.NeuralMoments.contracts.real_h8f_81_m9 \
      --archive /path/to/original-81.zip --output /new/path/m9.json --exact-mode all
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
import gzip
import json
import math
from pathlib import Path
import re
import time
from zipfile import ZipFile

import numpy as np

try:
    from .real_h8e_archive_m8 import (ArchiveAuditError, require, digest_bytes,
        canonical_digest, read_json, open_pinned, read_member,
        check_closed_indexed_surface, exact_rational_ten_moments,
        target_fixed_moments)
except ImportError:
    from real_h8e_archive_m8 import (ArchiveAuditError, require, digest_bytes,
        canonical_digest, read_json, open_pinned, read_member,
        check_closed_indexed_surface, exact_rational_ten_moments,
        target_fixed_moments)

ARCHIVE_SHA256 = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
REPORT_SHA256 = '28e5a641da153b08a7f15f4abb87336c797f1e85b6f2742fc025274c231f53c5'
CLASSIFICATION_SHA256 = 'f82801aa26d3f4228b8cb68f08abab5ef45458cc2368703e9187e0745662d6c5'
REQUEST_SHA256 = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
SOURCE_PREFIX = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'
REPORT_PREFIX = 'artifacts/h8f-all81-points/'
STABLE = 'SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'
CHANGED = 'CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE'
RUN_ID = 39123384402  # Original GitHub CI: failure. Never rewrite the status.
ARTIFACT_ID = 12135528290
FROZEN_SHA = '0bcc187b3005478baa586a6d6f450e73811ca342'
FOCUS_POINTS = (0, 59, 60)


def normalized_constraint(record):
    """Canonicalize only the mathematical LPI/TPI operand symmetries.

    Never collapse different input plane identities, source triangles,
    changed sides of an edge event, or reverse oriented material faces.
    """
    require(isinstance(record,dict), 'INVALID_CONSTRUCTION_RECORD')
    kind=record.get('point_type'); expected={'EXPLICIT3D':1,'LPI':5,'TPI':9,'LNC':2}
    require(kind in expected, 'UNSUPPORTED_CONSTRUCTION_KIND')
    operands=record.get('operands')
    require(isinstance(operands,list) and len(operands)==expected[kind], 'BAD_CONSTRUCTION_ARITY')
    refs=[]
    for op in operands:
        require(isinstance(op,dict) and op.get('status')=='UNIQUE', 'UNRESOLVED_CONSTRUCTION_OPERAND')
        vertices=op.get('source_vertices')
        require(isinstance(vertices,list) and len(vertices)==1, 'NONUNIQUE_CONSTRUCTION_OPERAND')
        x=vertices[0]
        require(isinstance(x,dict) and type(x.get('input_object')) is int and
                x['input_object'] in (0,1) and type(x.get('input_vertex')) is int and
                x['input_vertex']>=0,'INVALID_CONSTRUCTION_SOURCE_REF')
        refs.append((x['input_object'],x['input_vertex']))
    if kind=='LPI':
        return (kind,tuple(sorted(refs[:2])),tuple(sorted(refs[2:])))
    if kind=='TPI':
        return (kind,tuple(sorted(tuple(sorted(refs[i:i+3])) for i in (0,3,6))))
    return (kind,tuple(refs))


def normalized_features(material):
    proof=material.get('material_proof')
    require(isinstance(proof,dict) and proof.get('schema')=='cherchi-same-call-material-v1',
            'MISSING_NATIVE_CONSTRUCTION_PROOF')
    records=proof.get('resolved_construction_records')
    require(isinstance(records,list) and len(records)==len(material.get('variable_rational_vertices',[])),
            'CONSTRUCTION_RECORD_COUNT_MISMATCH')
    for i,r in enumerate(records):
        require(r.get('vertex_index')==i,'NONSEQUENTIAL_CONSTRUCTION_RECORD')
    signatures=tuple(normalized_constraint(rec) for rec in records)
    require(len(set(signatures))==len(signatures), 'DUPLICATE_CONSTRUCTION_VERTEX_IDENTITY')
    return signatures


def oriented_face_key(face, features):
    require(isinstance(face,list) and len(face)==3 and
            all(type(x) is int and 0<=x<len(features) for x in face) and
            len(set(face))==3,'INVALID_INDEXED_FACE')
    tri=tuple(features[x] for x in face)
    return min(tri,tri[1:]+tri[:1],tri[2:]+tri[:2])


def oriented_triangle_multiset(material, features):
    return Counter(oriented_face_key(face, features) for face in material['variable_faces'])


def construction_transition(base, trial):
    base_features=normalized_features(base)
    trial_features=normalized_features(trial)
    require(len(base_features)==len(trial_features), 'CHANGED_VERTEX_COUNT')
    changed_positions=[i for i,(a,b) in enumerate(zip(base_features,trial_features)) if a!=b]
    before=Counter(base_features);after=Counter(trial_features)
    removed=list((before-after).elements());added=list((after-before).elements())
    a=oriented_triangle_multiset(base,base_features)
    b=oriented_triangle_multiset(trial,trial_features)
    absent=a-b;introduced=b-a
    return dict(changed_vertex_indices=changed_positions,
                removed_features=removed,added_features=added,
                removed_oriented_triangles=sum(absent.values()),
                added_oriented_triangles=sum(introduced.values()),
                same_source_faces=base['quadric_source_faces']==trial['quadric_source_faces'],
                same_raw_material_face_indexing=base['variable_faces']==trial['variable_faces'],
                normalized_symbolic_triangle_identity=(not absent and not introduced))


def five_point_verification(points,report):
    J=np.asarray(report.get('analytic_10_by_10_jacobian'),dtype=np.float64)
    require(J.shape==(10,10) and np.isfinite(J).all(),'BAD_ANALYTIC_JACOBIAN')
    require(len(points)==81 and len(report.get('numeric_checks',[]))==30,
            'INCOMPLETE_NUMERICAL_STENCILS')
    baseline=points[0]; q=np.asarray(baseline['coefficients'],dtype=float)
    checks=[]; hash_stable_count=0
    for row in report['numeric_checks']:
        col=row.get('column');positions=row.get('sample_indices')
        require(type(col) is int and 0<=col<10 and isinstance(positions,list) and
                len(positions)==5 and len(set(positions))==5 and
                all(type(p) is int and 0<=p<81 for p in positions), 'INVALID_NUMERICAL_LAYOUT')
        X=np.asarray([points[i]['coefficients'][col]-q[col] for i in positions],dtype=float)
        require(np.isfinite(X).all() and len(set(X.tolist()))==5 and np.max(np.abs(X))>0,
                'INVALID_DIFFERENCE_ABSCISSAE')
        scale=np.max(np.abs(X))
        V=np.vstack([(X/scale)**k for k in range(5)])
        weights=np.linalg.solve(V,np.array([0.,1.,0.,0.,0.]))/scale
        values=np.asarray([points[i]['independent_variable_raw_moments'] for i in positions],dtype=float)
        require(values.shape==(5,10) and np.isfinite(values).all(),'INVALID_STENCIL_MOMENT')
        fd=weights@values
        error=float(np.max(np.abs(fd-J[:,col])/np.maximum(1.,np.abs(J[:,col]))))
        stable=all(points[i]['feature_branch_hash']==baseline['feature_branch_hash'] for i in positions)
        require(abs(error-row['max_scaled_derivative_error'])<=5e-9,
                'NUMERICAL_REPORT_NOT_REPRODUCED')
        require(row.get('numerical_passed') is (error <= 1e-6), 'NUMERICAL_STATUS_FORGED')
        require(row.get('feature_hash_stable') is stable,'HASH_STABILITY_STATUS_FORGED')
        hash_stable_count+=int(stable)
        checks.append(dict(column=col,step=row['step'],error=error,feature_hash_stable=stable))
    require(sorted((x['column'],x['step']) for x in checks)==
            sorted((c,h) for c in range(10) for h in (3e-6,1.5e-6,7.5e-7)),
            'MISSING_OR_DUPLICATE_COLUMN_STENCIL')
    null_norm=float(np.linalg.norm(J@q))
    require(abs(null_norm-report['scale_null_direction_norm'])<=1e-12,
            'QUADRIC_SCALING_NULL_DIRECTION_MISMATCH')
    return {'checked_stencils':len(checks),
            'max_scaled_error':max(x['error'] for x in checks),
            'original_feature_hash_unstable_stencils':len(checks)-hash_stable_count,
            'scale_null_direction_norm':null_norm}


def _independent_exact_one(path, i, density):
    with ZipFile(path) as z:
        b=read_member(z,REPORT_PREFIX+f'point-{i:03d}-material.json.gz',max_bytes=4_000_000)
        m=read_json(gzip.decompress(b))
        exact=exact_rational_ten_moments(m['variable_rational_vertices'],m['variable_faces'],density)
        stored=np.asarray(m['variable_raw_moments'],dtype=float)
        error=float(np.max(np.abs(np.asarray([float(v) for v in exact])-stored)))
        require(error<=1e-10,'EXACT_RATIONAL_MOMENT_MISMATCH')
        return i,error


def exact_reintegrate(path,density,indices,workers=1):
    """Independent Fraction reconstruction; each sample re-reads pinned archive."""
    require(1 <= workers <= 4, 'EXCESSIVE_REINTEGRATION_WORKERS')
    results={}
    if workers==1:
        for i in indices:
            k,err=_independent_exact_one(path,i,density)
            results[k]=err
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            fs=[pool.submit(_independent_exact_one,path,i,density) for i in indices]
            for f in as_completed(fs):
                k,err=f.result()
                results[k]=err
    return {str(k):results[k] for k in sorted(results)}


def audit(archive, *, exact_mode='focus', workers=1):
    start=time.monotonic()
    archive=Path(archive)
    require(exact_mode in ('none','focus','all'),'UNSUPPORTED_EXACT_MODE')
    require(archive.is_file() and not archive.is_symlink(),'INVALID_REAL_ZIP_FILE')
    with open_pinned(archive,ARCHIVE_SHA256) as z:
        names=z.namelist();require(len(names)==183,'UNEXPECTED_ARCHIVE_FILE_COUNT')
        r_raw=read_member(z,REPORT_PREFIX+'report.json')
        c_raw=read_member(z,'artifacts/h8f-81-exact-construction-classification.json')
        q_raw=read_member(z,'artifacts/h8-request/prepared-request.json',max_bytes=10_000_000)
        require(digest_bytes(r_raw)==REPORT_SHA256,'REPORT_DIGEST_MISMATCH')
        require(digest_bytes(c_raw)==CLASSIFICATION_SHA256,'CLASSIFICATION_DIGEST_MISMATCH')
        require(digest_bytes(q_raw)==REQUEST_SHA256,'FROZEN_REQUEST_DIGEST_MISMATCH')
        report=read_json(r_raw);classification=read_json(c_raw);request=read_json(q_raw)
        require(report['schema']=='heart-h8e-real-cherchi-jacobian-pilot-v1' and
                report['columns_requested']==list(range(10)) and
                report['completed_samples']==report['production_cherchi_calls']==81 and
                report['planned_sample_count']==81 and
                report['all_numerical_checks_passed'] is True and
                report['all_same_call_material_snapshots_sha256_saved'] is True,
                'INCOMPLETE_REAL_81_NATIVE_ARCHIVE')
        for key in ('qualified_branch_neighborhood','formal_newton_converged',
                    'objective_stationarity_certified','original_author_cad'):
            require(report.get(key) is False,'PROMOTED_UNSUPPORTED_H8F_CLAIM:'+key)
        require(report['all_tested_stencils_same_feature_hash'] is False,
                'ORIGINAL_FAILURE_FLAG_MISSING')
        require(classification['source_report_sha256']==REPORT_SHA256 and
                classification['request_sha256']==REQUEST_SHA256 and
                classification['complete_material_snapshots_verified']==81 and
                classification['exact_plane_diagnostics_resolved_points']==81 and
                classification['exact_plane_diagnostics_unresolved_points']==0 and
                classification['certified_smooth_neighborhood'] is False and
                classification['certified_newton_direction'] is False,
                'UNBOUND_OR_PROMOTED_CLASSIFICATION')
        require(classification['classifications']=={STABLE:79,CHANGED:1},
                'HISTORICAL_CLASSIFICATION_DRIFT')
        indexed={x['index']:x for x in classification['comparisons']}
        require(len(indexed)==80 and set(indexed)==set(range(1,81)),
                'MISSING_CLASSIFIED_POINTS')
        points=[];baseline=None;baseline_features=None;anomaly=[];source_sha=None
        fixed=target_fixed_moments(request['request']['fixed_shell_moments'],
                                   request['request']['target_origin'],request['request']['target_axes'])
        max_fixed=0.; edges_count=0; raw_hash_changed=0
        for i in range(81):
            n=REPORT_PREFIX+f'point-{i:03d}'
            record=read_json(read_member(z,n+'.json'))
            packed=read_member(z,n+'-material.json.gz',max_bytes=4_000_000)
            require(digest_bytes(packed)==record['exact_same_call_material_archive_sha256'],
                    'MATERIAL_GZIP_DIGEST_MISMATCH')
            m=read_json(gzip.decompress(packed))
            require(record['index']==i and
                    m['quadric_coefficients']==record['coefficients'] and
                    m['geometry_hash']==record['material_geometry_hash'] and
                    m['topology_hash']==record['feature_branch_hash'] and
                    len(m['variable_faces'])==record['triangle_count'] and
                    len(m['variable_rational_vertices'])==record['vertex_count'] and
                    len(m['material_proof']['exact_vertices'])==record['vertex_count'] and
                    m['material_proof']['schema']=='cherchi-same-call-material-v1',
                    'PACKET_POINT_IDENTITY_MISMATCH')
            require(m['boolean_backend_identity']==record['native_boolean_backend']==
                    SOURCE_PREFIX+report['actual_cherchi_sha256'],'NONPINNED_CHERCHI_BACKEND')
            require(canonical_digest({'vertices':m['material_proof']['exact_vertices'],
                                       'faces':m['variable_faces']})==m['geometry_hash'],
                    'RECOMPUTED_MATERIAL_GEOMETRY_HASH_MISMATCH')
            require(canonical_digest({'vertices':m['quadric_source_vertices'],
                                      'faces':m['quadric_source_faces'],
                                      'coefficients':m['quadric_coefficients']})==m['quadric_source_identity'],
                    'RECOMPUTED_QUADRIC_SOURCE_HASH_MISMATCH')
            count=check_closed_indexed_surface(m['variable_faces'],record['vertex_count'])
            require(count>0 and record['exact_native_material_boundary_passed'] is True,
                    'MISSING_NATIVE_AND_INDEPENDENT_CLOSURE')
            edges_count+=1
            actual=np.asarray(m['variable_raw_moments'],dtype=float)
            meta=np.asarray(record['independent_variable_raw_moments'],dtype=float)
            prod=np.asarray(record['production_variable_raw_moments'],dtype=float)
            total=np.asarray(m['raw_moments'],dtype=float)
            require(actual.shape==meta.shape==prod.shape==total.shape==(10,) and
                    np.isfinite(actual).all() and np.isfinite(meta).all() and
                    np.isfinite(prod).all() and np.isfinite(total).all(),
                    'INVALID_MOMENT_RECORD')
            require(np.max(np.abs(actual-meta))<=1e-10 and
                    np.max(np.abs(actual-prod))<=1e-10 and
                    np.max(np.abs(total-np.asarray(record['full_raw_moments'])))<=1e-12,
                    'WRONG_TEN_MOMENT_LINKAGE')
            max_fixed=max(max_fixed,float(np.max(np.abs((total-actual)-fixed))))
            require(max_fixed<=1e-10,'FIXED_MOMENT_FRAME_MISMATCH')
            require(m.get('derivative_defined') is True and
                    np.asarray(m.get('moment_jacobian'),dtype=float).shape==(10,10),
                    'JACOBIAN_ATTACHMENT_UNAVAILABLE')
            features=normalized_features(m)
            if i==0:
                baseline=m;baseline_features=features;source_sha=m['quadric_source_identity']
            else:
                changed=sum(a!=b for a,b in zip(baseline_features,features))
                expected=CHANGED if changed else STABLE
                require(indexed[i]['status']==expected,'INDEPENDENT_FEATURE_CLASSIFICATION_MISMATCH')
                if changed:anomaly.append({'index':i,'changed_vertex_positions':changed})
            points.append(record)
            raw_hash_changed+=int(record['feature_branch_hash']!=points[0]['feature_branch_hash'])
            if i==60:
                proof60=construction_transition(baseline,m)
                # Confirm neighboring points (59, 60) from exactly same signed-source run.
                require(proof60['changed_vertex_indices']==[8043,8044,8045,8046,8047],
                        'POINT60_AFFECTED_VERTICES_CHANGED')
                require(len(proof60['removed_features'])==len(proof60['added_features'])==2,
                        'POINT60_SOURCE_FEATURE_SET_NOT_REPRODUCED')
                require(proof60['removed_oriented_triangles']==proof60['added_oriented_triangles']==17,
                        'POINT60_ORIENTED_FACE_CHANGE_NOT_REPRODUCED')
                require(proof60['same_source_faces'] is True, 'POINT60_SOURCE_FACES_CHANGED')
        require(anomaly==[{'index':60,'changed_vertex_positions':5}],
                'POINT60_CONSTRUCTION_TRANSITION_NOT_REPRODUCED')
        require(raw_hash_changed==report['changed_feature_hash_points'],
                'NATIVE_FEATURE_HASH_CHANGE_COUNT_MISMATCH')
        require(report['complete_eighty_one_samples'] is False,
                'HISTORIC_81_POINT_UNCERTIFIED_STATUS_CHANGED')
        numerical=five_point_verification(points,report)
        require(numerical['checked_stencils']==30 and numerical['max_scaled_error']<=1e-6,
                'REAL_FINITE_DIFFERENCE_FAILURE')
        require(numerical['original_feature_hash_unstable_stencils']==9,
                'ORIGINAL_H8F_FAILURE_NOT_PRESERVED')
    sample_ids=tuple(range(81)) if exact_mode=='all' else FOCUS_POINTS if exact_mode=='focus' else ()
    exact=exact_reintegrate(archive,request['request']['material_density'],sample_ids,workers=workers)
    return dict(schema='W0_M9_REAL_H8F_81_ARCHIVE_AUDIT_V1',
                scope='RECONSTRUCTED_H8_NONAUTHOR_CAD_FINITE_POINTS_ONLY',
                github_workflow_run=RUN_ID,github_original_workflow_conclusion='failure',
                github_artifact_id=ARTIFACT_ID,github_head_sha=FROZEN_SHA,
                sha256_archive=ARCHIVE_SHA256,sha256_report=REPORT_SHA256,
                sha256_classification=CLASSIFICATION_SHA256,
                original_point_count=81,checked_packet_identities=81,
                independent_closed_oriented_surfaces=edges_count,
                independent_feature_classification={STABLE:79,CHANGED:1},
                original_native_feature_hash_changed_points=raw_hash_changed,
                original_native_failed_stencils=9,
                anomaly_point=60,point60_witness=dict(proof60,stable_neighbor_q7=points[59]['coefficients'][7],
                            changed_sample_q7=points[60]['coefficients'][7],
                            source_face_indices_stable=True),
                numerical=numerical,
                independent_fixed_moment_max_abs_error=max_fixed,
                fraction_reintegrated_sample_count=len(exact),
                fraction_reintegrated_per_sample_max_abs_error=exact,
                fraction_max_abs_error=max(exact.values()) if exact else None,
                artifact_numeric_moments_returned=True,
                certified_smooth_neighborhood=False,certified_newton_direction=False,
                newton_converged=False,training_admissible=False,
                evidence_meaning='REAL_FINITE_POINT_COMBINATORICS_NOT_CONTINUUM_OR_TERMINAL_CERTIFICATION',
                elapsed_seconds=time.monotonic()-start)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--exact-mode',choices=('none','focus','all'),default='focus')
    parser.add_argument('--workers',type=int,default=1)
    args=parser.parse_args(argv)
    # Never overwrite evidence, including a previous failure report.
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError('W0_M9_DO_NOT_OVERWRITE_EVIDENCE')
    result=audit(args.archive,exact_mode=args.exact_mode,workers=args.workers)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False)
        stream.write('\n')
    print('W0_M9_REAL_81_FINITE_POINT_REVIEW_COMPLETE_POINT60_CHANGE_NOT_NEWTON')
    print(json.dumps({'samples':result['original_point_count'],
          'independent_exact_moments':result['fraction_reintegrated_sample_count'],
          'anomaly_index':result['anomaly_point'],
          'finite_max_scaled_error':result['numerical']['max_scaled_error'],
          'newton_converged':False},sort_keys=True))
    return 0


if __name__=='__main__':
    raise SystemExit(main())

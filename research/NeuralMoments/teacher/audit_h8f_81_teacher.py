"""W2 M9: offline provenance and candidate-label audit for historical H8f 81 points.

Only archived Cherchi material is read. This program cannot certify smoothness,
start native Cherchi, or produce admitted Jacobian training labels.
"""
from collections import Counter
from fractions import Fraction
from pathlib import Path
from zipfile import ZipFile
import argparse
import gzip
import hashlib
import json
import math
import time
import numpy as np

ARCHIVE_SHA = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
REPORT_SHA = '28e5a641da153b08a7f15f4abb87336c797f1e85b6f2742fc025274c231f53c5'
CLASS_SHA = 'f82801aa26d3f4228b8cb68f08abab5ef45458cc2368703e9187e0745662d6c5'
REQUEST_SHA = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
RUN_ID, ARTIFACT_ID = 39123384402, 12135528290
ROOT = 'artifacts/h8f-all81-points/'
ORDER = ('M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY')
PAIRS = ((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))
STABLE='SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'
CHANGED='CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE'


def require(predicate, code):
    if not predicate: raise ValueError(code)


def hash_bytes(data): return hashlib.sha256(data).hexdigest()


def digest(data):
    return hash_bytes(json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def payload(zipfile, name):
    info=zipfile.getinfo(name)
    require(info.file_size < 8_000_000, 'OVERSIZED_ARCHIVE_MEMBER')
    return zipfile.read(info)


def vec10(data, label):
    require(type(data) in (list,tuple) and len(data)==10,'INVALID_TEN_'+label)
    require(all(type(x) in (int,float) and math.isfinite(x) for x in data),'NONFINITE_TEN_'+label)
    return np.asarray(data,dtype=np.float64)


def exact10(vertices, faces, density=1.0):
    """Independent density-weighted signed-tetra integral, exact rational sums."""
    rho=Fraction.from_float(float(density))
    require(rho>0,'INVALID_DENSITY')
    xyz=[]
    for vertex in vertices:
        require(len(vertex)==3,'INVALID_VERTEX')
        xyz.append(tuple(Fraction(x) for x in vertex))
    totals=[Fraction(0)]*10
    edges=Counter()
    for face in faces:
        require(len(face)==3 and all(type(i) is int and 0<=i<len(xyz) for i in face),
                'INVALID_FACE')
        i,j,k=face
        require(len({i,j,k})==3,'DEGENERATE_FACE')
        for u,v in ((i,j),(j,k),(k,i)): edges[u,v]+=1
        a,b,c=xyz[i],xyz[j],xyz[k]
        det=a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+a[2]*(b[0]*c[1]-b[1]*c[0])
        volume=rho*det/6
        sums=[a[t]+b[t]+c[t] for t in range(3)]
        totals[0]+=volume
        for t in range(3): totals[t+1]+=volume*sums[t]/4
        for n,(u,v) in enumerate(PAIRS,4):
            totals[n]+=volume*(sums[u]*sums[v]+a[u]*a[v]+b[u]*b[v]+c[u]*c[v])/20
    require(all(n==1 and edges[(v,u)]==1 for (u,v),n in edges.items()),'OPEN_OR_ORIENTATION_FAILED')
    require(totals[0]>0,'NONPOSITIVE_EXACT_MASS')
    return totals


def fixed_in_target(request):
    f=vec10(request['fixed_shell_moments'],'FIXED')
    o=np.asarray(request['target_origin'],dtype=float)
    rotation=np.asarray(request['target_axes'],dtype=float).T
    require(o.shape==(3,) and rotation.shape==(3,3),'INVALID_TARGET_FRAME')
    m=f[0];L=f[1:4]
    S=np.array(((f[4],f[9],f[8]),(f[9],f[5],f[7]),(f[8],f[7],f[6])))
    first=rotation@(L-m*o)
    second=rotation@(S-np.outer(o,L)-np.outer(L,o)+m*np.outer(o,o))@rotation.T
    return np.array([m,*first,second[0,0],second[1,1],second[2,2],second[1,2],second[0,2],second[0,1]])


def signature(rec):
    kind=rec['point_type']; expected={'EXPLICIT3D':1,'LPI':5,'TPI':9}
    require(kind in expected,'UNSUPPORTED_CONSTRUCTION')
    ops=rec['operands']
    require(len(ops)==expected[kind],'WRONG_CONSTRUCTION_ARITY')
    refs=[]
    for op in ops:
        require(op.get('status')=='UNIQUE' and len(op.get('source_vertices',[]))==1,
                'UNRESOLVED_CONSTRUCTION')
        r=op['source_vertices'][0]
        refs.append((r['input_object'],r['input_vertex']))
    if kind=='LPI': return (kind,tuple(sorted(refs[:2])),tuple(sorted(refs[2:])))
    if kind=='TPI': return (kind,tuple(sorted(tuple(sorted(refs[n:n+3])) for n in (0,3,6))))
    return (kind,tuple(refs))


def face_keys(material):
    recs=material['material_proof']['resolved_construction_records']
    sig=tuple(signature(r) for r in recs)
    require(len(sig)==len(material['variable_rational_vertices']), 'FEATURE_COUNT_MISMATCH')
    require(len(sig)==len(set(sig)),'DUPLICATE_FEATURE')
    result=Counter()
    for a,b,c in material['variable_faces']:
        tri=(sig[a],sig[b],sig[c])
        result[min(tri,tri[1:]+tri[:1],tri[2:]+tri[:2])]+=1
    return sig,result


def witness_59_60(mat59,mat60):
    a,fa=face_keys(mat59); b,fb=face_keys(mat60)
    require(len(a)==len(b),'WITNESS_VERTEX_COUNT_MISMATCH')
    changes=[i for i in range(len(a)) if a[i]!=b[i]]
    removed=list((Counter(a)-Counter(b)).elements())
    added=list((Counter(b)-Counter(a)).elements())
    report={
      'sample_indices':[59,60],
      'native_c7':[mat59['quadric_coefficients'][7],mat60['quadric_coefficients'][7]],
      'changed_vertex_indices':changes,
      'removed_feature_count':len(removed),'added_feature_count':len(added),
      'removed_oriented_triangle_count':sum((fa-fb).values()),
      'added_oriented_triangle_count':sum((fb-fa).values()),
      'same_source_faces':mat59['quadric_source_faces']==mat60['quadric_source_faces'],
      'continuous_branch_certified':False,
    }
    require(report['changed_vertex_indices']==[8043,8044,8045,8046,8047] and
            len(removed)==len(added)==2 and
            report['removed_oriented_triangle_count']==report['added_oriented_triangle_count']==17,
            'H8_POINT60_WITNESS_DRIFT')
    return report


def finite_difference(rows,report):
    J=np.asarray(report['analytic_10_by_10_jacobian'],dtype=np.float64)
    require(J.shape==(10,10) and np.isfinite(J).all(),'JACOBIAN_FORMAT_MISMATCH')
    require(len(report['numeric_checks'])==30, 'INCOMPLETE_FD_STENCILS')
    checks=[]
    for entry in report['numeric_checks']:
        col=entry['column'];indices=entry['sample_indices']
        require(type(col) is int and 0<=col<10 and len(indices)==5 and len(set(indices))==5,
                'FD_LAYOUT_INVALID')
        x=np.asarray([rows[i]['native_c'][col]-rows[0]['native_c'][col] for i in indices])
        scale=float(np.max(np.abs(x)))
        require(scale>0,'FD_ZERO_SCALE')
        matrix=np.vstack([(x/scale)**p for p in range(5)])
        weights=np.linalg.solve(matrix,[0.,1.,0.,0.,0.])/scale
        values=np.asarray([rows[i]['r_D'] for i in indices])
        fd=weights@values
        err=float(np.max(np.abs(fd-J[:,col])/np.maximum(1.,np.abs(J[:,col]))))
        require(abs(err-entry['max_scaled_derivative_error'])<5e-9,'FD_REPORT_MISMATCH')
        checks.append({'column':col,'step':entry['step'],'scaled_error':err,
                       'raw_feature_hash_stable':entry['feature_hash_stable']})
    require(len({(p['column'],p['step']) for p in checks})==30,'FD_DUPLICATE_STENCIL')
    return {'checked_stencils':len(checks),'max_scaled_error':max(p['scaled_error'] for p in checks),
            'raw_hash_unstable_stencils':sum(not p['raw_feature_hash_stable'] for p in checks),
            'numerical_only_not_smooth_certificate':True}


def audit(path, *, exact_mode='focus', progress=None):
    """Candidate r_D records are always excluded, and J_D values are never emitted."""
    require(exact_mode in ('none','focus','all'),'INVALID_EXACT_MODE')
    begin=time.monotonic(); archive=Path(path)
    require(archive.is_file() and hash_bytes(archive.read_bytes())==ARCHIVE_SHA,
            'UNRECOGNIZED_H8F_ARCHIVE_SHA')
    exact_indices=(set(range(81)) if exact_mode=='all' else {0,59,60} if exact_mode=='focus' else set())
    with ZipFile(archive) as z:
        require(len(z.namelist())==183,'WRONG_ARCHIVE_MEMBER_COUNT')
        raw_report=payload(z,ROOT+'report.json')
        raw_class=payload(z,'artifacts/h8f-81-exact-construction-classification.json')
        raw_request=payload(z,'artifacts/h8-request/prepared-request.json')
        require(hash_bytes(raw_report)==REPORT_SHA and hash_bytes(raw_class)==CLASS_SHA and
                hash_bytes(raw_request)==REQUEST_SHA,'EMBEDDED_EVIDENCE_SHA_MISMATCH')
        report=json.loads(raw_report);classifier=json.loads(raw_class)
        request=json.loads(raw_request)['request']
        require(report['completed_samples']==report['production_cherchi_calls']==81 and
                report['complete_eighty_one_samples'] is False and
                report['qualified_branch_neighborhood'] is False and
                report['all_tested_stencils_same_feature_hash'] is False and
                report['formal_newton_converged'] is False and
                report['all_numerical_checks_passed'] is True,'ORIGINAL_FAILURE_FLAGS_CHANGED')
        require(classifier['classifications']=={STABLE:79,CHANGED:1} and
                classifier['certified_smooth_neighborhood'] is False and
                classifier['source_report_sha256']==REPORT_SHA and
                classifier['request_sha256']==REQUEST_SHA,'CLASSIFIER_IDENTITY_OR_COUNTS_MISMATCH')
        statuses={i['index']:i['status'] for i in classifier['comparisons']}
        require(len(statuses)==80 and statuses[60]==CHANGED and
                all(statuses[i]==STABLE for i in statuses if i!=60),'POINT60_CLASSIFICATION_MISMATCH')
        f=fixed_in_target(request); density=float(request['material_density'])
        rows=[]; focus={}; max_error=0.; max_fixed=0.; exact_count=0
        for idx in range(81):
            name=ROOT+f'point-{idx:03d}'
            row=json.loads(payload(z,name+'.json'))
            zip_bytes=payload(z,name+'-material.json.gz')
            require(hash_bytes(zip_bytes)==row['exact_same_call_material_archive_sha256'],
                    'MATERIAL_ARCHIVE_SHA_MISMATCH')
            mat=json.loads(gzip.decompress(zip_bytes))
            require(row['index']==idx and mat['quadric_coefficients']==row['coefficients'] and
                    mat['geometry_hash']==row['material_geometry_hash'] and
                    mat['topology_hash']==row['feature_branch_hash'] and
                    len(mat['variable_faces'])==row['triangle_count'] and
                    len(mat['variable_rational_vertices'])==row['vertex_count'] and
                    row['exact_native_material_boundary_passed'] is True,
                    'SAME_CALL_MATERIAL_MISMATCH')
            require(mat['boolean_backend_identity']==row['native_boolean_backend'] and
                    mat['boolean_backend_identity'].endswith(report['actual_cherchi_sha256']) and
                    mat['rational_arithmetic_identity']['module_sha256']==report['actual_arithmetic_sha256'],
                    'NATIVE_MODULE_PROVENANCE_MISMATCH')
            require(digest({'vertices':mat['material_proof']['exact_vertices'],
                            'faces':mat['variable_faces']})==mat['geometry_hash'] and
                    digest({'vertices':mat['quadric_source_vertices'],
                            'faces':mat['quadric_source_faces'],
                            'coefficients':mat['quadric_coefficients']})==mat['quadric_source_identity'],
                    'EXACT_GEOMETRY_HASH_MISMATCH')
            r=vec10(mat['variable_raw_moments'],'VARIABLE'); total=vec10(mat['raw_moments'],'TOTAL')
            require(np.array_equal(r,vec10(row['production_variable_raw_moments'],'ARCHIVED_PRODUCTION')) and
                    np.array_equal(r,vec10(row['independent_variable_raw_moments'],'ARCHIVED_INDEPENDENT')),
                    'ARCHIVED_MOMENT_LINK_MISMATCH')
            require(np.array_equal(total,vec10(row['full_raw_moments'],'ARCHIVED_TOTAL')),
                    'ARCHIVED_TOTAL_LINK_MISMATCH')
            fixed_error=float(np.max(np.abs((total-r)-f)))
            require(fixed_error<1e-10,'FIXED_DOUBLE_COUNT_OR_FRAME_MISMATCH')
            max_fixed=max(max_fixed,fixed_error)
            J=mat['moment_jacobian']
            require(len(J)==10 and all(len(a)==10 for a in J) and
                    all(math.isfinite(v) for a in J for v in a), 'ARCHIVED_JACOBIAN_SHAPE_INVALID')
            e=None
            if idx in exact_indices:
                values=exact10(mat['variable_rational_vertices'],mat['variable_faces'],density)
                err=np.max(np.abs(np.array([float(v) for v in values])-r))
                e=float(err)
                require(e<=1e-10,'INDEPENDENT_EXACT_MOMENT_DISAGREEMENT')
                max_error=max(max_error,e);exact_count+=1
            if idx in (59,60):focus[idx]=mat
            # Withhold the 10x10 Jacobian contents; preserve only the audit digest.
            rows.append({'index':idx,'native_c':vec10(row['coefficients'],'NATIVE_C').tolist(),
                'polynomial_q':(vec10(row['coefficients'],'NATIVE_C')*np.array([1]*7+[2]*3)).tolist(),
                'r_D':r.tolist(),'r_F':f.tolist(),
                'same_call_material_gzip_sha256':row['exact_same_call_material_archive_sha256'],
                'geometry_hash':mat['geometry_hash'],'topology_hash':mat['topology_hash'],
                'jacobian_attachment_sha256':digest(J),'J_D':None,
                'derivative_status':'UNKNOWN_NOT_CERTIFIED',
                'finite_feature_status':statuses.get(idx,'BASELINE_ONLY'),
                'topology_observation':'VALID_ARCHIVED_FINITE_POINT_NOT_CONTINUUM',
                'independent_moment_rechecked':idx in exact_indices,
                'exact_vs_archived_max_abs_error':e,
                'split':'excluded','training_admitted':False})
            if progress is not None and (idx+1)%9==0:
                progress(idx+1,81)
        witness=witness_59_60(focus[59],focus[60])
        fd=finite_difference(rows,report)
    return {'schema':'w2-h8f-81-physical-moment-candidates-v1',
      'source':{'run_id':RUN_ID,'artifact_id':ARTIFACT_ID,'upstream_workflow_conclusion':'failure',
                'github_head_sha':'0bcc187b3005478baa586a6d6f450e73811ca342',
                'archive_sha256':ARCHIVE_SHA,'report_sha256':REPORT_SHA,
                'classification_sha256':CLASS_SHA,'request_sha256':REQUEST_SHA,
                'cad_scope':'H8_RECONSTRUCTED_NOT_AUTHOR_ORIGINAL'},
      'evaluated_historical_points':81,'new_native_evaluations':0,
      'candidate_count':len(rows),'exact_reintegrated_count':exact_count,
      'exact_mode':exact_mode,'max_exact_r_D_abs_error':max_error,
      'max_fixed_partition_abs_error':max_fixed,
      'finite_difference':fd,'point60_witness':witness,
      'feature_counts':{STABLE:79,CHANGED:1},
      'formal_smooth_neighborhood_certified':False,'newton_converged':False,
      'W0_MomentContractV1_derivative_admission':False,
      'formal_training_samples':0,'derivative_training_samples':0,
      'interpretation':'HISTORICAL_PHYSICAL_MOMENT_EVIDENCE_ONLY_NO_JACOBIAN_LABEL',
      'replay_wall_seconds':time.monotonic()-begin,
      'samples':rows}


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--exact-mode',choices=('none','focus','all'),default='focus')
    a=parser.parse_args(argv)
    out=Path(a.output)
    require(not out.exists(),'REFUSE_OVERWRITE_EVIDENCE')
    report=audit(a.archive,exact_mode=a.exact_mode,
                 progress=lambda done,total:print(f'offline exact gate {done}/{total}',flush=True))
    with out.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2,allow_nan=False,sort_keys=True)
        f.write('\n')
    print(json.dumps({k:v for k,v in report.items() if k in
         ('evaluated_historical_points','exact_reintegrated_count','max_exact_r_D_abs_error',
          'max_fixed_partition_abs_error','formal_training_samples','replay_wall_seconds',
          'finite_difference','point60_witness')},sort_keys=True))

if __name__=='__main__':main()

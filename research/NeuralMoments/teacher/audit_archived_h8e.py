"""Offline H8e 25-point *historical* Cherchi artifact verifier.

No native module, no resampling and no training labels. The original GitHub
workflow's FAILURE remains a failure (finite feature hash drift); this tool
only checks archived same-call physical ten-moment evidence.
"""
import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
import math
from pathlib import Path
import time
from zipfile import ZipFile

PREFIX='artifacts/h8e-jacobian-cols0-4-8/'
POINTS=25
ORDER=('M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY')
PAIR_ORDER=((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def json_from_zip(archive,name,*,compressed=False):
    payload=archive.read(name)
    if compressed:
        payload=gzip.decompress(payload)
    return json.loads(payload)


def require(flag, code):
    if not flag:
        raise ValueError(code)


def valid10(value,name):
    require(isinstance(value,(tuple,list)) and len(value)==10,'INVALID_TEN_'+name)
    require(all(type(x) in (float,int) and math.isfinite(x) for x in value),'NONFINITE_TEN_'+name)
    return [float(x) for x in value]


def check_point_header(index,row,material_bytes,material,report):
    require(type(row.get('index')) is int and row['index']==index,'POINT_INDEX_MISMATCH')
    require(sha(material_bytes)==row['exact_same_call_material_archive_sha256'],'MATERIAL_GZIP_SHA_MISMATCH')
    c=valid10(row['coefficients'],'POINT_NATIVE_C')
    require(c==valid10(material['quadric_coefficients'],'MATERIAL_NATIVE_C'), 'SAME_CALL_NATIVE_C_MISMATCH')
    require(material['geometry_hash']==row['material_geometry_hash'],'SAME_CALL_GEOMETRY_MISMATCH')
    require(material['topology_hash']==row['feature_branch_hash'],'SAME_CALL_TOPOLOGY_MISMATCH')
    require(material['boolean_backend_identity']==row['native_boolean_backend'],'CHERCHI_BACKEND_MISMATCH')
    require(material['boolean_backend_identity'].endswith(report['actual_cherchi_sha256']),
            'CHERCHI_MODULE_SHA_CONFLICT')
    require(material['rational_arithmetic_identity']['module_sha256']==report['actual_arithmetic_sha256'],
            'ARITHMETIC_MODULE_SHA_CONFLICT')
    require(material['derivative_defined'] is True and len(material['moment_jacobian'])==10 and
            all(len(x)==10 for x in material['moment_jacobian']),'ARCHIVED_JACOBIAN_SHAPE_UNEXPECTED')
    require(digest({'vertices':material['quadric_source_vertices'],
                    'faces':material['quadric_source_faces'],
                    'coefficients':material['quadric_coefficients']})==material['quadric_source_identity'],
            'SOURCE_GEOMETRY_IDENTITY_MISMATCH')
    require(digest({'vertices':material['material_proof']['exact_vertices'],
                    'faces':material['variable_faces']})==material['geometry_hash'],
            'EXACT_MATERIAL_GEOMETRY_HASH_MISMATCH')
    require(row['vertex_count']==len(material['variable_rational_vertices']) and
            row['triangle_count']==len(material['variable_faces']),'MATERIAL_GEOMETRY_COUNTS_MISMATCH')
    require(row['exact_native_material_boundary_passed'] is True,'ARCHIVED_NATIVE_MATERIAL_AUDIT_FAILED')
    require(valid10(row['production_variable_raw_moments'],'ARCHIVED_PRODUCTION')==
            valid10(material['variable_raw_moments'],'ATTACHED_PRODUCTION'),'ATTACHED_MOMENTS_MISMATCH')
    require(valid10(row['full_raw_moments'],'ARCHIVED_TOTAL')==
            valid10(material['raw_moments'],'ATTACHED_TOTAL'),'ATTACHED_TOTAL_MISMATCH')
    return c


def exact_fraction(token):
    require(isinstance(token,str) and token.count('/')==1,'INVALID_RATIONAL_TOKEN')
    a,b=token.split('/')
    # Archived target-space vertices are decimal numerator/denominator tokens.
    require(a.lstrip('-').isdigit() and b.isdigit() and int(b)>0,'INVALID_DECIMAL_RATIONAL')
    return Fraction(int(a),int(b))


def independent_exact_ten(vertices,faces):
    """Independent signed tetrahedron integral in the archived target frame."""
    coords=tuple(tuple(exact_fraction(x) for x in p) for p in vertices)
    require(all(len(p)==3 for p in coords),'INVALID_EXACT_VERTEX_SHAPE')
    r=[Fraction() for _ in range(10)]
    edges=Counter()
    for face in faces:
        require(len(face)==3 and all(type(i) is int and 0<=i<len(coords) for i in face),
                'INVALID_EXACT_FACE_INDEX')
        i,j,k=face
        require(len({i,j,k})==3,'DEGENERATE_FACE_INDEX')
        for x,y in ((i,j),(j,k),(k,i)):
            edges[x,y]+=1
        a,b,c=coords[i],coords[j],coords[k]
        det=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+
             a[2]*(b[0]*c[1]-b[1]*c[0]))
        if det==0:
            continue
        r[0]+=det/6
        sums=[a[d]+b[d]+c[d] for d in range(3)]
        for d in range(3):r[d+1]+=det*sums[d]/24
        for index,(i,j) in enumerate(PAIR_ORDER,start=4):
            r[index]+=det*(sums[i]*sums[j]+a[i]*a[j]+b[i]*b[j]+c[i]*c[j])/120
    require(all(n==1 and edges.get((v,u),0)==1 for (u,v),n in edges.items()),
            'EXACT_BOUNDARY_NOT_CLOSED_OR_ORIENTED')
    require(r[0]>0,'EXACT_NONPOSITIVE_MASS')
    return r


def check_ulp(actual,exact,field):
    values=valid10(actual,field)
    reference=[float(x) for x in exact]
    error=[abs(a-b) for a,b in zip(values,reference)]
    ulps=[abs(a-b)/math.ulp(max(abs(b),1.0)) for a,b in zip(values,reference)]
    require(max(ulps)<=4,'ARCHIVED_INDEPENDENT_TEN_MOMENT_ULP_MISMATCH:'+field)
    return max(error),max(ulps)


def fixed_in_target(request):
    """Reapply saved native target frame to fixed raw ten moments once."""
    import numpy as np
    r=np.asarray(valid10(request['fixed_shell_moments'],'FIXED_INPUT'))
    o=np.asarray(request['target_origin'],dtype=float)
    rotation=np.asarray(request['target_axes'],dtype=float).T
    mass=r[0]; first=r[1:4]
    s=np.asarray(((r[4],r[9],r[8]),(r[9],r[5],r[7]),(r[8],r[7],r[6])))
    f=rotation@(first-mass*o)
    t=rotation@(s-np.outer(o,first)-np.outer(first,o)+mass*np.outer(o,o))@rotation.T
    return [float(x) for x in (mass,*f,t[0,0],t[1,1],t[2,2],t[1,2],t[0,2],t[0,1])]


def audit_archive(zip_path, classifier_path=None, *, limit=25):
    require(type(limit) is int and 1<=limit<=25,'INVALID_POINT_LIMIT')
    started=time.monotonic()
    path=Path(zip_path)
    archive_hash=sha(path.read_bytes())
    points=[]
    with ZipFile(path) as z:
        names=set(z.namelist())
        report_bytes=z.read(PREFIX+'report.json')
        report=json.loads(report_bytes)
        request_bytes=z.read('artifacts/h8-request/prepared-request.json')
        request_json=json.loads(request_bytes)
        require(sha(request_bytes)==report['input_request_sha256'],'REQUEST_SHA_MISMATCH')
        require(report['completed_samples']==25 and report['production_cherchi_calls']==25,
                'NOT_COMPLETE_25_POINT_ARCHIVE')
        require(report['status']=='FINITE_JACOBIAN_DIAGNOSTIC_COMPLETED_NO_SMOOTH_ADMISSION',
                'UNEXPECTED_UPSTREAM_RUN_STATUS')
        require(report['qualified_branch_neighborhood'] is False and
                report['complete_eighty_one_samples'] is False,'UNEXPECTED_SMOOTH_CLAIM')
        require(report['original_author_cad'] is False,'AUTHOR_CAD_SCOPE_MISMATCH')
        require(request_json['schema']=='spin-heart-h8-faster-preparation-v1',
                'FROZEN_H8_REQUEST_SCHEMA_MISMATCH')
        fixed=fixed_in_target(request_json['request'])
        require(len(report['numeric_checks'])==9,'NUMERICAL_CHECK_COUNT_MISMATCH')
        for index in range(limit):
            name=PREFIX+f'point-{index:03d}'
            require(name+'.json' in names and name+'-material.json.gz' in names,
                    'MISSING_REAL_CHERCHI_POINT')
            point=json_from_zip(z,name+'.json')
            blob=z.read(name+'-material.json.gz')
            material=json.loads(gzip.decompress(blob))
            c=check_point_header(index,point,blob,material,report)
            tic=time.monotonic()
            exact=independent_exact_ten(material['variable_rational_vertices'],material['variable_faces'])
            elapsed=time.monotonic()-tic
            abs_err,ulp_err=check_ulp(material['variable_raw_moments'],exact,'PRODUCTION')
            independent_abs,independent_ulp=check_ulp(point['independent_variable_raw_moments'],exact,'ARCHIVED_INDEPENDENT')
            total=valid10(material['raw_moments'],'TOTAL')
            expected=[a+b for a,b in zip(material['variable_raw_moments'],fixed)]
            require(all(abs(a-b)<=4*math.ulp(max(abs(b),1.0)) for a,b in zip(total,expected)),
                    'DOUBLE_COUNT_OR_FIXED_FRAME_MISMATCH')
            points.append({'index':index,'archive_material_sha256':sha(blob),
                           'native_c_sha256':digest(c),'geometry_hash':material['geometry_hash'],
                           'topology_hash':material['topology_hash'],
                           'exact_reference_max_abs_error':abs_err,
                           'exact_reference_max_ulp_error':ulp_err,
                           'archived_independent_max_abs_error':independent_abs,
                           'archived_independent_max_ulp_error':independent_ulp,
                           'reference_elapsed_seconds':elapsed,
                           'archived_native_wall_seconds':point['wall_seconds'],
                           'archived_native_stage_seconds':point['stages_seconds'],
                           'r_D':valid10(material['variable_raw_moments'],'VARIABLE'),
                           'r_F':fixed,'total_r':total})
        classification=None
        if classifier_path:
            with ZipFile(classifier_path) as cls:
                cls_json=json.loads(cls.read('twenty-five-exact-construction-classification.json'))
            require(cls_json['source_report_sha256']==sha(report_bytes) and
                    cls_json['request_sha256']==report['input_request_sha256'] and
                    cls_json['complete_material_snapshots_verified']==25,
                    'CLASSIFIER_SOURCE_BINDING_MISMATCH')
            require(cls_json['certified_smooth_neighborhood'] is False and
                    cls_json['certified_newton_direction'] is False,'FALSE_SMOOTHNESS_ADMISSION')
            classification={'schema':cls_json['schema'],
                            'source_report_sha256':cls_json['source_report_sha256'],
                            'classifications':cls_json['classifications'],
                            'certified_smooth_neighborhood':False,
                            'certified_newton_direction':False}
        return {'schema':'w2-h8e-archived-real-material-independent-audit-v1',
            'source':{'artifact_id':12134772056,'run_id':39121571756,
                      'workflow_conclusion':'failure','zip_sha256':archive_hash,
                      'request_sha256':report['input_request_sha256'],
                      'reported_native_module_sha256':report['actual_native_sha256'],
                      'reported_cherchi_module_sha256':report['actual_cherchi_sha256'],
                      'reported_arithmetic_module_sha256':report['actual_arithmetic_sha256'],
                      'original_author_cad':False,'full_81_points':False},
            'verified_points':len(points),
            'max_exact_raw_ten_moment_absolute_error':max(p['exact_reference_max_abs_error'] for p in points),
            'max_exact_raw_ten_moment_ulp_error':max(p['exact_reference_max_ulp_error'] for p in points),
            'max_independent_archived_reference_absolute_error':max(p['archived_independent_max_abs_error'] for p in points),
            'unique_observed_topology_hashes':len({p['topology_hash'] for p in points}),
            'upstream_all_tested_stencils_same_feature_hash':report['all_tested_stencils_same_feature_hash'],
            'upstream_changed_feature_hash_points':report['changed_feature_hash_points'],
            'upstream_native_25point_wall_seconds':report['wall_seconds'],
            'offline_verification_wall_seconds':time.monotonic()-started,
            'independent_classification':classification,
            'physical_moments_status':'OFFLINE_ARCHIVED_CHERCHI_NUMERICAL_EVIDENCE_REVERIFIED',
            'derivative_status':'UNKNOWN_NO_CERTIFIED_CONTINUOUS_NEIGHBORHOOD',
            'training_samples_admitted':0,
            'local_native_calls':0,
            'limitations':['Not new Cherchi executions','Native modules are not present locally',
                           'Earlier GitHub run conclusion remains failure',
                           'No certified smooth neighborhood or W0 derivative admission',
                           '25-point historical archive is not H8 81-point proof',
                           'No independent local native material self-intersection audit'],
            'points':points}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--classifier',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--limit',type=int,default=25)
    args=p.parse_args(argv)
    if args.output.exists():
        raise FileExistsError('REFUSE_OVERWRITE_SCIENTIFIC_EVIDENCE')
    report=audit_archive(args.archive,args.classifier,limit=args.limit)
    with args.output.open('x',encoding='utf-8') as output:
        json.dump(report,output,sort_keys=True,indent=2,allow_nan=False)
        output.write('\n')
    print(json.dumps({k:report[k] for k in ('verified_points',
        'max_exact_raw_ten_moment_absolute_error','max_exact_raw_ten_moment_ulp_error',
        'unique_observed_topology_hashes','upstream_changed_feature_hash_points',
        'offline_verification_wall_seconds','training_samples_admitted')}))
    return 0

if __name__=='__main__':
    raise SystemExit(main())

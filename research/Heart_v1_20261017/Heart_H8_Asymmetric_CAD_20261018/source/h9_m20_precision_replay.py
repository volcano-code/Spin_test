"""W3 M20: offline rounding/cancellation ledger for the six saved native packets.

No Cherchi calls, no native-module imports, no mutations of prior evidence.
Reintegrates the represented rational surfaces, forms differences BEFORE float
conversion, and compares against the recorded binary64 Jacobian column 7.
An exact surface secant is NOT a certified derivative of the continuous CAD.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction as F
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import struct
import sys
import time

BASELINE_M18_SHA = '68ee61282caac38d160a4226d9e44df694b7723094890fd62cc61ada434e12e2'
M19_HEAD = '265bafc0525cc56f94c3f440e9337231ce805a52'
SIDES = ('left-coarse', 'left-near', 'right-near', 'right-coarse')
MID_SIDES = ('left-mid', 'right-mid')
NAMES = ('mass','Mx','My','Mz','Mxx','Myy','Mzz','Myz','Mxz','Mxy')
PAIRS = ((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))
HEX = re.compile(r'[0-9a-f]{64}\Z')
TOKEN = re.compile(r'(-?(?:0b[01]+|[0-9]+))/((?:0b[01]+|[0-9]+))\Z')


def need(ok, reason):
    if not ok:
        raise ValueError(reason)


def file_hash(path):
    h=sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()


def unique_pairs(pairs):
    result={}
    for key,value in pairs:
        need(key not in result, 'DUPLICATE_JSON_KEY:'+key)
        result[key]=value
    return result


def invalid_constant(value):
    raise ValueError('NONFINITE_JSON_CONSTANT:'+value)


def read_json(path, compressed=False):
    path=Path(path)
    need(path.is_file() and not path.is_symlink(), 'MISSING_OR_SYMLINK_INPUT:'+str(path))
    need(0<path.stat().st_size<128*1024**2, 'INPUT_SIZE_OUT_OF_RANGE:'+path.name)
    if compressed:
        with gzip.open(path,'rb') as stream:
            raw=stream.read(512*1024**2+1)
        need(len(raw)<=512*1024**2, 'EXPANDED_INPUT_TOO_LARGE')
    else:
        raw=path.read_bytes()
    return json.loads(raw,object_pairs_hook=unique_pairs,parse_constant=invalid_constant)


def finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def ten(values):
    need(type(values) is list and len(values)==10 and all(finite(x) for x in values),
         'FINITE_TEN_REQUIRED')
    return [float(x) for x in values]


def b64_equal(a,b):
    return finite(a) and finite(b) and struct.pack('!d',float(a))==struct.pack('!d',float(b))


def vector_equal(a,b):
    return all(b64_equal(x,y) for x,y in zip(ten(a),ten(b)))


def rational(token):
    need(type(token) is str, 'RATIONAL_TOKEN_MUST_BE_STRING')
    match=TOKEN.fullmatch(token)
    need(match is not None, 'BAD_EXACT_RATIONAL_TOKEN')
    def integer(s):
        sign=-1 if s.startswith('-') else 1
        t=s.lstrip('-')
        return sign*int(t[2:],2) if t.startswith('0b') else sign*int(t,10)
    a,b=(integer(x) for x in match.groups())
    need(b>0, 'NONPOSITIVE_RATIONAL_DENOMINATOR')
    return F(a,b)


def exact_surface_moments(material):
    """Exact oriented tetrahedron volume integrals in the saved target frame.

    Uses the same raw geometric moment convention as the validated M18/M19
    integrator; no unrecorded density/coordinate transformation is introduced.
    Edge checks here do not replace the earlier native self-intersection audit.
    """
    coords=material['variable_rational_vertices'];faces=material['variable_faces']
    need(type(coords) is list and len(coords)>=4 and type(faces) is list and faces,
         'EMPTY_SURFACE')
    vertices=[]
    for row in coords:
        need(type(row) is list and len(row)==3,'BAD_VERTEX')
        vertices.append(tuple(rational(x) for x in row))
    total=[F(0) for _ in range(10)]
    edges=Counter()
    for face in faces:
        need(type(face) is list and len(face)==3 and len(set(face))==3 and
             all(type(k) is int and 0<=k<len(vertices) for k in face),'INVALID_FACE')
        ia,ib,ic=face
        for edge in ((ia,ib),(ib,ic),(ic,ia)):
            edges[edge]+=1
        a,b,c=(vertices[k] for k in face)
        det=(a[0]*(b[1]*c[2]-b[2]*c[1])+a[1]*(b[2]*c[0]-b[0]*c[2])+
             a[2]*(b[0]*c[1]-b[1]*c[0]))
        total[0]+=det/6
        sums=[a[k]+b[k]+c[k] for k in range(3)]
        for k in range(3):total[1+k]+=det*sums[k]/24
        for k,(i,j) in enumerate(PAIRS):
            diagonal=a[i]*a[j]+b[i]*b[j]+c[i]*c[j]
            total[4+k]+=det*(sums[i]*sums[j]+diagonal)/120
    need(all(count==1 and edges[(b,a)]==1 for (a,b),count in edges.items()),
         'OPEN_NONMANIFOLD_OR_INCONSISTENT_SURFACE')
    need(total[0]>0,'NONPOSITIVE_ORIENTED_VOLUME')
    return total


def binary(value):
    need(finite(value),'NONFINITE_BINARY64')
    return F.from_float(float(value))


def number(value):
    return float(value)


def signed(value):
    return (value>0)-(value<0)


def interval_ledger(a,b):
    """Three routes, with an exact algebraic residual decomposition per moment."""
    x,y=a['c7'],b['c7']
    need(finite(x) and finite(y) and y>x,'BAD_ORDERED_INTERVAL')
    h=binary(y)-binary(x); h64=float(y)-float(x)
    components={}
    for k,name in enumerate(NAMES):
        ma,mb=a['moments'][k],b['moments'][k]
        ja,jb=a['j7'][k],b['j7'][k]
        # Faithfully reproduce the old M19 binary64 path.
        sec64=(mb-ma)/h64
        avg64=(ja+jb)/2
        resid64=sec64-avg64
        need(all(math.isfinite(v) for v in (sec64,avg64,resid64)),'NONFINITE_DIFFERENCE')
        scale=binary(max(1.,abs(avg64)))
        avg=(binary(ja)+binary(jb))/2
        # Exact arithmetic on already-rounded input numbers is not recovery
        # of the original exact surface moments.
        sec_rounded=(binary(mb)-binary(ma))/h
        sec_surface=(b['exact'][k]-a['exact'][k])/h
        r_rounded=sec_rounded-avg
        r_surface=sec_surface-avg
        r64=binary(resid64)
        round_inputs=r_rounded-r_surface
        round_arithmetic=r64-r_rounded
        need(r64-r_surface==round_inputs+round_arithmetic,'ROUNDING_LEDGER_ALGEBRA_FAILURE')
        ulp_bound=(binary(math.ulp(ma))+binary(math.ulp(mb)))/(2*h)
        component={
            'binary64_secant':sec64,
            'exact_arithmetic_on_saved_floats_secant':number(sec_rounded),
            'exact_surface_secant':number(sec_surface),
            'saved_jacobian_endpoint_average':number(avg),
            'binary64_signed_residual':resid64,
            'exact_surface_signed_residual':number(r_surface),
            'exact_surface_residual_sign':signed(r_surface),
            'binary64_scaled_error':abs(resid64)/float(scale),
            'exact_surface_scaled_error':number(abs(r_surface)/scale),
            'rounded_moment_input_contribution_signed':number(round_inputs),
            'floating_arithmetic_contribution_signed':number(round_arithmetic),
            'rounded_moment_input_scaled_contribution':number(abs(round_inputs)/scale),
            'floating_arithmetic_scaled_contribution':number(abs(round_arithmetic)/scale),
            'moment_space_signed_residual':number(h*r_surface),
            'moment_space_scaled_residual':number(abs(h*r_surface)/scale),
            'half_ulp_input_error_bound_in_slope_units_if_nearest':number(ulp_bound),
            'observed_moment_rounding_within_half_ulp_bound':abs(round_inputs)<=ulp_bound,
            'common_scale':float(scale),
            'exact_residual_decomposition_verified':True,
        }
        components[name]=component
    fmax=max(v['binary64_scaled_error'] for v in components.values())
    emax=max(v['exact_surface_scaled_error'] for v in components.values())
    return {'delta_c7':float(h),'delta_c7_exact':str(h),
            'max_binary64_scaled_error':fmax,'max_exact_surface_scaled_error':emax,
            'worst_exact_surface_component':max(NAMES,key=lambda n:components[n]['exact_surface_scaled_error']),
            'components':components}


def ratio(a,b):
    return a/b if b>0 else None


def side_ledger(a,m,b):
    full=interval_ledger(a,b);first=interval_ledger(a,m);second=interval_ledger(m,b)
    h1=binary(m['c7'])-binary(a['c7']);h2=binary(b['c7'])-binary(m['c7'])
    h=h1+h2;cancel={}
    for k,name in enumerate(NAMES):
        ja,jm,jb=(binary(row['j7'][k]) for row in (a,m,b))
        r0=(b['exact'][k]-a['exact'][k])/h-(ja+jb)/2
        r1=(m['exact'][k]-a['exact'][k])/h1-(ja+jm)/2
        r2=(b['exact'][k]-m['exact'][k])/h2-(jm+jb)/2
        weighted=(h1*r1+h2*r2)/h
        # General identity also covers a rounded midpoint with unequal halves.
        correction=(jm-(h2*ja+h1*jb)/h)/2
        need(r0==weighted+correction,'SUBINTERVAL_RESIDUAL_IDENTITY_FAILURE')
        unsigned=(h1*abs(r1)+h2*abs(r2))/h
        cancel[name]={'half_signed_residuals':[number(r1),number(r2)],
                      'opposite_half_residual_signs':r1*r2<0,
                      'weighted_half_residual':number(weighted),
                      'jacobian_midpoint_curvature_correction':number(correction),
                      'full_residual':number(r0),
                      'weighted_cancellation_fraction':number(abs(weighted)/unsigned) if unsigned else None,
                      'exact_partition_identity_verified':True}
    fhalf=max(first['max_binary64_scaled_error'],second['max_binary64_scaled_error'])
    ehalf=max(first['max_exact_surface_scaled_error'],second['max_exact_surface_scaled_error'])
    return {'full_interval':full,'two_half_intervals':[first,second],
            'binary64_full_over_worst_half':ratio(full['max_binary64_scaled_error'],fhalf),
            'binary64_worst_half_over_full':ratio(fhalf,full['max_binary64_scaled_error']),
            'exact_surface_full_over_worst_half':ratio(full['max_exact_surface_scaled_error'],ehalf),
            'exact_surface_worst_half_over_full':ratio(ehalf,full['max_exact_surface_scaled_error']),
            'signed_cancellation_ledger':cancel,
            'asymptotic_order_certified':False,'continuous_neighborhood_certified':False,'newton_admitted':False}


def load_packet(folder,stem,expected_hash,q,reported,j7,binaries,map_identity):
    packed=Path(folder)/(stem+'.json.gz');meta_path=Path(folder)/(stem+'.json')
    need(type(expected_hash) is str and HEX.fullmatch(expected_hash),'INVALID_PACKET_SHA')
    meta=read_json(meta_path)
    need(file_hash(packed)==expected_hash==meta.get('material_sha256'),'MATERIAL_SHA_MISMATCH:'+stem)
    mat=read_json(packed,compressed=True)
    need(vector_equal(mat.get('quadric_coefficients'),q) and vector_equal(meta.get('q'),q),
         'FULL_Q_MISMATCH:'+stem)
    need(mat.get('evaluation_map_identity')==map_identity and
         mat.get('boolean_backend_identity')=='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'+binaries['boolean'] and
         mat.get('rational_arithmetic_identity',{}).get('module_sha256')==binaries['arithmetic'] and
         mat.get('rational_arithmetic_identity',{}).get('backend')=='NATIVE_GMP_SURFACE_V1' and
         mat.get('material_proof',{}).get('schema')=='cherchi-same-call-material-v1',
         'MATERIAL_SOURCE_IDENTITY_MISMATCH:'+stem)
    need(meta.get('native_geometry_valid') is True and meta.get('newton_admitted') is False,
         'PRIOR_FINITE_AUDIT_MISSING:'+stem)
    jac=mat.get('moment_jacobian')
    need(type(jac) is list and len(jac)==10 and all(len(ten(row))==10 for row in jac),
         'BAD_JACOBIAN')
    need(vector_equal([row[7] for row in jac],j7),'JACOBIAN_COLUMN_NOT_SAME_PACKET:'+stem)
    started=time.perf_counter()
    print('M20_REINTEGRATING_SAVED_PACKET',stem,flush=True)
    exact=exact_surface_moments(mat)
    recorded=ten(reported);prod=ten(mat.get('variable_raw_moments'))
    exact_floats=[float(x) for x in exact]
    need(max(abs(a-b)/max(1.,abs(b)) for a,b in zip(exact_floats,recorded))<=1e-10 and
         max(abs(a-b)/max(1.,abs(b)) for a,b in zip(exact_floats,prod))<=1e-10,
         'RAW_MOMENT_CONVENTION_OR_INTEGRATION_MISMATCH:'+stem)
    need(file_hash(packed)==expected_hash,'PACKET_CHANGED_DURING_REPLAY')
    return {'c7':float(q[7]),'q':ten(q),'moments':recorded,'j7':ten(j7),'exact':exact,
            'evidence':{'stem':stem,'material_sha256':expected_hash,'metadata_sha256':file_hash(meta_path),
                        'moment_binary64_equals_rounded_exact':[b64_equal(a,b) for a,b in zip(recorded,exact_floats)],
                        'exact_ten_moments':[str(x) for x in exact],
                        'represented_surface_reintegration_seconds':time.perf_counter()-started}}


def replay(m18_path,old_dir,m19_root):
    m18_path=Path(m18_path);old_dir=Path(old_dir);root=Path(m19_root)
    need(file_hash(m18_path)==BASELINE_M18_SHA,'STAGE18_AUDIT_SHA_MISMATCH')
    a18=read_json(m18_path)
    plan_path=root/'midpoint-plan.json';plan=read_json(plan_path)
    run=root/'native-two-midpoints';mid_dir=run/'two-midpoint-native'
    refinement_path=run/'independent-refinement.json';refine=read_json(refinement_path)
    launch=read_json(run/'launch_result.json');report=read_json(mid_dir/'report.json')
    old_report=read_json(old_dir/'report.json')
    need(launch.get('status')=='TWO_NEW_NATIVE_MIDPOINTS_INDEPENDENTLY_VERIFIED_NO_NEWTON' and
         launch.get('worker_exit_code')==0 and launch.get('audit_exit_code')==0 and
         launch.get('new_qualified_midpoints')==2 and launch.get('newton_admitted') is False and
         launch.get('source_contract',{}).get('head_sha')==M19_HEAD,'M19_SUCCESS_SOURCE_RECORD_REQUIRED')
    need(a18.get('new_native_samples_reintegrated')==4 and a18.get('newton_admitted') is False and
         a18.get('finite_symbolic_branch_split_at_new_four_samples') is True,
         'STAGE18_FINITE_AUDIT_REQUIRED')
    need(plan.get('schema')=='heart-h9-m19-two-midpoints-plan-v1' and
         plan.get('stage18_independent_audit_sha256')==BASELINE_M18_SHA and
         report.get('plan_sha256')==file_hash(plan_path) and
         file_hash(old_dir/'report.json')==a18.get('new_native_run_report_sha256')==plan.get('stage17_real_producer_report_sha256'),
         'PLAN_OR_PRIOR_REPORT_NOT_BOUND')
    need(refine.get('schema')=='heart-h9-m19-finite-refinement-diagnostics-v1' and
         refine.get('original_m18_audit_sha256')==BASELINE_M18_SHA and
         refine.get('new_native_run_report_sha256')==file_hash(mid_dir/'report.json') and
         refine.get('new_real_midpoint_materials_independently_verified')==2 and
         refine.get('newton_admitted') is False and refine.get('continuous_neighborhood_certified') is False,
         'M19_INDEPENDENT_REFINEMENT_NOT_BOUND')
    binaries=plan.get('stage17_current_binary_sha256')
    need(type(binaries) is dict and set(binaries)=={'core','boolean','arithmetic'} and
         all(type(v) is str and HEX.fullmatch(v) for v in binaries.values()) and
         report.get('binary_hashes')==binaries==old_report.get('binary_hashes'),'BINARY_IDENTITY_CHANGED')
    map_identity=plan.get('stage18_current_evaluation_map_identity')
    need(type(map_identity) is str and HEX.fullmatch(map_identity) and
         map_identity==a18.get('new_native_evaluation_map_identity'),'MAP_IDENTITY_UNBOUND')
    old_rows=plan['baseline_four_real_rows']; audit_rows=a18['sample_diagnostics']
    need(len(old_rows)==len(audit_rows)==4,'FOUR_PRIOR_ROWS_REQUIRED')
    old=[]
    for i,side in enumerate(SIDES):
        row=old_rows[i];aud=audit_rows[i]
        need(row['index']==aud['index']==i and row['side']==aud['side']==side and
             row['material_sha256']==aud['new_same_call_material_sha256'] and
             vector_equal(row['moments'],aud['recomputed_exact_moments']) and
             vector_equal(row['j7'],aud['native_recorded_jacobian_col7']) and
             b64_equal(row['c7'],row['q'][7]) and b64_equal(row['c7'],aud['c7']),
             'PRIOR_BASELINE_ROW_UNBOUND:'+side)
        old.append(load_packet(old_dir,f'side-{i:02d}-{side}',row['material_sha256'],row['q'],
                               row['moments'],row['j7'],binaries,map_identity))
    proposals=plan['predeclared_two_midpoints'];packet_rows=refine['new_midpoint_packets']
    need(len(proposals)==len(packet_rows)==2,'TWO_MIDPOINT_ROWS_REQUIRED')
    mids=[]
    for i,side in enumerate(MID_SIDES):
        p=proposals[i];r=packet_rows[i];stem=f'm19-mid-{i:02d}-{side}'
        meta=read_json(mid_dir/(stem+'.json'))
        need(p['index']==r['index']==meta['index']==i and p['side']==r['side']==meta['side']==side and
             b64_equal(p['c7'],meta['c7']) and b64_equal(p['c7'],p['q'][7]) and
             r.get('exact_symbolic_side_validated') is True and
             r.get('independent_ten_moments_verified') is True and
             r.get('native_boolean_identity_bound') is True,'MIDPOINT_AUDIT_UNBOUND')
        mids.append(load_packet(mid_dir,stem,r['sha256'],p['q'],meta['independent_ten_raw_moments'],
                                meta['moment_jacobian_column7'],binaries,map_identity))
    sides=[]
    for i,(lo,hi) in enumerate(((0,1),(2,3))):
        a,m,b=old[lo],mids[i],old[hi]
        need(all(b64_equal(a['q'][k],m['q'][k]) and b64_equal(b['q'][k],m['q'][k])
                 for k in range(10) if k!=7),'OTHER_COEFFICIENT_CHANGED')
        ledger=side_ledger(a,m,b);ledger['side']='left' if i==0 else 'right'
        # A comparison with the old report must reproduce its floating path.
        earlier=refine['two_refined_sides'][i]
        observed=[ledger['full_interval']]+ledger['two_half_intervals']
        expected=[earlier['full_interval']]+earlier['two_half_intervals']
        for x,y in zip(observed,expected):
            for name in NAMES:
                need(math.isclose(x['components'][name]['binary64_scaled_error'],
                                  y['trapezoid_errors_by_component'][name],rel_tol=2e-7,abs_tol=1e-18),
                     'M19_BINARY64_DIAGNOSTIC_NOT_REPRODUCED:'+name)
        ledger['legacy_ratio_name_was_reciprocal']=True
        sides.append(ledger)
    return {'schema':'heart-h9-m20-exact-difference-rounding-ledger-v1',
            'status':'SIX_SAVED_SURFACES_REINTEGRATED_DIAGNOSTIC_ONLY',
            'stage18_audit_sha256':BASELINE_M18_SHA,
            'm19_plan_sha256':file_hash(plan_path),'m19_refinement_sha256':file_hash(refinement_path),
            'm19_original_launch_sha256':file_hash(run/'launch_result.json'),
            'new_native_calls_this_run':0,'saved_materials_reintegrated':6,
            'packets':[p['evidence'] for p in old+mids],'two_sides':sides,
            'original_materials_and_reports_modified':False,
            'raw_exactness_scope':'INTEGRALS_OF_SAVED_RATIONAL_POLYHEDRA_ONLY',
            'jacobian_scope':'RECORDED_BINARY64_COLUMN7_NOT_EXACT_DERIVATIVE_TRUTH',
            'native_geometry_generation_roundoff_removed':False,
            'runtime_origin_cryptographically_attested':False,
            'continuous_neighborhood_certified':False,'asymptotic_order_certified':False,
            'newton_admitted':False,'final_heart_obj_produced':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage18-audit',required=True,type=Path)
    p.add_argument('--stage17-native-dir',required=True,type=Path)
    p.add_argument('--m19-run',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path,help='NEW directory, not an existing directory')
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    try:
        result=replay(a.stage18_audit,a.stage17_native_dir,a.m19_run)
    except Exception as exc:
        failure={'status':'FAILED_OFFLINE_DIAGNOSTIC_NO_NATIVE_CALLS','reason':f'{type(exc).__name__}: {exc}',
                 'new_native_calls_this_run':0,'newton_admitted':False}
        (a.output/'failure.json').write_text(json.dumps(failure,indent=2,ensure_ascii=False)+'\n')
        raise
    result['diagnostic_script_sha256']=file_hash(__file__)
    with (a.output/'precision-ledger.json').open('x') as f:
        json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    for side in result['two_sides']:
        full=side['full_interval'];halves=side['two_half_intervals']
        print('M20_SIDE',side['side'],flush=True)
        print('  binary64 full / worst-half errors:',full['max_binary64_scaled_error'],
              max(x['max_binary64_scaled_error'] for x in halves),flush=True)
        print('  exact-surface full / worst-half errors:',full['max_exact_surface_scaled_error'],
              max(x['max_exact_surface_scaled_error'] for x in halves),flush=True)
        print('  exact-surface worst-half / full ratio:',side['exact_surface_worst_half_over_full'],flush=True)
        print('  Mzz signed cancellation:',json.dumps(side['signed_cancellation_ledger']['Mzz']),flush=True)
    print('M20_OFFLINE_PRECISION_REPLAY_COMPLETE_NEWTON_DENIED',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())

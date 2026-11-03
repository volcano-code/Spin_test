"""W3 M19: freeze four independently audited H9 packets and plan two same-side midpoints.

Native follow-up uses a separate two-point worker; these calculations alone never
prove a continuous Boolean stratum, validate a Newton step, or generate new data.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import struct
import zipfile

ARTIFACT_SHA = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
# M18 independent-audit result actually reported by the user's W3 workstation.
BASELINE_M18_SHA = '68ee61282caac38d160a4226d9e44df694b7723094890fd62cc61ada434e12e2'
SIDES = ('left-coarse','left-near','right-near','right-coarse')
MID_SIDES = ('left-mid','right-mid')
NAMES = ('mass','Mx','My','Mz','Mxx','Myy','Mzz','Myz','Mxz','Mxy')
SCHEMA = 'heart-h9-m19-two-midpoints-plan-v1'
SHA = re.compile(r'^[0-9a-f]{64}$')


class M19Rejected(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise M19Rejected(code)


def digest(data):
    return sha256(data).hexdigest()


def file_hash(path):
    obj = sha256()
    with Path(path).open('rb') as inp:
        for data in iter(lambda: inp.read(1024 * 1024), b''):
            obj.update(data)
    return obj.hexdigest()


def unique_keys(pairs):
    out = {}
    for name, value in pairs:
        need(name not in out, 'DUPLICATED_JSON_KEY:'+name)
        out[name]=value
    return out


def reject_constant(value):
    raise M19Rejected('NONFINITE_JSON_CONSTANT:'+str(value))


def read_json(path):
    path=Path(path)
    need(path.is_file() and 0 < path.stat().st_size < 16*1024**2,
         'MISSING_OR_OVERSIZE_JSON:'+path.name)
    return json.loads(path.read_bytes(),object_pairs_hook=unique_keys,
                      parse_constant=reject_constant)


def b64_same(a,b):
    return type(a) in (int,float) and type(b) in (int,float) and not isinstance(a,bool) and not isinstance(b,bool) and math.isfinite(a) and math.isfinite(b) and struct.pack('!d',float(a))==struct.pack('!d',float(b))


def vector(a,number=10):
    need(type(a) is list and len(a)==number and all(type(x) in (int,float) and math.isfinite(x) for x in a),
         'NONFINITE_OR_WRONG_LENGTH_VECTOR')
    return [float(v) for v in a]


def midpoint(x,y):
    need(b64_same(x,float(x)) and b64_same(y,float(y)) and x<y,
         'INVALID_MIDPOINT_END_POINTS')
    # Compute rational midpoint of the actual binary64 samples, then round once.
    value=float((Fraction.from_float(float(x))+Fraction.from_float(float(y)))/2)
    need(x<value<y,'M19_MIDPOINT_ROUNDING_NOT_INTERIOR')
    return value


def trapezoid_error(a,b):
    """Finite endpoint/J slope discrepancy. This is *not* smoothness certification."""
    x,y=float(a['c7']),float(b['c7'])
    need(math.isfinite(x) and math.isfinite(y) and 0<y-x<1e-5,'NONINTERIOR_OR_UNEXPECTED_STEP')
    ma=vector(a['moments']);mb=vector(b['moments'])
    ja=vector(a['j7']);jb=vector(b['j7'])
    secant=[(mb[i]-ma[i])/(y-x) for i in range(10)]
    need(all(math.isfinite(v) for v in secant),'NONFINITE_SECANT')
    ea=[abs(secant[i]-ja[i])/max(1.,abs(ja[i])) for i in range(10)]
    eb=[abs(secant[i]-jb[i])/max(1.,abs(jb[i])) for i in range(10)]
    mid=[(ja[i]+jb[i])/2 for i in range(10)]
    em=[abs(secant[i]-mid[i])/max(1.,abs(mid[i])) for i in range(10)]
    need(all(math.isfinite(v) for v in ea+eb+em),'NONFINITE_JACOBIAN_ERROR')
    return {'delta_c7':y-x,'max_endpoint_scaled_error':max(max(ea),max(eb)),
            'max_trapezoid_scaled_error':max(em),'trapezoid_errors_by_component':dict(zip(NAMES,em)),
            'max_trapezoid_component':NAMES[max(range(10),key=lambda k:em[k])]}


def make_midpoint_plan(rows):
    """Rows must be validated first. This cannot certify an input audit alone."""
    need(type(rows) is list and len(rows)==4,'M19_FOUR_BASELINE_ROWS_REQUIRED')
    need([(r.get('index'),r.get('side')) for r in rows]==list(enumerate(SIDES)),
         'M19_BASELINE_SIDE_ORDER_CHANGED')
    outputs=[]
    for idx,(i,j,side) in enumerate(((0,1,'left-mid'),(2,3,'right-mid'))):
        x,y=rows[i]['c7'],rows[j]['c7']
        v=midpoint(x,y)
        q=list(rows[i]['q']);need(len(q)==10,'M19_BASELINE_Q_INVALID')
        q[7]=v
        for k in range(10):
            if k!=7:need(b64_same(q[k],rows[j]['q'][k]),'M19_OTHER_COEFFICIENT_DIFFERS')
        outputs.append({'index':idx,'side':side,'baseline_indices':[i,j],
                        'c7':v,'q':q,'expected_proxy_event_sign':1 if idx==0 else -1,
                        'c7_binary64_hex':struct.pack('!d',v).hex(),
                        'moment_semantics':'SAME_SIDE_FINITE_PROBE_ONLY_NOT_NEWTON'})
    return outputs


def make_science_rows(audit, report, native_dir, base_q):
    need(type(audit) is dict and audit.get('schema')=='heart-h9-independent-new-side-material-audit-v1'
         and audit.get('new_native_samples_reintegrated')==4
         and audit.get('finite_symbolic_branch_split_at_new_four_samples') is True
         and audit.get('every_new_side_reproduces_expected_oriented_edge_sign') is True
         and audit.get('newton_admitted') is False
         and audit.get('continuous_native_boolean_smooth_stratum_proven') is False,
         'M18_INDEPENDENT_FOUR_POINT_AUDIT_NOT_ADMITTED')
    need(report.get('schema')=='heart-h9-crossing-sides-live-v1'
         and report.get('status')=='FOUR_FRESH_REAL_SAMPLES_EVALUATED_NOT_SMOOTH_OR_NEWTON_CERTIFIED'
         and report.get('finished_indices')==[0,1,2,3]
         and report.get('new_real_native_calls')==4
         and report.get('newton_admitted') is False,
         'M18_NATIVE_PRODUCER_REPORT_NOT_COMPLETE')
    binary=report.get('binary_hashes')
    need(type(binary) is dict and set(binary)=={'core','boolean','arithmetic'}
         and all(type(x) is str and SHA.fullmatch(x) for x in binary.values()),
         'M18_BINARY_SHA_MISSING')
    rows=audit.get('sample_diagnostics');need(type(rows) is list and len(rows)==4,
                                             'M18_SAMPLE_DIAGNOSTICS_MISSING')
    plans=report.get('plan');need(type(plans) is list and len(plans)==4,
                                 'M18_PROBE_PLAN_MISSING')
    need(type(audit.get('new_native_evaluation_map_identity')) is str
         and SHA.fullmatch(audit['new_native_evaluation_map_identity']),
         'M18_EVALUATION_MAP_IDENTITY_MISSING')
    baseline=[]
    for i,side in enumerate(SIDES):
        stem=f'side-{i:02d}-{side}'
        meta=read_json(Path(native_dir)/(stem+'.json'))
        packed=Path(native_dir)/(stem+'.json.gz')
        need(packed.is_file(),'M18_MATERIAL_GZIP_MISSING:'+stem)
        material_sha=file_hash(packed)
        need(material_sha==meta.get('material_sha256')==rows[i].get('new_same_call_material_sha256'),
             'M18_MATERIAL_SHA_NOT_BOUND:'+stem)
        with gzip.open(packed,'rb') as f:
            material=json.load(f,object_pairs_hook=unique_keys,parse_constant=reject_constant)
        need(meta.get('index')==i and meta.get('side')==side
             and rows[i].get('index')==i and rows[i].get('side')==side
             and plans[i].get('index')==i and plans[i].get('side')==side
             and b64_same(meta.get('c7'),plans[i].get('c7'))
             and b64_same(rows[i].get('c7'),meta.get('c7')),
             'M18_SIDE_PLAN_DRIFT:'+stem)
        q=vector(meta.get('q'))
        need(all(b64_same(q[k],base_q[k]) for k in range(10) if k!=7)
             and b64_same(q[7],meta['c7'])
             and all(b64_same(x,y) for x,y in zip(q,vector(material.get('quadric_coefficients')))),
             'M18_SAME_CALL_FULL_Q_NOT_BOUND:'+stem)
        need(material.get('evaluation_map_identity')==audit['new_native_evaluation_map_identity']
             and material.get('boolean_backend_identity')==
                'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'+binary['boolean']
             and material.get('rational_arithmetic_identity',{}).get('module_sha256')==binary['arithmetic']
             and material.get('rational_arithmetic_identity',{}).get('backend')=='NATIVE_GMP_SURFACE_V1',
             'M18_UNBOUND_CURRENT_NATIVE_PROVENANCE:'+stem)
        moments=vector(rows[i].get('recomputed_exact_moments'))
        jac=vector(rows[i].get('native_recorded_jacobian_col7'))
        baseline.append({'index':i,'side':side,'c7':meta['c7'],'q':q,
                         'moments':moments,'j7':jac,'material_sha256':material_sha})
    return baseline,binary


def generate_plan(artifact, certificate, stage18_audit, stage17_native_dir, expected_audit_sha=BASELINE_M18_SHA):
    """Rebind all four real M18 packets before scheduling any additional native work."""
    from h9_frozen_input_gate import validate_pair
    artifact,certificate,stage18_audit=map(Path,(artifact,certificate,stage18_audit))
    need(file_hash(artifact)==ARTIFACT_SHA,'M19_HISTORICAL_ARTIFACT_SHA_MISMATCH')
    frozen=validate_pair(artifact,certificate)
    need(file_hash(stage18_audit)==expected_audit_sha,'M19_INDEPENDENT_AUDIT_SHA_MISMATCH')
    audit=read_json(stage18_audit)
    old_native_dir=Path(stage17_native_dir)
    producer=old_native_dir/'report.json'
    need(producer.is_file() and file_hash(producer)==audit.get('new_native_run_report_sha256'),
         'M18_PRODUCER_REPORT_SHA_DRIFT')
    report=read_json(producer)
    with zipfile.ZipFile(artifact) as z:
        old_report=json.loads(z.read('artifacts/h8f-all81-points/report.json'))
    base_q=vector(old_report['target_q'])
    baseline,binaries=make_science_rows(audit,report,old_native_dir,base_q)
    frozen_plan=frozen['four_new_native_probe_plan']
    need(len(frozen_plan)==4 and all(b64_same(baseline[i]['c7'],frozen_plan[i]['c7'])
                                      for i in range(4)), 'M19_ORIGINAL_POINT_VALUES_DRIFT')
    return {'schema':SCHEMA,'status':'READY_FOR_TWO_NEW_CHERCHI_MIDPOINT_TRIALS_NOT_NEWTON',
            'original_h8f_artifact_sha256':ARTIFACT_SHA,
            'original_certificate_sha256':file_hash(certificate),
            'stage18_independent_audit_sha256':file_hash(stage18_audit),
            'stage17_real_producer_report_sha256':file_hash(producer),
            'stage17_current_binary_sha256':binaries,
            'stage18_current_evaluation_map_identity':audit['new_native_evaluation_map_identity'],
            'baseline_four_real_rows':baseline,
            'predeclared_two_midpoints':make_midpoint_plan(baseline),
            'new_native_points_issued_by_plan':0,'continuous_neighborhood_certified':False,
            'newton_admitted':False,'final_heart_obj_produced':False}


def compare_refinement(plan, new_rows):
    """Pure comparison of *already independently checked* M19 rows."""
    need(type(plan) is dict and plan.get('schema')==SCHEMA and plan.get('newton_admitted') is False,
         'M19_PLAN_INVALID')
    originals=plan['baseline_four_real_rows']; proposals=plan['predeclared_two_midpoints']
    need(type(new_rows) is list and len(new_rows)==2,'M19_TWO_NEW_ROWS_REQUIRED')
    out=[]
    for n,(lo,hi) in enumerate(((0,1),(2,3))):
        new=new_rows[n];candidate=proposals[n]
        need(new.get('side')==candidate['side'] and b64_same(new.get('c7'),candidate['c7'])
             and type(new.get('index')) is int and new['index']==n,
             'M19_NEW_SIDE_IDENTITY_WRONG')
        base_l,base_h=originals[lo],originals[hi]
        top=trapezoid_error(base_l,base_h)
        left=trapezoid_error(base_l,new);right=trapezoid_error(new,base_h)
        half_max=max(left['max_trapezoid_scaled_error'],right['max_trapezoid_scaled_error'])
        ratio=top['max_trapezoid_scaled_error']/half_max if half_max>0 else None
        out.append({'side':'left' if n==0 else 'right',
                    'baseline_indices':[lo,hi],
                    'new_midpoint_c7':new['c7'],
                    'full_interval':top,'two_half_intervals':[left,right],
                    'half_vs_full_trapezoid_max_error_ratio':ratio,
                    'observed_refinement_only_no_asymptotic_rate_claim':True,
                    'newton_admitted':False})
    return {'schema':'heart-h9-m19-finite-refinement-diagnostics-v1',
            'two_refined_sides':out,'newton_admitted':False,
            'continuous_neighborhood_certified':False,
            'result_interpretation':'FINITE_SAME_SIDE_TWO_SCALE_DIAGNOSTIC_ONLY'}


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--artifact',required=True)
    ap.add_argument('--certificate',required=True)
    ap.add_argument('--stage18-audit',required=True)
    ap.add_argument('--stage17-native-dir',required=True)
    ap.add_argument('--output',required=True)
    ap.add_argument('--expected-audit-sha256',default=BASELINE_M18_SHA)
    args=ap.parse_args(argv)
    output=Path(args.output)
    need(not output.exists(),'M19_REFUSE_OVERWRITE_EXISTING_PLAN')
    plan=generate_plan(args.artifact,args.certificate,args.stage18_audit,args.stage17_native_dir,
                       args.expected_audit_sha256)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf8') as f:
        json.dump(plan,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')
    print('M19_TWO_SIDE_MIDPOINTS_PLANNED_NO_NATIVE_CALLS',len(plan['predeclared_two_midpoints']))
    return 0


if __name__=='__main__':raise SystemExit(main())

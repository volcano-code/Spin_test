"""W3 H9 M21.6B: diagnostic ten-moment / J7 layer decomposition, no native calls.

Inputs: frozen six Cherchi material packets, source-only motion attachments, M20
exact-ten-moment ledger and M21.6A full-boundary report. Every known byte
identity is checked using pre-existing W3 readers before any computation.

This is NOT a certificate of continuous Boolean smoothness or Newton admission.
The *independently replayed* source motion is binary64, not an oracle. The
face-class contributions show sensitivity/cancellation and do NOT assign the
production C++ Jacobian mismatch to a particular face class.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
import json
import math
from pathlib import Path

NAMES = ('mass','Mx','My','Mz','Mxx','Myy','Mzz','Myz','Mxz','Mxy')
PAIRS = ((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))
GROUPS = ('EXPLICIT_ONLY', 'LPI_ONLY', 'MIXED_EXPLICIT_LPI', 'TPI_TOUCHING')
STEMS = ('side-00-left-coarse','side-01-left-near','side-02-right-near',
         'side-03-right-coarse','m19-mid-00-left-mid','m19-mid-01-right-mid')
SIDES = {'left': (0,4,1), 'right': (2,5,3)}
BINARY_SHA = 'd66ce44c42f66a875298ae271dda76c12d5f3660bd3d13a1089d4fdd152063fd'
LEDGER_SHA = '95bf2c6d91862bba488dd56118562a1fad826037966ed3f8f0bf382e5fba0703'
LPI_SHA = 'd353486cafb3b81a97c302c51d8a034eedee327fabe92f2497df2c48b49c522e'
BOUNDARY_SHA = '759b4df5111fa51e0d51f1e62ff36b5c84e02e85f13d6e3fc5edece95dbab793'

class Refused(ValueError):
    pass

def need(ok, message):
    if not ok: raise Refused(message)

def q(x):
    if isinstance(x,F): return x
    if type(x) is int: return F(x)
    if type(x) is float:
        need(math.isfinite(x),'NONFINITE_FLOAT')
        return F.from_float(x)
    need(type(x) is str and 0 < len(x) < 100000,'INVALID_EXACT_INPUT')
    # Fraction accepts decimal strings; this diagnostic deliberately forbids them.
    bits=x.split('/')
    need(len(bits)==2 and bits[0].lstrip('-').isascii() and
         bits[0].lstrip('-').isdigit() and bits[1].isascii() and
         bits[1].isdigit() and int(bits[1])>0,'INVALID_RATIONAL_TOKEN')
    return F(int(bits[0]),int(bits[1]))

def token(x):
    x=q(x);return f'{x.numerator}/{x.denominator}'

def v3(xs):
    need(isinstance(xs,(list,tuple)) and len(xs)==3,'BAD_VECTOR3')
    return tuple(q(x) for x in xs)

def digest(path):
    h=sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def strict_json(path, expected_sha):
    path=Path(path)
    need(path.is_file() and not path.is_symlink() and 0<path.stat().st_size<64*1024**2,
         'MISSING_OR_UNSAFE_INPUT:'+str(path))
    need(digest(path)==expected_sha,'SHA_MISMATCH:'+path.name)
    def unique(pairs):
        d={}
        for k,v in pairs:
            need(k not in d,'DUPLICATE_JSON_KEY:'+k)
            d[k]=v
        return d
    def invalid(s):raise Refused('INVALID_JSON_CONSTANT:'+s)
    return json.loads(path.read_bytes(),object_pairs_hook=unique,parse_constant=invalid)

class Dual:
    __slots__=('x','d')
    def __init__(self,x,d=0): self.x,self.d=q(x),q(d)
    def __add__(self,other):
        if not isinstance(other,Dual):other=Dual(other)
        return Dual(self.x+other.x,self.d+other.d)
    __radd__=__add__
    def __neg__(self):return Dual(-self.x,-self.d)
    def __sub__(self,other):return self+(-other if isinstance(other,Dual) else -q(other))
    def __mul__(self,other):
        if not isinstance(other,Dual):other=Dual(other)
        return Dual(self.x*other.x,self.d*other.x+self.x*other.d)
    __rmul__=__mul__
    def __truediv__(self,other):
        need(type(other) is int and other>0,'DUAL_ONLY_POSITIVE_INT_SCALING')
        return Dual(self.x/other,self.d/other)

def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])

def dot(a,b):return sum((x*y for x,y in zip(a,b)),Dual(0))

def face_ten(p,v,density=F(1)):
    """Independent dual-number AD of oriented tetrahedron moment polynomial."""
    need(len(p)==len(v)==3,'BAD_TRIANGLE')
    a,b,c=[tuple(Dual(x,d) for x,d in zip(v3(point),v3(speed)))
           for point,speed in zip(p,v)]
    det=dot(a,cross(b,c))
    sums=[a[i]+b[i]+c[i] for i in range(3)]
    moments=[det/6]+[det*sums[i]/24 for i in range(3)]
    for i,j in PAIRS:
        diag=sum((point[i]*point[j] for point in (a,b,c)),Dual(0))
        moments.append(det*(sums[i]*sums[j]+diag)/120)
    density=q(density)
    return [tuple((x.x*density,x.d*density)) for x in moments]

class BinSum:
    def __init__(self):self.parts=[]
    def add(self,x):
        if not x:return
        i=0
        while i<len(self.parts) and self.parts[i] is not None:
            x+=self.parts[i];self.parts[i]=None;i+=1
        if i==len(self.parts):self.parts.append(x)
        else:self.parts[i]=x
    def result(self):return sum((p for p in self.parts if p is not None),F(0))

def kind_group(keys):
    kinds={k[0] for k in keys}
    need(kinds <= {'EXPLICIT3D','LPI','TPI'} and len(keys)==3,'UNKNOWN_FACE_KIND')
    if 'TPI' in kinds:return 'TPI_TOUCHING'
    if kinds=={'EXPLICIT3D'}:return 'EXPLICIT_ONLY'
    if kinds=={'LPI'}:return 'LPI_ONLY'
    return 'MIXED_EXPLICIT_LPI'

def grouped_faces(state,density=1):
    """Streaming exact sums; no per-face evidence or slot-correspondence guesses."""
    p,v=state['positions'],state['motion']
    need(isinstance(p,dict) and isinstance(v,dict) and p.keys()==v.keys(),
         'MISSING_EXACT_BOUNDARY_MOTION')
    slots=state['slotkeys'];faces=state['faces']
    require_semantics=Counter()
    acc={group:[[BinSum(),BinSum()] for _ in NAMES] for group in GROUPS}
    counts=Counter()
    for face in faces:
        need(type(face) is list and len(face)==3 and len(set(face))==3 and
             all(type(i) is int and 0<=i<len(slots) for i in face),'BAD_FACE')
        keys=[slots[i] for i in face]
        need(all(k in p for k in keys),'FACE_REFERENCES_MISSING_CONSTRUCTION')
        semantic=min(tuple(keys),tuple(keys[1:]+keys[:1]),tuple(keys[2:]+keys[:2]))
        require_semantics[semantic]+=1
        group=kind_group(keys)
        counts[group]+=1
        for n,(val,der) in enumerate(face_ten([p[k] for k in keys],[v[k] for k in keys],density)):
            acc[group][n][0].add(val)
            acc[group][n][1].add(der)
    need(require_semantics==state['semantic_triangles'],'SEMANTIC_TRIANGLES_MISMATCH')
    grouped={g:{'faces':counts[g],'moments':[a.result() for a,b in acc[g]],
                'j7':[b.result() for a,b in acc[g]]} for g in GROUPS}
    total={'moments':[sum((grouped[g]['moments'][k] for g in GROUPS),F(0)) for k in range(10)],
           'j7':[sum((grouped[g]['j7'][k] for g in GROUPS),F(0)) for k in range(10)],
           'faces':len(faces)}
    need(sum(counts.values())==total['faces'],'FACE_GROUP_COVERAGE_FAILURE')
    return grouped,total

def numeric_vector(xs):return [float(x) for x in xs]

def exact_vector(xs):return [token(x) for x in xs]

def max_scaled(xs,scale):return max(float(abs(x)/s) for x,s in zip(xs,scale))

def layer_interval(a,b,*,side,interval,ledger_side=None):
    h=q(b['c7'])-q(a['c7']);need(h>0,'NONPOSITIVE_INTERVAL')
    need(a['face_counts']==b['face_counts'],'FACE_KIND_COUNTS_CHANGED')
    native=[];independent=[];delta=[];group_residual={}
    for g in GROUPS:
        x,y=a['groups'][g],b['groups'][g]
        group_residual[g]=[(y['moments'][k]-x['moments'][k])/h-(x['j7'][k]+y['j7'][k])/2
                           for k in range(10)]
    for k in range(10):
        sec=(b['exact'][k]-a['exact'][k])/h
        avg_native=(a['native'][k]+b['native'][k])/2
        avg_ind=(a['total']['j7'][k]+b['total']['j7'][k])/2
        native.append(sec-avg_native)
        independent.append(sec-avg_ind)
        delta.append(avg_ind-avg_native)
        need(native[-1] == independent[-1]+delta[-1], 'TOTAL_MOMENT_ERROR_SPLIT_FAILED')
        need(independent[-1]==sum((group_residual[g][k] for g in GROUPS),F(0)),
             'FACE_CLASS_SUM_NOT_TOTAL')
    scale=[max(F(1),abs((a['native'][k]+b['native'][k])/2)) for k in range(10)]
    if ledger_side is not None:
        need(ledger_side['side']==side,'LEDGER_SIDE_MISMATCH')
        row=ledger_side['full_interval'] if interval=='full' else ledger_side['two_half_intervals'][0 if interval=='first-half' else 1]
        need(q(row['delta_c7_exact'])==h,'LEDGER_DELTA_MISMATCH')
        for k,name in enumerate(NAMES):
            need(float(native[k])==row['components'][name]['exact_surface_signed_residual'],
                 'M20_SAVED_NATIVE_RESIDUAL_MISMATCH:'+name)
    priority=sorted(range(10),key=lambda k:float(abs(native[k])/scale[k]),reverse=True)
    rows={name:{'native_j7_residual_exact':token(native[k]),
                'replayed_j7_residual_exact':token(independent[k]),
                'replayed_minus_native_endpoint_j7_exact':token(delta[k]),
                'group_residuals_exact':{g:token(group_residual[g][k]) for g in GROUPS},
                'scaled_native_residual':float(abs(native[k])/scale[k]),
                'scaled_replayed_residual':float(abs(independent[k])/scale[k]),
                'scaled_j7_disagreement':float(abs(delta[k])/scale[k])}
          for k,name in enumerate(NAMES)}
    return {'side':side,'interval':interval,'from_stem':a['stem'],'to_stem':b['stem'],
            'delta_c7_exact':token(h),'component_diagnostics':rows,
            'worst_native_component':NAMES[priority[0]],
            'max_native_scaled_residual':max_scaled(native,scale),
            'max_independent_scaled_residual':max_scaled(independent,scale),
            'max_endpoint_j7_disagreement_scaled':max_scaled(delta,scale),
            'largest_component_residuals':[NAMES[k] for k in priority[:3]],
            'ten_component_exact_layer_identites_verified':10,
            'interpretation':'Finite saved surfaces and replayed source tangents only; no continuous branch certificate',
            'newton_admitted':False}

def verify_report_inputs(boundary,ledger,materials,motion_metadata=None):
    if motion_metadata is None:
        motion_metadata=materials
    need(len(motion_metadata)==6,'SIX_MOTION_METADATA_REQUIRED')
    need(boundary['schema']=='heart-h9-m21-6a-all-retained-boundary-motion-v1' and
         boundary['status']=='SIX_SAVED_PACKETS_FULL_BOUNDARY_DISCRETE_MOTION_DIAGNOSTIC_ONLY' and
         boundary['sample_count']==6 and len(boundary['intervals'])==6 and
         boundary['claims']['newton_admitted'] is False and
         boundary['claims']['root_cause_determined'] is False and
         boundary['claims']['new_boolean_calls']==0 and
         boundary['inputs']['precision_ledger_sha256']==LEDGER_SHA and
         boundary['inputs']['native_source_core_sha256']==BINARY_SHA and
         boundary['inputs']['m21_5b_lpi_sha256']==LPI_SHA and
         boundary['inputs']['six_material_sha256']==[x['material_sha256'] for x in ledger['packets']] and
         boundary['inputs']['six_motion_sha256']==[x['attachment_sha256'] for x in motion_metadata] and
         boundary['inputs']['full_raw_six_packet_bytes_read'] is True and
         boundary['inputs']['all_source_only_motion_attestations_replayed_and_hash_bound'] is True and
         boundary['inputs']['runtime_origin_cryptographically_attested'] is False,
         'BOUNDARY_OR_MATERIAL_IDENTITY_MISMATCH')
    for i,(s,e,p) in enumerate(zip(boundary['samples'],motion_metadata,ledger['packets'])):
        need(s['stem']==e['stem']==p['stem'] and e['material_sha256']==p['material_sha256'] and
             s['retained_vertex_count']==8455 and
             s['source_vertex_count']==162 and s['construction_counts']=={'EXPLICIT3D':7671,'LPI':784},
             'BOUNDARY_SAMPLE_SHAPE_CHANGED:'+str(i))

def compute(states,materials,ledger,boundary,density=1,motion_metadata=None):
    need(len(states)==len(materials)==len(ledger['packets'])==6 and len(boundary['intervals'])==6,
         'SIX_SAVED_PACKETS_REQUIRED')
    need(q(density)==1,'DENSITY_CONTRACT_CHANGED')
    verify_report_inputs(boundary,ledger,materials,motion_metadata)
    for side,sequence in SIDES.items():
        baseline=states[sequence[0]]
        for index in sequence[1:]:
            state=states[index]
            need(baseline['positions'].keys()==state['positions'].keys() and
                 baseline['semantic_triangles']==state['semantic_triangles'] and
                 baseline['source_faces']==state['source_faces'],
                 'CHANGED_ORIENTED_GEOMETRY_OR_CONSTRUCTION:'+side)
    prepared=[]
    for i,(state,mat,packet) in enumerate(zip(states,materials,ledger['packets'])):
        need(state['motion'] is not None and len(state['positions'])==8455 and
             len(state['source'])==162 and state['kinds']=={'EXPLICIT3D':7671,'LPI':784},
             'UNEXPECTED_FULL_BOUNDARY_STATE')
        groups,total=grouped_faces(state,density)
        exact=[q(x) for x in packet['exact_ten_moments']]
        need(total['moments']==exact,'LEDGER_TEN_MOMENTS_MISMATCH:'+str(i))
        native=[q(row[7]) for row in mat['moment_jacobian']]
        need(len(native)==10,'J7_DIMENSION')
        # Recompute independently against the retained-construction derivative.
        from h9_m21_motion_math import moment_tangent
        previous,active=moment_tangent(state,density)
        need(total['j7']==previous,'DUAL_AD_VS_RETAINED_TANGENT_MISMATCH')
        prepared.append({'stem':STEMS[i],'c7':state['c7'],'groups':groups,'total':total,
                         'face_counts':{g:groups[g]['faces'] for g in GROUPS},
                         'exact':exact,'native':native,'active_faces':active})
    intervals=[]
    for side,seq in SIDES.items():
        scope=next(x for x in ledger['two_sides'] if x['side']==side)
        for label,i,j in (('full',0,2),('first-half',0,1),('second-half',1,2)):
            a,b=prepared[seq[i]],prepared[seq[j]]
            row=layer_interval(a,b,side=side,interval=label,ledger_side=scope)
            reference=boundary['intervals'][len(intervals)]
            need(all(row[k]==reference[k] for k in ('side','interval','from_stem','to_stem','delta_c7_exact')),
                 'M21_6A_INTERVAL_IDENTITY_DRIFT')
            intervals.append(row)
    results=[]
    for state in prepared:
        mismatch=[a-b for a,b in zip(state['total']['j7'],state['native'])]
        scale=[max(F(1),abs(r)) for r in state['native']]
        results.append({'stem':state['stem'],'face_counts':state['face_counts'],
                        'active_faces':state['active_faces'],
                        'max_native_vs_independent_j7_scaled':max_scaled(mismatch,scale),
                        'exact_native_j7_difference':exact_vector(mismatch),
                        'face_group_moment_j7_summary':{g:{'face_count':state['groups'][g]['faces'],
                            'j7_contributions_exact':exact_vector(state['groups'][g]['j7'])}
                            for g in GROUPS},
                        'exact_moment_ledger_reintegration_match':True,
                        'dual_vs_existing_retained_tangent_exact_match':True})
    return {'schema':'heart-h9-m21-6b-moment-layer-audit-v1',
            'status':'SIX_SAVED_SURFACES_FACE_GROUP_TEN_MOMENT_J7_DIAGNOSTIC_ONLY',
            'sample_count':6,'samples':results,'intervals':intervals,
            'input_sha256':{'m20_ledger':LEDGER_SHA,'m21_6a_full_boundary':BOUNDARY_SHA,
                            'native_core':BINARY_SHA,'m21_5b_lpi':LPI_SHA},
            'face_group_keys':list(GROUPS),
            'total_component_split_checks':60,
            'scientific_limits':{'root_cause_determined':False,
                                 'continuous_neighborhood_certified':False,
                                 'asymptotic_order_certified':False,
                                 'newton_admitted':False,
                                 'final_heart_obj_produced':False,
                                 'new_boolean_calls_this_run':0,
                                 'new_native_source_calls_this_run':0,
                                 'native_runtime_origin_cryptographically_attested':False,
                                 'per_group_native_jacobian_available':False,
                                 'face_group_residual_is_not_unique_causal_attribution':True}}

def preview_derived(boundary_path, ledger_path, lpi_path):
    """Independent real-data *derived* report check, no original source packets.

    Do not use this phase to claim J7 truth: full grouped moments and ten-moment
    derivatives require reading the original six raw materials in native-layers.
    """
    boundary=strict_json(boundary_path,BOUNDARY_SHA)
    ledger=strict_json(ledger_path,LEDGER_SHA)
    lpi=strict_json(lpi_path,LPI_SHA)
    need(ledger['schema']=='heart-h9-m20-exact-difference-rounding-ledger-v1' and
         ledger['saved_materials_reintegrated']==6 and ledger['newton_admitted'] is False,
         'UNQUALIFIED_EXACT_LEDGER')
    need(lpi['schema']=='heart-h9-m21-3-selected-lpi-motion-v1' and
         lpi['status']=='SIX_SAVED_PACKETS_THREE_LPI_DIAGNOSTIC_ONLY' and
         len(lpi['samples'])==6 and lpi['newton_admitted'] is False,
         'UNQUALIFIED_M21_5B_LPI')
    meta=[{'stem':sample['stem'],'material_sha256':sample['material_sha256'],
           'attachment_sha256':sample['attachment_sha256']} for sample in lpi['samples']]
    verify_report_inputs(boundary,ledger,meta)
    need(len(boundary['full_half_exact_partition_checks'])==2,
         'INCOMPLETE_PARTITION_CHECKS')
    for side,partition in zip(SIDES,boundary['full_half_exact_partition_checks']):
        need(partition['side']==side and partition['exact_partition_identities_verified']==8617 and
             partition['source']['count']==162 and partition['groups']['EXPLICIT3D']['count']==7671 and
             partition['groups']['LPI']['count']==784 and partition['groups']['TPI']['count']==0,
             'PARTITION_INVALID_OR_UNEXPECTED_COUNT')
    checked=0;intervals=[]
    for i,row in enumerate(boundary['intervals']):
        side=('left' if i<3 else 'right')
        label=('full','first-half','second-half')[i%3]
        ref=lpi['same_side_interval_lpi_secants'][i]
        need(row['side']==ref['side']==side and row['interval']==ref['interval']==label and
             row['from_stem']==ref['from_stem'] and row['to_stem']==ref['to_stem'] and
             q(row['delta_c7_exact'])==q(ref['features']['Repeated']['delta_c7']),
             'LPI_FULL_BOUNDARY_INTERVAL_IDENTITY_MISMATCH')
        need(row['same_retained_constraints_and_oriented_triangles'] is True and
             row['continuously_smooth_stratum_certified'] is False and row['newton_admitted'] is False,
             'UNSAFE_INTERVAL_CLAIMS')
        need(row['retained_vertex_count']==8455,'INCOMPLETE_BOUNDARY')
        for kind,n in (('EXPLICIT3D',7671),('LPI',784),('TPI',0)):
            need(row['group_residuals'][kind]['count']==n,
                 'MISSING_GROUP_ROWS:'+kind)
        need(row['source_residuals']['count']==162,'SOURCE_COUNT_CHANGED')
        for group in (*[row['group_residuals'][k] for k in ('EXPLICIT3D','LPI','TPI')],row['source_residuals']):
            need(0<=len(group['top'])<=group['count'] and
                 group['max_residual_norm']>=0 and math.isfinite(group['max_residual_norm']),
                 'INVALID_GROUP_RESIDUALS')
            for witness in group['top']:
                residual=v3(witness['signed_residual_exact'])
                norm=math.sqrt(float(sum((x*x for x in residual),F(0))))
                need(math.isclose(norm,witness['residual_norm'],rel_tol=1e-13,abs_tol=1e-15) and
                     norm<=group['max_residual_norm']*(1+1e-12)+1e-18,
                     'INVALID_EXACT_WITNESS_NORM')
                checked+=1
        intervals.append({'side':side,'interval':label,
            'max_source_residual':row['source_residuals']['max_residual_norm'],
            'max_explicit_residual':row['group_residuals']['EXPLICIT3D']['max_residual_norm'],
            'max_lpi_residual':row['group_residuals']['LPI']['max_residual_norm'],
            'rms_explicit_residual':row['group_residuals']['EXPLICIT3D']['rms_residual_norm'],
            'rms_lpi_residual':row['group_residuals']['LPI']['rms_residual_norm']})
    return {'schema':'heart-h9-m21-6b-derived-preview-v1',
            'status':'M21_6A_DERIVED_MOTION_RECHECKED_J7_LAYERS_NOT_RUN',
            'input_sha256':{'m21_6a_boundary':BOUNDARY_SHA,'m20_ledger':LEDGER_SHA,
                            'm21_5b_lpi':LPI_SHA},
            'samples_verified':6,'intervals_verified':6,'exact_top_witness_norms_verified':checked,
            'intervals':intervals,
            'next_gate':'SIX_RAW_MATERIALS_AND_SOURCE_MOTION_FOR_TEN_MOMENT_J7_FACE_LAYERS',
            'claims':{'newton_admitted':False,'continuous_neighborhood_certified':False,
                      'root_cause_determined':False,'new_boolean_calls':0,
                      'new_native_source_calls':0,'native_j7_layer_comparison_done':False}}

def run(args):
    from h9_m21_layered_replay import (LEDGER_SHA as OLD_LEDGER_SHA,STEMS as OLD_STEMS,
                                       load_ledger,load_six,frozen_request,bind_file,dump)
    from h9_m21_3_lpi import source_rows,read_motion
    from h9_m21_motion_math import material_state
    need(OLD_LEDGER_SHA==LEDGER_SHA and OLD_STEMS==STEMS,'UPSTREAM_PROVENANCE_CHANGED')
    need(args.output.parent.is_dir() and not args.output.exists(),
         'OUTPUT_EXISTS_OR_PARENT_MISSING')
    ledger=load_ledger(args.precision_ledger)
    boundary=strict_json(args.boundary_report,BOUNDARY_SHA)
    request=frozen_request(args.artifact)['request']
    need(q(request['material_density'])==1,'DENSITY_CHANGED')
    raw,plan,_=load_six(args,ledger)
    core=plan['stage17_current_binary_sha256']['core']
    need(core==BINARY_SHA,'NATIVE_CORE_DRIFT')
    summary=strict_json(args.source_run/'layered-report.json',
                        digest(args.source_run/'layered-report.json'))
    worker=args.source_run/'worker'
    report=strict_json(bind_file(worker/'layered-report.json',summary['worker_report_sha256']),
                       summary['worker_report_sha256'])
    rows=source_rows(report,core)
    states=[]; metadata=[]
    for (material,_,ev),row in zip(raw,rows):
        speed=read_motion(worker,row,ev,core)
        states.append(material_state(material,request,speed))
        metadata.append({'stem':ev['stem'],'material_sha256':ev['material_sha256'],
                         'attachment_sha256':row['source_motion_attachment_sha256']})
    output=compute(states,[m for m,_,_ in raw],ledger,boundary,request['material_density'],metadata)
    return output

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=('preview','native-layers'),default='native-layers')
    for name in ('precision-ledger','lpi-report','artifact','stage17-native-dir','m19-run',
                 'source-run','boundary-report','output'):
        parser.add_argument('--'+name,type=Path)
    args=parser.parse_args(argv)
    required=('precision_ledger','boundary_report','output')
    if args.phase=='native-layers':
        required+=('artifact','stage17_native_dir','m19_run','source_run')
    else:required+=('lpi_report',)
    for key in required:
        if getattr(args,key) is None: parser.error('missing required --'+key.replace('_','-'))
    need(args.output.parent.is_dir() and not args.output.exists(),
         'OUTPUT_EXISTS_OR_PARENT_MISSING')
    if args.phase=='preview':
        out=preview_derived(args.boundary_report,args.precision_ledger,args.lpi_report)
    else:out=run(args)
    # Use the pre-existing W3 atomic/create-only writer for the six raw-material
    # path; a preview without native readers gets the same exclusive semantics.
    with args.output.open('x',encoding='utf8') as f:
        json.dump(out,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')
    print('M21_6B_STATUS',out['status'])
    print('M21_6B_SAMPLES',out.get('sample_count',out.get('samples_verified')))
    print('M21_6B_INTERVALS',len(out['intervals']))
    print('M21_6B_NEWTON',False)
    return 0

if __name__=='__main__':raise SystemExit(main())

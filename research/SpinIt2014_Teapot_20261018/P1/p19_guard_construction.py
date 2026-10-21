"""P19: registered dyadic guards and three genuine pinned Cherchi operations.

Every output is a new candidate.  No saved mesh is silently welded, repaired,
or substituted.  Native success alone never grants material/physics admission.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

from p17_boundary_certificate import read_binary64_obj
from p18_exact_surface import audit_exact_surface
from p18_solid_domain import exact_signed_volume


P18_COMMIT = 'b33fc93bd1fecd5b42fbd8d2eabfefd6ec9db7be'
SOURCE_MANIFEST_SHA = '3eef5e245590ebee18ea46e1f0198c81d73c17ffbbb064143a6ceb95a00d5a70'
SOURCES = {
    'old_outer': ('material/M_repaired_outer.obj', '4c2e4d480d1041f4817128a8b4b61675d80a699e448e7a5a253311c1805a3aa2'),
    'cavity': ('source/D-hypothesis.obj', 'c18b4ac3a9fb71e6169c975e6baab1e487f7d148af908ee4eac4df4077121452'),
    'shaft': ('source/shaft-reference.obj', '65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0'),
}
SCHEMA = 'W4P19DyadicGuardNativeConstructionV1'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_new_json(path, data):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def registered_plan():
    """Exact parameters registered before any P19 Teapot native operation."""
    return {
        'schema': 'W4P19PositiveGapConstructionPlanV1',
        'source_P18_commit': P18_COMMIT,
        'source_P17_manifest_sha256': SOURCE_MANIFEST_SHA,
        'sources': {k: {'path': p, 'sha256': h} for k, (p, h) in SOURCES.items()},
        'outer_collars': {
            'cross_section': 'DYADIC_CONVEX_OCTAGON',
            'a': '1/16', 'b': '13/512',
            'polygon_ccw': [['1/16','13/512'], ['13/512','1/16'],
                ['-13/512','1/16'], ['-1/16','13/512'],
                ['-1/16','-13/512'], ['-13/512','-1/16'],
                ['13/512','-1/16'], ['1/16','-13/512']],
            'z_intervals': [['153/1024','157/1024'], ['1439/1024','1443/1024']],
            'maximum_radial_extent_squared_exact': str(Fraction(1,16)**2+Fraction(13,512)**2),
            'scope': 'TWO_LOCAL_SHAFT_BODY_JUNCTION_COLLARS_NOT_WHOLE_TEAPOT_SCALING',
        },
        'inner_guard': {
            'cross_section': 'DYADIC_AXIS_ALIGNED_SQUARE',
            'half_width': '1/16', 'z_interval': ['3/8','1'],
            'polygon_ccw': [['-1/16','-1/16'], ['1/16','-1/16'],
                            ['1/16','1/16'], ['-1/16','1/16']],
        },
        'minimum_design_to_original_shaft_gap_reference': '1/500',
        'minimum_gap_is_not_maximum_shape_change_budget': True,
        'outer_shape_and_volume_changes_must_be_reported_separately': True,
        'native_operations': [
            {'op': 'union', 'inputs': ['old_outer','lower_collar','upper_collar'], 'output': 'M.obj'},
            {'op': 'subtraction', 'inputs': ['cavity','inner_guard'], 'output': 'D.obj'},
            {'op': 'subtraction', 'inputs': ['M.obj','D.obj'], 'output': 'F.obj'},
        ],
        'native_timeout_seconds_per_call': 120,
        'native_calls_serial': True,
        'automatic_mesh_postprocess_allowed': False,
        'W0_physical_approval': False,
        'W2_Teapot_teacher_admission': False,
        'optimization_admitted': False,
        'training_admitted': False,
    }


def write_dyadic_prism(path, polygon, zlo, zhi):
    """Write one convex prism with exact dyadic coordinates and explicit caps."""
    poly = [tuple(Fraction(c) for c in p) for p in polygon]
    zlo, zhi = Fraction(zlo), Fraction(zhi)
    if len(poly) < 3 or zlo >= zhi or any(len(p)!=2 for p in poly):
        raise ValueError('INVALID_PRISM_DIMENSIONS')
    if len(set(poly)) != len(poly):
        raise ValueError('DUPLICATE_PRISM_VERTEX')
    for p in poly:
        for x in p:
            if Fraction.from_float(float(x)) != x:
                raise ValueError('PRISM_COORDINATE_NOT_EXACT_BINARY64')
    for z in (zlo,zhi):
        if Fraction.from_float(float(z)) != z:
            raise ValueError('PRISM_HEIGHT_NOT_EXACT_BINARY64')
    n = len(poly)
    for i in range(n):
        a,b = poly[i],poly[(i+1)%n]
        for j,p in enumerate(poly):
            cross=(b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])
            if j not in (i,(i+1)%n) and cross<=0:
                raise ValueError('PRISM_POLYGON_NOT_STRICTLY_CONVEX_CCW')
    cx,cy = (sum(p[d] for p in poly)/n for d in (0,1))
    if any(Fraction.from_float(float(v))!=v for v in (cx,cy)):
        raise ValueError('PRISM_CAP_CENTER_NOT_DYADIC')
    vertices = [(x,y,z) for z in (zlo,zhi) for x,y in poly]
    vertices += [(cx,cy,zlo),(cx,cy,zhi)]
    faces=[]
    for i in range(n):
        j=(i+1)%n
        faces += [(i,j,n+j),(i,n+j,n+i),(2*n,j,i),(2*n+1,n+i,n+j)]
    with Path(path).open('x',encoding='ascii',newline='\n') as stream:
        stream.write('# P19 REGISTERED DYADIC GUARD; EXPLORATORY NOT PHYSICAL APPROVAL\n')
        for p in vertices:
            stream.write('v '+' '.join(format(float(x),'.17g') for x in p)+'\n')
        for face in faces:
            stream.write('f '+' '.join(str(i+1) for i in face)+'\n')
    mesh=read_binary64_obj(path)
    if exact_signed_volume(mesh)<=0:
        raise ValueError('PRISM_NOT_POSITIVELY_ORIENTED')
    return {'sha256':digest(path),'vertices':len(vertices),'faces':len(faces),
            'exact_volume':str(exact_signed_volume(mesh))}


def prepare(packet, output):
    packet,output=Path(packet).resolve(),Path(output).resolve()
    if digest(packet/'manifest.json')!=SOURCE_MANIFEST_SHA:
        raise ValueError('P19_REQUIRES_FROZEN_P17_MANIFEST')
    for name,(rel,sha) in SOURCES.items():
        if digest(packet/rel)!=sha:
            raise ValueError('FROZEN_P19_SOURCE_SHA_MISMATCH_'+name)
    output.mkdir(parents=True,exist_ok=False)
    plan=registered_plan()
    write_new_json(output/'registered-plan.json',plan)
    guards={}
    op=plan['outer_collars']
    for name,(lo,hi) in zip(('lower_collar','upper_collar'),op['z_intervals']):
        path=output/(name+'.obj')
        guards[name]=write_dyadic_prism(path,op['polygon_ccw'],lo,hi)
    ip=plan['inner_guard']
    guards['inner_guard']=write_dyadic_prism(output/'inner_guard.obj',ip['polygon_ccw'],*ip['z_interval'])
    write_new_json(output/'guard-identities.json',guards)
    return output


def native_call(binary, operation, operands, output, *, timeout=120):
    binary,output=Path(binary).resolve(),Path(output).resolve()
    operands=[Path(p).resolve() for p in operands]
    if (operation not in ('union','subtraction') or type(timeout) is not int or
            not 0<timeout<=120 or len(operands)<2 or
            (operation=='subtraction' and len(operands)!=2)):
        raise ValueError('UNREGISTERED_NATIVE_OPERATION_OR_TIMEOUT')
    if output.exists() or Path(str(output)+'.native.json').exists():
        raise ValueError('REFUSE_TO_OVERWRITE_NATIVE_EVIDENCE')
    source_sha=[digest(p) for p in operands]
    command=[str(binary),operation,*map(str,operands),str(output)]
    start=time.perf_counter()
    record={'operation':operation,'input_sha256':source_sha,
            'binary_sha256':digest(binary),'timeout_seconds':timeout,
            'new_native_process_launched':True,'output_file':output.name}
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=timeout,
            check=False,env={**os.environ,'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1'})
        record.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
    except subprocess.TimeoutExpired as exc:
        record.update(returncode=None,status='NATIVE_TIMEOUT',
            stdout=str(exc.stdout or ''),stderr=str(exc.stderr or ''))
    record['wall_seconds']=time.perf_counter()-start
    record['output_exists']=output.is_file()
    record['inputs_unchanged']=source_sha==[digest(p) for p in operands]
    record['binary_unchanged']=record['binary_sha256']==digest(binary)
    if output.is_file():record['output_sha256']=digest(output)
    write_new_json(str(output)+'.native.json',record)
    if not record['inputs_unchanged'] or not record['binary_unchanged']:
        raise ValueError('NATIVE_CALL_MUTATED_PINNED_INPUT_OR_BINARY')
    return record


def run(packet,binary,upstream_checkout,output):
    from p7_cherchi_native_union import native_identity
    packet,binary,upstream_checkout,output=map(lambda p:Path(p).resolve(),
                                               (packet,binary,upstream_checkout,output))
    identity=native_identity(binary,upstream_checkout)
    status=subprocess.run(['git','-C',str(upstream_checkout),'status','--porcelain','--untracked-files=no'],
        capture_output=True,text=True,check=True).stdout
    if status.strip():raise ValueError('CHERCHI_TRACKED_SOURCE_TREE_DIRTY')
    identity['operation']='REGISTERED_UNION_AND_SUBTRACTION'
    identity['tracked_source_tree_clean']=True
    prepare(packet,output)
    plan=json.loads((output/'registered-plan.json').read_text())
    from p17_material_candidate import typed_exact_equal
    if not typed_exact_equal(plan,registered_plan()):
        raise ValueError('EXECUTION_PLAN_DIFFERS_FROM_REGISTERED_PARAMETERS')
    guard_identities=json.loads((output/'guard-identities.json').read_text())
    record={'schema':SCHEMA,'status':'NATIVE_CONSTRUCTION_RUNNING',
        'registered_plan_sha256':digest(output/'registered-plan.json'),
        'native':identity,'operations':[], 'saved_surface_audits':{},
        'automatic_postprocess_executed':False,'geometry_accepted':False,
        'optimization_admitted':False,'training_admitted':False}
    def checkpoint():
        # The single active journal is mutable; all operation/mesh evidence is new-only.
        (output/'construction-journal.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n')
    checkpoint()
    inputs={name:packet/rel for name,(rel,_) in SOURCES.items()}
    inputs.update({name:output/(name+'.obj') for name in ('lower_collar','upper_collar','inner_guard')})
    expected={inputs[name]:sha for name,(_,sha) in SOURCES.items()}
    expected.update({inputs[name]:guard_identities[name]['sha256']
                     for name in ('lower_collar','upper_collar','inner_guard')})
    expected.update({binary:identity['binary_sha256'],
        output/'registered-plan.json':record['registered_plan_sha256'],
        output/'guard-identities.json':digest(output/'guard-identities.json')})
    def require_frozen_bytes():
        for path,sha in expected.items():
            if not path.is_file() or digest(path)!=sha:
                record.update(status='REJECTED_CHANGED_FROZEN_MATERIAL_OR_BINARY',
                    changed_file=path.name,native_outputs_modified_after_call=None)
                checkpoint()
                raise ValueError('P19_FROZEN_MATERIAL_OR_BINARY_CHANGED_'+path.name)
    require_frozen_bytes()
    passed={}
    for spec in plan['native_operations']:
        require_frozen_bytes()
        label=Path(spec['output']).stem
        if label=='F' and not all(passed.get(k) for k in ('M','D')):
            record['F_native_not_launched_reason']='M_OR_D_SAVED_SURFACE_NOT_CERTIFIED'
            break
        operands=[output/name if name.endswith('.obj') else inputs[name] for name in spec['inputs']]
        dest=output/spec['output']
        call=native_call(binary,spec['op'],operands,dest)
        record['operations'].append(call)
        if call.get('output_exists'):
            expected[dest]=call['output_sha256']
        checkpoint()
        require_frozen_bytes()
        if call.get('returncode')==0 and call.get('output_exists'):
            try:
                surface=audit_exact_surface(dest,call['output_sha256'])
                record['saved_surface_audits'][label]=surface
                passed[label]=(surface['exact_embedded_closed_oriented_2manifold'] is True)
                write_new_json(output/(label+'-surface-audit.json'),surface)
            except Exception as exc:
                passed[label]=False
                record['saved_surface_audits'][label]={'error':f'{type(exc).__name__}: {exc}'}
        else:
            passed[label]=False
        require_frozen_bytes()
        checkpoint()
    record['status']=('NATIVE_SAVED_SURFACES_PASS_FULL_MATERIAL_PROOF_PENDING'
        if all(passed.get(k) for k in ('M','D','F')) else 'NATIVE_SAVED_SURFACE_REJECTED')
    record['new_Teapot_native_calls']=len(record['operations'])
    require_frozen_bytes()
    record['native_outputs_modified_after_call']=False
    checkpoint()
    return record


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--packet',type=Path,required=True)
    ap.add_argument('--native-bin',type=Path,required=True)
    ap.add_argument('--upstream-checkout',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    r=run(args.packet,args.native_bin,args.upstream_checkout,args.out)
    print(json.dumps({k:r[k] for k in ('status','new_Teapot_native_calls','optimization_admitted')},indent=2))
    if r['status']=='NATIVE_SAVED_SURFACE_REJECTED':raise SystemExit(2)


if __name__=='__main__':main()

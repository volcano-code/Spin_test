"""W2 M16: real single-call Cherchi admission harness, no synthetic native truth.

Prepare frozen, byte-matched Heart input from authentic H8f artifact, then gate
one actual native call on three externally pinned compiled extensions and a
complete, clean W2 checkout. The native result is always excluded from training.
A 4-GiB sandbox reports a preflight failure; it NEVER simulates Cherchi.

The original H8f workflow failed its strict branch-neighborhood gate; that
failure remains immutable here, even if a new individual Cherchi call succeeds.
"""
from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time
from zipfile import ZipFile

import numpy as np

SOURCE_SHA = '0bcc187b3005478baa586a6d6f450e73811ca342'
HEART_ARTIFACT_SHA = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
REQUEST_SHA = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
HEART_SOURCE_SHA = {
 'initial_top.obj':'fbada64691e30b458bc5b5375f8d4ad351cb0b383d800512bb659077b29532f6',
 'fixed_shell.obj':'45c83ffd19c94b6c75ea63e7e7261fda645cd00ec0920c1a6ecc68e703c3a5b0',
 'design_domain.obj':'391fbeb80b8e7e4e2f12217880f4642c5fccd30ae5bb9ba2b5703d0dbd05b092',
}
MODULES = ('make_it_stand._make_it_stand','_cherchi_core_boolean','_cherchi_rational_moments')
# These shared source blobs were actually read from the frozen W2 tree, not inferred.
PINNED_CODE = {
 'python/make_it_stand/spin.py':'1adaacbb89e45bf9a546594cfa684da7ae0f1cf2',
 'python/make_it_stand/verification/cherchi_inprocess.py':'f9fa539f699df8baf8b8d30729048269a26ecb3c',
 'python/make_it_stand/verification/faster_material.py':'a3c56a395e98e5c19d5924d1568b4e800e94b4d9',
 'research/NeuralMoments/teacher/native_cherchi_teacher.py':'d19ef43d3591ff5f8f69886512781d3d19f470d5',
 'research/NeuralMoments/teacher/run_native_smoke.py':'4aa9bb6e3cd22aadcc372785eb0e6d6ca42d6bdf',
}
NATIVE_CAP_BYTES = 24 * 1024**3
RUN_DEADLINE_SECONDS = 3590
FROZEN_INPUT_BUDGET = 1e-9  # only outer = fixed + design, NOT a Boolean teacher budget
MOMENT_PAIRS = ((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))


def require(ok, code):
    if not ok: raise ValueError(code)


def h256(data): return hashlib.sha256(data).hexdigest()

def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''): h.update(chunk)
    return h.hexdigest()

def blob_hash(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False)

def strict_json(raw):
    def unique(pairs):
        out={}
        for k,v in pairs:
            require(k not in out, 'JSON_DUPLICATE_KEY')
            out[k]=v
        return out
    def reject(x):raise ValueError('NONFINITE_JSON:'+x)
    return json.loads(raw,object_pairs_hook=unique,parse_constant=reject)

def strict_mesh(obj):
    vertices=[];faces=[]
    for number,raw in enumerate(obj.decode('utf-8-sig').splitlines(),1):
        line=raw.partition('#')[0].strip()
        if not line: continue
        words=line.split()
        if words[0]=='v':
            require(len(words)==4,'OBJ_NON_XYZ_VERTEX:'+str(number))
            v=tuple(float(x) for x in words[1:]);require(all(math.isfinite(x) for x in v),'OBJ_NONFINITE_VERTEX')
            vertices.append(v)
        elif words[0]=='f':
            require(len(words)==4 and all(v.isdigit() and int(v)>0 for v in words[1:]),'OBJ_UNTRIANGULATED_OR_RELATIVE_FACE')
            f=tuple(int(i)-1 for i in words[1:]);require(len(set(f))==3 and max(f)<len(vertices),'OBJ_INVALID_FACE')
            faces.append(f)
        else: require(words[0] in ('g','o','vn','vt','s','usemtl','mtllib'),'OBJ_UNKNOWN_GEOMETRY_RECORD')
    require(len(vertices)>=4 and len(faces)>=4, 'EMPTY_MESH')
    return np.asarray(vertices,dtype='<f8'),np.asarray(faces,dtype='<i4')

def signed_ten(v,f):
    """Independent signed-tetra raw ten moments for frozen physical input."""
    t=v[f];a,b,c=t[:,0],t[:,1],t[:,2]
    wedges=np.einsum('ij,ij->i',a,np.cross(b,c))/6.
    sums=np.sum(t,axis=1);ret=np.empty(10)
    ret[0]=math.fsum(wedges.tolist())
    for i in range(3):ret[1+i]=math.fsum((wedges*sums[:,i]/4.).tolist())
    for k,(i,j) in enumerate(MOMENT_PAIRS):
        terms=wedges*(sums[:,i]*sums[:,j]+np.sum(t[:,:,i]*t[:,:,j],axis=1))/20
        ret[k+4]=math.fsum(terms.tolist())
    require(np.isfinite(ret).all(),'RAW_TEN_NOT_FINITE')
    return ret

def oriented_edges(faces):
    edges=Counter()
    for a,b,c in faces:
        for x,y in ((a,b),(b,c),(c,a)):edges[x,y]+=1
    require(all(n==1 and edges.get((b,a))==1 for (a,b),n in edges.items()),
            'NOT_CLOSED_ORIENTED_TRIANGLE_SURFACE')
    return len(edges)//2

def _member(archive,name):
    z=archive.getinfo(name)
    require(z.file_size<=8_000_000,'UNSAFE_ARCHIVE_MEMBER_SIZE')
    return archive.read(z)

def prepare_frozen_heart(zip_path,dir_path):
    """Open exactly one original H8f ZIP and rebuild input-normalized OBJ."""
    require(file_hash(zip_path)==HEART_ARTIFACT_SHA,'NOT_H8F_ARCHIVE')
    out=Path(dir_path)
    require(not out.exists(),'REFUSE_EXISTING_OUTPUT_DIRECTORY')
    out.mkdir(parents=True)
    with ZipFile(zip_path) as z:
        raw=_member(z,'artifacts/h8-request/prepared-request.json')
        require(h256(raw)==REQUEST_SHA,'FROZEN_REQUEST_CHANGED')
        saved=strict_json(raw);req=saved['request'];e=saved['evidence']
        require(saved['schema']=='spin-heart-h8-faster-preparation-v1'
                and e['original_author_cad'] is False and e['scope']=='H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED',
                'NOT_FROZEN_RECONSTRUCTED_H8_CASE')
        require(req['original_units_per_normalized_unit']==0.025 and e['normalized_scale_mm_per_unit']==25.,'METER_MM_SCALE_MISMATCH')
        meshes={};bound={};sha_rows={}
        for name in HEART_SOURCE_SHA:
            b=_member(z,'artifacts/h8-input/'+name)
            require(h256(b)==HEART_SOURCE_SHA[name] and e['source_sha256'][name]==HEART_SOURCE_SHA[name],
                    'CHANGED_OR_UNBOUND_SOURCE_OBJ:'+name)
            v,f=strict_mesh(b)
            bound[name]=(v,f)
            edges=oriented_edges(f)
            meshes[name]={'source_sha256':h256(b),'vertices':len(v),'faces':len(f),'paired_edges':edges}
            sha_rows[name]=h256(b)
        for name,prefix in [('initial_top.obj','outer'),('design_domain.obj','design')]:
            v,f=bound[name]
            refv=np.asarray(req[prefix+'_vertices'],dtype='<f8')
            reff=np.asarray(req[prefix+'_faces'],dtype='<i4')
            require(v.shape==refv.shape and f.shape==reff.shape,'NATIVE_REQUEST_SHAPE_MISMATCH:'+name)
            require((v/25.).tobytes()==refv.tobytes() and f.tobytes()==reff.tobytes(),
                    'NATIVE_REQUEST_VERTEX_OR_FACE_BYTES_CHANGED:'+name)
        values={name:signed_ten(v/25.,f) for name,(v,f) in bound.items()}
        rf=np.asarray(req['fixed_shell_moments'],dtype=np.float64)
        err_fixed=float(np.max(np.abs(values['fixed_shell.obj']-rf)))
        err_split=float(np.max(np.abs(values['initial_top.obj']-values['fixed_shell.obj']-values['design_domain.obj'])))
        require(err_fixed<=FROZEN_INPUT_BUDGET and err_split<=FROZEN_INPUT_BUDGET,'FROZEN_INPUT_F_D_SPLIT_ERROR')
        first=strict_json(_member(z,'artifacts/h8f-all81-points/point-000.json'))
        c=first['coefficients']
        require(type(c) is list and len(c)==10 and all(type(x) in (int,float) and math.isfinite(x) for x in c),'BAD_H8F_C10')
        view=out/'frozen_normalized_outer.obj'
        with view.open('x',encoding='utf-8') as f:
            f.write('# W2 M16 exact binary64 normalized H8f outer VIEW; not source CAD\n')
            for v in req['outer_vertices']:
                f.write('v '+ ' '.join(repr(float(t)) for t in v)+'\n')
            for a,b,c0 in req['outer_faces']:
                f.write(f'f {a+1} {b+1} {c0+1}\n')
        wv,wf=strict_mesh(view.read_bytes())
        require(wv.tobytes()==np.asarray(req['outer_vertices'],dtype='<f8').tobytes() and
                wf.tobytes()==np.asarray(req['outer_faces'],dtype='<i4').tobytes(),
                'NORMALIZED_VIEW_ROUNDTRIP_MISMATCH')
        frozen={
          'schema':'w2-m16-heart-immutable-preparation-v1',
          'source_sha':SOURCE_SHA,'original_workflow_conclusion':'failure',
          'historical_run_id':39123384402,'artifact_id':12135528290,
          'archive_sha256':HEART_ARTIFACT_SHA,'request_sha256':REQUEST_SHA,
          'native_model_path':str(view.resolve()),'native_model_sha256':file_hash(view),
          'model_is_original_CAD':False,'source_meshes':meshes,
          'native_c':first['coefficients'],
          'native_c_sha256':h256(canonical([float(x) for x in first['coefficients']]).encode()),
          'fixed_r_source_error_max_abs':err_fixed,
          'outer_F_D_error_max_abs':err_split,
          'input_partition_error_budget':FROZEN_INPUT_BUDGET,
          'input_budget_does_not_validate_Cherchi_boolean':True,
          'derivative_training_admitted':False,'new_native_calls':0,
          'frozen_request':req,'frozen_evaluator_settings':saved['evaluator_settings'],
        }
    with (out/'frozen_heart_preparation.json').open('x',encoding='utf-8') as f: json.dump(frozen,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    return frozen

def _meminfo(key):
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith(key+':'):
            return int(line.split()[1])*1024
    return 0

def runtime_limits():
    cgroup=Path('/sys/fs/cgroup/memory.max')
    raw=cgroup.read_text().strip() if cgroup.is_file() else None
    limit=int(raw) if raw and raw!='max' else None
    available=_meminfo('MemAvailable')
    total=_meminfo('MemTotal')
    used_path=Path('/sys/fs/cgroup/memory.current')
    try: used=int(used_path.read_text()) if used_path.is_file() and limit is not None else 0
    except (OSError, ValueError): used=0
    effective=min((max(0,limit-used) if limit is not None else total),available)
    swap=_meminfo('SwapTotal')
    cgroup_swap=Path('/sys/fs/cgroup/memory.swap.max')
    swap_raw=cgroup_swap.read_text().strip() if cgroup_swap.is_file() else '0'
    allowed=effective>=NATIVE_CAP_BYTES and swap==0 and swap_raw in ('0','max')
    return {'cgroup_memory_limit_bytes':limit,'cgroup_current_bytes':used,'host_available_bytes':available,
            'effective_available_bytes':effective,'host_swap_bytes':swap,
            'cgroup_swap_limit':swap_raw,'required_bytes':NATIVE_CAP_BYTES,
            'qualified_for_native_24gib_job':allowed}

def verify_source_checkout(root):
    path=Path(root)
    require(path.is_dir() and (path/'.git').exists(),'COMPLETE_GIT_W2_CHECKOUT_REQUIRED')
    branch=subprocess.run(['git','-C',str(path),'symbolic-ref','--short','HEAD'],capture_output=True,text=True,check=False)
    require(branch.returncode==0 and branch.stdout.strip()=='research/neuralmoments-w2-teacher-20261019',
            'NOT_W2_EXCLUSIVE_BRANCH')
    dirty=subprocess.run(['git','-C',str(path),'status','--porcelain','--untracked-files=no',
                          '--','python','src','bindings','research/NeuralMoments/teacher/run_native_smoke.py',
                          'research/NeuralMoments/teacher/native_cherchi_teacher.py'],
                         capture_output=True,text=True,check=False)
    require(dirty.returncode==0 and not dirty.stdout.strip(),'SHARED_SOURCE_OR_TEACHER_DIRTY')
    seen={}
    for name,want in PINNED_CODE.items():
        b=(path/name).read_bytes()
        actual=blob_hash(b)
        require(actual==want,'FROZEN_CORE_OR_TEACHER_SOURCE_DRIFT:'+name)
        seen[name]=actual
    return seen

def validate_module_manifest(path):
    """Independent build/operator-provided hashes; never inferred from a file alone."""
    row=strict_json(Path(path).read_bytes())
    require(type(row) is dict and row.get('schema')=='w2-m16-externally-frozen-ELF-extensions-v1',
            'NATIVE_MODULE_MANIFEST_REQUIRED')
    entries=row.get('extensions')
    require(type(entries) is dict and set(entries)==set(MODULES),'THREE_NATIVE_MODULES_REQUIRED')
    seen={}
    for name in MODULES:
        meta=entries[name]
        require(type(meta) is dict and set(meta)=={'path','sha256'},'NATIVE_ENTRY_FIELDS_REQUIRED')
        actual_path=Path(meta['path'])
        require(actual_path.is_file() and not actual_path.is_symlink(),'MISSING_NATIVE_BINARY:'+name)
        value=meta['sha256']
        require(type(value) is str and len(value)==64 and all(k in '0123456789abcdef' for k in value),
                'INVALID_EXTERNAL_SHA:'+name)
        with actual_path.open('rb') as stream:
            require(stream.read(4)==b'\x7fELF','NOT_A_NATIVE_ELF_BINARY:'+name)
        require(file_hash(actual_path)==value,'NATIVE_BINARY_SHA_MISMATCH:'+name)
        seen[name]={'path':str(actual_path.resolve()),'sha256':value}
    return seen

IMPORT_PROBE='''\
import json,hashlib
from pathlib import Path
import make_it_stand.spin as spin
import _cherchi_core_boolean as cherchi
import _cherchi_rational_moments as gmp
m={'make_it_stand._make_it_stand':spin._native_module(),'_cherchi_core_boolean':cherchi,'_cherchi_rational_moments':gmp}
print(json.dumps({n:hashlib.sha256(Path(x.__file__).read_bytes()).hexdigest() for n,x in m.items()},sort_keys=True))
'''

def audit_imports(checkout,modules):
    env=dict(os.environ)
    paths=[str(Path(checkout)/'python')]+sorted({str(Path(x['path']).parent) for x in modules.values()})
    env['PYTHONPATH']=os.pathsep.join(paths+[env.get('PYTHONPATH','')])
    result=subprocess.run([sys.executable,'-c',IMPORT_PROBE],capture_output=True,text=True,
                          timeout=20,env=env,cwd=checkout,check=False)
    require(result.returncode==0,'FAILED_PINNED_NATIVE_IMPORT:'+result.stderr[-250:])
    observed=strict_json(result.stdout.strip())
    require(observed=={k:v['sha256'] for k,v in modules.items()},'IMPORTED_NATIVE_MODULE_IDENTITY_MISMATCH')
    return env

def _wait_one(cmd,env,checkout,output):
    def limit():resource.setrlimit(resource.RLIMIT_AS,(NATIVE_CAP_BYTES,NATIVE_CAP_BYTES))
    start=time.monotonic()
    p=subprocess.Popen(cmd,cwd=checkout,env=env,start_new_session=True,
                       preexec_fn=limit,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    timed_out=False
    try:stdout,stderr=p.communicate(timeout=RUN_DEADLINE_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out=True
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        stdout,stderr=p.communicate()
    finally:
        try:os.killpg(p.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    return {'exit_code':p.returncode,'timed_out':timed_out,
            'wall_seconds':time.monotonic()-start,'stdout_tail':stdout[-2500:],'stderr_tail':stderr[-2500:]}

def run(archive,output,*,checkout=None,manifest=None,execute=False,reference_budgets=None):
    """Always prepare actual frozen Heart; refuse native without external proof."""
    dest=Path(output)
    frozen=prepare_frozen_heart(archive,dest)
    reasons=[];native_record=None;native_launch=None;limits=runtime_limits()
    if not limits['qualified_for_native_24gib_job']:
        reasons.append('EFFECTIVE_MEMORY_OR_SWAP_NOT_QUALIFIED')
    if checkout is None:
        reasons.append('COMPLETE_W2_CHECKOUT_NOT_SUPPLIED')
    else:
        try:verify_source_checkout(checkout)
        except (ValueError,OSError) as e:reasons.append(str(e))
    modules=None
    if manifest is None:reasons.append('THREE_COMPILED_NATIVE_BINARIES_NOT_PINNED')
    else:
        try:modules=validate_module_manifest(manifest)
        except (ValueError,OSError) as e:reasons.append(str(e))
    if reference_budgets is None:
        reasons.append('SEPARATE_PREDECLARED_CHERCHI_TEN_MOMENT_BUDGET_REQUIRED')
    else:
        require(type(reference_budgets) is list and len(reference_budgets)==10 and
                all(type(x) in (int,float) and math.isfinite(x) and x>0 for x in reference_budgets),
                'INVALID_CHERCHI_TEN_MOMENT_BUDGET')
    env=None
    if execute and not reasons:
        # Three native modules were externally SHA-pinned before we import them.
        try: env=audit_imports(checkout,modules)
        except (OSError,ValueError,subprocess.SubprocessError) as exc:
            reasons.append('COMPILED_NATIVE_IMPORT_NOT_VERIFIED:'+str(exc))
    if execute and not reasons:
        req=frozen['frozen_request']
        settings=frozen['frozen_evaluator_settings']
        spec={'schema':'w2-one-cherchi-request-v3','source_sha':SOURCE_SHA,
              'model_path':frozen['native_model_path'],
              'expected_model_sha256':frozen['native_model_sha256'],
              'expected_native_module_sha256':modules['make_it_stand._make_it_stand']['sha256'],
              'request':req,'evaluator_settings':settings,
              'native_c':frozen['native_c'],
              'expected_native_c_sha256':frozen['native_c_sha256'],
              'model_geometry_binding':{'mode':'OBJ_IS_INPUT_NORMALIZED_OUTER_V1'},
              'reference_absolute_tolerances':reference_budgets,
              'geometry':{'historical_model_source_sha256':HEART_SOURCE_SHA['initial_top.obj'],
                          'historical_design_sha256':HEART_SOURCE_SHA['design_domain.obj'],
                          'historical_fixed_sha256':HEART_SOURCE_SHA['fixed_shell.obj'],
                          'historical_run_id':39123384402,'historical_conclusion':'failure',
                          'new_view_sha256':frozen['native_model_sha256'],
                          'cherchi_bridge_sha256':modules['_cherchi_core_boolean']['sha256'],
                          'gmp_backend_sha256':modules['_cherchi_rational_moments']['sha256']},
              'frame':{'kind':'INPUT_NORMALIZED_TARGET_V1','native_target_origin':req['target_origin'],
                       'native_target_axes':req['target_axes']},
              'rational_arithmetic_backend':'NATIVE_GMP_SURFACE_V1',
              'derivative_contract':None}
        spec_path=dest/'M16_REAL_NATIVE_SPEC.json'
        with spec_path.open('x',encoding='utf-8') as f:
            json.dump(spec,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')
        label_path=dest/'M16_NEW_CHERCHI_TEACHER.json'
        native_launch=_wait_one([sys.executable,str(Path(checkout)/'research/NeuralMoments/teacher/run_native_smoke.py'),
                    '--spec',str(spec_path),'--output',str(label_path)],env,checkout,label_path)
        if native_launch['exit_code']==0 and label_path.is_file():
            label=strict_json(label_path.read_bytes())
            p=label.get('payload',{})
            proof=p.get('exact_proof',{})
            require(proof.get('native_cherchi') is True and
                proof.get('independent_ten_moment_audit',{}).get('comparison',{}).get('within_tolerance') is True
                and proof.get('same_call_attachment') is not None and
                p.get('J_D') is None and p.get('split')=='excluded',
                'UNVERIFIED_NATIVE_LABEL_REJECTED')
            # Re-read frozen code/binaries and source archive after the call.
            verify_source_checkout(checkout)
            validate_module_manifest(manifest)
            require(file_hash(archive)==HEART_ARTIFACT_SHA,'HISTORICAL_ARCHIVE_CHANGED_DURING_NATIVE_CALL')
            native_record={'path':str(label_path),'sha256':file_hash(label_path),
                           'real_native_call_verified':True,'training_admitted':False}
        else:
            reasons.append('NEW_NATIVE_TEACHER_NOT_COMPLETED')
    elif execute:
        reasons.append('NO_NATIVE_EXECUTION_DUE_TO_PREFLIGHT_BLOCK')
    result={'schema':'w2-m16-real-native-one-call-acceptance-v1',
       'status':'ONE_REAL_HEART_TEACHER_LABEL_VERIFIED_DERIVATIVE_EXCLUDED' if native_record else
                'BLOCKED_BEFORE_NATIVE_CALL' if reasons else 'FROZEN_INPUT_READY_NO_NATIVE_EXECUTION_REQUESTED',
       'input':{'archive_sha256':HEART_ARTIFACT_SHA,'frozen_request_sha256':REQUEST_SHA,
                'native_c_sha256':frozen['native_c_sha256'],
                'source_mesh_hashes':HEART_SOURCE_SHA,
                'source_partition_max_abs_error':frozen['outer_F_D_error_max_abs']},
       'preflight':{'qualified_resources':limits,'blockers':reasons,
                    'requested_native_execution':execute,'external_binary_manifest_verified':bool(modules)},
       'new_native_label':native_record,'new_native_launch':native_launch,
       'original_H8f_workflow_conclusion':'failure','new_native_teacher_verified':int(native_record is not None),
       'J_D_training_admitted':0,'training_admitted':False,
       'noodles_v7_status':'MISSING_SHA_AUTHENTICATED_OUTER_FIXED_DESIGN_NATIVE_INPUT',
       'noodles_optimized_output_not_a_teacher_input':True}
    report=dest/'M16_EXECUTION_RESULT.json'
    with report.open('x',encoding='utf-8') as f:
        json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
    return result

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--heart-archive',required=True)
    ap.add_argument('--output-dir',required=True)
    ap.add_argument('--checkout')
    ap.add_argument('--native-manifest')
    ap.add_argument('--execute-native',action='store_true')
    ap.add_argument('--reference-budgets-json',help='An external JSON list of ten predeclared absolute errors, NOT the F/D input budget')
    a=ap.parse_args(argv)
    budgets=strict_json(Path(a.reference_budgets_json).read_bytes()) if a.reference_budgets_json else None
    try:
        r=run(a.heart_archive,a.output_dir,checkout=a.checkout,manifest=a.native_manifest,
              execute=a.execute_native,reference_budgets=budgets)
        print(canonical({'status':r['status'],'blockers':r['preflight']['blockers'],
                         'new_native_teacher_verified':r['new_native_teacher_verified'],
                         'training_admitted':False}))
        return 0 if not a.execute_native or r['new_native_teacher_verified']==1 else 2
    except Exception as exc:
        print(canonical({'status':'FAILED_INPUT_PREPARATION_OR_IDENTITY',
                         'error':type(exc).__name__+': '+str(exc),
                         'training_admitted':False}),file=sys.stderr)
        return 2
if __name__=='__main__':sys.exit(main())

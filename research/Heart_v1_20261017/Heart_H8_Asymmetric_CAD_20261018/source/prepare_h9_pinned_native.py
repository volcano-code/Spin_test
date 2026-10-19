"""W3 H9 pinned native build and real side-probe handoff (no CI/workflow writes).

Phase plan is safe on a small offline machine. Phase build requires a complete
frozen W3 git checkout, >=24GiB effective memory and swap=0, and uses the
*source* pins/flags of historical H8f Actions run 39123384402. Phase run uses
the compiled binaries and the existing stage-5 60-minute guarded real runner.

The program neither manufactures historical data nor certifies Newton.
Build never uses sudo, moves system Boost archives, or writes a different git
branch; all output is local/untracked and no .github workflow is edited.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from run_h9_native_serial import (
    BRANCH, ANCESTOR, MAX_SECONDS, git_ref, preflight, read_machine_memory,
)

REPO_NAME = 'volcano-code/Spin_test'
CHERCHI_COMMIT = '7bd6c2697695f555f9a15d7e154e084d841316f0'
CGAL_COMMIT = 'f7c3c8212b56c0d6dae63787efc99093f4383415'
CHERCHI_URL = 'https://github.com/gcherchi/InteractiveAndRobustMeshBooleans.git'
CGAL_URL = 'https://github.com/CGAL/cgal.git'
HISTORICAL_ARTIFACT_SHA256 = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
H8F_WORKFLOW_BLOB_SHA = 'a6dda4d04998f1244ce0a7f80991d6198c037cdb'
MODULES = ('_make_it_stand', '_cherchi_core_boolean', '_cherchi_rational_moments')
BUILD_PARALLEL = 2
BUILD_SECONDS = 3500
MEMORY_FLOOR = 24*1024**3
PYTHON_MINOR = (3, 13)


class BuildBlocked(RuntimeError):
    pass


def die_unless(condition, reason):
    if not condition:
        raise BuildBlocked(reason)


def sha_file(path):
    digest=sha256()
    with Path(path).open('rb') as stream:
        for buf in iter(lambda: stream.read(1024*1024), b''):
            digest.update(buf)
    return digest.hexdigest()


def module_paths(repo: Path):
    return [repo/'python', repo/'build/h9-w3-core/python',
            repo/'build/h9-w3-cherchi/python']


def python_path_env(repo: Path, environ=None):
    env=dict(os.environ if environ is None else environ)
    paths=[str(p) for p in module_paths(repo)]
    if env.get('PYTHONPATH'):
        paths.append(env['PYTHONPATH'])
    env['PYTHONPATH']=os.pathsep.join(paths)
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               PYTHONUNBUFFERED='1')
    return env


def check_runtime(repo):
    """Fail before a compiler/network task if the W3 branch and resources are wrong."""
    reasons=[]
    mem=read_machine_memory()
    try:
        ref=git_ref(repo)
    except (OSError, subprocess.TimeoutExpired):
        ref={'branch':None,'head_sha':None,'frozen_ancestor_is_ancestor':False}
    if ref['branch']!=BRANCH or not ref['frozen_ancestor_is_ancestor']:
        reasons.append('NOT_FROZEN_W3_BRANCH_OR_ANCESTOR')
    if mem['effective_memory_bytes']<MEMORY_FLOOR:
        reasons.append('LESS_THAN_24GIB_EFFECTIVE_MEMORY')
    if mem['physical_swap_bytes']:
        reasons.append('SWAP_MUST_BE_ZERO')
    if sys.version_info[:2]!=PYTHON_MINOR:
        reasons.append('REQUIRES_PYTHON_3_13_PINNED_H8F')
    for executable in ('git','cmake','ninja','c++','pkg-config'):
        if shutil.which(executable) is None:
            reasons.append('MISSING_TOOL:'+executable)
    if not (repo/'.git').exists() or not (repo/'CMakeLists.txt').is_file():
        reasons.append('NOT_A_COMPLETE_SOURCE_CHECKOUT')
    return {'repo':str(repo.resolve()),'git_ref':ref,'machine_memory':mem,
            'python':sys.version.split()[0],'blocked_reasons':reasons,
            'ready':not reasons,'newton_admitted':False}


def build_plan(repo):
    """Structured, pinned command plan. No sudo, repo writes, or subprocess."""
    repo=Path(repo).resolve()
    cherchi=repo/'external/reference-sources-20260917/sources'/('InteractiveAndRobustMeshBooleans-'+CHERCHI_COMMIT)
    cgal=repo/'libigl/external/cgal'
    core=repo/'build/h9-w3-core'
    ext=repo/'build/h9-w3-cherchi'
    shared_base='/usr/lib/x86_64-linux-gnu'
    cmake_core=['cmake','-S',str(repo),'-B',str(core),'-G','Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        '-DMAKE_IT_STAND_BUILD_VIEWER=OFF',
        '-DMAKE_IT_STAND_BUILD_REACHABILITY=OFF',
        '-DMAKE_IT_STAND_BUILD_SPIN_IT_2014=OFF',
        '-DMAKE_IT_STAND_BUILD_SPIN_IT_FASTER=ON',
        '-DMAKE_IT_STAND_BUILD_EXACT_GEOMETRY_CHECKS=ON',
        '-DMAKE_IT_STAND_BUILD_PYTHON=ON',
        '-DMAKE_IT_STAND_FILTERED_BOUNDARY_KERNEL=ON',
        '-DBUILD_TESTING=OFF',
        '-DBoost_USE_STATIC_LIBS=OFF',
        '-DBoost_THREAD_LIBRARY_RELEASE='+shared_base+'/libboost_thread.so',
        '-DBoost_SYSTEM_LIBRARY_RELEASE='+shared_base+'/libboost_system.so',
        '-DPython_EXECUTABLE='+sys.executable,
        '-DPython3_EXECUTABLE='+sys.executable]
    return {'schema':'heart-h9-pinned-native-build-plan-v1',
        'historical_h8f_workflow_blob_sha':H8F_WORKFLOW_BLOB_SHA,
        'source_workflow_head':'0bcc187b3005478baa586a6d6f450e73811ca342',
        'source_references':{'cherchi':CHERCHI_COMMIT,'cgal':CGAL_COMMIT},
        'reference_urls':{'cherchi':CHERCHI_URL,'cgal':CGAL_URL},
        'branch':BRANCH,'frozen_ancestor':ANCESTOR,
        'require_mem_gib':24,'require_swap_bytes':0,
        'maximum_compiler_parallelism':BUILD_PARALLEL,
        'max_build_seconds':BUILD_SECONDS,'max_native_job_seconds':MAX_SECONDS,
        'python_minor':'3.13',
        'boost_abi_policy':'SHARED_LIB_ONLY_NO_SYSTEM_STATIC_ARCHIVE_MUTATION',
        'paths':{'cherchi':str(cherchi),'cgal':str(cgal),
                 'core':str(core),'cherchi_build':str(ext)},
        'steps':[
            {'name':'libigl_submodule','argv':['git','-C',str(repo),'submodule','update','--init','--recursive','--','libigl']},
            {'name':'core_configure','argv':cmake_core},
            {'name':'core_build','argv':['cmake','--build',str(core),'--target','_make_it_stand','--parallel',str(BUILD_PARALLEL)]},
            {'name':'cherchi_configure','argv':['cmake','-S',str(repo/'bindings/cherchi'),'-B',str(ext),'-G','Ninja','-DCMAKE_BUILD_TYPE=Release','-DPython_EXECUTABLE='+sys.executable,'-DMAKE_IT_STAND_CHERCHI_RATIONAL_ARITHMETIC=ON']},
            {'name':'cherchi_build','argv':['cmake','--build',str(ext),'--parallel',str(BUILD_PARALLEL)]},
        ],
        'operator_prerequisites':[
            'Ubuntu 24.04 isolated checkout with 24GiB effective RAM, zero swap, Git/CMake/Ninja/GCC/Python3.13.',
            'Preinstall libgmp-dev libmpfr-dev libboost-all-dev libtbb-dev libeigen3-dev and X11/OpenGL development dependencies.',
            'Install pybind11==3.0.1, numpy>=2,<3, pytest>=8,<10, scipy>=1.14,<2, trimesh>=4,<5.',
            'Allow access to pinned Cherchi and CGAL GitHub URLs. No sudo is invoked by this program.',
            'Do not run concurrent large native tasks; retain all test results and binary SHA256.',
        ],
        'no_newton_claim':True}


def run_command(argv, timeout_seconds, log_handle, *, cwd=None, env=None):
    """No shell expansion; enforce the same remaining deadline per step."""
    die_unless(timeout_seconds>0, 'BUILD_DEADLINE_EXHAUSTED')
    log_handle.write('EXEC '+json.dumps(argv,ensure_ascii=False)+'\n');log_handle.flush()
    result=subprocess.run(argv,cwd=cwd,env=env,stdout=log_handle,
                          stderr=subprocess.STDOUT,timeout=timeout_seconds,check=False)
    die_unless(result.returncode==0,'BUILD_SUBPROCESS_FAILED:'+str(result.returncode)+':'+argv[0])


def git_head(path):
    r=subprocess.run(['git','-C',str(path),'rev-parse','HEAD'],
                     capture_output=True,text=True,timeout=15,check=True)
    return r.stdout.strip()


def pinned_sources(repo, plan, deadline, log):
    cherchi=Path(plan['paths']['cherchi'])
    cgal=Path(plan['paths']['cgal'])
    if cherchi.exists():
        die_unless((cherchi/'.git').exists() and git_head(cherchi)==CHERCHI_COMMIT,
                   'EXISTING_CHERCHI_DIRECTORY_WRONG_REVISION_NO_OVERWRITE')
    else:
        cherchi.parent.mkdir(parents=True,exist_ok=True)
        run_command(['git','clone','--filter=blob:none','--no-checkout',CHERCHI_URL,str(cherchi)],
                    int(deadline-time.monotonic()),log)
        run_command(['git','-C',str(cherchi),'checkout','--detach',CHERCHI_COMMIT],
                    int(deadline-time.monotonic()),log)
        die_unless(git_head(cherchi)==CHERCHI_COMMIT,'CHERCHI_REFERENCE_PIN_DRIFT')
    die_unless((repo/'libigl/.git').exists() or (repo/'libigl/.git').is_file(),
               'LIBIGL_SUBMODULE_NOT_INITIALIZED')
    if (cgal/'.git').exists() or (cgal/'.git').is_file():
        die_unless(git_head(cgal)==CGAL_COMMIT,'EXISTING_CGAL_CHECKOUT_WRONG_REVISION_NO_OVERWRITE')
    else:
        cgal.mkdir(parents=True,exist_ok=True)
        run_command(['git','-C',str(cgal),'init'],int(deadline-time.monotonic()),log)
        run_command(['git','-C',str(cgal),'fetch','--depth=1','--filter=blob:none',CGAL_URL,CGAL_COMMIT],
                    int(deadline-time.monotonic()),log)
        run_command(['git','-C',str(cgal),'checkout','--detach','FETCH_HEAD'],
                    int(deadline-time.monotonic()),log)
        die_unless(git_head(cgal)==CGAL_COMMIT,'CGAL_REFERENCE_PIN_DRIFT')
    die_unless((cgal/'Number_types/include/CGAL/Gmpq.h').is_file(),
               'PINNED_CGAL_HEADERS_MISSING')
    return {'cherchi':git_head(cherchi),'cgal':git_head(cgal)}


def boost_shared_rewrite(build_file):
    """Never remove or move host-system .a; modify only W3 build.ninja."""
    build_file=Path(build_file)
    text=build_file.read_text()
    count=0
    for kind in ('thread','system'):
        old='/usr/lib/x86_64-linux-gnu/libboost_'+kind+'.a'
        new='/usr/lib/x86_64-linux-gnu/libboost_'+kind+'.so'
        die_unless(Path(new).exists(),'SHARED_BOOST_LIBRARY_NOT_INSTALLED:'+kind)
        count+=text.count(old)
        text=text.replace(old,new)
    die_unless('libboost_thread.a' not in text and 'libboost_system.a' not in text,
               'STATIC_BOOST_REFERENCES_REMAIN')
    build_file.write_text(text)
    return count


def validate_module_locations(repo, info):
    """Do not accept globally installed/old binary modules under PYTHONPATH."""
    expected = {
        '_make_it_stand': Path(repo)/'build/h9-w3-core/python',
        '_cherchi_core_boolean': Path(repo)/'build/h9-w3-cherchi/python',
        '_cherchi_rational_moments': Path(repo)/'build/h9-w3-cherchi/python',
    }
    die_unless(set(info.get('paths',{}))==set(MODULES)
               and set(info.get('sha256',{}))==set(MODULES),
               'MISSING_PINNED_NATIVE_MODULE_EVIDENCE')
    for mod, root in expected.items():
        path=Path(info['paths'][mod]).resolve()
        die_unless(path.is_file() and path.suffix=='.so'
                   and path.is_relative_to(root.resolve()),
                   'NATIVE_EXTENSION_LOADED_OUTSIDE_FRESH_W3_BUILD:'+mod)
        die_unless(info['sha256'][mod]==sha_file(path),
                   'NATIVE_BINARY_HASH_NOT_REPRODUCIBLE:'+mod)
    return info['sha256']


def native_module_smoke(repo):
    env=python_path_env(repo)
    code=('import importlib,json,hashlib,pathlib; '
          'names=("_make_it_stand","_cherchi_core_boolean","_cherchi_rational_moments"); '
          'mods=[importlib.import_module(n) for n in names]; '
          'print(json.dumps({"paths":{n:str(pathlib.Path(m.__file__).resolve()) '
          'for n,m in zip(names,mods)},'
          '"sha256":{n:hashlib.sha256(pathlib.Path(m.__file__).read_bytes()).hexdigest() '
          'for n,m in zip(names,mods)}},sort_keys=True))')
    r=subprocess.run([sys.executable,'-c',code],env=env,stdout=subprocess.PIPE,
                     stderr=subprocess.PIPE,text=True,timeout=60)
    die_unless(r.returncode==0,'REAL_NATIVE_EXTENSION_IMPORT_FAILED:'+r.stderr[-2000:])
    return validate_module_locations(repo,json.loads(r.stdout.strip()))


def build(repo, output):
    repo=Path(repo).resolve();out=Path(output)
    out.mkdir(parents=True,exist_ok=False)
    state=check_runtime(repo)
    state['plan']=build_plan(repo)
    (out/'preflight.json').write_text(json.dumps(state,indent=2,sort_keys=True)+'\n')
    if not state['ready']:
        print('H9_STAGE7_BUILD_BLOCKED_NO_NATIVE_CALLS',state['blocked_reasons'])
        return 2
    plan=state['plan'];deadline=time.monotonic()+BUILD_SECONDS
    evidence={'schema':'heart-h9-native-build-evidence-v1','status':'FAILED_OR_INCOMPLETE',
              'branch_head_before_build':state['git_ref']['head_sha'],
              'source_revisions':{},'pinned_H8f_workflow_blob_sha256':H8F_WORKFLOW_BLOB_SHA,
              'new_real_native_calls':0,'newton_admitted':False}
    try:
        with (out/'build.log').open('x') as log:
            run_command(plan['steps'][0]['argv'],int(deadline-time.monotonic()),log)
            evidence['source_revisions']=pinned_sources(repo,plan,deadline,log)
            for package in ('gmp','mpfr'):
                run_command(['pkg-config','--modversion',package],int(deadline-time.monotonic()),log)
            for lib in ('thread','system'):
                die_unless(Path('/usr/lib/x86_64-linux-gnu/libboost_'+lib+'.so').exists(),
                           'SHARED_BOOST_LIBRARY_MISSING:'+lib)
            run_command(plan['steps'][1]['argv'],int(deadline-time.monotonic()),log)
            evidence['boost_rewrites']=boost_shared_rewrite(Path(plan['paths']['core'])/'build.ninja')
            run_command(plan['steps'][2]['argv'],int(deadline-time.monotonic()),log)
            run_command(plan['steps'][3]['argv'],int(deadline-time.monotonic()),log)
            run_command(plan['steps'][4]['argv'],int(deadline-time.monotonic()),log)
            log.write('COMPILED_ALL_REQUESTED_PINNED_TARGETS\n')
        evidence['module_sha256']=native_module_smoke(repo)
        evidence['head_after_build']=git_ref(repo)['head_sha']
        die_unless(evidence['head_after_build']==evidence['branch_head_before_build'],
                   'W3_BRANCH_CHANGED_DURING_BUILD')
        evidence['status']='NATIVE_BINARIES_BUILT_AND_IMPORTABLE_NOT_YET_EVALUATED'
        (out/'build_evidence.json').write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
        print('H9_STAGE7_NATIVE_BUILD_IMPORTS_PASSED_NEEDS_REAL_SIDE_PROBE')
        return 0
    except (BuildBlocked,subprocess.CalledProcessError,subprocess.TimeoutExpired,OSError) as exc:
        evidence['failure']=f'{type(exc).__name__}: {exc}'
        (out/'build_evidence.json').write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
        print('H9_STAGE7_BUILD_FAILED_NO_REAL_SAMPLES',evidence['failure'])
        return 1


def verify_build_evidence(repo, evidence_file, module_hashes):
    """Require the pinned local successful build report, not a claimed CI run."""
    saved=json.loads(Path(evidence_file).read_text())
    die_unless(saved.get("schema")=="heart-h9-native-build-evidence-v1"
               and saved.get("status")=="NATIVE_BINARIES_BUILT_AND_IMPORTABLE_NOT_YET_EVALUATED"
               and saved.get("source_revisions")=={"cherchi":CHERCHI_COMMIT,"cgal":CGAL_COMMIT}
               and saved.get("pinned_H8f_workflow_blob_sha256")==H8F_WORKFLOW_BLOB_SHA
               and saved.get("head_after_build")==git_ref(repo)["head_sha"]
               and saved.get("module_sha256")==module_hashes,
               "LOCAL_NATIVE_BUILD_PROVENANCE_OR_BINARY_SHA_DRIFT")
    return sha_file(evidence_file)


def launch(repo,artifact,certificate,output,build_evidence):
    """Exact 60-minute W3 runner; distinct build and evaluation phases."""
    repo=Path(repo).resolve();out=Path(output)
    out.mkdir(parents=True,exist_ok=False)
    status=check_runtime(repo)
    status['artifact_sha256_expected']=HISTORICAL_ARTIFACT_SHA256
    status['newton_admitted']=False
    if not status['ready']:
        status['status']='BLOCKED_NO_NATIVE_EVALUATION'
        (out/'launch_preflight.json').write_text(json.dumps(status,indent=2,sort_keys=True)+'\n')
        return 2
    if sha_file(artifact)!=HISTORICAL_ARTIFACT_SHA256:
        status.update(status='FROZEN_H8F_ARTIFACT_SHA_DRIFT')
        (out/'launch_preflight.json').write_text(json.dumps(status,indent=2,sort_keys=True)+'\n')
        return 2
    try:
        status['module_sha256']=native_module_smoke(repo)
    except (BuildBlocked, subprocess.TimeoutExpired) as exc:
        status.update(status='NATIVE_BINARY_NOT_IMPORTABLE',failure=str(exc))
        (out/'launch_preflight.json').write_text(json.dumps(status,indent=2,sort_keys=True)+'\n')
        return 2
    try:
        status['verified_local_build_evidence_sha256']=verify_build_evidence(
            repo,build_evidence,status['module_sha256'])
    except (BuildBlocked,ValueError,KeyError,OSError) as exc:
        status.update(status='LOCAL_NATIVE_BUILD_EVIDENCE_REJECTED',failure=str(exc))
        (out/'launch_preflight.json').write_text(json.dumps(status,indent=2,sort_keys=True)+'\n')
        return 2
    status['status']='ELIGIBLE_TO_ATTEMPT_REAL_NATIVE_FOUR_POINT_JOB_NOT_NEWTON'
    (out/'launch_preflight.json').write_text(json.dumps(status,indent=2,sort_keys=True)+'\n')
    try:
        proc=subprocess.run([sys.executable,str(repo/'research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/run_h9_native_serial.py'),
                             '--artifact',str(artifact),'--certificate',str(certificate),
                             '--output',str(out/'serial-native')],
                            env=python_path_env(repo),check=False,timeout=MAX_SECONDS+30)
        exit_code=proc.returncode
    except subprocess.TimeoutExpired:
        exit_code=124
    audit_file=out/'serial-native/independent-audit.json'
    audit_complete=False
    if exit_code==0 and audit_file.exists():
        audit=json.loads(audit_file.read_text())
        audit_complete=(audit.get('schema')=='heart-h9-independent-new-side-material-audit-v1'
                        and audit.get('new_native_samples_reintegrated')==4
                        and audit.get('newton_admitted') is False
                        and audit.get('actual_newton_step_accepted') is False)
    if exit_code==0 and not audit_complete:
        exit_code=1
    result={'schema':'heart-h9-stage7-serial-native-handoff-v1',
            'status':'FOUR_NATIVE_SIDES_AND_INDEPENDENT_AUDIT_FINISHED_NOT_NEWTON'
                if exit_code==0 else 'FAILED_CLOSED',
            'exit_code':exit_code,'module_sha256':status['module_sha256'],
            'local_build_evidence_sha256':status['verified_local_build_evidence_sha256'],
            'actual_independent_audit_accepted':audit_complete,
            'independent_audit':str(audit_file),'newton_admitted':False}
    (out/'launch_result.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    return exit_code


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[4])
    parser.add_argument('--phase',required=True,choices=('plan','build','run'))
    parser.add_argument('--output',type=Path)
    parser.add_argument('--artifact',type=Path)
    parser.add_argument('--certificate',type=Path)
    parser.add_argument('--build-evidence',type=Path)
    a=parser.parse_args()
    if a.phase=='plan':
        print(json.dumps({'plan':build_plan(a.repo),'preflight':check_runtime(a.repo)},indent=2,sort_keys=True))
        return 0
    if a.output is None:parser.error('--output required for build/run phases')
    if a.phase=='build':return build(a.repo,a.output)
    if a.artifact is None or a.certificate is None or a.build_evidence is None:
        parser.error('--artifact, --certificate and --build-evidence required for run phase')
    return launch(a.repo,a.artifact,a.certificate,a.output,a.build_evidence)


if __name__=='__main__':raise SystemExit(main())

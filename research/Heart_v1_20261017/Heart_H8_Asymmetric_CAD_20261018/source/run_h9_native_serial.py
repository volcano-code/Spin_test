"""W3 H9: guarded one-shot native runner, ≤60min and 24GiB virtual memory.

On a correctly provisioned checkout, executes the REAL four-point
Cherchi side probe and subsequently the independent rational packet verifier.
Never runs Newton or creates any optimizer terminal-OBJ claim.

This container lacks the compiled native modules and is resource-constrained,
so the preflight must refuse safely rather than attempt fake work.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

BRANCH='research/neuralmoments-w3-heart-h9-20261019'
ANCESTOR='0bcc187b3005478baa586a6d6f450e73811ca342'
MAX_SECONDS=3600
PROBE_SECONDS=3100
AUDIT_SECONDS=360
MAX_AS_BYTES=24*1024**3
MIN_EFFECTIVE_MEMORY_BYTES=20*1024**3
MODULES=('_make_it_stand','_cherchi_core_boolean','_cherchi_rational_moments')


def read_machine_memory():
    meminfo={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        parts=line.replace(':','').split()
        if len(parts)>1 and parts[0] in ('MemTotal','MemAvailable','SwapTotal'):
            meminfo[parts[0]]=int(parts[1])*1024
    cap=None
    for name in ('/sys/fs/cgroup/memory.max','/sys/fs/cgroup/memory/memory.limit_in_bytes'):
        path=Path(name)
        if path.is_file():
            value=path.read_text().strip()
            if value.isdigit():
                observed=int(value)
                if 0<observed<1<<60:
                    cap=observed if cap is None else min(cap,observed)
    effective=min(meminfo.get('MemTotal',0),cap) if cap else meminfo.get('MemTotal',0)
    return {'physical_mem_bytes':meminfo.get('MemTotal',0),
            'mem_available_bytes':meminfo.get('MemAvailable',0),
            'container_memory_limit_bytes':cap,
            'effective_memory_bytes':effective,
            'physical_swap_bytes':meminfo.get('SwapTotal',0)}


def git_ref(repo):
    def call(args):
        p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,timeout=10)
        return p.stdout.strip() if p.returncode==0 else None
    branch=call(['symbolic-ref','--quiet','--short','HEAD'])
    # merge-base --is-ancestor prints nothing on success; check status directly.
    verify=subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',ANCESTOR,'HEAD'],
                          capture_output=True,text=True,timeout=10)
    head=call(['rev-parse','HEAD'])
    return {'branch':branch,'head_sha':head,'frozen_ancestor_is_ancestor':verify.returncode==0}


def preflight(repo):
    memory=read_machine_memory()
    try:
        checked=git_ref(repo)
    except (OSError,subprocess.TimeoutExpired):
        checked={'branch':None,'head_sha':None,'frozen_ancestor_is_ancestor':False}
    found={name:importlib.util.find_spec(name) is not None for name in MODULES}
    problems=[]
    if memory['effective_memory_bytes']<MIN_EFFECTIVE_MEMORY_BYTES:
        problems.append('INSUFFICIENT_EFFECTIVE_MEMORY_FOR_24GIB_ISOLATED_NATIVE_JOB')
    if memory['physical_swap_bytes']!=0:
        problems.append('SWAP_ZERO_RESOURCE_PROTOCOL_VIOLATED')
    if checked['branch']!=BRANCH or not checked['frozen_ancestor_is_ancestor']:
        problems.append('NOT_A_FROZEN_W3_GIT_CHECKOUT')
    if not all(found.values()):
        problems.append('PINNED_NATIVE_EXTENSIONS_UNAVAILABLE')
    return {
        'schema':'heart-h9-stage5-serial-native-preflight-v1',
        'repo_path':str(Path(repo).resolve()),
        'branch_state':checked,'memory':memory,
        'module_import_spec_presence':found,
        'cpu_threads':1,'gpu_training':False,
        'process_virtual_memory_cap_bytes':MAX_AS_BYTES,
        'max_total_wall_seconds':MAX_SECONDS,
        'max_probe_wall_seconds':PROBE_SECONDS,
        'max_independent_audit_wall_seconds':AUDIT_SECONDS,
        'newton_admitted':False,
        'status':'READY_TO_ATTEMPT_REAL_CHERCHI' if not problems else 'BLOCKED_NO_NATIVE_EVALUATION',
        'blockers':problems,
    }


def capped_exec(argv,seconds,stdout_path,stderr_path):
    def impose_limit():
        resource.setrlimit(resource.RLIMIT_AS,(MAX_AS_BYTES,MAX_AS_BYTES))
    env=os.environ.copy()
    env.update({'OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1',
                'MKL_NUM_THREADS':'1','PYTHONUNBUFFERED':'1'})
    with stdout_path.open('x') as stdout,stderr_path.open('x') as stderr:
        try:
            proc=subprocess.run(argv,stdout=stdout,stderr=stderr,env=env,
                                timeout=seconds,preexec_fn=impose_limit)
            return proc.returncode
        except subprocess.TimeoutExpired:
            return 124


def run_once(artifact,certificate,output):
    folder=Path(__file__).resolve().parents[4]
    out=Path(output)
    out.mkdir(parents=True,exist_ok=False)
    info=preflight(folder)
    info['original_h8f_artifact_sha256_expected']='99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
    (out/'preflight.json').write_text(json.dumps(info,indent=2,sort_keys=True)+'\n')
    if info['blockers']:
        print('H9_NATIVE_PREFLIGHT_BLOCKED_NO_NEW_NATIVE_CALLS',','.join(info['blockers']))
        return 2
    start=time.monotonic()
    source=Path(__file__).resolve().parent
    native_dir=out/'native'
    call=[sys.executable,str(source/'probe_h9_crossing_sides_live.py'),
          '--artifact',str(artifact),'--certificate',str(certificate),
          '--output',str(native_dir)]
    result=capped_exec(call,PROBE_SECONDS,out/'probe.stdout.txt',out/'probe.stderr.txt')
    if result!=0:
        status={'status':'REAL_NATIVE_PROBE_FAILED_NO_ADMISSION','probe_exit_code':result,
                'newton_admitted':False,'new_native_calls_verified':0}
        (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n')
        return result
    remain=int(MAX_SECONDS-(time.monotonic()-start)-30)
    if remain<=0:
        status={'status':'REAL_NATIVE_PROBE_FINISHED_BUT_NO_TIME_FOR_INDEPENDENT_AUDIT',
                'newton_admitted':False,'new_native_calls_verified':0}
        (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n')
        return 124
    call=[sys.executable,str(source/'audit_h9_new_native_sides.py'),
          '--artifact',str(artifact),'--certificate',str(certificate),
          '--native-dir',str(native_dir),'--output',str(out/'independent-audit.json')]
    result=capped_exec(call,min(AUDIT_SECONDS,remain),out/'audit.stdout.txt',out/'audit.stderr.txt')
    status={'status':('FOUR_NEW_REAL_NATIVE_POINTS_AND_INDEPENDENT_AUDIT_FINISHED_NO_NEWTON'
                      if result==0 else 'INDEPENDENT_AUDIT_FAILED_NO_ADMISSION'),
            'audit_exit_code':result,'newton_admitted':False}
    (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',type=Path,required=True)
    p.add_argument('--certificate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    sys.exit(run_once(args.artifact,args.certificate,args.output))

if __name__=='__main__':main()

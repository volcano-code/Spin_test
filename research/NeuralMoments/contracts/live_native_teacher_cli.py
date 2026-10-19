"""W0 M4: one native Cherchi replay with resource admission and audit log.

Invocation from repo root (24GiB/no-swap host, trusted factory provided by W2):
 python -m research.NeuralMoments.contracts.live_native_teacher_cli \
     --factory trusted_fixture_module:prepare_one \
     --pins frozen_native_pins.json --output w0_m4_native_evidence.json

The factory must return (authentic_InProcessCherchiEvaluator, SpinArtifactProblem,
normalized_native_c). Pins are PRECOMMITTED external SHA256 digests for the
native .so, exact Cherchi bridge .so, and in-process adapter .py.

Pins also contain externally frozen native c hash, complete problem input
digest, and evaluator context digest. Missing native runtime always fails.
Even successful live replay does not certify a smooth derivative or training.
"""
from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
import subprocess
import sys
import time

from .native_teacher_replay import (ReplayRejected, audit_live_native_once,
                                    canonical, digest, sha256_file)

MINIMUM_RAM_GIB = 20.0  # admission for the planned nominal 24GiB/swap0 node
MAX_RUNTIME_SECONDS = 3600


def linux_resources(read_text=None):
    """Only /proc/meminfo is supported; unknown host must fail closed."""
    if read_text is None:
        read_text=Path('/proc/meminfo').read_text(encoding='ascii')
    numbers={}
    for line in read_text.splitlines():
        words=line.split()
        if len(words)>=3 and words[2]=='kB' and words[1].isdecimal():
            numbers[words[0].rstrip(':')]=int(words[1])
    if 'MemTotal' not in numbers or 'SwapTotal' not in numbers:
        raise ReplayRejected('HOST_RESOURCE_INFORMATION_UNAVAILABLE')
    return dict(physical_memory_gib=numbers['MemTotal']/1024**2,
                swap_kib=numbers['SwapTotal'])


def admissible(resources):
    if resources['physical_memory_gib']<MINIMUM_RAM_GIB:
        return 'BLOCKED_INSUFFICIENT_PHYSICAL_RAM'
    if resources['swap_kib']!=0:
        return 'BLOCKED_NONZERO_SWAP'
    return 'ADMITTED_RESOURCE_POLICY_ONLY'


def store_report(path,report):
    if path is None:
        print(canonical(report))
        return
    dest=Path(path)
    dest.parent.mkdir(parents=True,exist_ok=True)
    staging=dest.with_suffix(dest.suffix+'.tmp')
    staging.write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    staging.replace(dest)
    print(canonical(report))


def execute_worker(args):
    # Import an explicitly chosen locally trusted research fixture. This is
    # intentionally NOT a deserialization/eval of an uploaded class or pickle.
    module_name,colon,function_name=args.factory.partition(':')
    if not colon or not module_name or not function_name or not function_name.isidentifier():
        raise ReplayRejected('TRUSTED_FACTORY_MUST_BE_module:function')
    pins=json.loads(Path(args.pins).read_text(encoding='utf-8'))
    module=importlib.import_module(module_name)
    factory=getattr(module,function_name)
    if not callable(factory):
        raise ReplayRejected('TRUSTED_FACTORY_NOT_CALLABLE')
    prepared=factory()
    if not isinstance(prepared,tuple) or len(prepared)!=3:
        raise ReplayRejected('FACTORY_EXPECTS_evaluator_problem_c')
    evaluator,problem,c=prepared
    return audit_live_native_once(evaluator=evaluator,problem=problem,c=c,pins=pins)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--factory',required=True)
    parser.add_argument('--pins',required=True)
    parser.add_argument('--output')
    parser.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    report=dict(schema='W0_M4_ONE_CALL_RESOURCE_GATED_V1',
                training_admissible=False,
                smooth_derivative_certified=False,
                true_cherchi_material_certified=False)  # syntax replaced below
    report['frozen_source_commit']='0bcc187b3005478baa586a6d6f450e73811ca342'
    report['source_branch']='research/neuralmoments-w0-contract-20261019'
    report['pins_file_sha256']=sha256_file(args.pins) if Path(args.pins).is_file() else None
    try:
        resources=linux_resources()
        report['host_resource_observation']=resources
        state=admissible(resources)
        if state!='ADMITTED_RESOURCE_POLICY_ONLY':
            report['status']=state
            store_report(args.output,report)
            return 3
        if args.worker:
            result=execute_worker(args)
            report.update(result)
            report['status']='REAL_NATIVE_REPLAY_PASSED_TRAINING_STILL_BLOCKED'
            store_report(args.output,report)
            return 0
        # Native call in a single isolated subprocess, kill on charter timeout.
        cmd=[sys.executable,'-m',__package__+'.live_native_teacher_cli',
             '--factory',args.factory,'--pins',args.pins,'--worker']
        proc=subprocess.run(cmd,capture_output=True,text=True,
                            timeout=MAX_RUNTIME_SECONDS)
        if proc.returncode==0:
            child=json.loads(proc.stdout.splitlines()[-1])
            report.update(child)
            report['status']='REAL_NATIVE_REPLAY_PASSED_TRAINING_STILL_BLOCKED'
            store_report(args.output,report)
            return 0
        report['status']='NATIVE_AUDIT_FAILED_OR_UNAVAILABLE'
        report['worker_returncode']=proc.returncode
        report['worker_stderr_excerpt']=proc.stderr[-4000:]
        store_report(args.output,report)
        return 4
    except subprocess.TimeoutExpired:
        report['status']='BLOCKED_NATIVE_RUNTIME_EXCEEDED_3600_SECONDS'
        store_report(args.output,report)
        return 5
    except (ReplayRejected,FileNotFoundError,ValueError,ImportError) as exc:
        report['status']='FAILED_CLOSED'
        report['reason']=type(exc).__name__+': '+str(exc)
        store_report(args.output,report)
        return 4


if __name__=='__main__':
    raise SystemExit(main())

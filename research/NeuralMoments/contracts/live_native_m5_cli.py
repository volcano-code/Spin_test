"""Run a single authentic Cherchi request with pinned W0 + W2 exact oracles.

Run ONLY on a node meeting charter resources, with a real trusted factory:
python -m research.NeuralMoments.contracts.live_native_m5_cli \
 --factory trusted_module:prepare_one --pins pinned_identity.json \
 --output w0_m5_native_result.json

Never releases training labels, even after numerical parity succeeds.
"""
from __future__ import annotations

import argparse
import fcntl
import importlib
import json
from pathlib import Path
import signal
import subprocess
import sys

from .live_native_teacher_cli import (admissible, linux_resources, store_report,
                                     MAX_RUNTIME_SECONDS)
from .native_teacher_replay import ReplayRejected, sha256_file
from .native_m5_bridge import audit_native_w0_w2_once

LOCK_PATH=Path('/tmp/spin_test_w0_m5_cherchi_job.lock')


def _locked_factory(args):
    modname,sep,function=args.factory.partition(':')
    if not sep or not modname or not function or not function.isidentifier() or \
            not all(x.isidentifier() for x in modname.split('.')):
        raise ReplayRejected('TRUSTED_FACTORY_MODULE_FUNCTION_REQUIRED')
    pins=json.loads(Path(args.pins).read_text(encoding='utf-8'))
    module=importlib.import_module(modname)
    entry=getattr(module,function,None)
    if not callable(entry):
        raise ReplayRejected('TRUSTED_FACTORY_NOT_CALLABLE')
    item=entry()
    if type(item) is not tuple or len(item)!=3:
        raise ReplayRejected('FACTORY_MUST_RETURN_NATIVE_EVALUATOR_PROBLEM_C')
    evaluator,problem,c=item
    return audit_native_w0_w2_once(evaluator=evaluator,problem=problem,c=c,pins=pins)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--factory',required=True)
    p.add_argument('--pins',required=True)
    p.add_argument('--output')
    p.add_argument('--_worker',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args(argv)
    report={"schema":"W0_M5_NATIVE_TWO_ORACLE_RUNTIME_V1",
            "source":"volcano-code/Spin_test",
            "frozen_source_sha":"0bcc187b3005478baa586a6d6f450e73811ca342",
            "training_admissible":False,
            "full_material_partition_certified":False,
            "smooth_neighborhood_certified":False}
    try:
        report['resources']=linux_resources()
        resource_state=admissible(report['resources'])
        if resource_state!='ADMITTED_RESOURCE_POLICY_ONLY':
            report['status']=resource_state
            store_report(args.output,report)
            return 3
        if not Path(args.pins).is_file():
            raise ReplayRejected('MISSING_PRECOMMITTED_SHA_PINS')
        report['pins_file_sha256']=sha256_file(args.pins)
        if args._worker:
            # Direct invocation does not avoid the 60-minute kill switch.
            signal.alarm(MAX_RUNTIME_SECONDS)
            result=_locked_factory(args)
            report.update(result)
            report['status']='REAL_NATIVE_TWO_ORACLE_PARITY_TRAINING_STILL_BLOCKED'
            store_report(None,report)
            return 0
        LOCK_PATH.parent.mkdir(parents=True,exist_ok=True)
        with LOCK_PATH.open('a+') as lock:
            try:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                report['status']='BLOCKED_OTHER_W0_M5_NATIVE_JOB_ACTIVE'
                store_report(args.output,report)
                return 3
            cmd=[sys.executable,'-m',__package__+'.live_native_m5_cli',
                 '--factory',args.factory,'--pins',str(Path(args.pins).resolve()),'--_worker']
            try:
                run=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                   text=True,timeout=MAX_RUNTIME_SECONDS)
            except subprocess.TimeoutExpired:
                report['status']='BLOCKED_NATIVE_RUNTIME_EXCEEDED_3600_SECONDS'
                store_report(args.output,report)
                return 5
        if run.returncode!=0:
            report['status']='FAILED_NATIVE_W0_W2_PARITY_OR_RUNTIME'
            report['worker_exit_code']=run.returncode
            report['worker_stderr_excerpt']=run.stderr[-4000:]
            store_report(args.output,report)
            return 4
        try:
            item=json.loads(run.stdout.splitlines()[-1])
        except (ValueError,IndexError) as exc:
            raise ReplayRejected('NATIVE_WORKER_RESULT_NOT_VALID_JSON') from exc
        if item.get('status')!='REAL_NATIVE_TWO_ORACLE_PARITY_TRAINING_STILL_BLOCKED' or \
                item.get('training_admissible') is not False:
            raise ReplayRejected('NATIVE_WORKER_CLAIMED_UNEXPECTED_ADMISSION')
        report.update(item)
        store_report(args.output,report)
        return 0
    except (ReplayRejected,RuntimeError,ImportError,ValueError,TypeError,
            FileNotFoundError,PermissionError,OverflowError) as exc:
        report['status']='FAILED_CLOSED'
        report['reason']=type(exc).__name__+': '+str(exc)
        store_report(args.output,report)
        return 4


if __name__=='__main__':
    raise SystemExit(main())

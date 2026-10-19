"""W0 M6: resource-serialized authentic exact FULL PARTITION native replay.

Requires trusted factory module:function -> (evaluator, locked_problem, native_c)
and externally PRECOMMITTED six-M4-pin JSON. Performs one source plus retained
and complementary same-source Cherchi Boolean (2 total), not a Newton solve.
Results NEVER automatically release a W2 training label.
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

from .full_partition_m6 import audit_native_full_partition_once
from .live_native_teacher_cli import admissible, linux_resources, MAX_RUNTIME_SECONDS
from .native_teacher_replay import ReplayRejected, canonical, sha256_file

# Share the W0 M5 intra-window lock. Other windows require an external
# cross-window serial scheduler: THIS DOES NOT LOCK W1/W2.
from .live_native_m5_cli import LOCK_PATH


def _trusted_factory(value):
    module,sep,function=value.partition(':')
    if not sep or not module or not function or not function.isidentifier() or \
       not all(segment.isidentifier() for segment in module.split('.')):
        raise ReplayRejected('TRUSTED_FACTORY_MODULE_FUNCTION_REQUIRED')
    return module,function


def _run_worker(args):
    module,function=_trusted_factory(args.factory)
    pins=json.loads(Path(args.pins).read_text(encoding='utf-8'))
    if type(pins) is not dict or set(pins)!={
            'native_sha256','bridge_sha256','adapter_sha256',
            'c_sha256','problem_input_digest','context_sha256'}:
        raise ReplayRejected('PRECOMMITTED_M4_PIN_SET_REQUIRED')
    factory=getattr(importlib.import_module(module),function,None)
    if not callable(factory):
        raise ReplayRejected('TRUSTED_FACTORY_MISSING')
    prepared=factory()
    if type(prepared) is not tuple or len(prepared)!=3:
        raise ReplayRejected('TRUSTED_FACTORY_MUST_RETURN_REAL_EVALUATOR_PROBLEM_COEFFICIENTS')
    evaluator,problem,c=prepared
    result=audit_native_full_partition_once(evaluator=evaluator,problem=problem,c=c,pins=pins)
    if result.get('schema')!='W0_M6_NATIVE_COMPLETE_MATERIAL_PARTITION_V1' or \
       result.get('native_full_partition_certified') is not True or \
       result.get('training_admissible') is not False:
        raise ReplayRejected('REAL_NATIVE_PARTITION_EVIDENCE_MISSING_OR_TRAINING_RELEASE_CLAIM')
    return result


def _emit(path,report):
    """Evidence-only CREATE; never rewrite previously stored failure reports."""
    output=canonical(report)
    if path is not None:
        dest=Path(path)
        dest.parent.mkdir(parents=True,exist_ok=True)
        try:
            with dest.open('x',encoding='utf-8') as f:
                f.write(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n')
        except FileExistsError as e:
            raise ReplayRejected('EVIDENCE_FILE_EXISTS_NO_OVERWRITE') from e
    print(output)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--factory',required=True)
    parser.add_argument('--pins',required=True)
    parser.add_argument('--output')
    parser.add_argument('--_worker',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    report={
        'schema':'W0_M6_NATIVE_FULL_PARTITION_RUNTIME_V1',
        'frozen_source_sha':'0bcc187b3005478baa586a6d6f450e73811ca342',
        'training_admissible':False,
        'smooth_neighborhood_certified':False,
        'newton_terminal_certified':False,
        'native_full_partition_certified':False,
    }
    if args.output and Path(args.output).exists():
        print('EVIDENCE_FILE_EXISTS_NO_OVERWRITE',file=sys.stderr)
        return 4
    try:
        report['resources']=linux_resources()
        resource_state=admissible(report['resources'])
        if resource_state!='ADMITTED_RESOURCE_POLICY_ONLY':
            report['status']=resource_state
            _emit(args.output,report)
            return 3
        _trusted_factory(args.factory)
        if not Path(args.pins).is_file():
            raise ReplayRejected('PRECOMMITTED_SHA_PINS_MISSING')
        report['pins_file_sha256']=sha256_file(args.pins)
        if args._worker:
            signal.alarm(MAX_RUNTIME_SECONDS)
            result=_run_worker(args)
            report.update(result)
            report['status']='REAL_NATIVE_FULL_PARTITION_VERIFIED_DERIVATIVE_AND_TERMINAL_PENDING'
            _emit(None,report)
            return 0
        with LOCK_PATH.open('a+') as lock:
            try:
                fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                report['status']='BLOCKED_OTHER_W0_M5_M6_NATIVE_JOB_ACTIVE'
                _emit(args.output,report)
                return 3
            command=[sys.executable,'-m',__package__+'.live_native_m6_cli',
                     '--factory',args.factory,'--pins',str(Path(args.pins).resolve()),'--_worker']
            try:
                run=subprocess.run(command,capture_output=True,text=True,
                                   timeout=MAX_RUNTIME_SECONDS)
            except subprocess.TimeoutExpired:
                report['status']='BLOCKED_NATIVE_RUNTIME_EXCEEDED_3600_SECONDS'
                _emit(args.output,report)
                return 5
        if run.returncode:
            report['status']='FAILED_NATIVE_PARTITION_OR_WORKER'
            report['worker_exit_code']=run.returncode
            report['worker_stderr_excerpt']=run.stderr[-2000:]
            _emit(args.output,report)
            return 4
        try:
            item=json.loads(run.stdout.splitlines()[-1])
        except (ValueError,IndexError) as exc:
            raise ReplayRejected('NATIVE_WORKER_JSON_INVALID') from exc
        if item.get('schema')!='W0_M6_NATIVE_FULL_PARTITION_RUNTIME_V1' or \
           item.get('native_full_partition_certified') is not True or \
           item.get('training_admissible') is not False:
            raise ReplayRejected('NATIVE_WORKER_NO_VERIFIABLE_FULL_PARTITION')
        report.update(item)
        report['status']='REAL_NATIVE_FULL_PARTITION_VERIFIED_DERIVATIVE_AND_TERMINAL_PENDING'
        _emit(args.output,report)
        return 0
    except (ReplayRejected,RuntimeError,ImportError,ValueError,TypeError,
            FileNotFoundError,PermissionError,OverflowError,OSError) as exc:
        report['status']='FAILED_CLOSED'
        report['reason']=f'{type(exc).__name__}: {exc}'
        try:
            _emit(args.output,report)
        except ReplayRejected:
            print('EVIDENCE_FILE_EXISTS_NO_OVERWRITE',file=sys.stderr)
        return 4


if __name__=='__main__':
    raise SystemExit(main())

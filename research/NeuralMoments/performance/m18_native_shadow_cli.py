"""M18 read-only shadow analysis of four saved M9 native-call failure receipts.

It cannot replace M9/M11/W0 production admission. It only explains whether
M9 failed on last-bit Jacobian noise or on exact geometry/provenance/moments.
Missing, partial or tampered M9 receipts are fatal; never run Cherchi here.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
from m18_jacobian_repeatability import ABBA_ORDER, shadow_abba


def _load_strict(path):
    path=Path(path)
    if not path.is_file() or not 0<path.stat().st_size<2_000_000:
        raise ValueError('M18_M9_JSON_MISSING_OR_OVERSIZED:'+path.name)
    def pairs(items):
        out={}
        for k,v in items:
            if k in out:raise ValueError('M18_M9_DUPLICATE_JSON_KEY')
            out[k]=v
        return out
    def nonfinite(x):raise ValueError('M18_M9_NONFINITE_TOKEN:'+x)
    return json.loads(path.read_bytes(),object_pairs_hook=pairs,parse_constant=nonfinite)


def analyze(m9_output):
    directory=Path(m9_output)
    failure=_load_strict(directory/'failure.json')
    if (failure.get('schema')!='w1-m9-fail-closed-v1' or
        failure.get('status')!='BLOCKED_OR_FAILED_NO_NATIVE_ABBA_CERTIFICATE' or
        failure.get('completed_points')!=4 or
        failure.get('stage')!='REAL_CHERCHI_ABBA'):
        raise ValueError('M18_FULL_FOUR_SAVED_FAILING_M9_CALLS_REQUIRED')
    rows=[];paths=[]
    for i,variant in enumerate(ABBA_ORDER):
        stem=f'point-{i:03d}-{variant}'
        row=_load_strict(directory/(stem+'.json'))
        if row.get('iteration')!=i or row.get('mode')!=variant:
            raise ValueError('M18_WRONG_SAVED_CALL_ORDER')
        rows.append(row)
        paths.append(directory/(stem+'.json.gz'))
    diagnostic=shadow_abba(rows,paths)
    if diagnostic.get('eligible_for_w1_production_speed_claim') is not False:
        raise ValueError('M18_SHADOW_PROMOTION_FORBIDDEN')
    return dict(schema='w1-m18-failed-m9-shadow-analysis-v1',
        scope='READ_ONLY_M9_FAILURE_DIAGNOSTIC_NOT_FRESH_EXECUTION',
        original_m9_failure_sha256=sha256((directory/'failure.json').read_bytes()).hexdigest(),
        original_strict_m9_failure_unchanged=True,
        saved_call_count=4,science_diagnostic=diagnostic,
        verified_native_source_runtime_independently=False,
        W0_smooth_Jacobian_acceptance=False,
        material_geometry_audits_not_skipped=True,
        W1_production_speedup_admitted=False,
        full_newton_speedup=None,paper_speed_qualified=False)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--m9-output',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError('M18_SHADOW_NO_OVERWRITE')
    try:
        result=analyze(args.m9_output)
    except BaseException as exc:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        fail=args.output.with_suffix('.failure.json')
        if not fail.exists():fail.write_text(json.dumps({
            'schema':'w1-m18-shadow-failed-v1',
            'status':'NOT_ADMITTED',
            'error':type(exc).__name__+': '+str(exc),
            'original_m9_failure_must_be_preserved':True,
            'paper_speed_qualified':False},indent=2)+'\n')
        raise
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('M18_SHADOW_DIAGNOSTIC_NOT_ADMITTED',result['saved_call_count'])

if __name__=='__main__':main()

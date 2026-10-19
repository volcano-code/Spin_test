"""W1 M5: reconcile same-run historical timing without cross-run accounting.

This static audit is never presented as a newly executed Cherchi solver.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import math

EXPECTED_RUN = 39121571756
EXPECTED_ARCHIVE = '14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38'
EXPECTED_REQUEST = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'


def make_report(record):
    if (record.get('schema') != 'w1-m4-archived-25point-stage-baseline-v1' or
            record.get('source_run_id') != EXPECTED_RUN or
            record.get('archive_sha256') != EXPECTED_ARCHIVE or
            record.get('frozen_request_sha256') != EXPECTED_REQUEST or
            record.get('completed_points') != 25 or
            record.get('archived_25point_status') != 'FAILED_BRANCH_HASH_DRIFT_PRESERVED' or
            record.get('native_cherchi_boolean_calls') != 0 or
            record.get('complete_solver_measured') is not False or
            record.get('archived_jacobian_not_recomputed') is not True):
        raise ValueError('M5_HISTORICAL_SCOPE_OR_IDENTITY_DRIFT')
    wall=record['historical_wall_seconds']
    stages=record['historical_named_stage_seconds']
    recorded_unattributed=record['historical_unattributed_seconds']
    if (not isinstance(stages,dict) or not stages or
            not isinstance(wall,(float,int)) or not math.isfinite(wall) or wall<=0 or
            any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in stages.values())):
        raise ValueError('M5_INVALID_HISTORICAL_TIMES')
    summed=sum(stages.values())
    remainder=wall-summed
    if remainder < 0 or not math.isclose(remainder,recorded_unattributed,abs_tol=1e-6,rel_tol=0):
        raise ValueError('M5_TIME_LEDGER_NOT_CLOSED')
    prepared=stages.get('prepare_arithmetic_boundary')
    if not isinstance(prepared,(int,float)) or prepared<=0:
        raise ValueError('M5_PREPARED_STAGE_MISSING')
    replay_wall=record['replay_wall_seconds']
    replay_stages=record['replay_stage_totals_seconds']
    replay_residual=record['replay_unattributed_seconds']
    if (not isinstance(replay_stages,dict) or replay_wall<=0 or
            any(v<0 or not math.isfinite(v) for v in replay_stages.values()) or
            not math.isclose(replay_wall-sum(replay_stages.values()),replay_residual,
                             abs_tol=1e-5,rel_tol=0)):
        raise ValueError('M5_INDEPENDENT_REPLAY_LEDGER_NOT_CLOSED')
    return dict(schema='w1-m5-historical-stage-attribution-v1',
        scope='STATIC_INTRA_RUN_ACCOUNTING_NOT_FRESH_BOOLEAN',
        archived_run_id=EXPECTED_RUN,archived_25point_failed=True,
        named_total_seconds=summed,recorded_wall_seconds=wall,
        unattributed_seconds=remainder,
        unattributed_fraction=remainder/wall,
        top_known_stages_seconds=dict(sorted(stages.items(),key=lambda x:-x[1])),
        original_prepared_boundary_seconds=prepared,
        ideal_elimination_of_prepared_stage_max_wall_saving_fraction=prepared/wall,
        ideal_elimination_of_prepared_stage_max_speedup=wall/(wall-prepared),
        archived_material_replay_seconds=replay_wall,
        replay_original_machine_different=True,
        cross_host_unattributed_time_subtraction_forbidden=True,
        original_25point_branch_changes=8,
        profiler_source_sha_required='f9fa539f699df8baf8b8d30729048269a26ecb3c',
        w0_w2_admission_pending=True,
        production_before_after_speedup=None,
        paper_speed_qualified=False)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--m4-report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError('M5_WILL_NOT_OVERWRITE_EVIDENCE')
    record=json.loads(args.m4_report.read_text())
    report=make_report(record)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'unattributed_fraction':report['unattributed_fraction'],
                      'prepared_stage_ideal_bound':report['ideal_elimination_of_prepared_stage_max_speedup']}))

if __name__=='__main__':main()

"""W1 M16: independently reconcile real GitHub Actions H8e native 25-point evidence.

This reads IMMUTABLE historical Cherchi materials and optionally actual Actions
job-log lines. It does NOT execute new Boolean calls, generate a Jacobian, or
claim Newton convergence or a solver speedup. All stages in this report come
from one archived same-host native job and never from local GMP replay timing.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import statistics
from zipfile import ZipFile

ORIGINAL_RUN = 39121571756
ORIGINAL_JOB = 117658066974
ORIGINAL_ZIP_SHA = '14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38'
ORIGINAL_REQUEST_SHA = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
ORIGINAL_HEAD = 'fd7459f7bf10344269d3b9b3ada39d3e81edde48'
H8E = 'artifacts/h8e-jacobian-cols0-4-8/'
STAGES = ('source','physical_source_boundary','boolean','intersection_motion',
          'prepare_arithmetic_boundary','derivative','integration',
          'material_attachment_serialization')
BACKEND = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'
LOG_ROW = re.compile(r'^(?P<time>\S+Z) H8e REAL_CHERCHI (?P<point>\d+)/25 (?P<wall>\d+\.\d+)s$')
LOG_FINAL = re.compile(r'^\S+Z H8e_JACOBIAN (?P<record>\{.*\})$')


def finite_number(x):
    return type(x) in (int,float) and math.isfinite(x)


def sha(data: bytes):
    return sha256(data).hexdigest()


def member(zip_file, name, maximum=10_000_000):
    hits = [e for e in zip_file.infolist() if e.filename == name]
    if len(hits)!=1 or not 0 < hits[0].file_size <= maximum:
        raise ValueError('M16_MEMBER_MISSING_DUPLICATE_OR_OVERSIZED:'+name)
    return zip_file.read(hits[0])


def load_original(zip_path):
    zip_path=Path(zip_path)
    if sha(zip_path.read_bytes())!=ORIGINAL_ZIP_SHA:
        raise ValueError('M16_ARCHIVE_NOT_ORIGINAL_ACTIONS_RUN')
    with ZipFile(zip_path) as z:
        request = member(z,'artifacts/h8-request/prepared-request.json')
        if sha(request)!=ORIGINAL_REQUEST_SHA:
            raise ValueError('M16_FROZEN_REQUEST_CHANGED')
        report=json.loads(member(z,H8E+'report.json'))
        rows=[]
        for i in range(25):
            row=json.loads(member(z,H8E+f'point-{i:03d}.json'))
            if sha(member(z,H8E+f'point-{i:03d}-material.json.gz',maximum=4_000_000)) != row.get('exact_same_call_material_archive_sha256'):
                raise ValueError('M16_ARCHIVED_SAME_CALL_PACKET_SHA_CHANGED:'+str(i))
            rows.append(row)
        return report,rows


def reconcile(report, rows):
    if (report.get('schema')!='heart-h8e-real-cherchi-jacobian-pilot-v1' or
        report.get('completed_samples')!=25 or report.get('production_cherchi_calls')!=25 or
        report.get('planned_sample_count')!=25 or
        report.get('columns_requested')!=[0,4,8] or
        report.get('original_author_cad') is not False or
        report.get('formal_newton_converged') is not False or
        report.get('qualified_branch_neighborhood') is not False or
        report.get('all_numerical_checks_passed') is not True or
        report.get('all_tested_stencils_same_feature_hash') is not False or
        report.get('changed_feature_hash_points')!=8):
        raise ValueError('M16_ORIGINAL_H8E_FAILURE_SCOPE_CHANGED')
    if (len(rows)!=25 or report.get('input_request_sha256')!=ORIGINAL_REQUEST_SHA or
        report.get('ambient_jacobian_shape')!=[10,10] or
        len(report.get('analytic_10_by_10_jacobian',[]))!=10 or
        any(len(x)!=10 or not all(map(finite_number,x)) for x in report['analytic_10_by_10_jacobian'])):
        raise ValueError('M16_ORIGINAL_MOMENT_JACOBIAN_OR_REQUEST_MISMATCH')
    if not all(re.fullmatch('[0-9a-f]{64}',report.get(k,'')) for k in
        ('actual_native_sha256','actual_cherchi_sha256','actual_arithmetic_sha256')):
        raise ValueError('M16_NATIVE_BUNDLE_IDENTITY_MISSING')
    point_walls=[]; point_stages=[];point_residuals=[];changed=[];summed=dict.fromkeys(STAGES,0.0)
    proof=[]
    for i,row in enumerate(rows):
        stages=row.get('stages_seconds',{})
        if (row.get('index')!=i or row.get('vertex_count')!=8455 or
            row.get('triangle_count')!=16910 or
            row.get('exact_native_material_boundary_passed') is not True or
            not str(row.get('native_boolean_backend','')).startswith(BACKEND) or
            not re.fullmatch('[0-9a-f]{64}',str(row.get('material_geometry_hash',''))) or
            not re.fullmatch('[0-9a-f]{64}',str(row.get('exact_same_call_material_archive_sha256',''))) or
            len(row.get('coefficients',[]))!=10 or
            not all(map(finite_number,row['coefficients'])) or
            len(row.get('production_variable_raw_moments',[]))!=10 or
            len(row.get('independent_variable_raw_moments',[]))!=10 or
            not all(map(finite_number,row['production_variable_raw_moments'])) or
            not all(map(finite_number,row['independent_variable_raw_moments'])) or
            not finite_number(row.get('independent_moments_max_scaled_error')) or
            row['independent_moments_max_scaled_error']>1e-10 or
            set(stages)!=set(STAGES) or
            any(not finite_number(v) or v<0 for v in stages.values()) or
            not finite_number(row.get('wall_seconds')) or row['wall_seconds']<=0):
            raise ValueError('M16_INCOMPLETE_OR_UNTRUSTWORTHY_NATIVE_POINT:'+str(i))
        for s in STAGES: summed[s]+=stages[s]
        stage_time=sum(stages.values()); wall=row['wall_seconds']
        if stage_time>wall:
            raise ValueError('M16_NEGATIVE_POINT_RESIDUAL:'+str(i))
        point_walls.append(wall);point_stages.append(stage_time);point_residuals.append(wall-stage_time)
        if row.get('feature_branch_hash')!=rows[0].get('feature_branch_hash'):
            changed.append(i)
        proof.append(dict(index=i,wall_seconds=wall,identified_stage_seconds=stage_time,
                          unidentified_in_point_seconds=wall-stage_time,
                          changed_feature_hash=i in changed,
                          exact_same_call_material_sha256=row['exact_same_call_material_archive_sha256']))
    if changed!=list(range(17,25)):
        raise ValueError('M16_ORIGINAL_EIGHT_CHANGED_FEATURE_HASHES_NOT_PRESERVED')
    totals=report.get('stage_totals_seconds',{})
    if set(totals)!=set(STAGES) or any(not finite_number(v) or abs(summed[k]-v)>1e-6 for k,v in totals.items()):
        raise ValueError('M16_STAGE_SUMMARY_NOT_SAME_RUN')
    wall=report.get('wall_seconds')
    if not finite_number(wall) or wall < sum(point_walls):
        raise ValueError('M16_WALL_DOES_NOT_INCLUDE_ALL_NATIVE_POINTS')
    for key in STAGES:
        if report.get('call_counts',{}).get(key)!=25:
            raise ValueError('M16_NATIVE_CALL_COUNT_MISMATCH:'+key)
    total_named=sum(point_stages)
    outside=wall-sum(point_walls)
    unidentified=sum(point_residuals)
    if outside<-1e-7 or abs(wall-(total_named+outside+unidentified))>1e-6:
        raise ValueError('M16_TIME_LEDGER_DOES_NOT_CLOSE')
    return dict(schema='w1-m16-same-run-archived-h8e-native-attribution-v1',
                scope='ORIGINAL_GITHUB_ACTIONS_NATIVE_25POINT_FORENSIC_ONLY',
                original_run_id=ORIGINAL_RUN,original_job_id=ORIGINAL_JOB,
                original_run_head=ORIGINAL_HEAD,
                archive_sha256=ORIGINAL_ZIP_SHA,request_sha256=ORIGINAL_REQUEST_SHA,
                native_binary_sha256=report['actual_native_sha256'],
                cherchi_binary_sha256=report['actual_cherchi_sha256'],
                gmp_binary_sha256=report['actual_arithmetic_sha256'],
                sample_count=25,real_cherchi_calls_original_run=25,
                reported_job_wall_seconds=wall,
                sum_point_wall_seconds=sum(point_walls),
                sum_named_native_stages_seconds=total_named,
                sum_unidentified_within_point_seconds=unidentified,
                outside_point_orchestration_seconds=outside,
                named_stage_totals_seconds=summed,
                mean_unidentified_per_point_seconds=statistics.mean(point_residuals),
                median_unidentified_per_point_seconds=statistics.median(point_residuals),
                min_unidentified_per_point_seconds=min(point_residuals),
                max_unidentified_per_point_seconds=max(point_residuals),
                observed_feature_hash_changed_indices=changed,
                original_branch_neighborhood_admission=False,
                original_ci_outcome='FAILURE_FEATURE_HASH_DRIFT',
                fresh_W1_optimized_cherchi_calls=0,
                newton_or_terminal_material_proven=False,
                faster_full_solver_speedup=None,paper_speed_qualified=False,
                point_receipts=proof)


def check_job_log(data, rows, expected_original_job_wall):
    """Bind true Actions console lines to same-run archived point durations."""
    parsed=[]; final=None
    for original_line in data.splitlines():
        line=original_line.removeprefix('\ufeff').strip()
        m=LOG_ROW.fullmatch(line)
        if m:
            parsed.append((m.group('time'),int(m.group('point')),float(m.group('wall'))))
        f=LOG_FINAL.fullmatch(line)
        if f:
            if final is not None: raise ValueError('M16_MULTIPLE_FINAL_LOG_SUMMARIES')
            final=json.loads(f.group('record'))
    if len(parsed)!=25 or [row[1] for row in parsed]!=list(range(1,26)):
        raise ValueError('M16_INCOMPLETE_DUPLICATE_OR_UNORDERED_ACTIONS_CONSOLE')
    last=None
    for i,(iso,_,wall) in enumerate(parsed):
        when=datetime.fromisoformat(iso.replace('Z','+00:00'))
        if when.tzinfo is None or (last is not None and when<=last):
            raise ValueError('M16_INVALID_ACTIONS_TIME_ORDER')
        last=when
        if abs(wall-rows[i]['wall_seconds'])>0.011:
            raise ValueError('M16_ACTIONS_LOG_NOT_MATCHING_ORIGINAL_ARCHIVE_POINT:'+str(i))
    if (final is None or final.get('completed_samples')!=25 or
        final.get('changed_feature_hash_points')!=8 or
        final.get('all_tested_stencils_same_feature_hash') is not False or
        final.get('all_numerical_checks_passed') is not True or
        abs(final.get('wall_seconds',-1)-expected_original_job_wall)>1e-6):
        raise ValueError('M16_ACTIONS_LOG_FINAL_STATUS_OR_WALL_DRIFT')
    return dict(real_actions_console_rows=25,console_final_status_preserved=True,
                console_first_sample_timestamp=parsed[0][0],
                console_last_sample_timestamp=parsed[-1][0],
                all_console_point_durations_match_archive=True)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--job-log',type=Path)
    a=ap.parse_args()
    if a.output.exists(): raise FileExistsError('M16_REFUSES_TO_OVERWRITE_EVIDENCE')
    try:
        original,rows=load_original(a.archive)
        result=reconcile(original,rows)
        if a.job_log is not None:
            result['original_actions_job_log']=check_job_log(
                a.job_log.read_text(encoding='utf-8-sig'),rows,original['wall_seconds'])
        else:
            result['original_actions_job_log']=None
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        print('M16_ORIGINAL_REAL_NATIVE_25POINT_SAME_RUN_AUDIT_PASS')
    except BaseException as exc:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        failure=a.output.with_suffix('.failure.json')
        if not failure.exists():
            failure.write_text(json.dumps(dict(status='FAILED_NO_NATIVE_EVIDENCE',
                error=type(exc).__name__+': '+str(exc),
                solver_speedup=None),indent=2)+'\n')
        raise


if __name__=='__main__': main()

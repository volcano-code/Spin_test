"""W1 M17: compare TWO REAL ORIGINAL H8e native Actions attempts.

These are repeated *baseline* evaluations of the unchanged frozen native build,
NOT W1 old-vs-optimized ABBA.  Full model, 25 per-point original material
snapshots, exact ten moments, all Jacobian entries, and stage time are compared.
A failure in the original stable-feature test remains a failure.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import gzip
import json
import math
from pathlib import Path
import statistics
import struct
from zipfile import ZipFile
try:
    import orjson as _fast_json
except ImportError:
    _fast_json = None


def _load_material(b):
    """Optional fast decoder; scientific comparisons are against source fields."""
    return _fast_json.loads(b) if _fast_json is not None else json.loads(b)

EXPECTED = {
    'attempt_1': '14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38',
    'attempt_2': 'b763aabfdcaddb821a8766bf661fb25c184f416aa96cb24609874b15f9bc08e1',
}
PREFIX = 'artifacts/h8e-jacobian-cols0-4-8/'
REQUEST = 'artifacts/h8-request/prepared-request.json'
REQUEST_SHA = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
NATIVE_SHA = {
    'actual_native_sha256':'ad0c4fe3527954c611743dbbccb384cc1521909e8a39d68c3b7554b3a3919d40',
    'actual_cherchi_sha256':'3cc8bf789168752f8b921c160ca9937cdf0f61c845d3088760811b9e5a4596b7',
    'actual_arithmetic_sha256':'ed05436e2796b190ddebb024f67318e2e88bdc46d96b01e9d7db71a6af080dca',
}
CAD = ('artifacts/h8-input/initial_top.obj',
       'artifacts/h8-input/fixed_shell.obj',
       'artifacts/h8-input/design_domain.obj')
REQUIRED_REPORT = ('input_request_sha256', 'actual_native_sha256',
                   'actual_cherchi_sha256', 'actual_arithmetic_sha256',
                   'columns_requested', 'target_q', 'completed_samples',
                   'all_numerical_checks_passed',
                   'all_tested_stencils_same_feature_hash',
                   'changed_feature_hash_points', 'ambient_jacobian_shape')
REQUIRED_POINT = ('coefficients', 'index', 'feature_branch_hash',
                  'material_geometry_hash', 'independent_variable_raw_moments',
                  'production_variable_raw_moments', 'full_raw_moments',
                  'vertex_count', 'triangle_count', 'exact_native_material_boundary_passed',
                  'native_boolean_backend')
FLOAT_MOMENT_FIELDS = ('variable_raw_moments','raw_moments')


def digest(b: bytes) -> str:
    return sha256(b).hexdigest()


def unique_member(z: ZipFile, name: str, max_bytes: int) -> bytes:
    info = [x for x in z.infolist() if x.filename == name]
    if len(info) != 1 or info[0].file_size <= 0 or info[0].file_size > max_bytes:
        raise ValueError('M17_MISSING_DUPLICATE_OR_OVERSIZED_MEMBER:' + name)
    return z.read(info[0])


def numeric_matrix(x):
    if (type(x) is not list or len(x)!=10 or any(
        type(row) is not list or len(row)!=10 or
        any(type(v) not in (float,int) or not math.isfinite(v) for v in row)
        for row in x)):
        raise ValueError('M17_INVALID_JACOBIAN_SHAPE_OR_FINITE')
    return x


def binary64_equal(a,b):
    if len(a)!=len(b):return False
    return all(type(x) in (float,int) and type(y) in (float,int) and
               math.isfinite(x) and math.isfinite(y) and
               struct.pack('>d',x)==struct.pack('>d',y) for x,y in zip(a,b))


def compare_material(a, b):
    """Exact non-Jacobian state is mandatory. J repeatability is measured.

    DO NOT treat a numerical Jacobian match as original stable-feature admission.
    Nor silently reinterpret serialized material SHA inequality as geometry drift.
    """
    if not isinstance(a,dict) or not isinstance(b,dict):
        raise ValueError('M17_MATERIAL_NOT_DICT')
    aj=numeric_matrix(a.get('moment_jacobian'))
    bj=numeric_matrix(b.get('moment_jacobian'))
    for key in ('variable_raw_moments','raw_moments'):
        if not binary64_equal(a.get(key,[]),b.get(key,[])) or len(a[key])!=10:
            raise ValueError('M17_ORIGINAL_TEN_MOMENTS_NOT_BITWISE_EQUAL:'+key)
    keys = set(a)|set(b)
    if 'moment_jacobian' not in keys or set(a)!=set(b):
        raise ValueError('M17_MATERIAL_KEYS_DRIFT')
    for key in keys - {'moment_jacobian'}:
        if a[key]!=b[key]:
            raise ValueError('M17_NONJACOBIAN_MATERIAL_DIFFERENCE:'+key)
    changes=[]
    max_abs=max_scaled=0.
    for i in range(10):
        for j in range(10):
            x,y=aj[i][j],bj[i][j]
            difference=abs(x-y)
            max_abs=max(max_abs,difference)
            max_scaled=max(max_scaled,difference/max(1.,abs(x),abs(y)))
            if struct.pack('>d',x)!=struct.pack('>d',y):
                changes.append((i,j))
    return dict(jacobian_bitwise_equal=len(changes)==0,
                changed_jacobian_entries=len(changes),
                max_abs_jacobian_difference=max_abs,
                max_scaled_jacobian_difference=max_scaled,
                nonjacobian_full_material_equivalent=True,
                raw_moments_bitwise_equivalent=True,
                changed_entries=changes)


def verify_report(a,b):
    if not isinstance(a,dict) or not isinstance(b,dict):
        raise ValueError('M17_REPORT_NOT_DICT')
    for field in REQUIRED_REPORT:
        if a.get(field)!=b.get(field):
            raise ValueError('M17_FROZEN_OR_FAILURE_STATUS_DRIFT:'+field)
    if (a['completed_samples']!=25 or a['columns_requested']!=[0,4,8] or
        a['all_numerical_checks_passed'] is not True or
        a['all_tested_stencils_same_feature_hash'] is not False or
        a['changed_feature_hash_points']!=8 or
        a['ambient_jacobian_shape']!=[10,10] or
        a.get('formal_newton_converged') is not False or
        b.get('formal_newton_converged') is not False or
        a.get('original_author_cad') is not False or
        b.get('original_author_cad') is not False):
        raise ValueError('M17_ORIGINAL_CI_FAILURE_MUST_BE_PRESERVED')
    for k,expected in NATIVE_SHA.items():
        if a[k]!=expected:
            raise ValueError('M17_MISSING_OR_UNPINNED_NATIVE_MODULE_SHA:'+k)
    numeric_matrix(a.get('analytic_10_by_10_jacobian'))
    numeric_matrix(b.get('analytic_10_by_10_jacobian'))
    return True


def compare(old_path,new_path):
    old_path,new_path=Path(old_path),Path(new_path)
    for k,p in (('attempt_1',old_path),('attempt_2',new_path)):
        if digest(p.read_bytes())!=EXPECTED[k]:
            raise ValueError('M17_GITHUB_ACTIONS_ARTIFACT_SHA_DRIFT:'+k)
    points=[];hash_changes=[]
    with ZipFile(old_path) as za, ZipFile(new_path) as zb:
        for name in (REQUEST,)+CAD:
            da=unique_member(za,name,7_000_000)
            db=unique_member(zb,name,7_000_000)
            if da!=db or (name==REQUEST and digest(da)!=REQUEST_SHA):
                raise ValueError('M17_FROZEN_INPUT_CHANGED:'+name)
        reports=[json.loads(unique_member(z,PREFIX+'report.json',400_000)) for z in (za,zb)]
        verify_report(*reports)
        # The H8c archived compressed packet can differ by gzip header, so
        # independently compare DECOMPRESSED exact geometry, not gzip timestamps.
        source='artifacts/h8-cherchi-point/actual-cherchi-packet.json.gz'
        raw_source=[gzip.decompress(unique_member(z,source,5_000_000)) for z in (za,zb)]
        if raw_source[0]!=raw_source[1]:
            raise ValueError('M17_BASE_CHERCHI_SOURCE_PACKET_CONTENT_DRIFT')
        for i in range(25):
            member=f'{PREFIX}point-{i:03d}.json'
            packet=f'{PREFIX}point-{i:03d}-material.json.gz'
            rows=[json.loads(unique_member(z,member,200_000)) for z in (za,zb)]
            zipped=[unique_member(z,packet,5_000_000) for z in (za,zb)]
            for r, blob in zip(rows,zipped):
                if (r.get('index')!=i or r.get('exact_same_call_material_archive_sha256')!=digest(blob) or
                    r.get('exact_native_material_boundary_passed') is not True or
                    r.get('vertex_count')!=8455 or r.get('triangle_count')!=16910 or
                    r.get('independent_moments_max_scaled_error',1)>1e-10 or
                    not (type(r.get('wall_seconds')) in (int,float) and
                         math.isfinite(r['wall_seconds']) and r['wall_seconds']>0)):
                    raise ValueError('M17_POINT_SAME_CALL_EVIDENCE_FAILED:'+str(i))
            for f in REQUIRED_POINT:
                if rows[0].get(f)!=rows[1].get(f):
                    raise ValueError('M17_POINT_SCIENTIFIC_IDENTITY_DRIFT:'+str(i)+':'+f)
            mats=[_load_material(gzip.decompress(blob)) for blob in zipped]
            match=compare_material(*mats)
            if rows[0]['feature_branch_hash']!=rows[1]['feature_branch_hash']:
                raise ValueError('M17_INTERNAL_HASH_DRIFT')
            if i>0 and rows[0]['feature_branch_hash']!=points[0]['feature_branch_hash']:
                hash_changes.append(i)
            if i % 5 == 0: print(f"M17_COMPARE_PAIR {i+1}/25",flush=True)
            points.append(dict(index=i,
                original_point_wall_seconds=rows[0]['wall_seconds'],
                repeated_point_wall_seconds=rows[1]['wall_seconds'],
                original_stages_seconds=rows[0].get('stages_seconds'),
                repeated_stages_seconds=rows[1].get('stages_seconds'),
                saved_material_gzip_sha256_old=digest(zipped[0]),
                saved_material_gzip_sha256_new=digest(zipped[1]),
                geometry_hash=rows[0]['material_geometry_hash'],
                feature_branch_hash=rows[0]['feature_branch_hash'],
                **{k:v for k,v in match.items() if k!='changed_entries'}))
            del mats, zipped
    if hash_changes!=list(range(17,25)):
        raise ValueError('M17_ORIGINAL_8_CHANGED_FEATURE_POINTS_NOT_PRESERVED')
    def sum_stages(column):
        keys=('source','physical_source_boundary','boolean','intersection_motion',
              'prepare_arithmetic_boundary','derivative','integration',
              'material_attachment_serialization')
        totals={k:0. for k in keys}
        wall=0.
        for p in points:
            span=p[column]
            if not isinstance(span,dict) or set(span)!=set(keys):
                raise ValueError('M17_INCOMPLETE_OR_EXTRA_NATIVE_STAGE')
            for k in keys:
                v=span[k]
                if type(v) not in (float,int) or not math.isfinite(v) or v<0:
                    raise ValueError('M17_INVALID_STAGE_TIMER')
                totals[k]+=v
            idx='original_point_wall_seconds' if column=='original_stages_seconds' else 'repeated_point_wall_seconds'
            total=sum(span.values())
            if total>p[idx]:raise ValueError('M17_NEGATIVE_PER_POINT_UNATTRIBUTED')
            wall+=p[idx]
        return totals,wall
    stages_old,pwall_old=sum_stages('original_stages_seconds')
    stages_new,pwall_new=sum_stages('repeated_stages_seconds')
    diff_count=sum(p['changed_jacobian_entries'] for p in points)
    changed_points=sum(bool(p['changed_jacobian_entries']) for p in points)
    totals=[]
    for r, stages, wall in zip(reports,(stages_old,stages_new),(pwall_old,pwall_new)):
        if any(abs(stages[k]-r['stage_totals_seconds'][k])>1e-7 for k in stages):
            raise ValueError('M17_NATIVE_STAGE_TOTALS_DO_NOT_CLOSE')
        if wall>r['wall_seconds'] or r['wall_seconds']-wall>1:
            raise ValueError('M17_OUTSIDE_POINT_TIME_UNEXPECTED')
        totals.append(dict(total_wall_seconds=r['wall_seconds'],
                           sum_points_wall_seconds=wall,
                           named_stage_seconds=sum(stages.values()),
                           unattributed_inside_points_seconds=wall-sum(stages.values()),
                           outside_point_seconds=r['wall_seconds']-wall,
                           stage_totals_seconds=stages))
    return dict(schema='w1-m17-repeated-original-native-25point-v1',
        scope='TWO_HISTORICAL_BASELINE_ACTIONS_NOT_W1_OPTIMIZED_ABBA_NOT_NEWTON',
        historical_run_id=39121571756,attempt_1_job_id=117658066974,
        attempt_2_job_id=118689837052,
        original_artifact_id=12134772056,rerun_artifact_id=12275408088,
        artifact_sha256=dict(EXPECTED),
        original_source_input_and_all_three_binaries_equal=True,
        exact_geometry_provenance_and_ten_moments_equal_25_of_25=True,
        jacobian_bitwise_unequal_points=changed_points,
        jacobian_bitwise_unequal_entries_across_2500=diff_count,
        jacobian_max_abs_diff=max(p['max_abs_jacobian_difference'] for p in points),
        jacobian_max_scaled_diff=max(p['max_scaled_jacobian_difference'] for p in points),
        original_failed_feature_hash_points=list(range(17,25)),
        first=totals[0],second=totals[1],
        baseline_speed_ratio_first_over_second=totals[0]['total_wall_seconds']/totals[1]['total_wall_seconds'],
        matched_original_original_not_w1_speedup=True,
        can_certify_W1_candidate=False,full_newton_speedup=None,
        w0_w2_admission=False,paper_speed_qualified=False,
        points=points)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--attempt-1',required=True,type=Path)
    p.add_argument('--attempt-2',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    out=Path(args.output)
    if out.exists():raise FileExistsError('M17_REFUSES_OVERWRITE')
    try:
        result=compare(args.attempt_1,args.attempt_2)
    except BaseException as error:
        out.parent.mkdir(parents=True,exist_ok=True)
        fail=out.with_suffix('.failure.json')
        if not fail.exists():fail.write_text(json.dumps(dict(status='FAILED_CLOSED',error=str(error)),indent=2)+'\n')
        raise
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('W1_M17_REPEAT_BASELINE_PASSED scientific=25/25 J_drift_entries=',
          result['jacobian_bitwise_unequal_entries_across_2500'],
          'native_optimized_ABBA=false',flush=True)

if __name__=='__main__':main()

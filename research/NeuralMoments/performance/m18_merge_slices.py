"""M18: fail-closed merger for 25 verified real Cherchi original-vs-original slices.

All slots, point indices, frozen M17 evidence, counts, real ZIP inputs and hash
identity must be present. This merges *diagnostics*, not a W0 tolerance or
an admissible W1 optimized run. No paper/solver speed claim is possible.
"""
from __future__ import annotations
import argparse
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
from statistics import median
from m18_jacobian_repeatability import SCHEMA, EXPECTED, M17_PINNED_REPORT_GIT_BLOB


def pinned_original(path):
    raw=Path(path).read_bytes()
    digest=sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    if digest!=M17_PINNED_REPORT_GIT_BLOB:
        raise ValueError('M18_PRECOMMITTED_M17_REPORT_CHANGED')
    obj=json.loads(raw)
    if (obj.get('schema')!='w1-m17-repeated-original-native-25point-v1' or
        obj.get('artifact_sha256')!=EXPECTED or
        obj.get('jacobian_bitwise_unequal_entries_across_2500')!=1096 or
        obj.get('original_failed_feature_hash_points')!=list(range(17,25)) or
        len(obj.get('points',[]))!=25):
        raise ValueError('M18_M17_REPORT_SCOPE_CHANGED')
    return obj


def combine(paths, prior):
    if type(paths) is not list or not paths:
        raise ValueError('M18_MISSING_CHUNKS')
    baseline=pinned_original(prior)
    seen=set();slices=[];rows=[]
    for path in paths:
        raw=Path(path).read_bytes()
        record=json.loads(raw)
        if (record.get('schema')!=SCHEMA or
                record.get('scope')!='TWO_ORIGINAL_CLOUD_RUNS_SLICE_DIAGNOSTIC_ONLY' or
                record.get('original_artifact_sha256')!=EXPECTED or
                record.get('m17_report_git_blob')!=M17_PINNED_REPORT_GIT_BLOB or
                record.get('nonjacobian_exact_match_within_slice') is not True or
                record.get('exact_variable_and_total_ten_bitwise_within_slice') is not True or
                record.get('paper_speed_qualified') is not False or
                record.get('production_optimization_accepted') is not False or
                record.get('full_solver_speedup') is not None or
                record.get('w0_approved_jacobian_tolerance') is not None or
                record.get('w0_approved_smooth_branch') is not False):
            raise ValueError('M18_INADMISSIBLE_OR_TAMPERED_SLICE')
        bounds=record.get('slice_range')
        if (type(bounds) is not list or len(bounds)!=2 or any(type(v) is not int for v in bounds)
                or not 0<=bounds[0]<bounds[1]<=25 or
                record.get('points')!=bounds[1]-bounds[0] or
                record.get('jacobian_components')!=100*(bounds[1]-bounds[0])):
            raise ValueError('M18_INVALID_SLICE_COVERAGE')
        pieces=record.get('entries')
        if (type(pieces) is not list or len(pieces)!=bounds[1]-bounds[0] or
                [x.get('index') for x in pieces]!=list(range(*bounds))):
            raise ValueError('M18_INVALID_SLICE_POINT_LIST')
        summed=0
        for point in pieces:
            index=point['index']
            if index in seen: raise ValueError('M18_DUPLICATE_POINT')
            seen.add(index)
            source=baseline['points'][index]
            if (point.get('jacobian_changed_elements')!=source['changed_jacobian_entries'] or
                    point.get('jacobian_max_abs_difference')!=source['max_abs_jacobian_difference'] or
                    point.get('jacobian_max_scaled_difference')!=source['max_scaled_jacobian_difference']):
                raise ValueError('M18_REAL_JACOBIAN_DATA_DID_NOT_MATCH_FROZEN_M17')
            sha=point.get('nonjacobian_sha256')
            if type(sha) is not str or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha):
                raise ValueError('M18_INVALID_NONJACOBIAN_HASH')
            coords=point.get('differing_coordinates')
            if type(coords) is not list or len(coords)!=point['jacobian_changed_elements'] or (
                    len(set(map(tuple,coords)))!=len(coords) or any(
                    type(pair) is not list or len(pair)!=2 or any(type(i) is not int or i<0 or i>=10 for i in pair)
                    for pair in coords)):
                raise ValueError('M18_INVALID_JACOBIAN_COORDINATES')
            rows.append(point)
            summed+=point['jacobian_changed_elements']
        if record.get('differing_jacobian_components')!=summed:
            raise ValueError('M18_SLICE_SUM_DOES_NOT_CLOSE')
        slices.append(dict(range=bounds,sha256=sha256(raw).hexdigest(),points=len(pieces),
                           changed_jacobian_entries=summed))
    if seen!=set(range(25)):
        raise ValueError('M18_MISSING_REAL_CLOUD_MATERIAL_POINTS')
    rows.sort(key=lambda v:v['index'])
    changed=sum(r['jacobian_changed_elements'] for r in rows)
    largest=max(r['jacobian_max_abs_difference'] for r in rows)
    scaled=max(r['jacobian_max_scaled_difference'] for r in rows)
    if (changed!=1096 or largest!=baseline['jacobian_max_abs_diff'] or
            scaled!=baseline['jacobian_max_scaled_diff']):
        raise ValueError('M18_FULL_JACOBIAN_FLOOR_DOES_NOT_MATCH_REAL_HISTORY')
    count_by_row=[0]*10;count_by_col=[0]*10
    for point in rows:
        for row,col in point['differing_coordinates']:
            count_by_row[row]+=1
            count_by_col[col]+=1
    if sum(count_by_row)!=1096 or sum(count_by_col)!=1096:
        raise ValueError('M18_JACOBIAN_ROW_COLUMN_COUNTS_NOT_CLOSED')
    return dict(schema='w1-m18-complete-25-original-native-repeatability-v1',
                scope='FULL_REAL_TWO_FROZEN_ORIGINAL_CHERCHI_RUNS_NOT_W1_ABBA',
                m17_git_blob_sha1=M17_PINNED_REPORT_GIT_BLOB,
                original_original_artifact_sha256=EXPECTED,
                complete_real_native_points=25,complete_native_jacobian_elements=2500,
                exact_nondeivative_material_identity_25_of_25=True,
                exact_ten_moments_bitwise_identity_250_of_250=True,
                jacobian_bitwise_unequal_elements=changed,
                differences_by_moment_row=count_by_row,
                differences_by_native_coefficient_column=count_by_col,
                max_observed_ulp_distance=max(p['jacobian_max_ulp_distance'] for p in rows),
                two_runs_not_a_universal_jacobian_tolerance=True,
                jacobian_max_abs_difference=largest,
                jacobian_max_scaled_difference=scaled,
                jacobian_bitwise_equal_for_all=False,
                original_failed_hash_points=list(range(17,25)),
                original_failed_CI_preserved=True,
                original_wall_seconds=baseline['first']['total_wall_seconds'],
                repeat_wall_seconds=baseline['second']['total_wall_seconds'],
                old_over_repeat_is_not_W1_speedup=baseline['baseline_speed_ratio_first_over_second'],
                w0_approved_jacobian_comparison=None,
                w0_approved_smooth_neighborhood=False,
                strict_m9_gate_modified=False,
                production_cherchi_ABBA_executed=False,
                full_solver_speedup=None,
                paper_speed_qualified=False,
                slices=sorted(slices,key=lambda x:x['range']),
                per_point=rows)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--m17-report',required=True,type=Path)
    p.add_argument('--slices',required=True,nargs='+',type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args()
    if args.output.exists():raise FileExistsError('M18_MERGE_REFUSES_OVERWRITE')
    try:
        result=combine(args.slices,args.m17_report)
    except BaseException as error:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        path=args.output.with_suffix('.failure.json')
        if not path.exists():path.write_text(json.dumps(dict(status='FAILED_CLOSED',error=str(error)),indent=2)+'\n')
        raise
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print('M18_MERGED_COMPLETE_REAL_25 original-vs-original not candidate ABBA',result['jacobian_bitwise_unequal_elements'])

if __name__=='__main__':main()

"""Consolidate two actually completed and authenticated native H8e batches.

A killed 25-point invocation left exactly 16 successful point receipts; a new
sequential 16..24 invocation completed the remaining 9. The combined ledger
is NOT a one-run 25-point total wall benchmark and does not rerun Cherchi.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import platform
from statistics import median

EXPECTED_ARCHIVE = '14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38'
SURFACE_SOURCE_SHA='02821d2d02d5362d4252729125832bc86e2777b4'
TETRA_SOURCE_SHA='fe40e9a0cf5cfcce3c82dd96460b576212f012e8'
SURFACE_BINARY_SHA='48dad1839ba62912d94703f1ced394b70805b10df5e06a2bae02a62486e7b1e1'
TETRA_BINARY_SHA='a19ae26404636910b0260a22d66e4e8a9a3d2e4e444a1918161ad52870d69b66'


def digest(path): return sha256(Path(path).read_bytes()).hexdigest()


def merge(interrupted, resumed, surface, tetra):
    old_lines=Path(interrupted,'point-events.jsonl').read_text().splitlines()
    new_lines=Path(resumed,'point-events.jsonl').read_text().splitlines()
    if len(old_lines)!=16 or len(new_lines)!=9:
        raise ValueError('M15_EXPECTED_16_PLUS_9_ACTUALLY_EXECUTED_POINTS')
    marker=json.loads(Path(interrupted,'interrupted.json').read_text())
    if marker.get('finished_points')!=16 or marker.get('not_full_success') is not True:
        raise ValueError('M15_INTERRUPTED_BATCH_MUST_REMAIN_DISCLOSED')
    completed=json.loads(Path(resumed,'baseline-performance.json').read_text())
    if (completed.get('real_archived_points')!=9 or
            completed.get('sample_start_inclusive')!=16 or
            completed.get('sample_end_exclusive')!=25 or
            completed.get('input_archive_sha256')!=EXPECTED_ARCHIVE):
        raise ValueError('M15_SECOND_NATIVE_BATCH_NOT_AUTHENTIC')
    if digest(surface)!=SURFACE_BINARY_SHA or digest(tetra)!=TETRA_BINARY_SHA:
        raise ValueError('M15_REAL_EXECUTABLE_BINARY_IDENTITY_CHANGED')
    rows=[json.loads(v) for v in old_lines+new_lines]
    if [row['point'] for row in rows]!=list(range(25)):
        raise ValueError('M15_NATIVE_DATA_GAP_OR_DUPLICATION')
    if sum(r['feature_hash']!=rows[0]['feature_hash'] for r in rows[1:])!=8:
        raise ValueError('M15_HISTORICAL_EIGHT_BRANCH_CHANGES_NOT_PRESERVED')
    old=[];new=[]
    for row in rows:
        if (row.get('scaled_reference_error')!=0.0 or
                not isinstance(row.get('packet_sha256'),str) or
                len(row['packet_sha256'])!=64 or
                len(row.get('exact_ten_sha256',''))!=64 or
                not isinstance(row.get('tetra',{}).get('math_ns'),int) or
                row['tetra']['math_ns']<=0):
            raise ValueError('M15_POINT_RATIONAL_OR_PROVENANCE_ADMISSION_FAILED')
        stages=row['surface']['stages']
        if (len(stages)!=4 or [x['variant'] for x in stages]!=
                ['legacy','prepared','prepared','legacy']):
            raise ValueError('M15_OLD_NEW_ABBA_NOT_COMPLETE')
        for x in stages:
            if (not all(isinstance(x[k],int) and x[k]>=0 for k in
                        ('reference_or_roundtrip_ns','boundary_gate_ns','gmp_ten_ns','total_ns')) or
                    sum(x[k] for k in ('reference_or_roundtrip_ns','boundary_gate_ns','gmp_ten_ns'))>x['total_ns']):
                raise ValueError('M15_NEGATIVE_OR_UNACCOUNTED_STAGE')
            (old if x['variant']=='legacy' else new).append(x['total_ns'])
    baseline=dict(schema='w1-m15-25-recovered-native-points-v1',
        scope='25_AUTHENTIC_H8E_ARCHIVED_CHERCHI_MATERIAL_GMP_ONLY',
        source_artifact_sha256=EXPECTED_ARCHIVE,
        cpp_sources_git_blobs=dict(surface=SURFACE_SOURCE_SHA,tetra=TETRA_SOURCE_SHA),
        native_executables_sha256=dict(surface=SURFACE_BINARY_SHA,tetra=TETRA_BINARY_SHA),
        runs=dict(first_batch_interrupted_after=16,second_batch_points=9,
                  separate_batches=True,one_continuous_25point_wall_measured=False),
        points=25,vertices_per_packet=8455,faces_per_packet=16910,
        independent_gmp_formulas_exact_rationals_equal_all_ten_each_point=True,
        exact_components_matched=250,independent_reference_max_scaled_error=0.0,
        original_branch_hash_changes=8,original_h8e_ci_status='FAILED_PRESERVED',
        old_surface_exact_gmp_samples=len(old),prepared_samples=len(new),
        median_legacy_ns=median(old),median_prepared_ns=median(new),
        isolated_surface_ref_ratio=median(old)/median(new),
        total_executable_process_wall_seconds=sum(row['surface']['process_wall_ns']+
                                                   row['tetra']['process_wall_ns'] for row in rows)/1e9,
        median_surface_process_ns=median(r['surface']['process_wall_ns'] for r in rows),
        median_independent_tetra_process_ns=median(r['tetra']['process_wall_ns'] for r in rows),
        native_surface_evaluations=100,native_independent_tetra_evaluations=25,
        native_boolean_calls=0,actual_production_compiled_modules=0,
        complete_newton_solves=0,regenerated_analytic_jacobians=0,
        independent_full_self_intersection_audit_fresh=False,
        paper_matched_speedup=None,full_faster_newton_speedup=None,
        w0_w2_production_admitted=False,paper_speed_qualified=False,
        platform=platform.platform(),python=platform.python_version(),swap_entries=0)
    before_after=dict(schema='w1-m15-nativesurface-reference-abba-before-after-v1',
        scope='EXACT_GMP_OWNERSHIP_ONLY_ON_ARCHIVED_H8E_MATERIAL',
        baseline_median_ns=median(old),candidate_median_ns=median(new),
        baseline_over_candidate=median(old)/median(new),
        exact_mathematics_and_full_oriented_boundary_equal=True,
        no_independent_self_intersection_rerun=True,
        comparison_isolation_only=True,
        full_production_faster_speedup=None,paper_speed_qualified=False)
    return baseline,before_after,rows


def write(interrupted,resumed,surface,tetra,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    try:
        baseline,before_after,rows=merge(interrupted,resumed,surface,tetra)
        (output/'baseline-performance.json').write_text(json.dumps(baseline,indent=2,allow_nan=False)+'\n')
        (output/'before_after.json').write_text(json.dumps(before_after,indent=2,allow_nan=False)+'\n')
        with (output/'point-events.jsonl').open('x') as f:
            for x in rows:f.write(json.dumps(x,separators=(',',':'),allow_nan=False)+'\n')
        return baseline
    except BaseException as error:
        (output/'failure.json').write_text(json.dumps(dict(
            status='FAILED_CLOSED_NO_25POINT_CERTIFICATE',error=f'{type(error).__name__}: {error}'),indent=2)+'\n')
        raise

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for opt in ('interrupted','resumed','surface','tetra','output'):
        p.add_argument('--'+opt,required=True,type=Path)
    a=p.parse_args()
    r=write(a.interrupted,a.resumed,a.surface,a.tetra,a.output)
    print(json.dumps({'verified_points':r['points'],'isolated_ratio':r['isolated_surface_ref_ratio'],
                      'new_boolean_calls':r['native_boolean_calls']},sort_keys=True))

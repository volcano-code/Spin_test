"""W1 M18: diagnose true same-source Cherchi Jacobian repeatability and ABBA.

This is intentionally NOT the W0 mathematical Jacobian approval or a new native
solver admission. Full non-Jacobian material remains an exact comparison;
Jacobian differences are measured rather than hidden behind a broad tolerance.
Never use these two baseline attempts as a universal acceptance threshold.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
from hashlib import sha1, sha256
import json
import math
from pathlib import Path
import statistics
import struct
from zipfile import ZipFile

from m17_repeated_native_baseline import (
    EXPECTED, PREFIX, compare_material, digest, unique_member,
    _load_material, binary64_equal,
)

SCHEMA = 'w1-m18-real-native-jacobian-repeatability-diagnostic-v1'
M17_PINNED_REPORT_GIT_BLOB = '077ac148eb35d2aebd14ea36c6bc1cd209156156'
ROWS = 10
COLS = 10
MAX_MATERIAL = 32_000_000
ABBA_ORDER = ('original', 'candidate', 'candidate', 'original')
NATIVE_FLAGS = ('boundary_valid','closed','edge_manifold','vertex_manifold',
                'consistently_oriented','component_orientations_valid',
                'self_intersection_completed','self_intersection_free')
AUDITS = ('audit:same_call_material','audit:native_exact_rational_boundary',
          'audit:independent_fraction_ten','audit:exact_material_serialization')


def _ordered_bits(value):
    """Monotonic encoding of a finite IEEE binary64, for descriptive ULP gaps."""
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('M18_NONFINITE_JACOBIAN')
    b=struct.unpack('>Q',struct.pack('>d',float(value)))[0]
    return (~b & ((1<<64)-1)) if (b & (1<<63)) else (b | (1<<63))


def _vector_bits(values):
    if type(values) is not list or len(values)!=10 or any(
            type(x) not in (int,float) or not math.isfinite(x) for x in values):
        raise ValueError('M18_INVALID_TEN_VECTOR')
    return b''.join(struct.pack('>d',x) for x in values)


def jacobian_difference(first,second):
    if (type(first) is not list or type(second) is not list or
        len(first)!=10 or len(second)!=10 or
        any(type(row) is not list or len(row)!=10 or
            any(type(x) not in (int,float) or not math.isfinite(x) for x in row)
            for mat in (first,second) for row in mat)):
        raise ValueError('M18_INVALID_FULL_FINITE_JACOBIAN')
    changes=[];top_abs=0.;top_scaled=0.;max_ulp=0
    row_counts=[0]*10;col_counts=[0]*10
    for i in range(10):
        for j in range(10):
            a,b=first[i][j],second[i][j]
            abs_error=abs(a-b)
            scaled=abs_error/max(1.,abs(a),abs(b))
            ulp=abs(_ordered_bits(a)-_ordered_bits(b))
            top_abs=max(top_abs,abs_error)
            top_scaled=max(top_scaled,scaled)
            max_ulp=max(max_ulp,ulp)
            if struct.pack('>d',a)!=struct.pack('>d',b):
                changes.append(dict(row=i,column=j,abs_difference=abs_error,
                                    scaled_difference=scaled,ulp_distance=ulp))
                row_counts[i]+=1;col_counts[j]+=1
    return dict(changed_entries=len(changes),max_abs_difference=top_abs,
                max_scaled_difference=top_scaled,max_ulp_distance=max_ulp,
                changed_by_output_row=row_counts,changed_by_input_column=col_counts,
                differences=changes)


def canonical_nonjac_bytes(material):
    if type(material) is not dict or 'moment_jacobian' not in material:
        raise ValueError('M18_MISSING_MATERIAL_JACOBIAN')
    # This is a deterministic semantic receipt, NOT the original compressed ZIP hash.
    return json.dumps({k:v for k,v in material.items() if k!='moment_jacobian'},
                      sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def diagnostic_original_rerun(old,new,m17_report,*,start=0,end=25):
    """Use immutable M17 full proof, recheck 50 saved packets & Jacobian.

    M17 separately verified every geometry/provenance/moment field. Pin its
    Git blob *before* reading it, then independently confirm the ZIP hashes,
    the per-point packet hashes and every non-Jacobian semantic fingerprint.
    This avoids rerunning M17's expensive audit twice in the same milestone.
    """
    if (type(start) is not int or type(end) is not int or
            not 0<=start<end<=25):
        raise ValueError('M18_INVALID_SLICE_RANGE')
    old,new=Path(old),Path(new)
    report=Path(m17_report).read_bytes()
    git_blob=sha1(b'blob '+str(len(report)).encode()+b'\0'+report).hexdigest()
    if git_blob!=M17_PINNED_REPORT_GIT_BLOB:
        raise ValueError('M18_M17_IMMUTABLE_EVIDENCE_BLOB_CHANGED')
    baseline=json.loads(report)
    if (baseline.get('schema')!='w1-m17-repeated-original-native-25point-v1' or
        baseline.get('artifact_sha256')!=EXPECTED or
        baseline.get('jacobian_bitwise_unequal_entries_across_2500')!=1096 or
        baseline.get('original_failed_feature_hash_points')!=list(range(17,25)) or
        baseline.get('exact_geometry_provenance_and_ten_moments_equal_25_of_25') is not True or
        baseline.get('full_newton_speedup') is not None or
        baseline.get('can_certify_W1_candidate') is not False or
        len(baseline.get('points',[]))!=25):
        raise ValueError('M18_PREVIOUS_REAL_REPEATABILITY_REPORT_INVALID')
    for key,p in (('attempt_1',old),('attempt_2',new)):
        if digest(p.read_bytes())!=EXPECTED[key]:
            raise ValueError('M18_REAL_ACTIONS_ARCHIVE_HASH_DRIFT:'+key)
    entries=[];all_ulp=[];rows=[0]*10;cols=[0]*10
    with ZipFile(old) as za, ZipFile(new) as zb:
        for i in range(start,end):
            name=PREFIX+f'point-{i:03d}-material.json.gz'
            materials=[]
            for z in (za,zb):
                raw=unique_member(z,name,5_000_000)
                side='old' if z is za else 'new'
                if digest(raw)!=baseline['points'][i]['saved_material_gzip_sha256_'+side]:
                    raise ValueError('M18_M17_POINT_ARCHIVE_SHA_DRIFT')
                unpacked=gzip.decompress(raw)
                if len(unpacked)>MAX_MATERIAL:
                    raise ValueError('M18_DECOMPRESSED_ARCHIVE_OVERSIZED')
                materials.append(_load_material(unpacked))
            check=compare_material(*materials)
            diag=jacobian_difference(*(x['moment_jacobian'] for x in materials))
            if (diag['changed_entries']!=check['changed_jacobian_entries'] or
                    diag['changed_entries']!=baseline['points'][i]['changed_jacobian_entries'] or
                    diag['max_abs_difference']!=check['max_abs_jacobian_difference'] or
                    diag['max_abs_difference']!=baseline['points'][i]['max_abs_jacobian_difference']):
                raise ValueError('M18_INDEPENDENT_JACOBIAN_DIAGNOSTICS_DISAGREE')
            hashes=[digest(canonical_nonjac_bytes(x)) for x in materials]
            if hashes[0]!=hashes[1]:
                raise ValueError('M18_NONJACOBIAN_MATERIAL_FINGERPRINT_DRIFT')
            for k,n in enumerate(diag['changed_by_output_row']):rows[k]+=n
            for k,n in enumerate(diag['changed_by_input_column']):cols[k]+=n
            all_ulp.extend(x['ulp_distance'] for x in diag['differences'])
            entries.append(dict(index=i,nonjacobian_sha256=hashes[0],
                jacobian_changed_elements=diag['changed_entries'],
                jacobian_max_abs_difference=diag['max_abs_difference'],
                jacobian_max_scaled_difference=diag['max_scaled_difference'],
                jacobian_max_ulp_distance=diag['max_ulp_distance'],
                differing_coordinates=[[e['row'],e['column']] for e in diag['differences']]))
    total=sum(x['jacobian_changed_elements'] for x in entries)
    if len(entries)!=end-start or any(
            row['jacobian_changed_elements']!=baseline['points'][row['index']]['changed_jacobian_entries']
            for row in entries):
        raise ValueError('M18_ORIGINAL_REPLAY_COUNTS_CHANGED')
    if start==0 and end==25 and total!=1096:
        raise ValueError('M18_REAL_FULL25_JACOBIAN_COUNTS_DRIFT')
    result=dict(schema=SCHEMA,
        scope='TWO_ORIGINAL_CLOUD_RUNS_SLICE_DIAGNOSTIC_ONLY',
        original_artifact_sha256=EXPECTED,
        historical_two_orig_runs_failed=True,
        preserved_hash_drift=list(range(17,25)),
        nonjacobian_exact_match_within_slice=True,
        exact_variable_and_total_ten_bitwise_within_slice=True,
        slice_range=[start,end],m17_report_git_blob=M17_PINNED_REPORT_GIT_BLOB,
        points=end-start,jacobian_components=(end-start)*100,
        differing_jacobian_components=total,
        per_row_changed_entries=rows,
        per_column_changed_entries=cols,
        maximum_absolute_drift=max((v['jacobian_max_abs_difference'] for v in entries),default=0.),
        maximum_scaled_drift=max((v['jacobian_max_scaled_difference'] for v in entries),default=0.),
        max_ulp_distance=max(all_ulp,default=0),
        median_ulp_distance_among_changed=statistics.median(all_ulp),
        ulp_near_zero_is_not_a_contract_tolerance=True,
        original_run_wall_seconds=baseline['first']['total_wall_seconds'],
        repeat_run_wall_seconds=baseline['second']['total_wall_seconds'],
        original_over_repeat_wall_ratio=baseline['baseline_speed_ratio_first_over_second'],
        w0_approved_jacobian_tolerance=None,
        w0_approved_smooth_branch=False,
        w1_strict_abba_gate_modified=False,
        production_optimization_accepted=False,
        full_solver_speedup=None,paper_speed_qualified=False,
        entries=entries)
    return result


def shadow_abba(rows,material_paths):
    """Classify four genuine candidate snapshots WITHOUT granting any admission.

    Caller must FIRST independently pin native runtime/modules, and check
    production side full exact boundary/independent Fraction audits. This
    observational check cannot establish provenance of a synthetic row by itself.
    """
    if type(rows) is not list or len(rows)!=4 or type(material_paths) is not list or len(material_paths)!=4:
        raise ValueError('M18_FOUR_PAIR_ENTRIES_REQUIRED')
    if tuple(row.get('mode') for row in rows)!=ABBA_ORDER:
        raise ValueError('M18_ABBA_ORDER_INVALID')
    reference=rows[0]
    must_same=('geometry_hash','topology_hash','source_identity','backend_identity',
               'q','vertices','faces','native_sha256','cherchi_sha256','gmp_sha256')
    field_moments=('ten',)
    observed=[];timestamps=[]
    previous=None
    for i,(row,filename) in enumerate(zip(rows,material_paths)):
        if not (row.get('same_call_passed') is True and
                row.get('exact_geometry_audit_passed') is True and
                row.get('independent_ten_max_scaled_error',1)>-1 and
                row.get('independent_ten_max_scaled_error',1)<=1e-10):
            raise ValueError('M18_NATIVE_AUDITS_OR_FRACTION_TEN_UNPROVEN')
        if (not isinstance(row.get('boundary_flags'),dict) or
                set(row['boundary_flags'])!=set(NATIVE_FLAGS) or
                any(row['boundary_flags'][n] is not True for n in NATIVE_FLAGS)):
            raise ValueError('M18_REAL_EXACT_BOUNDARY_FLAGS_MISSING')
        for ident in ('native_sha256','cherchi_sha256','gmp_sha256'):
            h=row.get(ident)
            if type(h) is not str or len(h)!=64 or any(c not in '0123456789abcdef' for c in h):
                raise ValueError('M18_MISSING_NATIVE_BINARY_IDENTITY')
        q=row.get('q')
        if (type(q) is not list or len(q)!=10 or any(
                type(v) not in (int,float) or not math.isfinite(v) for v in q) or
                abs(sum(x*x for x in q)-1)>1e-12 or
                row.get('vertices')!=8455 or row.get('faces')!=16910):
            raise ValueError('M18_FROZEN_NATIVE_QUADRIC_OR_MATERIAL_SIZE_INVALID')
        if any(row.get(n)!=reference.get(n) for n in must_same) or (
                not isinstance(row.get('backend_identity'),str) or
                not row['backend_identity'].startswith('cherchi-reference-')):
            raise ValueError('M18_DISCRETE_OR_NATIVE_SOURCE_IDENTITY_DRIFT')
        if _vector_bits(row.get('ten'))!=_vector_bits(reference.get('ten')):
            raise ValueError('M18_EXACT_TEN_VECTOR_DIFFERENCE')
        ledger=row.get('stage_ledger')
        if not isinstance(ledger,dict) or ledger.get('all_returned') is not True:
            raise ValueError('M18_STAGE_LEDGER_UNVERIFIED')
        elapsed=ledger.get('wall_ns');excl=ledger.get('exclusive_ns');rest=ledger.get('unattributed_ns')
        wall=row.get('complete_validation_ns')
        ev=row.get('eval_wall_ns')
        if type(ev) is not int or not 0<ev<=wall:
            raise ValueError('M18_EVALUATOR_TIMER_INVALID')
        if any(type(n) is not int or n<0 for n in (elapsed,excl,rest,wall)) or (
                elapsed==0 or elapsed!=wall or excl+rest!=elapsed):
            raise ValueError('M18_ABBA_TIMING_NOT_SAME_WINDOW')
        stage_rows=ledger.get('exclusive_stages')
        if type(stage_rows) is not list or not stage_rows or (
                sum(s.get('exclusive_ns',-1) for s in stage_rows)!=excl):
            raise ValueError('M18_STAGE_LEDGER_NOT_CLOSED')
        names=Counter(s.get('name') for s in stage_rows)
        if names['native:boolean']!=1 or any(names[a]!=1 for a in AUDITS) or any(
                s.get('status')!='PASS' for s in stage_rows):
            raise ValueError('M18_MANDATORY_EXACT_AUDITS_MISSING')
        src=Path(filename)
        if not src.is_file() or not 0<src.stat().st_size<=MAX_MATERIAL:
            raise ValueError('M18_SAVED_SNAPSHOT_NOT_FOUND')
        with gzip.open(src,'rb') as f:
            packet=f.read(MAX_MATERIAL+1)
        if len(packet)>MAX_MATERIAL:
            raise ValueError('M18_OVERSIZED_SAVED_SNAPSHOT')
        def _unique_object(pairs):
            value={}
            for key,item in pairs:
                if key in value: raise ValueError('M18_DUPLICATE_JSON_KEY')
                value[key]=item
            return value
        def _nonfinite(constant):
            raise ValueError('M18_NONFINITE_JSON_TOKEN:'+constant)
        mat=json.loads(packet, object_pairs_hook=_unique_object,
                       parse_constant=_nonfinite)
        # M9 'snap_sha' signs json.dumps(material, sort_keys=True,
        # allow_nan=False) UTF8 (default separators and ensure_ascii).
        canonical=json.dumps(mat,sort_keys=True,allow_nan=False).encode()
        if digest(canonical)!=row.get('material_sha256'):
            raise ValueError('M18_SAVED_MATERIAL_NOT_BOUND_TO_M9_RECORD')
        if not (mat.get('geometry_hash')==row['geometry_hash'] and
                mat.get('topology_hash')==row['topology_hash'] and
                mat.get('quadric_source_identity')==row['source_identity'] and
                _vector_bits(mat.get('variable_raw_moments'))==_vector_bits(row['ten'])):
            raise ValueError('M18_MATERIAL_ROW_SCIENCE_DRIFT')
        if not (type(row.get('jacobian')) is list and
                jacobian_difference(row['jacobian'],mat.get('moment_jacobian'))['changed_entries']==0):
            raise ValueError('M18_JACOBIAN_NOT_ACTUALLY_SAVED')
        if previous is None:
            previous=mat
            d=None
        else:
            # Compare exact *full* non-J fields, reject every geometry/normal,
            # q, density, source, provenance and moment difference.
            d=compare_material(previous,mat)
        observed.append(dict(mode=row['mode'],
                             full_snapshot_sha256=row['material_sha256'],
                             nonjacobian_sha256=digest(canonical_nonjac_bytes(mat)),
                             jacobian_drift_from_first=d and {k:v for k,v in d.items() if k!='changed_entries'}))
        timestamps.append(dict(mode=row['mode'],wall_ns=wall,eval_ns=row.get('eval_wall_ns')))
    old=statistics.median(x['wall_ns'] for x in timestamps if x['mode']=='original')
    new=statistics.median(x['wall_ns'] for x in timestamps if x['mode']=='candidate')
    return dict(schema='w1-m18-abba-shadow-diagnostic-v1',
                scope='INSPECT_AUTHENTIC_NATIVE_RECEIPTS_ONLY_NOT_W0_MATH_APPROVAL',
                nonjacobian_material_and_ten_exact_all_four=True,
                original_over_candidate_validation_wall_descriptive=old/new,
                material_sha_bitwise_all_four=len(set(r['material_sha256'] for r in rows))==1,
                jacobian_bitwise_all_four=all(r['jacobian_drift_from_first'] is None or
                    r['jacobian_drift_from_first']['jacobian_bitwise_equal'] for r in observed),
                per_run=observed,
                w0_approved_jacobian_tolerance=None,
                w0_approved_smooth_branch=False,
                eligible_for_w1_production_speed_claim=False,
                full_solver_speedup=None,
                paper_speed_qualified=False)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--attempt-1',required=True,type=Path)
    p.add_argument('--attempt-2',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--m17-report',required=True,type=Path)
    p.add_argument('--start',type=int,default=0)
    p.add_argument('--end',type=int,default=25)
    args=p.parse_args()
    if args.output.exists(): raise FileExistsError('M18_NO_OVERWRITE')
    try:
        receipt=diagnostic_original_rerun(args.attempt_1,args.attempt_2,args.m17_report,start=args.start,end=args.end)
    except BaseException as exc:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.with_suffix('.failure.json').write_text(
            json.dumps({'status':'FAILED_CLOSED','error':str(exc)},indent=2)+'\n')
        raise
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print('M18_REAL_TWO_BASELINES_DIAGNOSTIC_ONLY',
          receipt['differing_jacobian_components'],
          'bitwise_different_jacobian_entries',flush=True)

if __name__=='__main__':main()

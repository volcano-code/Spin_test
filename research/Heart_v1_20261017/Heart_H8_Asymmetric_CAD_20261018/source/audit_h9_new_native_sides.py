"""H9 independent, fail-closed verifier for four NEW pinned Cherchi side snapshots.

Historical H8f output and a *conditional* surrogate certificate alone can never
satisfy this input contract. Recompute provenance, exact rational tetrahedral
moments, oriented edge chains and native edge signs from all fresh snapshots.
Even if all finite observations agree, this code does NOT certify a continuous
smooth neighborhood, an accepted Newton step or a final Heart model.

The captured new material is still unauthenticated user-provided artifact data;
true runtime provenance requires the original native execution logs/CI too.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import gzip
import json
import math
from pathlib import Path
import sys
import traceback

from certify_h9_interior_edge_crossing import (
    SOURCE_IDS, DESIGN_IDS, archival_data, exact_line_witness,
    need, qvec, solve as offline_solve,
)
from probe_h9_crossing_sides_live import native_plan, BACKEND_PREFIX
from reintegrate_h9_true_moments import check_mass_snapshot
from h9_one_sided_derivative_audit import one_sided_diagnostics

EXACT_SAME = 'SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'
EXACT_CHANGED = 'CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE'


def sha(data):return sha256(data).hexdigest()


def check_equal_point(a,b):
    return type(a) in (int,float) and type(b) in (int,float) and math.isfinite(a) and math.isfinite(b) and a==b


def check_vec(actual, expected, n, reason):
    need(isinstance(actual,list) and isinstance(expected,list) and
         len(actual)==len(expected)==n and
         all(check_equal_point(a,b) for a,b in zip(actual,expected)),reason)


def validate_native_packet_provenance(material,historical_material,arithmetic_sha):
    """Recognize the exact Cherchi operation/provenance observed in H8f.

    A textual backend prefix is not a binary-identity or native execution
    signature. The new material must also agree with the recorded same-call
    arithmetic module hash; cross-build equality is reported separately.
    """
    need(str(material.get('boolean_backend_identity','')).startswith(BACKEND_PREFIX)
         and material.get('material_proof',{}).get('schema')=='cherchi-same-call-material-v1'
         and material.get('boolean_operation')==historical_material['boolean_operation']
         and material.get('derivative_defined') is True
         and material.get('derivative_identity')==historical_material['derivative_identity']
         and material.get('evaluation_map_identity')==historical_material['evaluation_map_identity']
         and material.get('rational_arithmetic_identity',{}).get('backend')=='NATIVE_GMP_SURFACE_V1'
         and material.get('rational_arithmetic_identity',{}).get('module_sha256')==arithmetic_sha,
         'UNPINNED_OR_CHANGED_CHERCHI_MATERIAL_PROVENANCE')
    need(material.get('quadric_source_faces')==historical_material['quadric_source_faces']
         and len(material.get('quadric_source_vertices',[]))==len(historical_material['quadric_source_vertices']),
         'NATIVE_SOURCE_TRIANGULATION_CHANGED_IN_PROBE_INTERVAL')
    return True



def validate_new_same_call_numerics(material, meta):
    """Validate actual stage-4 producer schema + independently re-integrate.

    This factors a previously untested success-path: `native_saved` was an
    undefined variable, so older fail-closed tests could not catch the bug.
    Historic material is accepted here ONLY as a unit-test fixture, not as a
    new native run; the enclosing audit still requires four fresh side files.
    """
    original = meta.get('independent_ten_mass_moments')
    production = material.get('variable_raw_moments')
    need(isinstance(original, list) and isinstance(production, list)
         and len(original)==len(production)==10
         and all(type(v) in (float,int) and math.isfinite(v)
                 for v in original+production),
         'NEW_NATIVE_MOMENTS_NOT_FINITE_TEN')
    # Cheap, strict fail-fast guards before expensive 16k-face Fraction
    # re-integration. Genuine material is still re-integrated below.
    saved_error = meta.get('independent_scaled_moment_error')
    need(type(saved_error) in (float,int) and math.isfinite(saved_error)
         and 0 <= saved_error <= 1e-10,
         'NEW_NATIVE_INDEPENDENT_MOMENT_ERROR_NOT_REPRODUCED')
    recorded_disagreement=max(abs(a-b)/max(1.,abs(b)) for a,b in zip(original,production))
    need(recorded_disagreement<=1e-10 and
         abs(saved_error-recorded_disagreement)<=1e-12,
         'NEW_NATIVE_SAVED_AND_PRODUCTION_TEN_MOMENT_MISMATCH')
    jac = material.get('moment_jacobian')
    j7 = meta.get('native_moment_jacobian_column7')
    need(isinstance(j7, list) and len(j7)==10
         and all(type(v) in (float,int) and math.isfinite(v) for v in j7),
         'NEW_NATIVE_JACOBIAN_COLUMN7_MISSING')
    need(isinstance(jac, list) and len(jac)==10 and
         all(isinstance(row,list) and len(row)==10 and
             all(type(v) in (float,int) and math.isfinite(v) for v in row)
             for row in jac), 'NEW_NATIVE_FULL_10X10_JACOBIAN_INVALID')
    need(all(abs(jac[k][7]-j7[k])<=1e-12 for k in range(10)),
         'NEW_NATIVE_JACOBIAN_COLUMN_NOT_FROM_SAME_MATERIAL')
    independent = check_mass_snapshot(material, original, production)
    need(abs(saved_error-independent['max_scaled_error_vs_archived_production'])<=1e-12,
         'NEW_NATIVE_INDEPENDENT_MOMENT_ERROR_NOT_REPRODUCED')
    return independent


def h7_observe(material,request):
    root=Path(__file__).resolve().parents[2]/'Cherchi_H7'/'source'
    sys.path.insert(0,str(root))
    try:
        from h7_planar_patch import observe_packet
    except ImportError as exc:
        raise RuntimeError('H7_EXACT_SEMANTIC_PROVENANCE_MODULE_MISSING') from exc
    proof=material['material_proof']
    packet={
        'backend':'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1',
        'exact_vertices':proof['exact_vertices'],
        'faces':material['variable_faces'],
        'construction_records':proof['construction_records'],
    }
    return observe_packet(packet,request['design_vertices'],request['design_faces'],
                          material['quadric_source_vertices'],material['quadric_source_faces'])


def audit(artifact,certificate_path,native_output):
    artifact=Path(artifact);native_output=Path(native_output)
    original,old_report,old_samples=archival_data(artifact)
    expected=offline_solve(artifact)
    supplied=json.loads(Path(certificate_path).read_text(encoding='utf8'))
    need(supplied==expected,'CROSSING_CERTIFICATE_NOT_REPRODUCED_FROM_FROZEN_ARTIFACT')
    plan=native_plan(expected)
    run_path=native_output/'report.json'
    need(run_path.is_file(),'NO_COMPLETED_NEW_REAL_CHERCHI_RUN_REPORT')
    run_bytes=run_path.read_bytes()
    runner=json.loads(run_bytes)
    need(runner.get('schema')=='heart-h9-crossing-sides-live-v1'
         and runner.get('status')=='FOUR_FRESH_REAL_SAMPLES_EVALUATED_NOT_SMOOTH_OR_NEWTON_CERTIFIED'
         and runner.get('new_real_native_calls')==4
         and runner.get('finished_indices')==[0,1,2,3]
         and runner.get('historical_run_id')==39123384402
         and runner.get('historical_run_conclusion')=='failure'
         and runner.get('source_archive_sha256')==expected['artifact_sha256']
         and runner.get('plan')==plan
         and runner.get('newton_admitted') is False
         and runner.get('actual_accepted_step') is False
         and runner.get('actual_smooth_neighborhood_certified') is False
         and runner.get('final_heart_obj_produced') is False,
         'NATIVE_REAL_RUN_COMPLETE_AND_DENIED_PROTOCOL_MISMATCH')
    binary_hashes=runner.get('binary_hashes',{})
    expected_bin={
       'core':old_report['actual_native_sha256'],
       'boolean':old_report['actual_cherchi_sha256'],
       'arithmetic':old_report['actual_arithmetic_sha256'],
    }
    need(set(binary_hashes)==set(expected_bin) and
         all(type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v)
             for v in binary_hashes.values()),
         'MISSING_ACTUAL_BINARY_SHA256_IDS')
    comparables={k:binary_hashes[k]==expected_bin[k] for k in expected_bin}
    need(runner.get('native_binary_identical_to_h8f')==comparables,
         'MISREPORTED_H8F_VS_NEW_NATIVE_BINARY_IDENTITY')
    # For different builds, only pointwise new native evidence can be claimed.
    # Same exact 64-byte SHA equality is not assumed across independent builds.
    frozen_q=old_report['target_q']
    data=original['request'];design=tuple(qvec(data['design_vertices'][j]) for j in DESIGN_IDS)
    stats=[];observations=[]
    for p in plan:
        i=p['index'];stem=f"side-{i:02d}-{p['side']}"
        meta_path=native_output/(stem+'.json')
        compressed_path=native_output/(stem+'.json.gz')
        need(meta_path.is_file() and compressed_path.is_file(),f'NEW_NATIVE_SIDE_SNAPSHOT_MISSING_{i}')
        meta=json.loads(meta_path.read_text(encoding='utf8'))
        raw=compressed_path.read_bytes()
        need(meta.get('material_sha256')==sha(raw),f'NEW_NATIVE_MATERIAL_SHA_DRIFT_{i}')
        material=json.loads(gzip.decompress(raw))
        validate_native_packet_provenance(material,old_samples[59][1],binary_hashes['arithmetic'])
        need(len(material['material_proof']['construction_records'])==len(material['material_proof']['exact_vertices'])
             and len(material['variable_faces'])==meta['face_count']
             and len(material['variable_rational_vertices'])==meta['vertex_count'],
             f'NEW_NATIVE_CONSTRUCTION_PROOF_INCOMPLETE_{i}')
        q=list(frozen_q);q[7]=p['c7']
        check_vec(meta.get('q'),q,10,f'NEW_NATIVE_RECORDED_Q_MISMATCH_{i}')
        check_vec(material['quadric_coefficients'],q,10,f'NEW_NATIVE_MATERIAL_Q_MISMATCH_{i}')
        for key in ('index','side','c7','expected_proxy_event_sign','distance_from_proxy_root'):
            need(meta.get(key)==p.get(key),f'NEW_NATIVE_PLAN_{key}_MISMATCH_{i}')
        need(meta.get('native_geometry_valid') is True
             and meta.get('newton_admitted',False) is False
             and meta.get('native_feature_branch_hash')==material['topology_hash']
             and meta.get('native_material_geometry_hash')==material['geometry_hash'],
             f'NEW_NATIVE_MATERIAL_AUDIT_OR_IDENTITY_MISMATCH_{i}')
        # Independently re-integrate the exact same-call material and verify the
        # producer's real numeric schema, including all 100 Jacobian entries.
        moment_audit=validate_new_same_call_numerics(material,meta)
        # The original H7 constructor identities must be recomputed from *new*
        # same-call records; do not trust statuses in side-XX.json.
        observation=h7_observe(material,data)
        observations.append(observation)
        source=tuple(qvec(material['quadric_source_vertices'][j]) for j in SOURCE_IDS)
        witness=exact_line_witness(*source,*design)
        need(0<witness['source_segment_parameter']<1
             and 0<witness['design_segment_parameter']<1,
             f'NEW_NATIVE_LINE_PROJECTION_NOT_INTERIOR_{i}')
        sign=(witness['determinant']>0)-(witness['determinant']<0)
        need(sign==p['expected_proxy_event_sign'] and sign==meta['native_event_sign']
             and meta['agrees_with_analytic_proxy_sign'] is True,
             f'NEW_NATIVE_EDGE_SIGN_OPPOSES_SURROGATE_{i}')
        need(abs(float(witness['source_segment_parameter'])-meta['native_source_param'])<=1e-12
             and abs(float(witness['design_segment_parameter'])-meta['native_design_param'])<=1e-12,
             f'NEW_NATIVE_EDGE_PARAMETERS_NOT_REPRODUCED_{i}')
        new_j7=meta['native_moment_jacobian_column7']
        # No continuous derivative truth from finite packets alone.
        stats.append({'index':i,'side':p['side'],'c7':p['c7'],
                      'new_same_call_material_sha256':meta['material_sha256'],
                      'recomputed_exact_moments':moment_audit['raw_ten_moments_from_independent_fraction'],
                      'fraction_vs_recorded_max_scaled_error':moment_audit['max_scaled_error_vs_archived_independent'],
                      'oriented_manifold_edges':moment_audit['edge_structure']['manifold_edges_checked'],
                      'source_edge_parameter':float(witness['source_segment_parameter']),
                      'design_edge_parameter':float(witness['design_segment_parameter']),
                      'crossing_sign':sign,
                      'native_recorded_jacobian_col7':new_j7,
                      'vertex_count':len(material['variable_rational_vertices']),
                      'face_count':len(material['variable_faces'])})
    root=Path(__file__).resolve().parents[2]/'Cherchi_H7'/'source'
    sys.path.insert(0,str(root))
    from h7_planar_patch import compare_observations
    original_left=h7_observe(old_samples[59][1],data)
    original_right=h7_observe(old_samples[60][1],data)
    classifications=[]
    for item,obs in zip(stats,observations):
        left=compare_observations(original_left,obs)
        right=compare_observations(original_right,obs)
        need(item['index'] in range(4), 'UNKNOWN_NATIVE_SIDE_INDEX')
        classifications.append({'index':item['index'],'side':item['side'],
                                 'relation_to_historical_59':left['status'],
                                 'relation_to_historical_60':right['status'],
                                 'same_historical_59_patch':left['status']==EXACT_SAME,
                                 'same_historical_60_patch':right['status']==EXACT_SAME})
    # The event can separate 59/60 finite construction features without ever
    # certifying a continuous q-neighborhood. Compare each *within-side* pair
    # and report independent secants against the same-call native Jacobians.
    inside_left=compare_observations(observations[0],observations[1])
    inside_right=compare_observations(observations[2],observations[3])
    one_sided=one_sided_diagnostics(stats,
        same_symbolic_left=inside_left['status']==EXACT_SAME,
        same_symbolic_right=inside_right['status']==EXACT_SAME)
    # Finite correspondence is only diagnostic, not a continuous stratum proof.
    expected_branch_split=(all(x['same_historical_59_patch'] and not x['same_historical_60_patch']
                               for x in classifications[:2])
                           and all(x['same_historical_60_patch'] and not x['same_historical_59_patch']
                               for x in classifications[2:]))
    return {'schema':'heart-h9-independent-new-side-material-audit-v1',
            'historical_ci_conclusion':'failure','historical_run_id':39123384402,
            'frozen_artifact_sha256':expected['artifact_sha256'],
            'independent_original_crossing_certificate_reproduced':True,
            'new_native_run_report_sha256':sha(run_bytes),
            'new_native_samples_reintegrated':len(stats),
            'original_H8f_binaries_identical_to_new_native':comparables,
            'same_binary_across_runs':all(comparables.values()),
            'every_new_side_reproduces_expected_oriented_edge_sign':True,
            'finite_symbolic_branch_split_at_new_four_samples':expected_branch_split,
            'cross_build_same_semantic_baseline_admitted':bool(expected_branch_split and all(comparables.values())),
            'one_sided_independent_moment_jacobian_diagnostics':one_sided,
            'sample_diagnostics':stats,
            'semantic_provenance_comparisons':classifications,
            'newton_admitted':False,
            'continuous_native_boolean_smooth_stratum_proven':False,
            'actual_newton_step_accepted':False,
            'final_heart_obj_produced':False,
            'decision':'DENY_NEWTON_MISSING_CONTINUOUS_STRATUM_AND_ACCEPTED_STEP',
            'cross_build_identity_reconciliation_needed':not all(comparables.values()),
            'sample_integrity_checked_but_runtime_origin_not_cryptographically_attested':True}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--artifact',required=True,type=Path)
    p.add_argument('--certificate',required=True,type=Path)
    p.add_argument('--native-dir',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args()
    path=a.output
    if path.exists():raise FileExistsError('NO_OVERWRITE_H9_AUDIT_PROVENANCE')
    path.parent.mkdir(parents=True,exist_ok=True)
    try:
        result=audit(a.artifact,a.certificate,a.native_dir)
        path.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n')
        print('H9_NEW_NATIVE_SIDES_REINTEGRATED_BUT_NEWTON_STILL_DENIED',len(result['sample_diagnostics']))
    except Exception as exc:
        failure={'schema':'heart-h9-independent-new-side-audit-failure-v1',
                 'status':'FAILED_CLOSED_NO_NEWTON',
                 'reason':f'{type(exc).__name__}: {exc}',
                 'historical_h8f_ci_conclusion':'failure',
                 'new_native_samples_reintegrated_and_qualified':0,
                 'newton_admitted':False}
        path.write_text(json.dumps(failure,indent=2,sort_keys=True,allow_nan=False)+'\n')
        print('H9_NEW_NATIVE_SIDES_NOT_CERTIFIED',failure['reason'])
        raise

if __name__=='__main__': main()

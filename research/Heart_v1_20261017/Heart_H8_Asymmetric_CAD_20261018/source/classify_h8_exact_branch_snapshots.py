"""Offline audit of H8e actual same-call Cherchi construction snapshots.

This reads archived *actual* materials, not historical hashes or a fake
geometry backend. All comparisons are finite-sample diagnostics; no patch
classification alone proves a smooth parameter neighborhood or Newton safety.
Run after the native 25-point workflow uploads all material-###.json.gz.
"""
from __future__ import annotations
from collections import Counter
from hashlib import sha256
import argparse
import gzip
import json
from pathlib import Path
import sys

H7=Path(__file__).resolve().parents[2]/'Cherchi_H7'/'source'
sys.path.insert(0,str(H7))
from h7_planar_patch import observe_packet,compare_observations,public_observation

def sha(path):return sha256(Path(path).read_bytes()).hexdigest()

def read_one(report_dir,idx,source_request):
    item=json.loads((Path(report_dir)/f'point-{idx:03d}.json').read_text())
    path=Path(report_dir)/f'point-{idx:03d}-material.json.gz'
    if not path.is_file() or sha(path)!=item.get('exact_same_call_material_archive_sha256'):
        raise ValueError('UNCERTIFIED_MATERIAL_ARCHIVE_MISSING_OR_SHA_MISMATCH')
    with gzip.open(path,'rt',encoding='utf8') as s:
        material=json.load(s)
    if (item['index']!=idx or material['topology_hash']!=item['feature_branch_hash']
         or material['geometry_hash']!=item['material_geometry_hash']
         or material['quadric_coefficients']!=item['coefficients']
         or material['boolean_backend_identity']!=item['native_boolean_backend']):
        raise ValueError('ARCHIVED_SAME_CALL_MATERIAL_IDENTITY_MISMATCH')
    if not material['boolean_backend_identity'].startswith(
        'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'):
        raise ValueError('UNPINNED_DYNAMIC_BOOLEAN')
    proof=material.get('material_proof',{})
    if proof.get('schema')!='cherchi-same-call-material-v1':
        raise ValueError('MISSING_SAME_CALL_EXACT_CONSTRUCTION_PROOF')
    packet=dict(backend='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1',
        exact_vertices=proof['exact_vertices'],faces=material['variable_faces'],
        construction_records=proof['construction_records'])
    if len(packet['exact_vertices'])!=item['vertex_count'] or len(packet['faces'])!=item['triangle_count']:
        raise ValueError('ARCHIVED_MATERIAL_SIZE_DRIFT')
    observation=None;error=None
    try:
        observation=observe_packet(packet,source_request['design_vertices'],
            source_request['design_faces'],material['quadric_source_vertices'],
            material['quadric_source_faces'])
    except (ValueError,KeyError,TypeError) as exc:
        error=f'{type(exc).__name__}: {exc}'
    return dict(index=idx,archive_sha256=sha(path),observation=observation,
        witness=public_observation(observation) if observation else None,error=error)

def assess(directory,request,output):
    directory=Path(directory);output=Path(output)
    if output.exists():raise FileExistsError('DO_NOT_OVERWRITE_EXACT_BRANCH_EVIDENCE')
    report=json.loads((directory/'report.json').read_text())
    request=Path(request);frozen=json.loads(request.read_text())
    if (report.get('schema')!='heart-h8e-real-cherchi-jacobian-pilot-v1'
        or report.get('input_request_sha256')!=sha(request)
        or frozen.get('schema')!='spin-heart-h8-faster-preparation-v1'
        or frozen.get('evidence',{}).get('scope')!='H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED'
        or report.get('qualified_branch_neighborhood') is not False
        or report.get('formal_newton_converged') is not False):
        raise ValueError('NOT_FROZEN_H8E_UNCERTIFIED_CHERCHI_EVIDENCE')
    n=report.get('completed_samples',0)
    if n not in (9,25,81) or n!=1+8*len(report['columns_requested']):
        raise ValueError('NOT_AN_COMPLETE_H8E_POINT_PROTOCOL')
    observations=[]
    for i in range(n):
        observations.append(read_one(directory,i,frozen['request']))
    baseline=observations[0]['observation']
    categories=Counter();comparisons=[]
    for entry in observations[1:]:
        if baseline is None or entry['observation'] is None:
            result=dict(status='UNRESOLVED_SOURCE_SUPPORT_OR_CONSTRUCTION',
                qualified_smooth_derivative=False,qualified_boolean_set_continuity=False)
        else:result=compare_observations(baseline,entry['observation'])
        categories[result['status']]+=1
        comparisons.append(dict(index=entry['index'],**result))
    summary=dict(schema='heart-h8e-exact-construction-finite-point-audit-v1',
        scope='NONAUTHOR_RECONSTRUCTED_H8_FINITE_SAMPLES_ONLY',
        source_report_sha256=sha(directory/'report.json'),
        request_sha256=sha(request),
        complete_material_snapshots_verified=n,
        numeric_checks_passed=report['all_numerical_checks_passed'],
        same_hashed_branch_observed=report['all_tested_stencils_same_feature_hash'],
        exact_plane_diagnostics_resolved_points=sum(e['observation'] is not None for e in observations),
        exact_plane_diagnostics_unresolved_points=sum(e['observation'] is None for e in observations),
        classifications=dict(categories),comparisons=comparisons,
        witnesses=[dict(index=e['index'],archive_sha256=e['archive_sha256'],
            witness=e['witness'],unresolved_error=e['error']) for e in observations],
        certified_smooth_neighborhood=False,
        certified_newton_direction=False,
        author_original_cad=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+'\n')
    print('H8E_EXACT_FINITE_PATCH_CLASSIFICATION',json.dumps({
        'samples':n,'resolved':summary['exact_plane_diagnostics_resolved_points'],
        'statuses':summary['classifications']},sort_keys=True))
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--request',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    assess(a.directory,a.request,a.output)

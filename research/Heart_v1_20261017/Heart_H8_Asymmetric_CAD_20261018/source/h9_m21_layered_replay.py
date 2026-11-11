"""W3 M21: six saved packets, exact constraint replay, optional SOURCE-ONLY motion.

ledger: use the uploaded M20 ledger; no raw geometry or native calls.
geometry: validate six raw packets and exactly reconstruct saved constraints.
source: same checks, replay six native source motions (NO Boolean), transport
        those binary64 velocities independently through rational constraints
        and differentiate tetrahedron moments. Does NOT authorize Newton.
"""
from __future__ import annotations
import argparse
from collections import Counter
from fractions import Fraction as F
import hashlib
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback
import zipfile

from h9_m20_precision_replay import read_json, file_hash, ten, b64_equal
from h9_m21_motion_math import (need, vec, frac, material_state, moment_tangent,
    motion_pair, compare_vectors, NAMES, ZERO)

# Export the already-frozen M21.6 core pin for the quarterpoint runner.
# This is a compatibility export, not native-runtime attestation.
BINARY_SHA='d66ce44c42f66a875298ae271dda76c12d5f3660bd3d13a1089d4fdd152063fd'

LEDGER_SHA='95bf2c6d91862bba488dd56118562a1fad826037966ed3f8f0bf382e5fba0703'
ARTIFACT_SHA='99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
REQUEST_SHA='1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
M18_SHA='68ee61282caac38d160a4226d9e44df694b7723094890fd62cc61ada434e12e2'
STEMS=('side-00-left-coarse','side-01-left-near','side-02-right-near',
       'side-03-right-coarse','m19-mid-00-left-mid','m19-mid-01-right-mid')
FLAGS=dict(new_boolean_calls_this_run=0,newton_admitted=False,
           continuous_neighborhood_certified=False,asymptotic_order_certified=False,
           final_heart_obj_produced=False,runtime_origin_cryptographically_attested=False)


def dump(path,data):
    with Path(path).open('x',encoding='utf8') as f:
        json.dump(data,f,indent=2,sort_keys=True,allow_nan=False,ensure_ascii=False)
        f.write('\n')


def bind_file(path, expected):
    path=Path(path)
    need(path.is_file() and not path.is_symlink(),'MISSING_OR_SYMLINK_FILE:'+str(path))
    need(file_hash(path)==expected,'INPUT_SHA_MISMATCH:'+path.name)
    return path


def load_ledger(path):
    bind_file(path,LEDGER_SHA)
    obj=read_json(path)
    need(obj.get('schema')=='heart-h9-m20-exact-difference-rounding-ledger-v1' and
         obj.get('status')=='SIX_SAVED_SURFACES_REINTEGRATED_DIAGNOSTIC_ONLY' and
         obj.get('saved_materials_reintegrated')==6 and obj.get('newton_admitted') is False and
         obj.get('stage18_audit_sha256')==M18_SHA,'M20_LEDGER_NOT_QUALIFIED_FOR_DIAGNOSTIC')
    need(tuple(x['stem'] for x in obj['packets'])==STEMS,'LEDGER_PACKET_ORDER_CHANGED')
    need([s['side'] for s in obj['two_sides']]==['left','right'],'LEDGER_SIDE_ORDER_CHANGED')
    return obj


def ledger_review(obj):
    rows=[]
    for side in obj['two_sides']:
        c=side['signed_cancellation_ledger']['Mzz']
        intervals=[side['full_interval']]+side['two_half_intervals']
        rows.append({'side':side['side'],
                     'exact_full_and_half_max_errors':[x['max_exact_surface_scaled_error'] for x in intervals],
                     'worst_half_over_full':side['exact_surface_worst_half_over_full'],
                     'mzz_half_residuals':c['half_signed_residuals'],
                     'mzz_midpoint_correction':c['jacobian_midpoint_curvature_correction'],
                     'mzz_opposite_signs':c['opposite_half_residual_signs']})
    return dict(schema='heart-h9-m21-ledger-triage-v1',status='M20_LEDGER_BOUND_RAW_MOTION_STILL_NEEDED',
                ledger_sha256=LEDGER_SHA,packet_manifest=[{k:p[k] for k in ('stem','material_sha256','metadata_sha256')}
                    for p in obj['packets']],two_sides=rows,
                raw_material_bytes_read=False,source_velocity_available_in_ledger=False,
                root_cause_determined=False,new_native_source_calls_this_run=0,**FLAGS)


def frozen_request(artifact):
    bind_file(artifact,ARTIFACT_SHA)
    with zipfile.ZipFile(artifact) as z:
        raw=z.read('artifacts/h8-request/prepared-request.json')
    need(hashlib.sha256(raw).hexdigest()==REQUEST_SHA,'FROZEN_REQUEST_SHA_MISMATCH')
    doc=json.loads(raw);request=doc['request']
    need(doc['schema']=='spin-heart-h8-faster-preparation-v1' and
         request['mode']=='SPINNING_TOP' and request['material_density']==1.,'UNEXPECTED_H9_REQUEST')
    return doc


def load_six(args, ledger):
    """Bind raw bytes to the uploaded M20 result, not just mutable filenames."""
    root=Path(args.m19_run);old=Path(args.stage17_native_dir)
    paths={}
    for rel,key in [('midpoint-plan.json','m19_plan_sha256'),
                    ('native-two-midpoints/launch_result.json','m19_original_launch_sha256'),
                    ('native-two-midpoints/independent-refinement.json','m19_refinement_sha256')]:
        p=bind_file(root/rel,ledger[key]);paths[str(p)]=ledger[key]
    plan=read_json(root/'midpoint-plan.json')
    need(plan.get('stage18_independent_audit_sha256')==M18_SHA,'M18_PLAN_BINDING_CHANGED')
    launch=read_json(root/'native-two-midpoints/launch_result.json')
    need(launch.get('worker_exit_code')==0 and launch.get('audit_exit_code')==0 and
         launch.get('new_qualified_midpoints')==2 and launch.get('newton_admitted') is False,
         'M19_NOT_FINITE_ACCEPTED')
    refinement=read_json(root/'native-two-midpoints/independent-refinement.json')
    mid=root/'native-two-midpoints/two-midpoint-native'
    for p,expected in [(old/'report.json',plan['stage17_real_producer_report_sha256']),
                       (mid/'report.json',refinement['new_native_run_report_sha256'])]:
        bind_file(p,expected);paths[str(p)]=expected
    proposals=plan['baseline_four_real_rows']+plan['predeclared_two_midpoints']
    binaries=plan['stage17_current_binary_sha256'];identity=plan['stage18_current_evaluation_map_identity']
    loaded=[]
    for i,ev in enumerate(ledger['packets']):
        stem=STEMS[i];folder=old if i<4 else mid
        raw=bind_file(folder/(stem+'.json.gz'),ev['material_sha256'])
        metapath=bind_file(folder/(stem+'.json'),ev['metadata_sha256'])
        paths[str(raw)]=ev['material_sha256'];paths[str(metapath)]=ev['metadata_sha256']
        meta=read_json(metapath);mat=read_json(raw,compressed=True);q=ten(proposals[i]['q'])
        need(meta.get('material_sha256')==ev['material_sha256'] and
             meta.get('native_geometry_valid') is True and meta.get('newton_admitted') is False,
             'PRIOR_PACKET_AUDIT_UNBOUND:'+stem)
        need(all(b64_equal(a,b) for a,b in zip(ten(meta.get('q')),q)) and
             all(b64_equal(a,b) for a,b in zip(ten(mat.get('quadric_coefficients')),q)),
             'PACKET_COEFFICIENT_MISMATCH:'+stem)
        need(mat.get('evaluation_map_identity')==identity and
             mat.get('boolean_backend_identity')=='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'+binaries['boolean'] and
             mat.get('rational_arithmetic_identity',{}).get('module_sha256')==binaries['arithmetic'],
             'PACKET_PROVENANCE_MISMATCH:'+stem)
        j=mat.get('moment_jacobian');need(type(j) is list and len(j)==10,'BAD_JACOBIAN')
        for row in j:ten(row)
        stored_col=meta.get('native_moment_jacobian_column7') if i<4 else meta.get('moment_jacobian_column7')
        need(all(b64_equal(a,b) for a,b in zip(ten(stored_col),[row[7] for row in j])),
             'SAME_CALL_JACOBIAN_COLUMN_MISMATCH')
        need(mat.get('derivative_defined') is True and
             mat.get('derivative_identity')=='cherchi-constructed-vertex-motion-v1','DERIVATIVE_IDENTITY_CHANGED')
        loaded.append((mat,meta,ev))
    q0=ten(loaded[0][0]['quadric_coefficients'])
    for mat,_,_ in loaded:
        need(all(b64_equal(q0[k],mat['quadric_coefficients'][k]) for k in range(10) if k!=7),
             'NOT_A_SINGLE_C7_EXPERIMENT')
    return loaded,plan,paths


def source_snapshot(native, np, settings, request, material):
    """Exact production source-call/affine order; never instantiate a Boolean evaluator."""
    axes=np.asarray(request['target_axes']);origin=np.asarray(request['target_origin'])
    design=np.asarray(request['design_vertices']);rotation=axes.T
    target=(design-origin)@rotation.T
    source=native.evaluate_spin_it_faster_source_motion(
        np.asarray(material['quadric_coefficients'],dtype=np.float64),target,settings)
    need(source['defined'] and source['side_selection_defined'],'SOURCE_REPLAY_UNDEFINED')
    physical=(np.asarray(source['vertices'])@axes.T+origin)*1.+np.zeros(3)
    saved=np.asarray(material['quadric_source_vertices'],dtype=np.float64)
    need(physical.shape==saved.shape and np.isfinite(physical).all(),'SOURCE_DIMENSION_OR_FINITE_ERROR')
    need(physical.tobytes()==saved.tobytes(),'SOURCE_REPLAY_NOT_BITWISE_SAVED_GEOMETRY')
    need(np.array_equal(np.asarray(source['faces']),np.asarray(material['quadric_source_faces'])),
         'SOURCE_REPLAY_FACE_IDENTITY_CHANGED')
    need(('intersection' if source['interior_is_positive'] else 'subtraction')==material['boolean_operation'],
         'SOURCE_SELECTOR_CHANGED')
    velocity=np.asarray(source['vertex_velocity']).reshape(len(saved),3,10)
    physical_velocity=np.einsum('vkd,jk->vjd',velocity,axes)*1.
    need(np.isfinite(physical_velocity).all(),'NONFINITE_REPLAYED_SOURCE_VELOCITY')
    discrete={k:(source[k].tolist() if hasattr(source[k],'tolist') else source[k])
              for k in ('surface_type','cap_face_count','source_normal_edges')}
    return physical_velocity[:,:,7].tolist(),discrete


def source_pair(a,b,va,vb):
    need(a['source_faces']==b['source_faces'] and len(a['source'])==len(b['source']),
         'SOURCE_DISCRETE_SIGNATURE_CHANGED')
    h=F(b['c7'])-F(a['c7']);maximum=F(-1);worst=None
    for i,(pa,pb,da,db) in enumerate(zip(a['source'],b['source'],va,vb)):
        for axis in range(3):
            r=(pb[axis]-pa[axis])/h-(frac(da[axis])+frac(db[axis]))/2
            if abs(r)>maximum:maximum=abs(r);worst=[i,axis,float(r)]
    return {'max_source_secant_vs_average_velocity':float(maximum),'worst_vertex_axis_residual':worst,
            'correspondence_scope':'PINNED_SOURCE_SLOTS_AND_IDENTICAL_DISCRETE_SIGNATURE_NOT_INTERVAL_PROOF'}


def run_geometry(args,ledger,output):
    doc=frozen_request(args.artifact);request=doc['request']
    packets,plan,input_hashes=load_six(args,ledger)
    source_mode=args.phase in ('source','source-child')
    audit={'schema':'heart-h9-m21-layered-motion-diagnostic-v1','status':'INCOMPLETE',
           'phase':args.phase,'ledger_sha256':LEDGER_SHA,'packet_results':[],
           'new_native_source_calls_this_run':0,'root_cause_determined':False,**FLAGS}
    native=np=settings=None;contract=None;native_path=None
    if source_mode:
        import resource
        repo=Path(args.repo).resolve()
        from prepare_h9_pinned_native import check_runtime,source_contract
        check=check_runtime(repo)
        need(check['ready'],'SOURCE_HOST_PREFLIGHT_BLOCKED:'+repr(check['blocked_reasons']))
        contract=source_contract(repo)
        resource.setrlimit(resource.RLIMIT_AS,(24*1024**3,24*1024**3))
        sys.path.insert(0,str(repo/'build/h9-w3-core/python'))
        sys.path.insert(0,str(repo/'python'))
        import numpy as np
        import _make_it_stand as native
        from make_it_stand import spin
        native_path=Path(native.__file__).resolve()
        need(native_path.parent==(repo/'build/h9-w3-core/python').resolve(),'WRONG_NATIVE_MODULE_LOCATION')
        bind_file(native_path,plan['stage17_current_binary_sha256']['core'])
        config=spin.SpinEvaluatorConfig(**doc['evaluator_settings'])
        settings=native.SpinTriangulationSettings()
        for name in ('icosphere_subdivisions','maximum_icosphere_subdivisions','maximum_radius_doublings',
                     'retain_fixed_normal_provenance','truncation_radius','paper_projective_hyperboloid','algebraic_finite_map'):
            setattr(settings,name,getattr(config,name))
        audit['source_contract']=contract
        audit['native_core_sha256']=file_hash(native_path)
        audit['python_spin_sha256']=file_hash(spin.__file__)
        audit['loaded_libstdcpp_paths']=sorted({line.split()[-1] for line in Path('/proc/self/maps').read_text().splitlines()
                                               if 'libstdc++.so.6' in line})
    states=[];velocities=[];discrete=[]
    try:
        for i,(mat,meta,ev) in enumerate(packets):
            print('M21_REPLAY_PACKET',ev['stem'],args.phase,flush=True)
            v=None;signature=None
            if source_mode:
                audit['new_native_source_calls_this_run']+=1
                v,signature=source_snapshot(native,np,settings,request,mat)
            state=material_state(mat,request,v);states.append(state);velocities.append(v);discrete.append(signature)
            row={'stem':ev['stem'],'material_sha256':ev['material_sha256'],
                 'exact_constraint_positions_verified':len(state['positions']),
                 'construction_counts':state['kinds'],'source_vertex_count':len(state['source']),
                 'saved_source_velocity_field_present':('vertex_velocity' in mat),
                 'source_motion_replayed':source_mode,'source_geometry_bitwise_matched':True if source_mode else None,
                 'boolean_calls':0,'continuous_neighborhood_certified':False,'newton_admitted':False}
            if source_mode:
                independent,active=moment_tangent(state,request['material_density'])
                ref=[row[7] for row in mat['moment_jacobian']]
                row['independent_chain_vs_saved_j7']=compare_vectors(independent,ref)
                row['active_tangent_faces']=active
                attachment=output/(ev['stem']+'.source-motion.json')
                dump(attachment,{'schema':'heart-h9-m21-source-only-motion-v1','material_sha256':ev['material_sha256'],
                     'native_core_sha256':audit['native_core_sha256'],'physical_source_velocity_column7':v,
                     'discrete_source_signature':signature,'boolean_calls':0,'newton_admitted':False})
                row['source_motion_attachment_sha256']=file_hash(attachment)
                row['tangent_exactness_scope']='EXACT_SAVED_CONSTRAINTS_AND_REPLAYED_BINARY64_SOURCE_TANGENTS'
            dump(output/(ev['stem']+'.diagnostic.json'),row)
            audit['packet_results'].append(row)
        pair_results=[]
        for side,seq in [('left',(0,4,1)),('right',(2,5,3))]:
            for label,(a,b) in zip(('full','first-half','second-half'),((seq[0],seq[2]),(seq[0],seq[1]),(seq[1],seq[2]))):
                pair=motion_pair(states[a],states[b]);pair.update(side=side,interval=label)
                if source_mode:
                    if discrete[a]==discrete[b]:
                        pair['source_motion_diagnostic']=source_pair(states[a],states[b],velocities[a],velocities[b])
                    else:pair['source_motion_diagnostic']={'status':'SOURCE_SIGNATURE_CHANGED_NO_SLOT_COMPARISON'}
                pair_results.append(pair)
        audit['six_intervals']=pair_results
        for path,expected in input_hashes.items():bind_file(path,expected)
        bind_file(args.precision_ledger,LEDGER_SHA)
        if source_mode:
            bind_file(native_path,plan['stage17_current_binary_sha256']['core'])
            need(source_contract(Path(args.repo).resolve())==contract,'SOURCE_CHANGED_DURING_REPLAY')
        audit.update(status='SOURCE_MOTION_AND_EXACT_CHAIN_REPLAYED_DIAGNOSTIC_ONLY' if source_mode else
                     'SIX_SAVED_CONSTRUCTIONS_REBUILT_SOURCE_MOTION_UNAVAILABLE',
                     raw_materials_read=6,input_files_unchanged=True,
                     next_gate='INTERPRET_LAYER_RESIDUALS_NOT_NEWTON' if source_mode else 'SOURCE_ONLY_REPLAY_REQUIRED')
        dump(output/'layered-report.json',audit)
        return audit
    except Exception:
        dump(output/'partial-layered-report.json',audit)
        raise


def source_supervisor(args, output):
    """Hard wall-time bound for the source-only C++ subprocess, including hangs."""
    command=[sys.executable,'-u',str(Path(__file__).resolve()),'--phase','source-child']
    for flag in ('precision_ledger','artifact','stage17_native_dir','m19_run','repo'):
        command += ['--'+flag.replace('_','-'),str(getattr(args,flag))]
    command += ['--output',str(output/'worker')]
    dump(output/'source-command.json',{'argv':command,'timeout_seconds':3480,**FLAGS})
    code=None
    with (output/'worker.stdout.txt').open('x') as stdout,(output/'worker.stderr.txt').open('x') as stderr:
        proc=subprocess.Popen(command,stdout=stdout,stderr=stderr,start_new_session=True)
        try:
            code=proc.wait(timeout=3480)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGTERM)
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait()
            code=124
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid,signal.SIGKILL);proc.wait()
    dump(output/'launch_result.json',{'schema':'heart-h9-m21-source-supervisor-v1',
        'worker_exit_code':code,'status':'SOURCE_ONLY_WORKER_EXITED' if code==0 else 'SOURCE_ONLY_WORKER_FAILED',**FLAGS})
    need(code==0,'SOURCE_ONLY_WORKER_FAILED:'+str(code))
    result=read_json(output/'worker/layered-report.json')
    need(result.get('new_native_source_calls_this_run')==6 and result.get('new_boolean_calls_this_run')==0 and
         result.get('newton_admitted') is False,'SOURCE_WORKER_RESULT_INCOMPLETE')
    result['worker_report_sha256']=file_hash(output/'worker/layered-report.json')
    dump(output/'layered-report.json',result)
    return result


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase',choices=('ledger','geometry','source','source-child'),required=True)
    ap.add_argument('--precision-ledger',required=True,type=Path)
    ap.add_argument('--artifact',type=Path)
    ap.add_argument('--stage17-native-dir',type=Path)
    ap.add_argument('--m19-run',type=Path)
    ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[4])
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args(argv)
    if args.phase!='ledger' and any(getattr(args,k) is None for k in ('artifact','stage17_native_dir','m19_run')):
        ap.error('geometry/source require --artifact --stage17-native-dir --m19-run')
    args.output.mkdir(parents=True,exist_ok=False)
    def timeout(signum,frame):raise TimeoutError('M21_3500_SECOND_LIMIT')
    previous=signal.signal(signal.SIGALRM,timeout);signal.alarm(3500)
    try:
        ledger=load_ledger(args.precision_ledger)
        if args.phase=='ledger':
            result=ledger_review(ledger);dump(args.output/'ledger-triage.json',result)
        elif args.phase=='source':result=source_supervisor(args,args.output)
        else:result=run_geometry(args,ledger,args.output)
        print('M21_STATUS',result['status'],flush=True)
        print('M21_NEW_BOOLEAN_CALLS',0,flush=True)
        print('M21_NEWTON_ADMITTED',False,flush=True)
        return 0
    except Exception as e:
        dump(args.output/'failure.json',dict(status='FAILED_CLOSED_DIAGNOSTIC_ONLY',
            reason=f'{type(e).__name__}: {e}',traceback=traceback.format_exc(),**FLAGS))
        traceback.print_exc();return 1
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,previous)


if __name__=='__main__':raise SystemExit(main())

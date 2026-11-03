"""W3 M19: two *new* Cherchi midpoint trials, separate from frozen H9 four sides.

--phase run: validate original archived H8f/M18 bytes, pinned W3 build + source,
             then launch a resource-limited isolated native worker and an
             independent new-material audit. No Newton is ever dispatched.
--phase worker: internal subprocess; not a shortcut around --phase run.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import gzip
import json
import math
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import traceback
import zipfile

from h9_stage19_multiscale import (SCHEMA, M19Rejected, need, file_hash,
    read_json, generate_plan, b64_same, vector, compare_refinement)

MAX_SECONDS=3600
MAX_AS_BYTES=24*1024**3
WORKER_SECONDS=3220
AUDIT_SECONDS=350


def _same_plan(plan_path, artifact, certificate, baseline_audit, old_native_dir):
    expected=generate_plan(artifact,certificate,baseline_audit,old_native_dir)
    supplied=read_json(plan_path)
    need(supplied==expected and supplied.get('schema')==SCHEMA,
         'M19_PLAN_OR_SOURCE_CHANGED_AFTER_ADMISSION')
    return supplied


def _gzip_packet(data):
    import io
    buf=io.BytesIO()
    with gzip.GzipFile(fileobj=buf,mode='wb',filename='',mtime=0,compresslevel=5) as out:
        out.write(data)
    return buf.getvalue()


def _exclusive_file(folder,name,content):
    """Same-FS, atomic link publication; no overwrite or untrusted symlink following."""
    import stat
    from h9_same_call_capture import _sync_directory
    folder=Path(folder)
    dest=folder/name
    need(not os.path.lexists(dest),'M19_DESTINATION_ALREADY_EXISTS:'+name)
    tmp=None
    try:
        with tempfile.NamedTemporaryFile(mode='wb',dir=folder,prefix='.m19-',suffix='.partial',delete=False) as f:
            tmp=Path(f.name)
            f.write(content);f.flush();os.fsync(f.fileno())
        os.link(tmp,dest)
        _sync_directory(folder)
    finally:
        if tmp is not None:tmp.unlink(missing_ok=True)
    return dest


def _save_unverified(folder,p,material,backend):
    """Preserve exact same-call response before any expensive scientific audit."""
    from h9_same_call_capture import same_binary64_coefficients
    need(same_binary64_coefficients(p['q'],material.get('quadric_coefficients')),
         'M19_PRODUCER_FULL_Q_MISMATCH')
    need(material.get('boolean_backend_identity')==backend and
         material.get('material_proof',{}).get('schema')=='cherchi-same-call-material-v1',
         'M19_PRODUCER_MATERIAL_BACKEND_OR_PROOF_CHANGED')
    text=json.dumps(material,sort_keys=True,separators=(',', ':'),ensure_ascii=False,allow_nan=False).encode()
    packed=_gzip_packet(text)
    stem=f"m19-mid-{p['index']:02d}-{p['side']}"
    raw=_exclusive_file(folder,stem+'.unverified.json.gz',packed)
    proof={'schema':'heart-h9-m19-pre-audit-real-material-checkpoint-v1',
           'index':p['index'],'side':p['side'],'q':p['q'],
           'archive_sha256':sha256(packed).hexdigest(),
           'material_json_sha256':sha256(text).hexdigest(),
           'newton_admitted':False,'qualified_continuous_neighborhood':False,
           'note':'PRESERVED_UNVERIFIED_NEVER_TRAINING_OR_NEWTON'}
    _exclusive_file(folder,stem+'.unverified.json',
                   (json.dumps(proof,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
    return proof,raw


def _promote(folder,p,proof,raw,meta):
    """Publish audited bytes, retaining raw evidence if final metadata fails."""
    from h9_same_call_capture import _sync_directory
    stem=f"m19-mid-{p['index']:02d}-{p['side']}"
    dest=Path(folder)/(stem+'.json.gz')
    need(not os.path.lexists(dest),'M19_FINAL_PACKET_ALREADY_EXISTS')
    os.link(raw,dest)
    _sync_directory(folder)
    need(file_hash(dest)==proof['archive_sha256'],'M19_GZIP_DRIFT_BEFORE_META')
    _exclusive_file(folder,stem+'.json',
                    (json.dumps(meta,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
    # Never discard the pre-audit archive even after a qualified finite packet.


def work(artifact,certificate,baseline_audit,old_native_dir,plan_file,output):
    """Called only in isolated subprocess by run(); always fail closed."""
    # Even when invoked directly, the worker may not bypass the W3 host contract.
    from prepare_h9_pinned_native import check_runtime, source_contract
    repo=Path(__file__).resolve().parents[4]
    machine=check_runtime(repo)
    need(machine['ready'],'M19_WORKER_REQUIRE_FROZEN_HIGH_MEMORY_NO_SWAP:'+repr(machine['blocked_reasons']))
    source_contract(repo)
    resource.setrlimit(resource.RLIMIT_AS,(MAX_AS_BYTES,MAX_AS_BYTES))
    start=time.monotonic();stage='INITIALIZE';output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    report={'schema':'heart-h9-m19-two-real-midpoint-probe-v1',
            'status':'INCOMPLETE_NO_NEWTON','finished_indices':[],
            'new_real_native_calls':0,'newton_admitted':False,
            'continuous_neighborhood_certified':False,'final_heart_obj_produced':False}
    try:
        stage='REVERIFY_M18_ORIGINAL_FROZEN_BASELINE'
        plan=_same_plan(plan_file,artifact,certificate,baseline_audit,old_native_dir)
        from probe_h9_crossing_sides_live import (load_native_or_reject,EXACT_AUDIT_REQUIRED,BACKEND_PREFIX)
        from certify_h9_interior_edge_crossing import (archival_data,exact_line_witness,qvec,SOURCE_IDS,DESIGN_IDS)
        stage='IMPORT_PINNED_CHERCHI_MODULES'
        (np,native,boolean,arithmetic,InProcessCherchiEvaluator,
         request_from_frozen,independent_ten_raw_moments,load_point,
         compare_observations,observe_packet)=load_native_or_reject()
        binary={name:sha256(Path(obj.__file__).read_bytes()).hexdigest()
                for name,obj in [('core',native),('boolean',boolean),('arithmetic',arithmetic)]}
        need(binary==plan['stage17_current_binary_sha256'],'M19_NATIVE_BINARY_SHA_DRIFT')
        with tempfile.TemporaryDirectory(prefix='h9-m19-frozen-request-') as d, zipfile.ZipFile(artifact) as z:
            from certify_h9_interior_edge_crossing import REQUEST_SHA,sha
            src=z.read('artifacts/h8-request/prepared-request.json')
            need(sha(src)==REQUEST_SHA,'M19_FROZEN_REQUEST_SHA_WRONG')
            req_path=Path(d)/'prepared-request.json';req_path.write_bytes(src)
            request,settings,_=request_from_frozen(req_path)
            old_request,old_report,_=archival_data(artifact)
            data=old_request['request']
            _,hist_left,left_obs=load_point(z,59,data)
            _,hist_right,right_obs=load_point(z,60,data)
            engine=InProcessCherchiEvaluator(request,settings,
                normalization={'origin':[0.,0.,0.],'L':1.},
                rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',
                fixed_boundary_reuse=False,integral_profile='EXACT_GMP_V1',
                branch_identity_policy='SOURCE_FEATURE_BRANCH_V2')
            need(engine.backend_identity==BACKEND_PREFIX+binary['boolean'],
                 'M19_BOOLEAN_BACKEND_HASH_DRIFT')
            base_q=np.asarray(old_report['target_q'],dtype=np.float64)
            need(base_q.shape==(10,) and np.isfinite(base_q).all(),'M19_BAD_FROZEN_COEFFICIENT_VECTOR')
            design=[qvec(data['design_vertices'][j]) for j in DESIGN_IDS]
            for p in plan['predeclared_two_midpoints']:
                i=p['index'];stage=f'REAL_CHERCHI_CALL_{i}'
                q=base_q.copy();q[7]=p['c7']
                need(all(b64_same(float(q[k]),p['q'][k]) for k in range(10)),
                     'M19_NATIVE_Q_NOT_EXACT_PREDECLARED_COEFFICIENT')
                value=engine(q);material=engine.material(q)
                engine.validate_same_call_material(material,q,request)
                stage=f'PRESERVE_SAME_CALL_UNVERIFIED_PACKET_{i}'
                proof,raw=_save_unverified(output,p,material,value['boolean_backend_identity'])
                need(material['evaluation_map_identity']==plan['stage18_current_evaluation_map_identity'],
                     'M19_EVALUATION_MAP_DIFFERS_FROM_VALIDATED_STAGE18')
                stage=f'EXACT_NATIVE_BOUNDARY_{i}'
                coords=material['variable_rational_vertices'];faces=np.asarray(material['variable_faces'],dtype=np.int32)
                facts=dict(native.audit_exact_rational_triangle_boundary(coords,faces,'AnyNonzero'))
                need(all(facts.get(k) is True for k in EXACT_AUDIT_REQUIRED)
                     and not facts.get('intersecting_pairs')
                     and not facts.get('degenerate_faces')
                     and not facts.get('intersection_error'),
                     'M19_INVALID_REAL_EXACT_NATIVE_BOUNDARY')
                stage=f'INDEPENDENT_REAL_TEN_MOMENTS_{i}'
                moments=independent_ten_raw_moments(coords,faces.tolist())
                independently=np.asarray([float(x) for x in moments],dtype=np.float64)
                recorded=np.asarray(value['variable_raw_moments'],dtype=np.float64)
                jac=np.asarray(value['moment_jacobian'],dtype=np.float64)
                need(independently.shape==(10,) and recorded.shape==(10,) and jac.shape==(10,10)
                     and np.isfinite(independently).all() and np.isfinite(recorded).all()
                     and np.isfinite(jac).all(),'M19_NATIVE_MOMENTS_OR_JAC_INVALID')
                scaled=float(np.max(np.abs(independently-recorded)/np.maximum(1.,np.abs(recorded))))
                need(scaled<=1e-10,'M19_INDEPENDENT_TEN_MOMENTS_DISAGREE')
                stage=f'REAL_NATIVE_FEATURE_BRANCH_{i}'
                proof_part=material['material_proof']
                packet={'backend':'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1',
                        'exact_vertices':proof_part['exact_vertices'],
                        'faces':material['variable_faces'],
                        'construction_records':proof_part['construction_records']}
                obs=observe_packet(packet,data['design_vertices'],data['design_faces'],
                                   material['quadric_source_vertices'],material['quadric_source_faces'])
                lh=compare_observations(left_obs,obs);rh=compare_observations(right_obs,obs)
                same='SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'
                need((lh['status']==same and rh['status']!=same) if i==0 else
                     (rh['status']==same and lh['status']!=same),
                     'M19_MIDPOINT_SYMBOLIC_BRANCH_DIFFERS_FROM_EXPECTED_SIDE')
                source=[qvec(material['quadric_source_vertices'][j]) for j in SOURCE_IDS]
                line=exact_line_witness(*source,*design)
                need(0<line['source_segment_parameter']<1
                     and 0<line['design_segment_parameter']<1,
                     'M19_NEW_NATIVE_EDGE_INTERSECTION_NOT_INTERIOR')
                sign=(line['determinant']>0)-(line['determinant']<0)
                need(sign==p['expected_proxy_event_sign'],'M19_NEW_NATIVE_EDGE_SIGN_DISAGREES')
                meta={'schema':'heart-h9-m19-midpoint-full-audit-producer-v1',
                      'index':i,'side':p['side'],'c7':p['c7'],'q':p['q'],
                      'material_sha256':proof['archive_sha256'],
                      'moment_jacobian_column7':jac[:,7].tolist(),
                      'independent_ten_raw_moments':independently.tolist(),
                      'independent_scaled_moment_error':scaled,
                      'native_event_sign':sign,
                      'feature_match_historical_59':lh['status'],
                      'feature_match_historical_60':rh['status'],
                      'evaluation_map_identity':material['evaluation_map_identity'],
                      'native_geometry_valid':True,
                      'newton_admitted':False,'continuous_neighborhood_certified':False}
                stage=f'PROMOTE_FINITE_NEW_NATIVE_MIDPOINT_{i}'
                _promote(output,p,proof,raw,meta)
                report['finished_indices'].append(i)
                report['new_real_native_calls']+=1
                print('H9_M19_REAL_CHERCHI_MIDPOINT',i,p['side'],sign,flush=True)
        report.update(status='TWO_FRESH_FINITE_NATIVE_MIDPOINTS_PRODUCED_PENDING_REAUDIT',
                      plan_sha256=file_hash(plan_file),binary_hashes=binary,
                      newton_admitted=False)
        _exclusive_file(output,'report.json',
                        (json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
        return 0
    except Exception as exc:
        report.update(status='FAILED_CLOSED_NO_NEWTON',stage=stage,
                      error=f'{type(exc).__name__}: {exc}',traceback=traceback.format_exc(),
                      newton_admitted=False)
        _exclusive_file(output,'failure.json',
                        (json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
        raise


def audit_new_midpoints(artifact,certificate,audit_file,old_native_dir,plan_file,new_native_dir):
    """Independently reconstruct two new exact ten moments & feature identities."""
    from audit_h9_new_native_sides import validate_native_packet_provenance,h7_observe
    from reintegrate_h9_true_moments import check_mass_snapshot
    from certify_h9_interior_edge_crossing import archival_data,exact_line_witness,qvec,SOURCE_IDS,DESIGN_IDS
    h7_root=Path(__file__).resolve().parents[2]/'Cherchi_H7'/'source'
    if str(h7_root) not in sys.path:sys.path.insert(0,str(h7_root))
    from h7_planar_patch import compare_observations

    plan=_same_plan(plan_file,artifact,certificate,audit_file,old_native_dir)
    folder=Path(new_native_dir); producer=read_json(folder/'report.json')
    need(producer.get('status')=='TWO_FRESH_FINITE_NATIVE_MIDPOINTS_PRODUCED_PENDING_REAUDIT'
         and producer.get('new_real_native_calls')==2
         and producer.get('finished_indices')==[0,1]
         and producer.get('plan_sha256')==file_hash(plan_file)
         and producer.get('binary_hashes')==plan['stage17_current_binary_sha256']
         and producer.get('newton_admitted') is False,
         'M19_PRODUCER_TWO_REAL_MIDPOINTS_INCOMPLETE')
    original,report,old=archival_data(artifact)
    design=[qvec(original['request']['design_vertices'][j]) for j in DESIGN_IDS]
    left_obs=h7_observe(old[59][1],original['request'])
    right_obs=h7_observe(old[60][1],original['request'])
    new=[]; audit_records=[]
    for p in plan['predeclared_two_midpoints']:
        stem=f"m19-mid-{p['index']:02d}-{p['side']}"
        meta=read_json(folder/(stem+'.json'))
        packed=folder/(stem+'.json.gz')
        need(packed.is_file() and file_hash(packed)==meta.get('material_sha256'),
             'M19_NEW_MATERIAL_SHA_MISMATCH:'+stem)
        with gzip.open(packed,'rb') as f:
            material=json.load(f)
        need(meta.get('schema')=='heart-h9-m19-midpoint-full-audit-producer-v1'
             and meta.get('index')==p['index'] and meta.get('side')==p['side']
             and b64_same(meta.get('c7'),p['c7'])
             and all(b64_same(x,y) for x,y in zip(vector(meta.get('q')),p['q']))
             and all(b64_same(x,y) for x,y in zip(vector(material.get('quadric_coefficients')),p['q']))
             and meta.get('native_geometry_valid') is True
             and meta.get('newton_admitted') is False,
             'M19_NEW_MIDPOINT_Q_OR_METADATA_UNBOUND:'+stem)
        benchmark=plan['baseline_four_real_rows'][0 if p['index']==0 else 2]
        old_material_path=Path(old_native_dir)/f"side-{benchmark['index']:02d}-{benchmark['side']}.json.gz"
        with gzip.open(old_material_path,'rb') as f:
            historical_current_material=json.load(f)
        validate_native_packet_provenance(material,historical_current_material,
                                          plan['stage17_current_binary_sha256']['arithmetic'],
                                          boolean_sha=plan['stage17_current_binary_sha256']['boolean'],
                                          expected_map_identity=plan['stage18_current_evaluation_map_identity'])
        need(material['evaluation_map_identity']==meta['evaluation_map_identity']==plan['stage18_current_evaluation_map_identity'],
             'M19_MIDPOINT_MAP_IDENTITY_DIFFERS')
        original_moments=vector(meta.get('independent_ten_raw_moments'))
        production=vector(material.get('variable_raw_moments'))
        moment_audit=check_mass_snapshot(material,original_moments,production)
        independently=vector(moment_audit['raw_ten_moments_from_independent_fraction'])
        need(all(abs(a-b)/max(1.,abs(b))<=1e-10 for a,b in zip(independently,original_moments)),
             'M19_INDEPENDENT_MIDPOINT_MOMENTS_MISMATCH')
        jac=material.get('moment_jacobian')
        need(type(jac) is list and len(jac)==10 and all(type(row) is list and len(row)==10
            and all(type(v) in (int,float) and math.isfinite(v) for v in row) for row in jac),
            'M19_NEW_MIDPOINT_JACOBIAN_INCOMPLETE')
        j7=vector(meta.get('moment_jacobian_column7'))
        need(all(b64_same(row[7],j7[k]) for k,row in enumerate(jac)),
             'M19_NEW_MIDPOINT_J7_NOT_SAME_CALL')
        obs=h7_observe(material,original['request'])
        left=compare_observations(left_obs,obs);right=compare_observations(right_obs,obs)
        stable='SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED'
        need((left['status']==stable and right['status']!=stable) if p['index']==0 else
             (right['status']==stable and left['status']!=stable),
             'M19_MIDPOINT_SYMBOLIC_IDENTITY_CHANGED')
        src=[qvec(material['quadric_source_vertices'][j]) for j in SOURCE_IDS]
        witness=exact_line_witness(*src,*design)
        sign=(witness['determinant']>0)-(witness['determinant']<0)
        need(sign==p['expected_proxy_event_sign']==meta['native_event_sign'],
             'M19_MIDPOINT_ORIENTED_EDGE_SIGN_CHANGED')
        new.append({'index':p['index'],'side':p['side'],'c7':p['c7'],
                    'moments':independently,'j7':j7})
        audit_records.append({'index':p['index'],'side':p['side'],
                              'sha256':meta['material_sha256'],
                              'independent_ten_moments_verified':True,
                              'native_boolean_identity_bound':True,
                              'exact_symbolic_side_validated':True,
                              'newton_admitted':False})
    diagnostic=compare_refinement(plan,new)
    diagnostic.update(new_real_midpoint_materials_independently_verified=2,
                      original_m18_audit_sha256=file_hash(audit_file),
                      new_native_run_report_sha256=file_hash(folder/'report.json'),
                      new_midpoint_packets=audit_records,
                      original_H8f_workflow_conclusion='failure',
                      runtime_origin_not_cryptographically_attested=True,
                      actual_newton_step_accepted=False,
                      final_heart_obj_produced=False)
    return diagnostic


def _worker_cap():
    resource.setrlimit(resource.RLIMIT_AS,(MAX_AS_BYTES,MAX_AS_BYTES))


def parent_run(arguments):
    from prepare_h9_pinned_native import (check_runtime,source_contract,
        native_module_smoke,verify_build_evidence,python_path_env)
    from h9_process_isolation import run_process_group
    output=Path(arguments.output)
    output.mkdir(parents=True,exist_ok=False)
    start=time.monotonic()
    status={'schema':'heart-h9-m19-local-launch-result-v1',
            'status':'BLOCKED_NO_NEW_NATIVE_SAMPLES','newton_admitted':False,
            'new_qualified_midpoints':0,'continuous_neighborhood_certified':False}
    try:
        repo=Path(arguments.repo).resolve()
        machine=check_runtime(repo)
        need(machine['ready'],'M19_NATIVE_HOST_PREFLIGHT_BLOCKED:'+repr(machine['blocked_reasons']))
        status['source_contract']=source_contract(repo)
        plan=_same_plan(arguments.plan,arguments.artifact,arguments.certificate,
                        arguments.stage18_audit,arguments.stage17_native_dir)
        hashes=native_module_smoke(repo)
        saved_hash={k:hashes[mod] for k,mod in [('core','_make_it_stand'),
            ('boolean','_cherchi_core_boolean'),('arithmetic','_cherchi_rational_moments')]}
        need(saved_hash==plan['stage17_current_binary_sha256'],'M19_NATIVE_BINARY_CHANGED_SINCE_M18')
        status['build_evidence_sha256']=verify_build_evidence(repo,arguments.build_evidence,hashes)
        env=python_path_env(repo)
        cmd=[sys.executable,__file__,'--phase','worker','--artifact',str(arguments.artifact),
             '--certificate',str(arguments.certificate),'--stage18-audit',str(arguments.stage18_audit),
             '--stage17-native-dir',str(arguments.stage17_native_dir),'--plan',str(arguments.plan),
             '--output',str(output/'two-midpoint-native')]
        with (output/'worker.stdout.txt').open('x') as stdout,(output/'worker.stderr.txt').open('x') as stderr:
            try:
                code=run_process_group(cmd,env=env,stdout=stdout,stderr=stderr,
                                       preexec_fn=_worker_cap,timeout=WORKER_SECONDS)
            except subprocess.TimeoutExpired:
                code=124
        status['worker_exit_code']=code
        need(code==0,'M19_REAL_MIDPOINT_WORKER_FAILED_OR_TIMED_OUT:'+str(code))
        remaining=int(MAX_SECONDS-(time.monotonic()-start)-15)
        need(remaining>0,'M19_NO_TIME_LEFT_FOR_INDEPENDENT_AUDIT')
        cmd=[sys.executable,__file__,'--phase','audit','--artifact',str(arguments.artifact),
             '--certificate',str(arguments.certificate),'--stage18-audit',str(arguments.stage18_audit),
             '--stage17-native-dir',str(arguments.stage17_native_dir),'--plan',str(arguments.plan),
             '--new-native-dir',str(output/'two-midpoint-native'),
             '--output',str(output/'independent-refinement.json')]
        with (output/'audit.stdout.txt').open('x') as stdout,(output/'audit.stderr.txt').open('x') as stderr:
            try:
                code=run_process_group(cmd,env=env,stdout=stdout,stderr=stderr,
                                       preexec_fn=_worker_cap,timeout=min(AUDIT_SECONDS,remaining))
            except subprocess.TimeoutExpired:
                code=124
        status['audit_exit_code']=code
        need(code==0,'M19_INDEPENDENT_TWO_MIDPOINT_AUDIT_FAILED:'+str(code))
        need(source_contract(repo)==status['source_contract'],
             'M19_SOURCE_CHANGED_DURING_NATIVE_TRIAL')
        status.update(status='TWO_NEW_NATIVE_MIDPOINTS_INDEPENDENTLY_VERIFIED_NO_NEWTON',
                      new_qualified_midpoints=2, newton_admitted=False)
        return 0
    except Exception as exc:
        status.update(status='FAILED_CLOSED_NO_NEWTON',error=f'{type(exc).__name__}: {exc}',
                      new_qualified_midpoints=0,newton_admitted=False)
        return 2 if 'HOST_PREFLIGHT' in str(exc) else 1
    finally:
        (output/'launch_result.json').write_text(json.dumps(status,indent=2,sort_keys=True,allow_nan=False)+'\n')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--phase',choices=('run','worker','audit'),required=True)
    p.add_argument('--repo',default=str(Path(__file__).resolve().parents[4]))
    p.add_argument('--artifact',required=True)
    p.add_argument('--certificate',required=True)
    p.add_argument('--stage18-audit',required=True)
    p.add_argument('--stage17-native-dir',required=True)
    p.add_argument('--plan',required=True)
    p.add_argument('--build-evidence')
    p.add_argument('--new-native-dir')
    p.add_argument('--output',required=True)
    a=p.parse_args(argv)
    if a.phase=='run':
        p.error('--build-evidence required for run') if not a.build_evidence else None
        return parent_run(a)
    if a.phase=='worker':
        return work(a.artifact,a.certificate,a.stage18_audit,a.stage17_native_dir,
                    a.plan,a.output)
    p.error('--new-native-dir required for audit') if not a.new_native_dir else None
    outcome=audit_new_midpoints(a.artifact,a.certificate,a.stage18_audit,
                                a.stage17_native_dir,a.plan,a.new_native_dir)
    with Path(a.output).open('x',encoding='utf8') as f:
        json.dump(outcome,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n')
    print('H9_M19_TWO_MIDPOINTS_REINTEGRATED_FINITE_ONLY_NO_NEWTON',2)
    return 0


if __name__=='__main__':raise SystemExit(main())

"""W3 Heart H9: bind four post-run materials to independently audited bytes.

Run only AFTER true native process succeeds. A self-consistent file set or
synthetic unit-test fixture does not cryptographically authenticate Cherchi.
Even a valid four-point finite sample NEVER admits Newton.
"""
from __future__ import annotations
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import zlib

H8F = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
H8F_SHA256 = H8F
NAMES = ('left-coarse','left-near','right-near','right-coarse')
MODS = {'core':'_make_it_stand','boolean':'_cherchi_core_boolean',
        'arithmetic':'_cherchi_rational_moments'}

class HandoffRejected(ValueError): pass

def require(ok,why):
    if not ok: raise HandoffRejected(why)

def sha(path):
    digest=sha256()
    with Path(path).open('rb') as src:
        for chunk in iter(lambda:src.read(1048576),b''):digest.update(chunk)
    return digest.hexdigest()

hash_file=sha

def read(path):
    path=Path(path)
    require(path.is_file() and 0<path.stat().st_size<8*1024**2,
            'MISSING_OR_OVERSIZED_EVIDENCE:'+path.name)
    try: return json.loads(path.read_text(encoding='utf8'))
    except (ValueError,UnicodeError) as exc:
        raise HandoffRejected('INVALID_JSON:'+path.name) from exc

def verified_gzip(path):
    path=Path(path)
    require(path.is_file() and 0<path.stat().st_size<32*1024**2,
            'MISSING_OR_OVERSIZED_REAL_NATIVE_MATERIAL:'+path.name)
    size=0
    try:
        with gzip.open(path,'rb') as src:
            while chunk:=src.read(1048576):
                size+=len(chunk)
                require(size<=512*1024**2,'UNBOUNDED_GZIP_EXPANSION')
    except (OSError,EOFError,zlib.error) as exc:
        raise HandoffRejected('CORRUPT_NATIVE_GZIP:'+path.name) from exc
    require(size>0,'EMPTY_GZIP:'+path.name)
    return sha(path)

def verify_handoff(folder,*,original_archive_sha256,module_sha256):
    """Independent structural crosslink. Never certifies runtime origin."""
    folder=Path(folder)
    require(original_archive_sha256==H8F,'HISTORICAL_H8F_SHA_CHANGED')
    require(isinstance(module_sha256,dict) and set(module_sha256)==set(MODS.values())
            and all(isinstance(h,str) and re.fullmatch('[a-f0-9]{64}',h)
                    for h in module_sha256.values()),'WRONG_BUILD_BINARY_MANIFEST')
    status=read(folder/'run_status.json')
    require(status.get('status')=='FOUR_NEW_REAL_NATIVE_POINTS_AND_INDEPENDENT_AUDIT_FINISHED_NO_NEWTON'
            and status.get('audit_exit_code')==0 and status.get('newton_admitted') is False,
            'SERIAL_SUCCESS_NOT_CONFIRMED')
    probe,independent=folder/'probe.stdout.txt',folder/'audit.stdout.txt'
    require(all(p.is_file() and 0<p.stat().st_size<16*1024**2 for p in (probe,independent)),
            'MISSING_NATIVE_EXECUTION_LOG')
    pattern=r'^H9_REAL_NATIVE_SIDE_PROBE\s+(\d+)\s+(\S+)\s+(-?\d+)\b'
    events=re.findall(pattern,probe.read_text(errors='replace'),re.M)
    require([(int(i),s,int(v)) for i,s,v in events]==
            [(i,s,1 if i<2 else -1) for i,s in enumerate(NAMES)]
            and re.search(r'^H9_NEW_NATIVE_SIDES_REINTEGRATED_BUT_NEWTON_STILL_DENIED\s+4\s*$',
                          independent.read_text(errors='replace'),re.M),
            'MISSING_REAL_FOUR_SIDE_EXECUTION_AND_INDEPENDENT_AUDIT_LOG_MARKERS')
    native=folder/'native';run_file=native/'report.json';audit_file=folder/'independent-audit.json'
    run=read(run_file);aud=read(audit_file)
    binaries={k:module_sha256[v] for k,v in MODS.items()}
    require(run.get('schema')=='heart-h9-crossing-sides-live-v1'
            and run.get('status')=='FOUR_FRESH_REAL_SAMPLES_EVALUATED_NOT_SMOOTH_OR_NEWTON_CERTIFIED'
            and run.get('new_real_native_calls')==4 and run.get('finished_indices')==[0,1,2,3]
            and run.get('historical_run_id')==39123384402
            and run.get('historical_run_conclusion')=='failure'
            and run.get('source_archive_sha256')==H8F
            and run.get('binary_hashes')==binaries
            and all(run.get(k) is False for k in ('newton_admitted','actual_accepted_step',
                          'actual_smooth_neighborhood_certified','final_heart_obj_produced')),
            'REAL_NATIVE_PRODUCER_REPORT_NOT_BOUND_TO_W3_BINARIES')
    plan=run.get('plan')
    require(isinstance(plan,list) and len(plan)==4 and
            [(v.get('index'),v.get('side')) for v in plan]==list(enumerate(NAMES))
            and all(type(v.get('c7')) is float and math.isfinite(v['c7']) for v in plan)
            and all(plan[i]['c7']<plan[i+1]['c7'] for i in range(3)),
            'NEW_NATIVE_PLAN_INVALID')
    require(aud.get('schema')=='heart-h9-independent-new-side-material-audit-v1'
            and aud.get('historical_ci_conclusion')=='failure'
            and aud.get('historical_run_id')==39123384402
            and aud.get('frozen_artifact_sha256')==H8F
            and aud.get('new_native_run_report_sha256')==sha(run_file)
            and aud.get('new_native_samples_reintegrated')==4
            and aud.get('every_new_side_reproduces_expected_oriented_edge_sign') is True
            and aud.get('sample_integrity_checked_but_runtime_origin_not_cryptographically_attested') is True
            and all(aud.get(k) is False for k in ('newton_admitted','actual_newton_step_accepted',
                    'continuous_native_boolean_smooth_stratum_proven','final_heart_obj_produced')),
            'INDEPENDENT_AUDIT_NOT_BOUND_TO_ORIGINAL_RUN_OR_REPORT')
    cross=run.get('native_binary_identical_to_h8f')
    require(isinstance(cross,dict) and set(cross)==set(MODS)
            and all(type(x) is bool for x in cross.values())
            and aud.get('original_H8f_binaries_identical_to_new_native')==cross
            and aud.get('same_binary_across_runs') is all(cross.values())
            and (all(cross.values()) or aud.get('cross_build_same_semantic_baseline_admitted') is False),
            'CROSS_BUILD_BASELINE_EQUIVALENCE_CLAIM_UNSUPPORTED')
    records=aud.get('sample_diagnostics')
    finite=aud.get('one_sided_independent_moment_jacobian_diagnostics',{})
    require(isinstance(records,list) and len(records)==4
            and [(x.get('index'),x.get('side')) for x in records]==list(enumerate(NAMES))
            and isinstance(finite,dict)
            and finite.get('schema')=='heart-h9-two-sided-finite-jacobian-diagnostics-v1'
            and [(x.get('side'),x.get('indices')) for x in finite.get('finite_same_side_pairs',[])]
                ==[('left',[0,1]),('right',[2,3])]
            and finite.get('newton_admitted') is False
            and finite.get('continuous_neighborhood_certified') is False,
            'FOUR_SIDES_OR_LEFT_RIGHT_JACOBIAN_AUDIT_MISSING')
    bound=[]
    for i,side in enumerate(NAMES):
        stem=f'side-{i:02d}-{side}';meta=read(native/(stem+'.json'))
        digest=verified_gzip(native/(stem+'.json.gz'))
        row=records[i];expected=plan[i]
        require(meta.get('index')==i and meta.get('side')==side
                and meta.get('c7')==expected['c7']
                and meta.get('native_event_sign')==expected.get('expected_proxy_event_sign')
                and meta.get('agrees_with_analytic_proxy_sign') is True
                and meta.get('native_geometry_valid') is True
                and meta.get('material_sha256')==digest
                and row.get('new_same_call_material_sha256')==digest
                and row.get('c7')==expected['c7']
                and row.get('crossing_sign')==meta['native_event_sign']
                and meta.get('vertex_count')==row.get('vertex_count')
                and meta.get('face_count')==row.get('face_count'),
                'SIDE_MATERIAL_SHA_EVENT_SIGN_OR_FRAME_NOT_BOUND:'+stem)
        bound.append({'index':i,'side':side,'material_sha256':digest})
    return {'schema':'heart-h9-stage8-outer-artifact-crosslink-v1',
        'completed_structurally_bound_side_count':4,
        'original_h8f_archive_sha256':H8F,'native_report_sha256':sha(run_file),
        'independent_audit_sha256':sha(audit_file),'materials':bound,
        'structurally_consistent_not_cryptographic_runtime_attestation':True,
        'continuous_neighborhood_proven':False,'accepted_Newton_step_observed':False,
        'newton_admitted':False,'final_heart_obj_produced':False}

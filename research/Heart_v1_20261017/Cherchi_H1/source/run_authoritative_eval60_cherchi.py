"""Strict Heart seed1/eval60 source-to-Cherchi replay on ORIGINAL frozen inputs.

Requires the original unmodified configuration.json and events.jsonl whose
SHA256 are recorded in the historical registration; NEVER substitutes V4.
A source exception is not a Cherchi Boolean failure. No Newton is performed.
"""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from cherchi_heart_guard import load_modules, assert_native_boundary, _as_vertices, _valid_faces, verify_material, publish, digest


def authenticate(registration, config, events):
    registration,config,events=map(Path,(registration,config,events))
    if not registration.is_file():raise FileNotFoundError('MISSING_EVAL60_REGISTRATION')
    reg=json.loads(registration.read_text())
    for role,p in [('configuration',config),('events',events)]:
        if not p.is_file():raise FileNotFoundError(f'MISSING_ORIGINAL_EVAL60_{role.upper()}')
        expected=reg.get(role+'_sha256')
        if not isinstance(expected,str) or len(expected)!=64 or digest(p)!=expected:
            raise ValueError(f'ORIGINAL_EVAL60_{role.upper()}_SHA256_MISMATCH')
    event=reg.get('event',{})
    if event.get('evaluation_index')!=60 or event.get('reason')!='evaluation_exception':
        raise ValueError('WRONG_EVAL60_REGISTRATION')
    config_data=json.loads(config.read_text())
    if not isinstance(config_data.get('request'),dict) or not isinstance(config_data.get('evaluator'),dict):
        raise ValueError('INVALID_ORIGINAL_EVAL60_CONFIG')
    return reg,config_data


def evaluate_authoritative(native,cherchi,reg,config):
    req=config['request'];e=config['evaluator'];cfg=native.SpinTriangulationSettings()
    for key in ('icosphere_subdivisions','maximum_icosphere_subdivisions',
                'maximum_radius_doublings','retain_fixed_normal_provenance',
                'truncation_radius','paper_projective_hyperboloid','algebraic_finite_map'):
        if key not in e:raise ValueError('MISSING_FORMAL_EVALUATOR_KEY:'+key)
        setattr(cfg,key,e[key])
    origin=np.asarray(req['target_origin']);axes=np.asarray(req['target_axes'])
    design=(_as_vertices(req['design_vertices'])-origin)@axes.T
    design_faces=_valid_faces(req['design_faces'],len(design))
    assert_native_boundary(native,design,design_faces,'DESIGN')
    source=native.evaluate_spin_it_faster_source_motion(
        np.asarray(reg['event']['quadric_coefficients'],dtype=np.float64),design,cfg)
    if not source.get('defined') or not source.get('side_selection_defined'):
        raise ValueError('AUTHENTIC_SOURCE_NOT_DEFINED')
    sv=_as_vertices(source['vertices']);sf=_valid_faces(source['faces'],len(sv))
    assert_native_boundary(native,sv,sf,'SOURCE')
    operation='intersection' if source['interior_is_positive'] else 'difference'
    packet=cherchi.boolean(design.tolist(),design_faces.tolist(),sv.tolist(),sf.tolist(),operation)
    report=verify_material(native,packet,operation)
    report.update(input_classification='ORIGINAL_REGISTERED_EVAL60',
                  source_faces=len(sf),design_faces=len(design_faces),
                  operation=operation,algorithm_boolean_fallback_count=0,
                  original_frozen_inputs_verified=True,
                  full_newton_converged=False)
    return packet,report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--registration',required=True,type=Path)
    p.add_argument('--configuration',required=True,type=Path)
    p.add_argument('--events',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--expected-native-sha256',default=None)
    p.add_argument('--expected-cherchi-sha256',default=None)
    args=p.parse_args()
    args.out.mkdir(parents=True,exist_ok=False)
    summary={'status':'AUTHORITATIVE_EVAL60_NOT_PERFORMED','optimization_invocations':0,
             'backend_fallback_count':0,'full_newton_converged':False}
    try:
        reg,config=authenticate(args.registration,args.configuration,args.events)
        native,cherchi=load_modules()
        for module,expected,label in [(native,args.expected_native_sha256,'native'),
                                       (cherchi,args.expected_cherchi_sha256,'cherchi')]:
            if expected is not None and digest(Path(module.__file__))!=expected:
                raise ValueError(label.upper()+'_MODULE_SHA256_MISMATCH')
        packet,report=evaluate_authoritative(native,cherchi,reg,config)
        result=publish(args.out/'material',packet,report)
        summary.update(status='EVAL60_CHERCHI_COMPLETE_WITH_OUTPUT_CONSTRAINTS',
                       original_frozen_inputs_verified=True,details=result)
    except (FileNotFoundError,ValueError,RuntimeError,ImportError,KeyError) as err:
        summary.update(status='AUTHORITATIVE_EVAL60_BLOCKED_OR_REJECTED',
                       error_type=type(err).__name__,error=str(err))
    (args.out/'report.json').write_text(json.dumps(summary,indent=2,allow_nan=False))
    print(json.dumps({k:summary.get(k) for k in ('status','error','original_frozen_inputs_verified')},allow_nan=False))
    return 0 if summary['status']=='EVAL60_CHERCHI_COMPLETE_WITH_OUTPUT_CONSTRAINTS' else 3

if __name__=='__main__':sys.exit(main())

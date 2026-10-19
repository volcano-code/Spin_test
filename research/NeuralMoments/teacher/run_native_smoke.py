"""One Cherchi request from a frozen JSON fixture; never starts an optimizer.

Run with timeout 60m and the project's compiled make_it_stand package.
Labels are pre-W0 and excluded from training even after successful evaluation.
"""
import argparse
import json
from pathlib import Path
import sys
import time

try:
    from .native_cherchi_teacher import canonical, load, vector
    from .cherchi_single_request import evaluate_one, sha256_file
except ImportError:
    from native_cherchi_teacher import canonical, load, vector
    from cherchi_single_request import evaluate_one, sha256_file


def parse_spec(path):
    spec=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(spec,dict) or spec.get('schema')!='w2-one-cherchi-request-v1':
        raise ValueError('INVALID_SINGLE_REQUEST_SCHEMA')
    if not isinstance(spec.get('request'),dict) or not isinstance(spec.get('evaluator_settings'),dict):
        raise ValueError('REQUEST_OR_SETTINGS_MISSING')
    spec['q']=vector(spec.get('q'))
    model=Path(spec.get('model_path',''))
    if not model.is_file():
        raise ValueError('FROZEN_MODEL_FILE_NOT_FOUND')
    if not isinstance(spec.get('geometry'),dict) or not isinstance(spec.get('frame'),dict):
        raise ValueError('GEOMETRY_OR_FRAME_MISSING')
    if spec.get('derivative_contract') is not None:
        raise ValueError('W0_DERIVATIVE_CONTRACT_UNAVAILABLE')
    return spec


def evaluate_from_spec(spec):
    """Lazy imports: preflight can be checked without compiled native modules."""
    import numpy as np
    from make_it_stand.spin import SpinItFasterRequest, SpinSolverConfig, SpinEvaluatorConfig
    from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
    request_data=dict(spec['request'])
    if isinstance(request_data.get('settings'),dict):
        request_data['settings']=SpinSolverConfig(**request_data['settings'])
    request=SpinItFasterRequest(**request_data)
    settings=SpinEvaluatorConfig(**spec['evaluator_settings'])
    # Fast fail before expensive Boolean evaluation. This native audit checks
    # the design shell, not the final Boolean set or a derivative neighborhood.
    from make_it_stand import spin
    native=spin._native_module()
    boundary=native.audit_exact_triangle_boundary(
        np.asarray(request.design_vertices,dtype=np.float64),
        np.asarray(request.design_faces,dtype=np.int32),'AnyNonzero')
    if not boundary['boundary_valid']:
        raise ValueError('OPEN_OR_ILLEGAL_DESIGN_BOUNDARY')
    evaluator=InProcessCherchiEvaluator(
        request,settings,normalization=spec.get('normalization'),
        design_vertices_physical=spec.get('design_vertices_physical'),
        rational_arithmetic_backend=spec.get('rational_arithmetic_backend','PYTHON_FRACTION_V1'))
    return evaluate_one(evaluator,spec['q'],model_path=spec['model_path'],
        native_module_path=evaluator.native.__file__,geometry=spec['geometry'],
        density=request.material_density,frame=spec['frame'],split='excluded',
        exclusion_reason='W0_MOMENT_CONTRACT_NOT_VERIFIED')


def run(spec_path,output_path):
    path=Path(output_path)
    if path.exists():
        raise FileExistsError('REFUSE_OVERWRITE_EXISTING_EVIDENCE')
    start=time.perf_counter()
    try:
        spec=parse_spec(spec_path)
        record=evaluate_from_spec(spec)
        # Create exclusively, including failed evaluations; never overwrite.
        with path.open('x',encoding='utf-8') as stream:
            stream.write(canonical(record)+'\n')
        body=record['payload']
        load(path,expected_q=spec['q'],
             expected_model_sha256=sha256_file(spec['model_path']),
             expected_native_module_sha256=record['identity']['native_module_sha256'])
        return {'status':'LABEL_RECORDED', 'label_path':str(path),
                'native_cherchi':body['exact_proof']['native_cherchi'],
                'topology_status':body['topology_status'],
                'derivative_status':body['derivative_status'],
                'training_admitted':False,
                'wall_seconds':time.perf_counter()-start,
                'failure_reason':body['failure_reason']}
    except Exception as error:
        # Before a valid module SHA exists this cannot be a teacher label.
        # Still record and count the attempted invocation as a preflight failure.
        failure={'schema':'w2-native-smoke-preflight-v1','status':'FAILED_PREFLIGHT',
                 'error':f'{type(error).__name__}: {error}',
                 'elapsed_seconds':time.perf_counter()-start,
                 'training_admitted':False}
        if not path.exists():
            with path.open('x',encoding='utf-8') as stream:
                stream.write(canonical(failure)+'\n')
        return failure


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args(argv)
    result=run(args.spec,args.output)
    print(canonical(result))
    return 0 if result.get('status')=='LABEL_RECORDED' and result.get('failure_reason') is None else 2


if __name__=='__main__':
    sys.exit(main())

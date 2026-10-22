"""W4 P20: frozen P19 input -> genuine native, unevaluated one-point factory.

Only the existing native owned-region checker authenticates M=F+D.  Cherchi
remains the geometric construction backend.  This module does not call the
evaluator, generate a surface, optimize, or grant W0/W2/physical admission.
The formal M6 launcher must apply its >=20 GiB and swap-zero checks *before*
importing or calling this factory.  A separate bounded preparation receipt
does not satisfy that formal launch requirement.
"""
from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import time


REQUEST_SHA256 = '74d9cfa64417dd2c82d196ab27094651976954742a4c692667a1b19b1032de62'
BASE = Path(__file__).resolve().parent
PIN_KEYS = frozenset(('native_sha256', 'bridge_sha256', 'adapter_sha256',
                      'c_sha256', 'problem_input_digest', 'context_sha256'))
ADMISSION = {
    'W0_owner_admitted': False,
    'W2_teacher_training_allowed': False,
    'derivative_neighborhood_certified': False,
    'Faster_optimization_executed': False,
    'physical_validation_passed': False,
    'MuJoCo_optimized_before_after_executed': False,
    'original_author_CAD': False,
    'formal_M6_executed': False,
    'formal_M6_passed': False,
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def canonical_digest(value):
    """Exact W0 native_teacher_replay.digest encoding (finite float c only)."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()


def _local_file(base, relative):
    base = Path(base)
    relative = Path(relative)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('P20_INPUT_PATH_ESCAPE')
    path = base / relative
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError('P20_INPUT_SYMLINK_REJECTED')
        if parent == base:
            break
    if not path.is_file() or not path.resolve().is_relative_to(base.resolve()):
        raise ValueError('P20_INPUT_NOT_LOCAL_REGULAR_FILE')
    return path


def load_request(base=BASE):
    """Hash the registered request and all six immutable P19 evidence inputs."""
    request_path = _local_file(base, 'P20_native_request.json')
    if sha256(request_path) != REQUEST_SHA256:
        raise ValueError('P20_REGISTERED_REQUEST_SHA256_MISMATCH')
    config = json.loads(request_path.read_text(encoding='utf-8'))
    refs = {'manifest': config['manifest'], 'canonical_report': config['canonical_report'],
            **config['material_inputs']}
    observed = {'P20_native_request.json': REQUEST_SHA256}
    for name, ref in refs.items():
        path = _local_file(base, ref['path'])
        actual = sha256(path)
        if actual != ref['sha256']:
            raise ValueError('P20_FROZEN_INPUT_SHA256_MISMATCH_' + name)
        observed[ref['path']] = actual
    return config, observed


def recheck_inputs(observed, base=BASE):
    for relative, expected in observed.items():
        if sha256(_local_file(base, relative)) != expected:
            raise ValueError('P20_INPUT_CHANGED_DURING_PREPARATION_' + relative)


def read_frozen_obj(path):
    """Preserve indexed binary64 input, including signed zero; never repair."""
    vertices, faces = [], []
    for raw in Path(path).read_text(encoding='ascii').splitlines():
        cells = raw.split('#', 1)[0].split()
        if not cells:
            continue
        if cells[0] == 'v':
            if len(cells) != 4:
                raise ValueError('P20_OBJ_VERTEX_ARITY')
            point = tuple(float(x) for x in cells[1:])
            if not all(math.isfinite(x) for x in point):
                raise ValueError('P20_OBJ_NONFINITE_VERTEX')
            vertices.append(point)
        elif cells[0] == 'f':
            if len(cells) != 4 or any(re.fullmatch(r'[1-9][0-9]*', x) is None for x in cells[1:]):
                raise ValueError('P20_OBJ_POSITIVE_INDEXED_TRIANGLES_REQUIRED')
            face = tuple(int(x) - 1 for x in cells[1:])
            if len(set(face)) != 3:
                raise ValueError('P20_OBJ_REPEATED_FACE_INDEX')
            faces.append(face)
        else:
            raise ValueError('P20_OBJ_UNREGISTERED_RECORD_' + cells[0])
    if not vertices or not faces or any(max(face) >= len(vertices) for face in faces):
        raise ValueError('P20_OBJ_EMPTY_OR_INDEX_OUT_OF_BOUNDS')
    return tuple(vertices), tuple(faces)


def verify_core_python(config):
    """Verify all 77 Python files of the frozen W4 native-facade source tree."""
    spec = importlib.util.find_spec('make_it_stand')
    if spec is None or spec.origin is None:
        raise RuntimeError('P20_FROZEN_CORE_PYTHON_UNAVAILABLE')
    package = Path(spec.origin).resolve().parent
    source_root = package.parent.parent
    actual = {}
    for relative, expected in config['runtime_python_git_blobs'].items():
        path = _local_file(source_root, relative)
        found = git_blob(path.read_bytes())
        if found != expected:
            raise ValueError('P20_CORE_SOURCE_BLOB_MISMATCH_' + relative)
        actual[relative] = found
    if (source_root / 'python/make_it_stand/__init__.py').resolve() != Path(spec.origin).resolve():
        raise ValueError('P20_CORE_PACKAGE_LOCATION_MISMATCH')
    return source_root, actual


def _stage(timings, observer, name, function):
    if observer:
        observer({'event': 'start', 'stage': name})
    started = time.monotonic()
    try:
        value = function()
    except BaseException as error:
        timings[name] = time.monotonic() - started
        if observer:
            observer({'event': 'failed', 'stage': name, 'seconds': timings[name],
                      'error_type': type(error).__name__, 'error': str(error)})
        raise
    timings[name] = time.monotonic() - started
    if observer:
        observer({'event': 'completed', 'stage': name, 'seconds': timings[name]})
    return value


def construct_problem(*, base=BASE, observer=None):
    config, observed = load_request(base)
    source_root, core_blobs = verify_core_python(config)
    import numpy as np
    from make_it_stand.verification.spin_problem import MeshSnapshot, SpinArtifactProblem

    timings, snapshots, raw_meshes = {}, {}, {}
    for name in ('M', 'F', 'D'):
        ref = config['material_inputs'][name]
        vertices, faces = read_frozen_obj(_local_file(base, ref['path']))
        if len(vertices) != ref['vertices'] or len(faces) != ref['faces']:
            raise ValueError('P20_FROZEN_INPUT_DIMENSION_MISMATCH_' + name)
        raw_meshes[name] = (vertices, faces)
        snapshots[name] = _stage(timings, observer, 'owned_region_' + name,
            lambda vertices=vertices, faces=faces: MeshSnapshot((vertices, faces)))
        # No winding repair, coordinate scaling, reindexing or welded copy is
        # allowed to replace the actual frozen P19 input.
        actual_v, actual_f = snapshots[name].arrays()
        expected_v = np.asarray(vertices, dtype='<f8')
        expected_f = np.asarray(faces, dtype='<i4')
        if actual_v.tobytes() != expected_v.tobytes() or actual_f.tobytes() != expected_f.tobytes():
            raise ValueError('P20_NATIVE_SNAPSHOT_CHANGED_INPUT_' + name)

    units = config['units']
    problem = _stage(timings, observer, 'owned_M_equals_F_plus_D', lambda: SpinArtifactProblem(
        original=snapshots['M'], fixed_regions=[('P19_FIXED_F', snapshots['F'], units['fixed_density'])],
        design_regions=[('P19_DESIGN_D', snapshots['D'], units['design_density'])],
        length_unit=units['length_unit'], mass_unit=units['mass_unit'],
        target=config['target'], minimum_outer_wall=config['minimum_outer_wall_reference']))
    if problem.identity['original_evidence_admission'] != 'BLOCKED_UNKNOWN':
        raise ValueError('P20_UNEXPECTED_ORIGINAL_EVIDENCE_ADMISSION')
    recheck_inputs(observed, base)
    verify_core_python(config)
    return dict(config=config, input_identity=observed, source_root=source_root,
                runtime_python_git_blobs=core_blobs, timings=timings,
                problem=problem, snapshots=snapshots, raw_meshes=raw_meshes)


def prepare_context(*, base=BASE, observer=None):
    bundle = construct_problem(base=base, observer=observer)
    from make_it_stand.spin import SpinEvaluatorConfig, SpinSolverConfig
    from make_it_stand.verification.faster_material import _prepare_faster_problem
    from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
    from p20_physical_contract import Frame, register_p20_dyadic_seed

    config, problem, timings = bundle['config'], bundle['problem'], bundle['timings']
    evaluator_settings = SpinEvaluatorConfig(**config['evaluator_settings'])
    solver_settings = SpinSolverConfig(**config['solver_settings'])
    prepared = _stage(timings, observer, 'prepare_native_request', lambda: _prepare_faster_problem(
        problem, evaluator_settings, solver_settings,
        input_validation_profile='CONSTRUCTOR_PROOF_REUSE_V1'))
    request = prepared.request
    frame = Frame.from_core(problem.normalization, request.target_origin, request.target_axes,
                            requested_tip=config['target']['origin'])
    seed = register_p20_dyadic_seed(frame)
    coefficients = tuple(float(x) for x in seed['native_c'])
    if len(coefficients) != 10 or not all(math.isfinite(x) for x in coefficients):
        raise ValueError('P20_INVALID_REGISTERED_NATIVE_C')
    if abs(math.sqrt(math.fsum(x*x for x in coefficients)) - 1.0) > 1e-12:
        raise ValueError('P20_NATIVE_C_NOT_UNIT_NORM')
    evaluator = _stage(timings, observer, 'initialize_fresh_cherchi_evaluator', lambda:
        InProcessCherchiEvaluator(request, evaluator_settings, normalization=problem.normalization,
            design_vertices_physical=problem.design_regions[0].mesh.arrays()[0],
            **config['evaluator_policy']))
    if evaluator.call_counts != {'source': 0, 'boolean': 0, 'integration': 0, 'derivative': 0} or evaluator._materials:
        raise ValueError('P20_FACTORY_MUST_RETURN_FRESH_UNEVALUATED_NATIVE_OBJECTS')
    if seed.get('native_c_sha256') != canonical_digest(list(coefficients)):
        raise ValueError('P20_REGISTERED_C_DIGEST_MISMATCH')
    recheck_inputs(bundle['input_identity'], base)
    verify_core_python(config)
    bundle.update(prepared=prepared, evaluator=evaluator, coefficients=coefficients,
                  frame=frame, seed_registration=seed,
                  evaluator_settings=asdict(evaluator_settings), solver_settings=asdict(solver_settings))
    return bundle


def observed_pins(bundle):
    """Collect real loaded binaries, real problem/context and represented c."""
    from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
    evaluator = bundle['evaluator']
    if type(evaluator) is not InProcessCherchiEvaluator:
        raise TypeError('P20_ACTUAL_INPROCESS_EVALUATOR_REQUIRED')
    adapter = sys.modules[InProcessCherchiEvaluator.__module__]
    pins = dict(native_sha256=sha256(evaluator.native.__file__),
                bridge_sha256=sha256(evaluator.bridge.__file__),
                adapter_sha256=sha256(adapter.__file__),
                c_sha256=canonical_digest(list(bundle['coefficients'])),
                problem_input_digest=bundle['problem'].input_digest,
                context_sha256=evaluator.context_identity)
    if set(pins) != PIN_KEYS or any(re.fullmatch('[0-9a-f]{64}', value) is None for value in pins.values()):
        raise ValueError('P20_OBSERVED_PIN_FORMAT_ERROR')
    return pins


def prepare_one():
    """Contract expected by fixed W0 M6: actual evaluator, problem, unit c."""
    bundle = prepare_context()
    return bundle['evaluator'], bundle['problem'], bundle['coefficients']

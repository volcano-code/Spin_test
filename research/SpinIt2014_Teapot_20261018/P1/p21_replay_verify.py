#!/usr/bin/env python3
"""Offline P21 archive, same-call byte identity and exact moment replay.

This standard-library program never imports a native extension, invokes a
factory, generates a source, or performs a Boolean.  Native set predicates
remain statements in the authenticated runtime receipt.  Equal archived
Jacobian bytes prove identity of saved values, not correctness or smoothness.
An external SHA binds the archive manifest; it is not runtime attestation.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path, PurePosixPath
import re
import struct
import sys


SCHEMA = 'W4_P21_OFFLINE_REPLAY_REVIEW_V1'
BUNDLE_SCHEMA = 'W4_P21_REPLAY_BUNDLE_V1'
W0_COMMIT = '51cbfd33d08063404d7e0c40e4256dd0e38efa1a'
W4_BASELINE = 'c85c7f3b8b985ad68e5db58975123654c57132dd'
P20_REQUEST_SHA = '74d9cfa64417dd2c82d196ab27094651976954742a4c692667a1b19b1032de62'
P20_LAUNCHER_SHA = '3f2f9164f73754479bfe923ddb09e022b152985d8e7fc04cf41832ccf4a07e03'
P20_PHYSICAL_SHA = '6f71e5d7ce1a2fcb14579beb5f6680ea3b847193ad4d6ba48cfcc962ce008391'
CHERCHI = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0'
ORDER = ['M', 'LX', 'LY', 'LZ', 'QXX', 'QYY', 'QZZ', 'QYZ', 'QXZ', 'QXY']
PIN_KEYS = {'native_sha256', 'bridge_sha256', 'adapter_sha256', 'c_sha256',
            'problem_input_digest', 'context_sha256'}
SHA = re.compile(r'[0-9a-f]{64}\Z')
TOKEN = re.compile(r'-?(?:0b[01]+|0|[1-9][0-9]*)/(?:0b[01]+|[1-9][0-9]*)\Z')
MAX_FILE_BYTES = 256 * 1024**2
FALSE_FLAGS = {'native_execution_independently_proved': False,
               'native_set_predicates_reexecuted': False,
               'numerical_J_correctness_proved': False,
               'derivative_neighborhood_certified': False,
               'W0_owner_admitted': False, 'W2_teacher_training_allowed': False,
               'physical_validation_passed': False, 'Faster_optimization_executed': False,
               'MuJoCo_optimized_before_after_executed': False}


class VerificationRejected(ValueError):
    pass


def need(condition, message):
    if not condition:
        raise VerificationRejected(message)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False)


def digest(value):
    return sha256(canonical(value).encode('ascii'))


def strict_json(data):
    def pairs(items):
        out = {}
        for key, value in items:
            need(key not in out, 'DUPLICATE_JSON_KEY:' + key)
            out[key] = value
        return out
    def nonfinite(value):
        raise VerificationRejected('NONFINITE_JSON:' + value)
    result = json.loads(data, object_pairs_hook=pairs, parse_constant=nonfinite)
    def finite_tree(value):
        if type(value) is float:
            need(math.isfinite(value), 'NONFINITE_JSON_EXPONENT')
        elif type(value) is dict:
            for child in value.values():
                finite_tree(child)
        elif type(value) is list:
            for child in value:
                finite_tree(child)
    finite_tree(result)
    return result


def reject_test_only(value):
    if isinstance(value, dict):
        for key, item in value.items():
            need(not ('TEST_ONLY' in key or key.lower() == 'test_only' and item is not False),
                 'TEST_ONLY_REJECTED_IN_PRODUCTION')
            reject_test_only(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            reject_test_only(item)
    elif isinstance(value, str):
        need('TEST_ONLY' not in value, 'TEST_ONLY_REJECTED_IN_PRODUCTION')


def reject_scientific_release(value):
    forbidden = set(FALSE_FLAGS) - {'native_execution_independently_proved', 'native_set_predicates_reexecuted',
                                  'numerical_J_correctness_proved'}
    forbidden |= {'W0_owner_adoption', 'W0_physical_case_approved', 'training_admissible',
                  'training_admitted', 'newton_admitted', 'newton_converged',
                  'smooth_derivative_proved', 'smooth_derivative_certified',
                  'smooth_neighborhood_certified', 'newton_terminal_certified'}
    if isinstance(value, dict):
        for key, item in value.items():
            if key in forbidden:
                need(item is False, 'FORBIDDEN_SCIENTIFIC_RELEASE:' + key)
            reject_scientific_release(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            reject_scientific_release(item)


def finite(value):
    need(type(value) in (int, float), 'FINITE_NUMBER_REQUIRED_NO_BOOL')
    result = float(value)
    need(math.isfinite(result), 'FINITE_NUMBER_REQUIRED')
    return result


def packed(values, length):
    need(type(values) in (list, tuple) and len(values) == length, 'F64_SHAPE_MISMATCH')
    return struct.pack('<' + str(length) + 'd', *(finite(x) for x in values))


def fraction(token):
    need(type(token) is str and TOKEN.fullmatch(token), 'INVALID_EXACT_RATIONAL_TOKEN')
    a, b = token.split('/')
    number = lambda s: int(s, 2 if s.lstrip('-').startswith('0b') else 10)
    return Fraction(number(a), number(b))


def encode(values):
    return [str(x.numerator) + '/' + str(x.denominator) for x in values]


def points_from_tokens(rows):
    need(type(rows) in (list, tuple), 'EXACT_VERTEX_ROWS_REQUIRED')
    out = []
    for row in rows:
        need(type(row) in (list, tuple) and len(row) == 3, 'EXACT_VERTEX_TRIPLE_REQUIRED')
        out.append(tuple(fraction(x) for x in row))
    return tuple(out)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def subtract(a, b):
    return tuple(x-y for x, y in zip(a, b))


def dot(a, b):
    return sum((x*y for x, y in zip(a, b)), Fraction(0))


def checked_faces(points, rows):
    need(type(rows) in (list, tuple), 'FACE_ROWS_REQUIRED')
    seen, result = set(), []
    for face in rows:
        need(type(face) in (list, tuple) and len(face) == 3, 'TRIANGLE_REQUIRED')
        need(all(type(i) is int and 0 <= i < len(points) for i in face), 'FACE_INDEX_INVALID')
        need(len(set(face)) == 3, 'REPEATED_FACE_VERTEX')
        key = tuple(sorted(face))
        need(key not in seen, 'DUPLICATE_TRIANGLE')
        seen.add(key)
        a, b, c = (points[i] for i in face)
        need(any(cross(subtract(b, a), subtract(c, a))), 'EXACT_ZERO_AREA_TRIANGLE')
        result.append(tuple(face))
    return tuple(result)


def orient_packet(points, raw_faces):
    """Independent exact replay of registered local winding normalization.

    Face order and coordinates are unchanged. Relative edge parity determines
    flips; the emitted signed volume sign of each component is preserved.
    This is arithmetic bookkeeping, never a new Boolean or embedding proof.
    """
    faces = checked_faces(points, raw_faces)
    if not points and not faces:
        return (), []
    need(len(points) >= 4 and len(faces) >= 4, 'CLOSED_BOUNDARY_REQUIRED')
    edges = defaultdict(list)
    for i, (a, b, c) in enumerate(faces):
        for u, v in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((u, v)))].append((i, 1 if u < v else -1))
    need(all(len(rows) == 2 for rows in edges.values()), 'OPEN_OR_NONMANIFOLD_EDGE')
    graph = [[] for _ in faces]
    for (i, di), (j, dj) in edges.values():
        graph[i].append((j, int(di == dj)))
        graph[j].append((i, int(di == dj)))
    assigned, components = {}, []
    for start in range(len(faces)):
        if start in assigned:
            continue
        assigned[start], stack, component = 0, [start], []
        while stack:
            i = stack.pop()
            component.append(i)
            for j, parity in graph[i]:
                expected = assigned[i] ^ parity
                if j in assigned:
                    need(assigned[j] == expected, 'NONORIENTABLE_BOUNDARY')
                else:
                    assigned[j] = expected
                    stack.append(j)
        components.append(component)
    output = tuple((a, c, b) if assigned[i] else (a, b, c)
                   for i, (a, b, c) in enumerate(faces))
    for component in components:
        reference = points[faces[component[0]][0]]
        emitted = coherent = Fraction(0)
        for i in component:
            a, b, c = (points[k] for k in faces[i])
            term = dot(subtract(a, reference), cross(subtract(b, a), subtract(c, a))) / 6
            emitted += term
            coherent += -term if assigned[i] else term
        need(emitted and coherent and (emitted > 0) == (coherent > 0),
             'AMBIGUOUS_COMPONENT_ORIENTATION')
    validate_closed(points, output)
    return output, [i for i in range(len(faces)) if assigned[i]]


def validate_closed(points, faces):
    if not points and not faces:
        return
    checked_faces(points, faces)
    edges, incident, adjacency = defaultdict(list), defaultdict(set), defaultdict(lambda: defaultdict(set))
    for i, (a, b, c) in enumerate(faces):
        for v in (a, b, c):
            incident[v].add(i)
        for u, v in ((a, b), (b, c), (c, a)):
            edges[tuple(sorted((u, v)))].append((u, v, i))
    for edge, rows in edges.items():
        need(len(rows) == 2, 'OPEN_OR_NONMANIFOLD_EDGE')
        (a, b, i), (c, d, j) = rows
        need(a == d and b == c, 'INCONSISTENT_FACE_ORIENTATION')
        for v in edge:
            adjacency[v][i].add(j)
            adjacency[v][j].add(i)
    for v in range(len(points)):
        need(bool(incident[v]), 'UNREFERENCED_VERTEX')
        seen, stack = set(), [next(iter(incident[v]))]
        while stack:
            i = stack.pop()
            if i not in seen:
                seen.add(i)
                stack.extend(adjacency[v][i])
        need(seen == incident[v], 'PINCHED_NONMANIFOLD_VERTEX')


def exact_raw10(points, faces, density=Fraction(1)):
    """Signed tetrahedral monomial integration, preserving inward cavity shells."""
    need(type(density) is Fraction and density > 0, 'POSITIVE_EXACT_DENSITY_REQUIRED')
    validate_closed(points, faces)
    out = [Fraction(0) for _ in ORDER]
    if not points and not faces:
        return tuple(out)
    for ia, ib, ic in faces:
        a, b, c = points[ia], points[ib], points[ic]
        weight = density * dot(a, cross(b, c)) / 6
        summed = tuple(a[i] + b[i] + c[i] for i in range(3))
        out[0] += weight
        for i in range(3):
            out[1+i] += weight*summed[i]/4
        for k, (i, j) in enumerate(((0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1)), 4):
            out[k] += weight*(summed[i]*summed[j] + a[i]*a[j] + b[i]*b[j] + c[i]*c[j])/20
    need(out[0] > 0, 'NONPOSITIVE_ORIENTED_MATERIAL_VOLUME')
    return tuple(out)


def read_obj_bytes(data):
    points, faces = [], []
    for line in data.decode('ascii').splitlines():
        fields = line.split('#', 1)[0].split()
        if not fields:
            continue
        if fields[0] == 'v':
            need(len(fields) == 4, 'OBJ_VERTEX_ARITY')
            values = [float(x) for x in fields[1:]]
            need(all(math.isfinite(x) for x in values), 'OBJ_NONFINITE_VERTEX')
            points.append(tuple(Fraction.from_float(x) for x in values))
        elif fields[0] == 'f':
            need(len(fields) == 4 and all(re.fullmatch(r'[1-9][0-9]*', x) for x in fields[1:]),
                 'OBJ_POSITIVE_INDEXED_TRIANGLES_REQUIRED')
            faces.append(tuple(int(x)-1 for x in fields[1:]))
        else:
            raise VerificationRejected('OBJ_UNREGISTERED_RECORD')
    need(points and faces, 'EMPTY_FROZEN_MATERIAL')
    return tuple(points), checked_faces(points, faces)


def _frozen_materials(data_by_name, request, *, test_only=False):
    need(request.get('schema') == 'W4_P20_TEAPOT_NATIVE_REQUEST_V1', 'FROZEN_REQUEST_SCHEMA')
    need(type(request['units']['fixed_density']) in (int, float) and
         type(request['units']['design_density']) in (int, float) and
         request['units']['fixed_density'] == request['units']['design_density'] == 1,
         'P21_REGISTERED_UNIT_MODEL_DENSITY_REQUIRED')
    boundaries, moments = {}, {}
    for name in ('M', 'F', 'D'):
        data = data_by_name[name]
        binding = request['material_inputs'][name]
        need(sha256(data) == binding['sha256'], 'FROZEN_MATERIAL_SHA_MISMATCH:' + name)
        points, faces = read_obj_bytes(data)
        need(len(points) == binding['vertices'] and len(faces) == binding['faces'],
             'FROZEN_MATERIAL_SHAPE_MISMATCH:' + name)
        boundaries[name] = (points, faces)
        moments[name] = exact_raw10(points, faces)
    residual = tuple(m-f-d for m, f, d in zip(moments['M'], moments['F'], moments['D']))
    need(not any(residual), 'FROZEN_MFD_EXACT_MOMENT_RESIDUAL')
    report = {'status': 'TEST_ONLY_FROZEN_MFD_ARITHMETIC_CONSISTENT' if test_only else
              'FROZEN_MFD_EXACT_MOMENTS_REPLAYED', 'raw10_order': ORDER,
              'reference_raw10': {k: encode(v) for k, v in moments.items()},
              'M_minus_F_minus_D_exact': encode(residual),
              'all_ten_residuals_zero': True, 'native_set_equality_proved': False,
              'geometry_or_factory_executed': False, 'test_only': test_only}
    return report, boundaries


def verify_frozen_materials(material_paths, request_path, *, allow_test_only=False):
    request_bytes = Path(request_path).read_bytes()
    request = strict_json(request_bytes)
    if not allow_test_only:
        need(sha256(request_bytes) == P20_REQUEST_SHA, 'P20_REGISTERED_REQUEST_SHA_MISMATCH')
        reject_test_only(request)
    report, _ = _frozen_materials({k: Path(material_paths[k]).read_bytes() for k in ('M', 'F', 'D')},
                                 request, test_only=allow_test_only)
    return report


def _launcher():
    return _load_pinned_python('p20_m6_launch.py', P20_LAUNCHER_SHA, '_p21_pinned_p20_launch')


def _load_pinned_python(filename, expected_sha, module_name):
    path = Path(__file__).with_name(filename)
    data = path.read_bytes()
    need(sha256(data) == expected_sha, 'PINNED_P20_VALIDATOR_CHANGED:' + filename)
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    # Execute the authenticated source bytes, never a timestamp-valid old .pyc.
    exec(compile(data, str(path), 'exec'), module.__dict__)
    return module


class Bundle:
    def __init__(self, root, expected_sha, allow_test_only):
        root = Path(root).absolute()
        need(not any(p.is_symlink() for p in (root, *root.parents)), 'BUNDLE_SYMLINK_REJECTED')
        need(type(expected_sha) is str and SHA.fullmatch(expected_sha), 'EXTERNAL_MANIFEST_SHA_REQUIRED')
        self.root, self.files, self.roles = root, {}, defaultdict(list)
        data = self.read_relative('manifest.json')
        need(sha256(data) == expected_sha, 'EXTERNAL_MANIFEST_SHA_MISMATCH')
        self.manifest, self.manifest_sha = strict_json(data), expected_sha
        need(self.manifest.get('schema') == BUNDLE_SCHEMA, 'BUNDLE_SCHEMA_MISMATCH')
        need(type(self.manifest.get('test_only')) is bool, 'EXPLICIT_TEST_ONLY_STATE_REQUIRED')
        self.test_only = self.manifest['test_only']
        need(not self.test_only or allow_test_only, 'TEST_ONLY_REJECTED_IN_PRODUCTION')
        if not self.test_only:
            reject_test_only(self.manifest)
            need(self.manifest.get('w0_commit') == W0_COMMIT and
                 self.manifest.get('source_w4_baseline_commit') == W4_BASELINE, 'FROZEN_COMMIT_MISMATCH')
        rows = self.manifest.get('files')
        need(type(rows) is list and 0 < len(rows) <= 4096, 'BUNDLE_FILE_INVENTORY_REQUIRED')
        total = 0
        for row in rows:
            need(type(row) is dict and set(('path', 'sha256', 'bytes', 'role')) <= set(row),
                 'BUNDLE_FILE_RECORD_INVALID')
            need(row['path'] not in self.files and row['path'] != 'manifest.json', 'DUPLICATE_BUNDLE_PATH')
            need(type(row['bytes']) is int and 0 <= row['bytes'] <= MAX_FILE_BYTES, 'BUNDLE_FILE_SIZE_INVALID')
            need(type(row['sha256']) is str and SHA.fullmatch(row['sha256']), 'BUNDLE_FILE_SHA_INVALID')
            raw = self.read_relative(row['path'])
            need(len(raw) == row['bytes'] and sha256(raw) == row['sha256'], 'BUNDLE_FILE_HASH_MISMATCH:' + row['path'])
            total += len(raw)
            need(total <= 1024**3, 'BUNDLE_TOTAL_SIZE_LIMIT')
            self.files[row['path']] = (row, raw)
            self.roles[row['role']].append(row['path'])

    def read_relative(self, relative):
        need(type(relative) is str and relative and '\\' not in relative, 'ARCHIVE_PATH_INVALID')
        parts = PurePosixPath(relative)
        need(not parts.is_absolute() and '..' not in parts.parts and parts.as_posix() == relative,
             'ARCHIVE_PATH_ESCAPE_OR_NONCANONICAL')
        path = self.root.joinpath(*parts.parts)
        need(not any(p.is_symlink() for p in (path, *path.parents)), 'ARCHIVE_SYMLINK_REJECTED')
        need(path.is_file() and path.stat().st_size <= MAX_FILE_BYTES, 'ARCHIVE_FILE_UNAVAILABLE')
        return path.read_bytes()

    def role(self, role, required=True):
        paths = self.roles.get(role, [])
        need(len(paths) == 1 or not required and not paths, 'SINGLETON_ROLE_REQUIRED:' + role)
        return self.files[paths[0]] if paths else None

    def json_role(self, role, required=True):
        record = self.role(role, required)
        if record is None:
            return None
        result = strict_json(record[1])
        if not self.test_only:
            reject_test_only(result)
        return result

    def capture_artifact(self, row, parent):
        need(type(row) is dict and set(('path', 'sha256', 'bytes')) <= set(row), 'CAPTURE_ARTIFACT_RECORD')
        relative = (PurePosixPath(parent) / row['path']).as_posix()
        need(relative in self.files, 'CAPTURE_FILE_NOT_IN_EXTERNAL_MANIFEST:' + relative)
        stored, raw = self.files[relative]
        need(stored['sha256'] == row['sha256'] and stored['bytes'] == row['bytes'], 'CAPTURE_ARTIFACT_IDENTITY_MISMATCH')
        return raw


def target_points(points, context):
    normalization, request = context['normalization'], context['request']
    origin = tuple(Fraction.from_float(finite(x)) for x in normalization['origin'])
    length = Fraction.from_float(finite(normalization['L']))
    shift = tuple(Fraction.from_float(finite(x)) for x in request['target_origin'])
    axes = tuple(tuple(Fraction.from_float(finite(x)) for x in row) for row in request['target_axes'])
    need(len(origin) == len(shift) == len(axes) == 3 and all(len(r) == 3 for r in axes) and length > 0,
         'CAPTURE_FRAME_INVALID')
    # The registered P20 experiment has exact identity target axes.
    need(axes == ((1, 0, 0), (0, 1, 0), (0, 0, 1)), 'UNREGISTERED_P21_TARGET_AXES')
    return tuple(tuple((p[i]-origin[i])/length-shift[i] for i in range(3)) for p in points)


def compare_conversion(values, exact, label):
    need(len(values) == len(exact) == 10, 'RAW10_SHAPE_MISMATCH:' + label)
    errors = []
    for actual, truth in zip(values, exact):
        a, e = finite(actual), float(truth)
        need(math.isfinite(e), 'EXACT_MOMENT_FLOAT_OVERFLOW')
        error = abs(a-e)
        need(error <= 32*math.ulp(max(1., abs(e))), 'RAW10_CONVERSION_MISMATCH:' + label)
        errors.append(error)
    return max(errors)


def _capture(bundle):
    manifest = bundle.json_role('capture_manifest')
    need(manifest.get('schema') == 'W4_P21_SAME_CALL_CAPTURE_MANIFEST_V1', 'CAPTURE_SCHEMA')
    need(manifest.get('state') == 'capturing' and type(manifest.get('admission')) is dict and
         all(value is False for value in manifest['admission'].values()), 'CAPTURE_STATE_OR_ADMISSION_INVALID')
    parent = PurePosixPath(bundle.roles['capture_manifest'][0]).parent.as_posix()
    context_raw = bundle.capture_artifact(manifest['context'], parent)
    events_raw = bundle.capture_artifact(manifest['events'], parent)
    need(context_raw == bundle.role('capture_context')[1] and events_raw == bundle.role('capture_events')[1],
         'CAPTURE_CONTEXT_OR_EVENTS_ROLE_MISMATCH')
    context = strict_json(context_raw)
    events = [strict_json(line) for line in events_raw.splitlines() if line.strip()]
    need(context.get('schema') == 'W4_P21_SAME_CALL_CONTEXT_V1' and
         manifest.get('event_count') == len(events), 'CAPTURE_CONTEXT_SCHEMA_OR_EVENT_COUNT')
    reject_scientific_release(context)
    if not bundle.test_only:
        reject_test_only(manifest)
        reject_test_only(context)
        reject_test_only(events)
    stages, pending, completed, attempts = defaultdict(list), {}, defaultdict(int), defaultdict(int)
    last_call_index = 0
    for index, event in enumerate(events, 1):
        need(event.get('schema') == 'W4_P21_STAGE_EVENT_V1' and
             event.get('seq') == index and type(event['seq']) is int, 'CAPTURE_EVENT_SEQUENCE')
        if event.get('phase') != 'native_stage':
            continue
        stage, ordinal = event.get('stage'), event.get('ordinal')
        need(type(stage) is str and type(ordinal) is int and ordinal > 0, 'CAPTURE_STAGE_ID_INVALID')
        key = (stage, ordinal)
        if event.get('event') == 'begin':
            need(not pending and type(event.get('call_index')) is int and event['call_index'] == last_call_index+1,
                 'CAPTURE_NON_SERIAL_OR_INVALID_CALL_INDEX')
            last_call_index += 1
            attempts[stage] += 1
            need(ordinal == attempts[stage] and key not in pending, 'CAPTURE_STAGE_ORDINAL')
            pending[key] = event
        elif event.get('event') == 'completed':
            need(key in pending and event.get('call_index') == pending[key].get('call_index'), 'CAPTURE_COMPLETION_WITHOUT_BEGIN')
            need(event.get('operation_returned') is True, 'CAPTURE_OPERATION_DID_NOT_RETURN')
            del pending[key]
            completed[stage] += 1
            artifacts = event.get('artifacts', [])
            stages[stage].append((event, {row['role']: (row, bundle.capture_artifact(row, parent)) for row in artifacts}))
            need(len(artifacts) == len(stages[stage][-1][1]), 'DUPLICATE_STAGE_ARTIFACT_ROLE')
        else:
            raise VerificationRejected('FORMAL_SUCCESS_WITH_FAILED_CAPTURE_STAGE')
    need(not pending, 'CAPTURE_INCOMPLETE_STAGES')
    need(dict(completed) == manifest['completed_stage_counts'], 'CAPTURE_COMPLETED_COUNTS_MISMATCH')
    need(dict(attempts) == manifest['operation_attempt_counts'], 'CAPTURE_ATTEMPT_COUNTS_MISMATCH')
    for stage, count in (('source', 1), ('boolean', 2), ('derivative', 1), ('material_attachment_serialization', 1), ('intersection_motion', 1)):
        need(completed[stage] == count, 'CAPTURE_REQUIRED_STAGE_COUNT:' + stage)
    need(len(stages['integration']) in (1, 2), 'CAPTURE_REQUIRED_INTEGRATION_COUNT')
    ordered = [('source', 0), ('boolean', 0), ('intersection_motion', 0), ('derivative', 0),
               ('integration', 0), ('material_attachment_serialization', 0), ('boolean', 1)]
    sequence = [stages[stage][index][0]['seq'] for stage, index in ordered]
    need(sequence == sorted(sequence) and len(set(sequence)) == len(sequence), 'CAPTURE_REQUIRED_STAGE_ORDER')
    if len(stages['integration']) == 2:
        need(stages['integration'][1][0]['seq'] > sequence[-1], 'COMPLEMENT_INTEGRATION_PRECEDES_BOOLEAN')
    def artifact(stage, ordinal, role):
        found = [a[role] for event, a in stages[stage] if event['ordinal'] == ordinal and role in a]
        need(len(found) == 1, 'CAPTURE_REQUIRED_ARTIFACT:' + stage + ':' + role)
        return found[0]
    return context, stages, artifact


def _envelope(bundle, report, pins):
    launch = _launcher()
    need(report.get('schema') == launch.SCHEMA and report.get('w0_commit') == W0_COMMIT, 'FORMAL_REPORT_SCHEMA_OR_W0')
    for key in launch.FALSE_ADMISSION_FLAGS:
        need(report.get(key) is False, 'FORMAL_FORBIDDEN_ADMISSION:' + key)
    need(report.get('status') == 'REAL_NATIVE_M6_GEOMETRY_VERIFIED_NO_SCIENTIFIC_RELEASE' and
         report.get('native_full_partition_certified') is True and report.get('worker_started') is True and
         report.get('native_audit_invoked') is True and report.get('source_files_unchanged') is True,
         'FORMAL_SUCCESS_RECEIPT_REQUIRED')
    need(launch.resource_admission(report['resources']) == 'ADMITTED_RESOURCE_POLICY_ONLY', 'FORMAL_RESOURCE_POLICY_NOT_SATISFIED')
    child = report['child_process']
    need(type(child['returncode']) is int and child['returncode'] == 0 and child['timed_out'] is False,
         'FORMAL_CHILD_FAILED_OR_TIMED_OUT')
    worker = child['worker_report']
    need(worker.get('schema') == launch.WORKER_SCHEMA and type(worker.get('run_nonce')) is str and
         re.fullmatch(r'[0-9a-f]{32}', worker['run_nonce']), 'FORMAL_WORKER_ENVELOPE')
    need(launch.resource_admission(worker['resources']) == 'ADMITTED_RESOURCE_POLICY_ONLY', 'WORKER_RESOURCE_POLICY_NOT_SATISFIED')
    need(worker.get('worker_started') is True and worker.get('native_audit_invoked') is True and
         worker.get('factory_imported') is True, 'WORKER_NATIVE_EXECUTION_FIELDS_MISSING')
    for envelope in (report, worker):
        counts = envelope.get('native_call_counts_observed')
        need(type(counts) is dict and counts == {'source': 1, 'boolean': 2} and
             all(type(value) is int for value in counts.values()), 'ENVELOPE_NATIVE_COUNTS_MISMATCH')
    limits = worker['child_limits']
    need(type(limits.get('RLIMIT_AS_soft_bytes')) is int and
         20*1024**3 <= limits['RLIMIT_AS_soft_bytes'] == limits.get('RLIMIT_AS_hard_bytes') <= 24*1024**3 and
         limits.get('wall_alarm_seconds') == 3600, 'WORKER_LIMITS_MISMATCH')
    for key in launch.FALSE_ADMISSION_FLAGS:
        need(worker.get(key) is False, 'WORKER_FORBIDDEN_ADMISSION:' + key)
    snapshot = report['source_snapshot']
    need(digest(snapshot) == report['source_snapshot_sha256'] == worker['source_snapshot_sha256'], 'SOURCE_SNAPSHOT_DIGEST_MISMATCH')
    pin_sha = bundle.role('pins')[0]['sha256']
    need(report['external_pins_sha256'] == report['pins_file_sha256'] == worker['pins_file_sha256'] == pin_sha,
         'FORMAL_EXTERNAL_PINS_MISMATCH')
    need(snapshot['factory_file']['sha256'] == report['external_factory_sha256'], 'FORMAL_FACTORY_SHA_MISMATCH')
    need(worker.get('source_files_unchanged') is True and worker.get('native_full_partition_certified') is True and
         report['m6_evidence'] == worker['m6_evidence'], 'FORMAL_PARENT_WORKER_M6_MISMATCH')
    launch.validate_m6_evidence(report['m6_evidence'], pins)
    for role, key in (('worker_stdout', 'stdout_log'), ('worker_stderr', 'stderr_log')):
        row, raw = bundle.role(role)
        need(child[key]['sha256'] == row['sha256'] and child[key]['bytes'] == len(raw), 'WORKER_LOG_HASH_MISMATCH')
        if role == 'worker_stdout':
            prefix = launch.RESULT_PREFIX
            found = [strict_json(line[len(prefix):]) for line in raw.decode('utf-8', errors='strict').splitlines()
                     if line.startswith(prefix)]
            need(len(found) == 1 and found[0] == worker, 'WORKER_STDOUT_ENVELOPE_MISMATCH')
    for key in ('native_sha256', 'bridge_sha256', 'adapter_sha256'):
        need(report['native_module_files'][key]['sha256'] == pins[key] and
             worker['native_module_files'][key] == report['native_module_files'][key], 'ACTUAL_MODULE_PIN_MISMATCH')
    return report['m6_evidence']


def _production_context(context, formal, request, pins):
    need(context.get('p20_request_sha256') == P20_REQUEST_SHA, 'CAPTURE_REGISTERED_REQUEST_MISMATCH')
    need(digest(context['problem_identity']) == pins['problem_input_digest'], 'PROBLEM_IDENTITY_DIGEST_MISMATCH')
    inputs = context['input_identity']
    need(inputs.get('P20_native_request.json') == P20_REQUEST_SHA, 'CAPTURE_REQUEST_INPUT_MISMATCH')
    references = {'manifest': request['manifest'], 'canonical_report': request['canonical_report'], **request['material_inputs']}
    for row in references.values():
        need(inputs.get(row['path']) == row['sha256'], 'CAPTURE_FROZEN_INPUT_MISMATCH')
    producers = context['producerfiles']
    for name, pin in (('native', 'native_sha256'), ('bridge', 'bridge_sha256'), ('adapter', 'adapter_sha256')):
        need(producers[name]['sha256'] == pins[pin], 'CAPTURE_PRODUCER_PIN_MISMATCH')
    need(producers['factory']['sha256'] == formal['external_factory_sha256'] and
         producers['p20_launcher']['sha256'] == P20_LAUNCHER_SHA, 'CAPTURE_FACTORY_OR_LAUNCHER_MISMATCH')
    snapshot = formal['source_snapshot']
    need(producers['capture']['sha256'] == snapshot['factory_peer_sources_and_config']['p21_same_call_capture.py']['sha256'],
         'CAPTURE_OBSERVER_SOURCE_MISMATCH')
    physical = _load_pinned_python('p20_physical_contract.py', P20_PHYSICAL_SHA, '_p21_pinned_p20_physical')
    frame = physical.Frame.from_core(context['normalization'], context['request']['target_origin'],
                                    context['request']['target_axes'], requested_tip=request['target']['origin'])
    need(frame.report() == context['frame'], 'EXACT_PHYSICAL_FRAME_REPORT_MISMATCH')
    seed = physical.register_p20_dyadic_seed(frame)
    need(packed(seed['native_c'], 10) == packed(context['c'], 10), 'REGISTERED_SEED_C_BYTES_MISMATCH')


def _replay_cut(context, artifact, stages, boundaries, pins, evidence, *, test_only=False):
    need(context['pins'] == pins and digest(context['c']) == pins['c_sha256'] and
         context['problem_input_digest'] == pins['problem_input_digest'], 'CAPTURE_CONTEXT_PIN_MISMATCH')
    need(context['normalization'] == context['problem_identity']['normalization'], 'CAPTURE_NORMALIZATION_MISMATCH')
    need(abs(math.sqrt(math.fsum(x*x for x in struct.unpack('<10d', packed(context['c'], 10))))-1) <= 1e-12,
         'CAPTURE_C_NOT_UNIT')
    material = strict_json(artifact('material_attachment_serialization', 1, 'retained_material')[1])
    source = strict_json(artifact('source', 1, 'source_result')[1])
    packets = [strict_json(artifact('boolean', i, 'boolean_packet')[1]) for i in (1, 2)]
    if not test_only:
        for document in (material, source, *packets):
            reject_test_only(document)
    reject_scientific_release(material)
    need(packed(material['quadric_coefficients'], 10) == packed(context['c'], 10), 'MATERIAL_C_BYTES_MISMATCH')
    need(material['evaluation_map_identity'] == pins['context_sha256'], 'MATERIAL_CONTEXT_MISMATCH')
    need(material['boolean_backend_identity'].startswith(CHERCHI + ':'), 'MATERIAL_BOOLEAN_BACKEND_CHANGED')
    need(material['derivative_defined'] is True, 'MATERIAL_POINT_DERIVATIVE_UNDEFINED')
    need(all(p.get('backend') == CHERCHI + '-inprocess-v1' for p in packets), 'RAW_BOOLEAN_BACKEND_CHANGED')
    need(source.get('defined') is True and source.get('side_selection_defined') is True and
         type(source.get('interior_is_positive')) is bool, 'SOURCE_UNDEFINED')
    operation = 'intersection' if source['interior_is_positive'] else 'subtraction'
    need(material['boolean_operation'] == operation, 'RETAINED_SOURCE_SIDE_MISMATCH')
    source_faces = source['faces']
    need(source_faces == material['quadric_source_faces'], 'SAVED_SOURCE_FACES_MISMATCH')
    # Registered axes are I; follow the producer's separate binary64 add/mul/add operations.
    target_points((), context)
    norm, request = context['normalization'], context['request']
    expected_sv = [[(finite(row[i])+finite(request['target_origin'][i]))*finite(norm['L']) + finite(norm['origin'][i])
                    for i in range(3)] for row in source['vertices']]
    need(len(expected_sv) == len(material['quadric_source_vertices']), 'SAVED_SOURCE_VERTEX_COUNT')
    need(all(len(b) == 3 and all(finite(x) == finite(y) for x, y in zip(a, b))
             for a, b in zip(expected_sv, material['quadric_source_vertices'])),
         'SAVED_SOURCE_PHYSICAL_BYTES_MISMATCH')
    source_hash = digest({'vertices': material['quadric_source_vertices'], 'faces': source_faces,
                          'coefficients': context['c']})
    need(source_hash == material['quadric_source_identity'], 'SAME_SOURCE_DIGEST_MISMATCH')
    retained_points = points_from_tokens(packets[0]['exact_vertices'])
    retained_faces, flips = orient_packet(retained_points, packets[0]['faces'])
    need(packets[0]['exact_vertices'] == material['material_proof']['exact_vertices'] and
         packets[0]['construction_records'] == material['material_proof']['construction_records'], 'RAW_RETAINED_PACKET_NOT_SAVED_MATERIAL')
    need([list(x) for x in retained_faces] == material['variable_faces'] and
         material['material_proof']['orientation']['flipped_face_indices'] == flips, 'RETAINED_ORIENTATION_REPLAY_MISMATCH')
    retained_target = target_points(retained_points, context)
    need(retained_target == points_from_tokens(material['variable_rational_vertices']), 'RETAINED_EXACT_FRAME_MISMATCH')
    need(all(packed(row, 3) == packed([float(v) for v in exact], 3)
             for row, exact in zip(material['variable_vertices'], retained_target)) and
         len(material['variable_vertices']) == len(retained_target), 'RETAINED_DISPLAY_ROUNDING_MISMATCH')
    geometry_hash = digest({'vertices': packets[0]['exact_vertices'], 'faces': material['variable_faces']})
    need(geometry_hash == material['geometry_hash'], 'RETAINED_GEOMETRY_DIGEST_MISMATCH')
    derivative_row, derivative = artifact('derivative', 1, 'derivative_f64le')
    need(derivative_row.get('shape') == [10, 10] and derivative_row.get('dtype') == '<f8' and
         derivative_row.get('order') == 'C' and derivative_row.get('encoding') == 'IEEE754_BINARY64_LITTLE_ENDIAN',
         'DERIVATIVE_BYTE_ENCODING_MISMATCH')
    jacobian = material['moment_jacobian']
    need(type(jacobian) is list and len(jacobian) == 10 and all(type(r) is list and len(r) == 10 for r in jacobian),
         'MATERIAL_JACOBIAN_SHAPE')
    need(len(derivative) == 800 and derivative == packed([v for row in jacobian for v in row], 100),
         'SAME_CALL_100_JACOBIAN_BYTES_MISMATCH')
    integration = artifact('integration', 1, 'integration_f64le')[1]
    need(len(integration) == 80 and integration == packed(material['variable_raw_moments'], 10), 'RETAINED_INTEGRATION_BYTES_MISMATCH')
    density = Fraction.from_float(finite(request['material_density']))
    raw = {'R': exact_raw10(retained_target, retained_faces, density)}
    cavity_points = points_from_tokens(packets[1]['exact_vertices'])
    cavity_faces, cavity_flips = orient_packet(cavity_points, packets[1]['faces'])
    cavity_target = target_points(cavity_points, context)
    raw['C'] = exact_raw10(cavity_target, cavity_faces, density)
    expected_integrations = 2 if cavity_points else 1
    need(len(stages['integration']) == expected_integrations, 'ACTUAL_INTEGRATION_STAGE_COUNT')
    errors = {'retained': compare_conversion(material['variable_raw_moments'], raw['R'], 'retained')}
    if cavity_points:
        encoded = artifact('integration', 2, 'integration_f64le')[1]
        need(len(encoded) == 80, 'CAVITY_INTEGRATION_SHAPE')
        errors['cavity'] = compare_conversion(struct.unpack('<10d', encoded), raw['C'], 'cavity')
    for name, (points, faces) in boundaries.items():
        raw[name] = exact_raw10(target_points(points, context), faces, density)
    design_residual = tuple(d-r-c for d, r, c in zip(raw['D'], raw['R'], raw['C']))
    full_residual = tuple(m-f-r-c for m, f, r, c in zip(raw['M'], raw['F'], raw['R'], raw['C']))
    need(not any(design_residual), 'EXACT_D_MINUS_R_MINUS_C_NONZERO')
    need(not any(full_residual), 'EXACT_M_MINUS_F_MINUS_R_MINUS_C_NONZERO')
    errors['fixed'] = compare_conversion(context['fixed'], raw['F'], 'fixed')
    errors['total'] = compare_conversion(material['raw_moments'], tuple(f+r for f, r in zip(raw['F'], raw['R'])), 'F_plus_R')
    m5, m4 = evidence['M5_evidence'], evidence['M5_evidence']['m4_native_evidence']
    need(m4['source_geometry_sha256'] == geometry_hash and m4['source_quadric_sha256'] == source_hash,
         'M4_SOURCE_OR_GEOMETRY_MISMATCH')
    need(tuple(fraction(x) for x in m5['w2_exact_math_reference']['exact_r10']) == raw['R'], 'M5_W2_EXACT_RAW10_MISMATCH')
    predicates = evidence['exact_partition_predicates']
    fmd, cut, full = [row['native_predicate_facts'] for row in predicates]
    original = context['problem_identity']['partition']
    need(fmd['whole_digest'] == full['whole_digest'] == original['whole_digest'] and
         fmd['part_digests'] == original['part_digests'] and
         cut['whole_digest'] == original['part_digests'][1] and
         full['part_digests'] == [original['part_digests'][0], *cut['part_digests']], 'THREE_PARTITION_DIGEST_BINDINGS_MISMATCH')
    return {'same_call_100_Jacobian_bytes_match': True, 'jacobian_sha256': sha256(derivative),
            'source_geometry_sha256': geometry_hash, 'source_quadric_sha256': source_hash,
            'source_transform_comparison': 'EXACT_BINARY64_VALUES_WITH_POSITIVE_NEGATIVE_ZERO_EQUIVALENCE_ONLY',
            'raw_source_and_saved_physical_source_hashes_preserve_original_bytes': True,
            'retained_operation': operation, 'complement_operation': 'subtraction' if operation == 'intersection' else 'intersection',
            'opposite_operation_binding_scope': 'PINNED_M6_RECEIPT_AND_STAGE_ORDER_RAW_PACKET_HAS_NO_OPERAND_ARGUMENTS',
            'target_raw10_exact': {k: encode(v) for k, v in raw.items()},
            'D_minus_R_minus_C_exact': encode(design_residual), 'M_minus_F_minus_R_minus_C_exact': encode(full_residual),
            'raw10_conversion_max_errors': errors, 'raw10_order': ORDER,
            'complement_relative_winding_flip_indices': cavity_flips,
            'three_native_predicate_receipts_structurally_bound': True,
            'arithmetic_equality_is_not_set_equality': True, **FALSE_FLAGS}


def verify_bundle(bundle_directory, expected_manifest_sha256, *, allow_test_only=False):
    report = {'schema': SCHEMA, 'status': 'INPUT_INCOMPLETE', 'completed': False,
              'formal_M6_receipt_success': False, 'same_call_100_Jacobian_bytes_match': False,
              'artifact_arithmetic_replay_passed': False, **FALSE_FLAGS}
    try:
        bundle = Bundle(bundle_directory, expected_manifest_sha256, allow_test_only)
        report.update(manifest_sha256=bundle.manifest_sha, verified_file_count=len(bundle.files),
                      test_only=bundle.test_only)
        collection_errors = bundle.manifest.get('collection_errors')
        need(type(collection_errors) is list and type(bundle.manifest.get('collection_completed')) is bool,
             'EXPLICIT_COLLECTION_STATE_REQUIRED')
        if bundle.manifest['collection_completed'] is not True or collection_errors:
            report.update(status='INPUT_INCOMPLETE_COLLECTION', collection_errors=collection_errors,
                          scope='FILE_HASHES_ONLY_COLLECTION_NOT_COMPLETE')
            return report
        request_raw = bundle.role('request')[1]
        request = bundle.json_role('request')
        if not bundle.test_only:
            need(sha256(request_raw) == P20_REQUEST_SHA, 'P20_REGISTERED_REQUEST_SHA_MISMATCH')
        frozen, boundaries = _frozen_materials({k: bundle.role('material_' + k)[1] for k in ('M', 'F', 'D')},
                                              request, test_only=bundle.test_only)
        report['frozen_MFD_arithmetic'] = frozen
        formal = bundle.json_role('formal_report')
        reject_scientific_release(formal)
        need(formal.get('schema') == 'W4_P20_M6_RUNTIME_V1' and formal.get('w0_commit') == W0_COMMIT,
             'FORMAL_REPORT_SCHEMA_OR_W0')
        executed = bundle.manifest.get('formal_executed')
        need(executed is None or type(executed) is bool, 'FORMAL_EXECUTION_STATE_INVALID')
        exit_code = bundle.manifest.get('formal_exit_code')
        need(type(exit_code) is int, 'ACTUAL_FORMAL_EXIT_CODE_REQUIRED')
        if executed is not True or exit_code != 0:
            need(exit_code != 0, 'FORMAL_NONEXECUTION_WITH_ZERO_EXIT')
            need(formal.get('native_full_partition_certified') is False, 'NONEXECUTION_WITH_SUCCESS_CLAIM')
            if executed is False:
                need(formal.get('worker_started') is False and formal.get('native_audit_invoked') is False and
                     formal.get('factory_imported') is False and formal.get('m6_evidence') is None,
                     'NONEXECUTION_ENVELOPE_CONTRADICTION')
                if formal.get('status', '').startswith(('BLOCKED_INSUFFICIENT_', 'BLOCKED_NONZERO_SWAP')):
                    need(_launcher().resource_admission(formal['resources']) == formal['status'],
                         'FORMAL_RESOURCE_REJECTION_REASON_MISMATCH')
                    need(exit_code == 3, 'FORMAL_RESOURCE_REJECTION_EXIT_MISMATCH')
            report.update(status='TEST_ONLY_BLOCKED_FORMAL_M6_NOT_EXECUTED' if bundle.test_only else
                          'BLOCKED_FORMAL_M6_NOT_EXECUTED' if executed is False else 'INPUT_INCOMPLETE_FORMAL_M6_NOT_VERIFIED',
                          formal_status=formal.get('status'), formal_exit_code=exit_code,
                          completed=True, scope='ARCHIVE_AND_FROZEN_MFD_ONLY_NO_FORMAL_CUT_OR_J')
            return report
        pins = bundle.json_role('pins')
        need(type(pins) is dict and set(pins) == PIN_KEYS and all(type(v) is str and SHA.fullmatch(v) for v in pins.values()),
             'EXACT_SIX_PIN_SET_REQUIRED')
        evidence = _envelope(bundle, formal, pins)
        context, stages, artifact = _capture(bundle)
        if not bundle.test_only:
            _production_context(context, formal, request, pins)
        replay = _replay_cut(context, artifact, stages, boundaries, pins, evidence, test_only=bundle.test_only)
        report.update(status='TEST_ONLY_ARITHMETIC_REPLAY_CONSISTENT_NO_NATIVE_PROOF' if bundle.test_only else
                      'ARCHIVE_AND_SAME_CALL_ARITHMETIC_REPLAY_CONSISTENT', completed=True,
                      formal_M6_receipt_success=not bundle.test_only,
                      test_only_formal_receipt_shape_valid=bundle.test_only,
                      same_call_100_Jacobian_bytes_match=True,
                      artifact_arithmetic_replay_passed=True, replay=replay,
                      scope='HASH_BOUND_RUNTIME_RECEIPT_AND_ARCHIVED_EXACT_ARITHMETIC_NOT_RUNTIME_ATTESTATION')
    except (VerificationRejected, OSError, ValueError, TypeError, KeyError, IndexError, OverflowError) as exc:
        report.update(status='REJECTED', error_type=type(exc).__name__, error=str(exc))
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    output = Path(args.output)
    need(not output.exists() and not any(p.is_symlink() for p in (output, *output.parents)), 'NO_OVERWRITE_OR_SYMLINK_OUTPUT')
    report = verify_bundle(args.bundle, args.manifest_sha256)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
    print(canonical({'status': report['status'], 'output': str(output),
                     'native_execution_independently_proved': False}))
    if report['status'] == 'ARCHIVE_AND_SAME_CALL_ARITHMETIC_REPLAY_CONSISTENT':
        return 0
    return 3 if report['status'].startswith(('BLOCKED', 'INPUT_INCOMPLETE')) else 4


if __name__ == '__main__':
    raise SystemExit(main())

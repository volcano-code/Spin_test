"""Portable analytical smoke for the pinned reference and APAP Cherchi CLIs.

This module uses only the Python standard library. It executes three native
operations and independently integrates the saved binary64 triangle boundaries.
Source checks authenticate the checked source bytes, not the compilation chain;
the binary hash must also be linked to the separate CI build manifest/logs.
An analytical smoke pass grants no Teapot, exact-rational, or physics admission.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction as Q
import hashlib
import json
import math
import os
from pathlib import Path
import stat
import subprocess
import time


BASE_COMMIT = '7bd6c2697695f555f9a15d7e154e084d841316f0'
MAIN_GIT_BLOB = '3f65d2a0f83b10629f99ed5dcd2781409cdca4b5'
WRAPPER_GIT_BLOB = '3259d1c3615306c06e3ef2d29a2bcb8a8d9f59af'
BASE_BOOLEANS_GIT_BLOB = 'f60a4b4ebb0838c5b4e81541c14d6ede2f5e8b8f'
APAP_BOOLEANS_GIT_BLOB = '67ff4e7d58393fb5f15483ed12f76933353d598c'
APAP_PATCH_SHA256 = 'de6300e25eea6ec84808c7a45c78f6288c92c266f9715dd688529c681ee87b84'
# The pinned oneTBB .gitattributes prescribes CRLF checkout for these two
# Windows scripts, while their Git blobs contain LF. No compiled source gets
# this exception; raw worktree SHA256 is still included in the snapshot.
PINNED_CRLF_CHECKOUT_PATHS = frozenset((
    'arrangements/external/oneTBB/integration/windows/env/vars.bat',
    'arrangements/external/oneTBB/integration/windows/sys_check/sys_check.bat',
))
OPERATIONS = ('union', 'intersection', 'subtraction')
MOMENT_NAMES = ('1', 'x', 'y', 'z', 'x2', 'y2', 'z2', 'xy', 'yz', 'xz')
EXPONENTS = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
             (2, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0),
             (0, 1, 1), (1, 0, 1))
BOX_FACES = ((0, 2, 1), (0, 3, 2), (4, 5, 6), (4, 6, 7),
             (0, 1, 5), (0, 5, 4), (3, 7, 6), (3, 6, 2),
             (0, 4, 7), (0, 7, 3), (1, 2, 6), (1, 6, 5))
SCIENTIFIC_FLAGS = {
    'native_implicit_rational_coordinates_certified': False,
    'general_boolean_correctness_certified': False,
    'Teapot_saved_geometry_certified': False,
    'Teapot_F_D_partition_certified': False,
    'W0_physical_tip_or_FD_approved': False,
    'W2_Teapot_teacher_admission': False,
    'optimization_admitted': False,
    'training_admitted': False,
    'MuJoCo_optimized_before_after_executed': False,
    'printability_certified': False,
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode('ascii')+b'\0'+data).hexdigest()


def write_new_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def _git_bytes(source, *args):
    result = subprocess.run(['git', '-c', 'color.ui=false', '-c', 'diff.context=3',
                             '-C', str(source), *args], capture_output=True, check=False)
    if result.returncode != 0:
        raise ValueError('SOURCE_GIT_QUERY_FAILED: '+result.stderr.decode('utf-8', 'replace')[:2000])
    return result.stdout


def validate_native_identity(native_bin, upstream_checkout, mode='unmodified', wrapper=None):
    """Check the fixed base, all tracked bytes/modes, main, wrapper, and patch.

Untracked files are outside this tracked-source check. The executable's current
SHA256 is recorded, not hard-coded across compilers or CI runs. These checks do
not prove that an arbitrary executable was compiled from the checked source.
"""
    if mode not in ('unmodified', 'apap'):
        raise ValueError('UNRECOGNIZED_NATIVE_MODE')
    binary, source = Path(native_bin).resolve(), Path(upstream_checkout).resolve()
    wrapper = Path(wrapper or Path(__file__).parent/'p7_cherchi_reference_cli/CMakeLists.txt').resolve()
    if (not binary.is_file() or not os.access(binary, os.X_OK) or
            binary.name != 'w4_cherchi_reference_native'):
        raise ValueError('PINNED_NATIVE_EXECUTABLE_REQUIRED')
    if not wrapper.is_file() or git_blob(wrapper.read_bytes()) != WRAPPER_GIT_BLOB:
        raise ValueError('PINNED_CMAKE_WRAPPER_MISMATCH')
    revision = _git_bytes(source, 'rev-parse', 'HEAD').decode('ascii').strip()
    if revision != BASE_COMMIT:
        raise ValueError('PINNED_SOURCE_COMMIT_MISMATCH')
    status = _git_bytes(source, 'status', '--porcelain=v1', '--untracked-files=no').decode('utf-8')
    if mode == 'unmodified' and status.strip():
        raise ValueError('UNMODIFIED_TRACKED_SOURCE_DIRTY')
    if mode == 'apap':
        lines = status.splitlines()
        if len(lines) != 1 or lines[0][3:] != 'code/booleans.cpp':
            raise ValueError('APAP_TRACKED_CHANGE_SET_MISMATCH')
    tree = _git_bytes(source, 'ls-tree', '-r', '-z', 'HEAD')
    tracked = []
    mismatches = []
    checkout_eol_normalizations = []
    for entry in tree.split(b'\0'):
        if not entry:
            continue
        header, raw_path = entry.split(b'\t', 1)
        file_mode, kind, base_blob = header.decode('ascii').split()
        rel = raw_path.decode('utf-8')
        if kind != 'blob' or file_mode not in ('100644', '100755', '120000'):
            raise ValueError('UNSUPPORTED_TRACKED_SOURCE_ENTRY_'+rel)
        path = source/rel
        try:
            if file_mode == '120000':
                if not path.is_symlink():
                    raise ValueError('TRACKED_SOURCE_KIND_CHANGED_'+rel)
                data = os.fsencode(os.readlink(path))
            else:
                if path.is_symlink() or not path.is_file():
                    raise ValueError('TRACKED_SOURCE_KIND_CHANGED_'+rel)
                executable = bool(path.stat().st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH))
                if executable != (file_mode == '100755'):
                    raise ValueError('TRACKED_SOURCE_MODE_CHANGED_'+rel)
                data = path.read_bytes()
        except OSError as exc:
            raise ValueError('TRACKED_SOURCE_UNREADABLE_'+rel) from exc
        actual = git_blob(data)
        expected = APAP_BOOLEANS_GIT_BLOB if mode == 'apap' and rel == 'code/booleans.cpp' else base_blob
        if actual != expected and rel in PINNED_CRLF_CHECKOUT_PATHS:
            normalized = git_blob(data.replace(b'\r\n', b'\n'))
            if normalized == expected:
                actual = normalized
                checkout_eol_normalizations.append(rel)
        if actual != expected:
            mismatches.append(rel)
        tracked.append((rel, file_mode, actual, hashlib.sha256(data).hexdigest()))
    if not tracked or mismatches:
        raise ValueError('TRACKED_SOURCE_BYTES_MISMATCH:'+','.join(mismatches[:8]))
    observed = {rel: blob for rel, _, blob, _ in tracked}
    if observed.get('main.cpp') != MAIN_GIT_BLOB:
        raise ValueError('PINNED_MAIN_BLOB_MISMATCH')
    expected_cpp = APAP_BOOLEANS_GIT_BLOB if mode == 'apap' else BASE_BOOLEANS_GIT_BLOB
    if observed.get('code/booleans.cpp') != expected_cpp:
        raise ValueError('PINNED_BOOLEANS_BLOB_MISMATCH')
    diff = _git_bytes(source, 'diff', '--no-ext-diff', '--no-textconv', '--no-color',
                      '--no-renames', '--full-index', '--binary', '--src-prefix=a/',
                      '--dst-prefix=b/', 'HEAD', '--')
    patch_sha = hashlib.sha256(diff).hexdigest()
    if mode == 'unmodified' and diff:
        raise ValueError('UNMODIFIED_HEAD_DIFF_NONEMPTY')
    if mode == 'apap' and patch_sha != APAP_PATCH_SHA256:
        raise ValueError('APAP_FULL_HEAD_PATCH_SHA_MISMATCH')
    return {
        'mode': mode,
        'classification': ('UNMODIFIED_SOURCE_REFERENCE_CLI' if mode == 'unmodified'
                           else 'PATCHED_APAP_EXPORTER_NOT_UNMODIFIED_REFERENCE'),
        'source_directory': str(source), 'base_commit': revision,
        'main_git_blob': observed['main.cpp'], 'booleans_git_blob': observed['code/booleans.cpp'],
        'tracked_source_status': status, 'all_tracked_files_independently_rehashed': True,
        'tracked_file_count': len(tracked),
        'pinned_windows_script_checkout_eol_normalizations': checkout_eol_normalizations,
        'tracked_snapshot_includes_raw_worktree_sha256': True,
        'tracked_snapshot_sha256': hashlib.sha256(json.dumps(sorted(tracked), separators=(',', ':')).encode()).hexdigest(),
        'full_head_diff_sha256': patch_sha,
        'wrapper_path': str(wrapper), 'wrapper_git_blob': WRAPPER_GIT_BLOB,
        'wrapper_sha256': sha256(wrapper),
        'binary_path': str(binary), 'binary_sha256': sha256(binary),
        'source_to_binary_compilation_chain_proven_by_this_check': False,
        'build_manifest_must_bind_this_binary_sha256': True,
        'untracked_files_authenticated': False,
    }


def write_box(path, lo, hi):
    if type(lo) is not int or type(hi) is not int or lo >= hi:
        raise ValueError('SMOKE_BOX_INTEGER_BOUNDS_REQUIRED')
    vertices = ((lo, lo, lo), (hi, lo, lo), (hi, hi, lo), (lo, hi, lo),
                (lo, lo, hi), (hi, lo, hi), (hi, hi, hi), (lo, hi, hi))
    with Path(path).open('x', encoding='ascii', newline='\n') as stream:
        for vertex in vertices:
            stream.write('v %d %d %d\n' % vertex)
        for face in BOX_FACES:
            stream.write('f %d %d %d\n' % tuple(i+1 for i in face))


def read_binary64_obj(path):
    """Read the native CLI's triangular OBJ geometry without repair or welding."""
    vertices, faces = [], []
    for line_number, raw in enumerate(Path(path).read_text(encoding='utf-8').splitlines(), 1):
        words = raw.split('#', 1)[0].split()
        if not words:
            continue
        if words[0] == 'v':
            if len(words) != 4:
                raise ValueError(f'OBJ_VERTEX_ARITY_LINE_{line_number}')
            values = tuple(float(v) for v in words[1:])
            if not all(math.isfinite(v) for v in values):
                raise ValueError(f'OBJ_NONFINITE_VERTEX_LINE_{line_number}')
            vertices.append(tuple(Q.from_float(v) for v in values))
        elif words[0] == 'f':
            if len(words) != 4:
                raise ValueError(f'OBJ_NONTRIANGLE_FACE_LINE_{line_number}')
            face = []
            for value in words[1:]:
                index = int(value.split('/', 1)[0])
                if index == 0:
                    raise ValueError('OBJ_INDEX_ZERO')
                index = index-1 if index > 0 else len(vertices)+index
                if not 0 <= index < len(vertices):
                    raise ValueError('OBJ_INDEX_OUT_OF_RANGE')
                face.append(index)
            if len(set(face)) != 3:
                raise ValueError('OBJ_REPEATED_FACE_VERTEX')
            faces.append(tuple(face))
        elif words[0] not in ('vn', 'vt', 'o', 'g', 's', 'usemtl', 'mtllib'):
            raise ValueError(f'OBJ_UNSUPPORTED_RECORD_LINE_{line_number}')
    if not vertices or not faces:
        raise ValueError('OBJ_EMPTY_TRIANGLE_BOUNDARY')
    return vertices, faces


def _cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _component_count(nodes, adjacency):
    remaining, count = set(nodes), 0
    while remaining:
        count += 1
        stack = [remaining.pop()]
        while stack:
            node = stack.pop()
            for neighbor in adjacency[node]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    return count


def exact_mesh_moments(path):
    """Independent signed tetrahedron integration; all arithmetic is rational."""
    vertices, faces = read_binary64_obj(path)
    moments = [Q(0)]*10
    directed, undirected, face_supports = Counter(), Counter(), Counter()
    edge_faces = defaultdict(list)
    links = defaultdict(Counter)
    referenced = set()
    for face_index, face in enumerate(faces):
        points = [vertices[i] for i in face]
        normal = _cross(tuple(points[1][i]-points[0][i] for i in range(3)),
                        tuple(points[2][i]-points[0][i] for i in range(3)))
        if not any(normal):
            raise ValueError('OBJ_EXACT_ZERO_AREA_TRIANGLE')
        referenced.update(face)
        face_supports[tuple(sorted(face))] += 1
        for u, v in zip(face, (face[1], face[2], face[0])):
            directed[(u, v)] += 1
            key = tuple(sorted((u, v)))
            undirected[key] += 1
            edge_faces[key].append(face_index)
        for i in range(3):
            links[face[i]][tuple(sorted((face[(i+1)%3], face[(i+2)%3])))] += 1
        determinant = sum(points[0][i]*_cross(points[1], points[2])[i] for i in range(3))
        volume = determinant/6
        sums = [sum(p[i] for p in points) for i in range(3)]
        moments[0] += volume
        for axis in range(3):
            moments[1+axis] += volume*sums[axis]/4
            moments[4+axis] += volume*(sums[axis]**2+sum(p[axis]**2 for p in points))/20
        for index, (a, b) in enumerate(((0, 1), (1, 2), (0, 2)), 7):
            moments[index] += volume*(sums[a]*sums[b]+sum(p[a]*p[b] for p in points))/20
    face_adjacency = defaultdict(set)
    for group in edge_faces.values():
        for a in group:
            face_adjacency[a].update(b for b in group if b != a)
    bad_links = 0
    for link in links.values():
        adjacency = defaultdict(set)
        for a, b in link:
            adjacency[a].add(b)
            adjacency[b].add(a)
        if (any(c != 1 for c in link.values()) or any(len(v) != 2 for v in adjacency.values())
                or _component_count(adjacency, adjacency) != 1):
            bad_links += 1
    components = _component_count(range(len(faces)), face_adjacency)
    topology = {
        'vertices': len(vertices), 'faces': len(faces), 'edges': len(undirected),
        'unused_vertices': len(vertices)-len(referenced),
        'closed_edge_incidence_two': all(c == 2 for c in undirected.values()),
        'opposite_directed_edge_incidence_one': all(directed[(a, b)] == directed[(b, a)] == 1 for a, b in undirected),
        'duplicate_indexed_face_supports': sum(c-1 for c in face_supports.values()),
        'noncycle_vertex_links': bad_links, 'face_connected_components': components,
        'euler_characteristic': len(referenced)-len(undirected)+len(faces),
        'all_triangle_areas_exactly_nonzero': True,
        'positive_exact_signed_volume': moments[0] > 0,
        'geometric_self_intersection_audit_performed': False,
    }
    topology['analytical_box_boundary_topology_pass'] = bool(
        topology['closed_edge_incidence_two'] and topology['opposite_directed_edge_incidence_one']
        and topology['unused_vertices'] == 0 and topology['duplicate_indexed_face_supports'] == 0
        and bad_links == 0 and components == 1 and topology['euler_characteristic'] == 2
        and moments[0] > 0)
    return moments, topology


def box_moments(lo, hi):
    """Cartesian product integral, independent of triangle integration."""
    lo, hi = Q(lo), Q(hi)
    if lo >= hi:
        raise ValueError('ANALYTICAL_BOX_BOUNDS')
    result = []
    for powers in EXPONENTS:
        value = Q(1)
        for power in powers:
            value *= (hi**(power+1)-lo**(power+1))/(power+1)
        result.append(value)
    return result


def expected_boolean_moments():
    a, b, intersection = box_moments(0, 2), box_moments(1, 3), box_moments(1, 2)
    return {'union': [x+y-z for x, y, z in zip(a, b, intersection)],
            'intersection': intersection,
            'subtraction': [x-z for x, z in zip(a, intersection)]}


def _moments_json(values):
    return dict(zip(MOMENT_NAMES, map(str, values)))


def _require_frozen(expected):
    for path, digest in expected.items():
        if path.is_symlink() or not path.is_file() or sha256(path) != digest:
            raise ValueError('FROZEN_SMOKE_ARTIFACT_CHANGED_'+path.name)


def native_operation(binary, operation, operands, output, *, expected_binary_sha256,
                     expected_input_sha256, timeout=60):
    """Execute an allowlisted two-input operation, retaining failed receipts."""
    if (operation not in OPERATIONS or type(timeout) is not int or not 0 < timeout <= 120
            or len(operands) != 2 or len(expected_input_sha256) != 2):
        raise ValueError('UNREGISTERED_SMOKE_OPERATION_OR_ARGUMENTS')
    binary, output = Path(binary).resolve(), Path(output).resolve()
    operands = [Path(p).resolve() for p in operands]
    receipt = Path(str(output)+'.native.json')
    stdout_path, stderr_path = Path(str(output)+'.stdout.log'), Path(str(output)+'.stderr.log')
    if any(p.exists() or p.is_symlink() for p in (output, receipt, stdout_path, stderr_path)):
        raise ValueError('REFUSE_TO_OVERWRITE_SMOKE_OPERATION_EVIDENCE')
    expected = {binary: expected_binary_sha256, **dict(zip(operands, expected_input_sha256))}
    _require_frozen(expected)
    command = [str(binary), operation, *map(str, operands), str(output)]
    record = {'operation': operation, 'command': command, 'input_sha256': list(expected_input_sha256),
              'binary_sha256': expected_binary_sha256, 'timeout_seconds': timeout,
              'output_file': output.name, 'new_native_process_launched': False, 'returncode': None}
    start = time.monotonic()
    stdout, stderr = b'', b''
    try:
        completed = subprocess.run(command, capture_output=True, check=False, timeout=timeout,
            env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'})
        record.update(new_native_process_launched=True, returncode=completed.returncode,
                      process_status='EXITED')
        stdout, stderr = completed.stdout, completed.stderr
    except subprocess.TimeoutExpired as exc:
        record.update(new_native_process_launched=True, process_status='NATIVE_TIMEOUT')
        stdout, stderr = exc.stdout or b'', exc.stderr or b''
    except OSError as exc:
        record.update(process_status='NATIVE_NOT_LAUNCHED', launch_error=f'{type(exc).__name__}: {exc}')
    record['wall_seconds'] = time.monotonic()-start
    for path, data in ((stdout_path, stdout), (stderr_path, stderr)):
        with path.open('xb') as stream:
            stream.write(data.encode('utf-8') if isinstance(data, str) else data)
    after_inputs = [sha256(p) if p.is_file() and not p.is_symlink() else None for p in operands]
    after_binary = sha256(binary) if binary.is_file() and not binary.is_symlink() else None
    record.update(input_sha256_after=after_inputs, binary_sha256_after=after_binary,
                  inputs_unchanged=after_inputs == list(expected_input_sha256),
                  binary_unchanged=after_binary == expected_binary_sha256,
                  output_exists=output.is_file() and not output.is_symlink(),
                  stdout_file=stdout_path.name, stdout_sha256=sha256(stdout_path),
                  stderr_file=stderr_path.name, stderr_sha256=sha256(stderr_path))
    if record['output_exists']:
        record['output_sha256'] = sha256(output)
    record['process_output_ready_for_independent_audit'] = bool(
        record['new_native_process_launched'] and record['returncode'] == 0
        and record['output_exists'] and record['inputs_unchanged'] and record['binary_unchanged'])
    write_new_json(receipt, record)
    return record


def run_smoke(native_bin, upstream_checkout, mode, out, *, wrapper=None, timeout=60):
    if type(timeout) is not int or not 0 < timeout <= 120:
        raise ValueError('SMOKE_TIMEOUT_OUT_OF_BOUNDS')
    out = Path(out).resolve()
    if out.exists():
        raise FileExistsError('REFUSE_TO_OVERWRITE_SMOKE_DIRECTORY')
    identity = validate_native_identity(native_bin, upstream_checkout, mode, wrapper)
    binary = Path(identity['binary_path'])
    out.mkdir(parents=True, exist_ok=False)
    a, b = out/'box_A_0_2.obj', out/'box_B_1_3.obj'
    write_box(a, 0, 2)
    write_box(b, 1, 3)
    expected_moments = expected_boolean_moments()
    plan = {'schema': 'W4P19RegisteredAnalyticalNativeSmokeV1', 'mode': mode,
            'operations': list(OPERATIONS), 'timeout_seconds_per_call': timeout,
            'analytical_case': 'A=[0,2]^3; B=[1,3]^3; intersection=[1,2]^3',
            'moment_order': list(MOMENT_NAMES),
            'expected_moments': {op: _moments_json(v) for op, v in expected_moments.items()},
            'native_identity': identity, 'scientific_flags': dict(SCIENTIFIC_FLAGS)}
    plan_path = out/'registered-smoke-plan.json'
    write_new_json(plan_path, plan)
    frozen = {binary: identity['binary_sha256'], Path(identity['wrapper_path']): identity['wrapper_sha256'],
              a: sha256(a), b: sha256(b), plan_path: sha256(plan_path)}
    report = {'schema': 'W4P19PortableAnalyticalNativeSmokeV1', 'status': 'RUNNING', 'passed': False,
              'native_identity': identity, 'registered_plan_sha256': sha256(plan_path),
              'analytical_case': plan['analytical_case'], 'moment_order': list(MOMENT_NAMES),
              'inputs': [{'file': p.name, 'sha256': frozen[p]} for p in (a, b)],
              'coordinate_semantics': 'Exact Fraction.from_float of saved OBJ binary64 coordinates',
              'coordinate_tolerance': None, 'mesh_repair_or_welding_performed': False,
              'checks': [], 'native_operation_calls': 0, 'attempted_operations': 0,
              'exact_moment_comparisons': 0, 'exact_moment_comparisons_equal': 0,
              'required_native_operation_calls': 3, 'required_exact_moment_comparisons': 30,
              'scientific_flags': dict(SCIENTIFIC_FLAGS),
              'scope': 'Analytical boxes only; no general set equality, geometric embeddedness, implicit-rational export, Teapot, physics, teacher, optimization, or training admission.'}
    journal = out/'smoke-journal.json'
    def checkpoint():
        journal.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    checkpoint()
    try:
        for path, analytic in ((a, box_moments(0, 2)), (b, box_moments(1, 3))):
            actual, topology = exact_mesh_moments(path)
            if actual != analytic or not topology['analytical_box_boundary_topology_pass']:
                raise ValueError('GENERATED_ANALYTICAL_INPUT_INVALID')
        for operation in OPERATIONS:
            _require_frozen(frozen)
            output = out/(operation+'.obj')
            call = native_operation(binary, operation, [a, b], output,
                                    expected_binary_sha256=identity['binary_sha256'],
                                    expected_input_sha256=[frozen[a], frozen[b]], timeout=timeout)
            item = dict(call, passed=False, expected_exact_moments=_moments_json(expected_moments[operation]))
            report['checks'].append(item)
            report['attempted_operations'] += 1
            report['native_operation_calls'] += int(call['new_native_process_launched'])
            if call['output_exists']:
                frozen[output] = call['output_sha256']
            for suffix in ('.native.json', '.stdout.log', '.stderr.log'):
                path = Path(str(output)+suffix)
                frozen[path] = sha256(path)
            checkpoint()
            if not call['inputs_unchanged'] or not call['binary_unchanged']:
                raise ValueError('NATIVE_CALL_MUTATED_FROZEN_SMOKE_INPUT_OR_BINARY')
            if call['process_output_ready_for_independent_audit']:
                try:
                    actual, topology = exact_mesh_moments(output)
                    wanted = expected_moments[operation]
                    comparisons = {name: x == y for name, x, y in zip(MOMENT_NAMES, actual, wanted)}
                    item.update(topology=topology, actual_saved_binary64_exact_moments=_moments_json(actual),
                                residual_exact_moments=_moments_json([x-y for x, y in zip(actual, wanted)]),
                                exact_comparisons=comparisons, all_ten_moments_exactly_equal=all(comparisons.values()),
                                passed=all(comparisons.values()) and topology['analytical_box_boundary_topology_pass'])
                    report['exact_moment_comparisons'] += 10
                    report['exact_moment_comparisons_equal'] += sum(comparisons.values())
                except (ValueError, OSError, UnicodeError) as exc:
                    item['saved_output_error'] = f'{type(exc).__name__}: {exc}'
            _require_frozen(frozen)
            checkpoint()
            if not call['new_native_process_launched']:
                break
        _require_frozen(frozen)
        after_identity = validate_native_identity(native_bin, upstream_checkout, mode, wrapper)
        if after_identity != identity:
            raise ValueError('NATIVE_SOURCE_IDENTITY_CHANGED_DURING_SMOKE')
        report['native_identity_unchanged'] = True
        report['all_frozen_artifacts_unchanged'] = True
        report['passed'] = bool(report['native_operation_calls'] == 3 and len(report['checks']) == 3
                                and report['exact_moment_comparisons'] == 30
                                and report['exact_moment_comparisons_equal'] == 30
                                and all(item['passed'] for item in report['checks']))
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        report.update(passed=False, fatal_error=f'{type(exc).__name__}: {exc}', all_frozen_artifacts_unchanged=False)
    report['status'] = 'ANALYTICAL_NATIVE_SMOKE_PASS' if report['passed'] else 'ANALYTICAL_NATIVE_SMOKE_REJECTED'
    checkpoint()
    write_new_json(out/'analytical-smoke-report.json', report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-bin', type=Path, required=True)
    parser.add_argument('--upstream-checkout', type=Path, required=True)
    parser.add_argument('--mode', choices=('unmodified', 'apap'), required=True)
    parser.add_argument('--wrapper', type=Path, default=None,
                        help='Pinned P7 CMakeLists.txt; defaults to the sibling p7_cherchi_reference_cli directory')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=60)
    args = parser.parse_args(argv)
    result = run_smoke(args.native_bin, args.upstream_checkout, args.mode, args.out,
                       wrapper=args.wrapper, timeout=args.timeout)
    print(json.dumps({key: result[key] for key in ('status', 'native_operation_calls',
          'exact_moment_comparisons', 'exact_moment_comparisons_equal', 'passed')}, indent=2))
    return 0 if result['passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())

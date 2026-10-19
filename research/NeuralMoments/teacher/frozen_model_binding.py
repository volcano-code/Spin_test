"""W2: strict OBJ -> frozen Faster outer-request coordinate correspondence.

This is an exact binary64 array correspondence audit, NOT a proof that a
triangle mesh is an embedded solid or that an OBJ faithfully represents CAD.
Output face and vertex indexing must match the frozen request without repair.
"""
from collections import Counter
import hashlib
import math
from pathlib import Path
import numpy as np

ALLOWED_MODES = (
    'OBJ_IS_INPUT_NORMALIZED_OUTER_V1',
    'OBJ_PHYSICAL_TO_INPUT_NORMALIZED_OUTER_V1',
)
_IGNORABLE = {'vt', 'vn', 'vp', 'o', 'g', 's', 'usemtl', 'mtllib'}


def _read_obj(path):
    """Parse only static indexed triangles, rejecting unrecognized geometry."""
    if Path(path).suffix.lower() != '.obj':
        raise ValueError('ONLY_FROZEN_OBJ_SUPPORTED')
    vertices, faces = [], []
    with Path(path).open('r', encoding='utf-8-sig') as stream:
        for number, raw in enumerate(stream, 1):
            line = raw.partition('#')[0].strip()
            if not line:
                continue
            items = line.split()
            tag, tokens = items[0], items[1:]
            if tag == 'v':
                if len(tokens) != 3:
                    raise ValueError(f'OBJ_VERTEX_NOT_XYZ:{number}')
                try:
                    row = tuple(float(token) for token in tokens)
                except ValueError as exc:
                    raise ValueError(f'OBJ_INVALID_VERTEX:{number}') from exc
                if not all(math.isfinite(x) for x in row):
                    raise ValueError(f'OBJ_NONFINITE_VERTEX:{number}')
                vertices.append(row)
            elif tag == 'f':
                if len(tokens) != 3:
                    raise ValueError(f'OBJ_NOT_TRIANGULATED:{number}')
                row = []
                for token in tokens:
                    fields = token.split('/')
                    if not fields[0].isdigit() or fields[0] == '0':
                        raise ValueError(f'OBJ_RELATIVE_OR_INVALID_FACE_INDEX:{number}')
                    index = int(fields[0]) - 1
                    if index >= len(vertices):
                        raise ValueError(f'OBJ_FORWARD_OR_INVALID_FACE_INDEX:{number}')
                    row.append(index)
                if len(set(row)) != 3:
                    raise ValueError(f'OBJ_DEGENERATE_FACE_INDEX:{number}')
                faces.append(tuple(row))
            elif tag not in _IGNORABLE:
                raise ValueError(f'OBJ_UNSUPPORTED_GEOMETRY_RECORD:{tag}:{number}')
    if len(vertices) < 4 or len(faces) < 4:
        raise ValueError('OBJ_INCOMPLETE_TRIANGLE_SHELL')
    return np.asarray(vertices, dtype='<f8'), np.asarray(faces, dtype='<i4')


def _closed_oriented_faces(faces):
    """Necessary oriented two-manifold test, not an embedding certificate."""
    edges = Counter()
    unordered = Counter()
    triangles = set()
    for a, b, c in faces.tolist():
        tri = tuple(sorted((a, b, c)))
        if tri in triangles:
            raise ValueError('OBJ_DUPLICATE_TRIANGLE')
        triangles.add(tri)
        for x, y in ((a, b), (b, c), (c, a)):
            edges[x, y] += 1
            unordered[min(x, y), max(x, y)] += 1
    if any(count != 2 or edges[a, b] != 1 or edges[b, a] != 1
           for (a, b), count in unordered.items()):
        raise ValueError('OBJ_OPEN_NONMANIFOLD_OR_WINDING_MISMATCH')


def _native_array(data, shape_tail, dtype, label):
    try:
        array = np.asarray(data, dtype=dtype)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('INVALID_REQUEST_'+label) from exc
    if array.ndim != 2 or array.shape[1] != shape_tail or not len(array):
        raise ValueError('INVALID_REQUEST_'+label+'_SHAPE')
    # Refuse coercing malformed floating indices or booleans into integer faces.
    if dtype == '<i4':
        if (not isinstance(data,(list,tuple)) or
            any(not isinstance(row,(list,tuple)) or
                any(type(value) is not int for value in row) for row in data)):
            raise ValueError('INVALID_REQUEST_'+label+'_INTEGER_INDICES_REQUIRED')
    if dtype == '<f8' and not np.isfinite(array).all():
        raise ValueError('INVALID_REQUEST_'+label+'_NONFINITE')
    return array


def validate_model_binding(model_path, request, binding, normalization=None):
    """Return verified byte-exact input-outer correspondence or fail closed.

    For physical OBJ coordinates, reproduce the frozen Faster normalization
    (physical_vertices - origin) / length using NumPy binary64 operations.
    It is deliberate to require original indexing, face order and orientation;
    canonicalizing/reordering would mask a broken provenance chain.
    """
    if not isinstance(binding, dict) or set(binding) != {'mode'}:
        raise ValueError('MODEL_BINDING_MODE_REQUIRED')
    mode = binding['mode']
    if mode not in ALLOWED_MODES:
        raise ValueError('UNSUPPORTED_MODEL_BINDING_MODE')
    if not isinstance(request, dict):
        raise ValueError('MISSING_FROZEN_NATIVE_REQUEST')
    obj_v, obj_f = _read_obj(model_path)
    expected_v = _native_array(request.get('outer_vertices'), 3, '<f8', 'OUTER_VERTICES')
    expected_f = _native_array(request.get('outer_faces'), 3, '<i4', 'OUTER_FACES')
    if obj_v.shape != expected_v.shape or obj_f.shape != expected_f.shape:
        raise ValueError('MODEL_REQUEST_TOPOLOGY_OR_VERTEX_COUNT_MISMATCH')
    if mode == 'OBJ_PHYSICAL_TO_INPUT_NORMALIZED_OUTER_V1':
        if not isinstance(normalization, dict):
            raise ValueError('MODEL_NORMALIZATION_REQUIRED')
        origin = np.asarray(normalization.get('origin'), dtype='<f8')
        length = float(normalization.get('L'))
        if origin.shape != (3,) or not np.isfinite(origin).all() or not math.isfinite(length) or length <= 0:
            raise ValueError('INVALID_FROZEN_NORMALIZATION')
        actual_scale = float(request.get('original_units_per_normalized_unit', 1.0))
        if actual_scale != length:
            raise ValueError('REQUEST_NORMALIZATION_LENGTH_MISMATCH')
        model_v = (obj_v - origin) / length
    else:
        model_v = obj_v
    if not np.isfinite(model_v).all() or model_v.tobytes() != expected_v.tobytes():
        raise ValueError('MODEL_REQUEST_OUTER_VERTEX_BYTES_MISMATCH')
    if obj_f.tobytes() != expected_f.tobytes():
        raise ValueError('MODEL_REQUEST_OUTER_FACE_BYTES_MISMATCH')
    _closed_oriented_faces(obj_f)
    return {
        'schema': 'w2-obj-faster-outer-correspondence-v1',
        'status': 'EXACT_BINARY64_ORDERED_OUTER_MESH_MATCH',
        'mode': mode,
        'vertex_count': len(obj_v),
        'face_count': len(obj_f),
        'model_file_sha256': hashlib.sha256(Path(model_path).read_bytes()).hexdigest(),
        'frozen_outer_vertices_bytes_sha256': hashlib.sha256(expected_v.tobytes()).hexdigest(),
        'frozen_outer_faces_bytes_sha256': hashlib.sha256(expected_f.tobytes()).hexdigest(),
        'limitations': 'No exact embedding/self-intersection, original CAD, fixed/design mesh or neighborhood proof',
    }

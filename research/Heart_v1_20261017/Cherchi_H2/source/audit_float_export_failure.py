"""Read-only forensic classifier for Cherchi's exact-vs-rounded triangle mesh.

This makes NO topological edits, never invokes CGAL as a production Boolean,
and cannot grant a qualified OBJ export. It intentionally analyzes the
already-recorded native audit instead of inventing intersection certificates.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np


def audit(exact_path, native_float_audit_path, native_exact_audit_path):
    exact_path, native_float_audit_path, native_exact_audit_path = map(Path, (exact_path, native_float_audit_path, native_exact_audit_path))
    material = json.loads(exact_path.read_text())
    binary = json.loads(native_float_audit_path.read_text())
    rational = json.loads(native_exact_audit_path.read_text())
    vertices = np.asarray(material['vertices'], dtype=np.float64)
    faces = np.asarray(material['faces'], dtype=np.int64)
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError('INVALID_MATERIAL_VERTICES')
    if faces.ndim != 2 or faces.shape[1] != 3 or len(faces) == 0 or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError('INVALID_MATERIAL_FACES')
    if len(material['exact_vertices']) != len(vertices):
        raise ValueError('INCOMPLETE_EXACT_COORDINATES')
    if not rational.get('boundary_valid') or not rational.get('self_intersection_free'):
        raise ValueError('RATIONAL_INPUT_NOT_ADMITTED')
    if binary.get('boundary_valid') or binary.get('self_intersection_free'):
        raise ValueError('NO_BINARY64_FAILURE_TO_CLASSIFY')
    pairs = binary.get('intersecting_pairs')
    if not isinstance(pairs, list) or not pairs:
        raise ValueError('MISSING_NATIVE_FAILURE_WITNESSES')
    if len(pairs) != binary.get('intersecting_pair_count'):
        raise ValueError('NATIVE_PAIR_COUNT_MISMATCH')
    involved = Counter()
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2 or not all(isinstance(i, int) and 0 <= i < len(faces) for i in pair):
            raise ValueError('INVALID_NATIVE_INTERSECTION_PAIR')
        for index in pair:
            involved[index] += 1
    triangles = vertices[faces]
    doubled = np.linalg.norm(np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0]), axis=1)
    areas = doubled / 2
    lengths = np.stack([np.linalg.norm(triangles[:, (i+1)%3] - triangles[:, i], axis=1) for i in range(3)], axis=1)
    shape = doubled / np.maximum(np.max(lengths, axis=1)**2, np.finfo(float).tiny)
    touched = np.array(sorted(involved), dtype=int)
    report = {
      'schema': 'heart-cherchi-h2-binary64-failure-diagnosis-v1',
      'input_sha256': {str(p.name): hashlib.sha256(p.read_bytes()).hexdigest() for p in (exact_path, native_float_audit_path, native_exact_audit_path)},
      'scope': 'READ_ONLY_RECORDED_CHERCHI_OUTPUT_NOT_AUTHOR_HEART_NOT_EVAL60',
      'input_vertex_count': int(len(vertices)),
      'input_face_count': int(len(faces)),
      'rational_boundary_valid': True,
      'float_boundary_valid': False,
      'float_intersecting_pairs': len(pairs),
      'involved_face_count': len(touched),
      'min_binary64_triangle_area_model_units_squared': float(areas.min()),
      'min_involved_triangle_area_model_units_squared': float(areas[touched].min()),
      'min_involved_shape_double_area_over_max_edge_squared': float(shape[touched].min()),
      'faces_below_area_1e_minus_15': int(np.sum(areas < 1e-15)),
      'intersecting_faces_below_area_1e_minus_15': int(np.sum(areas[touched] < 1e-15)),
      'most_frequently_involved_faces': [dict(face_index=int(i), native_pair_count=int(n), area_model_units_squared=float(areas[i]), triangle_indices=faces[i].tolist()) for i,n in involved.most_common(20)],
      'exact_retriangulation_authorized': False,
      'vertex_move_authorized': False,
      'triangle_deletion_authorized': False,
      'qualified_binary64_obj': False,
      'native_reaudit_required': True,
      'final_material_set_equality_after_repair_verified': False,
    }
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--material', required=True, type=Path)
    p.add_argument('--binary-audit', required=True, type=Path)
    p.add_argument('--rational-audit', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    args = p.parse_args()
    report = audit(args.material, args.binary_audit, args.rational_audit)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    print(json.dumps({'input_face_count': report['input_face_count'], 'float_intersecting_pairs': report['float_intersecting_pairs'], 'involved_face_count': report['involved_face_count'], 'qualified_binary64_obj': False}))

if __name__ == '__main__':
    main()

"""Independent finite-precision triangle SAT preflight for W4 P2.

Broad phase: deterministic x-axis sweep and AABB pruning.
Narrow phase: normals, edge-edge crosses and in-plane separating axes.
This is *not* an exact arithmetic CGAL certificate. Nonincident contacts
(including coplanar/edge touches) are treated as failures conservatively.
"""
from __future__ import annotations
import numpy as np


def triangle_contacts_one_to_many(a: np.ndarray, others: np.ndarray,
                                  tol: float = 1e-11) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(others, dtype=np.float64)
    if a.shape != (3, 3) or b.ndim != 3 or b.shape[1:] != (3, 3):
        raise ValueError('INVALID_TRIANGLE_SHAPE')
    if not len(b):
        return np.empty((0,), dtype=bool)
    ea = np.roll(a, -1, axis=0) - a
    eb = np.roll(b, -1, axis=1) - b
    na = np.cross(ea[0], ea[1])
    nb = np.cross(eb[:, 0, :], eb[:, 1, :])
    axes = np.concatenate((
        np.broadcast_to(na, (len(b), 1, 3)),
        nb[:, None, :],
        np.cross(ea[None, :, None, :], eb[:, None, :, :]).reshape(-1, 9, 3),
        np.cross(np.broadcast_to(na, (len(b), 1, 3)), eb),
        np.cross(nb[:, None, :], np.broadcast_to(ea, (len(b), 3, 3))),
    ), axis=1)
    norms = np.linalg.norm(axes, axis=2)
    proj_a = np.einsum('kjd,id->kji', axes, a)
    proj_b = np.einsum('kjd,kid->kji', axes, b)
    separated = ((proj_a.max(axis=2) < proj_b.min(axis=2) - tol * norms) |
                 (proj_b.max(axis=2) < proj_a.min(axis=2) - tol * norms)) & (norms > 1e-17)
    return ~np.any(separated, axis=1)


def check_nonincident_triangle_contacts(vertices: np.ndarray, faces: np.ndarray,
                                        tol: float = 1e-11, max_witnesses: int = 32) -> dict:
    vertices = np.asarray(vertices, dtype=np.float64)
    faces = np.asarray(faces, dtype=np.int64)
    if len(faces) == 0 or faces.ndim != 2 or faces.shape[1] != 3:
        raise ValueError('INVALID_FACES')
    if not np.isfinite(vertices).all() or faces.min() < 0 or faces.max() >= len(vertices):
        raise ValueError('INVALID_GEOMETRY')
    triangle = vertices[faces]
    lo = triangle.min(axis=1)
    hi = triangle.max(axis=1)
    order = np.argsort(lo[:, 0], kind='stable')
    sort_lo = lo[order, 0]
    contacts = []
    broadphase_pairs = 0
    adjacent_excluded = 0
    for sorted_position, index in enumerate(order):
        i = int(index)
        end = int(np.searchsorted(sort_lo, hi[i, 0] + tol, side='right'))
        if end <= sorted_position + 1:
            continue
        js = order[sorted_position + 1:end]
        good = ((lo[js, 1] <= hi[i, 1] + tol) & (lo[js, 2] <= hi[i, 2] + tol) &
                (hi[js, 1] >= lo[i, 1] - tol) & (hi[js, 2] >= lo[i, 2] - tol))
        js = js[good]
        if len(js) == 0:
            continue
        shared_vertex = np.any(np.any(faces[js, :, None] == faces[i, None, :], axis=2), axis=1)
        adjacent_excluded += int(shared_vertex.sum())
        js = js[~shared_vertex]
        if len(js) == 0:
            continue
        broadphase_pairs += len(js)
        colliding = triangle_contacts_one_to_many(triangle[i], triangle[js], tol)
        for j in js[colliding]:
            contacts.append([i, int(j)])
            if len(contacts) >= max_witnesses:
                return dict(method='FLOAT64_SAT_NONINCIDENT_V1', witnesses=contacts,
                            evaluated_nonincident_aabb_pairs=broadphase_pairs,
                            excluded_incident_pairs=adjacent_excluded,
                            exhaustive=False, tolerance=tol)
    return dict(method='FLOAT64_SAT_NONINCIDENT_V1', witnesses=contacts,
                evaluated_nonincident_aabb_pairs=broadphase_pairs,
                excluded_incident_pairs=adjacent_excluded,
                exhaustive=True, tolerance=tol)

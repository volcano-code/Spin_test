"""M3 closed-triangle-mesh geometry encoder input, never a Cherchi label.

This computes raw moments of the *input closed triangle mesh* by oriented
signed tetrahedra. It does not certify self-intersection, nesting, exact CAD,
Boolean cuts, or material Jacobians. Files are bound by their byte SHA-256.
W0 physical-to-normalized frame is applied explicitly; no re-normalization of c.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path

import numpy as np
import torch

MESH_FEATURE_DIM = 24


@dataclass(frozen=True)
class MeshFeatures:
    geometry: np.ndarray  # 24 deterministic dimensionless scalar features
    normalized_moments: np.ndarray  # ten undoubled W0 raw moments
    original_moments: np.ndarray  # physical-coordinate W0 raw moments
    source_sha256: str  # exact file bytes for OBJ, canonical arrays otherwise
    vertices: int
    faces: int
    material_certified: bool = False


def _raw_from_tetrahedra(vertices: np.ndarray, faces: np.ndarray, density: float) -> tuple[np.ndarray, float]:
    """Integrate [1,x,y,z,xx,yy,zz,yz,xz,xy] on oriented triangle shell."""
    origin = vertices.mean(axis=0)
    tri = vertices[faces] - origin
    a, b, c = tri[:, 0, :], tri[:, 1, :], tri[:, 2, :]
    vol = np.einsum('ij,ij->i', a, np.cross(b, c)) / 6.0
    volume = float(vol.sum())
    area = float(np.linalg.norm(np.cross(b-a, c-a), axis=1).sum() / 2.0)
    scale = float(np.prod(np.maximum(vertices.max(axis=0)-vertices.min(axis=0), 1e-15)))
    if not math.isfinite(volume) or volume <= 1e-12 * scale:
        raise ValueError('nonpositive or near-zero oriented solid volume')
    local_L = np.einsum('f,fi->i', vol / 4.0, a+b+c)
    s = a+b+c
    second = np.einsum('f,fi,fj->ij', vol / 20.0, s, s)
    for x in (a, b, c):
        second += np.einsum('f,fi,fj->ij', vol / 20.0, x, x)
    first = local_L + volume * origin
    Q = second + np.outer(local_L, origin) + np.outer(origin, local_L) + volume*np.outer(origin, origin)
    raw = density * np.array([volume, *first, Q[0,0], Q[1,1], Q[2,2], Q[1,2], Q[0,2], Q[0,1]])
    return raw, area


def mesh_features(vertices, faces, *, density: float = 1.0,
                  length_original_per_normalized: float = 1.0,
                  density_original_per_normalized: float = 1.0,
                  origin_original=(0., 0., 0.),
                  source_sha256: str | None = None) -> MeshFeatures:
    v, f = np.asarray(vertices, dtype=np.float64), np.asarray(faces)
    if v.ndim != 2 or v.shape[1] != 3 or len(v) < 4 or not np.isfinite(v).all():
        raise ValueError('finite mesh vertices [N,3] with N>=4 required')
    if f.ndim != 2 or f.shape[1] != 3 or len(f) < 4 or f.dtype.kind not in 'iu':
        raise ValueError('integer triangular faces [F,3] required')
    f = f.astype(np.int64)
    if (f < 0).any() or (f >= len(v)).any() or np.any(np.diff(np.sort(f, axis=1), axis=1) == 0):
        raise ValueError('invalid or degenerate face indices')
    if len(np.unique(f)) != len(v):
        raise ValueError('unreferenced mesh vertices forbidden')
    edges: dict[tuple[int,int], list[int]] = {}
    for x, y, z in f:
        for a, b in ((x, y), (y, z), (z, x)):
            key = (min(a,b), max(a,b))
            edges.setdefault(key, []).append(1 if a < b else -1)
    if not all(len(directions) == 2 and sum(directions) == 0 for directions in edges.values()):
        raise ValueError('open/nonmanifold or inconsistent face orientation')
    rho, L, rho_ref = map(float, (density, length_original_per_normalized, density_original_per_normalized))
    origin = np.asarray(origin_original, dtype=np.float64)
    if not all(math.isfinite(x) and x > 0 for x in (rho,L,rho_ref)) or origin.shape != (3,) or not np.isfinite(origin).all():
        raise ValueError('invalid W0 length, origin or density reference')
    normalized_vertices = (v - origin) / L
    normalized_r, area = _raw_from_tetrahedra(normalized_vertices, f, rho/rho_ref)
    raw, _ = _raw_from_tetrahedra(v, f, rho)
    mass = normalized_r[0]
    center = normalized_r[1:4] / mass
    Q = np.array([[normalized_r[4],normalized_r[9],normalized_r[8]],
                  [normalized_r[9],normalized_r[5],normalized_r[7]],
                  [normalized_r[8],normalized_r[7],normalized_r[6]]])
    covariance = Q / mass - np.outer(center, center)
    covariance = (covariance+covariance.T)/2
    span = np.ptp(normalized_vertices, axis=0)
    features = np.array([*normalized_r, *center,
        covariance[0,0], covariance[1,1], covariance[2,2],
        covariance[1,2], covariance[0,2], covariance[0,1],
        *span, area, math.log(rho/rho_ref)])
    if features.shape != (MESH_FEATURE_DIM,) or not np.isfinite(features).all():
        raise ValueError('nonfinite mesh descriptor')
    if source_sha256 is None:
        source_sha256 = hashlib.sha256(v.astype('<f8').tobytes()+f.astype('<i8').tobytes()).hexdigest()
    if (not isinstance(source_sha256, str) or len(source_sha256) != 64
            or any(ch not in '0123456789abcdef' for ch in source_sha256)):
        raise ValueError('invalid mesh source sha256')
    return MeshFeatures(features, normalized_r, raw, source_sha256, len(v), len(f))


def read_obj_features(path: str | Path, **frame) -> MeshFeatures:
    """Only explicit triangular OBJ surface, read without a CAD/Boolean claim."""
    data = Path(path).read_bytes()
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for line in data.decode('utf-8').splitlines():
        fields = line.strip().split()
        if not fields or fields[0].startswith('#'):
            continue
        if fields[0] == 'v':
            if len(fields) != 4:
                raise ValueError('only three-coordinate OBJ vertices supported')
            vertices.append([float(x) for x in fields[1:]])
        if fields[0] == 'f':
            if len(fields) != 4:
                raise ValueError('nontriangular OBJ face: triangulation needed upstream')
            row: list[int] = []
            for token in fields[1:]:
                idx = int(token.split('/')[0])
                if idx == 0:
                    raise ValueError('OBJ zero vertex index')
                row.append(idx - 1 if idx > 0 else len(vertices) + idx)
            faces.append(row)
    return mesh_features(vertices, np.asarray(faces, dtype=np.int64),
                         source_sha256=hashlib.sha256(data).hexdigest(), **frame)


def cached_mesh_geometry(model, descriptor: MeshFeatures, *, dtype=torch.float32) -> torch.Tensor:
    if getattr(model, 'geometry_dim', None) != MESH_FEATURE_DIM:
        raise ValueError('instantiate W5 model with geometry_dim=24 for mesh input')
    device = next(model.parameters()).device
    values = torch.as_tensor(descriptor.geometry, dtype=dtype, device=device)
    if values.dtype != next(model.parameters()).dtype:
        raise ValueError('geometry feature dtype must match model dtype')
    return model.encode_geometry(values)

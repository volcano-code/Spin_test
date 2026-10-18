"""W0-aligned closed-form P0 *cut* moments, not W2 Cherchi observations.

The retained region is D intersected with beta_c(x)>=0, where
beta_c(x)=c0+c1*x+...+2*c7*yz+2*c8*xz+2*c9*xy (native C++ order).
Only vertical plane c=(-h_world,0,0,1,0,...)/||.|| is supported here;
the *ambient* 10x10 Jacobian at that plane is exact for continuum interior
cuts of closed boxes, spheres and axis-aligned ellipsoids. The exact labels
refer to analytic solids, NOT to the 8^3 voxel approximation of their geometry.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Iterable

import numpy as np
import torch
from torch import Tensor

# Must agree with W0 NATIVE_C_ORDER and RAW_R_ORDER.
POWERS = ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1),
          (2, 0, 0), (0, 2, 0), (0, 0, 2), (0, 1, 1),
          (1, 0, 1), (1, 1, 0))
B_NATIVE_TO_MONOMIAL = np.diag([1.0] * 7 + [2.0] * 3)
TEACHER_KIND = "ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI"


@dataclass(frozen=True)
class GeometrySpec:
    family: str
    center: tuple[float, float, float]
    axes: tuple[float, float, float]
    density: float = 1.0

    def __post_init__(self) -> None:
        if self.family not in ("box", "sphere", "ellipsoid"):
            raise ValueError("unsupported analytic family")
        if len(self.center) != 3 or len(self.axes) != 3 or not all(
            math.isfinite(float(x)) for x in (*self.center, *self.axes, self.density)
        ) or min(self.axes) <= 0 or self.density <= 0:
            raise ValueError("finite center, positive semiaxes and density required")
        if self.family == "sphere" and max(self.axes) - min(self.axes) > 1e-12:
            raise ValueError("sphere axes must be equal")

    @property
    def geometry_id(self) -> str:
        body = {"family": self.family, "center": self.center,
                "axes": self.axes, "density": self.density}
        return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"),
                                         allow_nan=False).encode()).hexdigest()


def _axis_integral(k: int, low: float, high: float) -> float:
    return (high ** (k + 1) - low ** (k + 1)) / (k + 1)


def _monomial_affine_matrix(spec: GeometrySpec) -> np.ndarray:
    """phi(Au+t)=T phi(u), diagonal A. No hidden native cross factor."""
    index = {exponents: i for i, exponents in enumerate(POWERS)}
    out = np.zeros((10, 10), dtype=np.float64)
    for i, exponents in enumerate(POWERS):
        terms = {(0, 0, 0): 1.0}
        for axis, n in enumerate(exponents):
            parts = {}
            for k in range(n + 1):
                powers = [0, 0, 0]
                powers[axis] = k
                parts[tuple(powers)] = (math.comb(n, k) *
                    spec.center[axis] ** (n - k) * spec.axes[axis] ** k)
            terms_new = {}
            for u, coef in terms.items():
                for v, component in parts.items():
                    p = tuple(u[j] + v[j] for j in range(3))
                    terms_new[p] = terms_new.get(p, 0.0) + coef * component
            terms = terms_new
        for key, value in terms.items():
            out[i, index[key]] = value
    return out


def _unit_sphere_cap(h: float) -> tuple[np.ndarray, np.ndarray]:
    p = math.pi
    r = np.array((p * (2/3 - h + h**3/3), 0, 0,
                  p * (1-h*h)**2/4,
                  p/4 * ((1-h)-2*(1-h**3)/3+(1-h**5)/5),
                  p/4 * ((1-h)-2*(1-h**3)/3+(1-h**5)/5),
                  p * ((1-h**3)/3-(1-h**5)/5), 0, 0, 0), dtype=np.float64)
    disk_r = math.sqrt(1-h*h)
    gram = np.zeros((10, 10), dtype=np.float64)
    for i, p_i in enumerate(POWERS):
        for j, p_j in enumerate(POWERS):
            nx, ny, nz = (p_i[k] + p_j[k] for k in range(3))
            if nx % 2 == 0 and ny % 2 == 0:
                gram[i, j] = (math.gamma((nx+1)/2) * math.gamma((ny+1)/2)
                              / math.gamma((nx+ny)/2 + 2)
                              * disk_r ** (nx+ny+2) * h**nz)
    return r, gram


def _unit_box_cap(h: float) -> tuple[np.ndarray, np.ndarray]:
    r = np.array([_axis_integral(p[0], -1, 1) *
                  _axis_integral(p[1], -1, 1) *
                  _axis_integral(p[2], h, 1) for p in POWERS], dtype=np.float64)
    gram = np.array([[(_axis_integral(p[0]+q[0],-1,1) *
                       _axis_integral(p[1]+q[1],-1,1) * h**(p[2]+q[2]))
                     for q in POWERS] for p in POWERS], dtype=np.float64)
    return r, gram


def vertical_cut_truth(spec: GeometrySpec, h_local: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return unit native c, raw r, and d r / d c_native at c (ambient).

    Define world plane z = center_z + axes_z*h_local, retained q >= 0.
    J is exact for smooth interior continuum cuts -1<h_local<1; not an
    assertion of discrete voxel topology or real CAD derivative existence.
    """
    h = float(h_local)
    if not math.isfinite(h) or not -1.0 < h < 1.0:
        raise ValueError("cut must be strictly interior (-1,1)")
    r0, surface0 = _unit_box_cap(h) if spec.family == "box" else _unit_sphere_cap(h)
    T = _monomial_affine_matrix(spec)
    world_h = spec.center[2] + spec.axes[2]*h
    unnormalized = np.zeros(10)
    unnormalized[0] = -world_h
    unnormalized[3] = 1.0
    length = np.linalg.norm(unnormalized)
    c = unnormalized / length
    weight = spec.density * math.prod(spec.axes)
    r = weight * T @ r0
    # delta(c_world(x)) = ||unnormalized|| / axes_z * delta(u_z-h).
    # With c-native cross coefficients, d r / d c = Jq @ B.
    J = weight * length / spec.axes[2] * (T @ surface0 @ T.T) @ B_NATIVE_TO_MONOMIAL
    return c, r, J


def voxel_geometry(spec: GeometrySpec, grid_size: int) -> Tensor:
    """Fixed world cube [-1,1]^3; 4 channels, missing SDF/inner BC set 0.

    The first two channels contain sampled 0/1 density and occupancy;
    the analytical continuum boundary is *not* a voxel-Boolean teacher.
    """
    if grid_size < 8:
        raise ValueError("grid_size must be >=8")
    xyz = np.linspace(-1, 1, grid_size, dtype=np.float64)
    grid = np.stack(np.meshgrid(xyz, xyz, xyz, indexing="ij"), axis=-1)
    centered = (grid - np.array(spec.center)) / np.array(spec.axes)
    occupied = (np.max(np.abs(centered), axis=-1) <= 1 if spec.family == "box"
                else np.sum(centered**2, axis=-1) <= 1)
    # Do not falsely claim a true SDF for ellipsoid, and do not create an
    # implicit internal boundary where none is present.
    rho = occupied.astype(np.float32)*spec.density
    occ = occupied.astype(np.float32)
    return torch.from_numpy(np.stack((rho, occ, np.zeros_like(occ),
                                      np.zeros_like(occ)), axis=0))


def sample_dataset(families: tuple[str,...], *, per_family: int, seed: int,
                   grid_size: int = 8, queries_per_geometry: int = 2):
    """Family-held-out seeded data. Repeated queries share one geometry ID."""
    if per_family < 1 or queries_per_geometry < 1:
        raise ValueError("nonempty dataset required")
    rng = np.random.default_rng(seed)
    geometry, controls, moments, derivatives, meta = [], [], [], [], []
    for family in families:
        for index in range(per_family):
            center = tuple(float(x) for x in rng.uniform(-.1,.1,3))
            if family == "sphere":
                s = float(rng.uniform(.46,.73)); axes = (s,s,s)
            elif family in ("box", "ellipsoid"):
                axes = tuple(float(x) for x in rng.uniform(.46,.73,3))
                # Force visibly non-spherical test ellipsoids.
                if family == "ellipsoid":
                    axes = (axes[0], axes[1]*.8, axes[2]*1.1)
            else:
                raise ValueError(f"unsupported family {family}")
            spec = GeometrySpec(family, center, axes)
            vx = voxel_geometry(spec, grid_size)
            for query in range(queries_per_geometry):
                h = float(rng.uniform(-.65,.65))
                c, r, J = vertical_cut_truth(spec, h)
                geometry.append(vx)
                controls.append(torch.from_numpy(c).float())
                moments.append(torch.from_numpy(r).float())
                derivatives.append(torch.from_numpy(J).float())
                meta.append({"family": family, "geometry_id": spec.geometry_id,
                             "query_index": query, "source": TEACHER_KIND})
    return (torch.stack(geometry),torch.stack(controls),torch.stack(moments),
            torch.stack(derivatives),meta)


def assert_disjoint_family_splits(train, test) -> None:
    train_families, test_families = ({x["family"] for x in data[4]} for data in (train,test))
    if train_families & test_families:
        raise ValueError("geometry-family train/test leakage")
    train_ids, test_ids = ({x["geometry_id"] for x in data[4]} for data in (train,test))
    if train_ids & test_ids:
        raise ValueError("geometry-ID train/test leakage")

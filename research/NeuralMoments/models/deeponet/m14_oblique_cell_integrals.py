"""M14: exact oblique *plane* cuts of a declared cellwise-constant voxel volume.

r_i = sum_cells rho_k * int_{box_k intersect beta_c(x)>=0} m_i(x) dV.
Jc_ij = sum_cut_cells rho_k / ||b|| * int_{plane cap_k} m_i m_j dA * B_j,
where beta=a+b.x, c=[a,bx,by,bz,0,...,0], B=(1,...,1,2,2,2).

All volume moments are integrated exactly from tetrahedra, and degree-four
planar Gram moments use a degree-four exact triangle cubature. Floating point
roundoff aside, this is exact FOR THE DECLARED DISCONTINUOUS CELL DENSITY,
not the continuous source CAD or its Boolean material. J is only admitted
away from plane/grid-vertex contact; a quadratic native c is NOT supported.
A caller may never promote these labels to W2 native Cherchi truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
import math
from typing import Any

import numpy as np

from .m13_cell_integrals import B, CellwiseMomentReference, POWERS

_CORNER_BITS = np.array(list(product((0, 1), repeat=3)), dtype=np.int8)
_FACE_IDS = ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
             (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3))
_EDGE_IDS = tuple((i, j) for i in range(8) for j in range(i + 1, 8)
                  if np.count_nonzero(_CORNER_BITS[i] != _CORNER_BITS[j]) == 1)
_TET_SCALE = 1. / 20.
_TRI_RULE = (
    (0.445948490915965, 0.223381589678011),
    (0.091576213509771, 0.109951743655322),
)


def plane_native_c(normal: Any, offset: float) -> np.ndarray:
    """For newly constructed parameters only. Never renormalize a saved c."""
    b = np.asarray(normal, dtype=np.float64)
    if b.shape != (3,) or not np.isfinite(b).all() or not math.isfinite(float(offset)):
        raise ValueError('FINITE_PLANE_REQUIRED')
    v = np.array([-float(offset), *b, 0., 0., 0., 0., 0., 0.], dtype=np.float64)
    mag = float(np.linalg.norm(v))
    if mag <= 1e-14 or float(np.linalg.norm(b)) <= 1e-12:
        raise ValueError('PLANE_HAS_ZERO_NORMAL')
    return v / mag


def monomials(points: np.ndarray) -> np.ndarray:
    p = np.asarray(points, dtype=np.float64)
    if p.shape[-1] != 3:
        raise ValueError('THREE_DIMENSIONAL_POINTS_REQUIRED')
    x, y, z = p[..., 0], p[..., 1], p[..., 2]
    return np.stack((np.ones_like(x), x, y, z, x*x, y*y, z*z, y*z, x*z, x*y), axis=-1)


def _tet_moments(center: np.ndarray, triangle: np.ndarray) -> np.ndarray:
    tetra = np.concatenate((center[None, :], triangle), axis=0)
    vol = abs(float(np.linalg.det(triangle-center))) / 6.
    sums = tetra.sum(axis=0)
    Q = vol * (np.outer(sums, sums) + tetra.T @ tetra) * _TET_SCALE
    return np.array((vol, *(vol*sums/4.), Q[0,0], Q[1,1], Q[2,2],
                     Q[1,2], Q[0,2], Q[0,1]), dtype=np.float64)


def _triangle_gram(triangle: np.ndarray) -> np.ndarray:
    a, b, c = triangle
    area = float(np.linalg.norm(np.cross(b-a, c-a)))*0.5
    out = np.zeros((10,10), dtype=np.float64)
    for w, weight in _TRI_RULE:
        # The three barycentric permutations integrate every polynomial in
        # surface coordinates through degree four (weights sum to one).
        for bary in ((w,w,1-2*w), (w,1-2*w,w), (1-2*w,w,w)):
            point = np.array(bary) @ triangle
            m = monomials(point)
            out += area * weight * np.outer(m,m)
    return out


def _clip_face(vertices: np.ndarray, signed: np.ndarray) -> list[np.ndarray]:
    """Clip one axis-aligned cube face by native-positive linear halfspace."""
    output=[]
    for i in range(len(vertices)):
        p, q = vertices[i-1], vertices[i]
        s, t = signed[i-1], signed[i]
        pin, qin = s >= 0., t >= 0.
        if pin != qin:
            output.append(p+(s/(s-t))*(q-p))
        if qin:
            output.append(q)
    return output


def _partial_box(low: np.ndarray, high: np.ndarray, a: float,
                 normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Exact polynomial moments of a convex clipped box and cut-plane Gram."""
    cube = low[None,:] + _CORNER_BITS * (high-low)[None,:]
    s = a + cube @ normal
    faces=[]
    for indices in _FACE_IDS:
        face = _clip_face(cube[np.asarray(indices)], s[np.asarray(indices)])
        if len(face) >= 3:
            faces.append(np.asarray(face))
    section=[]
    for i,j in _EDGE_IDS:
        if (s[i]<0 and s[j]>0) or (s[i]>0 and s[j]<0):
            section.append(cube[i]+s[i]/(s[i]-s[j])*(cube[j]-cube[i]))
    if len(section) < 3:
        raise ValueError('DEGENERATE_PARTIAL_CELL_SECTION')
    section = np.asarray(section)
    center=section.mean(axis=0)
    axis=np.array((1.,0.,0.)) if abs(normal[0])<.8*float(np.linalg.norm(normal)) else np.array((0.,1.,0.))
    u = np.cross(normal, axis)
    u /= np.linalg.norm(u)
    v = np.cross(normal, u)
    v /= np.linalg.norm(v)
    delta=section-center
    ordering=np.argsort(np.arctan2(delta@v,delta@u))
    cap=section[ordering]
    faces.append(cap)
    # Star-tetrahedralize all clipped faces about a convex interior point.
    interior = np.concatenate(faces, axis=0).mean(axis=0)
    moments = np.zeros(10, dtype=np.float64)
    for face in faces:
        for k in range(1,len(face)-1):
            moments += _tet_moments(interior, face[[0,k,k+1]])
    gram = np.zeros((10,10), dtype=np.float64)
    for k in range(1,len(cap)-1):
        gram += _triangle_gram(cap[[0,k,k+1]])
    return moments, gram


@dataclass(frozen=True)
class ObliqueCellReference:
    """Immutable source-bound analytic proxy, reusing M13 cellwise density."""
    base: CellwiseMomentReference

    @classmethod
    def bind(cls, voxels: Any) -> 'ObliqueCellReference':
        return cls(CellwiseMomentReference.bind(voxels))

    @property
    def source_sha256(self) -> str:
        return self.base.source_sha256

    def assert_same_voxel_source(self, voxels: Any) -> None:
        self.base.assert_same_voxel_source(voxels)

    def evaluate(self, c_native: Any) -> dict[str, Any]:
        """Returns Jc iff a *planar, noncontact, cellwise* smooth derivative exists.

        Jc is a 10x10 local ambient derivative at a planar native c, including
        quadratic perturbation columns, but evaluating an actual nonplanar
        quadric at a perturbed c is NOT implemented. Never invent that output.
        """
        self.base._verify_cache()
        c=np.asarray(c_native,dtype=np.float64)
        if c.shape!=(10,) or not np.isfinite(c).all():
            raise ValueError('FINITE_NATIVE_C10_REQUIRED')
        if np.any(c[4:]!=0):
            raise ValueError('NATIVE_NONPLANAR_QUADRIC_UNSUPPORTED')
        if abs(float(np.linalg.norm(c))-1.)>2e-6:
            raise ValueError('NONUNIT_NATIVE_C_REJECTED_DO_NOT_RENORMALIZE')
        b=c[1:4]
        norm=float(np.linalg.norm(b))
        if norm<=1e-12:
            raise ValueError('ZERO_PLANE_NORMAL_UNSUPPORTED')
        edge=self.base.edges
        a=float(c[0]); n=self.base.resolution
        lo=edge[:-1]; hi=edge[1:]
        choose_min=[lo if bi>=0 else hi for bi in b]
        choose_max=[hi if bi>=0 else lo for bi in b]
        minimum=a+b[0]*choose_min[0][:,None,None]+b[1]*choose_min[1][None,:,None]+b[2]*choose_min[2][None,None,:]
        maximum=a+b[0]*choose_max[0][:,None,None]+b[1]*choose_max[1][None,:,None]+b[2]*choose_max[2][None,None,:]
        full=(minimum>0)
        empty=(maximum<0)
        active=self.base.weights
        # Reject even exact grid-vertex contact: discontinuous density on cell
        # interfaces makes the two-sided local derivative unverified.
        # This is intentionally more conservative than most smooth CAD cuts.
        vertex_value=(a+b[0]*edge[:,None,None]+b[1]*edge[None,:,None]+b[2]*edge[None,None,:])
        contact=bool(np.any(np.abs(vertex_value) <= 2.e-12))
        if contact:
            return dict(r=None,Jc=None,derivative_status='GRID_VERTEX_CONTACT_UNAVAILABLE',
                        geometry_sha256=self.source_sha256,
                        native_teacher_training_admissible=False,
                        formal_native_Cherchi=False)
        partial=~(full|empty)
        total=np.zeros(10,dtype=np.float64)
        if np.any(full):
            xint=self.base.x_integrals
            yint=self.base.y_integrals
            zint=xint
            w=np.where(full,active,0.)
            for i,(px,py,pz) in enumerate(POWERS):
                total[i]=float(np.einsum('ijk,i,j,k->',w,xint[:,px],yint[:,py],zint[:,pz],optimize=True))
        gram=np.zeros((10,10),dtype=np.float64)
        count=0
        for i,j,k in np.argwhere(partial & (active>0)):
            low=np.array((edge[i],edge[j],edge[k]),dtype=np.float64)
            high=np.array((edge[i+1],edge[j+1],edge[k+1]),dtype=np.float64)
            r_cell,h_cell=_partial_box(low,high,a,b)
            total+=active[i,j,k]*r_cell
            gram+=active[i,j,k]*h_cell
            count+=1
        J=(gram/norm)*B[None,:]
        if not np.isfinite(total).all() or not np.isfinite(J).all():
            raise ValueError('NONFINITE_CELL_INTEGRAL')
        status='STRICT_SIGN_CONSTANT_P0' if not np.any(partial) else 'PLANAR_CUT_CELLWISE_AMBIENT_LOCAL'
        return {'r':total,'Jc':J,'derivative_status':status,
                'geometry_sha256':self.source_sha256,'native_c_passthrough':c.copy(),
                'cut_cells':count,'cell_resolution':n,
                'supported_beta':'NATIVE_A_PLUS_B_DOT_X_ONLY',
                'native_teacher_training_admissible':False,
                'formal_native_Cherchi':False,'CAD_material_certified':False,
                'source':'DECLARED_PIECEWISE_CONSTANT_VOXEL_VOLUME_NOT_CAD'}

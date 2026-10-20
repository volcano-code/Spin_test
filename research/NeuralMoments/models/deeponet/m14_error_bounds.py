"""Conservative *analytic ellipsoid-source* voxelization error bounds.

Requires privileged, independently fixed ellipsoid center/axes/density. For
nonnegative cell-center sampled density, only cells intersecting the true
ellipsoid boundary can differ from exact continuous occupancy. Bound |r_i|
errors by total ambiguous cell mass, and |J_ij| by total ambiguous plane
section area times rho/||b|| times W0's native cross factor B_j.

This is a FLOAT64 interval-margined *analytic benchmark bound*, not a formal
CAD/Boolean or exact rational proof. It cannot be used on an unknown mesh,
self-intersecting solid, unverified frame or unspecified material density.
"""
from __future__ import annotations

import math
import numpy as np

from .m13_cell_integrals import B
from .m14_oblique_cell_integrals import _partial_box


def analytic_ellipsoid_uncertainty(center, axes, density, resolution, c_native):
    center=np.asarray(center,dtype=np.float64)
    axes=np.asarray(axes,dtype=np.float64)
    c=np.asarray(c_native,dtype=np.float64)
    if (center.shape!=(3,) or axes.shape!=(3,) or c.shape!=(10,) or
        not np.isfinite(center).all() or not np.isfinite(axes).all() or
        not np.isfinite(c).all() or not np.all(axes>0) or
        not math.isfinite(float(density)) or density<=0 or
        type(resolution) is not int or resolution<4 or
        np.any(c[4:]!=0) or abs(np.linalg.norm(c)-1)>2e-6 or
        np.linalg.norm(c[1:4])<=1e-12 or
        np.any(np.abs(center)+axes>=1)):
        raise ValueError('INDEPENDENT_CONTAINED_ELLIPSOID_AND_UNIT_PLANE_REQUIRED')
    edge=np.linspace(-1,1,resolution+1)
    lo=edge[:-1,None];hi=edge[1:,None]
    minimum=np.maximum(np.maximum(lo-center,center-hi),0.)/axes
    maximum=np.maximum(np.abs(lo-center),np.abs(hi-center))/axes
    smallest=(minimum**2).sum(-1)
    largest=(maximum**2).sum(-1)
    lower=(smallest[:,None,None]+smallest[None,:,None]+smallest[None,None,:])
    upper=(largest[:,None,None]+largest[None,:,None]+largest[None,None,:])
    margin=5e-13  # conservative double-precision interval guard
    ambiguous=~((upper < 1.-margin)|(lower > 1.+margin))
    b=c[1:4];offset=c[0]
    # Cell-center labels may be binary32, so append tiny density roundoff
    # budget on the full spatial cube (M13 sample uses float32 channels).
    roundoff=2e-6*max(1.,float(density))
    volume_bound=float(density)*int(ambiguous.sum())*(2./resolution)**3+roundoff*8.
    section_area=0.;boundary_sections=0
    for i,j,k in np.argwhere(ambiguous):
        left=np.array((edge[i],edge[j],edge[k]))
        right=np.array((edge[i+1],edge[j+1],edge[k+1]))
        minbeta=float(offset+np.sum(b*np.where(b>=0,left,right)))
        maxbeta=float(offset+np.sum(b*np.where(b>=0,right,left)))
        if minbeta < 0 < maxbeta:
            _,G=_partial_box(left,right,float(offset),b)
            section_area+=float(G[0,0])
            boundary_sections+=1
    Jbound=(float(density)*section_area/float(np.linalg.norm(b)) +
            roundoff*12./float(np.linalg.norm(b))) * float(max(B))
    return {'raw_ten_moment_max_abs_error_upper_bound':volume_bound,
            'native_Jc_max_abs_error_upper_bound':Jbound,
            'ambiguous_boundary_cell_count':int(ambiguous.sum()),
            'ambiguous_cut_cell_count':boundary_sections,
            'ambiguous_plane_area':section_area,
            'underlying_shape_oracle_required':True,
            'not_formal_interval_certification':True,
            'does_not_certify_CAD_material':True}

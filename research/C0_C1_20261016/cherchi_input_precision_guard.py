"""Lossless-identity preflight at Noodles v6 exact-rational -> binary64 Cherchi boundary.

Fail closed; do not weld/cull faces, silently round away features, or loosen
any solver residual. Topological admissibility is NOT inferred from this check:
this guard is necessary but not sufficient for robust Cherchi production use.
"""
from __future__ import annotations
from collections import defaultdict
from fractions import Fraction as Q
import hashlib,json
import numpy as np

class CherchiInputPrecisionError(ValueError):
    def __init__(self, report):
        super().__init__('CHERCHI_FLOAT64_UNREPRESENTABLE_RATIONAL_BOUNDARY')
        self.report=report

def _exact_nonzero_area_triangle(vertices,face):
    a,b,c=[[Q(x) for x in vertices[int(i)]] for i in face]
    u=[b[k]-a[k] for k in range(3)]
    v=[c[k]-a[k] for k in range(3)]
    return any(u[i]*v[j]!=u[j]*v[i] for i,j in ((0,1),(0,2),(1,2)))

def inspect_exact_to_binary64(packet, *, maximum_examples=12):
    """Inspect actual rational input, preserving output indices and exact identity."""
    raw_vertices=packet['vertices'];raw_faces=packet['faces']
    if not raw_vertices or not raw_faces:raise ValueError('EMPTY_RATIONAL_DESIGN_REGION')
    if any(len(row)!=3 for row in raw_vertices):raise ValueError('INVALID_VERTEX_SHAPE')
    V=np.asarray([[float(Q(x)) for x in row] for row in raw_vertices],dtype=np.float64)
    F=np.asarray(raw_faces,dtype=np.int64)
    if F.ndim!=2 or F.shape[1]!=3:raise ValueError('INVALID_FACE_SHAPE')
    if not np.isfinite(V).all():raise ValueError('NONFINITE_BINARY64_CONVERSION')
    if np.any(F<0) or np.any(F>=len(V)):raise ValueError('INVALID_FACE_INDEX')
    if np.any((F[:,0]==F[:,1])|(F[:,1]==F[:,2])|(F[:,2]==F[:,0])):
        raise ValueError('ORIGINAL_INDEX_DEGENERATE_FACE')
    _, inverse, counts = np.unique(V, axis=0, return_inverse=True, return_counts=True)
    duplicate_coordinate_groups=np.flatnonzero(counts>1)
    # Only count distinct exact positions that alias after binary64 rounding.
    # Repeated references to identical exact positions are a separate mesh
    # topology question, not a rounding collision.
    aliases=[]
    for gid in duplicate_coordinate_groups:
        indices=np.flatnonzero(inverse==gid)
        exact={tuple(Q(x) for x in raw_vertices[int(i)]) for i in indices}
        if len(exact)>1:
            aliases.append({'float_coordinates':[float(x) for x in V[int(indices[0])]],
                'vertex_indices':[int(x) for x in indices]})
    collapsed=(inverse[F[:,0]]==inverse[F[:,1]]) | (inverse[F[:,1]]==inverse[F[:,2]]) | (inverse[F[:,2]]==inverse[F[:,0]])
    A=V[F[:,1]]-V[F[:,0]];B=V[F[:,2]]-V[F[:,0]]
    with np.errstate(over='ignore',under='ignore',invalid='ignore'):
        areas=np.linalg.norm(np.cross(A,B),axis=1)/2
    zeros=np.flatnonzero((areas==0) | (~np.isfinite(areas)))
    collapsed_idx=np.flatnonzero(collapsed)
    exact_nonzero_from_float_zero=sum(_exact_nonzero_area_triangle(raw_vertices,F[int(i)]) for i in zeros)
    report={'schema':'noodles-v6-cherchi-float64-admission-v1',
        'rational_input_vertices':len(V),'rational_input_faces':len(F),
        'aliased_distinct_exact_coordinate_groups':len(aliases),
        'collapsed_face_count':len(collapsed_idx),
        'binary64_zero_or_nonfinite_area_faces':len(zeros),
        'exact_positive_area_among_binary64_zero_faces':int(exact_nonzero_from_float_zero),
        'aliased_vertex_examples':aliases[:maximum_examples],
        'collapsed_face_index_examples':[int(x) for x in collapsed_idx[:maximum_examples]],
        'failure_reason':('CHERCHI_FLOAT64_UNREPRESENTABLE_RATIONAL_BOUNDARY' if (aliases or len(zeros)) else None),
        'ready_for_cherchi_float_input':not (aliases or len(zeros)),
        'no_auto_weld_or_triangle_deletion':True}
    return report

def admit_exact_to_binary64(packet):
    report=inspect_exact_to_binary64(packet)
    if not report['ready_for_cherchi_float_input']:
        raise CherchiInputPrecisionError(report)
    return report
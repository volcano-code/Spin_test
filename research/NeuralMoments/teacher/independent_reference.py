"""W2 independent signed-tetrahedron moment oracle for exact rational boundaries.

Mathematical reference only. Closure/orientation is checked, but a closed
triangle soup is not an embedding or legal Cherchi material certificate.
"""
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math

POWER_ORDER = ((0,0,0),(1,0,0),(0,1,0),(0,0,1),
               (2,0,0),(0,2,0),(0,0,2),(0,1,1),(1,0,1),(1,1,0))


def _rational(value):
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("EXACT_RATIONAL_COORDINATE_REQUIRED")
    if not isinstance(value, (str, int, Fraction)):
        raise ValueError("EXACT_RATIONAL_COORDINATE_REQUIRED")
    try:
        return Fraction(value)
    except (ValueError, ZeroDivisionError) as error:
        raise ValueError("INVALID_RATIONAL_COORDINATE") from error


def _triple(a, b, c):
    return (a[0]*(b[1]*c[2]-b[2]*c[1])
           +a[1]*(b[2]*c[0]-b[0]*c[2])
           +a[2]*(b[0]*c[1]-b[1]*c[0]))


def _rational_text(v):
    return f"{v.numerator}/{v.denominator}"


def integrate_exact_boundary(vertices, faces, density):
    """Return 10 exact density-weighted moments and independently auditable proof.

    Requires each directed edge's reverse exactly once (locally oriented closed
    2-manifold). Does not certify no self-intersection or correct Boolean set.
    Runtime is linear in triangles but rational sizes depend on input bits.
    """
    if not isinstance(vertices, (tuple, list)) or not isinstance(faces, (tuple,list)):
        raise ValueError("BOUNDARY_SHAPE_INVALID")
    if len(vertices)<4 or len(faces)<4:
        raise ValueError("BOUNDARY_OPEN_OR_EMPTY")
    try:
        v=tuple(tuple(_rational(x) for x in row) for row in vertices)
    except TypeError as error:
        raise ValueError("VERTEX_SHAPE_INVALID") from error
    if any(len(row)!=3 for row in v):
        raise ValueError("VERTEX_SHAPE_INVALID")
    d=_rational(density)
    if d<=0:
        raise ValueError("DENSITY_MUST_BE_POSITIVE")
    f=[]
    directed=Counter()
    undirected=Counter()
    unique_faces=set()
    for row in faces:
        if not isinstance(row,(tuple,list)) or len(row)!=3 or any(type(i) is not int for i in row):
            raise ValueError("FACE_FORMAT_INVALID")
        i,j,k=row
        if len({i,j,k})!=3 or min(row)<0 or max(row)>=len(v):
            raise ValueError("FACE_INDEX_INVALID")
        if tuple(sorted(row)) in unique_faces:
            raise ValueError("DUPLICATE_FACE")
        unique_faces.add(tuple(sorted(row)))
        a,b,c=v[i],v[j],v[k]
        ab=tuple(b[m]-a[m] for m in range(3))
        ac=tuple(c[m]-a[m] for m in range(3))
        if all(ab[(m+1)%3]*ac[(m+2)%3]-ab[(m+2)%3]*ac[(m+1)%3]==0 for m in range(3)):
            raise ValueError("DEGENERATE_EXACT_FACE")
        for src,dst in ((i,j),(j,k),(k,i)):
            directed[src,dst]+=1
            undirected[min(src,dst),max(src,dst)]+=1
        f.append(row)
    if any(n!=2 or directed[a,b]!=1 or directed[b,a]!=1
           for (a,b),n in undirected.items()):
        raise ValueError("BOUNDARY_NOT_CLOSED_OR_ORIENTED")
    totals=[Fraction(0) for _ in POWER_ORDER]
    for i,j,k in f:
        p=(v[i],v[j],v[k])
        volume=d*_triple(*p)/6
        sx=[sum(point[axis] for point in p) for axis in range(3)]
        totals[0]+=volume
        for axis in range(3):
            totals[1+axis]+=volume*sx[axis]/4
        for index,(a,b) in enumerate(((0,0),(1,1),(2,2),(1,2),(0,2),(0,1)),start=4):
            totals[index]+=volume*(sx[a]*sx[b]+sum(pt[a]*pt[b] for pt in p))/20
    if totals[0]<=0:
        raise ValueError("NONPOSITIVE_ORIENTATION_OR_MASS")
    body={"vertices":[[_rational_text(x) for x in row] for row in v],
          "faces":[list(row) for row in f]}
    sha=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return totals,{"schema":"w2-independent-tetra-integral-v1",
        "exact_boundary_sha256":sha,"vertex_count":len(v),"face_count":len(f),
        "reference_raw_moments_exact":[_rational_text(x) for x in totals],
        "reference_scope":"CLOSED_ORIENTED_TRIANGLE_BOUNDARY_NOT_EMBEDDING_CERTIFICATE"}


def compare_exact_reference(measured, reference, *, rtol=1e-10, atol=1e-12):
    """Fail closed on numerical disagreements while preserving component errors."""
    if hasattr(measured,"tolist"):
        measured=measured.tolist()
    if not isinstance(measured,(list,tuple)) or len(measured)!=10 or len(reference)!=10:
        raise ValueError("TEN_MOMENT_REFERENCE_REQUIRED")
    try:
        values=[float(v) for v in measured]
        truth=[float(v) for v in reference]
    except (TypeError,ValueError,OverflowError) as error:
        raise ValueError("UNREPRESENTABLE_REFERENCE") from error
    if not all(math.isfinite(x) for x in values+truth):
        raise ValueError("NONFINITE_REFERENCE_OR_MOMENT")
    errors=[abs(a-b) for a,b in zip(values,truth)]
    tolerance=[atol+rtol*abs(b) for b in truth]
    return {"measured":values,"reference":truth,"absolute_errors":errors,
            "maximum_absolute_error":max(errors),
            "maximum_normalized_error":max(e/t for e,t in zip(errors,tolerance)),
            "within_tolerance":all(e<=t for e,t in zip(errors,tolerance)),
            "rtol":rtol,"atol":atol}

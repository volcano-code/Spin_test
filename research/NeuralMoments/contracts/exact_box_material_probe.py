"""Exact-rational P0 CLOSED-BOX F/D fixture (NOT Cherchi or a geometry seal).

The sign-oriented tetrahedra provide an independent integration path for the
same ten *undoubled* raw moments as spin_common.ORDER. This verifies actual
polyhedral boundary integrals and fixed-vs-design accounting, without claiming
that an arbitrary Cherchi Boolean output is closed, embedded or printable.
"""
from __future__ import annotations
from fractions import Fraction as F

ORDER = ('M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY')
EXPONENTS = ((0,0,0),(1,0,0),(0,1,0),(0,0,1),
             (2,0,0),(0,2,0),(0,0,2),(0,1,1),(1,0,1),(1,1,0))
FACES = ((0,2,1),(0,3,2), (4,5,6),(4,6,7), (0,1,5),(0,5,4),
         (3,7,6),(3,6,2), (0,4,7),(0,7,3), (1,2,6),(1,6,5))


def fraction(value):
    if isinstance(value, bool):
        raise ValueError('boolean is not a rational coordinate')
    if isinstance(value, float):
        return F(str(value))
    return F(value)


def box_mesh(lower, upper, *, inward=False):
    """An outward-oriented rectangular box, optionally negative inner shell."""
    if len(lower) != 3 or len(upper) != 3:
        raise ValueError('expected 3D bounds')
    lo, hi = tuple(map(fraction, lower)),tuple(map(fraction, upper))
    if any(b <= a for a,b in zip(lo, hi)):
        raise ValueError('box has nonpositive side')
    x,y,z = lo; X,Y,Z = hi
    vertices=((x,y,z),(X,y,z),(X,Y,z),(x,Y,z),
              (x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z))
    faces=tuple((a,c,b) if inward else (a,b,c) for a,b,c in FACES)
    return vertices,faces


def combine_meshes(*meshes):
    vertices=[]; faces=[]
    for vs, fs in meshes:
        off=len(vertices)
        vertices.extend(vs)
        faces.extend(tuple(off+i for i in face) for face in fs)
    return tuple(vertices),tuple(faces)


def integrate_tetra_exact(mesh, density=1):
    """Exact, orientation-checked signed tetrahedral sum (not self-intersection proof)."""
    vertices, faces = mesh
    rho=fraction(density)
    if rho<=0 or not vertices or not faces:
        raise ValueError('positive density and nonempty mesh required')
    P=tuple(tuple(map(fraction,v)) for v in vertices)
    edges={}
    if any(len(p)!=3 for p in P):
        raise ValueError('incorrect vertex dimension')
    terms=[F(0)]*10
    for face in faces:
        if len(face)!=3 or len(set(face))!=3 or any(type(i) is not int or i<0 or i>=len(P) for i in face):
            raise ValueError('invalid triangle index')
        for a,b in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):
            edge=(min(a,b),max(a,b))
            edges.setdefault(edge,[]).append((a,b))
        a,b,c=(P[i] for i in face)
        cross=(b[1]*c[2]-b[2]*c[1],b[2]*c[0]-b[0]*c[2],b[0]*c[1]-b[1]*c[0])
        V=(sum(a[i]*cross[i] for i in range(3))/6)*rho
        s=tuple(a[i]+b[i]+c[i] for i in range(3))
        terms[0]+=V
        for i in range(3):
            terms[1+i]+=V*s[i]/4
        for k,(i,j) in enumerate(((0,0),(1,1),(2,2),(1,2),(0,2),(0,1)),start=4):
            terms[k]+=V*(sum(p[i]*p[j] for p in (a,b,c))+s[i]*s[j])/20
    if any(len(uses)!=2 or uses[0]!=(uses[1][1],uses[1][0]) for uses in edges.values()):
        raise ValueError('non-closed or inconsistent oriented edge')
    if terms[0]<=0:
        raise ValueError('nonpositive oriented volume')
    return tuple(terms)


def analytical_box_exact(lower,upper,density=1):
    """Independent separable monomial integral (not tetrahedral integration)."""
    lo,hi=tuple(map(fraction,lower)),tuple(map(fraction,upper))
    if any(a>=b for a,b in zip(lo,hi)):
        raise ValueError('invalid analytic box')
    return tuple(fraction(density)*__import__('math').prod(
        (hi[i]**(degree+1)-lo[i]**(degree+1))/(degree+1)
        for i,degree in enumerate(powers)) for powers in EXPONENTS)


def totals_for_nested_boxes(outer_bounds,inner_bounds,rho_fixed,rho_design):
    """Fixed material F=outer\\inner, design D=inner; independent exact sum."""
    ol,oh=outer_bounds; il,ih=inner_bounds
    if any(not (ol[k]<il[k]<ih[k]<oh[k]) for k in range(3)):
        raise ValueError('design must be strictly inside original outer box')
    Fmesh=combine_meshes(box_mesh(ol,oh),box_mesh(il,ih,inward=True))
    Dmesh=box_mesh(il,ih)
    rf=integrate_tetra_exact(Fmesh,rho_fixed)
    rd=integrate_tetra_exact(Dmesh,rho_design)
    total=tuple(a+b for a,b in zip(rf,rd))
    assert total==tuple(a* fraction(rho_fixed) + b*(fraction(rho_design)-fraction(rho_fixed))
                        for a,b in zip(analytical_box_exact(ol,oh),analytical_box_exact(il,ih)))
    return {'fixed_r':rf,'design_r':rd,'total_r':total,
            'fixed_mesh':Fmesh,'design_mesh':Dmesh}


def mapped_mesh(mesh,A,t):
    """Exact rational affine vertex map; flip face winding on negative det(A)."""
    A=tuple(tuple(map(fraction,row)) for row in A)
    t=tuple(map(fraction,t))
    if len(A)!=3 or any(len(row)!=3 for row in A) or len(t)!=3:
        raise ValueError('invalid affine map')
    det=(A[0][0]*(A[1][1]*A[2][2]-A[1][2]*A[2][1])
         -A[0][1]*(A[1][0]*A[2][2]-A[1][2]*A[2][0])
         +A[0][2]*(A[1][0]*A[2][1]-A[1][1]*A[2][0]))
    if det==0:
        raise ValueError('singular map')
    vertices,faces=mesh
    out=tuple(tuple(sum((A[i][j]*v[j] for j in range(3)),t[i]) for i in range(3)) for v in vertices)
    flipped=tuple((a,c,b) for a,b,c in faces) if det<0 else faces
    return (out,flipped)


def transform_r_exact(r,A,t,density_ratio=1):
    """Independent raw-moment affine transfer with exact rational arithmetic."""
    M,*rest=r
    L=tuple(rest[:3]); xx,yy,zz,yz,xz,xy=rest[3:]
    Q=((xx,xy,xz),(xy,yy,yz),(xz,yz,zz))
    A=tuple(tuple(map(fraction,row)) for row in A)
    t=tuple(map(fraction,t))
    det=(A[0][0]*(A[1][1]*A[2][2]-A[1][2]*A[2][1])
         -A[0][1]*(A[1][0]*A[2][2]-A[1][2]*A[2][0])
         +A[0][2]*(A[1][0]*A[2][1]-A[1][1]*A[2][0]))
    w=abs(det)*fraction(density_ratio)
    AL=tuple(sum(A[i][j]*L[j] for j in range(3)) for i in range(3))
    Qp=tuple(tuple(sum((A[i][k]*Q[k][l]*A[j][l] for k in range(3) for l in range(3)),F(0))
                    +AL[i]*t[j]+t[i]*AL[j]+M*t[i]*t[j] for j in range(3)) for i in range(3))
    return (w*M,*(w*(AL[i]+M*t[i]) for i in range(3)),
            w*Qp[0][0],w*Qp[1][1],w*Qp[2][2],w*Qp[1][2],w*Qp[0][2],w*Qp[0][1])

"""P0 closed-mesh algebra, strict F/D accounting; not a Cherchi witness."""
from fractions import Fraction as F
from math import isclose
import pytest
from .exact_box_material_probe import (
    ORDER, box_mesh, combine_meshes, integrate_tetra_exact, analytical_box_exact,
    totals_for_nested_boxes, mapped_mesh, transform_r_exact)

OUTER=((-2,-2,-2),(2,2,2))
INNER=((F(-1,2),F(-1,4),F(-1,8)),(F(3,4),F(1,2),F(7,8)))
F_RHO=F(6,5)
D_RHO=F(7,4)


def test_exact_closed_oriented_box_moments():
    assert ORDER==('M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY')
    for b in (OUTER,INNER):
        assert integrate_tetra_exact(box_mesh(*b)) == analytical_box_exact(*b)
    assert any(analytical_box_exact(*INNER)[i] for i in (7,8,9))


def test_nested_F_plus_D_not_double_counted():
    data=totals_for_nested_boxes(OUTER,INNER,F_RHO,D_RHO)
    rf,rd,rt=data['fixed_r'],data['design_r'],data['total_r']
    assert rf[0] == F_RHO*(analytical_box_exact(*OUTER)[0]-analytical_box_exact(*INNER)[0])
    assert rd[0] == D_RHO*analytical_box_exact(*INNER)[0]
    assert rt[0] == rf[0]+rd[0]
    assert rt[7:]==tuple(rf[i]+rd[i] for i in (7,8,9))
    assert rt[0]!=rf[0]+2*rd[0]


@pytest.mark.parametrize('A', [
    ((0,-2,0),(2,0,0),(0,0,F(3,2))),
    ((-1,0,0),(0,1,0),(0,0,1)),
    ((1,F(1,3),0),(0,2,0),(0,0,F(3,2))),
])
def test_exact_affine_geometry_vs_transform_r(A):
    t=(F(3,4),F(-1,5),F(7,10))
    base=totals_for_nested_boxes(OUTER,INNER,F_RHO,D_RHO)
    for identity,density in (('fixed',F_RHO),('design',D_RHO)):
        mesh=base[identity+'_mesh']
        pre=base[identity+'_r']
        mapped=mapped_mesh(mesh,A,t)
        assert integrate_tetra_exact(mapped,density)==transform_r_exact(pre,A,t)


def test_density_linear_and_no_fixed_derivative():
    b=box_mesh(*INNER)
    one=integrate_tetra_exact(b)
    high=integrate_tetra_exact(b,F(11,7))
    assert high==tuple(v*F(11,7) for v in one)
    base=totals_for_nested_boxes(OUTER,INNER,F_RHO,D_RHO)
    assert tuple(a+b for a,b in zip(base['fixed_r'],base['design_r']))==base['total_r']


def test_reject_invalid_geometry():
    with pytest.raises(ValueError):box_mesh((1,0,0),(0,1,1))
    with pytest.raises(ValueError):box_mesh((True,0,0),(1,1,1))
    box=box_mesh(*INNER)
    with pytest.raises(ValueError,match='non-closed'):
        integrate_tetra_exact((box[0],box[1][:-1]))
    with pytest.raises(ValueError,match='nonpositive'):
        integrate_tetra_exact(box_mesh(*INNER,inward=True))
    with pytest.raises(ValueError):totals_for_nested_boxes(OUTER,((0,0,0),(3,1,1)),1,1)
    with pytest.raises(ValueError):mapped_mesh(box,((0,0,0),(0,0,0),(0,0,0)),(0,0,0))

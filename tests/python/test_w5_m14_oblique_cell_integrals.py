"""M14: independent exact oblique-box and ellipsoid P0 checks, not native CAD."""
import numpy as np
import pytest

from research.NeuralMoments.models.deeponet.m13_cell_integrals import (
    CellwiseMomentReference, vertical_native_c, B)
from research.NeuralMoments.models.deeponet.m14_oblique_cell_integrals import (
    ObliqueCellReference, plane_native_c, monomials, _triangle_gram)
from research.NeuralMoments.models.deeponet.m14_oblique_analytic import (
    tilted_box_oracle_from_yz, ellipsoid_plane_oracle)


def uniform(n=8,density=1.3):
    D=np.zeros((4,n,n,n),dtype=np.float64)
    D[0]=density;D[1]=1.
    return D


@pytest.mark.parametrize('n',[4,8,12,16])
@pytest.mark.parametrize('normal,offset',[([1.,.12,.07],.11317),([1.,-.13,.09],-.08119)])
def test_oblique_box_agrees_with_independent_yz_integrator(n,normal,offset):
    c=plane_native_c(normal,offset)
    a=ObliqueCellReference.bind(uniform(n)).evaluate(c)
    truth=tilted_box_oracle_from_yz(normal,offset,density=1.3)
    assert a['cut_cells']>0
    assert a['derivative_status']=='PLANAR_CUT_CELLWISE_AMBIENT_LOCAL'
    np.testing.assert_allclose(a['r'],truth['r'],atol=2e-11,rtol=2e-11)
    np.testing.assert_allclose(a['Jc'],truth['Jc'],atol=3e-11,rtol=3e-11)
    np.testing.assert_array_equal(a['native_c_passthrough'],c)
    assert not a['native_teacher_training_admissible']


def test_all_ten_jacobian_columns_independently_checked():
    ref=ObliqueCellReference.bind(uniform())
    c=plane_native_c([1.,.21,-.17],.11967)
    result=ref.evaluate(c)
    truth=tilted_box_oracle_from_yz([1.,.21,-.17],.11967,density=1.3)
    np.testing.assert_allclose(result['Jc'],truth['Jc'],atol=2e-11,rtol=2e-11)
    assert np.max(np.abs(result['Jc'][:,7:]))>0.001
    assert np.max(np.abs(result['Jc']-result['Jc'].T))>1e-5


def test_oblique_jq_psd_symmetric_radial_null():
    ref=ObliqueCellReference.bind(uniform())
    c=plane_native_c([.18,-.54,1.],.161723)
    J=ref.evaluate(c)['Jc']
    assert J is not None
    H=J/B[None,:]
    np.testing.assert_allclose(H,H.T,atol=2e-11)
    assert np.linalg.eigvalsh((H+H.T)/2).min()>-1e-10
    np.testing.assert_allclose(J@c,np.zeros(10),atol=2e-11)


def test_mass_complement_and_signed_halfspace():
    ref=ObliqueCellReference.bind(uniform(8,1.7))
    c=plane_native_c([.391,-.731,.87],.170917)
    first=ref.evaluate(c);second=ref.evaluate(-c)
    full=CellwiseMomentReference.bind(uniform(8,1.7)).raw_moments(-2.)
    np.testing.assert_allclose(first['r']+second['r'],full,atol=2e-11)
    np.testing.assert_allclose(second['Jc'],first['Jc'],atol=3e-11)
    assert not np.allclose(first['r'],second['r'])


@pytest.mark.parametrize('component',[0,1,2,3])
def test_finite_difference_along_native_unit_sphere(component):
    ref=ObliqueCellReference.bind(uniform(8,1.2))
    c=plane_native_c([.81,-.23,.37],.11731)
    eps=3e-6
    displacement=np.zeros(10);displacement[component]=1
    plus=c+eps*displacement;plus/=np.linalg.norm(plus)
    minus=c-eps*displacement;minus/=np.linalg.norm(minus)
    xp=ref.evaluate(plus);xm=ref.evaluate(minus)
    assert xp['Jc'] is not None and xm['Jc'] is not None
    finite=(xp['r']-xm['r'])/(2*eps)
    unit_tangent=displacement-c*c[component]
    analytic=ref.evaluate(c)['Jc']@unit_tangent
    np.testing.assert_allclose(finite,analytic,atol=4e-7,rtol=4e-7)


def test_vertical_m13_exact_parity():
    rng=np.random.default_rng(3)
    D=uniform(9)
    D[0]=rng.uniform(.1,1.9,(9,9,9))
    D[1]=rng.integers(0,2,(9,9,9))
    c=vertical_native_c(.13578)
    old=CellwiseMomentReference.bind(D).evaluate(c)
    new=ObliqueCellReference.bind(D).evaluate(c)
    np.testing.assert_allclose(old['r'],new['r'],atol=1e-12)
    np.testing.assert_allclose(old['Jc'],new['Jc'],atol=4e-12)


def test_full_empty_and_zero_density():
    ref=ObliqueCellReference.bind(uniform())
    for offset,expected in [(-3.2,'full'),(3.2,'empty')]:
        r=ref.evaluate(plane_native_c([.3,.41,.52],offset))
        assert r['derivative_status']=='STRICT_SIGN_CONSTANT_P0'
        np.testing.assert_array_equal(r['Jc'],np.zeros((10,10)))
        assert r['r'][0]==pytest.approx(10.4 if expected=='full' else 0.)
    D=uniform();D[0]=0
    zero=ObliqueCellReference.bind(D).evaluate(plane_native_c([.73,-.4,.25],.163971))
    np.testing.assert_array_equal(zero['r'],np.zeros(10))
    np.testing.assert_array_equal(zero['Jc'],np.zeros((10,10)))


@pytest.mark.parametrize('n',[4,8,12])
def test_contact_rejects_unqualified_jacobian(n):
    ref=ObliqueCellReference.bind(uniform(n))
    c=plane_native_c([1.,0.,0.],0.) if n%2==0 else plane_native_c([1.,0.,0.],1/n)
    result=ref.evaluate(c)
    assert result['r'] is None and result['Jc'] is None
    assert result['derivative_status']=='GRID_VERTEX_CONTACT_UNAVAILABLE'


def test_quadratic_and_nonunit_unavailable_not_silently_linearized():
    ref=ObliqueCellReference.bind(uniform())
    c=plane_native_c([1.,.2,.3],.12)
    bad=c.copy();bad[9]=1e-8
    with pytest.raises(ValueError,match='NONPLANAR'):
        ref.evaluate(bad)
    with pytest.raises(ValueError,match='NONUNIT'):
        ref.evaluate(c*1.01)
    with pytest.raises(ValueError,match='ZERO_PLANE_NORMAL'):
        ref.evaluate(np.array([1.,*([0.]*9)]))
    with pytest.raises(ValueError,match='FINITE_NATIVE'):
        bad=c.copy();bad[2]=np.nan;ref.evaluate(bad)


def test_geometry_cache_rejects_source_changes_and_forced_tampering():
    D=uniform()
    ref=ObliqueCellReference.bind(D)
    ref.assert_same_voxel_source(D)
    other=D.copy();other[0,0,0,0]+=.1
    with pytest.raises(ValueError,match='SOURCE_IDENTITY'):
        ref.assert_same_voxel_source(other)
    ref.base.weights.setflags(write=True)
    ref.base.weights[0,0,0]+=.1
    with pytest.raises(ValueError,match='NUMERIC_CONTENT_TAMPERED'):
        ref.evaluate(plane_native_c([.71,.18,.56],.19))


def test_bad_geometry_rejected():
    for mode in ('negative_rho','bad_occ','inf','wrong_channels','int'):
        D=uniform()
        if mode=='negative_rho':D[0,0,0,0]=-1.
        if mode=='bad_occ':D[1,2,2,2]=1.1
        if mode=='inf':D[0,0,0,0]=np.inf
        if mode=='wrong_channels':D=D[:3]
        if mode=='int':D=D.astype(int)
        with pytest.raises(ValueError):ObliqueCellReference.bind(D)


def test_ellipsoid_analytic_oblique_oracle_radial_null():
    c=plane_native_c([.27,-.33,.95],.10291)
    p=ellipsoid_plane_oracle((.02,-.04,.06),(.67,.54,.71),1.2,c)
    assert p['status']=='SMOOTH_ELLIPSOID_PLANE'
    H=p['Jc']/B[None,:]
    np.testing.assert_allclose(H,H.T,atol=5e-12)
    assert np.linalg.eigvalsh(H).min()>-1e-11
    assert np.linalg.norm(p['Jc']@c)<1e-11
    assert p['r'][0]>0


def test_oblique_sphere_and_ellipsoid_proxy_errors_are_finite():
    from research.NeuralMoments.models.deeponet.m8_analytic_data import Shape
    from research.NeuralMoments.models.deeponet.m13_resolution_benchmark import center_cell_voxel
    for shape in (Shape('sphere',(.05,-.08,.01),(.67,)*3,1.1),
                  Shape('ellipsoid',(.06,.01,-.03),(.61,.73,.57),1.)):
        c=plane_native_c([.24,-.39,1.],.17693)
        truth=ellipsoid_plane_oracle(shape.center,shape.axes,shape.density,c)
        D=center_cell_voxel(shape,16)
        out=ObliqueCellReference.bind(D).evaluate(c)
        assert out['Jc'] is not None
        assert np.abs(out['r']-truth['r']).mean()<.025
        assert np.abs(out['Jc']-truth['Jc']).mean()<.023


def test_triangle_degree_four_quadrature_against_exact_moments():
    # x/y powers over the reference right triangle: int x^p y^q dA = p!q!/(p+q+2)!
    t=np.array(((0.,0.,0.),(1.,0.,0.),(0.,1.,0.)))
    G=_triangle_gram(t)
    for i,pi in enumerate(((0,0,0),(1,0,0),(0,1,0),(0,0,0))):
        pass
    assert G[4,4]==pytest.approx(1/30.,abs=1e-14)  # ∫x^4 dxdy on triangle
    assert G[0,0]==pytest.approx(.5,abs=1e-14)
    assert G[9,9]==pytest.approx(1/180.,abs=1e-14)  # ∫x²y² dxdy

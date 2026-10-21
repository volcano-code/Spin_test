"""Executed M13 regressions; neither exact Cherchi nor original-CAD certification."""
from __future__ import annotations
import unittest
import numpy as np
import trimesh
from .m13_mesh_source import FrozenTriMesh, mesh_to_cells
from .m13_cell_integrals import FrozenCellVolume,unit_vertical_native_c,B_NATIVE


def box_source(*,center=(.07,-.08,.11),extents=(.8,1.1,.7),density=1.3):
    mesh=trimesh.creation.box(extents=extents)
    v=np.asarray(mesh.vertices)+np.asarray(center)
    return FrozenTriMesh(v,mesh.faces,density=density)


class M13MeshIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mesh=box_source()

    def test_01_source_is_closed_and_signed_positive(self):
        self.assertGreater(self.mesh.mesh_moments[0],0)
        self.mesh.verify_frozen()

    def test_02_mesh_mass_exact_box(self):
        self.assertAlmostEqual(self.mesh.mesh_moments[0],1.3*.8*1.1*.7,places=11)

    def test_03_mesh_first_moments_match_shift(self):
        np.testing.assert_allclose(self.mesh.mesh_moments[1:4]/self.mesh.mesh_moments[0],(.07,-.08,.11),atol=1e-12)

    def test_04_mesh_second_moments_match_shift(self):
        m=self.mesh.mesh_moments;ctr=(.07,-.08,.11);size=(.8,1.1,.7)
        np.testing.assert_allclose(m[4:7]/m[0],[ctr[i]**2+size[i]**2/12 for i in range(3)],atol=1e-12)

    def test_05_face_winding_flip_rejected(self):
        with self.assertRaisesRegex(ValueError,'NONPOSITIVE'):
            FrozenTriMesh(self.mesh.vertices,self.mesh.faces[:,::-1])

    def test_06_open_mesh_rejected(self):
        with self.assertRaisesRegex(ValueError,'MESH_OPEN'):
            FrozenTriMesh(self.mesh.vertices,self.mesh.faces[:-1])

    def test_07_duplicate_face_rejected(self):
        with self.assertRaisesRegex(ValueError,'DUPLICATE_FACE'):
            FrozenTriMesh(self.mesh.vertices,np.vstack((self.mesh.faces,self.mesh.faces[0])))

    def test_08_invalid_density_rejected(self):
        with self.assertRaises(ValueError):FrozenTriMesh(self.mesh.vertices,self.mesh.faces,density=-1.)

    def test_09_nonfinite_vertex_rejected(self):
        v=np.array(self.mesh.vertices);v[0,0]=np.nan
        with self.assertRaises(ValueError):FrozenTriMesh(v,self.mesh.faces)

    def test_10_source_hash_changes_with_vertex(self):
        v=np.array(self.mesh.vertices);v[:,0]+=0.001
        self.assertNotEqual(FrozenTriMesh(v,self.mesh.faces,density=1.3).identity,self.mesh.identity)

    def test_11_source_hash_changes_with_density(self):
        self.assertNotEqual(FrozenTriMesh(self.mesh.vertices,self.mesh.faces,density=1.01).identity,self.mesh.identity)

    def test_12_winding_inside_outside(self):
        w=self.mesh.winding(np.array([[.07,-.08,.11],[.99,.9,.8]],dtype=float))
        self.assertGreater(w[0],.9);self.assertLess(abs(w[1]),.1)

    def test_13_voxel_source_hashed_and_frozen(self):
        sample=mesh_to_cells(self.mesh,resolution=8,samples_per_axis=2)
        sample.verify_D(sample.D)
        self.assertFalse(sample.D.flags.writeable)
        self.assertEqual(sample.mesh_sha256,self.mesh.identity)
        self.assertEqual(sample.D.shape,(4,8,8,8))

    def test_14_tamper_voxel_rejected(self):
        sample=mesh_to_cells(self.mesh,resolution=8,samples_per_axis=1)
        data=sample.D.copy();data[1,0,0,0]=.5
        with self.assertRaisesRegex(ValueError,'VOXEL_IDENTITY'):
            sample.verify_D(data)

    def test_15_material_bounds_include_mesh_volume(self):
        sample=mesh_to_cells(self.mesh,resolution=16,samples_per_axis=2)
        lo,hi=sample.conditional_mass_bracket
        self.assertLessEqual(lo,self.mesh.mesh_moments[0]+1e-10)
        self.assertGreaterEqual(hi,self.mesh.mesh_moments[0]-1e-10)

    def test_16_super_sampling_estimate_is_bracketed(self):
        sample=mesh_to_cells(self.mesh,resolution=8,samples_per_axis=3)
        est=float(sample.D[0].astype(float).__mul__(sample.D[1]).sum()*(2/8)**3)
        lo,hi=sample.conditional_mass_bracket
        self.assertLessEqual(lo-1e-8,est);self.assertLessEqual(est,hi+1e-8)


class M13CellIntegralTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.full=np.zeros((4,8,8,8),dtype=np.float32)
        cls.full[0]=1.;cls.full[1]=1.
        cls.integral=FrozenCellVolume(cls.full)

    def test_17_full_cube_ten_moments(self):
        r=self.integral.evaluate(unit_vertical_native_c(-2)).r
        np.testing.assert_allclose(r,[8,0,0,0,8/3,8/3,8/3,0,0,0],atol=1e-12)

    def test_18_cut_cube_closed_form(self):
        h=.21
        r=self.integral.evaluate(unit_vertical_native_c(h)).r
        self.assertAlmostEqual(r[0],4*(1-h),places=11)
        self.assertAlmostEqual(r[3],2*(1-h*h),places=11)
        self.assertAlmostEqual(r[6],4*(1-h**3)/3,places=11)
        self.assertAlmostEqual(r[4],4*(1-h)/3,places=11)

    def test_19_jacobian_symmetric_monomial_and_psd(self):
        cut=self.integral.evaluate(unit_vertical_native_c(.19))
        jq=cut.Jc / B_NATIVE[None]
        np.testing.assert_allclose(jq,jq.T,atol=1e-10)
        self.assertGreater(np.linalg.eigvalsh(jq).min(),-1e-10)

    def test_20_projective_jacobian_radial_zero(self):
        cut=self.integral.evaluate(unit_vertical_native_c(.31))
        np.testing.assert_allclose(cut.Jc@cut.native_c,0,atol=1e-12)

    def test_21_h_directional_fd(self):
        h=.16;eps=1e-5
        c=unit_vertical_native_c(h)
        dc=(unit_vertical_native_c(h+eps)-unit_vertical_native_c(h-eps))/(2*eps)
        fd=(self.integral.evaluate(unit_vertical_native_c(h+eps)).r-
            self.integral.evaluate(unit_vertical_native_c(h-eps)).r)/(2*eps)
        np.testing.assert_allclose(self.integral.evaluate(c).Jc@dc,fd,rtol=1e-7,atol=1e-9)

    def test_22_layer_boundary_rejects_j_only(self):
        cut=self.integral.evaluate(unit_vertical_native_c(.25))
        self.assertEqual(cut.derivative_status,'UNAVAILABLE_AT_CELL_LAYER_CONTACT')
        self.assertIsNone(cut.Jc)
        self.assertTrue(np.isfinite(cut.r).all())

    def test_23_quadratic_and_oblique_rejected(self):
        c=unit_vertical_native_c(.15);c[7]=.01
        with self.assertRaises(ValueError):self.integral.evaluate(c)
        c=unit_vertical_native_c(.15);c[1]=.01
        with self.assertRaises(ValueError):self.integral.evaluate(c)

    def test_24_negative_projective_sign_not_equivalent(self):
        with self.assertRaises(ValueError):self.integral.evaluate(-unit_vertical_native_c(.12))

    def test_25_nonunit_c_rejected(self):
        with self.assertRaises(ValueError):self.integral.evaluate(2*unit_vertical_native_c(.12))

    def test_26_source_mismatch(self):
        x=self.full.copy();x[0,0,0,0]=2
        with self.assertRaisesRegex(ValueError,'SOURCE_MISMATCH'):
            self.integral.assert_source(x)

    def test_27_invalid_fraction_rejected(self):
        x=self.full.copy();x[1,0,0,0]=1.5
        with self.assertRaises(ValueError):FrozenCellVolume(x)

    def test_28_partial_uniform_cell_exact_proxy(self):
        x=self.full.copy();x[1]=.5
        res=FrozenCellVolume(x).evaluate(unit_vertical_native_c(.125))
        self.assertAlmostEqual(res.r[0],.5*4*(1-.125),places=11)

    def test_29_empty_and_full_j_zero(self):
        for h in (-2.,2.):
            c=self.integral.evaluate(unit_vertical_native_c(h))
            np.testing.assert_allclose(c.Jc,0.,atol=0)

    def test_30_mesh_cut_mass_is_in_interval(self):
        mesh=box_source()
        cells=mesh_to_cells(mesh,resolution=8,samples_per_axis=2)
        volume=FrozenCellVolume(cells.D)
        for h in (-.25,.1,.4):
            c=unit_vertical_native_c(h)
            lo,hi=volume.mass_overlap_bracket(c,cells)
            self.assertLessEqual(lo,volume.evaluate(c).r[0]+1e-9)
            self.assertGreaterEqual(hi,volume.evaluate(c).r[0]-1e-9)

    def test_31_source_bound_rejects_other_mesh(self):
        mesh=box_source()
        cells=mesh_to_cells(mesh,resolution=8,samples_per_axis=2)
        cells2=mesh_to_cells(box_source(center=(.12,-.08,.11)),resolution=8,samples_per_axis=2)
        with self.assertRaises(ValueError):
            FrozenCellVolume(cells.D).mass_overlap_bracket(unit_vertical_native_c(.2),cells2)

    def test_32_mesh_proxy_moments_not_alias(self):
        mesh=box_source()
        sample=mesh_to_cells(mesh,resolution=8,samples_per_axis=2)
        proxy=FrozenCellVolume(sample.D).evaluate(unit_vertical_native_c(-2)).r
        # Proxy differs from genuine triangulated source in general; never certify equality.
        self.assertGreater(np.max(np.abs(proxy-mesh.mesh_moments)),1e-7)

if __name__=='__main__':unittest.main()

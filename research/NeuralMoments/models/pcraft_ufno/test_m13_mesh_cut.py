"""Independent convex triangulated mesh P0 oracle and same-source dataset tests."""
from __future__ import annotations
import unittest
import numpy as np
import torch
import trimesh
from .m13_mesh_source import FrozenTriMesh,mesh_to_cells
from .m13_mesh_cut import convex_mesh_vertical_cut
from .m13_cell_integrals import B_NATIVE,unit_vertical_native_c,FrozenCellVolume
from .m13_experiment import (_create_convex_mesh,_load_split,_train_valid,_digest,
                             _fit,_metrics,W5VoxelDeepONet,RealizableUFNOMoment,run)


class M13TriangulatedCutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        box=trimesh.creation.box(extents=(1.2,1.4,1.0))
        cls.cube=FrozenTriMesh(box.vertices+.0,box.faces)
        shell=trimesh.creation.icosphere(subdivisions=2,radius=.6)
        cls.ball=FrozenTriMesh(shell.vertices,shell.faces)

    def test_01_mesh_full_slice_matches_tetra_integral(self):
        m=convex_mesh_vertical_cut(self.cube,-2.)
        np.testing.assert_allclose(m.r,self.cube.mesh_moments,atol=1e-12)
        self.assertEqual(m.derivative_status,'STRICT_FULL')
        np.testing.assert_array_equal(m.Jc,0.)

    def test_02_empty_slice_and_zero_J(self):
        m=convex_mesh_vertical_cut(self.cube,2.)
        np.testing.assert_array_equal(m.r,0.)
        np.testing.assert_array_equal(m.Jc,0.)

    def test_03_box_cut_mass_formula(self):
        cut=convex_mesh_vertical_cut(self.cube,.21)
        self.assertAlmostEqual(cut.r[0],1.2*1.4*(.5-.21),places=10)
        self.assertAlmostEqual(cut.r[3],1.2*1.4*(.5**2-.21**2)/2,places=10)

    def test_04_source_Jq_symmetry_and_PSD(self):
        cut=convex_mesh_vertical_cut(self.cube,.19)
        jq=cut.Jc/B_NATIVE[None]
        np.testing.assert_allclose(jq,jq.T,atol=1e-11)
        self.assertGreaterEqual(np.linalg.eigvalsh(jq).min(),-1e-10)

    def test_05_source_Jc_native_radial_identity(self):
        h=.19;cut=convex_mesh_vertical_cut(self.cube,h)
        np.testing.assert_allclose(cut.Jc@unit_vertical_native_c(h),0,atol=1e-12)

    def test_06_jacobian_agrees_analytic_box_mass(self):
        h=.19
        q=convex_mesh_vertical_cut(self.cube,h)
        c=unit_vertical_native_c(h)
        self.assertAlmostEqual(q.Jc[0,0],1.2*1.4/c[3],places=9)
        self.assertAlmostEqual(q.Jc[0,3],1.2*1.4*h/c[3],places=9)

    def test_07_box_jacobian_local_fd(self):
        h=.13;eps=1e-5
        result=convex_mesh_vertical_cut(self.cube,h)
        dc=(unit_vertical_native_c(h+eps)-unit_vertical_native_c(h-eps))/(2*eps)
        delta=(convex_mesh_vertical_cut(self.cube,h+eps).r-
               convex_mesh_vertical_cut(self.cube,h-eps).r)/(2*eps)
        np.testing.assert_allclose(result.Jc@dc,delta,rtol=1e-8,atol=1e-9)

    def test_08_ball_jacobian_local_fd(self):
        h=.137;eps=1e-5
        result=convex_mesh_vertical_cut(self.ball,h)
        dc=(unit_vertical_native_c(h+eps)-unit_vertical_native_c(h-eps))/(2*eps)
        fd=(convex_mesh_vertical_cut(self.ball,h+eps).r-
            convex_mesh_vertical_cut(self.ball,h-eps).r)/(2*eps)
        np.testing.assert_allclose(result.Jc@dc,fd,rtol=1e-6,atol=1e-8)

    def test_09_vertex_contact_j_unavailable(self):
        result=convex_mesh_vertical_cut(self.ball,.3)
        self.assertIsNone(result.Jc)
        self.assertEqual(result.derivative_status,'UNAVAILABLE_MESH_VERTEX_EVENT')

    def test_10_nonconvex_or_disconnected_rejected(self):
        a=trimesh.creation.box(extents=(.3,.3,.3));b=a.copy()
        a.apply_translation((-.4,0,0));b.apply_translation((.4,0,0))
        union=trimesh.util.concatenate([a,b])
        mesh=FrozenTriMesh(union.vertices,union.faces)
        with self.assertRaisesRegex(ValueError,'NOT_CERTIFIED_CONVEX'):
            convex_mesh_vertical_cut(mesh,.01)

    def test_11_mesh_identity_bound_to_cut(self):
        result=convex_mesh_vertical_cut(self.cube,.14)
        self.assertEqual(result.mesh_sha256,self.cube.identity)
        self.assertFalse(result.source.startswith('W2'))

    def test_12_mass_bounds_include_actual_mesh_cut(self):
        s=mesh_to_cells(self.cube,resolution=8,samples_per_axis=2)
        v=FrozenCellVolume(s.D)
        for h in (-.2,.13,.33):
            lo,hi=v.mass_overlap_bracket(unit_vertical_native_c(h),s)
            exact=convex_mesh_vertical_cut(self.cube,h).r[0]
            self.assertLessEqual(lo,exact+1e-9)
            self.assertGreaterEqual(hi,exact-1e-9)


class M13MatchedTrainingTests(unittest.TestCase):
    def test_13_same_source_and_split_identity(self):
        all_data,_=_load_split(('box','sphere'),131,5)
        fit,val=_train_valid(all_data,131)
        test,_=_load_split(('ellipsoid',),132,2)
        sets=[{e['mesh_sha256'] for e in x[4]} for x in (fit,val,test)]
        self.assertFalse(sets[0]&sets[1]);self.assertFalse(sets[1]&sets[2])
        self.assertFalse(sets[0]&sets[2]);self.assertTrue(all(e['voxel_sha256'] for e in test[4]))
        self.assertEqual(len(test[4]),4)

    def test_14_same_D_for_w5_and_w6(self):
        train,_=_load_split(('box','sphere'),131,5)
        D=train[0][:2];c=train[1][:2]
        with torch.no_grad():
            a=RealizableUFNOMoment(temperature=.12,grid_size=8)
            b=W5VoxelDeepONet()
            self.assertEqual(a.moment(a.encode_geometry(D),c).shape,(2,10))
            self.assertEqual(b.moment(b.encode_geometry(D),c).shape,(2,10))

    def test_15_dataset_sha_repeatable(self):
        x,_=_load_split(('ellipsoid',),139,2)
        y,_=_load_split(('ellipsoid',),139,2)
        self.assertEqual(_digest(x),_digest(y))

    def test_16_mesh_cannot_be_replaced_by_analytic_axes_in_input(self):
        data,_=_load_split(('ellipsoid',),137,2)
        self.assertEqual(data[0].shape[1:],(4,8,8,8))
        self.assertTrue(all('axes' not in x and 'center' not in x for x in data[4]))

    def test_17_neural_smoke_training_both(self):
        torch.set_num_threads(1)
        data,_=_load_split(('box','sphere'),137,5)
        fit,val=_train_valid(data,137)
        for cls in (RealizableUFNOMoment,W5VoxelDeepONet):
            torch.manual_seed(137)
            model=cls(temperature=.12,grid_size=8) if cls is RealizableUFNOMoment else cls()
            receipt=_fit(model,fit,val,seed=137,steps=2)
            self.assertEqual(receipt['steps_executed'],2)
            self.assertTrue(np.isfinite(_metrics(model,val)['r_mae']))

    def test_18_reject_invalid_training_budget(self):
        with self.assertRaises(ValueError):run(seeds=(131,131),include_neural=False)

    def test_19_source_identity_differs_for_mesh_tessellation(self):
        m1=trimesh.creation.icosphere(subdivisions=1,radius=.6)
        m2=trimesh.creation.icosphere(subdivisions=2,radius=.6)
        self.assertNotEqual(FrozenTriMesh(m1.vertices,m1.faces).identity,
                            FrozenTriMesh(m2.vertices,m2.faces).identity)

    def test_20_no_native_admission_claim(self):
        from .m13_experiment import SOURCE_POLICY
        self.assertNotIn('W2',SOURCE_POLICY.replace('NOT_W2',''))
        self.assertIn('NOT_W2',SOURCE_POLICY)

if __name__=='__main__':unittest.main()

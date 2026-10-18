"""Exact analytic P0 audit and executed integration smoke for W6 M2.

Run: python -m unittest research.NeuralMoments.models.pcraft_ufno.test_stage2 -v
"""
import math
import unittest

import numpy as np
import torch

from .analytic_cut import (B_NATIVE_TO_MONOMIAL, GeometrySpec, POWERS,
    assert_disjoint_family_splits, sample_dataset, vertical_cut_truth,
    voxel_geometry)
from .experiment_stage2 import run
from .fixed_moments import merge_fixed_moments
from .teacher_gate import (KNOWN_PRE_W0_SCHEMA, TeacherUnavailable,
                           inspect_teacher_manifest, require_native_teacher)


class W6Stage2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        np.random.seed(19)
        torch.manual_seed(19)

    def test_w0_order_and_native_cross_factor(self):
        self.assertEqual(POWERS[7:], ((0,1,1),(1,0,1),(1,1,0)))
        self.assertEqual(list(np.diag(B_NATIVE_TO_MONOMIAL)),[1.]*7+[2.]*3)
        p=np.array((.21,-.12,.33))
        c=np.arange(1,11,dtype=float)/13
        direct=(c[0]+c[1]*p[0]+c[2]*p[1]+c[3]*p[2]
                +c[4]*p[0]**2+c[5]*p[1]**2+c[6]*p[2]**2
                +2*c[7]*p[1]*p[2]+2*c[8]*p[0]*p[2]+2*c[9]*p[0]*p[1])
        polynomial=np.array([np.prod(p**k) for k in POWERS]) @ B_NATIVE_TO_MONOMIAL @ c
        self.assertAlmostEqual(direct,polynomial,places=14)

    def test_box_cut_volume_and_surface(self):
        spec=GeometrySpec('box',(0,0,0),(1,1,1))
        c,r,J=vertical_cut_truth(spec,0)
        self.assertTrue(np.allclose(r[:4],[4,0,0,2],atol=1e-13))
        self.assertAlmostEqual(r[4],4/3,places=12)
        self.assertAlmostEqual(r[6],4/3,places=12)
        self.assertAlmostEqual(J[0,0],4,places=12)
        self.assertTrue(np.isfinite(J).all())

    def test_sphere_cap_matches_w0_reference(self):
        # Matches published W0 sphere_cap(1,.2) and surface Gram formula.
        s=GeometrySpec('sphere',(0,0,0),(1,1,1))
        c,r,J=vertical_cut_truth(s,.2)
        expected_mass=math.pi*(2/3-.2+.2**3/3)
        self.assertAlmostEqual(r[0],expected_mass,places=13)
        self.assertAlmostEqual(r[3],math.pi*(1-.2**2)**2/4,places=13)
        self.assertAlmostEqual(J[0,0],math.pi*(1-.2**2)*np.linalg.norm([-.2,1]),places=12)

    def test_ellipsoid_transform_matches_raw_full_ellipsoid(self):
        s=GeometrySpec('ellipsoid',(.1,-.2,.3),(.4,.55,.75),density=1.4)
        _,r,_=vertical_cut_truth(s,-.999999)
        mass=4*math.pi/3*math.prod(s.axes)*s.density
        self.assertAlmostEqual(r[0],mass,places=9)
        self.assertAlmostEqual(r[1],mass*s.center[0],places=9)
        self.assertAlmostEqual(r[9],mass*s.center[0]*s.center[1],places=9)
        self.assertAlmostEqual(r[4],mass*(s.center[0]**2+s.axes[0]**2/5),places=9)

    def test_smooth_native_jacobian_not_symmetric_but_Jq_is(self):
        for family in ('box','sphere','ellipsoid'):
            axes=(.65,.5,.8) if family!='sphere' else (.6,.6,.6)
            spec=GeometrySpec(family,(.07,-.06,.13),axes)
            c,r,J=vertical_cut_truth(spec,.28)
            H=J @ np.linalg.inv(B_NATIVE_TO_MONOMIAL)
            self.assertLess(np.max(abs(H-H.T)),1e-12)
            self.assertGreater(np.max(abs(J-J.T)),1e-7)
            self.assertGreaterEqual(np.linalg.eigvalsh(H).min(),-1e-11)
            self.assertLess(np.max(abs(J@c)),1e-11)

    def test_jacobian_plane_parameters_agree_with_finite_difference(self):
        for family in ('box','sphere','ellipsoid'):
            spec=GeometrySpec(family,(.04,-.05,.14),
                (.55,.55,.55) if family=='sphere' else (.5,.65,.8))
            c,r,J=vertical_cut_truth(spec,.32)
            for idx in (0,3):
                d=np.zeros(10); d[idx]=1e-5
                cc_plus=c+d;cc_minus=c-d
                h_plus=(-cc_plus[0]/cc_plus[3]-spec.center[2])/spec.axes[2]
                h_minus=(-cc_minus[0]/cc_minus[3]-spec.center[2])/spec.axes[2]
                r_plus=vertical_cut_truth(spec,h_plus)[1]
                r_minus=vertical_cut_truth(spec,h_minus)[1]
                fd=(r_plus-r_minus)/(2e-5)
                self.assertLess(np.max(abs(fd-J[:,idx])),2e-8)

    def test_positive_projective_sign_is_not_identified(self):
        spec=GeometrySpec('box',(0,0,0),(.6,.6,.6))
        c,_,J=vertical_cut_truth(spec,.2)
        self.assertGreater(c[3],0)
        self.assertEqual(np.linalg.norm(c).round(12),1.0)
        self.assertGreater(abs(J[0,0]),0)

    def test_deterministic_family_holdout_and_voxel_shape(self):
        a=sample_dataset(('box','sphere'),per_family=3,seed=19)
        b=sample_dataset(('box','sphere'),per_family=3,seed=19)
        t=sample_dataset(('ellipsoid',),per_family=3,seed=20)
        assert_disjoint_family_splits(a,t)
        self.assertTrue(torch.equal(a[0],b[0]))
        self.assertTrue(torch.equal(a[1],b[1]))
        self.assertEqual(a[4],b[4])
        self.assertEqual(tuple(a[0].shape),(12,4,8,8,8))
        self.assertEqual(len({m['geometry_id'] for m in a[4]}),6)
        self.assertTrue(torch.all(a[0][:,2:]==0))
        with self.assertRaises(ValueError):
            assert_disjoint_family_splits(a,a)
        with self.assertRaises(ValueError):
            GeometrySpec('sphere',(0,0,0),(.5,.6,.5))

    def test_fixed_material_added_once_j_unchanged(self):
        design=torch.ones(2,10,requires_grad=True)
        dJ=torch.eye(10).expand(2,-1,-1).clone()
        fixed=torch.full((2,10),3.)
        total,outJ=merge_fixed_moments(design,dJ,fixed)
        self.assertTrue(torch.equal(total,design+fixed))
        self.assertTrue(torch.equal(outJ,dJ))
        total.sum().backward()
        self.assertTrue(torch.equal(design.grad,torch.ones_like(design)))
        with self.assertRaises(ValueError):
            merge_fixed_moments(design,dJ,torch.ones(1,10))

    def test_teacher_gate_rejects_w2_zero_manifest(self):
        manifest={"schema":KNOWN_PRE_W0_SCHEMA,
            "status":"ADAPTER_SMOKE_ONLY","native_teacher_runs":0,
            "training_samples":0,"pending_dependency":"W0 MomentContractV1"}
        report=inspect_teacher_manifest(manifest)
        self.assertFalse(report['admissible'])
        self.assertGreaterEqual(len(report['blockers']),4)
        with self.assertRaises(TeacherUnavailable):
            require_native_teacher(manifest)
        # A forged "ready" flag must not silently pass unpinned W2.
        with self.assertRaises(TeacherUnavailable):
            require_native_teacher({"schema":"unknown","status":"NATIVE_VERIFIED",
                                    "native_teacher_runs":100,"training_samples":100})

    def test_train_evaluation_and_query_adaptation_cpu(self):
        result=run(seed=19,steps=2,per_family=2,grid_size=8,repetitions=2)
        self.assertEqual(result['status'],'ANALYTIC_P0_CUT_SMOKE_NOT_W2_TEACHER')
        self.assertEqual(result['train_examples'],8)
        self.assertEqual(result['test_examples'],4)
        self.assertTrue(12500<result['parameters_real']<14500)
        self.assertFalse(result['W5_existing_report_comparable'])
        for arm in result['arms'].values():
            self.assertTrue(math.isfinite(arm['heldout']['r_mae']))
            self.assertLess(arm['heldout']['projective_radial_Jc_c_max'],1e-5)
            self.assertEqual(sorted(arm['adaptation']),['0','1','2'])
            self.assertEqual(arm['adaptation']['2']['teacher_queries'],2)
            self.assertGreater(arm['latency']['cached_J_10x10']['median_ms'],0)


if __name__=='__main__':
    unittest.main()

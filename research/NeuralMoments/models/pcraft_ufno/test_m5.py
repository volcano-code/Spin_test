"""W6 M5 local CPU mathematical and experiment regression tests.

Run from repo root:
  python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m5 -v
"""
from __future__ import annotations

import math
import unittest
from unittest.mock import patch

import numpy as np
import torch

from .m5_potential import ConvexPotentialMoment, quadrature_monomials, MONOMIAL_POWERS
from .m5_experiment import NAMES, CONFIG, create_model, report_run
from .m4_experiment import (dataset_digest, split_by_geometry, encoded, metrics)
from .analytic_cut import (GeometrySpec, sample_dataset, vertical_cut_truth,
                           assert_disjoint_family_splits)
from .fixed_moments import merge_fixed_moments
from .teacher_gate import require_native_teacher, TeacherUnavailable
from .m4_lite_model import num_real_parameters


class TestW6M5Potential(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(19)

    @staticmethod
    def sample(model, batch=1, dtype=torch.double):
        D=torch.ones(batch,4,8,8,8,dtype=torch.float32)
        z=model.encode_geometry(D).detach().to(dtype)
        c=torch.tensor([-.25,.10,-.04,1.0,.02,.01,-.03,.08,-.04,.02],
                       dtype=dtype).unsqueeze(0).expand(batch,-1).clone()
        return z,c

    def test_w0_monomial_and_cross_terms(self):
        self.assertEqual(MONOMIAL_POWERS[7:],((0,1,1),(1,0,1),(1,1,0)))
        m=quadrature_monomials(4)
        self.assertEqual(tuple(m.shape),(64,10))
        self.assertTrue(torch.equal(m[:,0],torch.ones(64)))
        for i,j,k in ((7,2,3),(8,1,3),(9,1,2)):
            self.assertTrue(torch.allclose(m[:,i],m[:,j]*m[:,k]))
        z=torch.tensor([.23,.39,.47])
        c=torch.arange(1.,11.)
        entries=tuple(float(x) for x in torch.cat((torch.ones(1),z,z**2,
                 torch.stack((z[1]*z[2],z[0]*z[2],z[0]*z[1])))))
        expected=sum(float(c[i])*entries[i]*(2 if i>=7 else 1) for i in range(10))
        actual=sum(float(c[i])*entries[i]*([1]*7+[2]*3)[i] for i in range(10))
        self.assertAlmostEqual(expected,actual,places=13)

    def test_count_matches_w5_within_5_percent(self):
        params={n:num_real_parameters(create_model(n,19)) for n in NAMES}
        self.assertEqual(params,{'lite_potential_4':13528,'lite_potential_6':13448,
            'lite_potential_8':13840,'lite_bottleneck':13746,
            'w5_deeponet':13674,'w5_geometry_mlp':13482})
        self.assertLess(max(params.values())/min(params.values()),1.05)
        for name in CONFIG:
            self.assertIsInstance(create_model(name,19).encoder.head,torch.nn.Identity)

    def test_potential_autograd_gradient_in_native_c(self):
        for grid,hidden in ((4,60),(6,32),(8,16)):
            model=ConvexPotentialMoment(points_per_axis=grid,hidden=hidden)
            z,c=self.sample(model,batch=2)
            c.requires_grad_(True)
            potential=model.potential(z,c)
            grads=torch.autograd.grad(potential.sum(),c)[0]
            actual=model.moment(z,c)
            expected=actual*model.native_B
            self.assertTrue(torch.allclose(grads,expected,rtol=1e-9,atol=1e-9))

    def test_autodiff_hessian_matches_native_J(self):
        model=ConvexPotentialMoment()
        z,c=self.sample(model)
        nativeB=model.native_B.double()
        gradient_hessian=torch.autograd.functional.hessian(
            lambda cc:model.potential(z,cc.unsqueeze(0))[0], c[0])
        J=model.jacobian(z,c)[0]
        self.assertTrue(torch.allclose(gradient_hessian /nativeB[:,None],J,atol=1e-8,rtol=1e-8))
        self.assertTrue(torch.allclose(gradient_hessian,gradient_hessian.T,atol=1e-12))

    def test_full_J_finite_difference(self):
        model=ConvexPotentialMoment(points_per_axis=6,hidden=32)
        z,c=self.sample(model)
        J=model.jacobian(z,c)[0]
        numeric=[]
        for col in range(10):
            delta=torch.zeros_like(c)
            delta[:,col]=1e-5
            numeric.append(((model.moment(z,c+delta)-model.moment(z,c-delta))/(2e-5))[0])
        finite=torch.stack(numeric,-1)
        self.assertTrue(torch.allclose(J,finite,rtol=2e-5,atol=3e-7))

    def test_exact_Jq_symmetry_PSD_and_radial_null(self):
        model=ConvexPotentialMoment(points_per_axis=6,hidden=32)
        z,c=self.sample(model,batch=4)
        c[1,7]=-.12;c[2,8]=.15;c[3,9]=-.25
        B=model.native_B.double()
        J=model.jacobian(z,c)
        H=J/B[None,None,:]
        self.assertLess(float((H-H.transpose(-1,-2)).abs().max()),1e-10)
        self.assertGreater(float(torch.linalg.eigvalsh(H).min()),-1e-9)
        self.assertLess(float(torch.bmm(J,c.unsqueeze(-1)).abs().max()),1e-10)
        # W0: native Jc is generally *not* symmetric when cross terms matter.
        self.assertGreater(float((J[3]-J[3].T).abs().max()),1e-6)

    def test_projective_positive_scaling_and_sign(self):
        model=ConvexPotentialMoment()
        z,c=self.sample(model)
        r=model.moment(z,c)
        J=model.jacobian(z,c)
        for scale in (.3,2.,10.):
            self.assertTrue(torch.allclose(model.moment(z,c*scale),r,rtol=1e-11,atol=1e-11))
            self.assertTrue(torch.allclose(model.jacobian(z,c*scale),J/scale,rtol=1e-10,atol=1e-10))
            self.assertTrue(torch.allclose(model.potential(z,c*scale),scale*model.potential(z,c),rtol=1e-11,atol=1e-11))
        self.assertGreater(float((model.moment(z,c)-model.moment(z,-c)).abs().max()),.05)

    def test_potential_convexity_without_degenerate_midpoint(self):
        model=ConvexPotentialMoment()
        z,c=self.sample(model)
        shifted=c.clone();shifted[0,0]=.4;shifted[0,1]=-.5;shifted[0,9]=.13
        middle=(c+shifted)/2
        self.assertLessEqual(float(model.potential(z,middle)),
            .5*float(model.potential(z,c)+model.potential(z,shifted))+1e-11)

    def test_quadrature_nonnegative_weights_and_zero_bad_inputs(self):
        model=ConvexPotentialMoment()
        z,c=self.sample(model)
        self.assertTrue((z>0).all())
        self.assertTrue((z<model.voxel_volume.double()).all())
        for bad in (torch.zeros_like(c),torch.full_like(c,float('nan')),
                    torch.ones(1,9,dtype=c.dtype)):
            with self.assertRaises(ValueError):model.moment(z,bad)
        badz=z.clone();badz[:,0]=-0.1
        with self.assertRaises(ValueError):model.jacobian(badz,c)
        with self.assertRaises(ValueError):ConvexPotentialMoment(smoothing=0)
        with self.assertRaises(ValueError):ConvexPotentialMoment(points_per_axis=1)

    def test_cache_geometry_one_time_multiple_c(self):
        model=ConvexPotentialMoment().eval()
        D=torch.rand(1,4,8,8,8)
        c=self.sample(model)[1].float()
        with patch.object(model,'encode_geometry',wraps=model.encode_geometry) as tracked:
            z=model.encode_geometry(D)
            for shift in (0.,-.10,.10):
                cc=c.clone();cc[:,0]+=shift
                self.assertEqual(tuple(model.moment(z,cc).shape),(1,10))
                self.assertEqual(tuple(model.jacobian(z,cc).shape),(1,10,10))
            self.assertEqual(tracked.call_count,1)

    def test_encoder_and_weight_training_gradients(self):
        model=ConvexPotentialMoment().train()
        data=sample_dataset(('box','sphere'),per_family=2,seed=19)
        z=model.encode_geometry(data[0][:2]);r=model.moment(z,data[1][:2]);J=model.jacobian(z,data[1][:2])
        loss=(r-data[2][:2]).square().mean()+.5*(J-data[3][:2]).square().mean()
        loss.backward()
        self.assertGreater(float(model.weight_head[-1].weight.grad.abs().sum()),0)
        self.assertGreater(float(model.encoder.lift.weight.grad.abs().sum()),0)
        self.assertTrue(torch.isfinite(model.weight_head[-1].weight.grad).all())

    def test_w0_analytic_reference_is_symmetric_only_after_B_inv(self):
        sp=GeometrySpec('ellipsoid',(.06,-.07,.02),(.62,.44,.69))
        c,r,J=vertical_cut_truth(sp,.13)
        H=J/np.array([1.]*7+[2.]*3)[None,:]
        self.assertLess(float(np.max(abs(H-H.T))),1e-12)
        self.assertGreater(float(np.max(abs(J-J.T))),1e-7)
        self.assertGreater(float(np.min(np.linalg.eigvalsh(H))),-1e-9)

    def test_analytic_data_same_as_frozen_M3_three_seeds(self):
        expected={19:'7b65ebbb3e5d32e82ff7ee23a1f88978fa4100902b67f63e16b0fdc2df54e087',
                  23:'d36d707cbf7ecdd0089f66fea3f8784a200830f09a2e0b5a60790ce6028562e7',
                  29:'25eece482d68d864064bfcc7785226785afc41307f56978f2f027ba4ac838394'}
        for seed,expected_sha in expected.items():
            train=sample_dataset(('box','sphere'),per_family=20,seed=seed)
            test=sample_dataset(('ellipsoid',),per_family=20,seed=seed+1)
            self.assertEqual(dataset_digest(train),expected_sha)
            assert_disjoint_family_splits(train,test)
            tr,val,_=split_by_geometry(train,seed)
            self.assertFalse({x['geometry_id'] for x in tr[4]} & {x['geometry_id'] for x in val[4]})

    def test_fixed_material_cached_once_and_derivative_excludes_F(self):
        model=ConvexPotentialMoment()
        z,c=self.sample(model)
        r=model.moment(z,c);J=model.jacobian(z,c)
        fixed=torch.ones_like(r)*.2
        total,derivative=merge_fixed_moments(r,J,fixed)
        self.assertTrue(torch.allclose(total,r+fixed))
        self.assertTrue(torch.equal(derivative,J))

    def test_preW0_W2_teacher_still_rejected(self):
        with self.assertRaises(TeacherUnavailable):require_native_teacher({
            'schema':'w2-cherchi-teacher-v1-pre-w0','status':'ADAPTER_SMOKE_ONLY',
            'native_teacher_runs':0,'training_samples':0})

    def test_cpu_end_to_end_all_models(self):
        report=report_run(seeds=(19,),steps=2,per_family=3,repeats=1)
        self.assertEqual(report['W2_real_teacher_samples'],0)
        self.assertEqual(report['status'],'ANALYTIC_P0_ONLY_NOT_NATIVE_CHERCHI')
        self.assertFalse(report['feature_parity'])
        self.assertEqual(len(report['experiments'][0]['models']),6)
        for name in NAMES:
            item=report['experiments'][0]['models'][name]
            self.assertTrue(math.isfinite(item['heldout']['r_mae']))
            self.assertTrue(math.isfinite(item['heldout']['J_mae']))
            self.assertGreater(item['timing']['cold_voxel_to_head']['median_ms'],0)
        for name in CONFIG:
            self.assertLess(report['experiments'][0]['models'][name]['structure']['Jq_max_asymmetry'],1e-5)

    def test_parameter_capacity_and_duplicate_seeds_fail(self):
        with self.assertRaises(ValueError):report_run(seeds=(19,19),steps=1,per_family=3,repeats=1)
        with self.assertRaises(ValueError):report_run(seeds=(19,),steps=1,per_family=3,repeats=1,
                                                       names=('lite_potential_8','w5_deeponet','lite_potential_8'))


if __name__=='__main__':unittest.main()

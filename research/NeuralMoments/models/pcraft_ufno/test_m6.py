"""M6 independent mathematical, W0/W2 gate, and experiment regressions.

python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m6 -v
"""
from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch

from .m6_gauss_potential import GaussPotentialMoment, gauss_rule
from .m6_teacher_handoff import (AdmissionBlocked, W0_PIN, W2_PIN,
    gate_teacher_manifest, inspect_w0_candidate, record_handoff,
    require_teacher_admission)
from .m6_experiment import run, make_model, MODES, CONFIRMATORY, gradient_decision_diagnostic, moment_support_diagnostic
from .m5_potential import ConvexPotentialMoment
from .m6_safe_inference import native_quadric_interval,region_states,guarded_evaluate
from .m6_moment_guard import (physical_moment_diagnostic, require_necessary_physical_moments,
                              PhysicalAdmissibilityFailure, hard_quadrature_moments)
from .m4_lite_model import num_real_parameters
from .analytic_cut import sample_dataset
from .m4_experiment import dataset_digest


class W6M6Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(19)

    def make(self,rule='gauss',prior=0.):
        return GaussPotentialMoment(rule=rule, prior_fraction=prior,
                                    points_per_axis=6,hidden=32).eval()

    def example(self,model,batch=2):
        D=torch.zeros(batch,4,8,8,8)
        D[:,0:2]=torch.rand(batch,1,8,8,8)
        with torch.no_grad():z=model.encode_geometry(D).double()
        c=torch.tensor([-.34,.1,-.2,1.,.07,-.03,.02,.14,-.01,.04],dtype=torch.float64).repeat(batch,1)
        return D,z,c

    def test_gauss_rule_normalization_and_shape(self):
        nodes,monomials,weights=gauss_rule(6,dtype=torch.float64)
        self.assertEqual(tuple(nodes.shape),(216,3))
        self.assertEqual(tuple(monomials.shape),(216,10))
        self.assertAlmostEqual(float(weights.sum()),8.,places=13)
        self.assertTrue(bool(((weights>0)&(nodes.abs()<1).all(-1)).all()))

    def test_gauss_integrates_monomials_exactly(self):
        p,_,w=gauss_rule(6,dtype=torch.float64)
        self.assertAlmostEqual(float((w*p[:,0]**10).sum()),8/11,places=11)
        self.assertAlmostEqual(float((w*p[:,1]**6*p[:,2]**4).sum()),8/(7*5),places=11)
        self.assertAlmostEqual(float((w*p[:,0]*p[:,1]).sum()),0.,places=13)
        self.assertAlmostEqual(float((w*p[:,0]**2).sum()),8/3,places=12)

    def test_invalid_quadrature_and_prior(self):
        for n in (1,0,2.5,True):
            with self.assertRaises(ValueError):gauss_rule(n)
        for s in (-.1,1.,float('nan'),float('inf')):
            with self.assertRaises(ValueError):self.make(prior=s)
        with self.assertRaises(ValueError):GaussPotentialMoment(rule='bogus')

    def test_exact_M5_midpoint_is_same_model(self):
        torch.manual_seed(191)
        baseline=ConvexPotentialMoment(points_per_axis=6,hidden=32)
        torch.manual_seed(191)
        new=self.make(rule='midpoint')
        D,z,c=self.example(new)
        with torch.no_grad():
            z0=baseline.encode_geometry(D).double()
        self.assertTrue(torch.equal(z,z0))
        self.assertTrue(torch.equal(new.moment(z,c),baseline.moment(z0,c)))
        self.assertTrue(torch.equal(new.jacobian(z,c),baseline.jacobian(z0,c)))
        self.assertEqual(num_real_parameters(new),num_real_parameters(baseline))

    def test_gauss_moments_are_cache_only(self):
        model=self.make()
        D,z,c=self.example(model)
        with patch.object(model.encoder,'encode_geometry',wraps=model.encoder.encode_geometry) as wrapped:
            z=model.encode_geometry(D)
            for t in (.7,1.,1.5):
                r=model.moment(z,c.float()*t)
                j=model.jacobian(z,c.float()*t)
                self.assertEqual(r.shape,(2,10))
                self.assertEqual(j.shape,(2,10,10))
            self.assertEqual(wrapped.call_count,1)

    def test_gauss_exact_autograd_potential_gradient(self):
        model=self.make()
        D,z,c=self.example(model)
        c.requires_grad_()
        gradient=torch.autograd.grad(model.potential(z,c).sum(),c)[0]
        self.assertTrue(torch.allclose(gradient,model.moment(z,c)*model.native_B.double(),atol=1e-11,rtol=1e-11))

    def test_gauss_full_J_matches_finite_difference(self):
        model=self.make()
        _,z,c=self.example(model,1)
        J=model.jacobian(z,c)[0]
        fd=[]
        for idx in range(10):
            delta=torch.zeros_like(c);delta[:,idx]=1e-5
            fd.append(((model.moment(z,c+delta)-model.moment(z,c-delta))/(2e-5))[0])
        self.assertTrue(torch.allclose(J,torch.stack(fd,-1),atol=3e-7,rtol=2e-5))

    def test_gauss_exact_Jq_symmetry_psd_and_radial(self):
        for prior in (0.,.25):
            model=self.make(prior=prior)
            D,z,c=self.example(model,2)
            c[1,7]=-.27
            H=model.jacobian(z,c)/model.native_B.double()[None,None,:]
            self.assertLess(float((H-H.transpose(-1,-2)).abs().max()),3e-10)
            self.assertGreater(float(torch.linalg.eigvalsh(H).min()),-3e-10)
            self.assertLess(float(torch.bmm(model.jacobian(z,c),c.unsqueeze(-1)).abs().max()),3e-10)

    def test_projective_positive_scaling_not_negative_sign(self):
        model=self.make()
        _,z,c=self.example(model,1)
        r=model.moment(z,c);J=model.jacobian(z,c)
        for k in (.3,2.,5.):
            self.assertTrue(torch.allclose(r,model.moment(z,k*c),atol=1e-11,rtol=1e-11))
            self.assertTrue(torch.allclose(J,model.jacobian(z,k*c)*k,atol=1e-10,rtol=1e-10))
        self.assertGreater(float((r-model.moment(z,-c)).abs().max()),.1)

    def test_learned_positive_weight_bounds_with_gauss(self):
        model=self.make(prior=.25)
        _,z,_=self.example(model)
        self.assertTrue(bool((z>=0).all()))
        self.assertTrue(bool((z<=model.voxel_volume.double()[None,:]).all()))
        self.assertAlmostEqual(float(model.voxel_volume.sum()),8.,places=5)

    def test_prior_is_sampling_label_blind_and_affects_weights(self):
        torch.manual_seed(20)
        no_prior=self.make()
        torch.manual_seed(20)
        prior=self.make(prior=.25)
        D=torch.zeros(1,4,8,8,8)
        D[:,1]=1.
        w0=no_prior.encode_geometry(D)
        w=prior.encode_geometry(D)
        expected=.75*w0+.25*prior.voxel_volume[None,:]
        self.assertTrue(torch.allclose(w,expected,atol=1e-7))
        D[:,1]=-1.
        with self.assertRaises(ValueError):prior.encode_geometry(D)

    def test_prior_input_requires_finite_probabilities(self):
        model=self.make(prior=.25)
        D=torch.ones(1,4,8,8,8)
        D[:,1,1]=float('nan')
        with self.assertRaises(ValueError):model.encode_geometry(D)

    def test_training_gradients_reach_encoder_and_head(self):
        model=self.make(prior=.25).train()
        D,c,r,J,_=sample_dataset(('box',),per_family=2,seed=19)
        z=model.encode_geometry(D[:2]);pr=model.moment(z,c[:2]);pj=model.jacobian(z,c[:2])
        ((pr-r[:2]).square().mean()+.5*(pj-J[:2]).square().mean()).backward()
        self.assertGreater(float(model.weight_head[-1].weight.grad.abs().sum()),0.)
        self.assertGreater(float(model.encoder.lift.weight.grad.abs().sum()),0.)

    def test_dataset_uses_exact_frozen_m3_seed(self):
        d=sample_dataset(('box','sphere'),per_family=20,seed=19)
        self.assertEqual(dataset_digest(d),'7b65ebbb3e5d32e82ff7ee23a1f88978fa4100902b67f63e16b0fdc2df54e087')

    def test_equal_capacity_all_three_variants(self):
        p=[num_real_parameters(make_model(k,19)) for k in MODES]
        self.assertEqual(p,[13448,13448,13448])

    def test_w2_preW0_manifest_rejects_zero_and_forged_positive(self):
        fake={'schema':'w2-cherchi-teacher-v1-pre-w0','status':'ADAPTER_SMOKE_ONLY',
              'native_teacher_runs':0,'training_samples':0,'pending_dependency':'W0 MomentContractV1'}
        gated=gate_teacher_manifest(fake)
        self.assertFalse(gated['training_admissible'])
        self.assertEqual(gated['W0_PIN'],W0_PIN)
        self.assertEqual(gated['W2_PIN'],W2_PIN)
        with self.assertRaises(AdmissionBlocked):require_teacher_admission(fake)
        fake.update(status='NATIVE_VERIFIED',native_teacher_runs=100,training_samples=100)
        self.assertFalse(gate_teacher_manifest(fake)['training_admissible'])

    def test_w2_json_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'w2.json'
            p.write_text('{"schema":"w2-cherchi-teacher-v1-pre-w0","native_teacher_runs":0,"training_samples":0}')
            self.assertFalse(record_handoff(p)['training_admissible'])

    def test_w0_contract_import_source_must_be_pinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'wrong.py'
            p.write_text('def validate_record(record): return {"structural_valid":True}')
            with self.assertRaises(AdmissionBlocked):inspect_w0_candidate({},external_w0_validator_path=p)
        with self.assertRaises(AdmissionBlocked):inspect_w0_candidate({},external_w0_validator_path='/missing/W0-validator.py')

    def test_true_gradient_diagnostic_is_not_fake_newton(self):
        name=MODES[0]
        model=make_model(name,19)
        test=sample_dataset(('ellipsoid',),per_family=3,seed=20)
        x=gradient_decision_diagnostic(model,name,test)
        self.assertTrue(math.isfinite(x['quadratic_gradient_mae']))
        self.assertIn('not true Spin',x['interpretation'])

    def test_smoothed_convex_potential_has_negative_empty_mass_counterexample(self):
        for rule in ('midpoint','gauss'):
            model=self.make(rule=rule)
            z=(model.voxel_volume.expand(model.monomials.shape[0])*.5).unsqueeze(0).double()
            c=torch.zeros(1,10,dtype=torch.double);c[:,0]=-1.
            rr=model.moment(z,c)
            jj=model.jacobian(z,c)
            self.assertLess(float(rr[0,0]),-1e-5)
            H=jj/model.native_B.double()[None,None,:]
            self.assertLess(float((H-H.transpose(-1,-2)).abs().max()),1e-10)
            self.assertFalse(bool(physical_moment_diagnostic(rr)['necessary_conditions_pass'].all()))
            with self.assertRaises(PhysicalAdmissibilityFailure):require_necessary_physical_moments(rr)

    def test_hard_quadrature_correct_empty_mass_without_smooth_derivative_claim(self):
        model=self.make(rule='gauss')
        z=(model.voxel_volume.expand(model.monomials.shape[0])*.5).unsqueeze(0).double()
        c=torch.zeros(1,10,dtype=torch.double);c[:,0]=-1.
        rr=hard_quadrature_moments(z,c,model.monomials.double())
        self.assertTrue(torch.equal(rr,torch.zeros_like(rr)))
        self.assertTrue(bool(physical_moment_diagnostic(rr)['necessary_conditions_pass'].all()))
        c[:,0]=1.
        rr=hard_quadrature_moments(z,c,model.monomials.double())
        self.assertAlmostEqual(float(rr[0,0]),4.,places=6)
        self.assertTrue(bool(physical_moment_diagnostic(rr)['necessary_conditions_pass'].all()))

    def test_true_analytic_solid_moments_pass_support_inequalities(self):
        _,_,r,_,_=sample_dataset(('box','sphere','ellipsoid'),per_family=3,seed=26)
        gate=physical_moment_diagnostic(r.double())
        self.assertTrue(bool(gate['necessary_conditions_pass'].all()))
        self.assertTrue(gate['not_a_material_proof'])

    def test_necessary_conditions_reject_negative_covariance_and_outside_cube(self):
        # Zero center, unit mass, negative variance or x beyond the support.
        valid=torch.tensor([[1.,0,0,0,.2,.2,.2,0,0,0]],dtype=torch.double)
        self.assertTrue(bool(physical_moment_diagnostic(valid)['necessary_conditions_pass'].all()))
        bad_cov=valid.clone();bad_cov[:,4]=-0.1
        self.assertFalse(bool(physical_moment_diagnostic(bad_cov)['necessary_conditions_pass'].all()))
        bad_lo=valid.clone();bad_lo[:,1]=2.0
        self.assertFalse(bool(physical_moment_diagnostic(bad_lo)['necessary_conditions_pass'].all()))
        bad_hi=valid.clone();bad_hi[:,4]=2.0
        self.assertFalse(bool(physical_moment_diagnostic(bad_hi)['necessary_conditions_pass'].all()))

    def test_physical_gate_rejects_invalid_reference_box_and_input(self):
        with self.assertRaises(ValueError):physical_moment_diagnostic(torch.ones(1,9))
        with self.assertRaises(ValueError):physical_moment_diagnostic(torch.full((1,10),float('nan')))
        with self.assertRaises(ValueError):physical_moment_diagnostic(torch.ones(1,10),low=(1.,1.,1.),high=(0.,0.,0.))
        with self.assertRaises(ValueError):hard_quadrature_moments(torch.tensor([[-1.]]),torch.ones(1,10),torch.ones(1,10))

    def test_predeclared_post_sweep_pair_equal_parameters(self):
        base=make_model(CONFIRMATORY[0],19)
        gauss=make_model(CONFIRMATORY[1],19)
        self.assertAlmostEqual(base.smoothing,.04)
        self.assertAlmostEqual(gauss.smoothing,.25)
        self.assertEqual(num_real_parameters(base),num_real_parameters(gauss))

    def test_heldout_support_diagnostic_records_counterexample(self):
        model=make_model(MODES[0],19)
        test=sample_dataset(('ellipsoid',),per_family=3,seed=20)
        diagnostic=moment_support_diagnostic(model,MODES[0],test)
        self.assertLess(diagnostic['empty_negative_constant_predicted_mass_mean'],0.)
        self.assertEqual(diagnostic['empty_negative_constant_fraction_rejected'],1.)

    def test_interval_bounds_contain_1000_sampled_quadric_values(self):
        generator=torch.Generator().manual_seed(118)
        c=torch.randn(30,10,generator=generator,dtype=torch.double)
        a,b=native_quadric_interval(c)
        points=torch.rand(1000,3,generator=generator,dtype=torch.double)*2-1
        x,y,z=points.T
        basis=torch.stack((torch.ones_like(x),x,y,z,x*x,y*y,z*z,
                           2*y*z,2*x*z,2*x*y),dim=-1)
        values=c@basis.T
        self.assertTrue(bool((values.min(dim=1).values>=a[:,None].squeeze(-1)-1e-12).all()))
        self.assertTrue(bool((values.max(dim=1).values<=b[:,None].squeeze(-1)+1e-12).all()))

    def test_conservative_region_states_for_cross_and_sign(self):
        c=torch.zeros(4,10,dtype=torch.double)
        c[0,0]=-1.;c[1,0]=1.;c[2,0]=.2;c[2,9]=.5
        c[3,0]=-.7;c[3,4]=-.1;c[3,7]=.2
        states=region_states(c)
        self.assertEqual(states[0],'CERTIFIED_EMPTY')
        self.assertEqual(states[1],'CERTIFIED_FULL')
        self.assertEqual(states[2],'UNDECIDED')
        self.assertEqual(states[3],'CERTIFIED_EMPTY')
        self.assertEqual(region_states(c*3),states)

    def test_guard_fixes_strict_empty_and_full_without_fabricated_J(self):
        model=self.make(rule='gauss')
        z=(model.voxel_volume.expand(model.monomials.shape[0])*.5).unsqueeze(0)
        for constant,mass in ((-1.,0.),(1.,4.)):
            c=torch.zeros(1,10);c[0,0]=constant
            checked=guarded_evaluate(model,z,c)
            self.assertAlmostEqual(float(checked['r'][0,0]),mass,places=5)
            self.assertTrue(bool((checked['Jc']==0).all()))
            self.assertTrue(bool(checked['necessary_conditions_pass'].all()))
            self.assertFalse(checked['independent_CAD_material_certified'])
            self.assertFalse(checked['training_admissible'])

    def test_guard_rejects_physically_invalid_undecided_rows(self):
        model=self.make()
        z=(model.voxel_volume.expand(model.monomials.shape[0])*.5).unsqueeze(0)
        c=torch.zeros(1,10);c[:,3]=1.;c[:,0]=-.01
        checked=guarded_evaluate(model,z,c,reject_invalid=False)
        self.assertEqual(checked['region_state'],('UNDECIDED',))
        self.assertTrue(checked['r'].isfinite().all())
        # Incorrect box arguments reject before labeling anything certified.
        with self.assertRaises(ValueError):guarded_evaluate(model,z,c,low=(1.,1.,1.),high=(0.,0.,0.))

    def test_end_to_end_three_variant_smoke(self):
        r=run(seeds=(19,),steps=2,per_family=3,repeats=1)
        self.assertEqual(r['W2_native_teacher_samples'],0)
        self.assertFalse(r['feature_parity_with_W5'])
        for name in MODES:
            x=r['experiments'][0]['models'][name]
            self.assertTrue(math.isfinite(x['heldout']['r_mae']))
            self.assertGreater(x['timings']['cached_J10x10']['median_ms'],0)
            self.assertLess(x['structure']['Jq_max_asymmetry'],1e-5)


if __name__ == '__main__':
    unittest.main()

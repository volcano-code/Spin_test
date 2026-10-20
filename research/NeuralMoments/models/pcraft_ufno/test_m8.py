"""M8 CPU regression: positive-atomic 0/1/2 analytic support adaptation.

python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m8 -v
"""
import math
import unittest
from unittest.mock import patch

import numpy as np
import torch

from .analytic_cut import GeometrySpec, sample_dataset, vertical_cut_truth, voxel_geometry
from .m4_experiment import dataset_digest
from .m7_experiment import M3_FROZEN_SHA
from .m7_realizable import RealizableUFNOMoment
from .m7_teacher_gate import NativeTeacherNotReady, audit_manifest
from .m8_bounded_adapter import BoundedAtomAdapter, SupportAdmissionError
from .m8_experiment import external_ellipsoid_queries, evaluate_adaptation, run
from .m6_moment_guard import PhysicalAdmissibilityFailure,physical_moment_diagnostic


class TestM8BoundedSupports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(20261020)
        torch.set_num_threads(1)

    def make(self, batch=1, *, dtype=torch.float32, n=4):
        m=RealizableUFNOMoment(points_per_axis=n,temperature=.12).eval()
        D=torch.ones(batch,4,8,8,8,dtype=dtype)
        D[:,2:]=0.
        z=m.encode_geometry(D).detach()
        spec=GeometrySpec('box',(0.,0.,0.),(1.,1.,1.))
        tuples=[vertical_cut_truth(spec,h) for h in (-.35,.25)]
        c=torch.as_tensor(np.stack([p[0] for p in tuples]),dtype=dtype).unsqueeze(0).expand(batch,-1,-1).clone()
        r=torch.as_tensor(np.stack([p[1] for p in tuples]),dtype=dtype).unsqueeze(0).expand(batch,-1,-1).clone()
        return m,D,z,c,r

    def adapt(self, model,D,z,c,r,k,**kw):
        return BoundedAtomAdapter(model,D,z,c[:,:k],r[:,:k],source='ANALYTIC_P0',**kw)

    def test_zero_query_keeps_base_exactly(self):
        m,D,z,c,r=self.make()
        a=self.adapt(m,D,z,c,r,0)
        self.assertTrue(torch.equal(a.weights,z))
        self.assertTrue(torch.equal(a.predict(c[:,0]),m.moment(z,c[:,0])))
        self.assertEqual(a.audit.query_count,0)
        self.assertEqual(a.audit.iterations,(0,))

    def test_one_query_bounded_and_monotone(self):
        m,D,z,c,r=self.make()
        a=self.adapt(m,D,z,c,r,1)
        self.assertGreaterEqual(float(a.weights.min()),0.)
        self.assertLessEqual(float((a.weights-a.capacity).max()),1e-7)
        self.assertLessEqual(a.audit.support_loss_after[0],a.audit.support_loss_before[0]+1e-12)
        self.assertFalse(a.weights.requires_grad)

    def test_two_query_bounded_and_monotone(self):
        m,D,z,c,r=self.make()
        a=self.adapt(m,D,z,c,r,2)
        self.assertTrue(bool((a.weights>=0).all()))
        self.assertTrue(bool((a.weights<=a.capacity+1e-7).all()))
        self.assertLessEqual(a.audit.support_loss_after[0],a.audit.support_loss_before[0]+1e-11)

    def test_geometry_encoded_once_many_inference_controls(self):
        m,D,z,c,r=self.make()
        with patch.object(m,'encode_geometry',wraps=m.encode_geometry) as counted:
            z2=m.encode_geometry(D).detach()
            a=self.adapt(m,D,z2,c,r,2)
            for t in (-.15,.25,.51):
                x=c[:,0].clone();x[:,0]=t
                _=a.predict(x);_=a.jacobian(x)
            self.assertEqual(counted.call_count,1)

    def test_positive_projective_scaling_survives_adaptation(self):
        m,D,z,c,r=self.make()
        a=self.adapt(m,D,z,c,r,2)
        self.assertTrue(torch.allclose(a.predict(c[:,0]),a.predict(3.3*c[:,0]),atol=1e-6))
        J=a.jacobian(c[:,0]);self.assertLess(float((J@c[:,0].unsqueeze(-1)).abs().max()),2e-6)
        self.assertFalse(torch.allclose(a.predict(c[:,0]),a.predict(-c[:,0]),atol=1e-5))

    def test_tangent_basis_shape_and_gram_psd(self):
        m,D,z,c,r=self.make(dtype=torch.float32)
        a=self.adapt(m,D,z,c,r,2)
        tangent,basis=a.tangent_jacobian(c[:,0])
        self.assertEqual(tuple(tangent.shape),(1,10,9))
        self.assertEqual(tuple(basis.shape),(1,10,9))
        self.assertLess(float((basis.transpose(-1,-2)@c[:,0].unsqueeze(-1)).abs().max()),2e-6)
        gram=m.projected_q_gram(a.weights,c[:,0])
        self.assertLess(float((gram-gram.transpose(-1,-2)).abs().max()),2e-6)
        self.assertGreaterEqual(float(torch.linalg.eigvalsh(gram).min()),-2e-6)

    def test_adapted_native_jacobian_finite_difference(self):
        m,D,z,c,r=self.make(dtype=torch.float32)
        a=self.adapt(m,D,z,c,r,2)
        probe=c[:,0].double().clone();w=a.weights.double();J=m.jacobian(w,probe)
        for axis in (0,3,7,9):
            d=torch.zeros_like(probe);d[:,axis]=1e-6
            fd=(m.moment(w,probe+d)-m.moment(w,probe-d))/(2e-6)
            self.assertTrue(torch.allclose(fd,J[:,:,axis],atol=2e-8,rtol=3e-5))

    def test_adapted_physical_moments_across_controls(self):
        m,D,z,c,r=self.make(n=6)
        a=self.adapt(m,D,z,c,r,2)
        for theta in (.1,.4,-.8):
            x=c[:,0].clone();x[:,3]=theta
            moment=a.predict(x)
            self.assertTrue(bool(physical_moment_diagnostic(moment,tol=1e-6)['necessary_conditions_pass'].all()))

    def test_strict_empty_and_full_remain_safe(self):
        m,D,z,c,r=self.make()
        a=self.adapt(m,D,z,c,r,2)
        q=torch.zeros(1,10);q[:,0]=-1.
        empty=a.safe_predict(q)
        self.assertEqual(empty['region_state'],('CERTIFIED_EMPTY',))
        self.assertTrue(torch.equal(empty['r'],torch.zeros_like(empty['r'])))
        self.assertTrue(torch.equal(empty['Jc'],torch.zeros_like(empty['Jc'])))
        q[:,0]=1.
        full=a.safe_predict(q)
        self.assertEqual(full['region_state'],('CERTIFIED_FULL',))
        self.assertTrue(bool(full['necessary_conditions_pass'].all()))
        self.assertFalse(full['admitted_for_real_optimizer'])

    def test_void_density_and_occupancy_keep_zero(self):
        m,D,z,c,r=self.make()
        D[:,0]=0;zero=m.encode_geometry(D)
        a=self.adapt(m,D,zero,c,r,1)
        self.assertTrue(torch.equal(a.capacity,torch.zeros_like(a.capacity)))
        self.assertTrue(torch.equal(a.weights,torch.zeros_like(a.weights)))
        self.assertTrue(torch.equal(a.predict(c[:,0]),torch.zeros_like(r[:,0])))

    def test_reject_nonphysical_support_label(self):
        m,D,z,c,r=self.make();bad=r.clone();bad[:,0,0]=-1
        with self.assertRaises(PhysicalAdmissibilityFailure):self.adapt(m,D,z,c,bad,1)

    def test_reject_malformed_support_dimensions(self):
        m,D,z,c,r=self.make()
        with self.assertRaises(ValueError):
            BoundedAtomAdapter(m,D,z,torch.cat((c,c[:,:1]),dim=1),torch.cat((r,r[:,:1]),dim=1),source='ANALYTIC_P0')
        with self.assertRaises(ValueError):BoundedAtomAdapter(m,D,z,c[:,:,:9],r,source='ANALYTIC_P0')
        with self.assertRaises(ValueError):BoundedAtomAdapter(m,D,z,c,r[:,:1],source='ANALYTIC_P0')

    def test_reject_unverified_cached_geometry_cap(self):
        m,D,z,c,r=self.make()
        with self.assertRaises(SupportAdmissionError):self.adapt(m,D,z*100,c,r,0)

    def test_reject_nan_and_invalid_density(self):
        m,D,z,c,r=self.make()
        D[:,0]=-1
        with self.assertRaises(ValueError):self.adapt(m,D,z,c,r,0)
        m,D,z,c,r=self.make();c[:,0,0]=float('nan')
        with self.assertRaises(ValueError):self.adapt(m,D,z,c,r,1)

    def test_reject_unbounded_or_zero_ridge(self):
        m,D,z,c,r=self.make()
        for val in (0.,-1.,float('nan'),float('inf')):
            with self.assertRaises(ValueError):self.adapt(m,D,z,c,r,1,ridge=val)
        with self.assertRaises(ValueError):self.adapt(m,D,z,c,r,1,max_iterations=0)

    def test_no_native_w2_even_if_manifest_forged(self):
        m,D,z,c,r=self.make()
        for label in ('NATIVE_W2','NATIVE_VERIFIED','W2_H8F_ARCHIVED',None):
            with self.assertRaises(NativeTeacherNotReady):
                BoundedAtomAdapter(m,D,z,c,r,source=label)

    def test_two_geometry_batch(self):
        m,D,z,c,r=self.make(batch=2)
        adapter=self.adapt(m,D,z,c,r,2)
        self.assertEqual(tuple(adapter.weights.shape),(2,64))
        self.assertEqual(len(adapter.audit.support_loss_before),2)
        self.assertEqual(tuple(adapter.predict(c[:,0]).shape),(2,10))

    def test_full_box_one_support_improves_unseen_p0(self):
        torch.manual_seed(19)
        m,D,z,c,r=self.make(n=6)
        # True analytic independent box moments, not network pseudo-labels.
        spec=GeometrySpec('box',(0.,0.,0.),(1.,1.,1.))
        queries=[vertical_cut_truth(spec,h) for h in (-.3,-.15,.1,.32,.46)]
        probe_c=torch.as_tensor(np.stack([x[0] for x in queries]),dtype=torch.float32)
        probe_r=torch.as_tensor(np.stack([x[1] for x in queries]),dtype=torch.float32)
        baseline=self.adapt(m,D,z,c,r,0,ridge=1e-4)
        one=self.adapt(m,D,z,c,r,1,ridge=1e-4)
        with torch.no_grad():
            mae0=torch.cat([baseline.predict(cc[None]) for cc in probe_c]).sub(probe_r).abs().mean()
            mae1=torch.cat([one.predict(cc[None]) for cc in probe_c]).sub(probe_r).abs().mean()
        self.assertLess(float(mae1),float(mae0))
        self.assertTrue(bool((one.weights<=one.capacity+1e-6).all()))
        # One-support improvement does NOT prove two-support test improvement.

    def test_current_w2_excluded_81_manifest_gate(self):
        from .m7_teacher_gate import audit_manifest,require_native_training
        mf={'schema':'w2-cherchi-teacher-v2-pre-w0',
            'status':'M10_READONLY_81_ARCHIVE_GATE_PASSED_DERIVATIVE_TRAINING_BLOCKED',
            'native_teacher_runs':0,'training_samples':0,
            'data_splits':{'train':[],'val':[],'test':[],
                'excluded':[{'dataset':'H8f archived candidates','count':81}]},
            'pending_dependency':'W0 certified native stratum missing'}
        self.assertEqual(audit_manifest(mf)['archived_excluded_candidates'],81)
        self.assertFalse(audit_manifest(mf)['admitted_for_training'])
        with self.assertRaises(NativeTeacherNotReady):require_native_training(mf)

    def test_network_weights_not_edited_by_adaptation(self):
        m,D,z,c,r=self.make()
        before=[p.detach().clone() for p in m.parameters()]
        a=self.adapt(m,D,z,c,r,2)
        self.assertTrue(all(torch.equal(p,b) for p,b in zip(m.parameters(),before)))

    def test_repeated_fit_is_deterministic(self):
        m,D,z,c,r=self.make()
        a=self.adapt(m,D,z,c,r,2)
        b=self.adapt(m,D,z,c,r,2)
        self.assertTrue(torch.equal(a.weights,b.weights))
        self.assertEqual(a.audit,b.audit)

    def test_analytic_continuum_can_exceed_sampled_capacity(self):
        m=RealizableUFNOMoment(points_per_axis=6,temperature=.12)
        spec=GeometrySpec('ellipsoid',(.02,.03,-.01),(.6,.49,.66))
        D=voxel_geometry(spec,8).unsqueeze(0)
        z=m.encode_geometry(D).detach()
        truth=vertical_cut_truth(spec,-.4)
        c=torch.from_numpy(truth[0].copy()).float().reshape(1,1,10)
        r=torch.from_numpy(truth[1].copy()).float().reshape(1,1,10)
        a=BoundedAtomAdapter(m,D,z,c,r,source='ANALYTIC_P0')
        self.assertTrue(a.audit.support_mass_exceeds_sampled_capacity[0])
        self.assertGreater(float(r[0,0,0]),float(a.capacity.sum()))
        self.assertTrue(bool((a.weights<=a.capacity+1e-7).all()))

    def test_external_holdout_query_disjoint(self):
        sample=sample_dataset(('ellipsoid',),per_family=5,seed=20)
        p=external_ellipsoid_queries(sample,seed=19)
        self.assertEqual(tuple(p['support_c'].shape),(5,2,10))
        self.assertEqual(tuple(p['eval_c'].shape),(5,8,10))
        self.assertEqual(len(set(p['geometry_ids'])),5)
        for s in p['support_eval_cut_ledger']:
            self.assertFalse(set(s['support_h'])&set(s['eval_h']))

    def test_frozen_m3_dataset_hash(self):
        d=sample_dataset(('box','sphere'),per_family=20,seed=19)
        self.assertEqual(dataset_digest(d),M3_FROZEN_SHA[19])

    def test_small_end_to_end_training_and_adaptation(self):
        run_result=run(seeds=(19,),max_steps=2,per_family=6)
        result=run_result['cases'][0]['query_counts']
        self.assertEqual(sorted(result),['0','1','2'])
        for k in ('0','1','2'):
            self.assertEqual(result[k]['necessary_condition_pass_fraction'],1.)
            self.assertTrue(math.isfinite(result[k]['r_mae']))
            self.assertEqual(result[k]['teacher_query_count_per_heldout_geometry'],int(k))
            self.assertFalse(result[k]['no_proven_CAD_realisability'] is False)


if __name__=='__main__':unittest.main()

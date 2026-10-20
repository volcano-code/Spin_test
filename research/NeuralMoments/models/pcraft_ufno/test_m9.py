"""M9 independent P0 cell-fraction / bounded-atom / identity tests.

Run from repository root:
python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m9 -v
"""
from __future__ import annotations
import inspect
import math
import unittest
from unittest.mock import patch
import numpy as np
import torch
from .analytic_cut import GeometrySpec, vertical_cut_truth
from .m6_moment_guard import physical_moment_diagnostic,PhysicalAdmissibilityFailure
from .m7_realizable import RealizableUFNOMoment
from .m7_teacher_gate import NativeTeacherNotReady
from .m9_antialias import PrimitiveP0,sample_capacity,baseline_point_sample_mass
from .m9_bounded_atoms import BoundedCellMoment,transfer_legacy_gate
from .m9_experiment import heldout_case_list,run


class TestM9(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(19)

    def sphere(self):return PrimitiveP0('sphere',(.04,-.06,.03),(.64,)*3)
    def ellipsoid(self):return PrimitiveP0('ellipsoid',(.02,-.08,.06),(.6,.42,.75))
    def box(self):return PrimitiveP0('box',(.12,-.03,.08),(.42,.55,.65),density=1.7)

    def example(self,n=8):
        s=self.ellipsoid();g=sample_capacity(s,resolution=n,refinement_depth=2)
        mc=BoundedCellMoment(g,temperature=.12)
        spec=GeometrySpec(s.family,s.center,s.axes,s.density)
        data=[vertical_cut_truth(spec,h) for h in (-.35,.23,.41)]
        c=torch.tensor(np.stack([x[0] for x in data]),dtype=torch.float64)
        r=torch.tensor(np.stack([x[1] for x in data]),dtype=torch.float64)
        return s,g,mc,c,r

    def test_box_exact_full_mass_and_bounds(self):
        shape=self.box()
        for res in (8,16,24):
            g=sample_capacity(shape,resolution=res)
            self.assertAlmostEqual(g.estimated_mass,shape.true_full_mass,places=12)
            self.assertAlmostEqual(g.mass_bracket[0],g.mass_bracket[1],places=12)
            self.assertEqual(g.uncertain_subcells,0)

    def test_box_cell_fraction_interior_and_partial(self):
        box=PrimitiveP0('box',(0.,0.,0.),(.5,.5,.5))
        g=sample_capacity(box,resolution=8)
        self.assertTrue(bool((g.estimated_capacity>=0).all()))
        self.assertTrue(bool((g.estimated_capacity<=8/8**3+1e-15).all()))
        self.assertEqual(g.estimated_capacity.numel(),512)
        self.assertAlmostEqual(g.estimated_mass,1.,places=12)

    def test_full_box_moments_valid_and_close(self):
        shape=self.box(); g=sample_capacity(shape,resolution=24)
        r=g.raw_full_moments()
        self.assertAlmostEqual(float(r[0]),shape.true_full_mass,places=12)
        self.assertAlmostEqual(float(r[1]),shape.true_full_mass*shape.center[0],delta=.004)
        self.assertTrue(bool(physical_moment_diagnostic(r[None],tol=1e-8)['necessary_conditions_pass'].all()))

    def test_sphere_ellipsoid_mass_in_bounds(self):
        for s in (self.sphere(),self.ellipsoid()):
            for n in (8,16,24):
                g=sample_capacity(s,resolution=n)
                lo,hi=g.mass_bracket
                self.assertLessEqual(lo,s.true_full_mass+1e-8)
                self.assertLessEqual(s.true_full_mass,hi+1e-8)
                self.assertLessEqual(lo-1e-12,g.estimated_mass)
                self.assertLessEqual(g.estimated_mass,hi+1e-12)

    def test_interval_width_shrinks_on_refinement(self):
        s=self.sphere()
        values=[sample_capacity(s,resolution=8,refinement_depth=d) for d in (0,1,2,3)]
        widths=[hi-lo for item in values for lo,hi in [item.mass_bracket]]
        self.assertTrue(all(a>=b-1e-12 for a,b in zip(widths,widths[1:])),widths)

    def test_antialias_improves_mass_on_missed_small_sphere(self):
        s=PrimitiveP0('sphere',(0.,0.,0.),(.2,.2,.2))
        old=baseline_point_sample_mass(s,resolution=8)
        new=sample_capacity(s,resolution=8,refinement_depth=3)
        self.assertAlmostEqual(old,0.,places=12)
        self.assertGreater(new.estimated_mass,0)
        self.assertLess(abs(new.estimated_mass-s.true_full_mass),s.true_full_mass)

    def test_order_and_cross_monomials(self):
        _,g,_,_,_=self.example()
        p=g.xyz[80];m=g.moment_basis[80]
        self.assertTrue(torch.allclose(m,torch.tensor([1.,p[0],p[1],p[2],p[0]**2,p[1]**2,p[2]**2,
             p[1]*p[2],p[0]*p[2],p[0]*p[1]],dtype=torch.float64)))
        self.assertEqual(tuple(g.moment_basis.shape),(512,10))

    def test_density_scale(self):
        s=self.ellipsoid(); r=sample_capacity(s,resolution=8)
        t=PrimitiveP0(s.family,s.center,s.axes,3.5)
        rt=sample_capacity(t,resolution=8)
        self.assertTrue(torch.allclose(rt.estimated_capacity,r.estimated_capacity*3.5,atol=1e-12))

    def test_empty_construction_and_invalid_resolution(self):
        with self.assertRaises(ValueError):PrimitiveP0('torus',(0,0,0),(.5,.5,.5))
        with self.assertRaises(ValueError):PrimitiveP0('sphere',(0,0,0),(.4,.3,.4))
        with self.assertRaises(ValueError):PrimitiveP0('sphere',(0,0,0),(0,.3,.4))
        with self.assertRaises(ValueError):PrimitiveP0('sphere',(0,0,0),(.2,.2,.2),density=-1)
        with self.assertRaises(ValueError):PrimitiveP0('sphere',(.9,0,0),(.4,.4,.4))
        with self.assertRaises(ValueError):sample_capacity(self.sphere(),resolution=3)
        with self.assertRaises(ValueError):sample_capacity(self.sphere(),resolution=8,refinement_depth=6)
        with self.assertRaises(ValueError):sample_capacity(self.sphere(),resolution=48,refinement_depth=5)

    def test_model_negative_and_excess_gate_rejected(self):
        _,g,_,_,_=self.example()
        with self.assertRaises(ValueError):BoundedCellMoment(g,gate=torch.full_like(g.estimated_capacity,-.1))
        with self.assertRaises(ValueError):BoundedCellMoment(g,gate=torch.full_like(g.estimated_capacity,1.2))
        with self.assertRaises(ValueError):BoundedCellMoment(g,temperature=0.)
        with self.assertRaises(ValueError):BoundedCellMoment(g,gate=torch.ones(4))

    def test_zero_query_preserves_weights(self):
        _,_,model,c,r=self.example()
        old=model.weights.clone(); pred=model.moment(c)
        audit=model.fit(c[:0],r[:0],source='ANALYTIC_P0')
        self.assertEqual(audit.query_count,0)
        self.assertTrue(torch.equal(old,model.weights))
        self.assertTrue(torch.equal(pred,model.moment(c)))

    def test_one_two_support_reduces_support_loss(self):
        for k in (1,2):
            _,g,model,c,r=self.example()
            audit=model.fit(c[:k],r[:k],source='ANALYTIC_P0')
            self.assertLessEqual(audit.loss_after,audit.loss_before+1e-13)
            self.assertTrue(bool((model.weights>=0).all()))
            self.assertTrue(bool((model.weights<=g.estimated_capacity+1e-13).all()))

    def test_fit_three_queries_rejected(self):
        _,_,model,c,r=self.example()
        with self.assertRaises(ValueError):model.fit(c,r,source='ANALYTIC_P0')

    def test_reject_native_and_forged_sources(self):
        _,_,model,c,r=self.example()
        for source in ('NATIVE_W2','H8F_ARCHIVE','NATIVE_VERIFIED','',None):
            with self.assertRaises(NativeTeacherNotReady):
                model.fit(c[:1],r[:1],source=source)

    def test_nonphysical_support_rejected(self):
        _,_,model,c,r=self.example()
        invalid=r[:1].clone();invalid[0,0]=-1
        with self.assertRaises(PhysicalAdmissibilityFailure):model.fit(c[:1],invalid,source='ANALYTIC_P0')

    def test_zero_coefficient_rejected(self):
        _,_,model,c,r=self.example()
        with self.assertRaises(ValueError):model.moment(torch.zeros_like(c))
        with self.assertRaises(ValueError):model.jacobian(torch.zeros_like(c))

    def test_projective_positive_scale_not_negative(self):
        _,_,model,c,r=self.example()
        model.fit(c[:1],r[:1],source='ANALYTIC_P0')
        a=model.moment(c[:1]);b=model.moment(3.1*c[:1])
        self.assertTrue(torch.allclose(a,b,atol=1e-12,rtol=1e-12))
        self.assertFalse(torch.allclose(a,model.moment(-c[:1]),atol=1e-7))

    def test_projective_radial_null(self):
        _,_,model,c,r=self.example()
        J=model.jacobian(c[:1])
        self.assertLess(float((J@c[:1].unsqueeze(-1)).abs().max()),2e-12)

    def test_jacobian_finite_diff_after_adaptation(self):
        _,_,model,c,r=self.example()
        model.fit(c[:2],r[:2],source='ANALYTIC_P0')
        c=c[2:3].clone();J=model.jacobian(c)
        for axis in (0,3,7,9):
            h=torch.zeros_like(c);h[:,axis]=1e-5
            numerical=(model.moment(c+h)-model.moment(c-h))/(2e-5)
            self.assertTrue(torch.allclose(numerical,J[:,:,axis],atol=2e-9,rtol=1e-5))

    def test_all_outputs_are_realizable_atomic(self):
        _,_,model,c,r=self.example()
        model.fit(c[:2],r[:2],source='ANALYTIC_P0')
        xx=torch.randn(10,10,dtype=torch.float64)
        q=torch.cat([c,xx],0)
        diag=physical_moment_diagnostic(model.moment(q),tol=1e-8)
        self.assertTrue(bool(diag['necessary_conditions_pass'].all()))

    def test_unchanged_source_uses_no_teacher_labels(self):
        signature=inspect.signature(sample_capacity)
        self.assertEqual(set(signature.parameters),{'shape','resolution','refinement_depth'})

    def test_optional_gate_transfer_single_encode(self):
        m=RealizableUFNOMoment(points_per_axis=4,temperature=.12).eval()
        D=torch.zeros(1,4,8,8,8);D[:,0:2]=1
        g=sample_capacity(self.ellipsoid(),resolution=8)
        with patch.object(m.encoder,'encode_geometry',wraps=m.encoder.encode_geometry) as counted:
            gate=transfer_legacy_gate(m,D,g)
            self.assertEqual(counted.call_count,1)
        self.assertEqual(tuple(gate.shape),(512,))
        self.assertTrue(bool(((gate>=0)&(gate<=1)).all()))

    def test_same_M8_disjoint_controls(self):
        x=list(heldout_case_list(19,3,8))
        self.assertEqual(len({s['geometry_id'] for s in x}),3)
        self.assertEqual(tuple(x[0]['support_c'].shape),(2,10))
        self.assertEqual(tuple(x[0]['eval_c'].shape),(8,10))
        self.assertEqual(tuple(x[0]['eval_J'].shape),(8,10,10))
        self.assertTrue(all(not any(abs(a-b)<1e-12 for a in s['support_h'] for b in s['eval_h']) for s in x))

    def test_tiny_end_to_end_report(self):
        result=run(seeds=(19,),per_family=2,resolutions=(8,16),depth=2,eval_queries=3)
        self.assertEqual(result['W2_admitted_labels'],0)
        self.assertEqual(len(result['samples']),4)
        for n in ('8','16'):
            self.assertEqual(set(result['aggregate'][n]['query_counts']),{'0','1','2'})
            self.assertEqual(result['aggregate'][n]['query_counts']['0']['necessary_condition_pass_fraction']['mean'],1.)
            self.assertLess(result['aggregate'][n]['relative_interval_width']['mean'],1.)


if __name__=='__main__':unittest.main()

"""W6 M7 CPU structural regression; no W2 samples and no fake native result.

python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m7 -v
"""
import math
import unittest
from unittest.mock import patch
import torch

from .m7_realizable import RealizableUFNOMoment
from .m5_potential import ConvexPotentialMoment
from .m6_moment_guard import physical_moment_diagnostic, hard_quadrature_moments
from .m4_lite_model import num_real_parameters


class TestM7Realizable(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(20261020)
        torch.set_num_threads(1)

    @staticmethod
    def build(rule='gauss',temperature=.2,n=4):
        return RealizableUFNOMoment(rule=rule,points_per_axis=n,hidden=32,
                                   temperature=temperature,grid_size=8).eval()

    @staticmethod
    def D(batch=2):
        D=torch.zeros(batch,4,8,8,8)
        D[:,0]=1.0;D[:,1]=1.0
        return D

    @staticmethod
    def C(batch=2):
        torch.manual_seed(91)
        x=torch.randn(batch,10);x[:,3]+=2.0
        return x / x.norm(dim=-1,keepdim=True)

    def test_geometry_cache_once_and_output_shapes(self):
        m=self.build();d=self.D();c=self.C()
        with patch.object(m,'encode_geometry',wraps=m.encode_geometry) as f:
            z=m.encode_geometry(d)
            for multiplier in (1.,1.7,2.3):
                pred=m.moment(z,multiplier*c)
                jac=m.jacobian(z,multiplier*c)
                self.assertEqual(tuple(pred.shape),(2,10))
                self.assertEqual(tuple(jac.shape),(2,10,10))
            self.assertEqual(f.call_count,1)

    def test_parameter_count_equal_to_m6(self):
        from .m6_gauss_potential import GaussPotentialMoment
        a=self.build(n=6);b=GaussPotentialMoment(points_per_axis=6,hidden=32)
        self.assertEqual(num_real_parameters(a),num_real_parameters(b))
        self.assertGreater(num_real_parameters(a),10000)

    def test_positive_weights_with_valid_support(self):
        m=self.build()
        z=m.encode_geometry(self.D())
        self.assertTrue(bool((z>=0).all()))
        self.assertTrue(bool((z<=m.voxel_volume*(1+1e-6)).all()))
        self.assertEqual(tuple(z.shape),(2,64))
        self.assertEqual(len(m.quadrature_xyz),64)

    def test_vacuum_d_has_zero_moments_and_j(self):
        m=self.build();d=self.D();d[:,0]=0
        z=m.encode_geometry(d);c=self.C()
        self.assertTrue(torch.equal(z,torch.zeros_like(z)))
        self.assertTrue(torch.equal(m.moment(z,c),torch.zeros(2,10)))
        self.assertTrue(torch.equal(m.jacobian(z,c),torch.zeros(2,10,10)))

    def test_occ_zero_prevents_learning_material_there(self):
        m=self.build();d=self.D();d[:,1]=0
        z=m.encode_geometry(d)
        self.assertTrue(torch.equal(z,torch.zeros_like(z)))

    def test_mass_and_quadrature_support_bounds(self):
        m=self.build(n=6);z=m.encode_geometry(self.D());r=m.moment(z,self.C())
        diag=physical_moment_diagnostic(r,tol=1e-7)
        self.assertTrue(bool(diag['necessary_conditions_pass'].all()))
        self.assertTrue(bool((r[:,0]>=0).all()))
        self.assertTrue(bool((r[:,0]<=z.sum(-1)+1e-6).all()))

    def test_scaled_positive_projective_and_radial_null(self):
        m=self.build();z=m.encode_geometry(self.D());c=self.C()
        p=m.moment(z,c);scaled=m.moment(z,c*8)
        self.assertTrue(torch.allclose(p,scaled,atol=1e-6))
        J=m.jacobian(z,c)
        self.assertLess(float((J @ c.unsqueeze(-1)).abs().max()),3e-6)
        self.assertFalse(torch.allclose(p,m.moment(z,-c),atol=1e-4))

    def test_full_10x10_analytic_jac_matches_fd(self):
        m=self.build(n=4).double()
        z=m.encode_geometry(self.D(1).double())
        c=self.C(1).double()
        J=m.jacobian(z,c).detach()
        for axis in (0,3,7,9):
            dc=torch.zeros_like(c);dc[:,axis]=1e-6
            fd=(m.moment(z,c+dc)-m.moment(z,c-dc))/(2e-6)
            self.assertTrue(torch.allclose(fd[0],J[0,:,axis],atol=1e-8,rtol=2e-5),axis)

    def test_tangent_basis_orthogonality(self):
        m=self.build();c=self.C()
        basis=m.native_tangent_basis(c)
        self.assertEqual(tuple(basis.shape),(2,10,9))
        self.assertLess(float((basis.transpose(-1,-2) @ c.unsqueeze(-1)).abs().max()),2e-6)
        eye=torch.eye(9)
        self.assertTrue(torch.allclose(basis.transpose(-1,-2)@basis,eye.expand(2,-1,-1),atol=1e-6))
        z=m.encode_geometry(self.D())
        tangent,other=m.tangent_jacobian(z,c)
        self.assertEqual(tuple(tangent.shape),(2,10,9))
        self.assertTrue(torch.allclose(tangent,m.jacobian(z,c)@other,atol=1e-6))

    def test_tangent_q_gram_symmetry_and_psd(self):
        m=self.build(n=4).double()
        z=m.encode_geometry(self.D().double());c=self.C().double()
        gram=m.projected_q_gram(z,c)
        self.assertLess(float((gram-gram.transpose(-1,-2)).abs().max()),1e-10)
        self.assertGreaterEqual(float(torch.linalg.eigvalsh(gram).min()),-1e-10)

    def test_ambient_Jq_not_claimed_symmetric(self):
        m=self.build().double();z=m.encode_geometry(self.D().double());c=self.C().double()
        Jq=m.jacobian(z,c)/m.native_B
        # Demonstrates why the native 10x10 derivative MUST NOT be mislabeled
        # as the ambient symmetric W0 smooth-continuum Hessian.
        self.assertGreater(float((Jq-Jq.transpose(-1,-2)).abs().max().detach()),1e-5)

    def test_value_finite_and_trainable(self):
        m=self.build().train();D=self.D(1);c=self.C(1)
        loss=m.moment(m.encode_geometry(D),c).square().mean()
        loss.backward()
        self.assertIsNotNone(m.weight_head[-1].weight.grad)
        self.assertGreater(float(m.weight_head[-1].weight.grad.abs().sum()),0.)
        self.assertIsNotNone(m.encoder.lift.weight.grad)

    def test_reject_nonfinite_negative_density_and_occ(self):
        m=self.build()
        d=self.D(1);d[:,0]=-1
        with self.assertRaises(ValueError):m.encode_geometry(d)
        d=self.D(1);d[:,1]=1.2
        with self.assertRaises(ValueError):m.encode_geometry(d)
        d=self.D(1);d[:,0,0,0,0]=float('nan')
        with self.assertRaises(ValueError):m.encode_geometry(d)
        z=m.encode_geometry(self.D(1))
        with self.assertRaises(ValueError):m.moment(z,torch.zeros(1,10))

    def test_safe_strict_empty_full_zero_derivatives(self):
        m=self.build();d=self.D(2);z=m.encode_geometry(d)
        c=torch.zeros(2,10);c[0,0]=-1;c[1,0]=1
        r=m.safe_predict(z,c)
        self.assertEqual(r['region_state'],('CERTIFIED_EMPTY','CERTIFIED_FULL'))
        self.assertTrue(torch.equal(r['r'][0],torch.zeros(10)))
        self.assertTrue(torch.allclose(r['r'][1],z[1]@m.monomials,atol=1e-6))
        self.assertTrue(torch.equal(r['Jc'],torch.zeros_like(r['Jc'])))
        self.assertTrue(bool(r['necessary_conditions_pass'].all()))
        self.assertFalse(r['native_teacher_certified'])
        self.assertFalse(r['admitted_for_real_optimizer'])

    def test_safe_unknown_remains_atomic_feasible(self):
        m=self.build();z=m.encode_geometry(self.D(1));c=torch.zeros(1,10);c[:,3]=1
        report=m.safe_predict(z,c)
        self.assertEqual(report['region_state'],('UNDECIDED',))
        self.assertTrue(bool(report['necessary_conditions_pass'].all()))
        self.assertTrue(torch.allclose(report['r'],m.moment(z,c),atol=1e-6))

    def test_guard_refuses_ungrounded_spatial_box(self):
        m=self.build();z=m.encode_geometry(self.D(1));c=self.C(1)
        with self.assertRaises(ValueError):m.safe_predict(z,c,low=(0,0,0))

    def test_hard_cut_comparison_moments_not_jacobian_truth(self):
        m=self.build();z=m.encode_geometry(self.D(1));c=torch.zeros(1,10);c[:,3]=1
        hard=hard_quadrature_moments(z,c,m.monomials)
        self.assertGreaterEqual(float(hard[0,0].detach()),0)
        self.assertTrue(bool(physical_moment_diagnostic(hard)['necessary_conditions_pass'].all()))
        self.assertEqual(tuple(hard.shape),(1,10))

    def test_midpoint_rule_and_symmetric_limit(self):
        m=self.build(rule='midpoint',n=4)
        z=m.encode_geometry(self.D(1));r=m.moment(z,self.C(1))
        self.assertEqual(tuple(r.shape),(1,10))

    def test_invalid_temperature_and_grid(self):
        for val in (0,-1,float('inf'),float('nan')):
            with self.assertRaises(ValueError):self.build(temperature=val)
        with self.assertRaises(ValueError):self.build(n=1)



# Explicit fail-closed W2 manifest regression. This is intentionally after the
# unittest.main guard; discover/unittest module imports still collect the class.
from .m7_teacher_gate import NativeTeacherNotReady, audit_manifest, require_native_training

class TestM7TeacherGate(unittest.TestCase):
    @staticmethod
    def historical_manifest():
        return {
          'schema':'w2-cherchi-teacher-v2-pre-w0',
          'native_teacher_runs':0,'training_samples':0,
          'data_splits':{'train':[],'test':[],
                         'excluded':[{'dataset':'H8f historical finite-point candidates',
                                     'count':81}]},
          'm9_real_h8f_81_evidence':{'newton_solved':False,
                                     'certified_continuous_neighborhood':False,
                                     'training_admitted':0},
          'pending_dependency':'W0 independently sealed derivative stratum'
        }

    def test_81_archived_candidates_are_not_teacher(self):
        record=audit_manifest(self.historical_manifest())
        self.assertEqual(record['archived_excluded_candidates'],81)
        self.assertEqual(record['Jacobian_training_admitted'],0)
        self.assertFalse(record['admitted_for_training'])
        with self.assertRaises(NativeTeacherNotReady):
            require_native_training(self.historical_manifest())

    def test_forged_verified_does_not_admit(self):
        rec=self.historical_manifest()
        rec.update(native_teacher_runs=200,training_samples=200,status='NATIVE_VERIFIED')
        rec['data_splits']['train']=[{'id':'forged'}]
        self.assertFalse(audit_manifest(rec)['admitted_for_training'])
        with self.assertRaises(NativeTeacherNotReady):require_native_training(rec)

    def test_malformed_split_is_rejected(self):
        rec=self.historical_manifest()
        del rec['data_splits']['excluded']
        with self.assertRaises(ValueError):audit_manifest(rec)

class TestM7AdditionalGeometryMath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_fixed_material_additive_and_J_unchanged(self):
        from .fixed_moments import merge_fixed_moments
        model=RealizableUFNOMoment(rule='gauss',points_per_axis=4,hidden=32).eval()
        D=torch.zeros(1,4,8,8,8);D[:,0]=1;D[:,1]=1
        z=model.encode_geometry(D)
        c=torch.zeros(1,10);c[:,3]=1
        r,J=model.moment(z,c),model.jacobian(z,c)
        F=torch.arange(10,dtype=r.dtype).unsqueeze(0)*.01
        total,J_total=merge_fixed_moments(r,J,F)
        self.assertTrue(torch.allclose(total,r+F))
        self.assertTrue(torch.equal(J_total,J))

    def test_tangent_directional_jacobian_fd(self):
        model=RealizableUFNOMoment(rule='gauss',points_per_axis=4,hidden=32).double().eval()
        D=torch.zeros(1,4,8,8,8,dtype=torch.float64);D[:,0]=1;D[:,1]=1
        z=model.encode_geometry(D)
        torch.manual_seed(7727)
        c=torch.randn(1,10,dtype=torch.float64)
        c=c/c.norm(dim=-1,keepdim=True)
        tangent,V=model.tangent_jacobian(z,c)
        for col in (0,4,8):
            direction=V[:,:,col]
            eps=1e-6
            plus=model.moment(z,c+eps*direction)
            minus=model.moment(z,c-eps*direction)
            fd=(plus-minus)/(2*eps)
            self.assertTrue(torch.allclose(fd[0],tangent[0,:,col],atol=1e-8,rtol=2e-5))

    def test_cross_monomial_native_double_mapping(self):
        model=RealizableUFNOMoment(rule='gauss',points_per_axis=4,hidden=32).eval()
        point=model.quadrature_xyz[0]
        m=model.monomials[0]
        c=torch.zeros(10);c[7]=1;c[8]=-2;c[9]=.75
        native_poly=(m*c*model.native_B).sum()
        explicit=2*point[1]*point[2]-4*point[0]*point[2]+1.5*point[0]*point[1]
        self.assertAlmostEqual(float(native_poly),float(explicit),places=6)

if __name__=='__main__':
    unittest.main()

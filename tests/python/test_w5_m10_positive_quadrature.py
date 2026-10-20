"""M10 same-Git-blob W6 encoder; physical cone and source-native derivative boundaries."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest
import os

import torch

from research.NeuralMoments.models.deeponet.m9_readonly_w6 import load_m9_w6
from research.NeuralMoments.models.deeponet.m10_positive_quadrature import (
    B_NATIVE, PositiveQuadratureMoment, cube_sign_states)
from research.NeuralMoments.models.deeponet.m10_experiment import (
    NAMES, make_model, execute)
from research.NeuralMoments.models.deeponet.m10_merge import merge_single_seed_files
from research.NeuralMoments.models.deeponet.m10_archive_gate import (
    inspect_w0_m9_report, inspect_joint_historical_gate)
from research.NeuralMoments.models.deeponet.m8_analytic_data import (
    dataset, sha_dataset, independent_family_check)
from research.NeuralMoments.models.deeponet.m8_fair_benchmark import (
    real_parameters, split_fit_validation)

BASE=Path(__file__).resolve().parents[2]
W6=Path(os.getenv('W5_M10_READONLY_W6_ROOT',str(BASE/'read_only_w6')))
W0=Path(os.getenv('W5_M10_READONLY_W0_REPORT',str(BASE/'read_only_w0/research/NeuralMoments/contracts/contract_smoke_m9.json')))
W2=Path(os.getenv('W5_M10_READONLY_W2_MANIFEST',str(BASE/'read_only_w2/research/NeuralMoments/teacher/teacher_manifest.json')))

@unittest.skipUnless(W6.is_dir() and W0.is_file() and W2.is_file(),
                     "requires source-pinned, read-only W6/W0/W2 inputs")
class M10Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.libraries=load_m9_w6(W6)
        cls.guard=cls.libraries[3]
        cls.data=dataset(('ellipsoid',),per_family=3,seed=43)

    def model(self, eps=.12, *, sign=True):
        _,_,m6,_=self.libraries
        torch.manual_seed(19)
        encoder=m6.GaussPotentialMoment(rule='gauss',points_per_axis=6,hidden=32,grid_size=8)
        return PositiveQuadratureMoment(encoder,smoothing=eps,certify_cube_sign=sign)

    def test_all_candidate_parameter_counts_within_five_percent(self):
        capacities=[real_parameters(make_model(name,19,self.libraries)) for name in NAMES]
        self.assertLessEqual(max(capacities)/min(capacities),1.05)
        self.assertEqual(capacities[-1],capacities[-2])
        self.assertEqual(capacities[-1],real_parameters(make_model('w6_gauss_004',19,self.libraries)))

    def test_same_voxel_tensor_not_lossy_nine_dimensional_summary(self):
        D,c,_,_,_=self.data
        model=self.model()
        z=model.encode_geometry(D)
        self.assertEqual(D.shape[1:],(4,8,8,8))
        self.assertEqual(z.shape,(6,216))
        self.assertEqual(model.moment(z,c).shape,(6,10))
        self.assertEqual(model.jacobian(z,c).shape,(6,10,10))

    def test_mass_cone_all_samples_even_untrained(self):
        D,c,_,_,_=self.data
        model=self.model()
        with torch.no_grad():out=model.moment(model.encode_geometry(D),c)
        diagnostics=self.guard.physical_moment_diagnostic(out,tol=1e-6)
        self.assertTrue(bool(diagnostics['necessary_conditions_pass'].all()))
        self.assertTrue(bool((out[:,0]>=0).all()))

    def test_real_fraction_bounds_cross_terms_double_and_signed_halfspace(self):
        c=torch.zeros((5,10),dtype=torch.float64)
        c[0,0]=-1
        c[1,0]=1
        c[2,0]=-1.5;c[2,7]=1
        c[3,0]=-2.1;c[3,7]=1
        c[4,0]=2.1;c[4,7]=-1
        self.assertEqual(cube_sign_states(c),('CERTIFIED_EMPTY','CERTIFIED_FULL',
                          'UNDECIDED','CERTIFIED_EMPTY','CERTIFIED_FULL'))

    def test_exact_empty_full_shortcuts_and_zero_local_J(self):
        D=self.data[0][:1]
        model=self.model()
        z=model.encode_geometry(D)
        c=torch.zeros((2,10));c[0,0]=-1;c[1,0]=1
        z2=z.expand(2,-1)
        r=model.moment(z2,c)
        J=model.jacobian(z2,c)
        torch.testing.assert_close(r[0],torch.zeros(10),rtol=0,atol=0)
        torch.testing.assert_close(J,torch.zeros(2,10,10),rtol=0,atol=0)
        torch.testing.assert_close(r[1],z[0]@model.encoder.monomials,atol=1e-6,rtol=1e-6)

    def test_native_B_diagonal_and_projective_positive_scale(self):
        self.assertEqual(B_NATIVE,(1.,)*7+(2.,)*3)
        D,c,_,_,_=self.data
        model=self.model()
        z=model.encode_geometry(D)
        with torch.no_grad():
            r1=model.moment(z,c)
            r2=model.moment(z,5*c)
            rminus=model.moment(z,-c)
        torch.testing.assert_close(r1,r2,atol=3e-6,rtol=3e-6)
        self.assertGreater(float((r1-rminus).abs().max()),.01)

    def test_closed_form_native_jacobian_agrees_with_torch_autograd(self):
        D,c,_,_,_=self.data
        model=self.model()
        z=model.encode_geometry(D[:1]).detach()
        native=c[0].clone().requires_grad_(True)
        jac_ref=torch.autograd.functional.jacobian(
            lambda x:model.moment(z,x.unsqueeze(0))[0], native)
        jac_analytic=model.jacobian(z,native.unsqueeze(0))[0]
        torch.testing.assert_close(jac_analytic,jac_ref,atol=2e-6,rtol=5e-6)

    def test_projective_radial_derivative_null(self):
        D,c,_,_,_=self.data
        model=self.model()
        z=model.encode_geometry(D)
        J=model.jacobian(z,c)
        self.assertLess(float(torch.bmm(J,c.unsqueeze(-1)).abs().max().detach()),1e-5)

    def test_physical_cone_does_not_promise_symmetry(self):
        D,c,_,_,_=self.data
        model=self.model(.12)
        z=model.encode_geometry(D)
        J=model.jacobian(z,c)
        B=torch.tensor(B_NATIVE)
        H=J/B
        # The sigmoid cut on q/||q|| does NOT come from an integrable
        # scalar potential. A symmetric H would not be guaranteed.
        self.assertGreater(float((H-H.transpose(-1,-2)).abs().max().detach()),1e-6)
        self.assertFalse(model.derivative_contract()['native_Cherchi_Jc_certified'])
        self.assertFalse(model.derivative_contract()['ambient_continuum_Hessian_symmetry_guaranteed'])

    def test_no_extra_geometry_encode_on_repeated_c(self):
        D,c,_,_,_=self.data
        model=self.model()
        counter={'n':0}
        old=model.encoder.encode_geometry
        def counted(*a,**kw):
            counter['n']+=1
            return old(*a,**kw)
        model.encoder.encode_geometry=counted
        z=model.encode_geometry(D[:1]);self.assertEqual(counter['n'],1)
        for delta in (-.1,0.,.08,.2):
            query=c[:1].clone();query[:,0]+=delta
            model.moment(z,query);model.jacobian(z,query)
        self.assertEqual(counter['n'],1)

    def test_training_backpropagates_through_J_to_W6_encoder(self):
        D,c,r,J,_=self.data
        model=self.model()
        zz=model.encode_geometry(D[:3]);rr=model.moment(zz,c[:3]);jj=model.jacobian(zz,c[:3])
        loss=(rr-r[:3]).square().mean()+.5*(jj-J[:3]).square().mean()
        loss.backward()
        grad=[p.grad for p in model.parameters() if p.grad is not None]
        self.assertTrue(grad)
        self.assertTrue(all(bool(torch.isfinite(x).all()) for x in grad))
        self.assertGreater(sum(float(x.abs().sum()) for x in grad),0)

    def test_training_family_and_validation_geometry_disjoint(self):
        fit=dataset(('box','sphere'),per_family=7,seed=19)
        held=dataset(('ellipsoid',),per_family=7,seed=20)
        a,b=split_fit_validation(fit,19,holdout_each=2)
        out=independent_family_check(a,b,held)
        self.assertEqual(out['heldout_families'],['ellipsoid'])
        self.assertNotEqual(sha_dataset(a),sha_dataset(b))

    def test_experiment_small_real_optimizer_smoke(self):
        report=execute(w6_root=W6,seeds=(97,),steps=3,
                       per_family=5,repeats=1,names=('w6_gauss_004','w5_positive_quadrature_012'))
        self.assertEqual(report['W2_real_native_J_training_labels_admitted'],0)
        self.assertEqual(report['W5_new_native_cherchi_calls'],0)
        self.assertTrue(report['four_channel_input_parity'])
        self.assertEqual(len(report['all_seed_records']),1)

    def test_real_h8f_81_byte_pinned_failure_and_no_training_admission(self):
        record=inspect_w0_m9_report(W0)
        self.assertEqual(record['historical_native_samples_numeric_reintegrated'],81)
        self.assertTrue(record['point60_symbolic_branch_change'])
        self.assertFalse(record['training_admitted'])
        self.assertEqual(record['original_workflow_conclusion'],'failure')

    def test_joint_w0_w2_gate_never_promotes_jacobians(self):
        both=inspect_joint_historical_gate(w0_report=W0,w2_manifest=W2)
        self.assertEqual(both['certified_smooth_J_admitted_total'],0)
        self.assertFalse(both['W2_H8e_25']['training_allowed'])
        self.assertEqual(both['W0_H8f_81']['historical_native_samples_numeric_reintegrated'],81)

    def test_tampering_readonly_real_archive_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            dst=Path(td)/'report.json'
            payload=json.loads(W0.read_text())
            payload['training_admissible']=True
            dst.write_text(json.dumps(payload))
            with self.assertRaises(ValueError):inspect_w0_m9_report(dst)
            dst.unlink()
            dst.symlink_to(W0)
            with self.assertRaises(ValueError):inspect_w0_m9_report(dst)

    def test_invalid_parameters_and_nonfinite_control_rejected(self):
        base=self.model()
        with self.assertRaises(ValueError):PositiveQuadratureMoment(base,smoothing=0.)
        with self.assertRaises(ValueError):PositiveQuadratureMoment(base,smoothing=float('inf'))
        D,c,_,_,_=self.data
        z=base.encode_geometry(D[:1]);bad=c[:1].clone();bad[:,7]=float('nan')
        with self.assertRaises(ValueError):base.moment(z,bad)
        with self.assertRaises(ValueError):cube_sign_states(torch.zeros((1,10)))

    def test_merge_real_seed_files_recomputes_statistics(self):
        root=BASE/'research/NeuralMoments/models/deeponet'
        paths=[root/f'm10_seed{x}.json' for x in (19,23,29)]
        if not all(p.is_file() for p in paths):
            self.skipTest('one-seed M10 training records not yet produced')
        result=merge_single_seed_files(paths)
        self.assertEqual(result['seeds'],[19,23,29])
        self.assertAlmostEqual(result['aggregate']['w5_positive_quadrature_012']['necessary_moment_pass_fraction']['mean'],1.)
        self.assertTrue(all(len(sha)==64 for sha in result['source_seed_file_sha256'].values()))

    def test_merge_duplicate_seed_and_tamper_rejected(self):
        root=BASE/'research/NeuralMoments/models/deeponet'
        p=root/'m10_seed19.json'
        if not p.exists():self.skipTest('training evidence not present')
        with self.assertRaises(ValueError):merge_single_seed_files([p,p])
        with tempfile.TemporaryDirectory() as td:
            x=json.loads(p.read_text())
            x['steps_upper_bound']=999
            other=Path(td)/'different.json';other.write_text(json.dumps(x))
            with self.assertRaises(ValueError):merge_single_seed_files([p,other])

    def test_dataset_identity_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source={'full_seed_experiments':[{'seed':19,'dataset_train_sha256':'bad',
                                           'dataset_heldout_sha256':'bad'}]}
            (Path(td)/'m9_seed19.json').write_text(json.dumps(source))
            with self.assertRaises(ValueError):
                execute(w6_root=W6,seeds=(19,),steps=2,per_family=5,repeats=1,
                        expected_m9_dir=td)

if __name__=='__main__':unittest.main()

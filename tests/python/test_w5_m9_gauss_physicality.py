"""M9 source-pinned cross-framework training, necessary physics and W2 exclusion."""
from __future__ import annotations
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np
import torch

from research.NeuralMoments.models.deeponet.m9_readonly_w6 import (
    W6_M6_FILES, load_m9_w6, git_blob_sha, UntrustedW6Source)
from research.NeuralMoments.models.deeponet.m9_merge_reports import merge_seeds
from research.NeuralMoments.models.deeponet.m9_archive_gate import (
    W2_MANIFEST_EXPECTED_SHA, inspect_historical_manifest)
from research.NeuralMoments.models.deeponet.m9_physical_benchmark import (
    NAMES, create_model, real_parameters, additional_physical_metrics,
    physically_guarded_decisions, query_budget_replay, execute)
from research.NeuralMoments.models.deeponet.m8_analytic_data import (
    Shape, analytic_truth, dataset, independent_family_check)
from research.NeuralMoments.models.deeponet.m8_fair_benchmark import split_fit_validation

W6 = os.environ.get('W5_M9_READONLY_W6_ROOT')
W2 = os.environ.get('W5_M9_READONLY_W2_MANIFEST')

@unittest.skipUnless(W6 and W2 and Path(W6).is_dir() and Path(W2).is_file(),
                     'set W5_M9_READONLY_W6_ROOT and W5_M9_READONLY_W2_MANIFEST')
class CrossFrameworkM9(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.libs=load_m9_w6(W6)
        cls.sample=dataset(('ellipsoid',),per_family=5,seed=37)

    def test_w6_m6_original_git_blob_exact(self):
        p=Path(W6)/'research/NeuralMoments/models/pcraft_ufno'
        for filename,blob in W6_M6_FILES.items():
            with self.subTest(file=filename):
                self.assertEqual(git_blob_sha((p/filename).read_bytes()),blob)

    def test_load_rejects_tampered_gauss_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'research/NeuralMoments/models/pcraft_ufno'
            p.mkdir(parents=True)
            base=Path(W6)/'research/NeuralMoments/models/pcraft_ufno'
            for filename in W6_M6_FILES:
                shutil.copy2(base/filename,p/filename)
            (p/'m6_gauss_potential.py').write_text('tampered',encoding='utf-8')
            with self.assertRaises(UntrustedW6Source): load_m9_w6(tmp)
            (p/'m6_gauss_potential.py').unlink()
            (p/'m6_gauss_potential.py').symlink_to(base/'m6_gauss_potential.py')
            with self.assertRaises(UntrustedW6Source): load_m9_w6(tmp)

    def test_real_w2_archive_manifest_hash_and_zero_training_gate(self):
        self.assertEqual(git_blob_sha(Path(W2).read_bytes()),W2_MANIFEST_EXPECTED_SHA)
        inspected=inspect_historical_manifest(W2)
        self.assertEqual(inspected['original_native_archive_evaluations'],25)
        self.assertEqual(inspected['original_workflow_status'],'failure')
        self.assertEqual(inspected['certified_smooth_J_training_labels'],0)
        self.assertFalse(inspected['training_allowed'])

    def test_w2_edited_manifest_not_trusted_even_if_counts_increased(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'label.json'
            source=json.loads(Path(W2).read_text())
            for name,value in [('training_samples',25),('native_teacher_runs',25),
                               ('previously_recorded_native_evidence',{})]:
                obj=dict(source)
                obj[name]=value
                path.write_text(json.dumps(obj),encoding='utf-8')
                with self.assertRaises(ValueError):inspect_historical_manifest(path)

    def test_all_seven_candidates_5_percent_capacity(self):
        params={name:real_parameters(create_model(name,19,self.libs)) for name in NAMES}
        self.assertEqual(len(params),7)
        self.assertLessEqual(max(params.values())/min(params.values()),1.05)
        self.assertEqual(params['w6_gauss_004'],params['w6_gauss_025'])
        self.assertEqual(params['w6_convex_potential6'],params['w6_gauss_004'])

    def test_gauss_midpoint_same_architecture_and_different_quadrature(self):
        _,m5,m6,_=self.libs
        torch.manual_seed(19)
        gauss=m6.GaussPotentialMoment(rule='gauss',points_per_axis=6,hidden=32,smoothing=.04)
        torch.manual_seed(19)
        mid=m6.GaussPotentialMoment(rule='midpoint',points_per_axis=6,hidden=32,smoothing=.04)
        self.assertEqual(gauss.real_parameter_count(),mid.real_parameter_count())
        self.assertAlmostEqual(float(gauss.voxel_volume.sum()),8.,places=5)
        self.assertAlmostEqual(float(mid.voxel_volume.sum())*6**3,8.,places=5)
        self.assertGreater(float((mid.monomials-gauss.monomials).abs().max()),.01)
        # Exact W6 M5 midpoint regression under same seed.
        torch.manual_seed(19)
        previous=m5.ConvexPotentialMoment(points_per_axis=6,hidden=32,smoothing=.04)
        D=self.sample[0][:1];c=self.sample[1][:1]
        with torch.no_grad():
            z=mid.encode_geometry(D);old=previous.encode_geometry(D)
            torch.testing.assert_close(z,old,atol=0,rtol=0)
            torch.testing.assert_close(mid.moment(z,c),previous.moment(old,c),atol=0,rtol=0)

    def test_gauss_Jq_symmetric_positive_semi_definite_on_smooth_P0(self):
        _,_,m6,_=self.libs
        m=m6.GaussPotentialMoment(points_per_axis=6,hidden=32,smoothing=.25)
        D=self.sample[0][:1]; c=self.sample[1][:1]
        with torch.no_grad():z=m.encode_geometry(D)
        J=m.jacobian(z,c)
        jq=J/torch.tensor([1.]*7+[2.]*3,dtype=J.dtype)
        self.assertLess(float((jq-jq.transpose(-1,-2)).abs().max()),1e-5)
        self.assertGreater(float(torch.linalg.eigvalsh(.5*(jq+jq.transpose(-1,-2))).amin()),-1e-5)
        self.assertLess(float((J@c[...,None]).abs().max()),1e-5)

    def test_material_necessary_condition_rejects_negative_mass(self):
        _,_,_,guard=self.libs
        valid=torch.tensor([[1.,0.,0.,0.,.25,.25,.25,0.,0.,0.]])
        bad=valid.clone();bad[:,0]=-1.
        good=guard.physical_moment_diagnostic(valid)
        failed=guard.physical_moment_diagnostic(bad)
        self.assertTrue(bool(good['necessary_conditions_pass'][0]))
        self.assertFalse(bool(failed['necessary_conditions_pass'][0]))
        with self.assertRaises(guard.PhysicalAdmissibilityFailure):
            guard.require_necessary_physical_moments(bad)

    def test_gauss_empty_negative_mass_counterexample_not_deployable(self):
        _,_,m6,guard=self.libs
        m=m6.GaussPotentialMoment(points_per_axis=6,hidden=32,smoothing=.25)
        # Deterministic truly all negative native beta; not a continuum cut.
        D=self.sample[0][:1];c=torch.zeros((1,10));c[:,0]=-1
        with torch.no_grad(): r=m.moment(m.encode_geometry(D),c)
        self.assertTrue(bool(torch.isfinite(r).all()))
        self.assertLess(float(r[:,0].item()),0.)
        self.assertFalse(bool(guard.physical_moment_diagnostic(r)['necessary_conditions_pass'][0]))

    def test_true_analytic_moments_pass_support_necessity(self):
        _,_,_,guard=self.libs
        D,c,r,J,meta=self.sample
        self.assertTrue(bool(guard.physical_moment_diagnostic(r)['necessary_conditions_pass'].all()))
        for row in meta:
            spec=Shape(row['family'],tuple(row['shape']['center']),tuple(row['shape']['axes']))
            self.assertLess(max(abs(spec.center[k])+spec.axes[k] for k in range(3)),1.)

    def test_physical_gate_and_independent_objective_replay(self):
        m=create_model('w5_deeponet_voxel',19,self.libs)
        _,_,_,guard=self.libs
        metrics=additional_physical_metrics(m,self.sample,guard)
        result=physically_guarded_decisions(m,self.sample,guard)
        self.assertEqual(result['eligible_samples'],10)
        self.assertAlmostEqual(result['true_moments_necessary_support_pass_fraction'],1.)
        self.assertLessEqual(result['accepted_candidates'],10)
        self.assertEqual(result['new_native_cherchi_queries'],0)
        self.assertTrue(result['no_geometric_state_committed'])
        self.assertTrue(0<=metrics['necessary_support_pass_fraction']<=1.)
        self.assertEqual(result['rejected_at_current_surrogate_physicality']+
                         result['rejected_at_candidate_surrogate_physicality_or_domain']+
                         result['rejected_by_independent_analytic_true_objective']+
                         result['accepted_candidates'],10)

    def test_actual_cached_query_budget_observed(self):
        model=create_model('w6_gauss_004',19,self.libs)
        times=query_budget_replay(model,self.sample,repeats=2,budgets=(1,2,4))
        self.assertEqual(sorted(times),['1','2','4'])
        self.assertTrue(all(row['single_encode_q_moment_and_J_ms']>0 for row in times.values()))
        self.assertTrue(all(row['actual_measured_not_additive_estimate'] for row in times.values()))

    def test_family_and_queries_never_leak(self):
        alltrain=dataset(('box','sphere'),per_family=5,seed=19)
        heldout=dataset(('ellipsoid',),per_family=5,seed=20)
        fit,val=split_fit_validation(alltrain,19,1)
        info=independent_family_check(fit,val,heldout)
        self.assertEqual(info['heldout_families'],['ellipsoid'])
        with self.assertRaises(ValueError):independent_family_check(fit,val,fit)

    def test_seven_candidate_end_to_end_training_smoke(self):
        result=execute(w6_root=W6,w2_manifest=W2,seeds=(19,),steps=2,
                       per_family=5,names=NAMES,repeats=1)
        self.assertEqual(len(result['aggregate']),7)
        self.assertEqual(result['W2_J_training_labels'],0)
        self.assertEqual(result['real_Cherchi_W5_calls'],0)
        self.assertTrue(result['fit_validation_test_from_exact_same_4channel_tensor'])
        for row in result['full_seed_experiments'][0]['models'].values():
            self.assertEqual(row['training']['steps_executed'],2)
            self.assertEqual(len(row['measured_query_budgets']),5)


    def test_merge_three_seeds_preserves_full_training_provenance(self):
        root=Path(__file__).resolve().parents[2]/'research/NeuralMoments/models/deeponet'
        paths=[root/f'm9_seed{s}.json' for s in (19,23,29)]
        if not all(p.is_file() for p in paths): self.skipTest('M9 experiment files not present')
        report=merge_seeds(paths)
        self.assertEqual(report['seeds'],[19,23,29])
        self.assertEqual(len(report['full_seed_experiments']),3)
        self.assertEqual(len(report['aggregate']),7)
        for key in NAMES:
            by_seed=report['aggregate'][key]['heldout.r_mae']['per_seed']
            self.assertEqual(set(by_seed),{'19','23','29'})
        with self.assertRaises(ValueError):merge_seeds([paths[0],paths[0]])

    def test_bad_query_budget_policy_rejected(self):
        model=create_model('w5_geometry_mlp_voxel',19,self.libs)
        with self.assertRaises(ValueError):query_budget_replay(model,self.sample,repeats=0)
        with self.assertRaises(ValueError):query_budget_replay(model,self.sample,budgets=(0,))

if __name__=='__main__':unittest.main()

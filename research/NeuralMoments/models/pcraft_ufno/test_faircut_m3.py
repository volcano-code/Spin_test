"""M3 regression: same W0 physical-cut labels, W5 source fidelity and budget.

Run from repo root:
 python -m unittest research.NeuralMoments.models.pcraft_ufno.test_faircut_m3 -v
"""
from __future__ import annotations

import hashlib
import math
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
import torch

from .adaptation import ResidualAdapter
from .analytic_cut import (B_NATIVE_TO_MONOMIAL, GeometrySpec, assert_disjoint_family_splits,
                           sample_dataset, vertical_cut_truth, voxel_geometry)
from .faircut_m3 import (_make_model, _same_minibatches, adapt_common, count_real_parameters,
                         evaluate, get_cached, prepare_geometry, run, synthetic_decision,
                         voxel_summary9)

HERE=Path(__file__).resolve().parent


def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


class W6FairCutM3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(19)

    def test_source_snapshot_pins_and_import_only_compatibility_patch(self):
        original={
            'model.py':'994aad8d6094e0a1343b2b3c9c1bf91be8da4bdf',
            'analytic_cut.py':'031e40151b6a28f8bdef809bc1ba710cdc7c3e4b',
            'adaptation.py':'9f07b7a3955c68cfb7ac4c7cd70e1340e20ce333',
            'w5_snapshot/deeponet/interface.py':'9d776e5c324140899f03296ee96dbfad602f8836',
            'w5_snapshot/deeponet/model.py':'7aa363769c0baf9f843d50e268164e761b566977'}
        for name,sha in original.items():
            self.assertEqual(git_blob_sha((HERE/name).read_bytes()),sha,name)
        path=HERE/'w5_snapshot/geometry_mlp/model.py'
        code=path.read_text(encoding='utf-8')
        self.assertIn('from ..deeponet.interface import (',code)
        original_code=code.replace('from ..deeponet.interface import (',
                                   'from research.NeuralMoments.models.deeponet.interface import (')
        self.assertEqual(git_blob_sha(original_code.encode()),
                         '85db98ec60926a653270020f05294a7347221dcb')

    def test_dataset_manifest_digest_and_seed_identity(self):
        from .faircut_m3 import dataset_sha256
        d1=sample_dataset(('box','sphere'),per_family=2,seed=19)
        d2=sample_dataset(('box','sphere'),per_family=2,seed=19)
        d3=sample_dataset(('box','sphere'),per_family=2,seed=20)
        self.assertEqual(dataset_sha256(d1),dataset_sha256(d2))
        self.assertNotEqual(dataset_sha256(d1),dataset_sha256(d3))
        self.assertEqual(len(dataset_sha256(d1)),64)

    def test_multiseed_aggregate_and_duplicate_seed_gate(self):
        from .m3_multiseed import aggregate
        a=run(seed=19,steps=1,per_family=1,repeats=1)
        b=run(seed=23,steps=1,per_family=1,repeats=1)
        result=aggregate([a,b])
        self.assertEqual(result['seeds'],[19,23])
        self.assertEqual(result['independent_native_teacher_runs'],0)
        self.assertTrue(math.isfinite(result['aggregates']['ufno']['moment_only']['r_mae']['mean']))
        with self.assertRaises(ValueError):aggregate([a,a])
        with self.assertRaises(ValueError):aggregate([])

    def test_model_capacity_within_five_percent(self):
        params={name:count_real_parameters(_make_model(name,19,8))
                for name in ('ufno','deeponet','geometry_mlp')}
        self.assertEqual(params,{'ufno':13982,'deeponet':13674,'geometry_mlp':13482})
        self.assertLess(max(params.values())/min(params.values()),1.05)

    def test_voxel_to_w5_adapter_is_label_and_family_blind(self):
        cube=voxel_geometry(GeometrySpec('box',(0,0,0),(.66,.55,.48)),8).unsqueeze(0)
        summary=voxel_summary9(cube)
        self.assertEqual(tuple(summary.shape),(1,9))
        self.assertTrue(torch.isfinite(summary).all())
        self.assertGreater(summary[0,0],0)
        self.assertTrue(torch.equal(prepare_geometry('geometry_mlp',cube),
                                    prepare_geometry('deeponet',cube)))
        # Mutation of only the raw voxels changes the W5 input features.
        altered=cube.clone();altered[:,0,1,1,1]+=3
        self.assertFalse(torch.equal(summary,voxel_summary9(altered)))
        with self.assertRaises(ValueError):voxel_summary9(torch.ones(1,9,8,8,8))
        with self.assertRaises(ValueError):voxel_summary9(torch.full_like(cube,float('nan')))

    def test_family_and_identity_holdout(self):
        train=sample_dataset(('box','sphere'),per_family=3,seed=19)
        test=sample_dataset(('ellipsoid',),per_family=3,seed=20)
        assert_disjoint_family_splits(train,test)
        self.assertEqual(len(train[0]),12)
        self.assertEqual(len({m['geometry_id'] for m in train[4]}),6)
        with self.assertRaises(ValueError):assert_disjoint_family_splits(train,train)
        self.assertEqual(set(m['source'] for m in train[4]),
                         {'ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI'})

    def test_common_minibatch_rng_exact(self):
        a=_same_minibatches(80,12,8,19)
        b=_same_minibatches(80,12,8,19)
        self.assertTrue(torch.equal(a,b))
        self.assertEqual(tuple(a.shape),(12,8))
        self.assertGreaterEqual(int(a.min()),0)
        self.assertLess(int(a.max()),80)
        with self.assertRaises(ValueError):_same_minibatches(0,12,8,19)

    def test_analytic_oracle_W0_native_jq_and_radial_null(self):
        c,r,J=vertical_cut_truth(GeometrySpec('ellipsoid',(.05,.03,.1),(.63,.42,.57)),.25)
        H=J@np.linalg.inv(B_NATIVE_TO_MONOMIAL)
        self.assertLess(np.max(abs(H-H.T)),1e-12)
        self.assertLess(np.max(abs(J@c)),1e-11)
        self.assertEqual(r.shape,(10,))

    def test_all_models_caching_and_jacobian_shapes(self):
        cube=voxel_geometry(GeometrySpec('sphere',(0,0,0),(.6,.6,.6)),8).unsqueeze(0)
        c=torch.tensor(vertical_cut_truth(GeometrySpec('sphere',(0,0,0),(.6,.6,.6)),.24)[0],dtype=torch.float32).unsqueeze(0)
        for name in ('ufno','deeponet','geometry_mlp'):
            model=_make_model(name,19,8).eval()
            with patch.object(model,'encode_geometry',wraps=model.encode_geometry) as spy:
                z=get_cached(model,name,cube)
                self.assertEqual(tuple(model.moment(z,c).shape),(1,10))
                self.assertEqual(tuple(model.jacobian(z,c).shape),(1,10,10))
                model.moment(z,c)
                self.assertEqual(spy.call_count,1)

    def test_head_derivatives_match_finite_difference(self):
        cube=voxel_geometry(GeometrySpec('box',(0,0,0),(.6,.6,.6)),8).unsqueeze(0)
        c=torch.tensor(vertical_cut_truth(GeometrySpec('box',(0,0,0),(.6,.6,.6)),.3)[0],dtype=torch.float32).unsqueeze(0)
        for name in ('ufno','deeponet','geometry_mlp'):
            model=_make_model(name,19,8).eval()
            with torch.no_grad():z=get_cached(model,name,cube).detach()
            J=model.jacobian(z,c)
            e=torch.zeros_like(c);e[:,0]=0.0005
            finite=(model.moment(z,c+e)-model.moment(z,c-e))/(2*e[0,0])
            self.assertTrue(torch.allclose(finite[0],J[0,:,0],atol=5e-4,rtol=.05),name)

    def test_identical_adaptation_budget_all_three(self):
        for name in ('ufno','deeponet','geometry_mlp'):
            model=_make_model(name,19,8).eval()
            scores=adapt_common(model,name,seed=119,grid_size=8)
            self.assertEqual(sorted(scores),['0','1','2'])
            self.assertEqual([scores[str(k)]['teacher_query_count'] for k in range(3)],
                             [0,1,2])
            self.assertTrue(all(math.isfinite(scores[str(k)]['r_mae']) for k in range(3)))

    def test_two_support_anchor_fit_exact_for_w5_and_w6(self):
        spec=GeometrySpec('ellipsoid',(0,0,0),(.6,.5,.7))
        source=[vertical_cut_truth(spec,h) for h in (-.2,.2)]
        cs=torch.tensor(np.stack([v[0] for v in source]),dtype=torch.float32)[None]
        rs=torch.tensor(np.stack([v[1] for v in source]),dtype=torch.float32)[None]
        cube=voxel_geometry(spec,8).unsqueeze(0)
        for name in ('ufno','deeponet','geometry_mlp'):
            model=_make_model(name,19,8).eval()
            with torch.no_grad():z=get_cached(model,name,cube).detach()
            adapter=ResidualAdapter(model,z,cs,rs)
            for i in range(2):
                self.assertTrue(torch.allclose(adapter.predict(cs[:,i]),rs[:,i],atol=2e-6))

    def test_real_cpu_e2e_three_architectures_two_arms(self):
        report=run(seed=19,steps=2,per_family=2,grid_size=8,repeats=2)
        self.assertEqual(report['status'],'SAME_NATIVE_C_ANALYTIC_CONTINUUM_P0_M3_ONLY')
        self.assertEqual(report['analytic_training_queries'],8)
        self.assertFalse(report['feature_equivalence'])
        self.assertTrue(report['raw_geometry_source_identical'])
        for name,results in report['model_results'].items():
            self.assertEqual(len(results),2)
            for arm,data in results.items():
                self.assertEqual(data['training']['steps'],2)
                self.assertTrue(math.isfinite(data['heldout']['r_mae']))
                self.assertTrue(math.isfinite(data['heldout']['J_mae']))
                self.assertTrue(math.isfinite(data['decision']['signed_true_objective_gap']))
                self.assertGreater(data['performance']['cached_J10x10']['median_ms'],0)


if __name__=='__main__':
    unittest.main()

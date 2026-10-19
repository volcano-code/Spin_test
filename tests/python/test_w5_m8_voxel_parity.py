"""W5 M8 verified source parity, analytic truth, training and provenance gates.

W6 optional external source is NEVER checked into W5; supply the pinned path
via W5_M8_READONLY_W6_ROOT for integration tests. Tests explicitly skip when
external W6 source is missing instead of claiming a pass.
"""
from __future__ import annotations
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
import torch
from research.NeuralMoments.models.deeponet.m8_voxel_models import VoxelMomentCandidate
from research.NeuralMoments.models.deeponet.m8_analytic_data import (
    Shape, analytic_truth, make_voxel, dataset, sha_dataset, independent_family_check)
from research.NeuralMoments.models.deeponet.m8_fair_benchmark import (
    FRAMEWORKS, W2_PINNED_HEAD, check_training_readiness, split_fit_validation,
    model_for, real_parameters, metrics, truth_decision_metrics, execute)
from research.NeuralMoments.models.deeponet.m7_cross_framework import (
    W6_FILES, load_pinned_w6, git_blob_sha, UntrustedW6Source)

W6=os.environ.get('W5_M8_READONLY_W6_ROOT')

class AnalyticContractTests(unittest.TestCase):
    def test_box_full_uncut_and_center(self):
        s=Shape('box',(0.,0.,0.),(1.,1.,1.))
        _,r,J=analytic_truth(s,0.)
        self.assertAlmostEqual(r[0],4.)
        self.assertAlmostEqual(r[3],2.)
        self.assertAlmostEqual(r[4],4./3.)
        self.assertEqual(J.shape,(10,10))

    def test_p0_native_J_B_inverse_symmetric_and_radial(self):
        for family in ('box','sphere','ellipsoid'):
            s=Shape(family,(.11,-.13,.02),(.6,)*3 if family=='sphere' else (.59,.65,.73))
            c,r,J=analytic_truth(s,.23)
            H=J/np.array([1.]*7+[2.]*3)[None,:]
            np.testing.assert_allclose(H,H.T,atol=1e-12,rtol=1e-12)
            np.testing.assert_allclose(J@c,np.zeros(10),atol=1e-12)
            self.assertGreaterEqual(np.linalg.eigvalsh((H+H.T)/2).min(),-1e-11)

    def test_independent_finite_difference_height_direction(self):
        for family in ('box','sphere','ellipsoid'):
            s=Shape(family,(.1,-.02,.09),(.6,)*3 if family=='sphere' else (.55,.64,.71))
            h=.21;eps=1e-6
            c,r,J=analytic_truth(s,h)
            dc=(analytic_truth(s,h+eps)[0]-analytic_truth(s,h-eps)[0])/(2*eps)
            fd=(analytic_truth(s,h+eps)[1]-analytic_truth(s,h-eps)[1])/(2*eps)
            np.testing.assert_allclose(J@dc,fd,atol=1e-8,rtol=1e-8)

    def test_four_channel_derived_without_hidden_cut_target(self):
        s=Shape('ellipsoid',(0.,0.,0.),(.6,.5,.7))
        x=make_voxel(s)
        self.assertEqual(tuple(x.shape),(4,8,8,8))
        self.assertGreater(x[0].sum(),0)
        self.assertGreater(x[1].sum(),0)
        self.assertGreater(x[2].abs().sum(),0)
        self.assertGreater(x[3].sum(),0)
        self.assertFalse(torch.allclose(x[2],x[3]))

    def test_family_and_identity_split_no_leakage(self):
        all_train=dataset(('box','sphere'),per_family=6,seed=19)
        heldout=dataset(('ellipsoid',),per_family=6,seed=20)
        train,valid=split_fit_validation(all_train,19,1)
        counts=independent_family_check(train,valid,heldout)
        self.assertEqual(counts,{'fit_ids':10,'validation_ids':2,'heldout_ids':6,'heldout_families':['ellipsoid']})
        self.assertEqual(sha_dataset(all_train),sha_dataset(dataset(('box','sphere'),per_family=6,seed=19)))
        with self.assertRaises(ValueError):independent_family_check(train,valid,train)
        with self.assertRaises(ValueError):independent_family_check(train,valid,valid)

    def test_no_invalid_shapes_or_singular_c(self):
        with self.assertRaises(ValueError):Shape('sphere',(0,0,0),(.4,.6,.4))
        with self.assertRaises(ValueError):analytic_truth(Shape('box',(0,0,0),(.5,.5,.5)),1.)
        m=VoxelMomentCandidate('deeponet')
        with self.assertRaises(ValueError):m.encode_geometry(torch.zeros(1,4,4,4,4))
        z=m.encode_geometry(torch.ones(1,4,8,8,8))
        with self.assertRaises(ValueError):m.moment(z,torch.zeros(1,10))

    def test_w2_m8_history_not_derivative_admissible(self):
        w2={'schema':'w2-cherchi-teacher-v2-pre-w0','native_teacher_runs':0,
            'training_samples':0,'previously_recorded_native_evidence':
            {'archived_samples_offline_independently_reverified':25}}
        gate=check_training_readiness(w2)
        self.assertEqual(gate['w2_head'],W2_PINNED_HEAD)
        self.assertEqual(gate['historical_native_h8e_offline_r_reverified'],25)
        self.assertEqual(gate['w2_admissible_training_labels'],0)
        self.assertFalse(gate['native_J_neighborhood_certified'])
        for change in (('training_samples',1),('native_teacher_runs',25),('schema','fake')):
            q=dict(w2);q[change[0]]=change[1]
            with self.assertRaises(ValueError):check_training_readiness(q)

class VoxelWrapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(19)
        cls.D=dataset(('box',),per_family=1,seed=19)[0][:1]
        cls.c=dataset(('box',),per_family=1,seed=19)[1][:1]

    def test_deeponet_and_geometry_mlp_same_raw_inputs_and_cache(self):
        for name in ('deeponet','geometry_mlp'):
            with self.subTest(name=name):
                m=VoxelMomentCandidate(name)
                z=m.encode_geometry(self.D)
                r=m.moment(z,self.c)
                j=m.jacobian(z,self.c)
                self.assertEqual(tuple(r.shape),(1,10))
                self.assertEqual(tuple(j.shape),(1,10,10))
                self.assertTrue(bool(torch.isfinite(j).all()))
                self.assertLess(float((j@self.c[...,None]).detach().abs().max()),2e-5)
                torch.testing.assert_close(r,m.moment(z,self.c*1.11),atol=1e-5,rtol=1e-5)

    def test_voxel_encoder_has_genuine_channel_sensitivity(self):
        m=VoxelMomentCandidate('deeponet').voxel_encoder
        x=self.D.clone()
        base=m(x)
        for channel in range(4):
            y=x.clone();y[:,channel]+=0.4
            self.assertGreater(float((base-m(y)).detach().abs().max()),1e-7)

    def test_cached_query_does_not_reencode(self):
        m=VoxelMomentCandidate('geometry_mlp')
        counts=[]
        handle=m.voxel_encoder.register_forward_hook(lambda *a:counts.append(1))
        try:
            z=m.encode_geometry(self.D)
            for i in range(4):
                m.moment(z,self.c*(1+.05*i))
                m.jacobian(z,self.c)
            self.assertEqual(len(counts),1)
        finally:handle.remove()

@unittest.skipUnless(W6 and Path(W6).is_dir(), 'set read-only W5_M8_READONLY_W6_ROOT')
class ExternalW6MatchedSourceTests(unittest.TestCase):
    def test_actual_remote_source_hashes(self):
        base=Path(W6)/'research/NeuralMoments/models/pcraft_ufno'
        for name,digest in W6_FILES.items():
            self.assertEqual(git_blob_sha((base/name).read_bytes()),digest)
        load_pinned_w6(W6)

    def test_all_five_capacity_within_5_percent(self):
        modules=load_pinned_w6(W6)
        counts={n:real_parameters(model_for(n,19,modules)) for n in FRAMEWORKS}
        self.assertEqual(len(counts),5)
        self.assertLessEqual(max(counts.values())/min(counts.values()),1.05)
        self.assertGreater(counts['w5_deeponet_voxel'],counts['w5_geometry_mlp_voxel'])

    def test_tampered_external_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            target=Path(tmp)/'research/NeuralMoments/models/pcraft_ufno'
            target.mkdir(parents=True)
            src=Path(W6)/'research/NeuralMoments/models/pcraft_ufno'
            for file in W6_FILES: shutil.copy2(src/file,target/file)
            with (target/'m5_potential.py').open('a') as f: f.write('\n# bad edit\n')
            with self.assertRaises(UntrustedW6Source):load_pinned_w6(tmp)

    def test_five_frameworks_train_and_independent_decision(self):
        out=execute(w6_root=W6,seeds=(19,),steps=2,per_family=5,repeats=1)
        self.assertTrue(out['input_information_parity'])
        self.assertFalse(out['encoder_architecture_parity'])
        self.assertEqual(out['native_cherchi_calls'],0)
        self.assertEqual(len(out['aggregate']),5)
        self.assertEqual(len(out['full_seed_experiments']),1)
        for row in out['aggregate'].values():
            self.assertTrue(math.isfinite(row['heldout.r_mae']['mean']))
        for _,metrics in out['full_seed_experiments'][0]['models'].items():
            self.assertEqual(metrics['training']['steps_executed'],2)
            self.assertEqual(metrics['decision']['validation_type'],'INDEPENDENT_ANALYTIC_P0_1D_ONLY')
            self.assertEqual(metrics['decision']['oracle_poststep_queries'],20)
            self.assertEqual(sorted(metrics['timing']['query_budget_cost_model']),['1','16','2','4','64','8'])

    def test_w6_convex_potential_Jq_structure(self):
        _,m5=load_pinned_w6(W6)
        m=m5.ConvexPotentialMoment(points_per_axis=6,hidden=32).eval()
        d=dataset(('box',),per_family=1,seed=19)
        with torch.no_grad():z=m.encode_geometry(d[0][:1])
        c=d[1][:1]
        j=m.jacobian(z,c);H=j/torch.tensor([1.]*7+[2.]*3)
        self.assertLess(float((H-H.transpose(-1,-2)).abs().max()),1e-6)
        self.assertGreaterEqual(float(torch.linalg.eigvalsh((H+H.transpose(-1,-2))/2).min()),-1e-5)

if __name__=='__main__':unittest.main()

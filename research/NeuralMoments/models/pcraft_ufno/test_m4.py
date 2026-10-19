"""Runnable CPU verification of lightweight W6 M4, W5 capacity and data protocol.

    python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m4 -v
"""
from __future__ import annotations
import hashlib, json, math, unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch
from .m4_lite_model import AxisFactorizedFFT,LiteUFNOMoment,VARIANTS,num_real_parameters,voxel_statistics9
from .m4_experiment import (NAMES,OLD_M3_SEED19_TRAIN_SHA,make_model,encoded,
    split_by_geometry,sample_schedule,metrics,train_early_stop,run,dataset_digest)
from .analytic_cut import GeometrySpec,sample_dataset,vertical_cut_truth,voxel_geometry

HERE=Path(__file__).resolve().parent
EXPECTED_M3_DIGESTS={
    19:'7b65ebbb3e5d32e82ff7ee23a1f88978fa4100902b67f63e16b0fdc2df54e087',
    23:'d36d707cbf7ecdd0089f66fea3f8784a200830f09a2e0b5a60790ce6028562e7',
    29:'25eece482d68d864064bfcc7785226785afc41307f56978f2f027ba4ac838394'}

class TestW6M4(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(19)

    def test_dataset_reproduces_M3_across_three_seeds(self):
        for seed,digest in EXPECTED_M3_DIGESTS.items():
            data=sample_dataset(('box','sphere'),per_family=20,seed=seed)
            self.assertEqual(dataset_digest(data),digest)

    def test_three_variant_fft_placement_is_explicit(self):
        for variant,(a,b,_) in VARIANTS.items():
            model=LiteUFNOMoment(variant)
            self.assertEqual(model.level4.spectral is not None,a)
            self.assertEqual(model.level2.spectral is not None,b)
        with self.assertRaises(ValueError):LiteUFNOMoment('not_a_variant')

    def test_all_five_near_equal_parameter_budget(self):
        models={name:num_real_parameters(make_model(name,19)) for name in NAMES}
        self.assertEqual(models,{'lite_dual':14122,'lite_bottleneck':13746,
                                 'lite_local_only':14098,'w5_deeponet':13674,
                                 'w5_geometry_mlp':13482})
        self.assertLess(max(models.values())/min(models.values()),1.05)

    def test_fft_mode_clamp_at_small_resolution_and_backward(self):
        layer=AxisFactorizedFFT(3,99)
        x=torch.randn(1,3,4,4,4,requires_grad=True)
        result=layer(x)
        self.assertEqual(result.shape,x.shape)
        self.assertTrue(torch.isfinite(result).all())
        result.square().mean().backward()
        self.assertTrue(torch.isfinite(x.grad).all())

    def test_voxel9_has_no_family_or_oracle_descriptors(self):
        spec=GeometrySpec('ellipsoid',(.01,.02,.03),(.67,.41,.58))
        vox=voxel_geometry(spec,8).unsqueeze(0)
        actual=voxel_statistics9(vox)
        self.assertEqual(tuple(actual.shape),(1,9))
        self.assertTrue(torch.isfinite(actual).all())
        modified=vox.clone();modified[0,0,3,3,3]*=.6
        self.assertFalse(torch.allclose(actual,voxel_statistics9(modified)))
        with self.assertRaises(ValueError):voxel_statistics9(torch.randn(1,3,8,8,8))

    def test_cached_geometry_only_once_for_multi_c(self):
        model=LiteUFNOMoment('bottleneck').eval()
        spec=GeometrySpec('box',(0,0,0),(.66,.6,.59))
        d=voxel_geometry(spec,8).unsqueeze(0)
        c=torch.tensor(vertical_cut_truth(spec,.2)[0],dtype=torch.float32)[None]
        with patch.object(model,'encode_geometry',wraps=model.encode_geometry) as spy:
            z=model.encode_geometry(d)
            for scale in (1.,2.,3.):
                r=model.moment(z,scale*c)
                j=model.jacobian(z,c)
                self.assertEqual(tuple(r.shape),(1,10))
                self.assertEqual(tuple(j.shape),(1,10,10))
            self.assertEqual(spy.call_count,1)

    def test_positive_projective_invariance_but_sign_distinct(self):
        model=LiteUFNOMoment('dual').eval()
        z=model.encode_geometry(torch.ones(1,4,8,8,8))
        c=torch.tensor([[-.2,0,0,1,0,0,0,0,0,0]],dtype=torch.float32)
        self.assertTrue(torch.allclose(model.moment(z,c),model.moment(z,2.5*c),atol=1e-6))
        self.assertFalse(torch.allclose(c/c.norm(),-c/c.norm()))
        self.assertLess(float((model.jacobian(z,c)@c.unsqueeze(-1)).abs().max().detach()),1e-5)
        with self.assertRaises(ValueError):model.moment(z,torch.zeros_like(c))

    def test_full_J_matches_finite_difference(self):
        for variant in VARIANTS:
            model=LiteUFNOMoment(variant).eval()
            z=model.encode_geometry(torch.ones(1,4,8,8,8)).detach()
            c=torch.tensor([[-.2,0,0,1,0,0,0,0,0,0]],dtype=torch.float32)
            J=model.jacobian(z,c)
            delta=torch.zeros_like(c);delta[0,0]=.0005
            finite=(model.moment(z,c+delta)-model.moment(z,c-delta))/(2*.0005)
            self.assertTrue(torch.allclose(finite[0],J[0,:,0],atol=3e-4,rtol=.03))

    def test_split_holds_out_whole_geometry_id(self):
        all_train=sample_dataset(('box','sphere'),per_family=20,seed=19)
        train,val,manifest=split_by_geometry(all_train,seed=19)
        self.assertEqual(manifest['train_queries'],64)
        self.assertEqual(manifest['validation_queries'],16)
        self.assertEqual(manifest['train_geo'],32)
        self.assertEqual(manifest['val_geo'],8)
        self.assertFalse({x['geometry_id'] for x in train[4]}&{x['geometry_id'] for x in val[4]})
        train2,val2,m2=split_by_geometry(all_train,seed=19)
        self.assertEqual(manifest,m2)
        self.assertTrue(torch.equal(val[1],val2[1]))

    def test_analytic_native_Jq_versus_Jc(self):
        c,r,J=vertical_cut_truth(GeometrySpec('ellipsoid',(.07,.02,-.04),(.64,.48,.7)),.28)
        H=J/np.array([1.]*7+[2.]*3)[None,:]
        self.assertLess(float(np.abs(H-H.T).max()),1e-12)
        self.assertGreater(float(np.abs(J-J.T).max()),1e-7)
        self.assertLess(float(np.abs(J@c).max()),1e-11)

    def test_same_minibatch_schedule(self):
        s=sample_schedule(64,30,8,19)
        self.assertTrue(torch.equal(s,sample_schedule(64,30,8,19)))
        self.assertFalse(torch.equal(s,sample_schedule(64,30,8,23)))
        with self.assertRaises(ValueError):sample_schedule(0,30,8,19)

    def test_early_stop_selects_validation_not_test(self):
        data=sample_dataset(('box','sphere'),per_family=3,seed=19)
        fit,val,_=split_by_geometry(data,seed=19,validation_geometries_per_family=1)
        model=LiteUFNOMoment('bottleneck')
        history=train_early_stop(model,'lite_bottleneck',fit,val,seed=19,
                                 steps=12,batch=4,eval_every=3,patience=2)
        self.assertGreaterEqual(history['steps_selected'],3)
        self.assertLessEqual(history['steps_selected'],history['steps_executed'])
        self.assertEqual(history['analytical_validation_labels'],4)
        self.assertTrue(all(math.isfinite(s['validation_score']) for s in history['history']))
        self.assertTrue(all('test' not in item for item in history['history']))

    def test_one_cpu_end_to_end_with_five_models(self):
        report=run(seeds=(19,),steps=2,per_family=3,repetitions=1,names=NAMES)
        self.assertEqual(report['W2_real_teacher_samples'],0)
        self.assertFalse(report['representation_parity'])
        self.assertEqual(report['all_experiments'][0]['geometry_split']['val_geo'],2)
        self.assertEqual(len(report['all_experiments'][0]['results']),5)
        for name in NAMES:
            item=report['all_experiments'][0]['results'][name]
            self.assertTrue(math.isfinite(item['heldout']['r_mae']))
            self.assertTrue(math.isfinite(item['heldout']['J_mae']))
            self.assertGreater(item['cpu_timing']['cold_voxel_to_head']['median_ms'],0)

    def test_duplicate_seed_or_parameter_budget_rejected(self):
        with self.assertRaises(ValueError):run(seeds=(19,19),steps=1,per_family=3,repetitions=1)
        with self.assertRaises(ValueError):LiteUFNOMoment(grid_size=7)

if __name__=='__main__':unittest.main()

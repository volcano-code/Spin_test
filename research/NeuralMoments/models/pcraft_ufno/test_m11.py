"""W6 M11: per-geometry, source-bound analytical oracle anchor decisions."""
from __future__ import annotations
import hashlib
import json
import math
import unittest
from unittest import mock

import numpy as np
import torch

from .analytic_cut import GeometrySpec, TEACHER_KIND,vertical_cut_truth
from .m10_decision import gn_step,native_plane_c_and_tangent
from .m10_experiment import make_model, centered_voxel
from .m11_anchor_cache import (AnalyticAnchorLedger,CacheBindingError,
                               NativeLabelsUnavailable,POLICIES)
from .m11_experiment import run,eval_model


class TestM11AnchorCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.manual_seed(20261021)
        torch.set_num_threads(1)

    def setUp(self):
        self.spec=GeometrySpec("ellipsoid",(.02,-.05,.03),(.54,.62,.71))
        self.D=centered_voxel(self.spec,8).unsqueeze(0)
        self.model=make_model("w6_m7_base",19).eval()

    def cache(self):
        return AnalyticAnchorLedger(self.model,self.D,self.spec)

    def test_one_time_encode_many_controls(self):
        with mock.patch.object(self.model,"encode_geometry",wraps=self.model.encode_geometry) as probe:
            cache=self.cache()
            for h in (-.3,0,.22,.47):
                d=cache.decision_input(h,"baseline")
                self.assertEqual(d.r_for_step.shape,(10,))
                self.assertEqual(d.Jc_surrogate.shape,(10,10))
            self.assertEqual(probe.call_count,1)
            self.assertEqual(cache.receipt()["encoder_calls"],1)
            self.assertEqual(cache.analytic_oracle_calls,0)

    def test_frozen_geometry_and_checkpoint_binding(self):
        cache=self.cache()
        cache.assert_bound(model=self.model,D=self.D,geometry=self.spec)
        mutated=self.D.clone()
        mutated[0,0,0,0,0]+=1e-4
        with self.assertRaises(CacheBindingError):cache.assert_bound(D=mutated)
        other=GeometrySpec("ellipsoid",(.03,-.05,.03),(.54,.62,.71))
        with self.assertRaises(CacheBindingError):cache.assert_bound(geometry=other)
        with self.assertRaises(CacheBindingError):cache.assert_bound(model=make_model("w6_m7_base",19))

    def test_stale_model_rejected(self):
        cache=self.cache()
        with torch.no_grad():
            next(self.model.parameters()).add_(1e-4)
        with self.assertRaises(CacheBindingError):cache.decision_input(.2,"baseline")
        with self.assertRaises(CacheBindingError):cache.obtain_r(.2)

    def test_zero_queries_exact_and_no_material_proof(self):
        cache=self.cache()
        d=cache.decision_input(.15,"baseline")
        self.assertFalse(d.correction_used)
        self.assertTrue(np.array_equal(d.r_for_step,d.raw_atomic_r))
        receipt=cache.receipt()
        self.assertEqual(receipt["analytic_oracle_calls"],0)
        self.assertFalse(receipt["native_training_admitted"])
        self.assertFalse(receipt["material_moment_certified"])

    def test_unique_anchor_charged_only_once(self):
        cache=self.cache()
        a=cache.obtain_r(.2)
        b=cache.obtain_r(.2)
        self.assertIs(a,b)
        self.assertEqual(cache.analytic_oracle_calls,1)
        self.assertEqual(cache.anchor_count,1)
        self.assertEqual(cache.surrogate_moment_calls,1)
        self.assertEqual(cache.surrogate_jacobian_calls,0)

    def test_anchor_truth_is_independent_analytic_r_only(self):
        cache=self.cache()
        observation=cache.obtain_r(.1)
        c,r,J=vertical_cut_truth(self.spec,.1)
        self.assertTrue(np.allclose(observation.r_design,r,rtol=0,atol=0))
        self.assertTrue(np.allclose(observation.c_native,c,rtol=0,atol=0))
        self.assertEqual(observation.source,TEACHER_KIND)
        self.assertEqual(observation.geometry_sha256,self.spec.geometry_id)
        self.assertEqual(observation.model_sha256,cache.receipt()["model_state_sha256"])

    def test_native_source_rejected_even_with_forged_status(self):
        cache=self.cache()
        for source in ("NATIVE_VERIFIED","W2_H8F_81", "ANALYTIC_P0",""):
            with self.assertRaises(NativeLabelsUnavailable):cache.obtain_r(0.,source=source)
        self.assertEqual(cache.analytic_oracle_calls,0)

    def test_invalid_h_fails_closed(self):
        cache=self.cache()
        for h in (math.nan,math.inf,-math.inf,-.75,.75,2.,True):
            with self.assertRaises(ValueError):cache.obtain_r(h)
        self.assertEqual(cache.analytic_oracle_calls,0)

    def test_one_anchor_corrects_exactly_at_anchor_only_for_decision(self):
        cache=self.cache()
        a=cache.obtain_r(.0)
        result=cache.decision_input(0.,"one_anchor")
        self.assertTrue(result.correction_used)
        self.assertTrue(result.candidate_cone_check_pass)
        self.assertTrue(np.allclose(result.r_for_step,a.r_design,atol=3e-8))
        self.assertGreater(np.abs(result.raw_atomic_r-np.asarray(a.r_design)).max(),1e-6)
        self.assertNotEqual(result.source,"NATIVE_VERIFIED")

    def test_one_anchor_has_no_second_true_query_at_new_control(self):
        cache=self.cache()
        cache.obtain_r(0.)
        with mock.patch('research.NeuralMoments.models.pcraft_ufno.m11_anchor_cache.vertical_cut_truth',
                        side_effect=AssertionError('target leakage')):
            cache.decision_input(.21,'one_anchor')
        self.assertEqual(cache.analytic_oracle_calls,1)

    def test_two_anchor_interpolated_bias_and_no_extra_true_queries(self):
        cache=self.cache()
        cache.obtain_r(-.35)
        cache.obtain_r(.35)
        p=cache.decision_input(0.,"two_anchors")
        self.assertEqual(p.Jc_surrogate.shape,(10,10))
        self.assertEqual(cache.analytic_oracle_calls,2)
        for h in (-.35,.35):
            d=cache.decision_input(h,"two_anchors")
            self.assertTrue(np.allclose(d.r_for_step,vertical_cut_truth(self.spec,h)[1],atol=3e-8))
        self.assertEqual(cache.analytic_oracle_calls,2)

    def test_distance_guard_fallback(self):
        cache=self.cache();cache.obtain_r(-.65)
        d=cache.decision_input(.65,"one_anchor",max_distance=.4)
        self.assertFalse(d.correction_used)
        self.assertEqual(d.fallback_reason,"OUTSIDE_ANCHOR_RADIUS")
        self.assertTrue(np.array_equal(d.r_for_step,d.raw_atomic_r))

    def test_cone_guard_fallback_for_invalid_corrected_vector(self):
        cache=self.cache();cache.obtain_r(.1)
        key=cache._key(.1)
        cache._anchor_bias[key]=np.array([-100.]+[0.]*9)
        d=cache.decision_input(.1,"one_anchor")
        self.assertFalse(d.correction_used)
        self.assertFalse(d.candidate_cone_check_pass)
        self.assertEqual(d.fallback_reason,"NONREALIZABLE_CORRECTED_DECISION_VECTOR")
        self.assertTrue(np.array_equal(d.r_for_step,d.raw_atomic_r))

    def test_wrong_anchor_count_denied(self):
        cache=self.cache()
        with self.assertRaises(CacheBindingError):cache.decision_input(.1,"one_anchor")
        cache.obtain_r(0.)
        with self.assertRaises(CacheBindingError):cache.decision_input(.1,"two_anchors")
        with self.assertRaises(ValueError):cache.decision_input(.1,"unknown")

    def test_original_M7_jacobian_unchanged_by_corrected_r(self):
        cache=self.cache();cache.obtain_r(.15)
        p=cache.decision_input(.2,"one_anchor")
        u=cache.decision_input(.2,"baseline")
        self.assertTrue(np.array_equal(p.Jc_surrogate,u.Jc_surrogate))
        c,_=native_plane_c_and_tangent(self.spec,.2)
        self.assertLess(float(np.abs(u.Jc_surrogate@c).max()),2e-5)

    def test_input_validation(self):
        with self.assertRaises(CacheBindingError):AnalyticAnchorLedger(self.model,self.D[0],self.spec)
        with self.assertRaises(CacheBindingError):AnalyticAnchorLedger(self.model,self.D[:0],self.spec)
        with self.assertRaises(CacheBindingError):AnalyticAnchorLedger(self.model,self.D.clone().requires_grad_(),self.spec)
        with self.assertRaises(ValueError):self.cache().decision_input(.1,"baseline",max_distance=0.)

    def test_all_policies_include_paid_current_truth(self):
        from .m11_experiment import MODEL_POLICIES
        self.assertEqual(set(MODEL_POLICIES),set(POLICIES)|{"current_truth_counterfactual"})

    def test_gauss_newton_finite_step(self):
        cache=self.cache();cache.obtain_r(.1)
        d=cache.decision_input(.2,"one_anchor")
        _,derivative=native_plane_c_and_tangent(self.spec,.2)
        step=gn_step(d.r_for_step,d.Jc_surrogate,derivative,
                     vertical_cut_truth(self.spec,.32)[1])
        self.assertTrue(math.isfinite(step))
        self.assertLessEqual(abs(step),.12)

    def test_training_dataset_identity_with_M10(self):
        from .m10_experiment import centered_dataset
        from .m4_experiment import dataset_digest
        a=centered_dataset(("box","sphere"),per_family=6,seed=67)
        b=centered_dataset(("box","sphere"),per_family=6,seed=67)
        self.assertEqual(dataset_digest(a),dataset_digest(b))
        self.assertEqual(len({x['geometry_id'] for x in a[4]}),12)

    def test_tiny_real_training_and_cost_budget(self):
        result=run(seeds=(67,),steps=2,per_family=6,
                   targets_per_geometry=3,models=("w6_m7_base",))
        self.assertEqual(result['status'],"ANALYTIC_P0_ONLY_NOT_NATIVE_CHERCHI")
        row=result['cases'][0]['models']['w6_m7_base']['evaluation']
        self.assertEqual(row['distinct_heldout_geometry_ids'],6)
        self.assertEqual(row['queried_analytic_support_count_total'],
                        {'baseline':0,'one_anchor':6,'two_anchors':12,
                         'current_truth_counterfactual':18})
        for policy in ('baseline','one_anchor','two_anchors','current_truth_counterfactual'):
            self.assertEqual(row['policy_stats'][policy]['cases'],18)
        self.assertAlmostEqual(row['policy_stats']['one_anchor']['selection_oracle_calls_per_candidate'],1/3)
        self.assertAlmostEqual(row['policy_stats']['two_anchors']['selection_oracle_calls_per_candidate'],2/3)
        self.assertEqual(row['policy_stats']['baseline']['selection_oracle_calls_per_candidate'],0)
        self.assertEqual(row['policy_stats']['current_truth_counterfactual']['selection_oracle_calls_per_candidate'],1)
        self.assertEqual(result['native_W2_calls'],0)

    def test_reverse_target_direction_is_supported(self):
        x=run(seeds=(67,),steps=2,per_family=6,targets_per_geometry=2,
              models=("w6_m7_base",),goal_offset=-.12)
        self.assertAlmostEqual(x['goal_offset'],-.12)
        self.assertEqual(x['cases'][0]['models']['w6_m7_base']['evaluation']['policy_stats']['baseline']['cases'],12)

    def test_failed_experiment_request_before_training(self):
        for kw in [dict(seeds=(19,19)),dict(models=("unknown",)),dict(per_family=2),dict(steps=0),dict(goal_offset=0.0),dict(goal_offset=.25)]:
            with self.assertRaises(ValueError):run(**kw)

    def test_loss_identity_no_insertion_of_true_current_to_no_oracle(self):
        # Policy correction only sees pre-purchased anchors. Current actual r
        # and candidate poststep oracle truth enter scoring AFTER step choice.
        cache=self.cache();cache.obtain_r(-.3);cache.obtain_r(.3)
        with mock.patch('research.NeuralMoments.models.pcraft_ufno.m11_anchor_cache.vertical_cut_truth',
                        side_effect=AssertionError('never query target inside selection')):
            p=cache.decision_input(.27,'two_anchors')
            self.assertTrue(np.isfinite(p.r_for_step).all())
        self.assertEqual(cache.analytic_oracle_calls,2)


if __name__=='__main__': unittest.main()

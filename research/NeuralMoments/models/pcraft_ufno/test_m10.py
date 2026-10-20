"""W6 M10 regression: independent analytic candidate decisions and cost ledger.

Run from repository root:
 python -m unittest research.NeuralMoments.models.pcraft_ufno.test_m10 -v
"""
from __future__ import annotations
import json
import math
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import torch
from .analytic_cut import GeometrySpec, vertical_cut_truth
from .m10_decision import (STRATEGIES, native_plane_c_and_tangent,
                           objective, gn_step, choose_and_evaluate,
                           predicted_backtrack_decision)
from .m10_experiment import (MODEL_NAMES,centered_dataset,centered_voxel,
        make_model,fit_model,evaluate_error,evaluate_decisions,cpu_timing,run)
from .m4_lite_model import num_real_parameters
from .m4_experiment import split_by_geometry,dataset_digest


class TestM10(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(67)
        cls.spec=GeometrySpec('ellipsoid',(.03,-.08,.05),(.6,.4,.72))
        cls.h=.14
        cls.c,cls.r,cls.J=vertical_cut_truth(cls.spec,cls.h)
        cls.goal=vertical_cut_truth(cls.spec,cls.h+.12)[1]

    def test_01_positive_plane_native_coefficient(self):
        c,dc=native_plane_c_and_tangent(self.spec,self.h)
        self.assertEqual(c.shape,(10,));self.assertEqual(dc.shape,(10,))
        self.assertAlmostEqual(float(c@c),1,places=14)
        self.assertGreater(c[3],0)
        self.assertTrue(np.array_equal(c,self.c))

    def test_02_curve_tangent_fd(self):
        e=1e-5
        cp=native_plane_c_and_tangent(self.spec,self.h+e)[0]
        cm=native_plane_c_and_tangent(self.spec,self.h-e)[0]
        dc=native_plane_c_and_tangent(self.spec,self.h)[1]
        self.assertLess(float(np.max(abs((cp-cm)/(2*e)-dc))),3e-10)
        self.assertLess(abs(float(dc@self.c)),1e-13)

    def test_03_chainrule_fd(self):
        for family in ('box','sphere','ellipsoid'):
            s=GeometrySpec(family,(.03,-.04,.09),(.6,.6,.6) if family=='sphere' else (.6,.48,.7))
            h=.23;e=1e-5
            _,_,J=vertical_cut_truth(s,h)
            dc=native_plane_c_and_tangent(s,h)[1]
            fd=(vertical_cut_truth(s,h+e)[1]-vertical_cut_truth(s,h-e)[1])/(2*e)
            self.assertLess(float(np.max(abs(J@dc-fd))),3e-8)

    def test_04_mass_cut_monotone(self):
        for h in (-.55,-.1,.2,.55):
            self.assertGreater(vertical_cut_truth(self.spec,h-.05)[1][0],
                               vertical_cut_truth(self.spec,h+.05)[1][0])

    def test_05_objective_shape_nonfinite(self):
        with self.assertRaises(ValueError):objective([0]*9,self.goal)
        with self.assertRaises(ValueError):objective([math.nan]*10,self.goal)
        self.assertAlmostEqual(objective(self.goal,self.goal),0)

    def test_06_gn_matches_published_w5_formula(self):
        d=self.J@native_plane_c_and_tangent(self.spec,self.h)[1]
        predicted=-float(d@(self.r-self.goal))/(float(d@d)+.01)
        self.assertAlmostEqual(gn_step(self.r,self.J,native_plane_c_and_tangent(self.spec,self.h)[1],
                                       self.goal),float(np.clip(predicted,-.12,.12)))

    def test_07_gn_shape_reject(self):
        with self.assertRaises(ValueError):gn_step(self.r,self.J[:9],np.ones(10),self.goal)
        with self.assertRaises(ValueError):gn_step(self.r,self.J,np.ones(10),self.goal,trust=.5)
        with self.assertRaises(ValueError):gn_step(self.r,self.J,np.ones(10),self.goal,damping=0)

    def test_08_full_oracle_step_progress(self):
        item=choose_and_evaluate(self.spec,self.h,self.r,self.J,self.goal,strategy='gn')
        self.assertTrue(item.actual_accept)
        self.assertEqual(item.additional_selection_oracle_calls,0)
        self.assertLessEqual(abs(item.step),.12+1e-12)
        self.assertGreater(item.actual_improvement,0)

    def test_09_stale_oracle_j_does_not_influence_proxy_step(self):
        r1=choose_and_evaluate(self.spec,self.h,self.r,self.J,self.goal,
                               strategy='gn',oracle_r=self.r,oracle_j=self.J)
        r2=choose_and_evaluate(self.spec,self.h,self.r,self.J,self.goal,
                               strategy='gn',oracle_r=np.zeros(10),oracle_j=np.eye(10))
        self.assertEqual(r1.step,r2.step)
        self.assertEqual(r1.additional_selection_oracle_calls,0)
        self.assertNotEqual(r1.oracle_step_abs_error,r2.oracle_step_abs_error)

    def test_10_checked_backtracking_charges_truth(self):
        wrong=-self.J
        result=choose_and_evaluate(self.spec,self.h,self.r,wrong,self.goal,
                                   strategy='checked_backtrack')
        self.assertGreaterEqual(result.additional_selection_oracle_calls,1)
        self.assertLessEqual(result.additional_selection_oracle_calls,4)
        self.assertFalse(result.actual_accept)
        self.assertEqual(result.step,0.)

    def test_11_checked_never_return_worse_step(self):
        for multiplier in (-1.,.01,1.,5.):
            res=choose_and_evaluate(self.spec,self.h,self.r,self.J*multiplier,self.goal,
                                    strategy='checked_backtrack')
            self.assertGreaterEqual(res.actual_improvement,-1e-12)
            self.assertLessEqual(abs(res.step),.12+1e-12)

    def test_12_mass_guard_no_extra_truth(self):
        res=choose_and_evaluate(self.spec,self.h,self.r,-self.J,self.goal,
                                strategy='mass_sign_guard')
        self.assertEqual(res.additional_selection_oracle_calls,0)
        self.assertGreater(res.step,0.)

    def test_13_policy_name_and_domain_fail_closed(self):
        with self.assertRaises(ValueError):choose_and_evaluate(self.spec,self.h,self.r,self.J,self.goal,strategy='nonsense')
        with self.assertRaises(ValueError):choose_and_evaluate(self.spec,.97,self.r,self.J,self.goal,strategy='gn')
        with self.assertRaises(ValueError):choose_and_evaluate(self.spec,self.h,self.r,self.J,self.goal,strategy='gn',backtrack=(.5,))
        self.assertEqual(len(STRATEGIES),4)

    def test_14_w5_w6_parameter_capacity(self):
        counts=[num_real_parameters(make_model(n,67)) for n in MODEL_NAMES]
        self.assertEqual(counts,[13448,13448,13939])
        self.assertLess(max(counts)/min(counts),1.05)

    def test_15_four_channel_centered_no_labels(self):
        vol=centered_voxel(self.spec,8)
        self.assertEqual(tuple(vol.shape),(4,8,8,8))
        self.assertTrue(torch.all(vol[0]>=0))
        self.assertTrue(torch.all((vol[1]>=0)&(vol[1]<=1)))
        self.assertTrue(torch.isfinite(vol).all())
        with self.assertRaises(ValueError):centered_voxel(self.spec,4)

    def test_16_train_family_geometry_split(self):
        all_data=centered_dataset(('box','sphere'),per_family=6,seed=67)
        test=centered_dataset(('ellipsoid',),per_family=6,seed=68)
        self.assertEqual(tuple(all_data[0].shape),(24,4,8,8,8))
        train,valid,info=split_by_geometry(all_data,67,validation_geometries_per_family=1)
        self.assertEqual(info['train_geo'],10)
        self.assertEqual(info['val_geo'],2)
        train_ids={x['geometry_id'] for x in train[4]}
        valid_ids={x['geometry_id'] for x in valid[4]}
        test_ids={x['geometry_id'] for x in test[4]}
        self.assertFalse(train_ids&valid_ids)
        self.assertFalse((train_ids|valid_ids)&test_ids)

    def test_17_identical_input_label_budgets(self):
        d=centered_dataset(('box','sphere'),per_family=6,seed=67)
        m1=make_model('w6_m7_base',67)
        m2=make_model('w5_voxel_deeponet',67)
        self.assertEqual(d[0].shape[1],4)
        self.assertEqual(m1.encode_geometry(d[0][:1]).shape[0],1)
        self.assertEqual(m2.encode_geometry(d[0][:1]).shape[0],1)
        self.assertEqual(dataset_digest(d),dataset_digest(centered_dataset(('box','sphere'),per_family=6,seed=67)))

    def test_18_early_stop_reuses_identical_labels(self):
        d=centered_dataset(('box','sphere'),per_family=6,seed=67)
        train,valid,_=split_by_geometry(d,67,validation_geometries_per_family=1)
        a=make_model('w6_m7_base',67)
        b=make_model('w6_m7_directional',67)
        x=fit_model(a,'w6_m7_base',train,valid,seed=67,steps=2)
        y=fit_model(b,'w6_m7_directional',train,valid,seed=67,steps=2)
        self.assertEqual(x['minibatch_schedule_sha256'],y['minibatch_schedule_sha256'])
        self.assertEqual(x['train_label_counts'],y['train_label_counts'])
        self.assertEqual(x['train_label_counts']['extra_oracle'],0)
        self.assertGreater(y['directional_loss_weight'],0)

    def test_19_predicted_backtrack_queries_only_model(self):
        model=make_model('w6_m7_base',67).eval()
        d=centered_voxel(self.spec,8).unsqueeze(0)
        with patch.object(model,'encode_geometry',wraps=model.encode_geometry) as encoder:
            with torch.no_grad():z=model.encode_geometry(d).detach()
            result=predicted_backtrack_decision(self.spec,self.h,z,model,self.goal)
            self.assertEqual(encoder.call_count,1)
        self.assertEqual(result.additional_selection_oracle_calls,0)
        self.assertGreaterEqual(result.additional_surrogate_moment_calls,1)
        self.assertLessEqual(result.additional_surrogate_moment_calls,4)

    def test_20_decision_report_budget_and_structure(self):
        report=run(seeds=(67,),steps=2,per_family=6)
        self.assertEqual(set(report['aggregate']),set(MODEL_NAMES))
        self.assertEqual(report['W2_native_training_admitted'],0)
        self.assertFalse(report['W2_H8f_81_archived_used'])
        self.assertEqual(report['trainable_real_parameters']['w6_m7_base'],13448)
        for model in report['cases'][0]['models'].values():
            policies=model['decision']['metrics']
            self.assertEqual(policies['gn']['selection_additional_oracle_calls'],0)
            self.assertEqual(policies['mass_sign_guard']['selection_additional_oracle_calls'],0)
            self.assertEqual(policies['predicted_backtrack']['selection_additional_oracle_calls'],0)
            self.assertGreater(policies['checked_backtrack']['selection_additional_oracle_calls'],0)
            self.assertEqual(policies['gn']['total_cases'],12)
            self.assertGreater(model['cpu_timing']['cached_J_ms'],0)

    def test_21_source_spec_blocking_unapproved_inputs(self):
        with self.assertRaises(ValueError):run(seeds=(),steps=2,per_family=6)
        with self.assertRaises(ValueError):run(seeds=(67,67),steps=2,per_family=6)
        with self.assertRaises(ValueError):run(seeds=(67,),steps=0,per_family=6)
        with self.assertRaises(ValueError):run(seeds=(67,),steps=1,per_family=1)
        with self.assertRaises(ValueError):run(seeds=(67,),steps=1,per_family=6,models=('invalid',))

    def test_22_freeze_previously_published_three_seed_numbers(self):
        path=Path(__file__).with_name('m10_three_seed_cpu.json')
        if not path.is_file():self.skipTest('not yet generated')
        record=json.loads(path.read_text())
        self.assertEqual(record['seeds'],[67,71,73])
        self.assertEqual(record['config']['steps_max'],100)
        self.assertEqual(record['W2_native_training_admitted'],0)
        self.assertLess(abs(record['aggregate']['w6_m7_base']['heldout']['r_mae']['mean']-.0097865),1e-5)
        self.assertLess(abs(record['aggregate']['w5_voxel_deeponet']['decisions']['gn']['accepted_fraction']['mean']-.8583333),1e-5)


if __name__=='__main__':unittest.main()

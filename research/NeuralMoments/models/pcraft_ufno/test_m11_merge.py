"""W6 M11: hostile merger / source identity / query-budget regressions."""
from __future__ import annotations
import copy
import unittest

from .m11_experiment import MODEL_POLICIES, MODEL_NAMES
from .m11_merge import AuditMismatch, merge


def fake_report(*,seeds=(3,5,7),goal_offset=.12):
    cases=[]
    for seed in seeds:
        models={}
        for name in MODEL_NAMES:
            records={p:[] for p in MODEL_POLICIES}
            for gid in ('a'*64,'b'*64):
                for h in (-.2,.25):
                    for policy in MODEL_POLICIES:
                        records[policy].append(dict(seed=seed,geometry_sha256=gid,h_local=h,
                                                    accepted=0 if policy=='baseline' else 1,
                                                    gradient_sign_wrong=0,
                                                    step_abs_error=0.,signed_regret=0.,
                                                    true_decrease=.01,corrected_mae=0.,
                                                    cone_pass=1,correction_used=int(policy!='baseline'),
                                                    anchor_fallback=0,trust_clipped=0,
                                                    selection_oracle_calls_charged={
                                                        'baseline':0.,'one_anchor':.5,'two_anchors':1.,
                                                        'current_truth_counterfactual':1.}[policy]))
            models[name]={'parameters_real':13448,
                'training':{'selected_step':10,'minibatch_schedule_sha256':'f'*64},
                'evaluation':{'per_case':records,'targets_per_geometry':2,
                 'distinct_heldout_geometry_ids':2,
                 'queried_analytic_support_count_total':{
                     'baseline':0,'one_anchor':2,'two_anchors':4,
                     'current_truth_counterfactual':4}}}
        cases.append(dict(seed=seed,training_tensor_sha256='a'*64,
                          heldout_tensor_sha256='b'*64,models=models))
    return {'schema':'W6_M11_ANCHORED_DECISION_AUDIT_V1',
            'status':'ANALYTIC_P0_ONLY_NOT_NATIVE_CHERCHI',
            'native_W2_admitted_training_labels':0,'native_W2_calls':0,
            'goal_offset':goal_offset,'seeds':list(seeds),'cases':cases}


class TestM11Merge(unittest.TestCase):
    def setUp(self):
        self.a=fake_report(seeds=(3,),goal_offset=.12)
        self.b=fake_report(seeds=(5,7),goal_offset=.12)
        self.c=fake_report(seeds=(3,5,7),goal_offset=-.12)

    def merged(self):return merge(copy.deepcopy(self.a),copy.deepcopy(self.b),copy.deepcopy(self.c))

    def test_good_merge_recomputes_all_selection_calls(self):
        m=self.merged()
        self.assertEqual(m['seeds'],[3,5,7])
        self.assertEqual(m['eligible_W2_labels'],0)
        self.assertEqual(m['models']['w6_m7_base']['positive']['two_anchors']['paid_selection_oracle_calls'],12.)
        self.assertEqual(m['models']['w6_m7_base']['negative']['one_anchor']['oracle_calls_per_candidate'],.5)
        self.assertEqual(m['models']['w5_voxel_deeponet']['positive']['two_anchors']['n_cases'],12)
        self.assertEqual(m['models']['w5_voxel_deeponet']['positive']['two_anchors']['paired_bootstrap_vs_zero']['geometry_groups'],6)

    def test_denies_fake_native_source(self):
        d=copy.deepcopy(self.a);d['native_W2_calls']=1
        with self.assertRaises(AuditMismatch):merge(d,self.b,self.c)
        d=copy.deepcopy(self.c);d['status']='NATIVE_VERIFIED'
        with self.assertRaises(AuditMismatch):merge(self.a,self.b,d)

    def test_denies_duplicate_or_mismatched_seed(self):
        d=copy.deepcopy(self.b);d['cases'][1]['seed']=5
        with self.assertRaises(AuditMismatch):merge(self.a,d,self.c)
        d=copy.deepcopy(self.b);d['seeds']=[5,5]
        with self.assertRaises(AuditMismatch):merge(self.a,d,self.c)

    def test_denies_dataset_and_checkpoint_mismatch(self):
        d=copy.deepcopy(self.c);d['cases'][0]['training_tensor_sha256']='c'*64
        with self.assertRaises(AuditMismatch):merge(self.a,self.b,d)
        d=copy.deepcopy(self.c)
        d['cases'][0]['models']['w6_m7_base']['training']['selected_step']=50
        with self.assertRaises(AuditMismatch):merge(self.a,self.b,d)

    def test_denies_anchor_query_count_underreport(self):
        d=copy.deepcopy(self.a)
        d['cases'][0]['models']['w6_m7_base']['evaluation']['queried_analytic_support_count_total']['two_anchors']=0
        with self.assertRaises(AuditMismatch):merge(d,self.b,self.c)

    def test_denies_unpaired_controls(self):
        d=copy.deepcopy(self.c)
        r=d['cases'][0]['models']['w6_m7_base']['evaluation']['per_case']['two_anchors']
        r[0]['h_local']=.101
        with self.assertRaises(AuditMismatch):merge(self.a,self.b,d)

    def test_legacy_positive_default_requires_valid_reverse_goal(self):
        a=copy.deepcopy(self.a);b=copy.deepcopy(self.b)
        a.pop('goal_offset');b.pop('goal_offset')
        merged=merge(a,b,self.c)
        self.assertTrue(merged['positive_legacy_CLI_goal_offset_inferred_from_documented_default'])
        c=copy.deepcopy(self.c);c['goal_offset']=.12
        with self.assertRaises(AuditMismatch):merge(a,b,c)

    def test_nonlegacy_wrong_direction_rejected(self):
        c=copy.deepcopy(self.c);c['goal_offset']=-.5
        with self.assertRaises(AuditMismatch):merge(self.a,self.b,c)


if __name__=='__main__':unittest.main()

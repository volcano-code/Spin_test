"""W6 M12 local no-W2 CPU regression and explicit oracle-budget/admission checks."""
import dataclasses, hashlib, inspect, math, unittest
from unittest.mock import patch
import numpy as np
import torch
from .analytic_cut import GeometrySpec, TEACHER_KIND, vertical_cut_truth
from .m10_experiment import centered_voxel, make_model
from .m11_anchor_cache import AnalyticAnchorLedger, NativeLabelsUnavailable, CacheBindingError
from .m12_value_policy import (cellwise_positive_cut_mass, observe_risk,
    ObservableRisk,FrozenVOIPolicy,calibration_identity,select_thresholds)
from .m12_experiment import (tasks_for_geometry,specs_from_dataset,_simulated_policy_rows,
    _family_scores,_geometry_experiment,run)
from .m10_decision import native_plane_c_and_tangent

class TestW6M12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        torch.manual_seed(107)

    def setUp(self):
        self.box=GeometrySpec('box',(0.,0.,0.),(1.,1.,1.))
        self.ball=GeometrySpec('sphere',(.02,-.03,.04),(.6,.6,.6))

    def test_exact_uniform_cell_mass_half(self):
        D=torch.ones(1,4,8,8,8)
        for h,expected in ((-2.,8.),(-1.,8.),(0.,4.),(.2,3.2),(1.,0.),(2.,0.)):
            self.assertAlmostEqual(cellwise_positive_cut_mass(D,h),expected,places=12)

    def test_cell_mass_nonnegative_monotonic(self):
        D=centered_voxel(self.ball,8).unsqueeze(0)
        heights=np.linspace(-1,1,13)
        results=[cellwise_positive_cut_mass(D,h) for h in heights]
        self.assertTrue(all(a>=b-1e-13 for a,b in zip(results,results[1:])))
        self.assertTrue(results[0]>=results[-1]>=0)

    def test_cell_source_requires_center_cell_contract(self):
        with self.assertRaises(ValueError):cellwise_positive_cut_mass(torch.ones(4,8,8,8),0)
        with self.assertRaises(ValueError):cellwise_positive_cut_mass(torch.ones(1,3,8,8,8),0)
        with self.assertRaises(ValueError):cellwise_positive_cut_mass(torch.ones(1,4,7,8,8),0)
        with self.assertRaises(ValueError):cellwise_positive_cut_mass(torch.ones(1,4,8,8,8),float('nan'))

    def test_occupancy_and_density_fail_closed(self):
        D=torch.ones(1,4,8,8,8)
        D[:,0]=-1
        with self.assertRaises(ValueError):cellwise_positive_cut_mass(D,0)
        D[:,0]=1;D[:,1]=1.5
        with self.assertRaises(ValueError):cellwise_positive_cut_mass(D,0)
        D[:,1]=float('inf')
        with self.assertRaises(ValueError):cellwise_positive_cut_mass(D,0)

    def test_proxy_requires_frozen_cpu(self):
        D=torch.ones(1,4,8,8,8,requires_grad=True)
        with self.assertRaises(ValueError):cellwise_positive_cut_mass(D,0.)

    def test_mixed_tasks_balanced_goals(self):
        rows=tasks_for_geometry(self.ball,seed=107,target_count=8)
        self.assertEqual(len(rows),8)
        self.assertEqual(sum(x['direction']==1 for x in rows),4)
        self.assertEqual(sum(x['direction']==-1 for x in rows),4)
        other=tasks_for_geometry(self.ball,seed=107,target_count=8)
        self.assertEqual([x['h'] for x in rows],[x['h'] for x in other])
        for x in rows:
            self.assertEqual(tuple(x['goal'].shape),(10,))
            self.assertLess(abs(x['h']),.56)

    def test_invalid_mixed_task_budget(self):
        for k in (0,1,3):
            with self.assertRaises(ValueError):tasks_for_geometry(self.ball,seed=107,target_count=k)

    def test_risk_does_not_receive_truth_array(self):
        params=set(inspect.signature(observe_risk).parameters)
        self.assertEqual(params,{'model','z','D','native_c','tangent','goal_r','h_world'})
        self.assertNotIn('r_true',params)
        self.assertNotIn('J_true',params)

    def test_model_risk_without_teacher_fn(self):
        model=make_model('w6_m7_base',107).eval()
        D=centered_voxel(self.ball,8).unsqueeze(0)
        rows=tasks_for_geometry(self.ball,seed=107,target_count=4)
        with torch.no_grad():z=model.encode_geometry(D).detach()
        with patch('research.NeuralMoments.models.pcraft_ufno.m12_experiment.vertical_cut_truth',side_effect=RuntimeError('oracle must be unavailable')):
            risk=observe_risk(model,z,D,np.stack([x['c'] for x in rows]),
                np.stack([x['tangent'] for x in rows]),np.stack([x['goal'] for x in rows]),
                np.array([x['world_h'] for x in rows]))
        self.assertGreaterEqual(risk.score,0)
        self.assertTrue(math.isfinite(risk.score))
        self.assertEqual(risk.target_count,4)

    def test_risk_fails_on_shape_mismatch(self):
        model=make_model('w6_m7_base',107).eval()
        D=centered_voxel(self.ball,8).unsqueeze(0)
        with torch.no_grad():z=model.encode_geometry(D).detach()
        c=np.zeros((1,10));goal=np.zeros((1,10))
        with self.assertRaises(ValueError):observe_risk(model,z,D,c,c,goal,np.zeros(2))

    def test_policy_rejects_invalid_thresholds(self):
        pin='a'*64
        for l,h in ((-.1,0),(.5,.2),(math.nan,1.)):
            with self.assertRaises(ValueError):FrozenVOIPolicy(l,h,.2,pin,107)

    def test_policy_does_not_see_oracle_outcomes(self):
        p=FrozenVOIPolicy(.05,.12,.2,'f'*64,107)
        self.assertEqual([p.select(ObservableRisk(s,0,0,0,8)) for s in (0,.05,.1,.13)], [0,0,1,2])
        self.assertNotIn('accepted',inspect.signature(FrozenVOIPolicy.select).parameters)

    def test_geometry_calibration_id_is_order_invariant(self):
        x,y='a'*64,'b'*64
        self.assertEqual(calibration_identity([x,y]),calibration_identity([y,x]))
        with self.assertRaises(ValueError):calibration_identity([x,x])

    def test_threshold_fitting_validation_only_and_query_cost(self):
        rows=[{'geometry_id':str(i)*64,'risk_score':.01*i,'cases':8,
            'acceptances':[.5,1.,1.] if i%2 else [1.,1.,1.]}
               for i in (1,2,3)]
        p,meta=select_thresholds(rows,price=.2,seed=107)
        self.assertEqual(p.calibration_geometry_sha256,calibration_identity(x['geometry_id'] for x in rows))
        self.assertTrue(meta['calibration_only_not_test'])
        self.assertLessEqual(meta['calibration_selected_calls_per_candidate'],.25)

    def test_strong_query_price_prefers_free_policy(self):
        rows=[{'geometry_id':'1'*64,'risk_score':.2,'cases':8,'acceptances':[.875,1.,1.]}]
        p,_=select_thresholds(rows,price=20,seed=107)
        self.assertEqual(p.select(ObservableRisk(.2,0,0,0,8)),0)

    def test_malformed_validation_rejected(self):
        with self.assertRaises(ValueError):select_thresholds([],price=.2,seed=107)
        with self.assertRaises(ValueError):select_thresholds([{'geometry_id':'a'*64,'risk_score':float('nan'),'cases':8,'acceptances':[0,1,1]}],price=.2,seed=107)

    def test_one_encoder_and_exact_oracle_selection_budget(self):
        model=make_model('w6_m7_base',107).eval()
        D=centered_voxel(self.ball,8).unsqueeze(0)
        tasks=tasks_for_geometry(self.ball,seed=107,target_count=4)
        for k in (0,1,2):
            result=_simulated_policy_rows(model,D,self.ball,tasks,k=k)
            self.assertEqual(result['calls']['selection_analytic_r_calls'],k)
            self.assertEqual(result['calls']['encoder_calls'],1)
            self.assertEqual(len(result['cases']),4)

    def test_excluded_W2_cannot_be_purchased(self):
        model=make_model('w6_m7_base',107).eval()
        D=centered_voxel(self.ball,8).unsqueeze(0)
        ledger=AnalyticAnchorLedger(model,D,self.ball)
        with self.assertRaises(NativeLabelsUnavailable):ledger.obtain_r(0.,source='W2_H8F_ARCHIVED')
        self.assertEqual(ledger.analytic_oracle_calls,0)

    def test_atom_fitting_keeps_necessary_moments(self):
        model=make_model('w6_m7_base',107).eval()
        D=centered_voxel(self.ball,8).unsqueeze(0)
        tasks=tasks_for_geometry(self.ball,seed=107,target_count=4)
        for k in (0,1,2):
            result=_simulated_policy_rows(model,D,self.ball,tasks,k=k,mode='bounded_atoms')
            self.assertEqual(result['calls']['selection_analytic_r_calls'],k)
            self.assertEqual(result['necessary_material_gate'],'M8 nonnegative bounded-atom-weight representation')

    def test_risk_selection_counted_per_geometry(self):
        fake=[{'geometry_id':'a'*64,'observable':{'score':.2,'discrepancy':0.,'direction_conflict':0.,'near_target_fraction':0.,'target_count':4,'sensor':'CELL_CENTER_PROXY_AND_SURROGATE_ONLY_NO_ORACLE'},
               'decision_only':{str(k):{'calls':{'selection_analytic_r_calls':k},'cases':[{'accepted':1,'correction_used':int(k>0),'fallback':0,'true_decrease':.01,'goal_direction':(1 if i%2==0 else -1)} for i in range(4)]} for k in range(3)}}]
        p=FrozenVOIPolicy(.01,.1,.2,'a'*64,107)
        result=_family_scores(fake,policy=p)
        self.assertEqual(result['selection_r_only_queries'],2)
        self.assertAlmostEqual(result['selection_calls_per_target'],.5)

    def test_new_seed_tiny_end_to_end_split(self):
        out=run(seeds=(107,),steps=2,per_family=6,target_count=4,models=('w6_m7_base',))
        self.assertEqual(out['native_W2_admitted_labels'],0)
        self.assertEqual(out['seed_records'][0]['heldout_geometries'],6)
        result=out['seed_records'][0]['model_runs']['w6_m7_base']
        self.assertTrue(result['validation_policy_and_heldout_no_overlap'])
        self.assertEqual(result['heldout']['0']['selection_r_only_queries'],0)
        self.assertEqual(result['heldout']['2']['selection_r_only_queries'],12)
        self.assertIn('voi_frozen',result['physical_bounded_atom_comparison'])

if __name__=='__main__':unittest.main()

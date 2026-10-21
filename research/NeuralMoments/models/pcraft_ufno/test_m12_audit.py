"""M12 aggressive replay-integrity regression (separate from runtime tests)."""
import copy,unittest
from .m12_audit import audit,AuditError
from .m12_experiment import run

class TestAuditM12(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=run(seeds=(107,),steps=2,per_family=6,target_count=4,
                       models=('w6_m7_base','w5_voxel_deeponet'))

    def test_valid_replay(self):
        self.assertEqual(audit(copy.deepcopy(self.result))['status'],'PASS_NOT_NATIVE')

    def assert_reject(self,mutation):
        x=copy.deepcopy(self.result);mutation(x)
        with self.assertRaises((AuditError,ValueError,KeyError)):
            audit(x)

    def test_native_count_must_remain_zero(self):
        self.assert_reject(lambda x:x.__setitem__('native_W2_admitted_labels',81))

    def test_native_calls_cannot_be_forged(self):
        self.assert_reject(lambda x:x.__setitem__('native_W2_calls',1))

    def test_no_repeated_seed(self):
        self.assert_reject(lambda x:x.__setitem__('seeds',[107,107]))

    def test_no_test_id_inside_development(self):
        def mutate(x):
            m=x['seed_records'][0]['model_runs']['w6_m7_base']
            m['policy_calibration_receipts'][0]['geometry_id']=m['heldout_per_geometry'][0]['geometry_id']
            m['frozen_policy']['calibration_geometry_sha256']='a'*64
        self.assert_reject(mutate)

    def test_no_changed_expected_cost(self):
        def mutate(x):x['seed_records'][0]['model_runs']['w6_m7_base']['heldout_per_geometry'][0]['decision_only']['2']['calls']['selection_analytic_r_calls']=0
        self.assert_reject(mutate)

    def test_no_changed_hidden_candidate_outcome(self):
        def mutate(x):
            cases=x['seed_records'][0]['model_runs']['w6_m7_base']['heldout_per_geometry'][0]['decision_only']['1']['cases']
            cases[0]['accepted']=1-cases[0]['accepted']
        self.assert_reject(mutate)

    def test_no_fake_free_risk_surrogate(self):
        def mutate(x):x['seed_records'][0]['model_runs']['w6_m7_base']['heldout_per_geometry'][0]['risk_extra_surrogate_r_and_J_evaluations']=0
        self.assert_reject(mutate)

    def test_no_incorrect_direction_mix(self):
        def mutate(x):x['seed_records'][0]['model_runs']['w6_m7_base']['heldout_per_geometry'][0]['decision_only']['0']['cases'][0]['goal_direction']=0
        self.assert_reject(mutate)

    def test_no_changed_aggregate_acceptance(self):
        self.assert_reject(lambda x:x['aggregate']['w6_m7_base']['0'].__setitem__('mean_acceptance',.5))

if __name__=='__main__':unittest.main()

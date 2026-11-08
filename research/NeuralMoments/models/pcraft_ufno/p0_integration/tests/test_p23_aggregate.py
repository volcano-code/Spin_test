import json,tempfile,unittest
from pathlib import Path
from research.NeuralMoments.models.pcraft_ufno.p0_integration.p23_aggregate import aggregate
def row(p,t,r,j):
 return {"pino_source_seed":p,"training_seed":t,"pino_parameters_frozen":True,"zero_gate_exact_pino_parity":True,
 "baseline_pino":{"heldout":{"negative_mass_fraction":0}},
 "quadrann_enhanced":{"heldout":{"negative_mass_fraction":0}},
 "improvement":{"heldout_r_relative_l2_fraction":r,"heldout_J_relative_l2_fraction":j},
 "quadrann_gate_selected":.01,"best_validation_step":60,"training_seconds":60.}
class P23Tests(unittest.TestCase):
 def test_all_three_positive_stays_optional(self):
  with tempfile.TemporaryDirectory() as d:
   for p,t in ((271,883),(277,887),(281,991)):(Path(d)/f"w6_p23_quadrann_pino{p}_seed{t}.json").write_text(json.dumps(row(p,t,.1,.05)))
   x=aggregate(d);self.assertTrue(x["aggregate"]["repeatable_both_metric_gain"]);self.assertFalse(x["claims"]["production_default"])
 def test_mixed_result_not_promoted(self):
  with tempfile.TemporaryDirectory() as d:
   for (p,t),(r,j) in zip(((271,883),(277,887),(281,991)),((.1,.05),(.1,-.01),(.02,.03))):(Path(d)/f"w6_p23_quadrann_pino{p}_seed{t}.json").write_text(json.dumps(row(p,t,r,j)))
   self.assertEqual(aggregate(d)["decision"],"KEEP_OPTIONAL_NO_PROMOTION")
if __name__=="__main__":unittest.main()

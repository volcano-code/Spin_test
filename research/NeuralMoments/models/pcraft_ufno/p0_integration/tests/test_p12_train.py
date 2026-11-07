"""P12 matched frozen PINO / original upstream adapter / split UQ checks."""
import unittest
import torch

from research.NeuralMoments.models.pcraft_ufno.p0_integration.p12_train import (
    _make_arm, _predict_by_geometry, _new_pino, ARMS, run,
)
from research.NeuralMoments.models.pcraft_ufno.spin_pino.dataset import generate_splits


class P12TrainingContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_same_frozen_pino_for_three_source_adapters(self):
        baseline=_new_pino()
        state=baseline.state_dict()
        models=[_make_arm(x,state,131) for x in ARMS]
        for k,v in state.items():
            for model in models:
                self.assertTrue(torch.equal(v,model.pino.state_dict()[k]))
        self.assertTrue(any(x.requires_grad for x in models[0].pino.weight_head.parameters()))
        self.assertFalse(any(x.requires_grad for x in models[1].pino.parameters()))
        self.assertFalse(any(x.requires_grad for x in models[2].pino.parameters()))
        self.assertTrue(models[2].quadrann_condition_on_material)

    def test_geometry_id_grouped_eval_preserves_finite_j(self):
        data=generate_splits(seed=131,train_geometries_per_family=4,
                             test_ellipsoid_geometries=2,grid_size=8)
        pino=_new_pino()
        with torch.no_grad():
            out=_predict_by_geometry(_make_arm("pino_head",pino.state_dict(),131),data["test"])
        self.assertEqual(out["unique_geometry_count"],2)
        self.assertEqual(out["total_queries"],4)
        self.assertTrue(torch.isfinite(out["r"]).all())
        self.assertTrue(torch.isfinite(out["J"]).all())
        self.assertFalse(out["model_J_native_admitted"])

    def test_short_three_arm_and_uqno_cannot_admit_newton(self):
        result=run(seeds=(13,),base_steps=2,adapter_steps=1,uq_steps=2,
                   train_geometries_per_family=8,test_ellipsoids=2)
        self.assertEqual(len(result["aggregate"]),3)
        self.assertTrue(result["same_frozen_pretrained_PINO_per_seed"])
        self.assertTrue(result["parameter_and_flop_budgets_not_matched"])
        self.assertTrue(result["uq_aggregate"]["all_native_newton_admissions_withheld"])
        self.assertFalse(result["claims"]["full_512_cube_training"])
        self.assertEqual(result["per_seed"][0]["val_geometries"],4)
        self.assertEqual(result["per_seed"][0]["test_geometries"],2)
        for arm in result["per_seed"][0]["arms"]:
            self.assertEqual(arm["updates"],1)


if __name__=="__main__":
    unittest.main()

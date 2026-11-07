"""M10b data separation, equal-architecture ablations, analytic CPU smoke."""
import unittest
import torch

from research.NeuralMoments.models.pcraft_ufno.spin_pino.m10b_train import (
    make_splits, _make_model, _encode, _eval, run, ARMS,
)


class M10bTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1)

    def test_geometry_disjoint_and_heldout_family(self):
        data,receipt=make_splits(seed=137,source_resolution=16,
                                 geometries_per_family=4,test_ellipsoids=2)
        self.assertTrue(receipt["geometry_disjoint"])
        sets=[set(receipt["split_ids"][x]) for x in ("fit","validation","test")]
        self.assertFalse((sets[0]&sets[1]) or (sets[0]&sets[2]) or (sets[1]&sets[2]))
        self.assertEqual({x["family"] for x in data["test"]},{"ellipsoid"})
        self.assertEqual(receipt["query_counts"]["test"],4)
        self.assertFalse(receipt["W2_or_Cherchi_labels_used"])

    def test_source_digest_is_stable_and_changes_with_seed(self):
        _,a=make_splits(seed=37,source_resolution=16,
                        geometries_per_family=4,test_ellipsoids=2)
        _,b=make_splits(seed=37,source_resolution=16,
                        geometries_per_family=4,test_ellipsoids=2)
        _,c=make_splits(seed=38,source_resolution=16,
                        geometries_per_family=4,test_ellipsoids=2)
        self.assertEqual(a["source_sha256"],b["source_sha256"])
        self.assertNotEqual(a["source_sha256"],c["source_sha256"])

    def test_same_pino_init_and_equal_auxiliary_parameter_counts(self):
        models=[_make_model(x,131,8,16) for x in ARMS]
        sd=[m.state_dict() if i==0 else m.pino.state_dict()
            for i,m in enumerate(models)]
        for k in sd[0]:
            self.assertTrue(torch.equal(sd[0][k],sd[1][k]))
            self.assertTrue(torch.equal(sd[0][k],sd[2][k]))
        counts=[sum(p.numel() for p in m.parameters()) for m in models]
        self.assertEqual(counts[1],counts[2])
        self.assertGreater(counts[1],counts[0])

    def test_arms_produce_finite_forward_and_test_metrics(self):
        data,_=make_splits(seed=41,source_resolution=16,
                            geometries_per_family=4,test_ellipsoids=2)
        for arm in ARMS:
            model=_make_model(arm,41,8,16).eval()
            with torch.no_grad():
                w=_encode(model,data["test"][0],source_resolution=16)
                metrics=_eval(model,data["test"],source_resolution=16)
            self.assertEqual(w.ndim,2)
            self.assertTrue(bool((w>=0).all()))
            self.assertGreater(metrics["r_relative_l2"],0.)
            self.assertTrue(torch.isfinite(torch.tensor(metrics["J_relative_l2"])))

    def test_short_train_validates_each_arm_without_test_selection(self):
        result=run(seeds=(13,),steps=2,source_resolution=16,
                   geometries_per_family=4,test_ellipsoids=2)
        self.assertEqual(len(result["aggregate"]),3)
        self.assertEqual(result["steps_per_arm_per_seed"],2)
        self.assertTrue(result["same_split_and_oracle_budget"])
        self.assertTrue(result["same_auxiliary_parameter_count"])
        self.assertEqual({x["arm"] for x in result["aggregate"]},set(ARMS))
        for row in result["per_seed"][0]["arms"]:
            self.assertLessEqual(row["selected_step"],2)
            self.assertEqual(row["optimizer_updates"],2)


if __name__=="__main__":
    unittest.main()

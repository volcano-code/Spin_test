import json, tempfile, unittest
from pathlib import Path
import numpy as np
from m29_3_2_partial_fd_audit import audit

class PartialFDAuditTests(unittest.TestCase):
    def test_partial_columns_are_preserved_and_compared(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);q=np.zeros(10);q[0]=1
            B=np.zeros((10,9));B[1:,:]=np.eye(9)
            J=np.ones((10,9))
            summary={"schema":"w1-m29-3-2-fresh-native-tangent-fd-v1",
              "expected_function_evaluations":4,"steps":[1e-3,1e-4],
              "tangent_basis":B.tolist(),"analytic_tangent_jacobian":J.tolist(),
              "base_m9_topology_hash":"base"}
            (root/"summary.json").write_text(json.dumps(summary))
            rows=[]
            for h in summary["steps"]:
                for j in range(9):
                    # Use 2 directions at coarse h, 1 at fine h.
                    valid=(j<2 if h==1e-3 else j<1)
                    for side,sign in (("plus",1),("minus",-1)):
                        rows.append({"step":h,"direction":j,"side":side,
                          "topology_matches_base":valid,"topology_hash":"base" if valid else "other",
                          "operation":"difference","surface_type":"ELLIPSOID","cap_face_count":0,
                          "ten":(sign*h*np.ones(10)).tolist()})
            (root/"samples.jsonl").write_text("".join(json.dumps(x)+"\n" for x in rows))
            result=audit(root/"summary.json",root/"samples.jsonl",root/"out.json")
            self.assertEqual(result["step_results"]["0.001"]["valid_directions"],[0,1])
            self.assertEqual(result["step_results"]["0.0001"]["valid_directions"],[0])
            self.assertEqual(result["step_results"]["0.001"]["partial_metrics"]["max_direction_relative_error"],0.0)

    def test_reject_incomplete_pairs(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            summary={"schema":"w1-m29-3-2-fresh-native-tangent-fd-v1",
              "expected_function_evaluations":2,"steps":[1e-3],
              "tangent_basis":np.zeros((10,9)).tolist(),
              "analytic_tangent_jacobian":np.zeros((10,9)).tolist(),
              "base_m9_topology_hash":"base"}
            (root/"summary.json").write_text(json.dumps(summary))
            (root/"samples.jsonl").write_text(json.dumps({"step":1e-3,"direction":0,"side":"plus"})+"\n")
            with self.assertRaisesRegex(ValueError,"SAMPLE_COUNT_MISMATCH"):
                audit(root/"summary.json",root/"samples.jsonl",root/"out.json")

if __name__=="__main__":unittest.main()

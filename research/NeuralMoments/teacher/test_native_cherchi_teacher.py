"""Run: python -m unittest discover -s research/NeuralMoments/teacher -p 'test_*.py' -v"""
import copy
import tempfile
import unittest
from pathlib import Path
from native_cherchi_teacher import analytical_box_moments, seal, verify, save, load

class TeacherContractSmoke(unittest.TestCase):
    def setUp(self):
        self.q=[0.0]*10
        self.model="a"*64
        self.native="b"*64
        self.expected=[48.,48.,72.,96.,64.,144.,256.,144.,96.,72.]
        self.label=seal(model_sha256=self.model,native_module_sha256=self.native,
          geometry={"kind":"analytic_closed_box","bounds":[[0,2],[0,3],[0,4]]},
          density=2,frame={"name":"physical"},q=self.q,r_d=self.expected,j_d=None,
          r_f=[0]*10,topology_status="VALID",derivative_status="UNKNOWN",
          derivative_contract=None,stage_seconds={"analytic":0.0},peak_rss_bytes=None,
          exact_proof={"kind":"symbolic_box_integral","native_cherchi":False},split="excluded")
    def check(self,label):
        return verify(label,expected_q=self.q,expected_model_sha256=self.model,
                      expected_native_module_sha256=self.native)
    def test_reference(self):
        self.assertEqual(list(map(float,analytical_box_moments(((0,2),(0,3),(0,4)),2))),self.expected)
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"label.json"
            save(path,self.label)
            self.assertEqual(load(path,expected_q=self.q,expected_model_sha256=self.model,
                                  expected_native_module_sha256=self.native)["r_D"],self.expected)
    def test_tampering(self):
        for kind in ("missing","changed","swap"):
            label=copy.deepcopy(self.label)
            if kind=="missing": del label["payload"]["r_D"]
            elif kind=="changed": label["payload"]["r_D"][0]+=1
            else: label["payload"]["r_D"][7],label["payload"]["r_D"][8]=label["payload"]["r_D"][8],label["payload"]["r_D"][7]
            with self.assertRaises(ValueError): self.check(label)
    def test_wrong_identity(self):
        with self.assertRaises(ValueError):
            verify(self.label,expected_q=[1]+[0]*9,expected_model_sha256=self.model,
                   expected_native_module_sha256=self.native)
        with self.assertRaises(ValueError):
            verify(self.label,expected_q=self.q,expected_model_sha256="c"*64,
                   expected_native_module_sha256=self.native)
    def test_invalid_derivative(self):
        label=copy.deepcopy(self.label)
        label["payload"]["J_D"]=[[0]*10]*10
        with self.assertRaises(ValueError): self.check(label)

if __name__=="__main__":
    unittest.main()

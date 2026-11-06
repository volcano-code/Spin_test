import unittest
from m22_p4_arrangement_certificate import verify_certificate

class TestArrangementCertificate(unittest.TestCase):
    def fixture(self):
        return {"schema":"w2-exact-boolean-arrangement-certificate-v1",
          "operation":"DESIGN_MINUS_QUADRIC_SOURCE",
          "output_face_ids":["o0"],
          "parents":[{"parent_id":"d0","parent_area2":"2","cells":[
            {"cell_id":"c0","polygon":[["0","0"],["1","0"],["1","1"]],"membership":"INSIDE_DESIGN_OUTSIDE_QUADRIC","output_face_ids":["o0"]},
            {"cell_id":"c1","polygon":[["0","0"],["1","1"],["0","1"]],"membership":"INSIDE_DESIGN_INSIDE_QUADRIC","output_face_ids":[]}]}],
          "global_partition":{"selected_area2":"1","excluded_area2":"1","cells":2}}
    def test_valid_bookkeeping_passes_without_claiming_global_proof(self):
        r=verify_certificate(self.fixture(),["d0"],["o0"])
        self.assertEqual(r["status"],"EXACT_ARRANGEMENT_CERTIFICATE_INTERNAL_CONSISTENCY_PASS")
        self.assertFalse(r["global_boolean_set_equality_proven"])
    def test_missing_parent_fails(self):
        c=self.fixture(); c["parents"]=[]
        with self.assertRaisesRegex(ValueError,"PARENT_FACE_COVERAGE"): verify_certificate(c,["d0"],["o0"])
    def test_missing_output_face_fails(self):
        c=self.fixture(); c["output_face_ids"]=[]
        with self.assertRaisesRegex(ValueError,"OUTPUT_FACE_COVERAGE"): verify_certificate(c,["d0"],["o0"])
    def test_area_gap_fails(self):
        c=self.fixture(); c["parents"][0]["parent_area2"]="3"
        with self.assertRaisesRegex(ValueError,"AREA_NOT_EXACTLY"): verify_certificate(c,["d0"],["o0"])
    def test_selected_cell_without_output_fails(self):
        c=self.fixture(); c["parents"][0]["cells"][0]["output_face_ids"]=[]
        with self.assertRaisesRegex(ValueError,"OUTPUT_CELL_MISSING"): verify_certificate(c,["d0"],["o0"])
    def test_excluded_cell_with_output_fails(self):
        c=self.fixture(); c["parents"][0]["cells"][1]["output_face_ids"]=["o0"]
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_OUTPUT"): verify_certificate(c,["d0"],["o0"])
    def test_float_is_not_exact(self):
        c=self.fixture(); c["parents"][0]["cells"][0]["polygon"][0][0]=0.0
        with self.assertRaisesRegex(ValueError,"EXACT_RATIONAL"): verify_certificate(c,["d0"],["o0"])
    def test_ambiguous_cell_fails_closed(self):
        c=self.fixture(); c["parents"][0]["cells"][0]["membership"]="BOUNDARY_AMBIGUOUS"
        with self.assertRaisesRegex(ValueError,"UNRESOLVED"): verify_certificate(c,["d0"],["o0"])
    def test_duplicate_cell_id_fails(self):
        c=self.fixture(); c["parents"][0]["cells"][1]["cell_id"]="c0"
        with self.assertRaisesRegex(ValueError,"DUPLICATE"): verify_certificate(c,["d0"],["o0"])
    def test_wrong_global_area_fails(self):
        c=self.fixture(); c["global_partition"]["selected_area2"]="2"
        with self.assertRaisesRegex(ValueError,"SELECTED_AREA"): verify_certificate(c,["d0"],["o0"])

if __name__=="__main__": unittest.main()

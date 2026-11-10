import unittest
from m29_3_2_2_branch_fingerprint import fingerprint_components

def records():
    return [{"point_type":"EXPLICIT3D","operands":[
      {"status":"UNIQUE","source_vertices":[{"input_object":0,"input_vertex":i}]}]}
      for i in range(3)]

class BranchFingerprintTests(unittest.TestCase):
    def setUp(self):
        self.faces=[[0,1,2]]
        self.source_faces=[[4,5,6]]
        self.edges=[[1,2],[3,4]]
        self.records=records()

    def test_component_hashes_and_branch_hash_are_created(self):
        x=fingerprint_components("difference",self.faces,self.source_faces,
                                 "ELLIPSOID",0,self.edges,self.records)
        self.assertEqual(x["source_face_count"],1)
        self.assertEqual(x["output_feature_triangle_count"],1)
        self.assertEqual(x["construction_record_count"],3)
        self.assertEqual(x["point_type_counts"],{"EXPLICIT3D":3})
        self.assertEqual(len(x["recomputed_feature_branch_sha256"]),64)

    def test_cyclic_face_start_does_not_change_feature_triangle_hash(self):
        a=fingerprint_components("difference",[[0,1,2]],self.source_faces,
                                 "ELLIPSOID",0,self.edges,self.records)
        b=fingerprint_components("difference",[[1,2,0]],self.source_faces,
                                 "ELLIPSOID",0,self.edges,self.records)
        self.assertEqual(a["output_feature_triangles_sha256"],b["output_feature_triangles_sha256"])

    def test_reversed_feature_orientation_changes_feature_hash(self):
        a=fingerprint_components("difference",[[0,1,2]],self.source_faces,
                                 "ELLIPSOID",0,self.edges,self.records)
        b=fingerprint_components("difference",[[0,2,1]],self.source_faces,
                                 "ELLIPSOID",0,self.edges,self.records)
        self.assertNotEqual(a["output_feature_triangles_sha256"],b["output_feature_triangles_sha256"])

    def test_source_face_ordered_and_set_hashes_are_distinct(self):
        a=fingerprint_components("difference",[[0,1,2]],[[4,5,6],[7,8,9]],
                                 "ELLIPSOID",0,self.edges,self.records)
        b=fingerprint_components("difference",[[0,1,2]],[[7,8,9],[4,5,6]],
                                 "ELLIPSOID",0,self.edges,self.records)
        self.assertNotEqual(a["source_faces_ordered_sha256"],b["source_faces_ordered_sha256"])
        self.assertEqual(a["source_faces_oriented_set_sha256"],b["source_faces_oriented_set_sha256"])

    def test_source_edges_are_a_separate_component(self):
        a=fingerprint_components("difference",self.faces,self.source_faces,
                                 "ELLIPSOID",0,self.edges,self.records)
        b=fingerprint_components("difference",self.faces,self.source_faces,
                                 "ELLIPSOID",0,[[1,2],[3,5]],self.records)
        self.assertNotEqual(a["source_normal_edges_sha256"],b["source_normal_edges_sha256"])

    def test_ambiguous_correspondence_fails_closed(self):
        bad=records()
        bad[0]["operands"][0]["status"]="AMBIGUOUS"
        bad[0]["operands"][0]["source_vertices"].append({"input_object":0,"input_vertex":9})
        with self.assertRaisesRegex(ValueError,"CORRESPONDENCE_UNAVAILABLE"):
            fingerprint_components("difference",self.faces,self.source_faces,
                                    "ELLIPSOID",0,self.edges,bad)

    def test_invalid_or_degenerate_face_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"INVALID_TRIANGLE"):
            fingerprint_components("difference",[[0,0,1]],self.source_faces,
                                    "ELLIPSOID",0,self.edges,self.records)

if __name__=="__main__":unittest.main()

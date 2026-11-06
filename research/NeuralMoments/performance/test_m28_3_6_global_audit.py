import unittest
from m28_3_6_global_audit import topology_audit
TETRA_V=[(0,0,0),(1,0,0),(0,1,0),(0,0,1)]
TETRA_F=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
class GlobalTopologyTests(unittest.TestCase):
 def test_closed_tetrahedron_is_single_sphere(self):
  r,_=topology_audit((TETRA_V,TETRA_F));self.assertTrue(r["passes"])
  self.assertEqual(r["connected_components"],1);self.assertEqual(r["euler_characteristic"],2)
  self.assertEqual(r["geometric_edge_incidence_bad"],0);self.assertEqual(r["vertex_link_bad"],0)
 def test_open_mesh_detects_boundary_edges(self):
  r,_=topology_audit((TETRA_V,TETRA_F[:-1]));self.assertFalse(r["passes"])
  self.assertGreater(r["edge_incidence_bad"],0)
 def test_reversed_face_detects_orientation_conflict(self):
  f=TETRA_F.copy();f[0]=(f[0][0],f[0][2],f[0][1])
  r,_=topology_audit((TETRA_V,f));self.assertGreater(r["edge_orientation_bad"],0)
 def test_two_closed_components_are_counted(self):
  v=TETRA_V+[(x+3,y,z) for x,y,z in TETRA_V]
  f=TETRA_F+[tuple(i+4 for i in face) for face in TETRA_F]
  r,_=topology_audit((v,f));self.assertTrue(r["passes"])
  self.assertEqual(r["connected_components"],2);self.assertEqual(r["euler_characteristic"],4)
 def test_duplicate_geometric_vertex_is_detected(self):
  r,_=topology_audit((TETRA_V+[(0,0,0)],TETRA_F));self.assertFalse(r["passes"])
  self.assertEqual(r["duplicate_coordinate_vertices"],1);self.assertGreater(r["vertex_link_bad"],0)
if __name__=="__main__":unittest.main()

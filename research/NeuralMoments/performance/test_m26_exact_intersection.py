"""Synthetic positive and adversarial tests for W1 M26 standalone exact geometry audit."""
from pathlib import Path
import subprocess, tempfile, unittest
import m26_replay

BIN=Path(__file__).with_name('m26_exact_intersection')
V=[(0,0,0),(2,0,0),(0,2,0),(0,0,2)]
F=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]

def packet(verts,faces):
    return ('%d %d\n'%(len(verts),len(faces)) +
       ''.join(' '.join(map(str,v))+'\n' for v in verts)+
       ''.join(' '.join(map(str,f))+'\n' for f in faces)).encode()

def tetra(a=(0,0,0),s=1):
    return [[(a[k]+s*v[k]) for k in range(3)] for v in V], F

def join(meshes):
    vv=[];ff=[]
    for vertices,faces in meshes:
        ff.extend(tuple(i+len(vv) for i in face) for face in faces);vv.extend(vertices)
    return vv,ff

class TestM26(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not BIN.exists():raise RuntimeError('compile exact standalone C++ first')
    def check(self,mesh,status,exit_code):
        cp=subprocess.run([str(BIN),'--max-seconds','10'],input=packet(*mesh),capture_output=True,timeout=15)
        self.assertEqual(cp.returncode,exit_code,cp.stdout.decode()+cp.stderr.decode())
        self.assertIn(('reason=' if exit_code==4 else 'status=')+status,cp.stdout.decode())
    def test_relative_binary_path_executes_without_PATH_lookup(self):
        # Regress the caught bug: Path("./bin") must not lose executable prefix.
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"fake_m26"
            p.write_text("#!/bin/sh\nprintf 'status=STRICT_EMPTY_NO_POSITIVE_MASS\\n'\n")
            p.chmod(0o755)
            self.assertTrue(p.resolve(strict=True).is_file())
            cp=subprocess.run([str(p.resolve()),"--max-seconds","10"],input=packet([],[]),capture_output=True)
            self.assertEqual(cp.returncode,0)
            self.assertIn(b"status=STRICT_EMPTY_NO_POSITIVE_MASS",cp.stdout)
    def test_rational_stream_rejects_orphan_empty(self):
        with self.assertRaisesRegex(ValueError, "M26_MALFORMED_EMPTY"):
            m26_replay.rational_stream({"exact_vertices":[],"vertices":[[1,2,3]],"faces":[],"construction_records":[]})
    def test_rational_stream_rejects_index_outside_vertices(self):
        with self.assertRaisesRegex(ValueError, "M26_BAD_FACE"):
            m26_replay.rational_stream({"exact_vertices":[["0","0","0"]],"vertices":[[0,0,0]],"faces":[[0,1,2]],"construction_records":[{}]})
    def test_closed_single_tetra(self):
        self.check(tetra(),'EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE',0)
    def test_disjoint_tetra(self):
        self.check(join([tetra(),tetra((10,10,10))]),'EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE',0)
    def test_intersecting_two_closed_tetra(self):
        self.check(join([tetra(),tetra((1,0,0))]),'POST_BOOLEAN_SELF_INTERSECTION',2)
    def test_identical_disconnected_shells(self):
        self.check(join([tetra(),tetra()]),'POST_BOOLEAN_SELF_INTERSECTION',2)
    def test_zero_faces_but_orphan_vertex(self):
        self.check(([(0,0,0)],[]),'ORPHAN_VERTICES_IN_EMPTY_MATERIAL',4) # error text only
    def test_empty(self):
        self.check(([],[]),'STRICT_EMPTY_NO_POSITIVE_MASS',0)
    def test_triangle_dangling_open(self):
        self.check((V,[F[0]]),'NOT_CLOSED_ORIENTED_TWO_MANIFOLD_EDGE',4)
    def test_duplicate_face(self):
        self.check((V,F+[F[0]]),'NOT_CLOSED_ORIENTED_TWO_MANIFOLD_EDGE',4)
    def test_invalid_face_index(self):
        self.check((V,F[:-1]+[(1,2,10)]),'BAD_FACE_INDEX',4)
    def test_zero_area(self):
        self.check((V,F[:-1]+[(0,1,0)]),'REPEATED_VERTEX',4)
    def test_vertex_pinched_two_tetra(self):
        # A and B share only vertex 0, edge manifold but vertex fan disconnected.
        b=[(0,0,0),(-2,0,0),(0,-2,0),(0,0,-2)]
        faces=F+[tuple(0 if x==0 else x+3 for x in face) for face in F]
        self.check((V+b[1:],faces),'NONMANIFOLD_VERTEX_LINK',4)

if __name__=='__main__':unittest.main()

import subprocess, random, unittest
from pathlib import Path
import importlib.util

BIN=Path(__file__).with_name("m28_3_7_exact_pair_sat")
def run_pair(a,b):
    lines=["3 1 3 1 0"]
    lines += [" ".join(map(str,p)) for p in a]
    lines += ["0 1 2"]
    lines += [" ".join(map(str,p)) for p in b]
    lines += ["0 1 2"]
    cp=subprocess.run([str(BIN)],input="\n".join(lines)+"\n",text=True,capture_output=True,timeout=10)
    if cp.returncode: raise AssertionError(cp.stderr+cp.stdout)
    head={x.split()[0]:int(x.split()[1]) for x in cp.stdout.splitlines()[:3]}
    return head["positive_dim_cut_pairs"]
A=((0,0,0),(2,0,0),(0,2,0))
class ExactPairSATTests(unittest.TestCase):
 def test_non_coplanar_segment_intersection(self):
  B=((1,-1,-1),(1,2,1),(1,2,-1))
  self.assertEqual(run_pair(A,B),1)
 def test_coplanar_positive_area_overlap(self):
  B=((0,0,0),(1,0,0),(0,1,0))
  self.assertEqual(run_pair(A,B),1)
 def test_coplanar_shared_edge_contact(self):
  B=((2,0,0),(0,2,0),(2,2,0))
  self.assertEqual(run_pair(A,B),1)
 def test_coplanar_single_point_contact_is_not_a_cut_segment(self):
  B=((2,0,0),(3,0,0),(2,1,0))
  self.assertEqual(run_pair(A,B),0)
 def test_coplanar_disjoint_with_overlapping_aabb(self):
  B=((1,2,0),(2,1,0),(2,2,0))
  self.assertEqual(run_pair(A,B),0)
 def test_non_coplanar_point_contact_is_not_a_cut_segment(self):
  B=((0,0,0),(0,1,-1),(0,-1,-1))
  self.assertEqual(run_pair(A,B),0)
 def test_non_coplanar_disjoint_with_overlapping_aabb(self):
  B=((1,1,1),(2,1,-1),(1,2,-1))
  self.assertEqual(run_pair(A,B),0)
 def test_seeded_randomized_160_pairs_match_fraction_reference(self):
  spec=importlib.util.spec_from_file_location("m28_cut_reference",Path(__file__).with_name("m28_3_3_extract_exact_cuts.py"))
  ref=importlib.util.module_from_spec(spec);spec.loader.exec_module(ref)
  rng=random.Random(37291)
  av=[];bv=[];af=[];bf=[];expected=set()
  for i in range(160):
   off=i*100
   def triangle():
    while True:
     pts=[tuple(rng.randint(-5,5) for _ in range(3)) for _ in range(3)]
     if ref.cross(ref.sub(pts[1],pts[0]),ref.sub(pts[2],pts[0]))!=(0,0,0):return pts
   a=[(x+off,y,z) for x,y,z in triangle()]
   b=[(x+off,y,z) for x,y,z in triangle()]
   ai=len(av);bi=len(bv);av.extend(a);bv.extend(b)
   af.append((ai,ai+1,ai+2));bf.append((bi,bi+1,bi+2))
   aq=tuple(ref.qpoint(p) for p in a);bq=tuple(ref.qpoint(p) for p in b)
   if ref.plane_segment(aq,bq):expected.add((i,i))
  lines=[f"{len(av)} {len(af)} {len(bv)} {len(bf)} 0"]
  lines += [" ".join(map(str,p)) for p in av]+[" ".join(map(str,f)) for f in af]
  lines += [" ".join(map(str,p)) for p in bv]+[" ".join(map(str,f)) for f in bf]
  cp=subprocess.run([str(BIN)],input="\n".join(lines)+"\n",text=True,capture_output=True,timeout=20)
  self.assertEqual(cp.returncode,0,cp.stderr+cp.stdout)
  found={tuple(map(int,x.split())) for x in cp.stdout.splitlines()
         if len(x.split())==2 and all(t.lstrip("-").isdigit() for t in x.split())}
  self.assertEqual(found,expected)
 def test_degenerate_input_triangle_fails_closed(self):
  a=((0,0,0),(1,0,0),(2,0,0));b=((0,0,0),(0,1,0),(0,0,1))
  lines=["3 1 3 1 0"]+[" ".join(map(str,p)) for p in a]+["0 1 2"]
  lines += [" ".join(map(str,p)) for p in b]+["0 1 2"]
  cp=subprocess.run([str(BIN)],input="\n".join(lines)+"\n",text=True,capture_output=True,timeout=10)
  self.assertNotEqual(cp.returncode,0)
  self.assertIn("DEGENERATE_DESIGN_INPUT_FACE",cp.stderr)
if __name__=="__main__":unittest.main()

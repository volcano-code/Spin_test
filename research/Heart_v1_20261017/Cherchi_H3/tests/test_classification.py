from pathlib import Path
from importlib.util import module_from_spec,spec_from_file_location
import json,pytest
p=Path(__file__).resolve().parents[1]
s=spec_from_file_location('classifier',p/'source/classify_support_planes.py');m=module_from_spec(s);s.loader.exec_module(m)
h=Path('/mnt/data/Heart_Cherchi_H1')
a=h/'output_proxy_v1/cherchi-authoritative-exact.json';b=h/'evidence/proxy-cherchi-full-audit.json';c=h/'evidence/rational-output-audit.json'

def test_real_h1():
 r=m.classify(a,b,c)
 assert (r['faces'],r['exact_support_planes'],r['same_plane_pairs'],r['different_plane_pairs'],r['affected_faces'])==(1570,798,11,67,71)
 assert r['candidate_created'] is False and r['float_output_qualified'] is False

def test_unvalidated_exact_fails(tmp_path):
 v=json.loads(c.read_text());v['boundary_valid']=False;f=tmp_path/'exact.json';f.write_text(json.dumps(v))
 with pytest.raises(ValueError,match='EXACT_INPUT_NOT_VALIDATED'):m.classify(a,b,f)

def test_fabricated_pair_count_fails(tmp_path):
 v=json.loads(b.read_text());v['intersecting_pair_count']=77;f=tmp_path/'bin.json';f.write_text(json.dumps(v))
 with pytest.raises(ValueError,match='PAIR_COUNT_MISMATCH'):m.classify(a,f,c)

def test_plane_orientation_invariant():
 from fractions import Fraction as F
 a=(F(0),F(0),F(1));b=(F(1),F(0),F(1));c=(F(0),F(1),F(1))
 assert m.plane_key(a,b,c)==m.plane_key(c,b,a)

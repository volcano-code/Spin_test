import importlib.util
from pathlib import Path
from fractions import Fraction as F
import os

ROOT=Path(__file__).resolve().parents[1]
SP=ROOT/'source/classify_binary64_plane_sign_changes.py'
spec=importlib.util.spec_from_file_location('signs',SP)
# Add own source path for local import of certificate module.
import sys
sys.path.insert(0,str(ROOT/'source'))
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

def test_vertex_above_below_exact_plane():
    p=([F(0),F(0),F(1)],F(0))
    assert mod.side((F(0),F(0),F(2)),p)==1
    assert mod.side((F(0),F(0),F(0)),p)==0
    assert mod.side((F(0),F(0),F(-1)),p)==-1

def test_all_78_original_failed_float_pairs_show_side_changes():
    p=Path(os.environ.get('HEART_H1_ROOT', str((ROOT.parent/'Cherchi_H1') if (ROOT.parent/'Cherchi_H1').exists() else (ROOT.parent/'Heart_Cherchi_H1'))))
    r=mod.classify(p/'output_proxy_v1/cherchi-authoritative-exact.json',p/'evidence/proxy-cherchi-full-audit.json',p/'evidence/rational-output-audit.json')
    assert r['summary']['with_at_least_one_side_change']==78
    assert r['summary'].get('with_no_side_change',0)==0
    assert r['summary']['cross_exact_plane']==67
    assert r['summary']['same_exact_plane']==11

"""Test independent exact tetrahedron moments and strict tokens (not native solve)."""
from fractions import Fraction as F
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from verify_h8_exact_moments import independent_ten_raw_moments, exact

def tet():
    v=[['0/1','0b0/0b1','0/1'],['1/1','0/1','0/1'],['0/1','1/1','0/1'],['0/1','0/1','1/1']]
    f=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
    return v,f

def test_unit_tetra_exact_all_ten():
    result=independent_ten_raw_moments(*tet())
    assert result==(F(1,6),F(1,24),F(1,24),F(1,24),F(1,60),F(1,60),F(1,60),F(1,120),F(1,120),F(1,120))

def test_reversed_orientation_is_negative():
    v,f=tet()
    assert independent_ten_raw_moments(v,[list(reversed(face)) for face in f])==tuple(-x for x in independent_ten_raw_moments(v,f))

def test_binary_and_decimal_exact_parse():
    assert exact('-0b111/0b100')==F(-7,4)
    assert exact('11/4')==F(11,4)

@pytest.mark.parametrize('bad',['1','0b2/0b1','1/0','1/-1','0b101/0b','-0b1/-0b10','0b/0b1'])
def test_invalid_rational_rejected(bad):
    with pytest.raises(ValueError):exact(bad)

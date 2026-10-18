"""Offline H8b request contract checks. No native solver claims."""
import json,sys
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
from prepare_h8_solver_request import build,raw_moments

def test_synthetic_mass_tensor_ordering():
    import trimesh,numpy as np
    b=trimesh.creation.box(extents=(2,2,2))
    m=raw_moments(b)
    assert abs(m[0]-8)<1e-10
    assert np.max(np.abs(m[1:4]))<1e-10
    np.testing.assert_allclose(m[4:7],[8/3]*3,atol=1e-10)
    assert np.max(np.abs(m[7:]))<1e-10

def test_reject_existing_output(tmp_path):
    with pytest.raises(FileExistsError,match='FROZEN_REQUEST_EXISTS'):
        build(tmp_path,tmp_path)

def test_fail_closed_without_cad(tmp_path):
    with pytest.raises(FileNotFoundError):
        build(tmp_path,tmp_path/'result')

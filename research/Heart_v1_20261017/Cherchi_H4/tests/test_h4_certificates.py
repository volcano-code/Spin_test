from pathlib import Path
import importlib.util
import json
import os
import numpy as np
import pytest
from fractions import Fraction as F

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('h4',HERE/'source'/'certify_h4_retriangulation.py')
h4=importlib.util.module_from_spec(spec);spec.loader.exec_module(h4)

# Convex square with 4 exact vertices, no shape-specific tolerances.
R=[tuple(F(x) for x in p) for p in ((0,0,0),(1,0,0),(0,1,0),(1,-1,0))]
OLD=np.array([[0,1,2],[1,0,3]],dtype=np.int32)
NEW=np.array([[2,3,1],[3,2,0]],dtype=np.int32)

def test_exact_convex_flip_preserves_ten_moments_and_plane_chain():
    assert h4.certify_single_flip(OLD,NEW,(0,1),R)
    assert h4.global_oriented_plane_chain(OLD,R)==h4.global_oriented_plane_chain(NEW,R)

def test_strict_concavity_rejected():
    # x moves inside the original first triangle, invalid quad flip.
    concave=[*R[:3],tuple(F(x) for x in (.2,.2,0))]
    assert not h4.strict_convex_quad_from_diagonal(0,1,2,3,concave)

def test_non_coplanar_rejected():
    wrong=[*R[:3],tuple(F(x) for x in (1,-1,1))]
    with pytest.raises(ValueError,match='SUPPORT_PLANE_CHANGED'):
        h4.certify_single_flip(OLD,NEW,(0,1),wrong)

def test_breaking_boundary_or_orientation_rejected():
    broken=NEW.copy();broken[0]=broken[0][::-1]
    with pytest.raises(ValueError,match='LOCAL_ORIENTED_BOUNDARY_CHANGED|NOT_STRICTLY_CONVEX'):
        h4.certify_single_flip(OLD,broken,(0,1),R)

def test_frozen_H1_sha_and_false_export_refused(tmp_path):
    root=Path(os.environ.get('HEART_H1_ROOT', str((HERE.parent/'Cherchi_H1') if (HERE.parent/'Cherchi_H1').exists() else (HERE.parent/'Heart_Cherchi_H1'))))
    mat=root/'output_proxy_v1/cherchi-authoritative-exact.json'
    fl=root/'evidence/proxy-cherchi-full-audit.json'
    ex=root/'evidence/rational-output-audit.json'
    h4.load_frozen(mat,fl,ex)
    corrupted=tmp_path/'material.json'
    corrupted.write_bytes(mat.read_bytes()+b' ')
    with pytest.raises(ValueError,match='FROZEN_INPUT_SHA256_CHANGED'):
        h4.load_frozen(corrupted,fl,ex)

def test_final_certificate_has_not_claimed_author_CAD_or_newton():
    cert=json.loads((HERE/'final_certified/certification.json').read_text())
    assert cert['final_qualified'] is True
    assert cert['final_float_intersecting_pairs']==0
    assert cert['global_exact_oriented_plane_boundary_chain_equal'] is True
    assert cert['total_local_exact_flip_operations']==38
    assert cert['complete_author_heart'] is False
    assert cert['original_eval60_reproduced'] is False
    assert cert['complete_faster_newton_converged'] is False

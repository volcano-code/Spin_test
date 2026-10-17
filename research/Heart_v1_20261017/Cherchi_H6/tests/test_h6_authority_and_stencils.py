"""Pure-Python admission/finite-difference contract checks; not native proof."""
import json
import sys
from pathlib import Path
import numpy as np
import pytest

SRC=Path(__file__).resolve().parents[1]/'source'
sys.path.insert(0,str(SRC))
from heart_h6_authority import verify_frozen_eval60,verify_v4_proxy,EXPECTED
from heart_h6_cherchi_jacobian import five_point_weights,planned_samples,SCALES

from restore_v4_proxy import restore
ROOT=Path(__file__).resolve().parents[1]
REG=ROOT/'input/registered-eval60-coefficients.json'
V4=ROOT/'input/_unused_restored_v4.json'  # per-test fresh reconstruction below

@pytest.fixture(autouse=True)
def frozen_proxy(tmp_path, monkeypatch):
    restored=tmp_path/'v4.json'
    restore(restored)
    monkeypatch.setattr(sys.modules[__name__], 'V4', restored)


def test_authoritative_missing_is_a_hard_block(tmp_path):
    with pytest.raises(ValueError,match='MISSING_AUTHENTIC_HEART_EVAL60_FILES'):
        verify_frozen_eval60(tmp_path/'registration.json',tmp_path/'configuration.json',tmp_path/'events.jsonl')


def test_proxy_cannot_masquerade_as_original_config(tmp_path):
    c=tmp_path/'configuration.json';c.write_bytes(V4.read_bytes())
    e=tmp_path/'events.jsonl';e.write_text('{}\n')
    with pytest.raises(ValueError,match='AUTHENTIC_HEART_CONFIGURATION_SHA256_MISMATCH'):
        verify_frozen_eval60(REG,c,e)


def test_mutated_archived_proxy_rejected(tmp_path):
    altered=tmp_path/'v4.json';altered.write_bytes(V4.read_bytes()+b'\n')
    with pytest.raises(ValueError,match='ARCHIVED_PROXY_SHA256_MISMATCH'):
        verify_v4_proxy(altered,REG)


def test_archived_proxy_pin_valid_and_not_frozen_original():
    d,r=verify_v4_proxy(V4,REG)
    assert d['schema'].endswith('-v4')
    assert r['event']['evaluation_index']==60
    assert d['schema']!='cherchi-inprocess-formal-run-v1'
    assert EXPECTED['configuration'] not in (EXPECTED['v4_proxy'],EXPECTED['registration'])


def test_full_original_ten_direction_sample_schedule():
    q=np.arange(10,dtype=float)/20
    samples,layouts=planned_samples(q,list(range(10)))
    assert len(samples)==81
    assert len(layouts)==30
    assert all(len(l['indices'])==5 for l in layouts)
    assert all(len(set(l['indices']))==5 for l in layouts)
    assert len({tuple(x) for x in samples})==81


def test_three_column_partial_schedule():
    samples,layouts=planned_samples(np.arange(10)/20.,[0,4,8])
    assert len(samples)==25
    assert len(layouts)==9
    assert tuple(sorted(set(l['h'] for l in layouts))) == tuple(sorted(SCALES))


@pytest.mark.parametrize('H',SCALES)
def test_five_point_weights_exact_polynomial_derivatives(H):
    base=0.437
    x=np.array([base+shift for shift in (-H,-H/2,0,H/2,H)])
    w=five_point_weights(x-base)
    # Verify exact derivatives of degree 0..4 at 0 in scaled abscissae.
    h=x-base
    for degree in range(5):
        got=sum(w*(h/H)**degree)*H
        expected=1. if degree==1 else 0.
        assert abs(got-expected)<3e-10


def test_repeated_nodes_forbidden():
    with pytest.raises(ValueError,match='FIVE_DISTINCT_FD_POSITIONS_REQUIRED'):
        five_point_weights([0,0,0,0,0])


def test_invalid_directions_are_never_silently_mapped():
    with pytest.raises(IndexError):
        planned_samples(np.zeros(10),[10])

from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import struct
import hashlib
import pytest
import numpy as np

from .archived_raw_c_m13 import (
    RawCRejected, _binary64_vector, binary64_digest, positive_ray_exact,
    diagnose_native_c, audit_real_h8f_81, main, ARCHIVE_SHA256, N,
)

BASE=[1.]+[0.]*9


def test_strict_unit_and_nonunit_are_two_distinct_states():
    assert diagnose_native_c(BASE)['unit_norm_compatible_v1'] is True
    drift=[1.+3e-6]+[0.]*9
    x=diagnose_native_c(drift)
    assert x['unit_norm_compatible_v1'] is False
    assert x['raw_native_c']==drift
    assert x['signed_unit_ray_for_display_only']==BASE
    assert x['raw_binary64_sha256']!=binary64_digest(BASE)
    assert x['derivative_J_D'] is None
    assert x['training_admissible'] is False
    assert not x['native_Jc_reparameterized']


def test_raw_cross_term_convention_and_sign_are_preserved():
    c=[1.,0.,0.,0.,0.,0.,0.,3e-6,-4e-6,2e-6]
    r=diagnose_native_c(c)
    assert r['polynomial_q_from_raw_c'][7:]==[6e-6,-8e-6,4e-6]
    assert r['raw_native_c'][7]==3e-6
    assert not r['unit_norm_compatible_v1']
    assert r['raw_binary64_sha256']==hashlib.sha256(struct.pack('!10d',*c)).hexdigest()


def test_exact_positive_projective_equivalence_without_sign_flip():
    c=[1.,.5,-.25,0.,0.,0.,0.,0.,0.,0.]
    assert positive_ray_exact(c,[v*2 for v in c])
    assert positive_ray_exact([v*2 for v in c],c)
    assert not positive_ray_exact(c,[-v for v in c])
    assert not positive_ray_exact(c,[1.,.5,-.25,1e-15,0,0,0,0,0,0])
    assert not positive_ray_exact(c,[1.0000000000000002,.5,-.25,0,0,0,0,0,0,0])


def test_negative_zero_bit_preserved_in_raw_digest():
    a=[1.,0.]+[0.]*8
    b=[1.,-0.]+[0.]*8
    assert binary64_digest(a)!=binary64_digest(b)
    assert positive_ray_exact(a,b)  # geometric ray equivalence != bytes


@pytest.mark.parametrize('bad',[
    [0.]*10, [True]+[0.]*9, [1.]+[None]*9, [1.]+[float('nan')]*9,
    [1.]+[float('inf')]*9, [1.]+[0.]*8, [1.]+[0.]*9+['x'],
    [[1.]]+[0.]*9, dict(c=[1.]+[0.]*9),
])
def test_malformed_c_rejected(bad):
    with pytest.raises((RawCRejected,ValueError,TypeError)):
        diagnose_native_c(bad)


def test_source_vector_not_modified_by_diagnostics():
    arr=[.25,-.125]+[0.]*5+[2e-6,3e-6,-1e-6]
    original=copy.deepcopy(arr)
    a=diagnose_native_c(arr)
    b=diagnose_native_c(arr)
    assert arr==original
    assert a==b
    assert a['native_Jc_reparameterized'] is False


def _authentic():
    v=os.environ.get('W0_M13_REAL_ZIP')
    if not v:pytest.skip('REAL H8f artifact must be explicitly provided')
    return Path(v)


def test_authentic_full_81_archived_norm_compatibility():
    r=audit_real_h8f_81(_authentic())
    assert r['sample_count']==81
    assert r['v1_unit_c_compatible_count']==17
    assert r['v1_nonunit_c_count']==64
    assert len(r['rows'])==81
    assert all(len(x['native_binary64_sha256'])==64 for x in r['rows'])
    assert all(x['release_native_Jc'] is False for x in r['rows'])
    assert r['maximum_native_c_norm_deviation']==pytest.approx(2.282620930493806e-6)
    assert r['point60_native_c7']==3e-6
    assert r['point60_monomial_q7']==6e-6
    assert r['original_workflow_conclusion']=='failure'
    assert r['training_admissible'] is False
    assert r['J_D'] is None


def test_real_archive_compatibility_indices_are_frozen():
    r=audit_real_h8f_81(_authentic())
    assert r['v1_compatible_indices']==[0,21,22,23,24,61,62,63,64,69,70,71,72,77,78,79,80]
    assert r['rows'][60]['unit_norm_compatible_v1'] is False
    assert r['rows'][0]['unit_norm_compatible_v1'] is True


def test_cli_does_not_overwrite_existing_output(tmp_path):
    p=tmp_path/'prior.json';p.write_text('immutable')
    with pytest.raises(FileExistsError,match='DO_NOT_OVERWRITE'):
        main(['--archive',str(tmp_path/'not-here.zip'),'--output',str(p)])
    assert p.read_text()=='immutable'


def test_rejects_non_original_zip(tmp_path):
    p=tmp_path/'wrong.zip';p.write_bytes(b'not genuine')
    with pytest.raises(RawCRejected,match='H8F_ARCHIVE_SHA256_MISMATCH'):
        audit_real_h8f_81(p)

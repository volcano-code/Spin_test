"""M14 test-only fixtures are not native provenance or teacher release."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import struct

import numpy as np
import pytest

from .w2_ray_compatibility_m14 import (
    RawCRejected,
    M14Rejected, W2_ALL81_CROSSWALK_GIT_BLOB, W2_LEDGER_GIT_BLOB,
    exact_ray, canonical, git_blob, reconcile_m13, audit_archived_h8f,
    strict_json, _read_w2_official_bytes, main,
)

BASE=[1.0,0.5,-0.25,0.0,0.0,0.0,0.0,0.125,0.0625,0.0]


def test_positive_exact_scale_is_only_algebraic_ray_equivalence():
    one=exact_ray(BASE)
    doubled=exact_ray([2*v for v in BASE])
    assert one['exact_positive_ray_sha256']==doubled['exact_positive_ray_sha256']
    assert one['original_binary64_sha256']!=doubled['original_binary64_sha256']
    assert one['native_sample_reevaluated'] is False
    assert one['derivative_J_D'] is None
    assert doubled['training_admissible'] is False


def test_negative_scaling_not_the_same_signed_retained_halfspace():
    pos=exact_ray(BASE)
    neg=exact_ray([-v for v in BASE])
    assert pos['exact_positive_ray_sha256']!=neg['exact_positive_ray_sha256']


def test_negative_zero_changes_original_bytes_but_not_exact_algebraic_ray():
    a=BASE.copy();b=BASE.copy();b[3]=-0.0
    ra,rb=exact_ray(a),exact_ray(b)
    assert ra['original_binary64_sha256']!=rb['original_binary64_sha256']
    assert ra['original_c_canonical_sha256']!=rb['original_c_canonical_sha256']
    assert ra['exact_positive_ray_sha256']==rb['exact_positive_ray_sha256']
    assert struct.pack('!d',ra['original_binary64_c'][3])!=struct.pack('!d',rb['original_binary64_c'][3])


def test_nonunit_float_display_does_not_imply_same_exact_rational_ray():
    c=[0.3701293978732728,-0.15863761828595124,-0.0,-0.7608730119328398,
       0.293773367196206,0.293773367196206,0.293773367196206,0.0,0.0,0.0]
    r=exact_ray(c)
    assert r['w0_original_c_unit_compatible'] is False
    assert abs(np.linalg.norm(r['w0_display_unit_c_only'])-1.) <= 1e-12
    assert r['display_exact_rational_ray_matches_source'] is False
    assert r['w0_display_is_original_source_bytes'] is False
    assert r['archived_Jc_reparameterized'] is False


def test_monomial_B_only_last_three_doubled():
    c=[1.0,0,0,0,0,0,0,0.125,-0.25,0.75]
    x=exact_ray(c)
    assert x['monomial_q_from_original_c']==[1.,0.,0.,0.,0.,0.,0.,0.25,-0.5,1.5]


@pytest.mark.parametrize('bad',[
    [0.]*10,[True]+[0.]*9,[1.]+[float('nan')]*9,
    [1.]+[float('inf')]*9,[1.]+[None]*9,
    [1.]+[0.]*8,[1.]+[0.]*9+['wrong'],
    [[1.]]+[0.]*9,{'c':[1.]+[0.]*9},
])
def test_invalid_archived_c_rejected(bad):
    with pytest.raises((M14Rejected,OverflowError,ValueError,TypeError)):
        exact_ray(bad)


def test_canonical_tokens_and_git_blob_deterministic():
    x=exact_ray(BASE)
    token=x['signed_exact_ratio_tokens']
    assert x['exact_positive_ray_sha256']==hashlib.sha256(canonical(token)).hexdigest()
    assert token[-1]=='0/1'
    assert git_blob(canonical(token))==git_blob(canonical(token))
    assert W2_LEDGER_GIT_BLOB=='2d4cf4aae1368e22e760803d9bfe49479125ac4b'
    assert len(W2_ALL81_CROSSWALK_GIT_BLOB)==40


def test_strict_json_rejects_duplicate_and_nan_constants():
    for raw in (b'{"a":1,"a":2}',b'{"a":NaN}',b'{"a":Infinity}'):
        with pytest.raises(M14Rejected):strict_json(raw)


def test_untrusted_w2_full_ledger_is_not_mistaken_for_official(tmp_path):
    p=tmp_path/'fake.json';p.write_text('{"schema":"w2-m12-exact-positive-projective-ray-v1"}')
    with pytest.raises(M14Rejected,match='W2_M12_FULL_LEDGER'):
        _read_w2_official_bytes(p)


def test_missing_w2_ledger_rejected(tmp_path):
    with pytest.raises(M14Rejected,match='W2_LEDGER_MISSING'):
        _read_w2_official_bytes(tmp_path/'missing.json')


def test_cli_refuses_overwriting_existing_files(tmp_path):
    p=tmp_path/'immutable.json';p.write_text('original bytes')
    with pytest.raises(FileExistsError,match='M14_NEVER_OVERWRITE'):
        main(['--original-h8f-zip','/fake/missing.zip','--output',str(p)])
    assert p.read_text()=='original bytes'


@pytest.fixture(scope='module')
def authentic_replay():
    p=os.getenv('W0_M14_REAL_ZIP')
    if not p:pytest.skip('Genuine GitHub Actions H8f 81-point artifact not supplied')
    return audit_archived_h8f(p)


def test_real_81_W0_W2_exact_ray_and_material_digest_root(authentic_replay):
    s=authentic_replay
    assert s['w2_all81_crosswalk_git_blob_sha1']==W2_ALL81_CROSSWALK_GIT_BLOB
    assert s['sample_count']==81
    assert s['unit_c_samples']==17 and s['nonunit_c_samples']==64
    assert s['different_signed_positive_rays']==81
    assert s['original_binary64_unit_display_same_rational_ray']==17
    assert s['nonunit_binary64_display_same_rational_ray']==0
    assert s['w2_full_original_loaded_locally'] is False
    assert s['MomentContractV1_changed'] is False
    assert s['training_admissible'] is False and s['derivative_J_D'] is None


def test_real_point60_retains_actual_c7_no_fake_derivative(authentic_replay):
    r=authentic_replay
    assert r['point60_raw_c7']==3e-6
    assert r['point60_monomial_q7']==6e-6
    assert r['rows'][60]['v1_native_unit_compatible'] is False
    assert r['rows'][60]['J_D'] is None
    assert r['rows'][60]['original_material_gzip_sha256']==\
        '9e4e6e3f108096985227482bd7717be34989383194ded8ea941e54e4404a83f6'


def test_real_source_archive_swap_rejected(tmp_path):
    file=tmp_path/'imposter.zip';file.write_bytes(b'not native')
    with pytest.raises((RawCRejected, ValueError)):
        audit_archived_h8f(file)


def test_real_result_never_associates_display_c_with_archived_J(authentic_replay):
    r=authentic_replay
    assert len(r['rows'])==81
    assert all(item['native_c_replaced'] is False and item['J_D'] is None
               and item['training_admissible'] is False for item in r['rows'])
    assert r['raw_archived_r_J_never_assigned_to_display_vector'] is True


@pytest.fixture(scope='module')
def authentic_m13_rows():
    p=Path(__file__).with_name('archived_raw_c_81_ledger_m13.json')
    if p.is_file():
        return json.loads(p.read_text())
    from .archived_raw_c_m13 import audit_real_h8f_81
    archive=os.getenv('W0_M14_REAL_ZIP')
    if not archive:pytest.skip('Pinned genuine H8f ZIP required for M13 tampering test')
    return audit_real_h8f_81(archive)


def test_modified_m13_row_fails_root_even_when_source_sha_unmodified(authentic_m13_rows):
    s=copy.deepcopy(authentic_m13_rows)
    s['rows'][60]['raw_native_c'][7]=1.4e-6
    with pytest.raises(M14Rejected):reconcile_m13(s)


def test_modified_m13_material_sha_fails_independent_W2_crosswalk(authentic_m13_rows):
    s=copy.deepcopy(authentic_m13_rows)
    s['rows'][1]['source_material_gzip_sha256']='0'*64
    with pytest.raises(M14Rejected,match='W2_M12_ORIGINAL_81'):
        reconcile_m13(s)


def test_m14_diagnostic_schema_validated_on_genuine_source(authentic_replay):
    jsonschema=pytest.importorskip('jsonschema')
    path=Path(__file__).with_name('schema_archived_ray_m14.json')
    jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text()))
    jsonschema.validate(authentic_replay,json.loads(path.read_text()))


def test_schema_never_allows_training_release(authentic_replay):
    jsonschema=pytest.importorskip('jsonschema')
    schema=json.loads(Path(__file__).with_name('schema_archived_ray_m14.json').read_text())
    tampered=copy.deepcopy(authentic_replay)
    tampered['training_admissible']=True
    with pytest.raises(jsonschema.ValidationError):jsonschema.validate(tampered,schema)

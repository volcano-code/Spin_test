"""W0 M17 migration safety tests: synthetic v2 fixtures are NEVER native labels."""
from __future__ import annotations
import copy
from hashlib import sha256
import json
from pathlib import Path
import pytest

from .consumer_v2_preview_m17 import (
    W2_V2, RAW_ORDER, NATIVE_ORDER, TOTAL_POLICY, NATIVE_CONVENTION,
    MigrationRejected, archived_v2_preview, audit_legacy_runtime,
    canonical, digest, signed_ray_tokens, strict_json, main,
)


def example(raw=None):
    if raw is None:
        raw=[1.0]+[0.0]*6+[0.125, -0.25, 0.375]
    geom={'original_sha256':'c'*64,'design_D_sha256':'d'*64,'fixed_F_sha256':'f'*64}
    expected={'model':'1'*64,'module':'2'*64,'geometry':digest(geom)}
    p={
        'schema':W2_V2,'native_c':list(raw),'q':list(raw),
        'polynomial_q':[x*(2 if i>=7 else 1) for i,x in enumerate(raw)],
        'native_c_order':NATIVE_ORDER,'order':RAW_ORDER,
        'coefficient_convention':NATIVE_CONVENTION,'total_policy':TOTAL_POLICY,
        'model_sha256':expected['model'],'native_module_sha256':expected['module'],
        'geometry':geom,'density':1.0,'split':'excluded','J_D':None,
        'derivative_status':'UNKNOWN','derivative_contract':None,
        'topology_status':'OBSERVED_DISCRETE_MAP','exact_proof':{},
        'r_D':[float(x) for x in range(10)],'r_F':[0.0]*10,
    }
    identity={'q_sha256':digest([float(x) for x in raw]),
              'geometry_sha256':expected['geometry'],
              'model_sha256':expected['model'],
              'native_module_sha256':expected['module']}
    return {'payload':p,'identity':identity,'payload_sha256':digest(p)},expected


def check(document,expected, raw=None):
    if raw is None:raw=document['payload']['native_c']
    return archived_v2_preview(document,expected_native_c=raw,
        expected_model_sha256=expected['model'],
        expected_module_sha256=expected['module'],
        expected_geometry_sha256=expected['geometry'])


def resign(document):
    document['payload_sha256']=digest(document['payload'])


def test_synthetic_excluded_v2_is_valid_diagnostic_never_label():
    document, pins=example()
    r=check(document,pins)
    assert r['status']=='W2_V2_ARCHIVE_DIAGNOSTIC_ONLY_NO_RELEASE'
    assert r['cross_terms_doubled_correctly']
    assert r['training_admitted'] is False
    assert r['full_J_D_training_targets'] is None
    assert not r['saved_native_material_certified']


def test_original_nonunit_c_preserved_and_no_unit_relabel():
    c=[1.000004]+[0.0]*6+[3e-6,0.,-3e-6]
    document,pins=example(c)
    before=copy.deepcopy(document)
    r=check(document,pins)
    assert r['native_c_unit_compatible_w0'] is False
    assert r['original_c_never_normalized']
    assert document==before
    assert r['training_admitted'] is False


def test_exact_rational_positive_ray_not_negative_ray():
    a=[2.0,1.0,-0.5]+[0.0]*7
    b=[4.0,2.0,-1.0]+[0.0]*7
    c=[-v for v in a]
    assert signed_ray_tokens(a)==signed_ray_tokens(b)
    assert signed_ray_tokens(a)!=signed_ray_tokens(c)


def test_negative_zero_binary64_identity_kept():
    a=[1.0,-0.0]+[0.0]*8
    b=[1.0,0.0]+[0.0]*8
    x,px=example(a)
    y,py=example(b)
    assert check(x,px)['raw_binary64_sha256']!=check(y,py)['raw_binary64_sha256']
    assert check(x,px)['signed_exact_projective_ray_sha256']==check(y,py)['signed_exact_projective_ray_sha256']


@pytest.mark.parametrize('mutation,reason',[
    ('schema','V2_SCHEMA_REQUIRED'),
    ('train','V2_ARCHIVED_SAMPLE_MUST_REMAIN_EXCLUDED'),
    ('jacobian','V2_ARCHIVED_SAMPLE_MUST_REMAIN_EXCLUDED'),
    ('derivative','V2_ARCHIVED_SAMPLE_MUST_REMAIN_EXCLUDED'),
    ('legacy_q','V2_LEGACY_Q_IS_NOT_NATIVE_C'),
    ('monomial','V2_MONOMIAL_CROSS_TERM_B_MAPPING_INCORRECT'),
    ('raw_c','V2_ORIGINAL_C_BYTES_NOT_PRESERVED'),
    ('old_convention','V2_NATIVE_COEFFICIENT_OR_FIXED_POLICY_CHANGED'),
    ('fixed_double','V2_NATIVE_COEFFICIENT_OR_FIXED_POLICY_CHANGED'),
    ('model','V2_SOURCE_GEOMETRY_UNBOUND'),
    ('density','V2_DENSITY_INVALID'),
    ('failed_material_fake','V2_FAILED_MATERIAL_MOMENTS_FORGED'),
])
def test_resigned_modified_label_still_rejected(mutation,reason):
    document,pins=example()
    p=document['payload']
    independent_c=p['native_c'][:] # expected original before any self-resigning
    if mutation=='schema': p['schema']='w2-cherchi-teacher-v1-pre-w0'
    elif mutation=='train':p['split']='train'
    elif mutation=='jacobian':p['J_D']=[[0.]*10 for _ in range(10)]
    elif mutation=='derivative':p['derivative_status']='VALID'
    elif mutation=='legacy_q':p['q'][0]+=0.5
    elif mutation=='monomial':p['polynomial_q'][7]=p['native_c'][7]
    elif mutation=='raw_c':p['native_c'][0]+=1e-3
    elif mutation=='old_convention':p['coefficient_convention']='NATIVE_MATRIX_ENTRY_Q10'
    elif mutation=='fixed_double':p['total_policy']='r_total=r_F+r_F+r_D'
    elif mutation=='model':p['model_sha256']='a'*64
    elif mutation=='density':p['density']=-1.
    elif mutation=='failed_material_fake':p.update(topology_status='FAILED',derivative_status='INVALID')
    resign(document)
    with pytest.raises(MigrationRejected,match=reason):check(document,pins,independent_c)


def test_changed_untrusted_expected_c_rejected_even_with_resealed_identity():
    doc,pins=example()
    expected=doc['payload']['native_c'][:]
    expected[0]+=1e-8
    with pytest.raises(MigrationRejected,match='V2_ORIGINAL_C_BYTES_NOT_PRESERVED'):
        check(doc,pins,expected)


def test_changed_external_geometry_pin_denied_even_if_self_resealed():
    doc,pins=example()
    doc['payload']['geometry']['design_D_sha256']='b'*64
    doc['identity']['geometry_sha256']=digest(doc['payload']['geometry'])
    resign(doc)
    with pytest.raises(MigrationRejected,match='V2_EXTERNAL_PIN_MISSING_OR_DIFFERENT'):
        check(doc,pins)


def test_modified_payload_hash_denied():
    doc,pins=example()
    doc['payload_sha256']='0'*64
    with pytest.raises(MigrationRejected,match='V2_PAYLOAD_SHA_INCORRECT'):
        check(doc,pins)


@pytest.mark.parametrize('wrong',[0,True,float('nan'),float('inf'),None,'1.0',[]])
def test_invalid_native_coordinate_denied(wrong):
    doc,pins=example()
    doc['payload']['native_c'][0]=wrong
    if not (type(wrong) is float and not __import__('math').isfinite(wrong)):
        resign(doc)
    with pytest.raises(MigrationRejected):check(doc,pins)


def test_wrong_vector_length_denied():
    doc,pins=example()
    doc['payload']['native_c'].append(1)
    resign(doc)
    with pytest.raises(MigrationRejected):check(doc,pins)


def test_strict_external_duplicate_and_nonfinite_json():
    with pytest.raises(ValueError): strict_json(b'{"q":1,"q":2}')
    with pytest.raises(ValueError): strict_json(b'{"q":NaN}')


def test_real_frozen_w5_parser_and_strict_w0_disagree_only_on_structure():
    root=Path(__file__).resolve().parent
    if not (root/'frozen_external_m16/w5_contract_gate.py').is_file():
        pytest.skip('full W0 branch checkout required for true pinned W5 runtime')
    r=audit_legacy_runtime(root)
    assert r['actual_w5_legacy_parser_accepts_nonunit_w0_record'] is True
    assert r['actual_w0_strict_validator_accepts_same_record'] is False
    assert r['training_admitted'] is False


def test_real_snapshot_runtime_output_exclusive(tmp_path):
    existing=tmp_path/'prior.json';existing.write_text('original')
    with pytest.raises(FileExistsError,match='M17_OUTPUT_MUST_BE_NEW'):
        main(['--output',str(existing)])
    assert existing.read_text()=='original'

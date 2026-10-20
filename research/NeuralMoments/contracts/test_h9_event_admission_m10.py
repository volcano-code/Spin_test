"""W0 M10 pure fail-closed tests, and opt-in original GitHub H8f ZIP check."""
from __future__ import annotations

from fractions import Fraction
import json
import os

import numpy as np
import pytest

from .h9_event_admission_m10 import (
    W3_SURROGATE_BRACKET, audit, determinant, subtract, exact_line_witness,
    git_blob_sha1, midpoint_derivative_diagnostic, verify_w3_surrogate_certificate,
    main, ArchiveAuditError,
)


def fake_certificate():
    return dict(schema="heart-h9-native-endpoints-and-conditional-interior-event-v1",
       scope="REAL_NATIVE_BINARY64_FINITE_ENDPOINTS_AND_FIXED_NORMAL_ANALYTIC_SURROGATE_ONLY",
       real_native_endpoint_indices=[59,60],input_design_edge=[5517,5518],input_source_edge=[24,90],
       historical_run_conclusion="failure",historical_run_id=39123384402,
       request_sha256="1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c",
       actual_native_cherchi_newton_accepted=False,final_heart_obj_produced=False,
       final_independently_integrated_metrics_available=False,
       full_coefficient_interval=[1.5e-6,3e-6],
       artifact_sha256="99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9",
       conditional_analytic_interior_edge_crossing_certified=True,
       actual_in_between_native_boolean_samples_evaluated=0,
       native_production_continuity_or_topology_certified=False,
       newton_admitted=False,surrogate_root_exact_interval=[str(x) for x in W3_SURROGATE_BRACKET])


def certified_bytes(obj):
    return (json.dumps(obj,sort_keys=True,indent=2)+'\n').encode()


def test_exact_determinant_sign():
    def P(row):return tuple(Fraction(x) for x in row)
    a,b,c=P((1,0,0)),P((0,1,0)),P((0,0,1))
    assert determinant(a,b,c)==1
    assert determinant(b,a,c)==-1
    assert subtract(a,c)==P((1,0,-1))


def test_exact_lines_with_interior_nearest_points():
    # Two skew segments, projected nearest points are at s=t=1/2.
    source=[[0.,0.,1.],[1.,0.,1.]]
    design=[[.5,-1.,0.],[.5,1.,0.]]
    record=exact_line_witness(source,design)
    assert record['sign']!=0
    assert record['source_edge_parameter_exact']=='1/2'
    assert record['design_edge_parameter_exact']=='1/2'
    assert record['infinite_lines_min_squared_distance']==1.


@pytest.mark.parametrize('source,design',[
    ([[0.,0.,0.],[1.,0.,0.]],[[0.,1.,0.],[1.,1.,0.]]), # parallel
    ([[0.,0.,1.],[1.,0.,1.]],[[2.,-1.,0.],[2.,1.,0.]]), # projection outside source edge
    ([[0.,0.,0.],[1.,0.,0.]],[[.5,-1.,0.],[.5,1.,0.]]), # lines already cross
])
def test_noninterior_degenerate_or_intersecting_rejected(source,design):
    with pytest.raises(ArchiveAuditError): exact_line_witness(source,design)


@pytest.mark.parametrize('invalid', [True, '0', float('nan'),float('inf'),None])
def test_fraction_conversion_rejects_nonnumeric_and_nonfinite(invalid):
    with pytest.raises((ArchiveAuditError,TypeError,ValueError)):
        exact_line_witness([[invalid,0.,1.],[1.,0.,1.]],[[.5,-1.,0.],[.5,1.,0.]])


def test_trapezoid_diagnostic_numeric_only_even_when_exact():
    q0=np.zeros(10);q1=q0.copy();q1[7]=1.5e-6
    r0=np.zeros(10);r1=r0.copy();r1[0]=3e-6
    J0=np.zeros((10,10));J1=np.zeros((10,10))
    J0[0,7]=J1[0,7]=2.
    d=midpoint_derivative_diagnostic(q0,r0,J0,q1,r1,J1)
    assert d['max_scaled_secant_minus_endpoint_J_average']<1e-12
    assert d['no_continuity_or_differentiability_certified'] is True


@pytest.mark.parametrize('bad_q', ['other_column','nonpositive','zero'])
def test_secant_refuses_wrong_direction_or_step(bad_q):
    q0=np.zeros(10);q1=q0.copy()
    if bad_q=='other_column': q1[6]=1e-6;q1[7]=1e-6
    if bad_q=='nonpositive': q1[7]=-1e-6
    with pytest.raises(ArchiveAuditError):
        midpoint_derivative_diagnostic(q0,np.zeros(10),np.zeros((10,10)),q1,np.zeros(10),np.zeros((10,10)))


@pytest.mark.parametrize('key,bad',[
    ('actual_in_between_native_boolean_samples_evaluated',1),
    ('native_production_continuity_or_topology_certified',True),
    ('newton_admitted',True),
    ('historical_run_conclusion','success'),
    ('input_design_edge',[5517,5523]),
    ('surrogate_root_exact_interval',['0','1']),
    ('conditional_analytic_interior_edge_crossing_certified',False),
    ('actual_native_cherchi_newton_accepted',True),
    ('final_heart_obj_produced',True),
    ('request_sha256','0'*64),
])
def test_w3_surrogate_cannot_be_promoted(key,bad):
    x=fake_certificate();x[key]=bad;raw=certified_bytes(x)
    with pytest.raises(ArchiveAuditError,match='W3_SURROGATE'):
        verify_w3_surrogate_certificate(raw,expected_git_blob_sha1=git_blob_sha1(raw))


def test_w3_git_blob_pin_prevents_resealed_tampering():
    good=certified_bytes(fake_certificate());sha=git_blob_sha1(good)
    assert verify_w3_surrogate_certificate(good,expected_git_blob_sha1=sha)['real_native_root_certified'] is False
    bad=good.replace(b'"newton_admitted": false',b'"newton_admitted": true')
    with pytest.raises(ArchiveAuditError,match='GIT_BLOB_MISMATCH'):
        verify_w3_surrogate_certificate(bad,expected_git_blob_sha1=sha)


def test_fixed_W3_exact_fraction_bracket_not_unique_native_root_claim():
    a,b=W3_SURROGATE_BRACKET
    assert Fraction('0.0000015')<a<b<Fraction('0.000003')
    assert 0<float(b-a)<1e-16


def test_cli_never_replaces_completed_evidence(tmp_path):
    dest=tmp_path/'prior-report.json';dest.write_text('old')
    with pytest.raises(FileExistsError,match='DO_NOT_OVERWRITE'):
        main(['--archive',str(tmp_path/'missing.zip'),'--output',str(dest)])
    assert dest.read_text()=='old'


def test_unknown_artifact_fails_before_any_report(tmp_path):
    source=tmp_path/'missing.zip'
    with pytest.raises(ArchiveAuditError):audit(source)


def test_binary64_fraction_is_exact():
    a=0.1
    from .h9_event_admission_m10 import fraction_float
    assert fraction_float(a)==Fraction.from_float(a)
    assert fraction_float(a)!=Fraction('1/10')


@pytest.fixture(scope='module')
def real_audit():
    path=os.environ.get('W0_M10_REAL_ZIP')
    if not path:pytest.skip('original SHA-pinned H8f artifact ZIP not supplied')
    return audit(path)


def test_real_native_endpoint_sign_and_support_change(real_audit):
    d=real_audit
    assert [d['native_endpoint_exact_line_witness'][str(i)]['sign'] for i in (59,60)]==[1,-1]
    assert d['point60_structural_transition']['changed_vertex_indices']==[8043,8044,8045,8046,8047]
    assert d['point60_structural_transition']['removed_oriented_triangles']==17
    assert d['newton_admitted'] is False
    assert d['actual_continuous_native_event_location_certified'] is False


def test_real_native_secant_numerical_only(real_audit):
    d=real_audit['real_archived_secant_Jc_diagnostic']
    assert d['endpoint_Jc_column7_l2_difference']==pytest.approx(1.3018788333120816e-05,rel=1e-8)
    assert d['max_absolute_secant_minus_endpoint_J_average']==pytest.approx(6.11608878342898e-10,rel=1e-4)
    assert d['no_continuity_or_differentiability_certified'] is True


def test_real_native_exact_line_numbers_match_independent_W3(real_audit):
    d=real_audit['native_endpoint_exact_line_witness']
    assert d['59']['det_approx']==pytest.approx(1.5630561011148573e-08,rel=1e-12)
    assert d['60']['det_approx']==pytest.approx(-1.4405585247826644e-08,rel=1e-12)
    for k in ('59','60'):
        assert 0<d[k]['source_edge_parameter']<1
        assert 0<d[k]['design_edge_parameter']<1
        assert d[k]['infinite_lines_min_squared_distance']>0


def test_exact_w3_style_endpoint_numbers_compared_against_real_native(real_audit):
    # Locally resealed fake W3 metadata here tests the *cross-check mathematics*;
    # it is NOT an authentic W3 certificate (authentic SHA must be pinned separately).
    witness=real_audit['native_endpoint_exact_line_witness']
    x=fake_certificate();historical={}
    for key in ('59','60'):
        w=witness[key]
        historical[key]={}
        for name,value in [('signed_determinant',w['signed_determinant']),
                           ('source_parameter',w['source_edge_parameter_exact']),
                           ('design_parameter',w['design_edge_parameter_exact'])]:
            n,d=Fraction(value).as_integer_ratio()
            historical[key][name]={'numerator':str(n),'denominator':str(d)}
    x['exact_native_binary64_projected_line_witnesses']=historical
    raw=certified_bytes(x)
    proof=verify_w3_surrogate_certificate(raw,
        expected_git_blob_sha1=git_blob_sha1(raw),native_witness=witness)
    assert proof['native_endpoint_exact_values_crosschecked'] is True
    assert proof['real_native_root_certified'] is False
    # A forged exact numerator must fail even if a new self-hash is computed.
    x['exact_native_binary64_projected_line_witnesses']['59']['source_parameter']['numerator']='1'
    tampered=certified_bytes(x)
    with pytest.raises(ArchiveAuditError,match='W3_ENDPOINT_WITNESS_INCOMPATIBLE'):
        verify_w3_surrogate_certificate(tampered,
            expected_git_blob_sha1=git_blob_sha1(tampered),native_witness=witness)

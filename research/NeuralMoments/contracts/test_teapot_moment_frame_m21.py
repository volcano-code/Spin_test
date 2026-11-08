from fractions import Fraction
import numpy as np
import pytest

from .moment_coordinates import pushforward_raw
from .teapot_moment_frame_m21 import (
    NATIVE_FRAME, SI_FRAME, MomentFrameRejected, build_p20_moment_frame_contract,
    normalization_for_frame, validate_normalization, transform_raw10_native_to_si,
    transform_jacobian_native_to_si, audit_tangent_neighborhood_in_frame)
from .test_tangent_neighborhood import _data


def frac(n,d=1): return {"numerator":str(n),"denominator":str(d)}

def fixture():
    request={"units":{"fixed_density":1,"design_density":1,
        "length_m_per_reference_binary64":0.025,
        "length_m_per_reference_exact":"3602879701896397/144115188075855872",
        "physical_density_kg_m3":1200,"physical_parameters_approved":False},
        "target":{"mode":"SPINNING_TOP","axis":[0,0,1],"origin":[0,0,0],"support_points":[]},
        "admission":{"W0_owner_admitted":False,"original_author_CAD":False}}
    frame={"actual_frame":{"coefficient_frame":NATIVE_FRAME,
        "actual_target_axes_exact":[[frac(1),frac(0),frac(0)],[frac(0),frac(1),frac(0)],[frac(0),frac(0),frac(1)]],
        "length_original_per_normalized_exact":frac(723841050109123,281474976710656),
        "density_original_per_normalized_exact":frac(1),
        "native_length_scale_is_bbox_L_not_SI_0025":True,
        "represented_tip_reference_exact":[
            frac(-66571086769065,20282409603651670423947251286016),frac(0),
            frac(102728673147415,2535301200456458802993406410752)],
        "represented_tip_is_exact_requested_tip":False,"frame_identity_sha256":"a"*64},
        "physical_replay":{"density_reference":1.0}}
    return request,frame

def raw_points(points):
    r=np.zeros(10)
    for w,(x,y,z) in points:r+=w*np.array([1,x,y,z,x*x,y*y,z*z,y*z,x*z,x*y])
    return r

def test_native_and_si_normalizations_are_distinct():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr)
    assert normalization_for_frame(c,NATIVE_FRAME)==(1.,1.)
    assert normalization_for_frame(c,SI_FRAME)==pytest.approx((.06429,1200.))
    assert c.original_per_native_length==pytest.approx(2.5716)

def test_native_to_si_raw10_equals_two_stage_reference_conversion():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr)
    r=raw_points([(1.2,(.1,.2,.3)),(.7,(-.2,.4,.1)),(.9,(.3,-.1,.2))])
    direct=transform_raw10_native_to_si(r,c)
    tip=np.array(c.target_to_si_translation)/c.scale_m_per_reference
    ref=pushforward_raw(r,np.eye(3)*c.original_per_native_length,tip,density_ratio=1.)
    staged=pushforward_raw(ref,np.eye(3)*c.scale_m_per_reference,np.zeros(3),density_ratio=1200.)
    np.testing.assert_allclose(direct,staged,rtol=2e-13,atol=1e-24)

def test_si_transform_retains_tiny_represented_tip_residual():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr)
    assert c.target_to_si_translation[0]!=0 and c.target_to_si_translation[2]!=0
    assert max(abs(x) for x in c.target_to_si_translation)<1e-17

def test_jacobian_is_transformed_columnwise():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr)
    J=np.arange(100,dtype=float).reshape(10,10)/17
    got=transform_jacobian_native_to_si(J,c)
    want=np.column_stack([transform_raw10_native_to_si(J[:,i],c) for i in range(10)])
    np.testing.assert_array_equal(got,want)
    assert got.shape==(10,10) and not np.array_equal(got,J)

def test_native_frame_rejects_si_normalization():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr)
    with pytest.raises(MomentFrameRejected,match="MOMENT_FRAME_NORMALIZATION_MISMATCH"):
        validate_normalization(c,NATIVE_FRAME,.06429,1200.)

def test_si_frame_rejects_native_normalization():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr)
    with pytest.raises(MomentFrameRejected,match="MOMENT_FRAME_NORMALIZATION_MISMATCH"):
        validate_normalization(c,SI_FRAME,1.,1.)

@pytest.mark.parametrize("mutator,error",[
    (lambda q,fr:q["units"].update(physical_parameters_approved=True),"P20_PHYSICAL_ADMISSION_STATE_CHANGED"),
    (lambda q,fr:fr["actual_frame"].update(length_original_per_normalized_exact=frac(3)),"P20_FRAME_LENGTH_CHANGED"),
    (lambda q,fr:fr["actual_frame"].update(density_original_per_normalized_exact=frac(2)),"P20_FRAME_DENSITY_SCALE_CHANGED"),
    (lambda q,fr:q["units"].update(length_m_per_reference_exact="1/10"),"P20_REFERENCE_TO_SI_SCALE_CHANGED"),
    (lambda q,fr:q["units"].update(design_density=2),"P20_REQUEST_DENSITIES_NOT_ONE"),
    (lambda q,fr:fr["actual_frame"]["actual_target_axes_exact"][0].__setitem__(1,frac(1)),"P20_FRAME_AXES_NOT_EXACT_IDENTITY"),
])
def test_bad_source_frame_rejected(mutator,error):
    q,fr=fixture();mutator(q,fr)
    with pytest.raises(MomentFrameRejected,match=error):build_p20_moment_frame_contract(q,fr)

def test_unknown_frame_rejected():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr)
    with pytest.raises(MomentFrameRejected,match="UNKNOWN_MOMENT_COORDINATE_FRAME"):
        normalization_for_frame(c,"P19_REFERENCE_ALREADY_Z_UP")

def test_si_roundtrip_all_ten_moments():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr)
    r=raw_points([(1.,(.1,.2,.3)),(2.,(-.3,.2,.1))])
    si=transform_raw10_native_to_si(r,c)
    A=np.asarray(c.target_to_si_linear);t=np.asarray(c.target_to_si_translation);Ai=np.linalg.inv(A)
    back=pushforward_raw(si,Ai,-Ai@t,density_ratio=1./c.native_to_si_density_ratio)
    np.testing.assert_allclose(back,r,rtol=2e-12,atol=2e-12)

def test_native_and_si_tangent_paths_both_preserve_diagnostic_only_status():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr);d=_data()
    args=dict(native_c=d["native_c"],Jc=d["Jc"],tangent_basis=d["tangent_basis"],
        probes=d["probes"],base_feature_branch_sha256=d["base_feature_branch_sha256"],
        step_radians=d["step_radians"],max_normalized_jacobian_error=2e-7)
    native=audit_tangent_neighborhood_in_frame(contract=c,moment_coordinate_frame=NATIVE_FRAME,
        normalization_L=1.,normalization_R=1.,**args)
    si=audit_tangent_neighborhood_in_frame(contract=c,moment_coordinate_frame=SI_FRAME,
        normalization_L=c.si_length_ref,normalization_R=c.si_density_ref,**args)
    for result in (native,si):
        assert result["status"]=="NUMERIC_TANGENT_CHECK_PASS_SMOOTHNESS_NOT_PROVED"
        assert result["smooth_neighborhood_certified"] is False
        assert result["training_admissible"] is False
    assert native["coordinate_transform_applied"] is False
    assert si["coordinate_transform_applied"] is True

def test_si_path_keeps_branch_change_veto():
    q,fr=fixture();c=build_p20_moment_frame_contract(q,fr);d=_data()
    d["probes"][0]["plus_h"]["feature_branch_sha256"]="f"*64
    result=audit_tangent_neighborhood_in_frame(contract=c,moment_coordinate_frame=SI_FRAME,
        normalization_L=c.si_length_ref,normalization_R=c.si_density_ref,
        native_c=d["native_c"],Jc=d["Jc"],tangent_basis=d["tangent_basis"],
        probes=d["probes"],base_feature_branch_sha256=d["base_feature_branch_sha256"],
        step_radians=d["step_radians"],max_normalized_jacobian_error=2e-7)
    assert result["status"]=="OBSERVED_BRANCH_CHANGE_DERIVATIVE_EXCLUDED"
    assert result["smooth_neighborhood_certified"] is False

def test_frame_report_never_grants_admission():
    q,fr=fixture();r=build_p20_moment_frame_contract(q,fr).report()
    assert r["physical_parameters_approved"] is False
    assert r["P30B_diagnostic_authorized"] is False
    assert r["Newton_accepted"] is False and r["training_admissible"] is False

"""W0 structural gate negative/adversarial regression, no Cherchi invocation."""
from __future__ import annotations
import copy
import json
import math
import numpy as np
import pytest
from .analytic_references import box, sphere_cap, sphere_cap_ambient_jacobian
from .moment_coordinates import normalize_new_c, jacobian_native_to_monomial
from .validate_contract_v1 import (ContractError, canonical_digest, load_record,
                                   strict_json, validate_record)


def valid_record():
    c = normalize_new_c((-.2,0,0,1,0,0,0,0,0,0)).tolist()
    return {
        "schema":"MomentContractV1", "source_sha":"0bcc187b3005478baa586a6d6f450e73811ca342",
        "geometry":{
            "original_sha256":"1"*64, "fixed_F_sha256":"2"*64,
            "design_D_sha256":"3"*64,
            "frame":{"kind":"INPUT_NORMALIZED_TARGET_V1",
                     "length_original_per_normalized":2.5,
                     "density_original_per_normalized":3.0,
                     "origin_original":[.1,.2,-.4]},
            "density":1.4,"fixed_r_computed_once":True},
        "coefficients":{"c":c, "order":"CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY",
                        "positive_scale_equivalent":True,
                        "negative_sign_equivalent":False,
                        "retained_side":"BETA_POSITIVE",
                        "cross_mapping":"q=Bc;Bdiag=1,1,1,1,1,1,1,2,2,2"},
        "moments":{"order":"M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY",
                   "fixed_r":[0.]*10,"variable_r":None,"total_r":None,
                   "status":"ANALYTIC_ONLY","independent_geometry_evidence":False},
        "jacobian":{"type":"UNAVAILABLE","derivative_defined":False,
                    "values":None,"native_tangent_basis":None,
                    "hessian_rule":"ONLY_IF_SMOOTH_AMBIENT_CHECK_Jc_B_INVERSE"},
        "error":{"truth_kind":"ANALYTIC_P0","length_ref":2.5,"density_ref":3.,
                 "metric":"ABSOLUTE_PER_COMPONENT_DIVIDED_BY_RHO_L3_L4_L5",
                 "threshold_policy":"PER_CASE_PREDECLARED_NO_UNIVERSAL_1_PERCENT",
                 "certifies_proof":False}}


def with_moments():
    x=valid_record()
    rf=box((-.3,.2,.1),(.2,.3,.1),density=1.).tolist()
    rd=sphere_cap(1.,.2,density=1.).tolist()
    x["moments"]["fixed_r"]=rf
    x["moments"]["variable_r"]=rd
    x["moments"]["total_r"]=(np.asarray(rf)+rd).tolist()
    return x


def valid_ambient():
    x=with_moments()
    j=sphere_cap_ambient_jacobian(1.,.2,vertical_coefficient=x["coefficients"]["c"][3])
    x["jacobian"].update(type="AMBIENT_10X10",derivative_defined=True,
                          values=j.tolist())
    return x


def valid_tangent():
    x=with_moments()
    basis=np.zeros((10,2));basis[1,0]=1;basis[4,1]=1
    x["jacobian"].update(type="TANGENT_10XK",derivative_defined=True,
                          values=(np.ones((10,2))*.1).tolist(),
                          native_tangent_basis=basis.tolist())
    return x


@pytest.mark.parametrize("f", [valid_record, with_moments, valid_ambient, valid_tangent])
def test_accept_structural_but_never_as_trusted_teacher(f):
    result=validate_record(f())
    assert result["structural_valid"] is True
    assert result["native_material_certified_by_this_gate"] is False
    assert result["safe_for_training_without_external_native_proof"] is False
    assert len(result["canonical_sha256"])==64


def test_raw_Jc_can_be_nonsymmetric_without_rejection():
    x=valid_ambient()
    J=np.asarray(x["jacobian"]["values"])
    assert np.max(np.abs(J-J.T))>.1
    H=jacobian_native_to_monomial(J)
    np.testing.assert_allclose(H,H.T,atol=1e-14)
    assert validate_record(x)["jacobian_mode"]=="AMBIENT_10X10"


@pytest.mark.parametrize("mutate", [
    lambda x:x.__setitem__("schema","MomentContractV2"),
    lambda x:x.__setitem__("evil_extra",True),
    lambda x:x["geometry"].__setitem__("fixed_F_sha256","a"*63),
    lambda x:x["geometry"].__setitem__("fixed_r_computed_once",False),
    lambda x:x["geometry"]["frame"].__setitem__("length_original_per_normalized",0),
    lambda x:x["geometry"]["frame"].__setitem__("origin_original",[True,0,0]),
    lambda x:x["coefficients"].__setitem__("cross_mapping","B=identity"),
    lambda x:x["coefficients"].__setitem__("negative_sign_equivalent",True),
    lambda x:x["coefficients"].__setitem__("retained_side","UNSPECIFIED"),
    lambda x:x["coefficients"].__setitem__("c",[0.]*10),
    lambda x:x["coefficients"].__setitem__("c",[1.]*10),
    lambda x:x["error"].__setitem__("threshold_policy","UNIFORM_1_PERCENT"),
    lambda x:x["error"].__setitem__("certifies_proof",True),
    lambda x:x["moments"].__setitem__("status","NATIVE_VERIFIED"),
    lambda x:x["jacobian"].__setitem__("derivative_defined",True),
    lambda x:x["jacobian"].__setitem__("values",[[0.]*10]*10),
])
def test_reject_basic_invalid_contract_fields(mutate):
    x=valid_record();mutate(x)
    with pytest.raises((ContractError,ValueError)):validate_record(x)


def test_tampered_fixed_added_twice_fails():
    x=with_moments()
    x["moments"]["total_r"][0]+=x["moments"]["fixed_r"][0]
    with pytest.raises(ContractError,match="fixed F"):validate_record(x)


def test_missing_variable_total_mismatch_fails():
    x=with_moments();x["moments"]["total_r"]=None
    with pytest.raises(ContractError,match="both present"):validate_record(x)


def test_failed_material_forbids_moment_and_J():
    x=valid_ambient();x["moments"]["status"]="FAILED_MATERIAL"
    with pytest.raises(ContractError):validate_record(x)


def test_native_flag_does_not_count_as_independent_proof():
    x=with_moments();x["moments"]["status"]="NATIVE_VERIFIED"
    x["moments"]["independent_geometry_evidence"]=True
    x["error"]["truth_kind"]="INDEPENDENT_NATIVE_SEAL"
    result=validate_record(x)
    assert result["native_material_certified_by_this_gate"] is False
    x["error"]["truth_kind"]="ANALYTIC_P0"
    with pytest.raises(ContractError):validate_record(x)


@pytest.mark.parametrize("bad", [
    lambda x:x["jacobian"].__setitem__("native_tangent_basis",[[0.,0.]]*10),
    lambda x:x["jacobian"].__setitem__("values",[[1.]]*10),
    lambda x:x["jacobian"]["native_tangent_basis"][1].__setitem__(0,0.5),
    lambda x:x["jacobian"]["native_tangent_basis"][3].__setitem__(0,0.5),
    lambda x:x["jacobian"]["values"][0].__setitem__(0,float("nan")),
])
def test_invalid_tangent_or_nonfinite_derivatives_rejected(bad):
    x=valid_tangent();bad(x)
    with pytest.raises((ContractError,ValueError)):validate_record(x)


def test_ambient_missing_basis_status_rejected():
    x=valid_ambient();x["jacobian"]["native_tangent_basis"]=[[0.]]*10
    with pytest.raises(ContractError):validate_record(x)


def test_duplicate_json_keys_rejected():
    with pytest.raises(ContractError,match="duplicate JSON"):
        strict_json('{"schema":"MomentContractV1","schema":"MomentContractV1"}')
    with pytest.raises(ContractError,match="invalid JSON"):
        strict_json('{"x": NaN}')


def test_canonical_sha_detects_changes():
    x=valid_ambient();sha=canonical_digest(x)
    copy_x=copy.deepcopy(x)
    assert sha==canonical_digest(copy_x)
    copy_x["coefficients"]["retained_side"]="BETA_NEGATIVE"
    assert sha!=canonical_digest(copy_x)


def test_positive_scale_equivalence_not_negative():
    x=valid_record();c=np.asarray(x["coefficients"]["c"])
    # c has the same canonical normalization on every positive ray,
    # whereas negating it exchanges the positive material halfspace.
    np.testing.assert_allclose(c,normalize_new_c(17*c),atol=1e-14)
    assert not np.allclose(c,normalize_new_c(-c))

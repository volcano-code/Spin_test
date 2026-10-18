"""W0-only W2 pre-release interface smoke. No W2 code is modified or run."""
import copy
import numpy as np
import pytest
from .moment_coordinates import normalize_new_c
from .validate_contract_v1 import ContractError, canonical_digest
from .w2_teacher_gate import inspect_w2_label

H1="a"*64; H2="b"*64
GEOMETRY={"original_sha256":"1"*64,"fixed_F_sha256":"2"*64,
          "design_D_sha256":"3"*64}
G_SHA=canonical_digest(GEOMETRY)
C=normalize_new_c([-.2,0,0,1,0,0,0,0,0,0]).tolist()


def label(*,derivative="VALID"):
    p={"schema":"w2-cherchi-teacher-v1-pre-w0",
       "order":["m","x","y","z","xx","yy","zz","yz","xz","xy"],
       "coefficient_convention":"NATIVE_MATRIX_ENTRY_Q10",
       "model_sha256":H1,"native_module_sha256":H2,
       "geometry":GEOMETRY,"density":1.,"frame":{"kind":"test"},
       "q":C,"r_D":[1.]+[0.]*9,"r_F":[2.]+[0.]*9,
       "J_D":(np.ones((10,10))*.1).tolist() if derivative=="VALID" else None,
       "topology_status":"VALID" if derivative=="VALID" else "OBSERVED_DISCRETE_MAP",
       "derivative_status":derivative,
       "derivative_contract":{"verified_neighborhood":True} if derivative=="VALID" else None,
       "stage_seconds":{"fake_for_unit_test":0.001},"peak_rss_bytes":1024,
       "exact_proof":{"native_cherchi":True},"split":"train","failure_reason":None,
       "total_policy":"r_total=r_F+r_D;J_total=J_D;fixed_never_in_r_D"}
    return {"payload":p,"payload_sha256":canonical_digest(p),
            "identity":{"q_sha256":canonical_digest(C),
                        "geometry_sha256":G_SHA,"model_sha256":H1,
                        "native_module_sha256":H2}}


def inspect(rec):
    return inspect_w2_label(rec,expected_native_c=C,
        expected_geometry_sha256=G_SHA,expected_model_sha256=H1,
        expected_native_module_sha256=H2)


def reseal(rec):
    rec["payload_sha256"]=canonical_digest(rec["payload"])
    rec["identity"]["q_sha256"]=canonical_digest(rec["payload"]["q"])


def test_w2_ambient_is_prelabeled_only():
    r=inspect(label())
    assert r["identity_bindings_checked"] is True
    assert r["w2_q_semantics"] == "NATIVE_C_NOT_W0_MONOMIAL_Q"
    assert not r["training_admissible"] and not r["native_material_certified"]
    assert r["r_total_candidate"][0] == 3.
    assert r["Jq_monomial_candidate"][0][-1] == .05


def test_w2_unknown_derivative_provisional_only():
    r=inspect(label(derivative="UNKNOWN"))
    assert r["Jc_native_candidate"] is None and not r["training_admissible"]


@pytest.mark.parametrize("mutate",[
    lambda r:r["payload"]["q"].__setitem__(9,0.5),
    lambda r:r["payload"].__setitem__("order",list(reversed(r["payload"]["order"]))),
    lambda r:r["payload"].__setitem__("coefficient_convention","MONOMIAL_DOUBLED"),
    lambda r:r["payload"].__setitem__("native_module_sha256","f"*64),
    lambda r:r["payload"].__setitem__("topology_status","FAILED"),
    lambda r:r["payload"].__setitem__("derivative_contract",{}),
    lambda r:r["payload"]["J_D"].__setitem__(0,[1.]),
    lambda r:r["payload"].__setitem__("r_F",[1.]),
    lambda r:r["payload"].__setitem__("stage_seconds",{"bad":float("nan")}),
])
def test_w2_tamper_and_invalid_labeled_truth_rejected(mutate):
    r=copy.deepcopy(label());mutate(r)
    with pytest.raises((ContractError, ValueError,TypeError)):
        inspect(r)


def test_w2_malicious_reseal_still_fails_expected_c():
    r=copy.deepcopy(label());r["payload"]["q"][9]=.1;reseal(r)
    with pytest.raises(ContractError, match="native q"):
        inspect(r)


def test_w2_malicious_reseal_native_module_still_fails_expected_sha():
    r=copy.deepcopy(label());r["payload"]["native_module_sha256"]="f"*64
    r["identity"]["native_module_sha256"]="f"*64;reseal(r)
    with pytest.raises(ContractError,match="module"):
        inspect(r)

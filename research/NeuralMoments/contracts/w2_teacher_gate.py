"""Read-only W2 pre-W0 adapter admission: verifies identity, never grants truth.

W2 currently calls its native matrix-entry *c* vector 'q'. This is NOT the
monomial coefficient q=Bc defined by W0. Cross-terms must never be doubled on
both sides. W2 native/r information is a *candidate* until separately checked
by a sealed, genuinely executed Cherchi/material and Newton audit.
"""
from __future__ import annotations

import math

import numpy as np

from .moment_coordinates import jacobian_native_to_monomial, checked
from .validate_contract_v1 import (
    ContractError, canonical_digest, fields, require, sha, values)

W2_SCHEMA = "w2-cherchi-teacher-v1-pre-w0"
W2_ORDER = ["m", "x", "y", "z", "xx", "yy", "zz", "yz", "xz", "xy"]
W2_NATIVE_CONVENTION = "NATIVE_MATRIX_ENTRY_Q10"
W2_TOTAL_POLICY = "r_total=r_F+r_D;J_total=J_D;fixed_never_in_r_D"


def inspect_w2_label(record, *, expected_native_c, expected_geometry_sha256,
                     expected_model_sha256, expected_native_module_sha256):
    """Return untrusted candidate numbers only after independent identity bind.

    Never equate proof.native_cherchi=True with successful native execution.
    No training admission decision can be made by this gate alone.
    """
    fields(record, ("payload", "payload_sha256", "identity"), "W2 envelope")
    payload = record["payload"]
    fields(payload, ("schema", "order", "coefficient_convention", "model_sha256",
                     "native_module_sha256", "geometry", "density", "frame", "q",
                     "r_D", "J_D", "r_F", "topology_status", "derivative_status",
                     "derivative_contract", "stage_seconds", "peak_rss_bytes",
                     "exact_proof", "split", "failure_reason", "total_policy"),
           "W2 payload")
    require(payload["schema"] == W2_SCHEMA and payload["order"] == W2_ORDER,
            "W2 schema/order mismatch")
    require(payload["coefficient_convention"] == W2_NATIVE_CONVENTION,
            "W2 q must be explicitly native symmetric-entry c, NOT W0 monomial q")
    require(payload["total_policy"] == W2_TOTAL_POLICY,
            "W2 fixed/variable counting mismatch")
    sha(record["payload_sha256"], "W2 payload SHA")
    require(canonical_digest(payload) == record["payload_sha256"],
            "W2 payload digest mismatch")
    fields(record["identity"], ("q_sha256", "geometry_sha256",
                                "model_sha256", "native_module_sha256"), "W2 identity")
    model, module = payload["model_sha256"], payload["native_module_sha256"]
    for name, value, expected in (
        ("model",model,expected_model_sha256),
        ("native module",module,expected_native_module_sha256)):
        sha(value, name);sha(expected, f"expected {name}")
        require(value == expected and record["identity"][
            "model_sha256" if name == "model" else "native_module_sha256"] == value,
            f"W2 {name} identity drift")
    sha(expected_geometry_sha256, "expected geometry")
    require(canonical_digest(payload["geometry"]) == expected_geometry_sha256 ==
            record["identity"]["geometry_sha256"],
            "W2 geometry does not bind frozen original/F/D")
    c = values(payload["q"], (10,), "W2 native q, mapped to W0 c")
    expected = checked(expected_native_c, (10,), "externally expected native c")
    require(np.array_equal(c, expected) and
            canonical_digest(payload["q"]) == record["identity"]["q_sha256"],
            "W2 native q not identical to frozen W0 c")
    require(abs(float(np.linalg.norm(c)) - 1.) <= 1e-12,
            "W2 saved native c must be unit norm")
    require(type(payload["density"]) in (int,float) and
            math.isfinite(payload["density"]) and payload["density"] > 0,
            "W2 density invalid")
    require(payload["topology_status"] in
            ("VALID", "OBSERVED_DISCRETE_MAP", "FAILED"), "W2 topology status invalid")
    derivative = payload["derivative_status"]
    require(derivative in ("VALID", "UNKNOWN", "INVALID"),
            "W2 derivative status invalid")
    r_f = None if payload["r_F"] is None else values(payload["r_F"], (10,), "W2 fixed")
    r_d = None if payload["r_D"] is None else values(payload["r_D"], (10,), "W2 design")
    if derivative == "VALID":
        require(r_f is not None and r_d is not None and
                payload["topology_status"] == "VALID" and
                type(payload["derivative_contract"]) is dict and
                payload["derivative_contract"].get("verified_neighborhood") is True,
                "W2 derivative has no explicitly certified smooth neighborhood")
        Jc = values(payload["J_D"], (10,10), "W2 native Jc")
        Jq = jacobian_native_to_monomial(Jc)
    else:
        require(payload["J_D"] is None, "invalid/unknown W2 derivative cannot publish J")
        Jc = Jq = None
    if payload["topology_status"] == "FAILED":
        require(r_f is None and r_d is None and derivative == "INVALID",
                "failed W2 candidate cannot publish moments")
    require(type(payload["stage_seconds"]) is dict and all(
        type(t) is str and type(sec) in (int,float) and math.isfinite(sec) and sec >= 0
        for t, sec in payload["stage_seconds"].items()), "W2 timings invalid")
    rss = payload["peak_rss_bytes"]
    require(rss is None or (type(rss) is int and rss >= 0), "W2 RSS invalid")
    require(payload["split"] in ("train", "val", "test", "excluded"),
            "W2 split invalid")
    require(type(payload["exact_proof"]) is dict,
            "missing W2 claimed proof metadata")
    return {
        "source_schema": W2_SCHEMA,
        "w2_q_semantics": "NATIVE_C_NOT_W0_MONOMIAL_Q",
        "c_native": c.tolist(),
        "r_fixed_candidate": None if r_f is None else r_f.tolist(),
        "r_design_candidate": None if r_d is None else r_d.tolist(),
        "r_total_candidate": None if r_f is None or r_d is None else (r_f+r_d).tolist(),
        "Jc_native_candidate": None if Jc is None else Jc.tolist(),
        "Jq_monomial_candidate": None if Jq is None else Jq.tolist(),
        "derivative_status": derivative,
        "record_sha256": canonical_digest(record),
        "identity_bindings_checked": True,
        "native_material_certified": False,
        "training_admissible": False,
        "reason": "W2 pre-W0 identity is structurally bound, but independent native geometry/material and derivative rechecks are not supplied",
    }

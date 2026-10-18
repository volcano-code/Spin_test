"""Fail-closed structural/semantic gate for MomentContractV1 records.

Structural acceptance does NOT authenticate Cherchi geometry, provenance,
physics, or training labels. The caller must independently check these.
Runtime requires only Python stdlib + NumPy, like other W0 modules.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

from .moment_coordinates import B, SOURCE_SHA, checked

SCHEMA = "MomentContractV1"
C_ORDER = "CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY"
R_ORDER = "M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY"
CROSS_MAPPING = "q=Bc;Bdiag=1,1,1,1,1,1,1,2,2,2"
HESSIAN_RULE = "ONLY_IF_SMOOTH_AMBIENT_CHECK_Jc_B_INVERSE"
METRIC = "ABSOLUTE_PER_COMPONENT_DIVIDED_BY_RHO_L3_L4_L5"
THRESHOLD = "PER_CASE_PREDECLARED_NO_UNIVERSAL_1_PERCENT"
SHA = re.compile(r"[0-9a-f]{64}\Z")


class ContractError(ValueError):
    """The record is inconsistent with the published W0 math contract."""


def require(value, msg):
    if not value:
        raise ContractError(msg)


def fields(obj, names, where):
    require(type(obj) is dict and set(obj) == set(names), f"{where}: field mismatch")


def finite(value, name, *, positive=False):
    require(type(value) in (int, float), f"{name}: number (not bool) required")
    try:
        x = float(value)
    except (OverflowError, ValueError) as exc:
        raise ContractError(f"{name}: cannot represent number") from exc
    require(math.isfinite(x) and (not positive or x > 0), f"{name}: nonfinite/nonpositive")
    return x


def sha(value, name):
    require(type(value) is str and SHA.fullmatch(value) is not None,
            f"{name}: 64 lowercase hex SHA256 required")


def values(data, shape, name):
    require(type(data) is list, f"{name}: list required")
    try:
        array = checked(data, shape, name)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ContractError(f"{name}: nonfinite/wrong shape") from exc
    return array


def strict_json(text):
    """Disallow duplicate keys and JavaScript NaN/Infinity spellings."""
    def pairs(rows):
        out = {}
        for key, value in rows:
            require(key not in out, f"duplicate JSON key: {key}")
            out[key] = value
        return out
    def bad_constant(token):
        raise ContractError(f"invalid JSON numeric token: {token}")
    return json.loads(text, object_pairs_hook=pairs, parse_constant=bad_constant)


def load_record(path):
    return strict_json(Path(path).read_text(encoding="utf-8"))


def canonical_digest(record):
    data = json.dumps(record, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(data.encode("ascii")).hexdigest()


def validate_record(record):
    """Validate serialized numerical fields without upgrading physical trust.

    All J rows are moment-output coordinates, columns
    are native symmetric-entry *c*. A tangent J must also carry its basis.
    No generic symmetry test is permitted for Jc.
    """
    fields(record, ("schema", "source_sha", "geometry", "coefficients",
                    "moments", "jacobian", "error"), "contract")
    require(record["schema"] == SCHEMA and record["source_sha"] == SOURCE_SHA,
            "schema/source identity mismatch")

    g = record["geometry"]
    fields(g, ("original_sha256", "fixed_F_sha256", "design_D_sha256",
               "frame", "density", "fixed_r_computed_once"), "geometry")
    for key in ("original_sha256", "fixed_F_sha256", "design_D_sha256"):
        sha(g[key], key)
    require(type(g["fixed_r_computed_once"]) is bool and g["fixed_r_computed_once"],
            "fixed r must be prepared once")
    finite(g["density"], "geometry density", positive=True)
    frame = g["frame"]
    fields(frame, ("kind", "length_original_per_normalized",
                   "density_original_per_normalized", "origin_original"), "frame")
    require(frame["kind"] == "INPUT_NORMALIZED_TARGET_V1", "unknown frame")
    finite(frame["length_original_per_normalized"], "frame length", positive=True)
    finite(frame["density_original_per_normalized"], "frame density", positive=True)
    values(frame["origin_original"], (3,), "frame origin")

    cs = record["coefficients"]
    fields(cs, ("c", "order", "positive_scale_equivalent",
                "negative_sign_equivalent", "retained_side", "cross_mapping"),
           "coefficients")
    require(cs["order"] == C_ORDER and cs["cross_mapping"] == CROSS_MAPPING,
            "native cross-term/order mismatch")
    require(cs["positive_scale_equivalent"] is True and
            cs["negative_sign_equivalent"] is False, "projective sign mismatch")
    require(cs["retained_side"] in ("BETA_POSITIVE", "BETA_NEGATIVE"),
            "retained side missing/unknown")
    c = values(cs["c"], (10,), "native c")
    require(abs(float(np.linalg.norm(c)) - 1.) <= 1e-12,
            "saved native c must be unit norm (no silent renormalization)")

    m = record["moments"]
    fields(m, ("order", "fixed_r", "variable_r", "total_r", "status",
               "independent_geometry_evidence"), "moments")
    require(m["order"] == R_ORDER, "wrong raw r order")
    rf = values(m["fixed_r"], (10,), "fixed r")
    status = m["status"]
    require(status in ("ANALYTIC_ONLY", "NATIVE_VERIFIED", "FAILED_MATERIAL", "NOT_RUN"),
            "unknown moment status")
    require(type(m["independent_geometry_evidence"]) is bool,
            "geometry evidence flag must be bool")
    require(m["independent_geometry_evidence"] is (status == "NATIVE_VERIFIED"),
            "native status/evidence flag mismatch")
    has_variable = m["variable_r"] is not None
    require(has_variable == (m["total_r"] is not None),
            "variable and total r must be both present or both null")
    require(status not in ("FAILED_MATERIAL", "NOT_RUN") or not has_variable,
            "failed/not-run cannot publish r")

    error = record["error"]
    fields(error, ("truth_kind", "length_ref", "density_ref", "metric",
                   "threshold_policy", "certifies_proof"), "error")
    require(error["truth_kind"] in ("ANALYTIC_P0", "INDEPENDENT_NATIVE_SEAL", "NONE"),
            "truth kind unknown")
    length = finite(error["length_ref"], "length_ref", positive=True)
    density = finite(error["density_ref"], "density_ref", positive=True)
    require(error["metric"] == METRIC and error["threshold_policy"] == THRESHOLD and
            error["certifies_proof"] is False, "error policy must not claim proof")
    require(status != "NATIVE_VERIFIED" or
            error["truth_kind"] == "INDEPENDENT_NATIVE_SEAL", "native label needs native seal")
    require(status != "ANALYTIC_ONLY" or
            error["truth_kind"] in ("ANALYTIC_P0", "NONE"),
            "analytic record cannot claim native proof")
    if has_variable:
        rd = values(m["variable_r"], (10,), "variable r")
        total = values(m["total_r"], (10,), "total r")
        expected = rf + rd
        # 32 ULP-equivalent on normalized input scale: an algebraic accounting
        # check, NOT a universal prediction/physical accuracy threshold.
        scales = density * np.array([length**3]*1+[length**4]*3+[length**5]*6)
        require(np.isfinite(scales).all() and np.all(scales > 0),
                "nonrepresentable moment error reference")
        discrepancy = np.max(np.abs(total - expected)/scales)
        budget = 32*np.finfo(float).eps*(1.+np.max(np.abs(expected)/scales))
        require(math.isfinite(float(discrepancy)) and discrepancy <= budget,
                "fixed F counted twice or total r inconsistent")

    j = record["jacobian"]
    fields(j, ("type", "derivative_defined", "values", "native_tangent_basis",
               "hessian_rule"), "jacobian")
    require(j["hessian_rule"] == HESSIAN_RULE and
            type(j["derivative_defined"]) is bool, "Jacobian rule/status mismatch")
    mode = j["type"]
    require(mode in ("AMBIENT_10X10", "TANGENT_10XK", "UNAVAILABLE"),
            "unsupported Jacobian coordinate mode")
    if mode == "UNAVAILABLE":
        require(not j["derivative_defined"] and j["values"] is None and
                j["native_tangent_basis"] is None, "unavailable J must not contain values")
    elif mode == "AMBIENT_10X10":
        require(j["derivative_defined"] and j["native_tangent_basis"] is None,
                "ambient J/basis flag mismatch")
        values(j["values"], (10,10), "ambient Jc")
    else:
        require(j["derivative_defined"] and
                type(j["values"]) is list and len(j["values"]) == 10 and
                all(type(row) is list for row in j["values"]),
                "tangent Jacobian rows required")
        k = len(j["values"][0])
        require(1 <= k <= 9, "tangent dimension must be 1..9")
        Jt = values(j["values"], (10,k), "tangent J")
        basis = values(j["native_tangent_basis"], (10,k), "native tangent basis")
        require(np.max(np.abs(basis.T@basis-np.eye(k))) < 1e-10 and
                np.max(np.abs(basis.T@c)) < 1e-10, "tangent basis not orthonormal/orthogonal to c")
    require(status not in ("FAILED_MATERIAL", "NOT_RUN") or mode == "UNAVAILABLE",
            "failed/not-run cannot publish derivatives")
    require(not (mode != "UNAVAILABLE" and not has_variable),
            "derivatives require published variable moments")
    # A structurally valid label is never an independent material certificate.
    return {"structural_valid": True,
            "native_material_certified_by_this_gate": False,
            "safe_for_training_without_external_native_proof": False,
            "jacobian_mode": mode,
            "canonical_sha256": canonical_digest(record)}

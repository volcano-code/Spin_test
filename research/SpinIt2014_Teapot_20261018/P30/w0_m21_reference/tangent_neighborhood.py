"""M5: numerical Jc tangent-neighborhood probe with explicit branch-change veto.

A topology/feature fingerprint is a *point-sample observation*, never a
continuous-neighborhood proof. Even a tiny residual does not certify Cherchi
geometry or a training-ready derivative. This module does NOT call native code.
"""
from __future__ import annotations

import math
import re
import numpy as np

def checked(data, shape, label):
    # Reject booleans before NumPy silently promotes mixed arrays to float.
    def bad(v):
        if isinstance(v, (bool, np.bool_)):
            return True
        if isinstance(v, (list, tuple)):
            return any(bad(x) for x in v)
        return isinstance(v, np.ndarray) and (v.dtype.kind == "b" or
            (v.dtype.kind == "O" and any(bad(x) for x in v.flat)))
    if bad(data):
        raise ValueError(f"{label}: boolean coordinate")
    a = np.asarray(data)
    if a.shape != shape or a.dtype.kind not in "iuf":
        raise ValueError(f"{label}: wrong shape/type")
    a = np.asarray(a, dtype=np.float64)
    if not np.isfinite(a).all():
        raise ValueError(f"{label}: nonfinite")
    return a.copy()


SHA = re.compile(r"[0-9a-f]{64}\Z")


class NeighborhoodRejected(ValueError):
    """Malformed or mismatched numerical differential evidence."""


def _need(condition, reason):
    if not condition:
        raise NeighborhoodRejected(reason)


def _v(data, shape, label):
    try:
        return checked(data, shape, label)
    except (ValueError, TypeError, OverflowError) as exc:
        raise NeighborhoodRejected("INVALID_" + label) from exc


def _sample(data, expected_c):
    _need(type(data) is dict and set(data)=={"c_native", "r_design", "feature_branch_sha256"},
          "MISSING_OR_EXTRA_PROBE_FIELDS")
    c = _v(data["c_native"], (10,), "probe_native_c")
    _need(np.max(np.abs(c - expected_c)) <= 5e-13,
          "PROBE_GEODESIC_COEFFICIENTS_MISMATCH")
    r = _v(data["r_design"], (10,), "probe_r_design")
    token = data["feature_branch_sha256"]
    _need(type(token) is str and SHA.fullmatch(token) is not None,
          "INVALID_FEATURE_BRANCH_HASH")
    return r,token


def audit_tangent_neighborhood(*, native_c, Jc, tangent_basis, probes,
                              base_feature_branch_sha256, step_radians, length_ref, density_ref,
                              max_normalized_jacobian_error):
    """Check ±h and ±h/2 per direction in native coefficient coordinates.

    Extrapolated finite difference R=(4 D(h/2)-D(h))/3 is compared to Jc@v.
    All tolerances are *predeclared per-case* and dimensional-normalized; there
    is no invented universal 1% gate. A branch mismatch reports UNSTABLE and
    cannot be interpreted as a smooth Jacobian. Pure data and arithmetic only.
    """
    _need(type(base_feature_branch_sha256) is str and
          SHA.fullmatch(base_feature_branch_sha256) is not None,
          "MISSING_VALID_BASE_FEATURE_BRANCH_SHA")
    c = _v(native_c, (10,), "native_c")
    _need(abs(np.linalg.norm(c)-1) <= 1e-12, "BASE_COEFFICIENTS_NOT_UNIT")
    J = _v(Jc, (10,10), "native_Jc")
    basis = np.asarray(tangent_basis)
    _need(basis.ndim==2 and basis.shape[0]==10 and 1<=basis.shape[1]<=9,
          "INVALID_TANGENT_SHAPE")
    basis=_v(basis, (10,basis.shape[1]), "tangent_basis")
    _need(np.max(np.abs(basis.T@basis-np.eye(basis.shape[1])))<1e-10 and
          np.max(np.abs(c@basis))<1e-10, "NON_ORTHONORMAL_OR_NONTANGENT_BASIS")
    for name,v in (("step_radians",step_radians),("length_ref",length_ref),
                   ("density_ref",density_ref),("error_budget",max_normalized_jacobian_error)):
        _need(type(v) in (int,float) and math.isfinite(v) and v>0,
              "INVALID_"+name.upper())
    _need(step_radians<=.1, "FINITE_DIFFERENCE_STEP_TOO_LARGE")
    _need(type(probes) in (list,tuple) and len(probes)==basis.shape[1],
          "PROBE_DIRECTION_COUNT_MISMATCH")
    scale=np.array([length_ref**3]+[length_ref**4]*3+[length_ref**5]*6,dtype=float)*density_ref
    _need(np.isfinite(scale).all() and np.all(scale>0), "INVALID_MOMENT_NORMALIZATION")
    values=[]
    for i,v in enumerate(basis.T):
        packet=probes[i]
        _need(type(packet) is dict and set(packet)=={"plus_h", "minus_h", "plus_half", "minus_half"},
              "MISSING_OR_EXTRA_TANGENT_SAMPLES")
        observed={}
        for name,angle in (("plus_h",step_radians),("minus_h",-step_radians),
                           ("plus_half",step_radians/2),("minus_half",-step_radians/2)):
            expected=math.cos(angle)*c+math.sin(angle)*v
            observed[name]=_sample(packet[name],expected)
        identities={s[1] for s in observed.values()}
        dh=(observed["plus_h"][0]-observed["minus_h"][0])/(2*step_radians)
        dhalf=(observed["plus_half"][0]-observed["minus_half"][0])/step_radians
        extrap=(4*dhalf-dh)/3
        expected=J@v
        abs_errors=np.abs(extrap-expected)/scale
        worst=float(np.max(abs_errors))
        branch_stable=(identities=={base_feature_branch_sha256})
        passed=branch_stable and worst<=max_normalized_jacobian_error
        values.append({
            "index":i,
            "sampled_branch_stable":branch_stable,
            "feature_branch_sha256":next(iter(identities)) if branch_stable else None,
            "native_Jc_directional_max_normalized_error":worst,
            "central_difference_step_halving_change":float(np.max(np.abs(dh-dhalf)/scale)),
            "predeclared_error_budget":float(max_normalized_jacobian_error),
            "numerically_consistent":passed,
        })
    if any(not row["sampled_branch_stable"] for row in values):
        status="OBSERVED_BRANCH_CHANGE_DERIVATIVE_EXCLUDED"
    elif not all(row["numerically_consistent"] for row in values):
        status="NUMERICAL_JACOBIAN_DISAGREEMENT_DERIVATIVE_EXCLUDED"
    else:
        status="NUMERIC_TANGENT_CHECK_PASS_SMOOTHNESS_NOT_PROVED"
    return {
        "schema":"W0_M5_TANGENT_NUMERIC_DIAGNOSTIC_V1",
        "base_feature_branch_sha256":base_feature_branch_sha256,
        "status":status,
        "directions":values,
        "all_probes_sampled":True,
        "smooth_neighborhood_certified":False,
        "complete_material_geometry_certified":False,
        "training_admissible":False,
    }

"""W5 M2 read-only interoperability gate for W0 and W2 *published* formats.

W0/W2 live on OTHER unmerged branches. This module neither writes to those
branches nor treats W2's self-asserted ``native_cherchi`` field as independent
proof. A separately approved, byte-pinned W2 record is required before even
returning a candidate native label. No conversion to W5's nine-dimensional
*synthetic* geometry representation is provided: these are different tasks.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

W0_SOURCE_SHA = "0bcc187b3005478baa586a6d6f450e73811ca342"
W0_PUBLISHED_HEAD = "fbf3f3a3916d504baef0557ed9979525ec63b7b6"
W2_PUBLISHED_HEAD = "2319d7a816bf03bd641886a8070b5c809b9456be"
W0_SCHEMA = "MomentContractV1"
W2_SCHEMA = "w2-cherchi-teacher-v1-pre-w0"
NATIVE_C_ORDER = "CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY"
RAW_R_ORDER = "M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY"
W2_ORDER = ["m", "x", "y", "z", "xx", "yy", "zz", "yz", "xz", "xy"]
B_DIAG = np.asarray([1.0] * 7 + [2.0] * 3)
_SHA = re.compile(r"^[a-f0-9]{64}$")
_VALID_SPLITS = {"train", "val", "test"}


class AdmissionError(ValueError):
    """Reject untrusted, incompatible, incomplete or invalid teacher records."""


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise AdmissionError(reason)


def _sha(value: Any) -> bool:
    return isinstance(value, str) and _SHA.fullmatch(value) is not None


def _vector(value: Any, n: int, name: str) -> np.ndarray:
    _require(isinstance(value, (list, tuple, np.ndarray)), f"{name}: not a vector")
    _require(len(value) == n, f"{name}: expected {n} entries")
    _require(all(isinstance(x, (int, float, np.integer, np.floating)) and not isinstance(x, (bool, np.bool_)) for x in value), f"{name}: not real-valued")
    arr = np.asarray(value, dtype=np.float64)
    _require(arr.shape == (n,) and bool(np.isfinite(arr).all()), f"{name}: nonfinite or incorrect shape")
    return arr.copy()


def _matrix(value: Any, rows: int, cols: int, name: str) -> np.ndarray:
    _require(isinstance(value, (list, tuple, np.ndarray)) and len(value) == rows, f"{name}: incorrect rows")
    return np.stack([_vector(row, cols, name) for row in value])


def _positive(value: Any, name: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{name}: not numeric")
    number = float(value)
    _require(math.isfinite(number) and number > 0, f"{name}: not strictly positive finite")
    return number


def canonical(payload: Any) -> str:
    """Match the JSON hashing convention published by W2 (not a signature)."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(payload: Any) -> str:
    return hashlib.sha256(canonical(payload).encode("utf-8")).hexdigest()


def file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _no_duplicate_object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        _require(key not in result, f"duplicate JSON property: {key}")
        result[key] = value
    return result


def strict_json(path: str | Path) -> Any:
    """No duplicate keys, NaN/Infinity, or reinterpreted JSON labels."""
    return json.loads(Path(path).read_text(encoding="utf-8"),
                      object_pairs_hook=_no_duplicate_object_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(AdmissionError(f"nonfinite JSON: {value}")))


def coefficient_to_monomial(c_native: Sequence[float]) -> np.ndarray:
    """W0: monomial q=B*c, *not* W2's legacy field named 'q'."""
    return _vector(c_native, 10, "c_native") * B_DIAG


def native_polynomial(c_native: Sequence[float], xyz: Sequence[float]) -> float:
    x, y, z = _vector(xyz, 3, "position")
    features = np.array([1, x, y, z, x*x, y*y, z*z, y*z, x*z, x*y])
    return float(coefficient_to_monomial(c_native) @ features)


def native_jacobian_to_monomial(j_native: Any, *, smooth_full_ambient: bool) -> np.ndarray:
    """W0 Hessian diagnostic only for separately certified smooth ambient maps."""
    _require(smooth_full_ambient is True, "Hessian rule not applicable to tangent/discrete/unknown derivative")
    return _matrix(j_native, 10, 10, "Jc") / B_DIAG[None, :]


def raw_pushforward(r: Any, a: Any, t: Any, *, density_ratio: float = 1) -> np.ndarray:
    """W0 raw physical mass/first/second moment transform, including shear."""
    r = _vector(r, 10, "raw moments")
    A = _matrix(a, 3, 3, "affine linear")
    t = _vector(t, 3, "affine translation")
    w = abs(float(np.linalg.det(A))) * _positive(density_ratio, "density ratio")
    _require(math.isfinite(w) and w > 1e-15, "singular affine transform")
    M = r[0]
    L = r[1:4]
    Q = np.array([[r[4], r[9], r[8]], [r[9], r[5], r[7]], [r[8], r[7], r[6]]])
    AL = A @ L
    Lp = w * (AL + M * t)
    Qp = w * (A @ Q @ A.T + np.outer(AL, t) + np.outer(t, AL) + M*np.outer(t, t))
    return np.array([w*M, *Lp, Qp[0,0], Qp[1,1], Qp[2,2], Qp[1,2], Qp[0,2], Qp[0,1]])


def normalized_component_error(pred: Any, truth: Any, *, length_ref: float, density_ref: float) -> np.ndarray:
    L = _positive(length_ref, "reference length")
    rho = _positive(density_ref, "reference density")
    scale = rho * np.array([L**3] + [L**4]*3 + [L**5]*6)
    return abs(_vector(pred, 10, "prediction") - _vector(truth, 10, "truth")) / scale


def _check_frame(frame: Any) -> None:
    _require(isinstance(frame, dict) and frame.get("kind") == "INPUT_NORMALIZED_TARGET_V1", "W0 frame mismatch")
    _positive(frame.get("length_original_per_normalized"), "frame length")
    _positive(frame.get("density_original_per_normalized"), "frame density")
    _vector(frame.get("origin_original"), 3, "frame origin")


def check_w0_contract(record: Any) -> dict[str, Any]:
    """Validate the needed W0 MomentContractV1 *subset*, not full JSON schema.

    A mathematically valid W0 envelope is not proof of native material or label
    eligibility. W0's independent material seal is a separate requirement.
    """
    _require(isinstance(record, dict) and record.get("schema") == W0_SCHEMA, "W0 schema mismatch")
    _require(record.get("source_sha") == W0_SOURCE_SHA, "W0 source SHA mismatch")
    geometry, coeff, moments, jac = (record.get(k) for k in ("geometry", "coefficients", "moments", "jacobian"))
    _require(all(isinstance(x, dict) for x in (geometry, coeff, moments, jac)), "W0 sections absent")
    for key in ("original_sha256", "fixed_F_sha256", "design_D_sha256"):
        _require(_sha(geometry.get(key)), f"W0 geometry {key} missing")
    _check_frame(geometry.get("frame"))
    _positive(geometry.get("density"), "W0 density")
    _require(geometry.get("fixed_r_computed_once") is True, "W0 fixed mass must be cached once")
    _require(coeff.get("order") == NATIVE_C_ORDER and coeff.get("cross_mapping") == "q=Bc;Bdiag=1,1,1,1,1,1,1,2,2,2", "W0 coefficient convention mismatch")
    _require(coeff.get("positive_scale_equivalent") is True and coeff.get("negative_sign_equivalent") is False, "W0 projective sign mismatch")
    _require(coeff.get("retained_side") in ("BETA_POSITIVE", "BETA_NEGATIVE"), "W0 retained side missing")
    c = _vector(coeff.get("c"), 10, "W0 native c")
    _require(abs(float(np.linalg.norm(c))-1) <= 1e-12, "W0 c not native unit-normalized; do not renormalize saved bit pattern")
    _require(moments.get("order") == RAW_R_ORDER, "W0 raw moment order mismatch")
    F = _vector(moments.get("fixed_r"), 10, "W0 fixed F")
    _require(moments.get("status") in ("ANALYTIC_ONLY", "NATIVE_VERIFIED", "FAILED_MATERIAL", "NOT_RUN"), "W0 material status invalid")
    D = moments.get("variable_r")
    total = moments.get("total_r")
    _require((D is None) == (total is None), "W0 total/variable presence mismatch")
    if D is not None:
        D, total = _vector(D, 10, "W0 D"), _vector(total, 10, "W0 total")
        _require(np.allclose(total, F+D, rtol=1e-11, atol=1e-11), "W0 fixed counted twice or total mismatch")
    _require(jac.get("hessian_rule") == "ONLY_IF_SMOOTH_AMBIENT_CHECK_Jc_B_INVERSE", "W0 Hessian assumption mismatch")
    jt = jac.get("type")
    _require(jt in ("AMBIENT_10X10", "TANGENT_10XK", "UNAVAILABLE"), "W0 Jacobian type invalid")
    if jt == "AMBIENT_10X10":
        _require(jac.get("derivative_defined") is True, "W0 ambient derivative unavailable")
        _matrix(jac.get("values"), 10, 10, "W0 ambient Jacobian")
        _require(jac.get("native_tangent_basis") is None, "W0 ambient J has tangent basis")
    elif jt == "UNAVAILABLE":
        _require(jac.get("values") is None and jac.get("derivative_defined") is False, "W0 undefined derivative was promoted")
    else:
        _require(jac.get("derivative_defined") is True and jac.get("values") is not None and jac.get("native_tangent_basis") is not None, "W0 tangent derivative lacks basis")
        _require(isinstance(jac["values"], list) and len(jac["values"]) == 10, "W0 tangent derivative shape invalid")
        K = len(jac["values"][0]); _require(1 <= K <= 10, "W0 tangent rank invalid")
        _matrix(jac["values"], 10, K, "W0 tangent values")
        _matrix(jac["native_tangent_basis"], 10, K, "W0 tangent basis")
    return {"c_native": c, "r_fixed": F, "r_variable": D,
            "j_type": jt, "material_status": moments["status"], "geometry": geometry}


def _verify_w2_envelope(envelope: Any, *, c: Sequence[float], model_sha: str, module_sha: str) -> Mapping[str, Any]:
    _require(isinstance(envelope, dict) and set(envelope) == {"payload", "payload_sha256", "identity"}, "W2 envelope mismatch")
    p, identity = envelope["payload"], envelope["identity"]
    _require(isinstance(p, dict) and isinstance(identity, dict), "W2 envelope sections missing")
    w2_expected_fields = {"schema", "order", "coefficient_convention", "model_sha256",
         "native_module_sha256", "geometry", "density", "frame", "q", "r_D",
         "J_D", "r_F", "topology_status", "derivative_status", "derivative_contract",
         "stage_seconds", "peak_rss_bytes", "exact_proof", "split", "failure_reason",
         "total_policy"}
    _require(set(p) == w2_expected_fields, "W2 seal payload fields mismatch published W2 v1")
    _require(p.get("schema") == W2_SCHEMA and p.get("order") == W2_ORDER and p.get("coefficient_convention") == "NATIVE_MATRIX_ENTRY_Q10", "W2 order/convention mismatch")
    _require(_sha(envelope["payload_sha256"]) and digest(p) == envelope["payload_sha256"], "W2 payload tampered")
    q = _vector(p.get("q"), 10, "W2 q (native c)")
    _require(q.tolist() == _vector(c, 10, "expected native c").tolist(), "W2 c mismatches expected exact serialized coefficients")
    _require(abs(float(np.linalg.norm(q))-1) <= 1e-12, "W2 q must contain saved unit-normalized native coefficients")
    _require(_sha(model_sha) and _sha(module_sha), "W2 unpinned model/module identities")
    _require(p.get("model_sha256") == model_sha and p.get("native_module_sha256") == module_sha, "W2 model/module byte SHA mismatch")
    _require(set(identity) == {"q_sha256", "geometry_sha256", "model_sha256", "native_module_sha256"}, "W2 identity fields mismatch")
    _require(identity.get("q_sha256") == digest(p["q"]) and identity.get("geometry_sha256") == digest(p.get("geometry")), "W2 q/geometry fingerprint mismatch")
    _require(identity.get("model_sha256") == model_sha and identity.get("native_module_sha256") == module_sha, "W2 identity aliases mismatch")
    _require(p.get("total_policy") == "r_total=r_F+r_D;J_total=J_D;fixed_never_in_r_D", "W2 F/D policy mismatch")
    _positive(p.get("density"), "W2 density")
    _require(isinstance(p.get("stage_seconds"), dict), "W2 timings absent")
    for k, v in p["stage_seconds"].items():
        _require(isinstance(v, (int,float)) and not isinstance(v,bool) and math.isfinite(v) and v >= 0, f"W2 invalid timing {k}")
    rss = p.get("peak_rss_bytes")
    _require(rss is None or (isinstance(rss, int) and not isinstance(rss, bool) and rss >= 0), "W2 invalid RSS")
    _require(p.get("failure_reason") is None, "W2 explicitly failed/excluded")
    return p


def admit_w2_record(path: str | Path, *, expected_c_native: Sequence[float],
                    model_path: str | Path, native_module_path: str | Path,
                    approved_file_sha256: Iterable[str],
                    expected_design_sha256: str,
                    expected_w0_original_sha256: str,
                    expected_w0_fixed_sha256: str) -> dict[str, Any]:
    """Fail-closed W2 => W0 candidate label, subject to EXTERNAL byte approval.

    Approved hashes must come from an independent frozen teacher manifest;
    generating a hash from an untrusted record does not make it genuine.
    The W2 pre-W0 teacher's manifest has ZERO real runs and so currently
    provides no legitimate approved hashes. This loader does NOT train.
    """
    # Native v2 has no independently approved release catalog yet. Do not
    # reinterpret its q alias as a monomial vector or train on excluded rows.
    incoming = strict_json(path)
    if (isinstance(incoming,dict) and isinstance(incoming.get("payload"),dict)
            and incoming["payload"].get("schema")==W2_V2_SCHEMA):
        raise AdmissionError("W2_V2_FORMAL_NATIVE_RELEASE_NOT_INDEPENDENTLY_SEALED")
    permitted = frozenset(approved_file_sha256)
    _require(bool(permitted) and all(_sha(x) for x in permitted), "No independently approved W2 label checksum")
    actual_sha = file_sha256(path)
    _require(actual_sha in permitted, "W2 record checksum not independently approved")
    p = _verify_w2_envelope(strict_json(path), c=expected_c_native,
                            model_sha=file_sha256(model_path), module_sha=file_sha256(native_module_path))
    _require(p.get("split") in _VALID_SPLITS, "W2 sample excluded from all learning splits")
    _require(p.get("derivative_status") == "VALID" and p.get("topology_status") == "VALID", "W2 derivative or topology not validated")
    dc = p.get("derivative_contract")
    _require(isinstance(dc, dict) and dc.get("verified_neighborhood") is True, "W2 verified neighborhood proof absent")
    _matrix(p.get("J_D"), 10, 10, "W2 J_D")
    D = _vector(p.get("r_D"), 10, "W2 r_D")
    F = _vector(p.get("r_F"), 10, "W2 r_F")
    proof = p.get("exact_proof")
    _require(isinstance(proof, dict) and proof.get("kind") == "cherchi_same_call_discrete_map" and proof.get("native_cherchi") is True, "W2 real same-call native proof absent")
    for key in ("geometry_hash", "topology_hash", "evaluation_map_identity", "boolean_backend_identity", "derivative_identity"):
        _require(isinstance(proof.get(key), str) and len(proof[key]) > 4 and "mock" not in proof[key].lower(), f"W2 {key} missing/mock")
    geom = p.get("geometry")
    _require(isinstance(geom, dict) and isinstance(geom.get("family"), str) and len(geom["family"]) > 0, "W2 geometry family absent")
    for key, expected in (("design_D_sha256", expected_design_sha256),
                          ("original_sha256", expected_w0_original_sha256),
                          ("fixed_F_sha256", expected_w0_fixed_sha256)):
        _require(_sha(expected) and geom.get(key) == expected, f"W0/W2 {key} identity mismatch")
    _check_frame(p.get("frame"))
    return {"split":p["split"], "family":geom["family"], "geometry":dict(geom),
            "c_native": _vector(p["q"], 10, "native c"), "r_variable":D, "r_fixed":F,
            "r_total": F+D, "J_native": _matrix(p["J_D"], 10, 10, "J native"),
            "record_sha256":actual_sha, "model_sha256":p["model_sha256"],
            "native_module_sha256":p["native_module_sha256"],
            "stage_seconds": dict(p["stage_seconds"]), "peak_rss_bytes":p["peak_rss_bytes"],
            "status":"CANDIDATE_APPROVED_W2_NATIVE_LABEL_NOT_INDEPENDENT_MATERIAL_CERTIFICATION"}


def audit_family_split(candidates: Sequence[Mapping[str, Any]], *, require_train_and_test: bool = True) -> dict[str, Any]:
    """Disallow both exact material leakage and cross-family train/test leakage."""
    split_families: dict[str, set[str]] = {s:set() for s in _VALID_SPLITS}
    split_ids: dict[str, set[str]] = {s:set() for s in _VALID_SPLITS}
    row_ids: set[str] = set()
    for c in candidates:
        split = c.get("split")
        _require(split in _VALID_SPLITS, "invalid dataset split")
        family = c.get("family")
        geom = c.get("geometry")
        _require(isinstance(family, str) and family and isinstance(geom, dict), "missing family/geometry")
        split_families[split].add(family)
        for key in ("original_sha256", "fixed_F_sha256", "design_D_sha256"):
            _require(_sha(geom.get(key)), f"missing {key}")
            split_ids[split].add(geom[key])
        _require(_sha(c.get("record_sha256")), "missing pinned record checksum")
        _require(c["record_sha256"] not in row_ids, "duplicated teacher record")
        row_ids.add(c["record_sha256"])
    if require_train_and_test:
        _require(bool(split_families["train"]) and bool(split_families["test"]), "train/test must both have admitted samples")
    pairs = (("train", "val"), ("train", "test"), ("val", "test"))
    for lhs, rhs in pairs:
        _require(not (split_families[lhs] & split_families[rhs]), f"leaked geometry family across {lhs}/{rhs}")
        _require(not (split_ids[lhs] & split_ids[rhs]), f"leaked original/F/D geometry identity across {lhs}/{rhs}")
    return {"total":len(candidates),"by_split":{s:sum(r["split"]==s for r in candidates) for s in sorted(_VALID_SPLITS)},
            "families":{s:sorted(v) for s,v in split_families.items()}, "leakage":False}


# W5 migration proposal: distinct excluded-v2 inspection, NEVER an admission.
# Original W5 v1 candidate importer is intentionally kept for compatibility.
# Reviewed source: volcano-code/Spin_test W5 blob 14b2ab225a032188fe16570414ef321af9a81e00
W2_V2_SCHEMA = "w2-cherchi-teacher-v2-pre-w0"
_W2_V2_KEYS = frozenset((
    "schema","order","coefficient_convention","native_c_order","native_c",
    "polynomial_q","model_sha256","native_module_sha256","geometry","density",
    "frame","q","r_D","J_D","r_F","topology_status","derivative_status",
    "derivative_contract","stage_seconds","peak_rss_bytes","exact_proof",
    "split","failure_reason","total_policy"
))


def _same_native_binary64(left, right):
    import struct
    a=_vector(left,10,"raw native c")
    b=_vector(right,10,"independently expected native c")
    return struct.pack("!10d",*a)==struct.pack("!10d",*b)


def inspect_w2_v2_excluded_record(path, *, expected_native_c,
                                  expected_model_sha256,
                                  expected_native_module_sha256,
                                  expected_geometry_sha256):
    """Parse current W2 v2 strictly for diagnostics, NEVER return r/J labels.

    Expected SHA and original c MUST originate in an independent review;
    copying the envelope's claimed pins is not provenance certification.
    """
    import struct
    doc = strict_json(path)
    _require(type(doc) is dict and set(doc)=={"payload","payload_sha256","identity"},
             "V2_ENVELOPE_FIELDS_INVALID")
    p, identity=doc["payload"],doc["identity"]
    _require(type(p) is dict and set(p)==_W2_V2_KEYS and type(identity) is dict
             and set(identity)=={"q_sha256","geometry_sha256","model_sha256",
                                 "native_module_sha256"}, "V2_PAYLOAD_SHAPE_INVALID")
    _require(p.get("schema")==W2_V2_SCHEMA and p.get("native_c_order")==
             NATIVE_C_ORDER.split(",") and p.get("order")==W2_ORDER,
             "V2_SCHEMA_OR_MOMENT_ORDER_INVALID")
    _require(p.get("coefficient_convention")==
             "NATIVE_MATRIX_ENTRIES_C10_POLYNOMIAL_Q_EQUALS_BC_V1" and
             p.get("total_policy")=="r_total=r_F+r_D;J_total=J_D;fixed_never_in_r_D",
             "V2_NATIVE_C_AND_FIXED_POLICY_CHANGED")
    _require(_sha(doc["payload_sha256"]) and doc["payload_sha256"]==digest(p),
             "V2_PAYLOAD_DIGEST_MISMATCH")
    for key,expected in (("model_sha256",expected_model_sha256),
                          ("native_module_sha256",expected_native_module_sha256),
                          ("geometry_sha256",expected_geometry_sha256)):
        _require(_sha(expected) and identity.get(key)==expected,
                 "V2_INDEPENDENT_EXPECTED_SHA_MISMATCH:"+key)
    _require(p["model_sha256"]==expected_model_sha256 and
             p["native_module_sha256"]==expected_native_module_sha256 and
             type(p["geometry"]) is dict and digest(p["geometry"])==
             expected_geometry_sha256, "V2_UNBOUND_SOURCE_OR_GEOMETRY")
    raw=_vector(p["native_c"],10,"v2 native c")
    _require(_same_native_binary64(p["native_c"],expected_native_c) and
             _same_native_binary64(p["q"],expected_native_c),
             "V2_ORIGINAL_RAW_NATIVE_C_NOT_BITWISE_PRESERVED")
    monomial=(raw*B_DIAG).tolist()
    _require(_same_native_binary64(p["polynomial_q"],monomial),
             "V2_MONOMIAL_Q_NOT_B_TIMES_NATIVE_C")
    _require(identity.get("q_sha256")==digest(p["native_c"]),
             "V2_LEGACY_NATIVE_C_SHA_MISMATCH")
    _require(p.get("split")=="excluded" and p.get("J_D") is None and
             p.get("derivative_status") in ("UNKNOWN","INVALID") and
             p.get("derivative_contract") is None,
             "V2_REAL_TEACHER_RELEASE_NOT_AUTHORIZED")
    _require(p.get("topology_status") in
             ("FAILED","VALID","OBSERVED_DISCRETE_MAP") and
             type(p.get("exact_proof")) is dict,
             "V2_TOPOLOGY_OR_SOURCE_PROOF_INVALID")
    if p["topology_status"]=="FAILED":
        _require(p["r_D"] is None and p["r_F"] is None and
                 p["derivative_status"]=="INVALID",
                 "V2_FAILED_MATERIAL_CANNOT_PUBLISH_MOMENTS")
    for key in ("r_D","r_F"):
        if p[key] is not None:_vector(p[key],10,key)
    _positive(p.get("density"),"v2 density")
    _check_frame(p.get("frame"))
    _require(type(p.get("stage_seconds")) is dict and
             all(type(k) is str and type(v) in (float,int) and
                 math.isfinite(v) and v>=0
                 for k,v in p["stage_seconds"].items()), "V2_BAD_TIMING")
    _require(p.get("peak_rss_bytes") is None or
             (type(p["peak_rss_bytes"]) is int and p["peak_rss_bytes"]>=0),
             "V2_BAD_RSS")
    _require(math.isfinite(float(np.linalg.norm(raw))) and
             float(np.linalg.norm(raw))>0., "V2_DEGENERATE_C")
    return {
       "schema":"W5_MIGRATION_V2_EXCLUDED_DIAGNOSTIC_V1",
       "archived_raw_native_binary64_sha256":hashlib.sha256(
           struct.pack("!10d",*raw)).hexdigest(),
       "native_c_w0_unit_compatible":abs(float(np.linalg.norm(raw))-1.)<=1e-12,
       "legacy_q_is_native_c_not_polynomial":True,
       "monomial_q_is_B_times_native_c":True,
       "status":"READ_ONLY_V2_EXCLUDED_NO_NATIVE_RELEASE",
       "derivative_J_D":None,
       "native_material_certified":False,
       "train_val_test_admitted":False,
       "training_admitted":False
    }

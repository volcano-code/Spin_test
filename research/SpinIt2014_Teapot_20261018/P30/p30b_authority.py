#!/usr/bin/env python3
"""P30-B: fail-closed W0/W2 authorization for genuine Teapot tangent *diagnostics*.

The authenticated P27 one-point M6 receipt is NOT an authorization for any new
native evaluation. W0's physical-case authority and W2's separate Teapot
feature/teacher authority must independently issue *tracked* read-only receipts
on their respective research branches. Only diagnostic sampling is possible
after those receipts and a separately registered pilot lock; this script
cannot grant W0/W2/derivative/optimization/training scientific admission.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys

import p30_neighborhood_preflight as seed

SCHEMA = "W4_P30B_OWNER_TEACHER_DIAGNOSTIC_READINESS_V1"
LOCK_SCHEMA = "W4_P30B_TANGENT_PILOT_PRERUN_LOCK_V1"
W0_BRANCH = "research/neuralmoments-w0-contract-20261019"
W2_BRANCH = "research/neuralmoments-w2-teacher-20261019"
W0_REL = "research/NeuralMoments/contracts/P30_TEAPOT_DIAGNOSTIC_AUTHORIZATION.json"
W2_REL = "research/NeuralMoments/teacher/P30_TEAPOT_FEATURE_PILOT_AUTHORIZATION.json"
EXPECTED_REQUEST_SHA = "a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9"
EXPECTED_W0_FROZEN = "5bab2eb2616df306906a6887a273f68acfa49320"
EXPECTED_W2_REVIEW_BASE = "64f7c491fff8efca6f8dc1d4f12871c677a0ec02"
P30_PRIVATE_PLAN_SHA = "fc2d9a1b3c372513cdf3d6ba41e74812a12761e67f6b6fa82c0a66982351bacc"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
CLOSED = dict(W0_owner_admitted=False, W2_teacher_training_allowed=False,
              continuous_smoothness_certified=False, Newton_accepted=False,
              training_admissible=False, Faster_optimization_executed=False,
              physical_validation_certified=False, MuJoCo_optimized_before_after_executed=False)

class GateRejected(ValueError):
    pass

def need(condition, reason):
    if not condition:
        raise GateRejected(reason)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)

def strict_json(data):
    def unique(rows):
        d = {}
        for k, v in rows:
            need(k not in d, "DUPLICATE_JSON_KEY:"+k)
            d[k] = v
        return d
    def invalid(token):
        raise GateRejected("NONFINITE_JSON:"+token)
    doc = json.loads(data, object_pairs_hook=unique, parse_constant=invalid)
    need(type(doc) is dict, "JSON_OBJECT_REQUIRED")
    return doc

def git(root, *argv):
    result = subprocess.run(["git", "-C", str(root), *argv],
                            capture_output=True, check=False, timeout=45)
    need(result.returncode == 0, "GIT_INVALID:"+":".join(argv))
    return result.stdout.decode("utf-8", errors="strict").strip()

def resolve_authority(repo, branch, rel):
    """Inspect immutable HEAD blob, then require that HEAD belongs to the owner remote.

    This is a provenance guard against using uncommitted W4 copies. It is NOT a
    cryptographic signature or independent runtime attestation.
    """
    root = Path(repo).resolve(strict=True)
    head = git(root, "rev-parse", "HEAD")
    need(HEX40.fullmatch(head), "GIT_HEAD_REQUIRED")
    if git(root, "rev-parse", "--verify", "refs/remotes/origin/"+branch) != head:
        raise GateRejected("OWNER_BRANCH_HEAD_NOT_CURRENT:"+branch)
    try:
        entry = git(root, "ls-tree", "HEAD", "--", rel)
    except GateRejected as exc:
        raise GateRejected("OWNER_COMMIT_NOT_READABLE:"+branch) from exc
    if not entry:
        return {"state": "MISSING", "branch": branch, "head": head, "path": rel}
    row = entry.split("\t", 1)
    need(len(row) == 2 and row[1] == rel, "OWNER_PATH_NOT_CANONICAL")
    mode, kind, blob = row[0].split()
    need(mode == "100644" and kind == "blob" and HEX40.fullmatch(blob), "OWNER_FILE_TYPE_INVALID")
    raw = subprocess.run(["git", "-C", str(root), "show", "HEAD:"+rel],
                         capture_output=True, timeout=45, check=False)
    need(raw.returncode == 0, "OWNER_BLOB_READ_FAILED")
    need(hashlib.sha1(b"blob "+str(len(raw.stdout)).encode()+b"\0"+raw.stdout).hexdigest() == blob,
         "OWNER_BLOB_HASH_MISMATCH")
    local = root / rel
    need(local.is_file() and not local.is_symlink() and local.read_bytes() == raw.stdout,
         "OWNER_WORKTREE_CHANGED")
    return {"state": "AVAILABLE", "branch": branch, "head": head,
            "path": rel, "git_blob": blob, "sha256": digest(raw.stdout),
            "doc": strict_json(raw.stdout)}

def read_authorities(w0_review_root, w2_review_root):
    return {
        "w0": resolve_authority(w0_review_root, W0_BRANCH, W0_REL),
        "w2": resolve_authority(w2_review_root, W2_BRANCH, W2_REL),
    }

def validate_plan(plan):
    need(type(plan) is dict and plan.get("schema") == seed.SCHEMA and
         plan.get("status") == "P30_PROBES_PLANNED_NOT_EVALUATED", "UNVERIFIED_PLAN_SCHEMA")
    evidence = plan.get("evidence", {})
    for k, value in (("run",seed.RUN),("archive_sha256",seed.ARCHIVE_SHA),
                     ("manifest_sha256",seed.MANIFEST_SHA),("lock_sha256",seed.LOCK_SHA),
                     ("base_native_c_sha256",seed.C_SHA),("same_call_Jc_binary_sha256",seed.J_SHA)):
        need(evidence.get(k) == value, "P27_PLAN_PARENT_MISMATCH:"+k)
    need(type(plan.get("probes")) is list and len(plan["probes"]) == 36,
         "PLAN_REQUIRES_36_CANDIDATE_COEFFICIENTS")
    need(plan.get("pilot_probe_count") == 12 and plan.get("pilot_directions") == 3 and
         plan.get("completed_new_native_evaluations") == 0 and
         plan.get("native_derivative_neighborhood_certified") is False and
         plan.get("training_admissible") is False and plan.get("Newton_accepted") is False,
         "PLAN_PREMATURE_SCIENTIFIC_RELEASE")
    h = plan.get("step_radians")
    need(type(h) is float and 0 < h <= 0.1, "INVALID_PROPOSED_STEP")
    c = plan.get("native_c")
    need(type(c) is list and len(c)==10 and all(type(v) is float and math.isfinite(v) for v in c)
         and seed.canonical_hash(c) == seed.C_SHA, "PLAN_BASE_C_CHANGED")
    reconstructed = seed.plan({
        "c": c,
        "Jc": plan["captured_single_point_Jc"],
        "pins": {"context_sha256": evidence["evaluator_context_sha256"]},
        "saved_topology_hash": plan["observed_base_topology_hash_not_feature_branch_certificate"],
        "saved_geometry_hash": evidence["geometry_hash"],
    }, step=h)
    need(canonical(reconstructed) == canonical(plan), "PLAN_RECONSTRUCTION_OR_ORDER_MISMATCH")
    return plan

def validate_owner(w0, plan, request):
    need(w0.get("schema") == "W0_TEAPOT_P30_DIAGNOSTIC_AUTHORIZATION_V1" and
         w0.get("decision") == "APPROVED_FOR_DIAGNOSTIC_PILOT_ONLY",
         "W0_DIAGNOSTIC_AUTHORIZATION_NOT_ISSUED")
    need(w0.get("source_w0_baseline") == EXPECTED_W0_FROZEN and
         w0.get("p20_request_sha256") == EXPECTED_REQUEST_SHA and
         w0.get("p27_manifest_sha256") == seed.MANIFEST_SHA and
         w0.get("p30_plan_sha256") == P30_PRIVATE_PLAN_SHA and
         w0.get("native_c_sha256") == seed.C_SHA,
         "W0_PHYSICAL_APPROVAL_IDENTITY_MISMATCH")
    need(w0.get("approved_physical_case") is True and
         w0.get("real_support_tip_and_shaft_reviewed") is True and
         w0.get("approve_real_native_pilot") is True,
         "W0_CASE_OR_TIP_APPROVAL_MISSING")
    need(w0.get("pilot_directions") == [0,1,2] and
         w0.get("maximum_real_native_points") == 12 and
         w0.get("step_radians") == plan["step_radians"],
         "W0_PILOT_SCOPE_CHANGED")
    for key in ("length_ref","density_ref","max_normalized_jacobian_error"):
        value = w0.get(key)
        need(type(value) is float and math.isfinite(value) and value > 0,
             "W0_OWNER_NUMERIC_BUDGET_MISSING:"+key)
    need(w0["length_ref"] > 0 and w0["density_ref"] > 0 and
         w0["max_normalized_jacobian_error"] > 0, "W0_INVALID_BUDGET")
    need(w0.get("newton_authorized") is False and w0.get("training_authorized") is False,
         "W0_SCIENTIFIC_RELEASE_NOT_SUPPORTED")
    return {"step_radians": w0["step_radians"], "length_ref": w0["length_ref"],
            "density_ref": w0["density_ref"],
            "max_normalized_jacobian_error": w0["max_normalized_jacobian_error"]}

def validate_teacher(w2, plan, w0_sha):
    need(w2.get("schema") == "W2_TEAPOT_P30_FEATURE_PILOT_AUTHORIZATION_V1" and
         w2.get("decision") == "APPROVED_FOR_DIAGNOSTIC_PILOT_ONLY",
         "W2_DIAGNOSTIC_AUTHORIZATION_NOT_ISSUED")
    need(w2.get("p27_manifest_sha256") == seed.MANIFEST_SHA and
         w2.get("p30_plan_sha256") == P30_PRIVATE_PLAN_SHA and
         w2.get("native_c_sha256") == seed.C_SHA and
         w2.get("native_Jc_sha256") == seed.J_SHA and
         w2.get("w0_approval_sha256") == w0_sha,
         "W2_TEAPOT_APPROVAL_IDENTITY_MISMATCH")
    need(w2.get("feature_branch_policy") == "SOURCE_FEATURE_BRANCH_V2" and
         w2.get("base_feature_branch_sha256") ==
         plan.get("observed_base_topology_hash_not_feature_branch_certificate") and
         w2.get("independent_feature_branch_reviewed") is True and
         w2.get("approve_real_native_pilot") is True,
         "W2_BASE_FEATURE_INDEPENDENT_REVIEW_MISSING")
    need(w2.get("native_Jc_numerically_certified") is False and
         w2.get("smooth_neighborhood_certified") is False and
         w2.get("training_authorized") is False and
         w2.get("Newton_authorized") is False,
         "W2_PREMATURE_DERIVATIVE_OR_NEWTON_RELEASE")
    return {"base_feature_branch_sha256": w2["base_feature_branch_sha256"]}

def evaluate(plan, approvals, request, plan_raw):
    if approvals["w0"]["state"] != "AVAILABLE" or approvals["w2"]["state"] != "AVAILABLE":
        missing = [name for name in ("w0","w2") if approvals[name]["state"] != "AVAILABLE"]
        return {"schema":SCHEMA, "status":"BLOCKED_WAITING_INDEPENDENT_"+("_".join(missing)).upper()+"_APPROVAL",
                "missing":missing, "P27_one_point_M6_verified":True,
                "real_native_pilot_authorized":False, "new_native_calls":0, **CLOSED}
    need(digest(plan_raw)==P30_PRIVATE_PLAN_SHA, "EXTERNAL_P30_PLAN_SHA_MISMATCH")
    need(digest(request)==EXPECTED_REQUEST_SHA, "P20_REQUEST_HASH_MISMATCH")
    plan=validate_plan(plan)
    owner=validate_owner(approvals["w0"]["doc"],plan,request)
    teacher=validate_teacher(approvals["w2"]["doc"],plan,approvals["w0"]["sha256"])
    return {"schema":SCHEMA, "status":"DIAGNOSTIC_PILOT_APPROVALS_PRESENT_NOT_EXECUTED",
            "real_native_pilot_authorized":True,
            "evidence":{"p27_manifest_sha256":seed.MANIFEST_SHA,"P30_plan_sha256":digest(plan_raw)},
            "owner":owner,"teacher":teacher,
            "approvals":{k:{f:v[f] for f in ("branch","head","path","git_blob","sha256")}
                         for k,v in approvals.items()},
            "new_native_calls":0, **CLOSED}

def make_lock(readiness):
    need(readiness.get("status") == "DIAGNOSTIC_PILOT_APPROVALS_PRESENT_NOT_EXECUTED" and
         readiness.get("real_native_pilot_authorized") is True and
         readiness.get("new_native_calls") == 0 and
         all(readiness.get(k) is False for k in CLOSED),
         "DIAGNOSTIC_OWNER_APPROVALS_NOT_READY")
    return {"schema":LOCK_SCHEMA,"status":"EXTERNAL_REVIEW_REQUIRED_BEFORE_NATIVE_PILOT",
            "readiness":readiness, "expected_p27_lock_sha256":seed.LOCK_SHA,
            "expected_p27_manifest_sha256":seed.MANIFEST_SHA,
            "expected_p27_archive_sha256":seed.ARCHIVE_SHA,
            "probe_count_max":12, "native_calls_allowed_by_this_lock":False,
            "scientific_admission":False, **CLOSED}

def write_new(path, doc):
    path=Path(path)
    need(not path.exists() and not path.is_symlink() and
         not any(p.is_symlink() for p in path.parents), "REFUSE_OVERWRITE_OR_SYMLINK")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x",encoding="utf-8") as stream:
        json.dump(doc,stream,sort_keys=True,indent=2,allow_nan=False);stream.write("\n")

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--w0-review-root",type=Path,required=True)
    p.add_argument("--w2-review-root",type=Path,required=True)
    p.add_argument("--plan",type=Path,required=True)
    p.add_argument("--p20-request",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--mode",choices=("preflight","seal"),default="preflight")
    a=p.parse_args(argv)
    try:
        # Missing owner-issued JSON is a supported BLOCKED result, not an
        # invitation to fabricate W4-local authorizations.
        approvals=read_authorities(a.w0_review_root,a.w2_review_root)
        raw=a.plan.read_bytes()
        request=a.p20_request.read_bytes()
        plan=validate_plan(strict_json(raw))
        result=evaluate(plan,approvals,request,raw)
        if a.mode=="seal":
            result=make_lock(result)
        write_new(a.output,result)
        print(canonical({"status":result["status"],"output":str(a.output),
                         "real_native_pilot_authorized":result.get("real_native_pilot_authorized",False),
                         "new_native_calls":0,"training_admissible":False}))
        return 0 if a.mode=="seal" else 3 if not result["real_native_pilot_authorized"] else 0
    except (GateRejected,seed.PlanRejected,OSError,TypeError,KeyError,ValueError,
            json.JSONDecodeError,subprocess.SubprocessError) as exc:
        print(canonical({"status":"REJECTED_CLOSED","error":str(exc),
                         "new_native_calls":0,"training_admissible":False}),
              file=sys.stderr)
        return 4

if __name__=="__main__":
    raise SystemExit(main())

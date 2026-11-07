#!/usr/bin/env python3
"""W4 P29-A: independently pin and inspect W0/W2 scientific admission readiness.

This is a READ-ONLY cross-window audit. A formal W4 M6 native geometry success
is not an authorized W0 owner/physical release or W2 teacher/newton release.
This program never imports native code and deliberately has no path that grants
scientific admission. If upstream releases change, a new reviewed contract is
required instead of automatically trusting newly true JSON flags.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

W4_REF = "research/neuralmoments-w4-teapot-p1-20261019"
W0_SHA = "5bab2eb2616df306906a6887a273f68acfa49320"
W2_SHA = "64f7c491fff8efca6f8dc1d4f12871c677a0ec02"
P27_LOCK_SHA = "451d8b46cd047325b0b3e2d406f9e89dd0252cece677f5f310ca5abe3c8089a4"
P27_MANIFEST_SHA = "3a9b6b21d1d1185e00d1ef25a1bfc625d4696f554c3ab4a7719f5d85ca109773"
P27_RUN = "formal-m6-run-20261107T050117Z"
W4_P20 = "research/SpinIt2014_Teapot_20261018/P1/P20_native_request.json"
W4_P28 = "research/SpinIt2014_Teapot_20261018/P28/P28_FORMAL_M6_OFFLINE_REVIEW_20261107.json"
W0_PARTITION = "research/NeuralMoments/contracts/full_partition_m6.py"
W0_TANGENT = "research/NeuralMoments/contracts/tangent_neighborhood.py"
W0_TEACHER = "research/NeuralMoments/contracts/w2_teacher_gate.py"
W2_MANIFEST = "research/NeuralMoments/teacher/teacher_manifest.json"
W2_STATUS = "research/NeuralMoments/teacher/W2_STATUS_SNAPSHOT_20261106.md"
FILES = {
    "w4": {
        W4_P20: "f3bca7bef1f207cb5b857848c9588543fb7e5a9c",
        W4_P28: "5c7cffcc3868ab5494ef75db34ebb429fbf72dd5",
    },
    "w0": {
        W0_PARTITION: "7f18bafa1094ae38eadc0fa13cde7730c35cfe32",
        W0_TANGENT: "4fbfd52a787f3cbbc4228b1c1bbdab01638ed57f",
        W0_TEACHER: "b42ec6d9b389675123250d79f9cc9efb1b658c07",
    },
    "w2": {
        W2_MANIFEST: "05968ded975532422d52327011768833f087afec",
        W2_STATUS: "a384c84bc2001b3f6584caf5ab514cbe853a9d80",
    },
}
SCHEMA = "W4_P29_CROSS_WINDOW_SCIENTIFIC_ADMISSION_AUDIT_V1"
STATUS = "P29_BLOCKED_OWNER_PHYSICAL_AND_TEACHER_DERIVATIVE_NEWTON"
HEX = re.compile(r"[0-9a-f]{40}\Z")


class AdmissionRejected(ValueError):
    pass


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise AdmissionRejected(reason)


def command(root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45, check=False,
    )
    require(completed.returncode == 0, "GIT_SOURCE_UNAVAILABLE:" + " ".join(args))
    return completed.stdout


def git_head(root: Path) -> str:
    return command(root, "rev-parse", "HEAD").decode("ascii").strip()


def checked_file(root: Path, rel: str, expected_blob: str) -> bytes:
    # Read the actual pinned commit object, not the modified working tree.
    require(bool(HEX.fullmatch(expected_blob)), "INVALID_SOURCE_BLOB_PIN")
    entry = command(root, "ls-tree", "HEAD", "--", rel).decode("utf-8").strip()
    fields = entry.split()
    require(len(fields) == 4 and fields[0] in ("100644", "100755")
            and fields[1] == "blob" and fields[2] == expected_blob
            and fields[3] == rel, "GIT_BLOB_IDENTITY_DRIFT:" + rel)
    data = command(root, "show", "HEAD:" + rel)
    sha = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    require(sha == expected_blob, "SOURCE_CONTENT_BLOB_DRIFT:" + rel)
    local = root / rel
    require(local.is_file() and not local.is_symlink()
            and local.read_bytes() == data, "CHECKOUT_WORKTREE_DRIFT:" + rel)
    return data


def strict_json(data: bytes) -> dict:
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "DUPLICATE_JSON_KEY:" + key)
            out[key] = value
        return out
    obj = json.loads(data, object_pairs_hook=pairs,
                     parse_constant=lambda _: (_ for _ in ()).throw(AdmissionRejected("NONFINITE_JSON")))
    require(type(obj) is dict, "JSON_ROOT_MUST_BE_OBJECT")
    return obj


def inspect(w4: dict, p28: dict, w2: dict, *, observed_w0: str, observed_w2: str) -> dict:
    """Pure structural decision; never authorizes Newton/training."""
    require(w4.get("schema") == "W4_P20_TEAPOT_NATIVE_REQUEST_V1"
            and w4.get("purpose") == "PREREGISTERED_NONOPTIMIZED_ONE_POINT_MATERIAL_PARTITION_PROBE",
            "W4_REGISTERED_TEAPOT_CASE_CHANGED")
    require(w4.get("source_w0_commit") == W0_SHA, "W4_W0_SOURCE_NOT_PINNED")
    require(w4.get("units", {}).get("physical_parameters_approved") is False,
            "W0_PHYSICAL_APPROVAL_CHANGE_NEEDS_OWNER_AUTHENTICATION")
    require(w4.get("admission", {}).get("W0_owner_admitted") is False
            and w4.get("admission", {}).get("W2_teacher_training_allowed") is False
            and w4.get("admission", {}).get("Faster_optimization_executed") is False
            and w4.get("admission", {}).get("MuJoCo_optimized_before_after_executed") is False,
            "FORGED_W4_SCIENTIFIC_ADMISSION")
    require(w4.get("admission", {}).get("original_author_CAD") is False
            and w4.get("admission", {}).get("physical_validation_passed") is False,
            "FORGED_ORIGINAL_CAD_OR_PHYSICAL_PROOF")
    require(w4.get("target", {}).get("mode") == "SPINNING_TOP"
            and w4.get("target", {}).get("axis") == [0, 0, 1]
            and w4.get("target", {}).get("origin") == [0, 0, 0]
            and w4.get("target", {}).get("support_points") == [],
            "TEAPOT_TARGET_OR_SUPPORT_CHANGED")
    require(w4.get("geometry_policy", {}).get("shaft_material")
            == "S_ALREADY_INCLUDED_IN_F_NEVER_ADDED_AGAIN",
            "FIXED_SHAFT_MATERIAL_CONTRACT_CHANGED")
    require(w4.get("units", {}).get("physical_density_kg_m3") == 1200
            and w4.get("units", {}).get("length_m_per_reference_binary64") == 0.025,
            "TEAPOT_PHYSICAL_PROPOSAL_IDENTITY_CHANGED")
    require(p28.get("status") == "ARCHIVE_AND_SAME_CALL_ARITHMETIC_REPLAY_CONSISTENT"
            and p28.get("formal_status") == "REAL_NATIVE_M6_GEOMETRY_VERIFIED_NO_SCIENTIFIC_RELEASE"
            and p28.get("formal_exit_code") == 0
            and p28.get("formal_w0_commit") == W0_SHA
            and p28.get("formal_run_id") == P27_RUN
            and p28.get("registered_lock_sha256") == P27_LOCK_SHA
            and p28.get("formal_manifest_sha256") == P27_MANIFEST_SHA,
            "P27_P28_FORMAL_EVIDENCE_IDENTITY_CHANGED")
    require(p28.get("manifest_files_hash_verified") == 37
            and p28.get("manifest_files_hash_failed") == 0
            and p28.get("exact_D_minus_R_minus_C_zero") is True
            and p28.get("exact_M_minus_F_minus_R_minus_C_zero") is True
            and p28.get("same_call_100_jacobian_bytes_match") is True
            and p28.get("independent_negative_controls") == {"total": 2, "correctly_rejected": 2},
            "P28_ARITHMETIC_OR_BYTE_EVIDENCE_MISSING")
    require(p28.get("official_p21_replay_verify_executed") is False
            and p28.get("independent_native_set_predicates_reexecuted") is False
            and p28.get("independent_runtime_attestation") is False
            and p28.get("scientific_admission") is False
            and p28.get("W0_owner_admitted") is False
            and p28.get("W2_teacher_training_allowed") is False
            and p28.get("smooth_neighborhood_certified") is False
            and p28.get("newton_terminal_certified") is False
            and p28.get("Faster_optimization_executed") is False,
            "P28_REVIEW_SCOPE_OR_RELEASE_FLAGS_CHANGED")
    require(w2.get("schema") == "w2-cherchi-teacher-v2-pre-w0"
            and type(w2.get("training_samples")) is int and w2["training_samples"] == 0
            and type(w2.get("native_teacher_runs")) is int and w2["native_teacher_runs"] == 1,
            "W2_TEACHER_MANIFEST_CHANGED_REQUIRES_NEW_RELEASE_REVIEW")
    splits = w2.get("data_splits", {})
    require(type(splits) is dict
            and all(splits.get(k) == [] for k in ("train", "val", "test"))
            and type(splits.get("excluded")) is list
            and len(splits["excluded"]) > 0,
            "W2_TRAINING_SPLIT_PROMOTION_REQUIRES_REVIEW")
    diagnostic = w2.get("latest_native_diagnostic", {})
    require(diagnostic.get("J_D") is None and diagnostic.get("split") == "excluded"
            and diagnostic.get("training_admitted") is False,
            "W2_EXCLUDED_HEART_DIAGNOSTIC_CHANGED")
    require(observed_w0 == W0_SHA and observed_w2 == W2_SHA,
            "UPSTREAM_COMMIT_NOT_PINNED")
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "reviewed_upstreams": {"w0_commit": observed_w0, "w2_commit": observed_w2},
        "teapot_run": P27_RUN,
        "formal_m6_geometry_receipt_passed": True,
        "independent_exact_arithmetic_replay_passed": True,
        "physical_case": {
            "length_m_per_reference": 0.025,
            "density_kg_m3": 1200,
            "unit_material_density_F_D": 1,
            "target_axis": [0, 0, 1],
            "target_origin": [0, 0, 0],
            "support_points": [],
            "fixed_shaft_already_in_F": True,
            "physical_parameters_approved_by_W0": False,
            "original_author_CAD_certified": False,
            "physical_validation_passed": False,
        },
        "w2_manifest": {
            "schema": w2["schema"],
            "status": w2.get("status"),
            "native_teacher_runs_historical_heart": w2["native_teacher_runs"],
            "training_samples": 0,
            "train_val_test_empty": True,
            "latest_heart_diagnostic_J_D": None,
            "latest_heart_diagnostic_split": "excluded",
            "matching_teapot_teacher_admission": False,
        },
        "gates": {
            "P27_formal_native_M6_geometry_receipt": True,
            "P28_independent_archive_arithmetic": True,
            "original_P21_offline_verifier_executed": False,
            "W0_owner_adoption_for_Teapot": False,
            "W0_physical_parameters_and_true_tip_approved": False,
            "W2_independent_Teapot_teacher_proof": False,
            "W0_W2_smooth_derivative_neighborhood": False,
            "W0_W2_Newton_terminal_certification": False,
            "W2_training_release": False,
            "Teapot_three_objective_optimization": False,
            "MuJoCo_optimized_before_after": False,
        },
        "required_handoffs": [
            "W0 must independently adopt the P20/P27 physical case or issue a new pinned physical case; settle true tip/contact, shell/shaft F/D, density, dimensions and printability.",
            "W2 must review the same Teapot c, geometry, source/Boolean and native module identities; Heart/Noodles evidence is not interchangeable with Teapot.",
            "W0/W2 must obtain new authenticated same-branch tangent probes around the Teapot c and an independently approved smooth-neighborhood certificate.",
            "Newton and training remain prohibited until separate terminal and teacher release receipts.",
        ],
        "new_native_calls": 0,
        "native_set_predicates_reexecuted": False,
        "scientific_admission": False,
        "training_admissible": False,
        "Newton_accepted": False,
        "physical_validation_certified": False,
        "scope": "READ_ONLY_PINNED_CROSS_WINDOW_EVIDENCE_REVIEW_NOT_APPROVAL",
    }


def run(w4_root: Path, w0_root: Path, w2_root: Path) -> dict:
    roots = {"w4": w4_root.resolve(strict=True),
             "w0": w0_root.resolve(strict=True),
             "w2": w2_root.resolve(strict=True)}
    w0_head, w2_head = git_head(roots["w0"]), git_head(roots["w2"])
    require(w0_head == W0_SHA and w2_head == W2_SHA, "UPSTREAM_GIT_HEAD_MISMATCH")
    require(command(roots["w4"], "rev-parse", "--abbrev-ref", "HEAD").decode().strip()
            in (W4_REF, "HEAD"), "NOT_W4_RESEARCH_CHECKOUT")
    raw = {kind: {rel: checked_file(roots[kind], rel, blob)
                  for rel, blob in files.items()}
           for kind, files in FILES.items()}
    p20 = strict_json(raw["w4"][W4_P20])
    p28 = strict_json(raw["w4"][W4_P28])
    w2 = strict_json(raw["w2"][W2_MANIFEST])
    # The W0 frozen gates explicitly exclude promotion of single-point values;
    # W2 status is frozen to an independent Git blob for review provenance.
    require(b"training_admissible" in raw["w0"][W0_PARTITION]
            and b"smooth_neighborhood_certified" in raw["w0"][W0_TANGENT]
            and b"training_admissible" in raw["w0"][W0_TEACHER],
            "W0_CONTRACT_SOURCE_SEMANTICS_CHANGED")
    require(b"training samples remain zero" in raw["w2"][W2_STATUS]
            and b"J_D=null" in raw["w2"][W2_STATUS],
            "W2_STATUS_SNAPSHOT_SEMANTICS_CHANGED")
    report = inspect(p20, p28, w2, observed_w0=w0_head, observed_w2=w2_head)
    report["source_blob_pins"] = FILES
    report["w4_head"] = git_head(roots["w4"])
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--w4-root", type=Path, required=True)
    parser.add_argument("--w0-root", type=Path, required=True)
    parser.add_argument("--w2-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.w4_root, args.w0_root, args.w2_root)
        output = args.output.absolute()
        require(not output.exists() and not output.is_symlink(), "REFUSE_TO_OVERWRITE_AUDIT")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
                          encoding="utf-8")
        print(json.dumps({"status": result["status"], "scientific_admission": False,
                          "training_admissible": False, "output": str(output)}, sort_keys=True))
        return 3  # An authentic BLOCKED decision must never look like admission.
    except (AdmissionRejected, OSError, ValueError, KeyError, TypeError,
            subprocess.SubprocessError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "P29_REJECTED", "error": str(exc),
                          "scientific_admission": False}, sort_keys=True), file=sys.stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())

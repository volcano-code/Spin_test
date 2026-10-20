"""W0 M15: conservative cross-window observation gate, never a teacher publisher."""
from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

SOURCE = "0bcc187b3005478baa586a6d6f450e73811ca342"
H8F = "99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9"
WINDOWS = {f"W{i}" for i in range(7)}
HEX40 = re.compile(r"[a-f0-9]{40}\Z")

class GateError(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise GateError(message)

def strict_json(raw):
    def unique(rows):
        output = {}
        for key, value in rows:
            require(key not in output, "DUPLICATE_JSON_KEY")
            output[key] = value
        return output
    def invalid(number):
        raise GateError("INVALID_NONFINITE_NUMBER")
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)

def audit(snapshot):
    require(type(snapshot) is dict and set(snapshot) == {"schema", "frozen_source", "branch_observations", "w2", "w3", "consumer_policy"}, "WRONG_SNAPSHOT_SCHEMA")
    require(snapshot["schema"] == "W0_M15_CROSS_WINDOW_OBSERVATION_V1" and snapshot["frozen_source"] == SOURCE, "SOURCE_CHANGED")
    branch = snapshot["branch_observations"]
    require(type(branch) is dict and set(branch) == WINDOWS, "SEVEN_BRANCHES_REQUIRED")
    for name, entry in branch.items():
        require(type(entry) is dict and set(entry) == {"branch", "sha", "observed_message"}, "INVALID_BRANCH_ENTRY")
        require(type(entry["branch"]) is str and entry["branch"].startswith("research/neuralmoments-w" + name[1:] + "-") and
                type(entry["sha"]) is str and HEX40.fullmatch(entry["sha"]) and type(entry["observed_message"]) is str and bool(entry["observed_message"]), "BRANCH_SHA_NOT_PINNED")
    w2 = snapshot["w2"]
    w3 = snapshot["w3"]
    policy = snapshot["consumer_policy"]
    require(type(w2) is dict and set(w2) == {"archive_sha256", "archived_samples", "unit_native_c", "nonunit_native_c", "new_native_teacher_samples", "released_J_D", "train_splits_present", "continuous_neighborhood_certified", "formal_teacher_release"}, "W2_SHAPE")
    require(w2["archive_sha256"] == H8F and w2["archived_samples"] == 81 and w2["unit_native_c"] == 17 and w2["nonunit_native_c"] == 64, "W2_ARCHIVED_SOURCE_DRIFT")
    require(type(w3) is dict and set(w3) == {"new_side_materials", "required_side_materials", "accepted_newton_steps", "continuous_neighborhood_certified", "final_heart_obj"}, "W3_SHAPE")
    require(type(policy) is dict and policy == {"w5_requires_formal_teacher": True, "w6_requires_formal_teacher": True, "analytic_p0_is_real_teacher": False}, "CONSUMER_GATE_BYPASS")
    require(w3["required_side_materials"] == 4, "W3_FOUR_SIDE_CONTRACT_CHANGED")
    for name in ("new_native_teacher_samples", "released_J_D"):
        require(type(w2[name]) is int and w2[name] >= 0, "W2_COUNT_INVALID")
    for name in ("new_side_materials", "accepted_newton_steps"):
        require(type(w3[name]) is int and w3[name] >= 0, "W3_COUNT_INVALID")
    for name in ("train_splits_present", "continuous_neighborhood_certified", "formal_teacher_release"):
        require(type(w2[name]) is bool, "W2_BOOLEAN_INVALID")
    for name in ("continuous_neighborhood_certified", "final_heart_obj"):
        require(type(w3[name]) is bool, "W3_BOOLEAN_INVALID")
    blocked = []
    if not w2["new_native_teacher_samples"]: blocked.append("NO_NEW_NATIVE_TEACHER")
    if not w2["released_J_D"]: blocked.append("NO_RELEASED_J_D")
    if not w2["continuous_neighborhood_certified"]: blocked.append("NO_W2_CONTINUOUS_NEIGHBORHOOD")
    if w3["new_side_materials"] < 4: blocked.append("W3_FOUR_REAL_SIDES_MISSING")
    if not w3["continuous_neighborhood_certified"]: blocked.append("W3_CONTINUOUS_NEIGHBORHOOD_MISSING")
    if not w3["accepted_newton_steps"]: blocked.append("NO_ACCEPTED_NEWTON_STEP")
    if not w3["final_heart_obj"]: blocked.append("NO_NEWTON_TERMINAL")
    if w2["train_splits_present"] or w2["formal_teacher_release"]: blocked.append("UNVERIFIED_UPSTREAM_RELEASE_CLAIM")
    return {
        "schema": "W0_M15_RELEASE_GATE_RESULT_V1",
        "observations_not_CI_or_native_proof": True,
        "branch_shas": {k: v["sha"] for k,v in branch.items()},
        "blockers": blocked,
        "status": "BLOCKED_INDEPENDENT_RELEASE_SEAL_MISSING",
        "historical_failure_preserved": True,
        "newton_admitted": False,
        "W5_real_teacher_admitted": False,
        "W6_real_teacher_admitted": False,
        "training_admitted": False
    }

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError("DO_NOT_OVERWRITE")
    result = audit(strict_json(args.snapshot.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["status"], len(result["blockers"]))
    return 3

if __name__ == "__main__":
    raise SystemExit(main())

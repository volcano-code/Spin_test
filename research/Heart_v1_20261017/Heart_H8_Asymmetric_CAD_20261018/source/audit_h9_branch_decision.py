"""H9: fail-closed replay of actual H8f Cherchi sample-60 construction evidence.

Reads the immutable Actions artifact 12135528290; never synthesizes Boolean
packets, reruns Newton, or treats finite-difference agreement as admission.
Only uses standard-library rational arithmetic and the frozen H7 diagnostics.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys
import zipfile

H7_SOURCE = Path(__file__).resolve().parents[2] / "Cherchi_H7" / "source"
sys.path.insert(0, str(H7_SOURCE))
from h7_planar_patch import (  # noqa: E402
    compare_observations, construction_features, exact_point, observe_packet, public_observation,
)

ZIP_SHA256 = "99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9"
REQUEST_SHA256 = "1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c"
REPORT_PREFIX = "artifacts/h8f-all81-points/"
REQUEST_PATH = "artifacts/h8-request/prepared-request.json"
CLASSIFICATION_PATH = "artifacts/h8f-81-exact-construction-classification.json"
REPORT_PATH = REPORT_PREFIX + "report.json"
REPLAY_INDICES = (0, 57, 59, 60, 62, 64)
BACKEND = "cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:"


def digest(data: bytes) -> str:
    return sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for buf in iter(lambda: stream.read(1 << 20), b""):
            h.update(buf)
    return h.hexdigest()


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(reason)


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def det4(a, b, c, d):
    """Exact signed 6x tetrahedron volume, zero iff four rational points coplanar."""
    u = tuple(b[k]-a[k] for k in range(3))
    v = tuple(c[k]-a[k] for k in range(3))
    w = tuple(d[k]-a[k] for k in range(3))
    return sum(x*y for x, y in zip(cross(u, v), w))


def sign(value):
    return (value > 0) - (value < 0)


def fraction_witness(value: Fraction):
    return {"sign": sign(value), "numerator": str(value.numerator),
            "denominator": str(value.denominator), "approx": float(value)}


def read_json(archive, path):
    return json.loads(archive.read(path))


def load_point(archive, index, source_request):
    name = REPORT_PREFIX + f"point-{index:03d}"
    point = read_json(archive, name + ".json")
    compressed = archive.read(name + "-material.json.gz")
    require(digest(compressed) == point.get("exact_same_call_material_archive_sha256"),
            f"MATERIAL_SHA256_MISMATCH_POINT_{index}")
    material = json.loads(gzip.decompress(compressed))
    require(point.get("index") == index and material.get("topology_hash") == point.get("feature_branch_hash")
            and material.get("geometry_hash") == point.get("material_geometry_hash")
            and material.get("quadric_coefficients") == point.get("coefficients"),
            f"POINT_OR_MATERIAL_IDENTITY_MISMATCH_{index}")
    require(str(material.get("boolean_backend_identity", "")).startswith(BACKEND)
            and material.get("material_proof", {}).get("schema") == "cherchi-same-call-material-v1",
            f"UNPINNED_OR_NON_EXACT_CHERCHI_MATERIAL_{index}")
    proof = material["material_proof"]
    require(len(proof["exact_vertices"]) == point["vertex_count"]
            and len(material["variable_faces"]) == point["triangle_count"]
            and len(proof["construction_records"]) == point["vertex_count"],
            f"POINT_CONSTRUCTION_SIZE_MISMATCH_{index}")
    packet = {"backend": "cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1",
              "exact_vertices": proof["exact_vertices"], "faces": material["variable_faces"],
              "construction_records": proof["construction_records"]}
    observation = observe_packet(packet, source_request["design_vertices"],
                                 source_request["design_faces"],
                                 material["quadric_source_vertices"], material["quadric_source_faces"])
    return point, material, observation


def diff_counts(base_material, trial_material, base_obs, trial_obs, design_vertices):
    bf, tf = base_material["variable_faces"], trial_material["variable_faces"]
    bc = base_material["material_proof"]["construction_records"]
    tc = trial_material["material_proof"]["construction_records"]
    require(len(bf) == len(tf) and len(bc) == len(tc), "NOT_A_SAME_SIZE_FACE_COMPARISON")
    changed_slots = [i for i, (x, y) in enumerate(zip(bf, tf)) if x != y]
    def indexed_features(m):
        packet = {"construction_records": m["material_proof"]["construction_records"],
                  "exact_vertices": m["material_proof"]["exact_vertices"]}
        return construction_features(packet, design_vertices, m["quadric_source_vertices"])
    changed_vertices = [i for i, (x, y) in enumerate(zip(indexed_features(base_material),
                             indexed_features(trial_material))) if x != y]
    removed = Counter(base_obs["_features"]) - Counter(trial_obs["_features"])
    added = Counter(trial_obs["_features"]) - Counter(base_obs["_features"])
    absent_triangles = Counter(base_obs["_triangles"]) - Counter(trial_obs["_triangles"])
    novel_triangles = Counter(trial_obs["_triangles"]) - Counter(base_obs["_triangles"])
    return {"changed_face_slot_count": len(changed_slots), "first_changed_face_slots": changed_slots[:20],
            "changed_feature_vertex_slots": changed_vertices,
            "removed_construction_features": [list(x) for x in sorted(removed.elements())],
            "added_construction_features": [list(x) for x in sorted(added.elements())],
            "removed_semantic_triangles": sum(absent_triangles.values()),
            "added_semantic_triangles": sum(novel_triangles.values()),
            "unoriented_index_triangle_symmetric_difference": len(set(map(lambda f: tuple(sorted(f)), bf))
                 ^ set(map(lambda f: tuple(sorted(f)), tf))),
            "raw_face_count_same": len(bf) == len(tf), "raw_vertex_count_same": len(bc) == len(tc)}


def rational_plane_witness(source, design, constructed):
    source_old = det4(source[24], source[90], source[151], constructed[8043])
    source_new = det4(source[24], source[89], source[90], constructed[8043])
    design_old = det4(design[5517], design[5518], design[5523], constructed[8044])
    design_new = det4(design[5516], design[5517], design[5518], constructed[8044])
    source_4pt = det4(source[24], source[90], source[151], source[89])
    design_4pt = det4(design[5516], design[5517], design[5518], design[5523])
    require(source_new == 0 and source_old != 0 and design_new == 0 and design_old != 0
            and source_4pt != 0 and design_4pt != 0,
            "NO_EXACT_NONCOPLANAR_LPI_SWITCH_WITNESS")
    return {"candidate_source_facets": [[24, 90, 151], [24, 89, 90]],
            "candidate_design_facets": [[5517, 5518, 5523], [5516, 5517, 5518]],
            "trial_lpi_8043_on_new_source_facet": fraction_witness(source_new),
            "trial_lpi_8043_off_old_source_facet": fraction_witness(source_old),
            "trial_lpi_8044_on_new_design_facet": fraction_witness(design_new),
            "trial_lpi_8044_off_old_design_facet": fraction_witness(design_old),
            "source_four_point_non_coplanarity": fraction_witness(source_4pt),
            "design_four_point_non_coplanarity": fraction_witness(design_4pt)}


def replay(artifact: Path):
    require(file_digest(artifact) == ZIP_SHA256, "NOT_FROZEN_ACTIONS_ARTIFACT_ZIP_SHA256")
    with zipfile.ZipFile(artifact) as archive:
        request_bytes = archive.read(REQUEST_PATH)
        require(digest(request_bytes) == REQUEST_SHA256, "NOT_FROZEN_REQUEST_SHA256")
        request = json.loads(request_bytes)
        report = read_json(archive, REPORT_PATH)
        classification = read_json(archive, CLASSIFICATION_PATH)
        require(request.get("schema") == "spin-heart-h8-faster-preparation-v1"
                and request.get("evidence", {}).get("scope") == "H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED",
                "NOT_FROZEN_HEART_H8_REQUEST")
        require(report.get("input_request_sha256") == REQUEST_SHA256
                and report.get("completed_samples") == 81
                and report.get("all_tested_stencils_same_feature_hash") is False
                and report.get("changed_feature_hash_points") == 17
                and report.get("all_same_call_material_snapshots_sha256_saved") is True
                and report.get("all_numerical_checks_passed") is True
                and len(report.get("numeric_checks", [])) == 30
                and all(x["numerical_passed"] for x in report["numeric_checks"])
                and report.get("qualified_branch_neighborhood") is False
                and report.get("formal_newton_converged") is False,
                "NOT_FAILED_H8F_81_POINT_NUMERIC_EVIDENCE")
        require(classification.get("complete_material_snapshots_verified") == 81
                and classification.get("request_sha256") == REQUEST_SHA256
                and classification.get("source_report_sha256") == digest(archive.read(REPORT_PATH))
                and classification.get("certified_smooth_neighborhood") is False
                and classification.get("certified_newton_direction") is False
                and classification.get("classifications") == {
                    "CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE": 1,
                    "SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED": 79}
                and [x["index"] for x in classification["comparisons"] if x["status"] !=
                     "SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED"] == [60],
                "NOT_FROZEN_SAMPLE_60_UNIQUE_ANOMALY")
        points = {}; materials = {}; obs = {}
        for i in REPLAY_INDICES:
            points[i], materials[i], obs[i] = load_point(archive, i, request["request"])
            require(public_observation(obs[i]) == classification["witnesses"][i]["witness"],
                    f"INDEPENDENT_WITNESS_MISMATCH_{i}")
        comparisons = {}
        for i in REPLAY_INDICES[1:]:
            v = compare_observations(obs[0], obs[i])
            expected = next(x for x in classification["comparisons"] if x["index"] == i)
            require(all(v[k] == expected[k] for k in v), f"SAMPLE_COMPARISON_DRIFT_{i}")
            comparisons[str(i)] = {"coefficient_7": points[i]["coefficients"][7], **v}
        require(all(comparisons[str(i)]["status"] == "SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED"
                    for i in REPLAY_INDICES if i not in (0,60))
                and comparisons["60"]["status"] == "CONSTRUCTION_FEATURE_CHANGE_OR_COUNT_CHANGE",
                "REPLAY_BRANCH_OUTCOME_CHANGED")
        delta = diff_counts(materials[0], materials[60], obs[0], obs[60], request["request"]["design_vertices"])
        require(delta["changed_face_slot_count"] == 434
                and delta["changed_feature_vertex_slots"] == [8043, 8044, 8045, 8046, 8047]
                and len(delta["removed_construction_features"]) == 2
                and len(delta["added_construction_features"]) == 2,
                "SAMPLE_60_FIRST_DIFFERENCE_DRIFT")
        source = [exact_point(p) for p in materials[60]["quadric_source_vertices"]]
        design = [exact_point(p) for p in request["request"]["design_vertices"]]
        constructed = [exact_point(p) for p in materials[60]["material_proof"]["exact_vertices"]]
        proof = rational_plane_witness(source, design, constructed)
        return {
            "schema": "heart-h9-frozen-sample60-branch-decision-v1",
            "evidence": {"run_id": 39123384402, "historical_ci_conclusion": "failure",
                         "artifact_id": 12135528290, "artifact_zip_sha256": ZIP_SHA256,
                         "request_sha256": REQUEST_SHA256,
                         "source_81_point_report_sha256": digest(archive.read(REPORT_PATH)),
                         "source_81_point_classification_sha256": digest(archive.read(CLASSIFICATION_PATH)),
                         "replayed_material_sha256": {str(i): points[i]["exact_same_call_material_archive_sha256"]
                                                     for i in REPLAY_INDICES}},
            "frozen_eighty_one_point_status": {"completed_samples": 81, "numeric_fd_checks_passed": 30,
                         "only_exact_construction_outlier_index": 60,
                         "changed_opaque_feature_hash_points": report["changed_feature_hash_points"],
                         "qualified_smooth_neighborhood": False, "newton_converged": False},
            "replayed_indices": list(REPLAY_INDICES), "comparison_to_baseline": comparisons,
            "sample_60_first_difference": delta,
            "sample_60_exact_rational_counterexample": proof,
            "decision": "DENY_CHERCHI_FASTER_NEWTON_ADMISSION",
            "reason": "DIFFERENT_NONCOPLANAR_LPI_SOURCE_AND_DESIGN_SUPPORT_FACETS_AT_SAMPLE_60",
            "only_finite_samples_checked": True, "continuous_smooth_neighborhood_proven": False,
            "boolean_set_discontinuity_proven": False, "final_heart_obj_produced": False,
            "final_independently_integrated_physical_metrics_produced": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = replay(args.artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    print("H9_SAMPLE60_CONFIRMED_NONCOPLANAR_LPI_BRANCH_SWITCH_NEWTON_DENIED")
    print(json.dumps({"replayed": result["replayed_indices"],
                      "changed_face_slots": result["sample_60_first_difference"]["changed_face_slot_count"],
                      "removed_features": len(result["sample_60_first_difference"]["removed_construction_features"]),
                      "decision": result["decision"]}, sort_keys=True))


if __name__ == "__main__":
    main()

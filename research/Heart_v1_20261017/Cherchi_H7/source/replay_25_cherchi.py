"""H7b: strict 25-point replay of H6's *historical V4 proxy* using real Cherchi.

Requires separately installed SHA-matching native binaries. Nothing in this file
grants original Heart eval60 identity, neighborhood smoothness, or Newton success.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import gzip
import json
from pathlib import Path
import sys
import time

import numpy as np

H7 = Path(__file__).resolve().parents[1]
H6 = H7.parent / "Cherchi_H6"
sys.path.insert(0, str(H6 / "source"))
from heart_h6_authority import verify_v4_proxy
from heart_h6_cherchi_jacobian import planned_samples
from probe_h6_feature_branches import h as legacy_hash, packet_features
from h7_planar_patch import compare_observations, observe_packet, public_observation

BACKEND = "cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1"

def file_sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def source_fingerprint(source, faces):
    """Mirror every registered H6 source fact, not just counts."""
    return {
        "source_faces": legacy_hash(faces.tolist()),
        "source_normal_edges": legacy_hash(np.asarray(source["source_normal_edges"]).tolist()),
        "source_normal_vertices": legacy_hash(np.asarray(source["source_normal_vertices"]).tolist()),
        "source_projective_rays": legacy_hash(source["source_projective_rays"]),
        "source_face_caps": legacy_hash(np.asarray(source["face_is_cap"]).tolist()),
        "source_surface_type": str(source["surface_type"]),
        "source_radius": float(source["truncation_radius"]),
        "source_vertices": len(source["vertices"]),
        "source_faces_count": len(faces),
    }

def exact_rational_audit(native, packet):
    """Check rational topology; float OBJ validity is a separate export gate."""
    faces = np.asarray(packet["faces"], dtype=np.int32)
    verdict = dict(native.audit_exact_rational_triangle_boundary(
        packet["exact_vertices"], faces, "AnyNonzero"))
    essential = ("boundary_valid", "closed", "edge_manifold",
                 "vertex_manifold", "self_intersection_free",
                 "self_intersection_completed")
    if any(verdict.get(k) is not True for k in essential):
        raise ValueError("NATIVE_RATIONAL_MATERIAL_AUDIT_FAILED:" +
                         json.dumps({k: verdict.get(k) for k in essential}))
    if verdict.get("intersection_error") or verdict.get("intersecting_pairs") or verdict.get("degenerate_faces"):
        raise ValueError("NATIVE_RATIONAL_MATERIAL_INTERSECTION_OR_DEGENERACY")
    return {k: verdict.get(k) for k in essential}

def validate_reference(fixture, registration, features, native, cherchi, cols):
    doc, registered = verify_v4_proxy(fixture, registration)
    source = json.loads(Path(features).read_text())
    if (source.get("scope") != "HISTORICAL_V4_PROXY_ONLY_NOT_AUTHENTIC_EVAL60"
            or source.get("input_sha256") != file_sha(fixture)
            or source.get("registration_sha256") != file_sha(registration)
            or source.get("directions") != list(cols)
            or source.get("evaluated_points") != 25
            or len(source.get("rows", [])) != 25):
        raise ValueError("FROZEN_H6_FEATURE_REFERENCE_MISMATCH")
    expected = json.loads((H6 / "H6_STAGE_STATUS.json").read_text())
    hashes = {"native_core_sha256": file_sha(native.__file__),
              "native_cherchi_sha256": file_sha(cherchi.__file__)}
    if any(expected.get(k) != v for k, v in hashes.items()):
        raise ValueError("H6_HISTORICAL_NATIVE_BINARY_HASH_MISMATCH")
    return doc, registered, source, hashes

def replay(fixture, registration, features, output, archive_packets=True):
    import _make_it_stand as native
    import _cherchi_core_boolean as cherchi
    cols = [0, 4, 8]
    doc, registered, reference, hashes = validate_reference(
        fixture, registration, features, native, cherchi, cols)
    raw = doc["requests"][1]["request"]
    opts = doc["evaluator_settings"]
    design = np.asarray(raw["design_vertices"], dtype=np.float64)
    faces = np.asarray(raw["design_faces"], dtype=np.int32)
    origin = np.asarray(raw["target_origin"], dtype=np.float64)
    axes = np.asarray(raw["target_axes"], dtype=np.float64)
    target_design = (design - origin) @ axes.T
    settings = native.SpinTriangulationSettings()
    for k in ("icosphere_subdivisions", "maximum_radius_doublings",
              "truncation_radius", "algebraic_finite_map"):
        setattr(settings, k, opts[k])
    settings.maximum_icosphere_subdivisions = settings.icosphere_subdivisions
    settings.retain_fixed_normal_provenance = True
    settings.paper_projective_hyperboloid = True
    q = np.asarray(registered["event"]["quadric_coefficients"], dtype=np.float64)
    samples, _ = planned_samples(q, cols)
    if len(samples) != 25:
        raise ValueError("H6_25_POINT_LAYOUT_CHANGED")

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    observations, points, comparisons = [], [], []
    try:
        with (output / "events.jsonl").open("x", encoding="utf8") as stream:
            for index, coefficients in enumerate(samples):
                t0 = time.perf_counter()
                expected = reference["rows"][index]
                if expected.get("index") != index or coefficients.tolist() != expected["coefficients"]:
                    raise ValueError("H6_REGISTERED_SAMPLE_COEFFICIENTS_CHANGED:" + str(index))
                t = time.perf_counter()
                source = native.evaluate_spin_it_faster_source_motion(
                    coefficients, target_design, settings)
                source_seconds = time.perf_counter() - t
                if not source["defined"] or not source["side_selection_defined"]:
                    raise ValueError("H7_SOURCE_NOT_DEFINED:" + str(index))
                moving_vertices = (np.asarray(source["vertices"]) @ axes.T + origin)
                moving_faces = np.asarray(source["faces"], dtype=np.int32)
                operation = "intersection" if source["interior_is_positive"] else "difference"
                current_source = source_fingerprint(source, moving_faces)
                for name, value in current_source.items():
                    if expected[name] != value:
                        raise ValueError(f"H6_SOURCE_IDENTITY_DRIFT:{index}:{name}")

                t = time.perf_counter()
                packet = cherchi.boolean(design.tolist(), faces.tolist(),
                                         moving_vertices.tolist(), moving_faces.tolist(), operation)
                boolean_seconds = time.perf_counter() - t
                if packet.get("backend") != BACKEND:
                    raise ValueError("CHERCHI_BACKEND_MISMATCH_NO_FALLBACK")
                historical = packet_features(packet, design, moving_vertices, operation)
                for name in ("canonical_triangles", "constructed_vertex_features",
                             "geometric_faces", "geometric_vertices", "type_counts",
                             "input_operation"):
                    if historical[name] != expected[name]:
                        raise ValueError(f"H6_CHERCHI_FEATURE_DRIFT:{index}:{name}")

                t = time.perf_counter()
                audit = exact_rational_audit(native, packet)
                exact_audit_seconds = time.perf_counter() - t
                # Geometry/provenance ambiguity is evidence, not license to guess.
                t = time.perf_counter()
                observation = None
                unresolved = None
                try:
                    observation = observe_packet(packet, design.tolist(),
                        faces.tolist(), moving_vertices.tolist(), moving_faces.tolist())
                except (ValueError, KeyError, TypeError) as error:
                    unresolved = f"{type(error).__name__}: {error}"
                symbolic_seconds = time.perf_counter() - t
                observations.append(observation)
                if index > 0:
                    if observations[0] is None or observation is None:
                        result = dict(status="UNRESOLVED_EXACT_PATCH_CORRESPONDENCE",
                            qualified_smooth_derivative=False,
                            qualified_boolean_set_continuity=False,
                            exact_material_audit_performed=True)
                    else:
                        result = compare_observations(observations[0], observation)
                        result["exact_material_audit_performed"] = True
                    comparisons.append(dict(index=index, **result))

                archive_hash = None
                if archive_packets:
                    filename = output / f"cherchi-packet-{index:02d}.json.gz"
                    with gzip.open(filename, "wt", encoding="utf8") as writer:
                        json.dump({"packet": packet,
                                   "source_vertices": moving_vertices.tolist(),
                                   "source_faces": moving_faces.tolist(),
                                   "design_vertices": design.tolist(),
                                   "design_faces": faces.tolist(),
                                   "operation": operation}, writer, default=str)
                    archive_hash = file_sha(filename)
                row = dict(index=index,
                    seconds=time.perf_counter() - t0,
                    stage_seconds=dict(source=source_seconds, boolean=boolean_seconds,
                        exact_rational_audit=exact_audit_seconds,
                        symbolic_patch_classification=symbolic_seconds),
                    material_vertex_count=len(packet["exact_vertices"]),
                    material_face_count=len(packet["faces"]),
                    original_h6_fingerprints_verified=True,
                    exact_material_audit=audit,
                    symbolic_diagnostic=public_observation(observation) if observation else None,
                    symbolic_diagnostic_error=unresolved,
                    packet_archive_sha256=archive_hash)
                points.append(row)
                stream.write(json.dumps({"index":index,
                    "status":"ACTUAL_CHERCHI_H6_V4_PROXY_REPLAYED",
                    "symbolic_diagnostic_error":unresolved}) + "\n")
                stream.flush()
                print(f"H7b {index+1}/25 rational Cherchi audited", flush=True)
        report = dict(schema="heart-h7b-25point-real-cherchi-proxy-replay-v1",
            scope="HISTORICAL_V4_PROXY_NOT_ORIGINAL_EVAL60",
            original_eval60_verified=False, latest_source_recompiled=False,
            formal_heart_newton_converged=False, all_81_derivative_points_passed=False,
            qualified_smooth_derivative=False, qualified_boolean_set_continuity=False,
            native_hashes=hashes, h6_feature_sha256=file_sha(features),
            frozen_proxy_sha256=file_sha(fixture),
            frozen_registration_sha256=file_sha(registration),
            native_cherchi_calls=len(points),
            exact_material_audited_points=len(points),
            unresolved_symbolic_points=sum(x is None for x in observations),
            category_counts=dict(Counter(c["status"] for c in comparisons)),
            packet_archives_stored=archive_packets,
            points=points, comparisons=comparisons)
        with (output/"report.json").open("x") as f:
            json.dump(report,f,indent=2,allow_nan=False);f.write("\n")
        return report
    except Exception as error:
        with (output/"FAILURE.json").open("w") as f:
            json.dump({"complete":False,"type":type(error).__name__,"error":str(error),
                       "completed_points":len(points)},f,indent=2);f.write("\n")
        raise

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--archived-v4", type=Path, required=True)
    parser.add_argument("--registered-q", type=Path,
        default=H6/"input/registered-eval60-coefficients.json")
    parser.add_argument("--h6-features", type=Path,
        default=H6/"evidence/three-column-feature-classification.json")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-archive-packets", action="store_true")
    args = parser.parse_args()
    result = replay(args.archived_v4,args.registered_q,args.h6_features,args.output,
                    not args.no_archive_packets)
    print("H7b_CATEGORIES", json.dumps(result["category_counts"],sort_keys=True))

if __name__ == "__main__":
    main()

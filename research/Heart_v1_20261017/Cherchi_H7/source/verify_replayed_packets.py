"""Offline verifier of H7b's captured real Cherchi packets, NOT a native rerun.

Checks hashes, historical H6 fingerprints, exact packet identities, and symbolic
comparisons without assigning Boolean set equivalence or smoothness admission.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gzip
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parents[1]
H6 = HERE.parent / "Cherchi_H6"
sys.path.insert(0, str(H6 / "source"))
from probe_h6_feature_branches import packet_features
from h7_planar_patch import observe_packet, public_observation, compare_observations

def digest_file(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def verify_one_archive(path, recorded_sha, expected_h6=None, saved_witness=None):
    if not Path(path).is_file():
        raise ValueError("CAPTURED_CHERCHI_PACKET_SHA256_MISMATCH:ARCHIVE_MISSING")
    if not recorded_sha or len(recorded_sha)!=64 or digest_file(path)!=recorded_sha:
        raise ValueError("CAPTURED_CHERCHI_PACKET_SHA256_MISMATCH")
    with gzip.open(path,"rt",encoding="utf8") as fh:
        archived=json.load(fh)
    for field in ("packet","source_vertices","source_faces","design_vertices",
                  "design_faces","operation"):
        if field not in archived:
            raise ValueError("CAPTURED_CHERCHI_OPERAND_MISSING:" + field)
    packet=archived["packet"]
    if packet.get("backend") != "cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1":
        raise ValueError("ARCHIVED_BACKEND_NOT_PINNED_CHERCHI")
    if archived["operation"] not in ("intersection","difference"):
        raise ValueError("ARCHIVED_OPERATION_INVALID")
    if expected_h6 is not None:
        src=np.asarray(archived["source_vertices"],dtype=np.float64)
        old=packet_features(packet,np.asarray(archived["design_vertices"],dtype=np.float64),
                            src,archived["operation"])
        for name in ("canonical_triangles","constructed_vertex_features",
                     "geometric_faces","geometric_vertices","type_counts","input_operation"):
            if old[name] != expected_h6[name]:
                raise ValueError("CAPTURED_CHERCHI_H6_FINGERPRINT_MISMATCH:" + name)
    observation=None
    unresolved=None
    try:
        observation=observe_packet(packet,archived["design_vertices"],archived["design_faces"],
                    archived["source_vertices"],archived["source_faces"])
    except (ValueError,KeyError,TypeError) as exc:
        unresolved=f"{type(exc).__name__}: {exc}"
    if saved_witness != (public_observation(observation) if observation else None):
        raise ValueError("CAPTURED_CHERCHI_SYMBOLIC_WITNESS_MISMATCH")
    return observation,unresolved

def verify_report(report_path, features_path):
    report_path=Path(report_path);report=json.loads(report_path.read_text())
    ref=json.loads(Path(features_path).read_text())
    if report.get("schema")!="heart-h7b-25point-real-cherchi-proxy-replay-v1" or (
        report.get("scope")!="HISTORICAL_V4_PROXY_NOT_ORIGINAL_EVAL60"
        or report.get("original_eval60_verified") is not False
        or report.get("formal_heart_newton_converged") is not False
        or report.get("qualified_smooth_derivative") is not False
        or report.get("qualified_boolean_set_continuity") is not False):
        raise ValueError("FORBIDDEN_FORMAL_H7_REPLAY_CLAIM")
    if report.get("h6_feature_sha256")!=digest_file(features_path) or (
        ref.get("scope")!="HISTORICAL_V4_PROXY_ONLY_NOT_AUTHENTIC_EVAL60"
        or ref.get("evaluated_points")!=25):
        raise ValueError("H6_FEATURE_REPORT_IDENTITY_MISMATCH")
    if (report.get("native_cherchi_calls")!=25 or report.get("exact_material_audited_points")!=25
        or not report.get("packet_archives_stored")
        or len(report.get("points",[]))!=25
        or len(report.get("comparisons",[]))!=24):
        raise ValueError("H7b_INCOMPLETE_OR_UNARCHIVED_REPLAY")
    observations=[];unresolved_count=0
    for index,point in enumerate(report["points"]):
        if point.get("index")!=index or point.get("original_h6_fingerprints_verified") is not True:
            raise ValueError("H7b_SAMPLE_INDEX_OR_AUTHORITY_MISMATCH")
        audit=point.get("exact_material_audit",{})
        for key in ("boundary_valid","closed","edge_manifold",
                    "vertex_manifold","self_intersection_free","self_intersection_completed"):
            if audit.get(key) is not True:raise ValueError("STORED_RATIONAL_AUDIT_NOT_QUALIFIED")
        archive=report_path.parent / f"cherchi-packet-{index:02d}.json.gz"
        observation,error=verify_one_archive(archive,point["packet_archive_sha256"],
                              ref["rows"][index],point.get("symbolic_diagnostic"))
        if error!=point.get("symbolic_diagnostic_error"):
            raise ValueError("H7b_SYMBOLIC_ERROR_MISMATCH")
        unresolved_count+=observation is None
        observations.append(observation)
    categories=Counter()
    for i,item in enumerate(report["comparisons"],start=1):
        if item.get("index")!=i:raise ValueError("H7b_COMPARISON_ORDER_CHANGED")
        if observations[0] is None or observations[i] is None:
            status="UNRESOLVED_EXACT_PATCH_CORRESPONDENCE"
        else:
            recomputed=compare_observations(observations[0],observations[i])
            for key,value in recomputed.items():
                if key=="exact_material_audit_performed":continue
                if item.get(key)!=value:
                    raise ValueError("H7b_PATCH_COMPARISON_EVIDENCE_MISMATCH")
            status=recomputed["status"]
        if item.get("status")!=status or item.get("qualified_smooth_derivative") is not False:
            raise ValueError("H7b_PATCH_CLASSIFICATION_MISMATCH")
        categories[status]+=1
    if dict(categories)!=report.get("category_counts") or unresolved_count!=report.get("unresolved_symbolic_points"):
        raise ValueError("H7b_AGGREGATE_COUNTS_MISMATCH")
    return dict(schema="heart-h7b-offline-archive-verification-v1",
        historical_h6_proxy_only=True,read_all_25_archives=True,
        recorded_archive_sha256_verified=True,all_h6_feature_digests_matched=True,
        symbolic_comparisons_recomputed=True,
        native_geometry_audits_independently_rerun=False,
        original_eval60_authenticated=False,
        derivative_branch_qualified=False,counts=dict(categories),
        replay_report_sha256=digest_file(report_path))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--h6-features",type=Path,
        default=H6/"evidence/three-column-feature-classification.json")
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    verdict=verify_report(a.report,a.h6_features)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x") as f:json.dump(verdict,f,indent=2);f.write("\n")
    print("H7b_OFFLINE",json.dumps(verdict,sort_keys=True))

if __name__=="__main__":
    main()

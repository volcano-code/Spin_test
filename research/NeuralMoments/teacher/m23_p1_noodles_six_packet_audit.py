#!/usr/bin/env python3
"""Audit Noodles V7 six-packet identities across the frozen main snapshot and W2 M20.

This is deliberately an identity/receipt audit. It does not recreate absent
rational packet bytes, rerun CGAL, or certify the solids.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

SNAPSHOT_SHA256 = "f7cf4c2efbd32b9c19d33359471f0671aa2efae104d3aa912500157052f39980"
PACKETS = {
    "design": ("48e8d3008bba746823eafd9c3704b52d597595b802066450a921ecc0dcb7f611", 108804),
    "envelope": ("92f46d68025467961fcc8b2b52353b4a18c2a981a09ad654ad6af3fb128b73fd", 1280),
    "fixed": ("71f9df91fca12fde4f4f2c80dc26e2d1229e8209e09db46e680d0de7baee264a", 114942),
    "fixed-inside-envelope": ("a944da4e36e5fe386cee3b28e4acf5800fc3942cde4eb35ba54f5de626f55dc7", 107160),
    "fixed-outside-envelope": ("8c66f71da99773fbc9a76b4f82fc43c55816df1876b643634ae64768f72ba262", 35342),
    "initial": ("640877647134a54152a8e1f63c1f356d752e6c66f7913301580c1e85a356d83b", 36986),
}
SOURCE_MANIFEST_SHA = "67364abba55c74ccd377eef6174b8c96ee04e4af1aadbd7e505466bafabd2a3a"
BACKEND_SHA = "d6803f184047f6172b177b9f436b16f22cdb6a949126d1df88a5d084f3dd9df3"
CHAIN_RELATIONS = {
    "F_plus_D_equals_A": {"fixed": PACKETS["fixed"][0], "design": PACKETS["design"][0], "initial": PACKETS["initial"][0]},
    "K_plus_D_equals_E": {"fixed-inside-envelope": PACKETS["fixed-inside-envelope"][0], "design": PACKETS["design"][0], "envelope": PACKETS["envelope"][0]},
    "K_plus_R_equals_F": {"fixed-inside-envelope": PACKETS["fixed-inside-envelope"][0], "fixed-outside-envelope": PACKETS["fixed-outside-envelope"][0], "fixed": PACKETS["fixed"][0]},
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json_text(snapshot: dict, name: str) -> dict:
    raw = snapshot.get(name)
    if not isinstance(raw, str):
        raise ValueError("SNAPSHOT_MEMBER_MISSING:" + name)
    try:
        value = json.loads(raw)
    except Exception as exc:
        raise ValueError("SNAPSHOT_MEMBER_INVALID_JSON:" + name) from exc
    if not isinstance(value, dict):
        raise ValueError("SNAPSHOT_MEMBER_NOT_OBJECT:" + name)
    return value


def audit(snapshot_path: Path, m20_dag_path: Path, m20_preflight_path: Path) -> dict:
    snapshot_bytes = snapshot_path.read_bytes()
    if sha(snapshot_bytes) != SNAPSHOT_SHA256:
        raise ValueError("SOURCE_SNAPSHOT_SHA256_MISMATCH")
    snapshot = json.loads(snapshot_bytes)
    if not isinstance(snapshot, dict):
        raise ValueError("SOURCE_SNAPSHOT_SCHEMA_INVALID")

    construction = load_json_text(snapshot, "frozen-inputs/author-rational/construction.json")
    chain = load_json_text(snapshot, "frozen-inputs/author-rational/exact-chain-summary.json")
    stage = load_json_text(snapshot, "V7_STAGE_STATUS.json")
    manifest = load_json_text(snapshot, "frozen-parts-v7c/manifest.json")

    dag = json.loads(m20_dag_path.read_text())
    preflight = json.loads(m20_preflight_path.read_text())
    if construction.get("schema") != "noodles-v7-exact-cgal-input-construction":
        raise ValueError("V7_CONSTRUCTION_SCHEMA_MISMATCH")
    if construction.get("status") != "EXACT_INPUT_CONSTRUCTED_NOT_OPTIMIZED":
        raise ValueError("V7_CONSTRUCTION_STATUS_MISMATCH")
    if construction.get("manifest_sha") != SOURCE_MANIFEST_SHA or dag.get("source_manifest_sha256") != SOURCE_MANIFEST_SHA:
        raise ValueError("SOURCE_MANIFEST_IDENTITY_MISMATCH")
    if construction.get("backend_sha") != BACKEND_SHA or dag.get("historical_backend_sha256") != BACKEND_SHA:
        raise ValueError("CGAL_BACKEND_IDENTITY_MISMATCH")
    if construction.get("csg_executed_current_process") != 96 or dag.get("expected_exact_backend_operations") != 96:
        raise ValueError("CSG_OPERATION_COUNT_MISMATCH")
    if dag.get("fixed_union_operations") != 92 or dag.get("final_CSG_operations") != 4:
        raise ValueError("CSG_DAG_SHAPE_MISMATCH")
    if dag.get("input_parts_total") != 94 or dag.get("fixed_source_parts") != 93:
        raise ValueError("SOURCE_PART_COUNT_MISMATCH")

    expected = dag.get("expected_historical_outputs")
    preflight_expected = {x["name"]: (x["sha256"], x["faces"]) for x in preflight.get("historic_6_outputs_expected", [])}
    outputs = construction.get("outputs")
    if not isinstance(expected, dict) or not isinstance(outputs, dict):
        raise ValueError("OUTPUT_IDENTITY_TABLE_MISSING")
    if set(expected) != set(PACKETS) or set(outputs) != set(PACKETS) or set(preflight_expected) != set(PACKETS):
        raise ValueError("SIX_PACKET_SET_MISMATCH")

    rows = {}
    for name, (digest, faces) in PACKETS.items():
        c = outputs[name]
        d = expected[name]
        p_sha, p_faces = preflight_expected[name]
        if (c.get("sha"), c.get("faces")) != (digest, faces):
            raise ValueError("V7_CONSTRUCTION_PACKET_IDENTITY_MISMATCH:" + name)
        if (d.get("sha256"), d.get("triangles")) != (digest, faces):
            raise ValueError("W2_M20_DAG_PACKET_IDENTITY_MISMATCH:" + name)
        if (p_sha, p_faces) != (digest, faces):
            raise ValueError("W2_M20_PREFLIGHT_PACKET_IDENTITY_MISMATCH:" + name)
        rows[name] = {"sha256": digest, "faces": faces, "identity_cross_match": True, "raw_packet_bytes_in_snapshot": False}

    if chain.get("all_three_chains_verified") is not True or chain.get("does_not_prove_native_solid_validity") is not True:
        raise ValueError("CHAIN_SUMMARY_STATUS_MISMATCH")
    results = {x.get("name"): x for x in chain.get("results", [])}
    if set(results) != set(CHAIN_RELATIONS):
        raise ValueError("CHAIN_RELATION_SET_MISMATCH")
    for relation, inputs in CHAIN_RELATIONS.items():
        r = results[relation]
        if r.get("success") is not True or r.get("nonzero_support_planes") != 0 or r.get("exact_zero_area_triangles") != 0:
            raise ValueError("CHAIN_RELATION_NOT_PASSED:" + relation)
        if r.get("inputs") != inputs:
            raise ValueError("CHAIN_RELATION_INPUT_BINDING_MISMATCH:" + relation)

    packet_member_keys = [k for k in snapshot if k.endswith("-rational.json") or "/exact_v7c/" in k]
    author_original = manifest.get("spec", {}).get("author_original")
    if author_original is not False:
        raise ValueError("AUTHOR_CAD_CLASSIFICATION_CHANGED")
    if stage.get("classification") != "PAPER_PHOTO_GUIDED_RECONSTRUCTED_METHOD_VALIDATION_NOT_AUTHOR_CAD":
        raise ValueError("V7_STAGE_CLASSIFICATION_MISMATCH")

    return {
        "schema": "w2-m23-p1-noodles-six-packet-cross-branch-identity-audit-v1",
        "status": "SIX_PACKET_IDENTITIES_AND_THREE_EXACT_CHAIN_RECEIPTS_CROSS_MATCH_PACKET_BYTES_STILL_MISSING",
        "snapshot_sha256": SNAPSHOT_SHA256,
        "source_manifest_sha256": SOURCE_MANIFEST_SHA,
        "backend_sha256": BACKEND_SHA,
        "csg_operations_reported": 96,
        "source_parts": 94,
        "fixed_source_parts": 93,
        "packets": rows,
        "packet_count": len(rows),
        "raw_packet_payloads_in_snapshot": False,
        "snapshot_exact_v7c_payload_member_count": len(packet_member_keys),
        "chain_relations": {
            name: {"success": True, "nonzero_support_planes": 0, "exact_zero_area_triangles": 0, "inputs": inputs}
            for name, inputs in CHAIN_RELATIONS.items()
        },
        "chain_relation_count": len(CHAIN_RELATIONS),
        "author_original_cad": author_original,
        "native_solid_validity_proven_by_chain": False,
        "native_cherchi_calls_in_this_audit": 0,
        "J_D": None,
        "training_admitted": False,
        "next": "Recover six packet bytes from original experiment storage or rerun pinned CGAL DAG in a qualified local environment; then certify solids and binary64 F/D/A partition before a fresh Cherchi teacher request."
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--snapshot", type=Path, required=True)
    ap.add_argument("--m20-dag", type=Path, required=True)
    ap.add_argument("--m20-preflight", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        ap.error("REFUSE_OVERWRITE_EXISTING_OUTPUT")
    try:
        result = audit(args.snapshot, args.m20_dag, args.m20_preflight)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        ap.exit(2, "M23-P1 audit blocked: " + str(exc) + "\n")
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

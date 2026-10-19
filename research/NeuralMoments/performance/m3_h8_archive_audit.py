"""W1 M3: verify archived genuine H8c/H8e evidence without rerunning Cherchi.

Original H8e 25-point native-job FAILURE must never be overwritten.
Standalone, stdlib-only. Source identity != fresh solver acceptance.
"""
from __future__ import annotations
import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile

REQUEST_SHA = "1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c"
PACKET_SHA = "ba47a6d6f9fad2dce2569434bf9340252cceaeaf99c14a82df02b637092b6464"
POINT_SHA = "9538d11fbc180b7b96e7afe3dc98a6af1a5ddf074a680eb182f63517a48d72e3"
REQUEST = "artifacts/h8-request/prepared-request.json"
BASE = "artifacts/h8-cherchi-point/"
P25 = "artifacts/h8e-jacobian-cols0-4-8/"
FLAGS = ("boundary_valid", "closed", "edge_manifold", "vertex_manifold",
         "consistently_oriented", "component_orientations_valid",
         "self_intersection_completed", "self_intersection_free")

def digest(data):
    return sha256(data).hexdigest()

def member(z, path):
    hits = [entry for entry in z.infolist() if entry.filename == path]
    if len(hits) != 1 or hits[0].file_size > 10_000_000:
        raise ValueError("M3_MISSING_DUPLICATE_OR_OVERSIZED:" + path)
    return z.read(hits[0])

def verify(h8c_zip, h8e_zip):
    with ZipFile(h8c_zip) as a, ZipFile(h8e_zip) as b:
        reqs = [member(z, REQUEST) for z in (a,b)]
        if any(digest(raw) != REQUEST_SHA for raw in reqs):
            raise ValueError("M3_REQUEST_SHA_DRIFT")
        frozen = json.loads(reqs[0])
        if frozen["evidence"]["original_author_cad"] is not False:
            raise ValueError("M3_AUTHOR_CAD_SCOPE_DRIFT")
        origin = frozen["request"]["target_origin"]
        if (frozen["request"]["target_axes"] != [[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
                or origin[:2] != [0.,0.]):
            raise ValueError("M3_TARGET_FRAME_DRIFT")
        facts = json.loads(member(a, BASE+"result.json"))
        cert = json.loads(member(a, BASE+"exact-ten-moment-certificate.json"))
        record = json.loads(member(b, P25+"point-000.json"))
        report = json.loads(member(b, P25+"report.json"))
        old = member(a, BASE+"actual-cherchi-packet.json.gz")
        new = member(b, P25+"point-000-material.json.gz")
        if digest(old) != PACKET_SHA or digest(new) != POINT_SHA:
            raise ValueError("M3_MATERIAL_SHA_DRIFT")
        if cert["verified_actual_packet_sha256"] != PACKET_SHA or cert["pure_python_fraction_vs_native_gmp_max_ulp"] != 0:
            raise ValueError("M3_INDEPENDENT_TEN_PROOF_DRIFT")
        if record["exact_same_call_material_archive_sha256"] != POINT_SHA or record["independent_moments_max_scaled_error"] != 0:
            raise ValueError("M3_SAME_CALL_DRIFT")
        if any(facts["rational_material_boundary"].get(flag) is not True for flag in FLAGS):
            raise ValueError("M3_HISTORICAL_BOUNDARY_FAILURE")
        if (record["exact_native_material_boundary_passed"] is not True or
            report["production_cherchi_calls"] != 25 or report["completed_samples"] != 25 or
            report["all_tested_stencils_same_feature_hash"] is not False or
            report["changed_feature_hash_points"] != 8 or
            report["formal_newton_converged"] is not False):
            raise ValueError("M3_H8E_ORIGINAL_FAILURE_NOT_PRESERVED")
        for z in (a,b):
            for name, expected in facts["source_sha256"].items():
                if name not in ("initial_top.obj","fixed_shell.obj","design_domain.obj") or digest(member(z,"artifacts/h8-input/"+name)) != expected:
                    raise ValueError("M3_CAD_SHA_DRIFT:" + name)
        x = json.loads(gzip.decompress(old))
        y = json.loads(gzip.decompress(new))
        if (len(x["exact_vertices"]) != 8455 or len(x["faces"]) != 16910 or
            len(y["variable_rational_vertices"]) != 8455 or len(y["variable_faces"]) != 16910 or
            x["quadric_coefficients"] != y["quadric_coefficients"] or
            record["coefficients"] != y["quadric_coefficients"] or
            y["geometry_hash"] != record["material_geometry_hash"] or
            y["topology_hash"] != record["feature_branch_hash"]):
            raise ValueError("M3_SOURCE_TOPOLOGY_OR_Q_DRIFT")
        m = cert["variable_raw_ten_moments_normalized"]
        actual = record["production_variable_raw_moments"]
        oz = origin[2]
        target = [m[0],m[1],m[2],m[3]-oz*m[0],m[4],m[5],
                  m[6]-2*oz*m[3]+oz*oz*m[0],m[7]-oz*m[2],m[8]-oz*m[1],m[9]]
        error = max(abs(v-w) for v,w in zip(actual,target))
        if error > 1e-12:
            raise ValueError("M3_FRAME_PARITY_FAILURE")
        stages = report["stage_totals_seconds"]
        wall = report["wall_seconds"]
        if any(not isinstance(v,(int,float)) or v < 0 for v in stages.values()) or sum(stages.values()) > wall:
            raise ValueError("M3_EXCLUSIVE_TIME_INVALID")
        return dict(schema="w1-m3-real-h8-archived-evidence-v1",
                    scope="HISTORICAL_MATERIAL_ONLY_NOT_FRESH_NATIVE_SOLVE",
                    original_h8c_run_id=39118951636,original_h8e_run_id=39121571756,
                    frozen_request_sha256=REQUEST_SHA,
                    archived_h8c_packet_sha256=PACKET_SHA,
                    archived_h8e_point0_sha256=POINT_SHA,
                    archived_native_binary_sha256=facts["native_sha256"],
                    archived_cherchi_binary_sha256=facts["cherchi_sha256"],
                    same_q=True,vertices=8455,faces=16910,
                    frame_max_abs_error=error,original_25point_wall_seconds=wall,
                    isolated_stage_sum_seconds=sum(stages.values()),
                    unattributed_seconds=wall-sum(stages.values()),
                    prepare_arithmetic_boundary_seconds=stages["prepare_arithmetic_boundary"],
                    original_h8e25_ci_failure_preserved=True,
                    fresh_cherchi_boolean_calls=0,full_solver_speedup=None,
                    paper_speed_qualified=False)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--h8c",required=True,type=Path)
    p.add_argument("--h8e",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    if a.output.exists(): raise FileExistsError("M3_OUTPUT_ALREADY_EXISTS")
    try:
        result=verify(a.h8c,a.h8e)
    except Exception as exc:
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.with_suffix(".failure.json").write_text(json.dumps(
            {"status":"FAILED_CLOSED","error":str(exc)})+"\n")
        raise
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print("PASS_ARCHIVED_REAL_H8_EVIDENCE_ONLY")

if __name__=="__main__":
    main()

"""W0 M10: independent event-admission audit of a genuine FAILED H8f archive.

This is NOT an in-between native Cherchi evaluation or a certification of a
continuous parameter stratum. W3's inverse-Gauss root is a CONDITIONAL MODEL,
not a measured Cherchi event. No training/Newton release may follow this audit.

Usage (repository root):
 python -m research.NeuralMoments.contracts.h9_event_admission_m10 \
   --archive /path/to/verified-original-81.zip --output /new/path/m10.json
Optional W3 conditional certificate --w3-certificate /path/to/original.json is
verified against its frozen Git blob before its claims are cross-checked.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import gzip
from hashlib import sha1
import json
from pathlib import Path
import numpy as np

try:
    from .real_h8f_81_m9 import (
        ARCHIVE_SHA256, REPORT_SHA256, REQUEST_SHA256, CLASSIFICATION_SHA256,
        REPORT_PREFIX, SOURCE_PREFIX, STABLE, CHANGED,
        construction_transition, normalized_features,
    )
    from .real_h8e_archive_m8 import (
        ArchiveAuditError, require, open_pinned, read_json, read_member, digest_bytes,
    )
except ImportError:  # offline script may be imported directly during checks
    from real_h8f_81_m9 import (
        ARCHIVE_SHA256, REPORT_SHA256, REQUEST_SHA256, CLASSIFICATION_SHA256,
        REPORT_PREFIX, SOURCE_PREFIX, STABLE, CHANGED,
        construction_transition, normalized_features,
    )
    from real_h8e_archive_m8 import (
        ArchiveAuditError, require, open_pinned, read_json, read_member, digest_bytes,
    )

W3_BRANCH = "research/neuralmoments-w3-heart-h9-20261019"
W3_CERTIFICATE_BLOB_SHA1 = "213d0d7f7bfec6ffa293cfd735556d8b10316601"
W3_SURROGATE_BRACKET = (
    Fraction("16048198887747/7036874417766400000"),
    Fraction("40120497219369/17592186044416000000"),
)
W3_AFFECTED_VERTEX_INDICES = [8043, 8044, 8045, 8046, 8047]
SAMPLES = (0, 59, 60)
DESIGN_EDGE = (5517, 5518)
SOURCE_EDGE = (24, 90)


def fraction_float(x):
    """Treat original binary64 coordinates as exact rationals, never decimalize."""
    require(type(x) is float and np.isfinite(x), "INVALID_BINARY64_COORDINATE")
    return Fraction.from_float(x)


def point(row):
    require(isinstance(row, (list, tuple)) and len(row) == 3,
            "INVALID_POINT_SHAPE")
    return tuple(fraction_float(x) for x in row)


def subtract(a, b):
    return tuple(x-y for x,y in zip(a,b))


def dot(a,b):
    return sum((x*y for x,y in zip(a,b)), Fraction(0))


def determinant(a,b,c):
    return a[0]*(b[1]*c[2]-b[2]*c[1]) + a[1]*(b[2]*c[0]-b[0]*c[2]) + a[2]*(b[0]*c[1]-b[1]*c[0])


def exact_line_witness(source_edge, design_edge):
    """Signed coplanarity and nearest INFINITE-line geometry in exact ℚ.

    Parameter ranges 0<t,s<1 imply nearest infinite-line points lie in the
    respective segments. The lines at archived endpoints are skew, not
    intersecting: small positive squared distances do not imply an event.
    """
    s0,s1=map(point,source_edge)
    d0,d1=map(point,design_edge)
    u,v,w=subtract(s1,s0), subtract(d1,d0), subtract(s0,d0)
    oriented_det = determinant(u,v,w)  # W3 sign: + at 59, - at 60.
    a,b,c,d,e=dot(u,u),dot(u,v),dot(v,v),dot(u,w),dot(v,w)
    denom=a*c-b*b
    require(denom>0,"DEGENERATE_PARALLEL_EDGE_PAIR")
    t=(b*e-c*d)/denom
    s=(a*e-b*d)/denom
    delta=tuple(wi+t*ui-s*vi for wi,ui,vi in zip(w,u,v))
    distance2=dot(delta,delta)
    require(Fraction(0)<t<1 and Fraction(0)<s<1 and distance2>0,
            "EDGE_CLOSEST_POINT_NOT_INTERIOR_OR_ALREADY_INTERSECTING")
    return {"signed_determinant":f"{oriented_det.numerator}/{oriented_det.denominator}",
            "sign":(1 if oriented_det>0 else -1 if oriented_det<0 else 0),
            "det_approx":float(oriented_det),
            "source_edge_parameter":float(t),
            "design_edge_parameter":float(s),
            "infinite_lines_min_squared_distance":float(distance2),
            "source_edge_parameter_exact":f"{t.numerator}/{t.denominator}",
            "design_edge_parameter_exact":f"{s.numerator}/{s.denominator}"}


def midpoint_derivative_diagnostic(q_left,r_left,J_left,q_right,r_right,J_right):
    """ONLY archived secant/trapezoid diagnostic across changed combinatorics."""
    q_left,q_right=map(lambda x:np.asarray(x,dtype=float),(q_left,q_right))
    r_left,r_right=map(lambda x:np.asarray(x,dtype=float),(r_left,r_right))
    J_left,J_right=map(lambda x:np.asarray(x,dtype=float),(J_left,J_right))
    require(q_left.shape==q_right.shape==r_left.shape==r_right.shape==(10,) and
            J_left.shape==J_right.shape==(10,10) and
            all(np.isfinite(x).all() for x in (q_left,q_right,r_left,r_right,J_left,J_right)),
            "INVALID_SECANT_ARRAY_SHAPE_OR_VALUE")
    dq=q_right-q_left
    require(dq[7]>0 and np.count_nonzero(dq)==1,"NOT_AN_ISOLATED_C7_INTERVAL")
    sec=(r_right-r_left)/dq[7]
    midpoint=(J_left[:,7]+J_right[:,7])/2
    error=np.abs(sec-midpoint)
    scale=np.maximum(1.,np.maximum(np.abs(sec),np.abs(midpoint)))
    return {"step":float(dq[7]),"max_absolute_secant_minus_endpoint_J_average":float(error.max()),
            "max_scaled_secant_minus_endpoint_J_average":float((error/scale).max()),
            "endpoint_Jc_column7_l2_difference":float(np.linalg.norm(J_right[:,7]-J_left[:,7])),
            "no_continuity_or_differentiability_certified":True}


def git_blob_sha1(raw):
    require(isinstance(raw,bytes),"W3_CERTIFICATE_MUST_BE_RAW_BYTES")
    return sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()


def verify_w3_surrogate_certificate(raw, *, expected_git_blob_sha1=W3_CERTIFICATE_BLOB_SHA1, native_witness=None):
    """Authenticate W3 authored conditional result, never make it a native fact."""
    require(git_blob_sha1(raw)==expected_git_blob_sha1,"W3_CERTIFICATE_GIT_BLOB_MISMATCH")
    doc=read_json(raw)
    require(doc.get("schema")=="heart-h9-native-endpoints-and-conditional-interior-event-v1"
            and doc.get("scope")=="REAL_NATIVE_BINARY64_FINITE_ENDPOINTS_AND_FIXED_NORMAL_ANALYTIC_SURROGATE_ONLY"
            and doc.get("real_native_endpoint_indices")==[59,60]
            and doc.get("input_design_edge")==list(DESIGN_EDGE)
            and doc.get("input_source_edge")==list(SOURCE_EDGE)
            and doc.get("historical_run_conclusion")=="failure"
            and doc.get("historical_run_id")==39123384402
            and doc.get("request_sha256")==REQUEST_SHA256
            and doc.get("artifact_sha256")==ARCHIVE_SHA256
            and doc.get("actual_native_cherchi_newton_accepted") is False
            and doc.get("final_heart_obj_produced") is False
            and doc.get("final_independently_integrated_metrics_available") is False
            and doc.get("full_coefficient_interval")==[1.5e-6,3e-6]
            and doc.get("conditional_analytic_interior_edge_crossing_certified") is True
            and type(doc.get("actual_in_between_native_boolean_samples_evaluated")) is int
            and doc.get("actual_in_between_native_boolean_samples_evaluated")==0
            and doc.get("native_production_continuity_or_topology_certified") is False
            and doc.get("newton_admitted") is False
            and doc.get("surrogate_root_exact_interval")==[str(x) for x in W3_SURROGATE_BRACKET],
            "W3_SURROGATE_SCOPE_OR_BRACKET_MISMATCH")
    if native_witness is not None:
        historical=doc.get("exact_native_binary64_projected_line_witnesses",{})
        require(set(historical)=={"59","60"},"W3_ENDPOINT_WITNESSES_MISSING")
        for key in ("59","60"):
            witness=native_witness[key]
            original=historical[key]
            for orig_key,calc_key in (("signed_determinant","signed_determinant"),
                                      ("source_parameter","source_edge_parameter_exact"),
                                      ("design_parameter","design_edge_parameter_exact")):
                datum=original[orig_key]
                from_w3=Fraction(int(datum["numerator"]),int(datum["denominator"]))
                require(from_w3==Fraction(witness[calc_key]),
                        "W3_ENDPOINT_WITNESS_INCOMPATIBLE_WITH_REAL_SOURCE:"+key+":"+orig_key)
    return {"W3_blob_sha1":git_blob_sha1(raw),"conditional_surrogate_valid":True,
            "in_between_native_samples":0,"real_native_root_certified":False,
            "native_endpoint_exact_values_crosschecked":native_witness is not None}


def _read_real_point(z, i, report):
    name=REPORT_PREFIX+f"point-{i:03d}"
    record=read_json(read_member(z,name+".json"))
    packed=read_member(z,name+"-material.json.gz",max_bytes=4_000_000)
    require(digest_bytes(packed)==record["exact_same_call_material_archive_sha256"],
            "ORIGINAL_NATIVE_MATERIAL_GZIP_SHA_MISMATCH")
    material=read_json(gzip.decompress(packed))
    require(record["index"]==i and material["quadric_coefficients"]==record["coefficients"]
            and material["geometry_hash"]==record["material_geometry_hash"]
            and material["topology_hash"]==record["feature_branch_hash"]
            and material["boolean_backend_identity"]==record["native_boolean_backend"]
             ==SOURCE_PREFIX+report["actual_cherchi_sha256"],
            "REAL_POINT_PROVENANCE_MISMATCH")
    require(np.asarray(material["moment_jacobian"],dtype=float).shape==(10,10),
            "REAL_POINT_JACOBIAN_MISSING")
    return record,material


def audit(original_zip, *, w3_certificate=None):
    """Validate original real left/right anchors, return DENY for all releases."""
    original_zip=Path(original_zip)
    require(original_zip.is_file() and not original_zip.is_symlink(),"MISSING_AUTHENTIC_ZIP")
    with open_pinned(original_zip,ARCHIVE_SHA256) as z:
        report_bytes=read_member(z,REPORT_PREFIX+"report.json")
        request_bytes=read_member(z,"artifacts/h8-request/prepared-request.json",max_bytes=10_000_000)
        classification_bytes=read_member(z,"artifacts/h8f-81-exact-construction-classification.json")
        require(digest_bytes(report_bytes)==REPORT_SHA256 and
                digest_bytes(request_bytes)==REQUEST_SHA256 and
                digest_bytes(classification_bytes)==CLASSIFICATION_SHA256,
                "ORIGINAL_REPORT_REQUEST_CLASSIFICATION_IDENTITY_DRIFT")
        report,request,classification=map(read_json,(report_bytes,request_bytes,classification_bytes))
        require(report["completed_samples"]==81 and report["production_cherchi_calls"]==81
                and report["all_numerical_checks_passed"] is True
                and report["complete_eighty_one_samples"] is False
                and report["qualified_branch_neighborhood"] is False
                and report["formal_newton_converged"] is False
                and classification["classifications"]=={STABLE:79,CHANGED:1}
                and classification["source_report_sha256"]==REPORT_SHA256
                and classification["certified_smooth_neighborhood"] is False,
                "HISTORICAL_FAILURE_NOT_PRESERVED")
        records={};materials={}
        for i in SAMPLES:
            records[i],materials[i]=_read_real_point(z,i,report)
    base,stable,changed=materials[0],materials[59],materials[60]
    require(not construction_transition(base,stable)["changed_vertex_indices"],
            "LEFT_NATIVE_SYMBOLIC_BRANCH_NOT_BASE")
    diff=construction_transition(base,changed)
    require(diff["changed_vertex_indices"]==W3_AFFECTED_VERTEX_INDICES
            and len(diff["removed_features"])==len(diff["added_features"])==2
            and diff["removed_oriented_triangles"]==diff["added_oriented_triangles"]==17
            and diff["same_source_faces"] is True
            and diff["normalized_symbolic_triangle_identity"] is False,
            "POINT60_EVENT_SYNTAX_WITNESS_CHANGED")
    frozen=request["request"]["design_vertices"]
    d_edges=[frozen[i] for i in DESIGN_EDGE]
    witness={i:exact_line_witness([materials[i]["quadric_source_vertices"][j] for j in SOURCE_EDGE],d_edges)
             for i in (59,60)}
    require(witness[59]["sign"]==1 and witness[60]["sign"]==-1,
            "ACTUAL_NATIVE_EXACT_SIGN_BRACKET_ABSENT")
    qbase=np.asarray(records[0]["coefficients"],dtype=float)
    left=float(records[59]["coefficients"][7]-qbase[7])
    right=float(records[60]["coefficients"][7]-qbase[7])
    require(left>0 and right>left and
            abs(left-1.5e-6)<1e-15 and abs(right-3.0e-6)<1e-15,
            "ORIGINAL_C7_SAMPLING_INTERVAL_CHANGED")
    require(Fraction.from_float(left)<W3_SURROGATE_BRACKET[0] < W3_SURROGATE_BRACKET[1]<Fraction.from_float(right),
            "W3_SURROGATE_ROOT_OUTSIDE_NATIVE_SAMPLE_INTERVAL")
    numeric=midpoint_derivative_diagnostic(
        records[59]["coefficients"],stable["variable_raw_moments"],stable["moment_jacobian"],
        records[60]["coefficients"],changed["variable_raw_moments"],changed["moment_jacobian"])
    require(numeric["max_scaled_secant_minus_endpoint_J_average"]<1e-7,
            "CROSS_EVENT_NUMERICAL_DIAGNOSTIC_THRESHOLD_EXCEEDED")
    independent_w3=None
    if w3_certificate is not None:
        p=Path(w3_certificate)
        require(p.is_file() and not p.is_symlink(),"INVALID_W3_CERTIFICATE_PATH")
        independent_w3=verify_w3_surrogate_certificate(p.read_bytes(),native_witness={str(k):witness[k] for k in (59,60)})
    return {"schema":"W0_M10_NATIVE_ENDPOINT_EVENT_ADMISSION_V1",
        "original_h8f_job":{"run":39123384402,"conclusion":"failure","artifact":12135528290,
                            "zip_sha256":ARCHIVE_SHA256,"source_commit":"0bcc187b3005478baa586a6d6f450e73811ca342"},
        "original_native_completed_points":81,"original_finite_difference_checks":30,
        "actual_new_in_between_native_samples":0,
        "literal_c7_interval_offsets":{"left":left,"right":right},
        "native_endpoint_exact_line_witness":{str(i):witness[i] for i in (59,60)},
        "surrogate_root_from_read_only_W3":{"branch":W3_BRANCH,
           "git_blob_sha1":W3_CERTIFICATE_BLOB_SHA1,
           "exact_interval":[str(x) for x in W3_SURROGATE_BRACKET],
           "approximate_midpoint":float(sum(W3_SURROGATE_BRACKET)/2),
           "conditional_only":True,"verified_against_supplied_W3_source":independent_w3 is not None,
           "certificate_evaluation":independent_w3},
        "real_archived_secant_Jc_diagnostic":numeric,
        "point60_structural_transition":{"changed_vertex_indices":diff["changed_vertex_indices"],
             "removed_feature_count":len(diff["removed_features"]),
             "added_feature_count":len(diff["added_features"]),
             "removed_oriented_triangles":diff["removed_oriented_triangles"],
             "added_oriented_triangles":diff["added_oriented_triangles"]},
        "asserted_scope":"TWO_REAL_NATIVE_ENDPOINTS_PLUS_W3_CONDITIONAL_SURROGATE",
        "actual_continuous_native_event_location_certified":False,
        "smooth_parameter_neighborhood_certified":False,
        "newton_admitted":False,
        "newton_terminal_certified":False,
        "training_admissible":False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive",type=Path,required=True)
    parser.add_argument("--w3-certificate",type=Path)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError("DO_NOT_OVERWRITE_EXISTING_EVIDENCE")
    record=audit(args.archive,w3_certificate=args.w3_certificate)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as dest:
        json.dump(record,dest,indent=2,sort_keys=True,allow_nan=False)
        dest.write('\n')
    print(record["schema"],"signed end points",[record["native_endpoint_exact_line_witness"][str(i)]["sign"] for i in (59,60)],"admit Newton",record["newton_admitted"])
    return 0


if __name__=="__main__":
    raise SystemExit(main())

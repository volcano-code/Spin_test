"""Fail-closed verifier for exact per-face Boolean arrangement certificates.

This module verifies a supplied exact planar cell decomposition. It does not
construct the arrangement and does not claim a real Heart global set proof
unless every input face has a complete, disjoint, classified cell partition.
"""
from fractions import Fraction
import hashlib
import json


def Q(x):
    if isinstance(x, bool) or isinstance(x, float):
        raise ValueError("EXACT_RATIONAL_TOKEN_REQUIRED")
    try:
        return Fraction(x)
    except Exception as exc:
        raise ValueError("INVALID_RATIONAL_TOKEN") from exc


def area2(poly):
    if not isinstance(poly, list) or len(poly) < 3:
        raise ValueError("CELL_POLYGON_INVALID")
    pts=[(Q(p[0]),Q(p[1])) for p in poly]
    s=Fraction(0)
    for i,p in enumerate(pts):
        q=pts[(i+1)%len(pts)]
        s += p[0]*q[1]-p[1]*q[0]
    if s == 0:
        raise ValueError("ZERO_AREA_CELL")
    return abs(s)


def canonical_sha(obj):
    raw=json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def verify_certificate(cert, expected_parent_ids, expected_output_face_ids):
    if cert.get("schema") != "w2-exact-boolean-arrangement-certificate-v1":
        raise ValueError("ARRANGEMENT_SCHEMA_MISMATCH")
    if cert.get("operation") != "DESIGN_MINUS_QUADRIC_SOURCE":
        raise ValueError("BOOLEAN_OPERATION_MISMATCH")
    parents=cert.get("parents")
    if not isinstance(parents,list):
        raise ValueError("PARENTS_REQUIRED")
    parent_ids=[p.get("parent_id") for p in parents]
    if len(parent_ids)!=len(set(parent_ids)) or set(parent_ids)!=set(expected_parent_ids):
        raise ValueError("PARENT_FACE_COVERAGE_INCOMPLETE")
    output_ids=cert.get("output_face_ids")
    if not isinstance(output_ids,list) or len(output_ids)!=len(set(output_ids)):
        raise ValueError("OUTPUT_FACE_ID_DUPLICATE_OR_MISSING")
    if set(output_ids)!=set(expected_output_face_ids):
        raise ValueError("OUTPUT_FACE_COVERAGE_INCOMPLETE")
    selected_area=Fraction(0)
    excluded_area=Fraction(0)
    cell_count=0
    seen_cells=set()
    for parent in parents:
        pid=parent["parent_id"]
        expected=Q(parent["parent_area2"])
        if expected<=0:
            raise ValueError("PARENT_AREA_INVALID")
        cells=parent.get("cells")
        if not isinstance(cells,list) or not cells:
            raise ValueError("PARENT_CELLS_MISSING")
        summed=Fraction(0)
        for cell in cells:
            cid=cell.get("cell_id")
            if not isinstance(cid,str) or not cid or (pid,cid) in seen_cells:
                raise ValueError("CELL_ID_INVALID_OR_DUPLICATE")
            seen_cells.add((pid,cid))
            a=area2(cell.get("polygon"))
            summed+=a
            classification=cell.get("membership")
            if classification not in ("INSIDE_DESIGN_OUTSIDE_QUADRIC",
                                      "INSIDE_DESIGN_INSIDE_QUADRIC",
                                      "OUTSIDE_DESIGN",
                                      "BOUNDARY_AMBIGUOUS"):
                raise ValueError("CELL_MEMBERSHIP_INVALID")
            if classification=="BOUNDARY_AMBIGUOUS":
                raise ValueError("ARRANGEMENT_CELL_NOT_OPEN_OR_UNRESOLVED")
            output=cell.get("output_face_ids")
            if not isinstance(output,list) or len(output)!=len(set(output)):
                raise ValueError("CELL_OUTPUT_BINDING_INVALID")
            if classification=="INSIDE_DESIGN_OUTSIDE_QUADRIC":
                if not output:
                    raise ValueError("EXPECTED_OUTPUT_CELL_MISSING")
                selected_area+=a
            else:
                if output:
                    raise ValueError("UNEXPECTED_OUTPUT_CELL_PRESENT")
                excluded_area+=a
            if any(x not in expected_output_face_ids for x in output):
                raise ValueError("UNKNOWN_OUTPUT_FACE_REFERENCE")
            cell_count+=1
        if summed != expected:
            raise ValueError("PARENT_ARRANGEMENT_AREA_NOT_EXACTLY_COVERED:"+str(pid))
    declared=cert.get("global_partition")
    if not isinstance(declared,dict):
        raise ValueError("GLOBAL_PARTITION_MISSING")
    if Q(declared.get("selected_area2"))!=selected_area:
        raise ValueError("SELECTED_AREA_TOTAL_MISMATCH")
    if Q(declared.get("excluded_area2"))!=excluded_area:
        raise ValueError("EXCLUDED_AREA_TOTAL_MISMATCH")
    if declared.get("cells")!=cell_count:
        raise ValueError("GLOBAL_CELL_COUNT_MISMATCH")
    return {
        "status":"EXACT_ARRANGEMENT_CERTIFICATE_INTERNAL_CONSISTENCY_PASS",
        "parents":len(parents),"cells":cell_count,
        "selected_area2":str(selected_area),
        "excluded_area2":str(excluded_area),
        "output_faces":len(output_ids),
        "certificate_sha256":canonical_sha(cert),
        "global_boolean_set_equality_proven":False,
        "reason":"This verifier checks certificate bookkeeping; the producer must independently prove cells are the complete arrangement of all exact triangle intersections and that output_face_ids tile each selected cell without overlap."
    }

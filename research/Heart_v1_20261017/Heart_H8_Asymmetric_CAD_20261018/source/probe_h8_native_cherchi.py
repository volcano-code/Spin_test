"""H8 reconstructed Heart: native-boundary + REAL Cherchi single-q preflight.

No Newton, 81-point finite differences, manufacturing, or author-CAD claim.
A run fails closed and archives failure evidence when any stage rejects data.
Requires freshly compiled native _make_it_stand / pinned _cherchi_core_boolean.
"""
from __future__ import annotations
import argparse
import gzip
from hashlib import sha256
import json
from pathlib import Path
import time
import traceback

import numpy as np

CHERCHI = "cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1"
FACES = ("initial_top.obj", "fixed_shell.obj", "design_domain.obj")
AUDIT_REQUIRED = (
    "boundary_valid", "closed", "edge_manifold", "vertex_manifold",
    "consistently_oriented", "component_orientations_valid",
    "self_intersection_completed", "self_intersection_free"
)

def sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()

def initial_ellipsoid_q(pivot, *, radius=0.70, center_model=(0.27, 0., 1.18)):
    """One registered exploratory sphere, expressed in actual target frame.

    beta(x) = ||x - center||^2 - radius^2.
    Basis: (1,x,y,z,x²,y²,z²,yz,xz,xy); no algorithm/answer warm start.
    """
    pivot = np.asarray(pivot, dtype=np.float64)
    center = np.asarray(center_model, dtype=np.float64) - pivot
    if pivot.shape!=(3,) or center.shape!=(3,) or not np.isfinite(center).all():
        raise ValueError("BAD_TARGET_FRAME")
    raw = np.array([np.dot(center, center)-radius**2, *(-2*center),
                    1., 1., 1., 0., 0., 0.], dtype=np.float64)
    q = raw / np.linalg.norm(raw)
    if abs(np.linalg.norm(q)-1.)>1e-12:
        raise ValueError("QUADRIC_NOT_UNIT_NORM")
    return q

def request_from_frozen(request_file):
    from make_it_stand import spin
    document=json.loads(Path(request_file).read_text())
    if document.get("schema")!="spin-heart-h8-faster-preparation-v1":
        raise ValueError("NOT_FROZEN_H8_RECONSTRUCTED_REQUEST")
    evidence=document.get("evidence",{})
    if (evidence.get("scope")!="H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED"
            or evidence.get("native_exact_boundary_admitted") is not False
            or evidence.get("newton_converged") is not False
            or evidence.get("original_author_cad") is not False):
        raise ValueError("H8_HISTORICAL_SCOPE_MISLABELED")
    payload=dict(document["request"])
    payload["settings"]=spin.SpinSolverConfig(**payload["settings"])
    request=spin.SpinItFasterRequest(**payload)
    settings=spin.SpinEvaluatorConfig(**document["evaluator_settings"])
    if request.mode!="SPINNING_TOP" or settings.derivative_method!="DISCRETE_FULL_RANK_QUADRIC":
        raise ValueError("INVALID_FASTER_HEART_PROFILE")
    if settings.icosphere_subdivisions!=2 or not settings.paper_projective_hyperboloid:
        raise ValueError("H8_SOURCE_PROFILE_CHANGED")
    return request,settings,evidence

def verified_native_boundary(native,vertices,faces,label):
    matrix=np.asarray(vertices,dtype=np.float64)
    faceids=np.asarray(faces,dtype=np.int32)
    if matrix.ndim!=2 or matrix.shape[1]!=3 or faceids.ndim!=2 or faceids.shape[1]!=3:
        raise ValueError("INVALID_NATIVE_BOUNDARY_SHAPE:"+label)
    start=time.perf_counter()
    facts=dict(native.audit_exact_triangle_boundary(matrix,faceids,"AnyNonzero"))
    summary={k:facts.get(k) for k in AUDIT_REQUIRED}
    summary.update(triangle_count=len(faceids),vertex_count=len(matrix),
                   seconds=time.perf_counter()-start,
                   intersecting_pair_count=len(facts.get("intersecting_pairs") or []))
    if (any(summary.get(k) is not True for k in AUDIT_REQUIRED)
            or summary["intersecting_pair_count"]!=0
            or facts.get("intersection_error") or facts.get("degenerate_faces")):
        raise ValueError("NATIVE_BOUNDARY_REJECTED:"+label+":"+json.dumps(summary))
    return summary

def rational_boundary(native,packet):
    start=time.perf_counter()
    facts=dict(native.audit_exact_rational_triangle_boundary(
        packet["exact_vertices"],np.asarray(packet["faces"],dtype=np.int32),"AnyNonzero"))
    result={k:facts.get(k) for k in AUDIT_REQUIRED}
    result["seconds"]=time.perf_counter()-start
    result["intersecting_pair_count"]=len(facts.get("intersecting_pairs") or [])
    if (any(result.get(k) is not True for k in AUDIT_REQUIRED)
            or result["intersecting_pair_count"] or facts.get("intersection_error")
            or facts.get("degenerate_faces")):
        raise ValueError("CHERCHI_RATIONAL_MATERIAL_BOUNDARY_REJECTED:"+json.dumps(result))
    return result

def probe(cad_dir, request_file, output):
    import _make_it_stand as native
    import _cherchi_core_boolean as cherchi
    import trimesh
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    stage="START"
    summary=dict(schema="heart-h8c-new-cad-real-cherchi-one-q-v1",
        scope="RECONSTRUCTED_NON_AUTHOR_CAD_ONLY",
        stages={},formal_newton_converged=False,
        jacobian_neighborhood_certified=False,full_81_point_protocol=False,
        physics_and_manufacturing_certified=False)
    try:
        stage="REQUEST_IDENTITY"
        request,settings,evidence=request_from_frozen(request_file)
        cad_dir=Path(cad_dir)
        manifest=json.loads((cad_dir/"H8_CAD_AUDIT.json").read_text())
        if (manifest.get("classification")!="PAPER_INSPIRED_RECONSTRUCTED_CAD_NOT_AUTHOR_CAD_NOT_OPTIMIZED"
            or manifest["parameters"]["length_mm"]!=25.
            or not (manifest["parameters"]["density_kg_m3"]>0)
            or abs(evidence["normalized_scale_mm_per_unit"]-25.)>1e-12):
            raise ValueError("CAD_FROZEN_IDENTITY_OR_UNITS_MISMATCH")
        scale=evidence["normalized_scale_mm_per_unit"]
        meshes={}
        for name in FACES:
            if sha(cad_dir/name)!=evidence["source_sha256"][name]:
                raise ValueError("CAD_OBJ_HASH_DRIFT:"+name)
            mesh=trimesh.load(cad_dir/name,force="mesh",process=False)
            meshes[name]=mesh
        summary["source_sha256"]={name:sha(cad_dir/name) for name in FACES}
        summary["frozen_request_sha256"]=sha(request_file)
        summary["native_sha256"]=sha(native.__file__)
        summary["cherchi_sha256"]=sha(cherchi.__file__)

        stage="NATIVE_ALL_BOUNDARY_ADMISSION"
        summary["native_boundaries"]={}
        for name in FACES:
            mesh=meshes[name]
            summary["native_boundaries"][name]=verified_native_boundary(
                native,mesh.vertices/scale,mesh.faces,name)
        summary["stages"]["input_boundaries"]="PASSED"

        stage="SOURCE_QUADRIC"
        axes=np.asarray(request.target_axes,dtype=np.float64)
        origin=np.asarray(request.target_origin,dtype=np.float64)
        design=np.asarray(request.design_vertices,dtype=np.float64)
        design_faces=np.asarray(request.design_faces,dtype=np.int32)
        q=initial_ellipsoid_q(origin)
        target_design=(design-origin)@axes.T
        signs=q[0]+(target_design@q[1:4])+np.sum(target_design**2*q[4:7],axis=1)
        if np.count_nonzero(signs>0)<40 or np.count_nonzero(signs<0)<40:
            raise ValueError("PROBE_ELLIPSOID_DOES_NOT_INTERSECT_DESIGN_DOMAIN")
        summary["exploratory_q"]=q.tolist()
        summary["design_samples_positive_beta"]=int(np.count_nonzero(signs>0))
        summary["design_samples_negative_beta"]=int(np.count_nonzero(signs<0))
        triangulation=native.SpinTriangulationSettings()
        for key in ("icosphere_subdivisions","maximum_icosphere_subdivisions",
                    "maximum_radius_doublings","truncation_radius",
                    "retain_fixed_normal_provenance","paper_projective_hyperboloid",
                    "algebraic_finite_map"):
            setattr(triangulation,key,getattr(settings,key))
        t=time.perf_counter()
        source=native.evaluate_spin_it_faster_source_motion(q,target_design,triangulation)
        summary["timing_source_seconds"]=time.perf_counter()-t
        if not source.get("defined") or not source.get("side_selection_defined"):
            raise ValueError("REAL_H8_SOURCE_REJECTED:"+str(source.get("diagnostic")))
        source_vertices=(np.asarray(source["vertices"])@axes.T+origin)
        source_faces=np.asarray(source["faces"],dtype=np.int32)
        summary["source_boundary"]=verified_native_boundary(native,source_vertices,source_faces,"source")
        operation="intersection" if source["interior_is_positive"] else "difference"
        summary["source_faces"]=len(source_faces)
        summary["boolean_operation"]=operation
        summary["stages"]["source"]="PASSED"

        stage="ACTUAL_CHERCHI_BOOLEAN"
        t=time.perf_counter()
        packet=cherchi.boolean(design.tolist(),design_faces.tolist(),
               source_vertices.tolist(),source_faces.tolist(),operation)
        summary["timing_cherchi_boolean_seconds"]=time.perf_counter()-t
        if packet.get("backend")!=CHERCHI:
            raise ValueError("CHERCHI_BACKEND_MISMATCH_NO_ALTERNATE")
        if len(packet["exact_vertices"])!=len(packet["vertices"]) or len(packet["faces"])<4:
            raise ValueError("CHERCHI_INVALID_MATERIAL_PACKET")
        summary["material_vertices"]=len(packet["exact_vertices"])
        summary["material_faces"]=len(packet["faces"])
        summary["stages"]["cherchi_boolean"]="PASSED"

        stage="INDEPENDENT_RATIONAL_MATERIAL_AUDIT"
        summary["rational_material_boundary"]=rational_boundary(native,packet)
        summary["stages"]["rational_boundary"]="PASSED"

        stage="ARCHIVE_NATIVE_PACKET"
        with gzip.open(output/"actual-cherchi-packet.json.gz","wt",encoding="utf8") as stream:
            json.dump({"backend":packet["backend"],"vertices":packet["vertices"],
                "exact_vertices":packet["exact_vertices"],"faces":packet["faces"],
                "construction_records":packet.get("construction_records"),
                "operation":operation,"quadric_coefficients":q.tolist()},stream,default=str)
        summary["actual_packet_archive_sha256"]=sha(output/"actual-cherchi-packet.json.gz")
        summary["status"]="ACTUAL_CHERCHI_ONE_POINT_RATIONAL_BOUNDARY_PASSED_NOT_OPTIMIZED"
        (output/"result.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
        print("H8_REAL_CHERCHI",json.dumps({k:summary[k] for k in (
            "status","material_vertices","material_faces",
            "timing_source_seconds","timing_cherchi_boolean_seconds")}),flush=True)
        return summary
    except Exception as error:
        summary.update(status="FAILED_NO_FORMAL_ADMISSION",failed_stage=stage,
            error=f"{type(error).__name__}: {error}",traceback=traceback.format_exc())
        (output/"failure.json").write_text(json.dumps(summary,indent=2,default=str)+"\n")
        raise

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--cad",type=Path,required=True)
    p.add_argument("--request",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    probe(a.cad,a.request,a.output)

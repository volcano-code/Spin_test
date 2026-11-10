#!/usr/bin/env python3
"""M29.3.2.2: diagnose discrete branch fingerprint changes with 13 fresh calls.

One fresh base-q evaluation plus +/- perturbations for directions 6,7,8 at
h=1e-5 and h=1e-6. No cached M9 material is used. Each call performs a new
Cherchi evaluation, same-call validation, exact boundary audit and independent
Fraction ten-moment verification. Serial and fail-closed.
"""
from __future__ import annotations
import argparse,gc,hashlib,json,math,os,resource,signal,sys,time
from pathlib import Path
import numpy as np

from m29_3_2_fd_math import tangent_basis,retract_unit
from m29_3_2_2_branch_fingerprint import fingerprint_components

MEMORY_FLOOR=6*1024**3
DISK_FLOOR=1*1024**3
CHERCHI_PREFIX="cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:"
COMPONENT_HASHES=(
 "source_faces_ordered_sha256","source_faces_oriented_set_sha256",
 "source_faces_unoriented_set_sha256","source_normal_edges_sha256",
 "construction_signature_sha256","output_feature_triangles_sha256")

def _mem_available():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"): return int(line.split()[1])*1024
    raise RuntimeError("M29_3_2_2_MEMAVAILABLE_UNAVAILABLE")

def _sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def _append(path,row):
    with Path(path).open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,sort_keys=True,allow_nan=False)+"\n")
        f.flush();os.fsync(f.fileno())

def _one(engine_type,request,settings,q,native,independent_ten_raw_moments,strict_audit):
    began=time.monotonic_ns()
    engine=engine_type(request,settings,normalization={"origin":[0.,0.,0.],"L":1.},
        branch_identity_policy="SOURCE_FEATURE_BRANCH_V2",
        rational_arithmetic_backend="NATIVE_GMP_SURFACE_V1",
        fixed_boundary_reuse=False,integral_profile="EXACT_GMP_V1")
    if not engine.backend_identity.startswith(CHERCHI_PREFIX):
        raise ValueError("M29_3_2_2_NON_PINNED_CHERCHI_BACKEND")
    evaluated=engine(q)
    material=engine.material(q)
    engine.validate_same_call_material(material,q,request)
    coords=material["variable_rational_vertices"]
    faces=np.asarray(material["variable_faces"],dtype=np.int32)
    flags=dict(native.audit_exact_rational_triangle_boundary(coords,faces,"AnyNonzero"))
    strict_audit(flags)
    ten=np.asarray(evaluated["variable_raw_moments"],dtype=np.float64)
    jac=np.asarray(evaluated["moment_jacobian"],dtype=np.float64)
    independent=np.asarray([float(x) for x in independent_ten_raw_moments(coords,faces.tolist())],dtype=np.float64)
    if ten.shape!=(10,) or jac.shape!=(10,10) or not np.isfinite(ten).all() or not np.isfinite(jac).all():
        raise ValueError("M29_3_2_2_INVALID_TEN_OR_JACOBIAN")
    err=float(np.max(np.abs(ten-independent)/np.maximum(1.,np.abs(independent))))
    if err>1e-10: raise ValueError("M29_3_2_2_INDEPENDENT_TEN_MISMATCH")
    last=engine.last;source=last["source"];records=last["resolved_construction_records"]
    source_faces=np.asarray(source["faces"]).tolist()
    source_edges=np.asarray(source["source_normal_edges"]).tolist()
    components=fingerprint_components(last["operation"],last["faces"],source_faces,
        source["surface_type"],source["cap_face_count"],source_edges,records)
    if components["recomputed_feature_branch_sha256"]!=evaluated["topology_hash"]:
        raise ValueError("M29_3_2_2_RECOMPUTED_BRANCH_HASH_MISMATCH")
    receipt={
      "q":[float(x) for x in q],"ten":[float(x) for x in ten],
      "geometry_hash":evaluated["geometry_hash"],"topology_hash":evaluated["topology_hash"],
      "components":components,"vertices":len(coords),"faces":len(faces),
      "independent_ten_max_scaled_error":err,
      "boundary_flags":{k:bool(flags.get(k)) for k in (
        "boundary_valid","closed","edge_manifold","vertex_manifold",
        "consistently_oriented","component_orientations_valid",
        "self_intersection_completed","self_intersection_free")},
      "elapsed_ns":time.monotonic_ns()-began}
    del material,evaluated,engine,coords,faces,independent,ten,jac
    gc.collect()
    return receipt

def run(root,archive,m9_run,output,steps=(1e-5,1e-6),directions=(6,7,8),max_seconds=2400):
    root=Path(root).resolve(strict=True);archive=Path(archive).resolve(strict=True)
    m9_run=Path(m9_run).resolve(strict=True);output=Path(output)
    if output.exists(): raise FileExistsError("M29_3_2_2_OUTPUT_EXISTS")
    mem=_mem_available()
    parent=output.parent if output.parent.exists() else Path.home()
    stat=os.statvfs(parent);disk=stat.f_bavail*stat.f_frsize
    if mem<MEMORY_FLOOR: raise RuntimeError("M29_3_2_2_AVAILABLE_MEMORY_BELOW_6_GIB")
    if disk<DISK_FLOOR: raise RuntimeError("M29_3_2_2_OUTPUT_DISK_BELOW_1_GIB")
    from m5_native_call_instrumentation import preflight,resource_guard,strict_audit,git_blob,SOURCE_BLOB,H8
    from m8_native_paired_gate import clone_paired_classes
    from m9_native_abba_gate import historic_h8c_anchor,model_to_target_identity_ten
    frozen=preflight(archive,root);limits=resource_guard()
    import _make_it_stand as native
    import _cherchi_core_boolean as boolean
    import _cherchi_rational_moments as arithmetic
    from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
    source_path=root/"python/make_it_stand/verification/cherchi_inprocess.py"
    if git_blob(source_path.read_bytes())!=SOURCE_BLOB:
        raise ValueError("M29_3_2_2_PRODUCTION_SOURCE_DRIFT")
    baseline=json.loads((m9_run/"baseline-performance.json").read_text())
    if baseline.get("schema")!="w1-m9-native-h8c-abba-v1" or not baseline.get("parity_and_timing",{}).get("pass_all_four_material_and_jacobian_parity"):
        raise ValueError("M29_3_2_2_M9_BASELINE_NOT_PASSED")
    expected=baseline.get("module_binary_sha256",{})
    actual={"native_sha256":_sha_file(native.__file__),
            "cherchi_sha256":_sha_file(boolean.__file__),
            "gmp_sha256":_sha_file(arithmetic.__file__)}
    if any(expected.get(k)!=v for k,v in actual.items()):
        raise ValueError("M29_3_2_2_NATIVE_MODULE_HASH_DRIFT")
    rows=baseline["measurements"]
    if len(rows)!=4 or [r["mode"] for r in rows]!=["original","candidate","candidate","original"]:
        raise ValueError("M29_3_2_2_M9_ABBA_ORDER_INVALID")
    base=rows[1]
    q,B=tangent_basis(np.asarray(base["q"],dtype=float))
    J=np.asarray(base["jacobian"],dtype=float)
    if np.linalg.matrix_rank(J@B)!=9: raise ValueError("M29_3_2_2_TANGENT_JACOBIAN_NOT_FULL_RANK")
    import tempfile
    output.mkdir(parents=True,exist_ok=False)
    samples_path=output/"samples.jsonl"
    started=time.monotonic();completed=0
    stage="PREPARE"
    try:
        with tempfile.TemporaryDirectory(prefix="w1-m29-3-2-2-") as td:
            req_path=Path(td)/"request.json";req_path.write_bytes(frozen)
            sys.path.insert(0,str(root/H8/"source"))
            from probe_h8_native_cherchi import initial_ellipsoid_q,request_from_frozen
            from verify_h8_exact_moments import independent_ten_raw_moments
            request,settings,evidence=request_from_frozen(req_path)
            if evidence.get("original_author_cad") is not False:
                raise ValueError("M29_3_2_2_CAD_SCOPE_DRIFT")
            q_expected=np.asarray(initial_ellipsoid_q(request.target_origin),dtype=float)
            if np.max(np.abs(q_expected-q))>1e-14:
                raise ValueError("M29_3_2_2_BASE_Q_MISMATCH")
            historic=historic_h8c_anchor(archive,expected_q=q.tolist())
            expected_ten=np.asarray(model_to_target_identity_ten(historic["model_moments"],
                request.target_origin,request.target_axes),dtype=float)
            if np.max(np.abs(np.asarray(base["ten"])-expected_ten))>1e-10:
                raise ValueError("M29_3_2_2_HISTORICAL_TEN_MISMATCH")
            old_ledger=__import__("m5_native_call_instrumentation").InclusiveExclusiveLedger()
            new_ledger=__import__("m5_native_call_instrumentation").InclusiveExclusiveLedger()
            Old,Candidate,labels,caches=clone_paired_classes(InProcessCherchiEvaluator,old_ledger,new_ledger)
            signal.signal(signal.SIGALRM,lambda signum,frame: (_ for _ in ()).throw(TimeoutError("M29_3_2_2_TIMEOUT")))
            signal.alarm(max_seconds)
            stage="FRESH_NATIVE_FEATURE_DIAGNOSTIC"
            base_receipt=_one(Candidate,request,settings,q,native,independent_ten_raw_moments,strict_audit)
            if base_receipt["topology_hash"]!=base["topology_hash"] or base_receipt["geometry_hash"]!=base["geometry_hash"]:
                raise ValueError("M29_3_2_2_FRESH_BASE_DIFFERS_FROM_M9")
            if np.max(np.abs(np.asarray(base_receipt["ten"])-np.asarray(base["ten"])))>1e-10:
                raise ValueError("M29_3_2_2_FRESH_BASE_TEN_DIFFERS_FROM_M9")
            base_components=base_receipt["components"]
            _append(samples_path,{"sample":"base","components":base_components,
                "topology_hash":base_receipt["topology_hash"],"geometry_hash":base_receipt["geometry_hash"],
                "q":base_receipt["q"],"ten":base_receipt["ten"]})
            completed+=1
            for h in steps:
                for j in directions:
                    if not 0<=int(j)<9: raise ValueError("M29_3_2_2_DIRECTION_OUT_OF_RANGE")
                    pair=[]
                    for side,sign in (("plus",1.),("minus",-1.)):
                        qp=retract_unit(q,sign*float(h)*B[:,int(j)])
                        receipt=_one(Candidate,request,settings,qp,native,independent_ten_raw_moments,strict_audit)
                        matches={k:receipt["components"].get(k)==base_components.get(k)
                                 for k in COMPONENT_HASHES}
                        matches["surface_type"]=receipt["components"]["surface_type"]==base_components["surface_type"]
                        matches["cap_face_count"]=receipt["components"]["cap_face_count"]==base_components["cap_face_count"]
                        receipt.update({"sample":"perturbation","step":float(h),"direction":int(j),
                            "side":side,"component_matches_base":matches,
                            "mismatch_components":[k for k,v in matches.items() if not v]})
                        _append(samples_path,receipt);pair.append(receipt);completed+=1
                    # Pair summary is a separate compact record; no mesh is persisted.
                    _append(samples_path,{"sample":"pair_summary","step":float(h),"direction":int(j),
                        "plus_mismatches":pair[0]["mismatch_components"],
                        "minus_mismatches":pair[1]["mismatch_components"],
                        "plus_minus_component_equal":{
                          k:pair[0]["components"].get(k)==pair[1]["components"].get(k)
                          for k in COMPONENT_HASHES}})
            all_rows=[json.loads(x) for x in samples_path.read_text().splitlines() if x.strip()]
            perturb=[x for x in all_rows if x.get("sample")=="perturbation"]
            mismatch_counts={k:sum(1 for x in perturb if not x["component_matches_base"].get(k,True))
                             for k in (*COMPONENT_HASHES,"surface_type","cap_face_count")}
            summary={"schema":"w1-m29-3-2-2-branch-component-diagnostic-v1",
              "status":"DIAGNOSTIC_COMPLETED_NOT_ADMITTED","fresh_native_evaluations":completed,
              "expected_fresh_native_evaluations":1+2*len(steps)*len(directions),
              "steps":[float(x) for x in steps],"directions":[int(x) for x in directions],
              "base_topology_hash":base_receipt["topology_hash"],
              "component_mismatch_counts_vs_base":mismatch_counts,
              "sample_count":len(perturb),"pair_summary_count":sum(1 for x in all_rows if x.get("sample")=="pair_summary"),
              "native_module_sha256":actual,"archive_sha256":baseline["archive_sha256"],
              "m9_baseline_run":str(m9_run),"memory_available_at_start_bytes":mem,
              "disk_free_at_start_bytes":disk,"resource_limits":limits,
              "elapsed_seconds":time.monotonic()-started,
              "formal_derivative_admission":False,"newton_admission":False,
              "full_solver_speedup":None,
              "interpretation":"Separates the discrete branch fingerprint into independently comparable components. Geometry hashes are recorded but deliberately excluded from branch equality."}
            (output/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n")
            print(json.dumps({"status":summary["status"],"fresh_native_evaluations":completed,
                "component_mismatch_counts_vs_base":mismatch_counts,"output":str(output)},indent=2))
            return summary
    except BaseException as exc:
        output.mkdir(parents=True,exist_ok=True)
        (output/"failure.json").write_text(json.dumps({"schema":"w1-m29-3-2-2-failure-v1",
            "status":"FAILED_CLOSED","stage":stage,"error":f"{type(exc).__name__}: {exc}",
            "completed_fresh_native_evaluations":completed,"formal_derivative_admission":False,
            "newton_admission":False,"full_solver_speedup":None},indent=2)+"\n")
        raise
    finally: signal.alarm(0)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--m9-run",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--steps",default="1e-5,1e-6")
    p.add_argument("--directions",default="6,7,8")
    p.add_argument("--max-seconds",type=int,default=2400)
    a=p.parse_args()
    result=run(a.root,a.archive,a.m9_run,a.output,
        tuple(float(x) for x in a.steps.split(",")),
        tuple(int(x) for x in a.directions.split(",")),a.max_seconds)
    if result["status"]!="DIAGNOSTIC_COMPLETED_NOT_ADMITTED": raise SystemExit(2)

if __name__=="__main__":main()

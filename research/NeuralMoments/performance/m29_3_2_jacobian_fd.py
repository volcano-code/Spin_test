#!/usr/bin/env python3
"""W1 M29.3.2: fresh-native central finite differences in the 9-D tangent space.

Runs serially and fail-closed. Every +/- perturbation constructs a fresh
InProcessCherchiEvaluator, performs a new source-motion + Cherchi Boolean +
moment/derivative evaluation, validates same-call material, exact boundary,
and an independent Fraction ten-moment integral. No M9 material cache is reused.
Only compact per-sample receipts are written; full mesh packets are not duplicated.
"""
from __future__ import annotations
import argparse, gc, hashlib, importlib.util, json, math, os, resource
from pathlib import Path
import signal, sys, time
from zipfile import ZipFile

import numpy as np

from m29_3_2_fd_math import tangent_basis, retract_unit, central_difference, compare_jacobians

STEPS_DEFAULT=(1e-3,1e-4,1e-5,1e-6)
MEMORY_FLOOR_BYTES=6*1024**3
DISK_FLOOR_BYTES=1*1024**3
CHERCHI_PREFIX="cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:"

def _sha_bytes(b):
    return hashlib.sha256(b).hexdigest()

def _sha_file(p):
    return _sha_bytes(Path(p).read_bytes())

def _mem_available():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1])*1024
    raise RuntimeError("M29_3_2_MEMAVAILABLE_UNAVAILABLE")

def _json_sha(value):
    return _sha_bytes(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode())

def _construction_signature(records):
    normalized=[]
    for record in records:
        operands=[]
        for operand in record.get("operands",[]):
            refs=[]
            for candidate in operand.get("source_vertices",[]):
                refs.append([candidate.get("input_object"),candidate.get("input_vertex")])
            operands.append({"status":operand.get("status"),"refs":sorted(refs)})
        normalized.append({"point_type":record.get("point_type"),"operands":operands})
    return normalized

def _sample(engine_type, request, settings, q, native, independent_ten_raw_moments, strict_audit):
    began=time.monotonic_ns()
    engine=engine_type(request,settings,normalization={"origin":[0.,0.,0.],"L":1.},
        branch_identity_policy="SOURCE_FEATURE_BRANCH_V2",
        rational_arithmetic_backend="NATIVE_GMP_SURFACE_V1",
        fixed_boundary_reuse=False,integral_profile="EXACT_GMP_V1")
    if not engine.backend_identity.startswith(CHERCHI_PREFIX):
        raise ValueError("M29_3_2_NON_PINNED_CHERCHI_BACKEND")
    evaluated=engine(q)
    material=engine.material(q)
    engine.validate_same_call_material(material,q,request)
    coords=material["variable_rational_vertices"]
    faces=np.asarray(material["variable_faces"],dtype=np.int32)
    flags=dict(native.audit_exact_rational_triangle_boundary(coords,faces,"AnyNonzero"))
    strict_audit(flags)
    ten=np.asarray(evaluated["variable_raw_moments"],dtype=np.float64)
    jac=np.asarray(evaluated["moment_jacobian"],dtype=np.float64)
    total=np.asarray(evaluated["raw_moments"],dtype=np.float64)
    independent=np.asarray([float(x) for x in independent_ten_raw_moments(coords,faces.tolist())],dtype=np.float64)
    if ten.shape!=(10,) or jac.shape!=(10,10) or total.shape!=(10,) or independent.shape!=(10,):
        raise ValueError("M29_3_2_BAD_TEN_OR_JACOBIAN_SHAPE")
    if not all(np.isfinite(x).all() for x in (ten,jac,total,independent)):
        raise ValueError("M29_3_2_NONFINITE_EVALUATION")
    scaled=float(np.max(np.abs(independent-ten)/np.maximum(1.0,np.abs(independent))))
    if scaled>1e-10:
        raise ValueError("M29_3_2_INDEPENDENT_TEN_MISMATCH")
    fixed=np.asarray(engine.fixed,dtype=np.float64)
    if fixed.shape!=(10,) or np.max(np.abs(total-(ten+fixed)))>1e-10:
        raise ValueError("M29_3_2_FIXED_MOMENT_IDENTITY_MISMATCH")
    last=engine.last
    source=last["source"]
    records=_construction_signature(last["resolved_construction_records"])
    source_edges=np.asarray(source["source_normal_edges"]).tolist()
    receipt={
      "q":[float(x) for x in q],
      "ten":[float(x) for x in ten],
      "geometry_hash":evaluated["geometry_hash"],
      "topology_hash":evaluated["topology_hash"],
      "operation":last["operation"],
      "surface_type":source["surface_type"],
      "cap_face_count":int(source["cap_face_count"]),
      "source_edges_sha256":_json_sha(source_edges),
      "construction_signature_sha256":_json_sha(records),
      "construction_record_count":len(records),
      "point_type_counts":{k:sum(1 for r in records if r["point_type"]==k)
                           for k in sorted({r["point_type"] for r in records})},
      "vertices":len(coords),"faces":len(faces),
      "independent_ten_max_scaled_error":scaled,
      "boundary_flags":{k:bool(flags.get(k)) for k in (
        "boundary_valid","closed","edge_manifold","vertex_manifold",
        "consistently_oriented","component_orientations_valid",
        "self_intersection_completed","self_intersection_free")},
      "elapsed_ns":time.monotonic_ns()-began,
    }
    del material,evaluated,engine,coords,faces,independent,ten,jac,total
    gc.collect()
    return receipt

def _append_jsonl(path,row):
    with Path(path).open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,sort_keys=True,allow_nan=False)+"\n")
        f.flush()
        os.fsync(f.fileno())

def run(root,archive,m9_run,output,steps=STEPS_DEFAULT,mode="candidate",max_seconds=3600,
        global_tol=1e-4,column_tol=1e-3):
    root=Path(root).resolve(strict=True);archive=Path(archive).resolve(strict=True)
    m9_run=Path(m9_run).resolve(strict=True);output=Path(output)
    if output.exists(): raise FileExistsError("M29_3_2_OUTPUT_ALREADY_EXISTS")
    steps=tuple(float(x) for x in steps)
    if not steps or any(not math.isfinite(x) or x<=0 for x in steps) or len(set(steps))!=len(steps):
        raise ValueError("M29_3_2_INVALID_STEP_LIST")
    if tuple(sorted(steps,reverse=True))!=steps:
        raise ValueError("M29_3_2_STEPS_MUST_BE_DESCENDING")
    if mode not in ("candidate","original"): raise ValueError("M29_3_2_INVALID_MODE")
    if type(max_seconds) is not int or not 1<=max_seconds<=7200:
        raise ValueError("M29_3_2_INVALID_TIME_LIMIT")
    mem=_mem_available()
    disk=os.statvfs(output.parent if output.parent.exists() else Path.home())
    disk_free=disk.f_bavail*disk.f_frsize
    if mem<MEMORY_FLOOR_BYTES:
        raise RuntimeError("M29_3_2_AVAILABLE_MEMORY_BELOW_6_GIB")
    if disk_free<DISK_FLOOR_BYTES:
        raise RuntimeError("M29_3_2_OUTPUT_DISK_BELOW_1_GIB")
    from m5_native_call_instrumentation import (
        preflight,resource_guard,strict_audit,git_blob,SOURCE_BLOB,H8,
        ARCHIVE_SHA,REQUEST_SHA)
    from m8_native_paired_gate import clone_paired_classes
    from m9_native_abba_gate import (
        historic_h8c_anchor,model_to_target_identity_ten)
    frozen=preflight(archive,root)
    limits=resource_guard()
    from make_it_stand.verification.cherchi_inprocess import (
        InProcessCherchiEvaluator,_json_value)
    source_path=Path(root/"python/make_it_stand/verification/cherchi_inprocess.py")
    if git_blob(source_path.read_bytes())!=SOURCE_BLOB:
        raise ValueError("M29_3_2_PRODUCTION_SOURCE_DRIFT")
    sys.path.insert(0,str(root/H8/"source"))
    from probe_h8_native_cherchi import initial_ellipsoid_q,request_from_frozen
    from verify_h8_exact_moments import independent_ten_raw_moments
    baseline_path=m9_run/"baseline-performance.json"
    baseline=json.loads(baseline_path.read_text())
    if baseline.get("schema")!="w1-m9-native-h8c-abba-v1":
        raise ValueError("M29_3_2_M9_BASELINE_SCHEMA_MISMATCH")
    # Refuse to compare against a Jacobian produced by different native ELF
    # binaries, even if the filenames and Python ABI still match.
    import _make_it_stand as native
    import _cherchi_core_boolean as boolean
    import _cherchi_rational_moments as arithmetic
    expected_modules=baseline.get("module_binary_sha256",{})
    actual_modules={
        "native_sha256":_sha_file(native.__file__),
        "cherchi_sha256":_sha_file(boolean.__file__),
        "gmp_sha256":_sha_file(arithmetic.__file__),
    }
    if any(expected_modules.get(k)!=v for k,v in actual_modules.items()):
        raise ValueError("M29_3_2_NATIVE_MODULE_SHA_DIFFERS_FROM_M9_BASELINE")
    if not baseline.get("parity_and_timing",{}).get("pass_all_four_material_and_jacobian_parity"):
        raise ValueError("M29_3_2_M9_ABBA_NOT_ADMITTED")
    measurements=baseline.get("measurements",[])
    if len(measurements)!=4 or [r.get("mode") for r in measurements]!=["original","candidate","candidate","original"]:
        raise ValueError("M29_3_2_M9_ABBA_MEASUREMENTS_INVALID")
    base_row=measurements[1] if mode=="candidate" else measurements[0]
    q_base=np.asarray(base_row["q"],dtype=np.float64)
    J=np.asarray(base_row["jacobian"],dtype=np.float64)
    if q_base.shape!=(10,) or J.shape!=(10,10) or not np.isfinite(J).all():
        raise ValueError("M29_3_2_M9_BASE_JACOBIAN_INVALID")
    q,B=tangent_basis(q_base)
    Jt=J@B
    if np.linalg.matrix_rank(Jt)!=9:
        raise ValueError("M29_3_2_TANGENT_JACOBIAN_NOT_FULL_COLUMN_RANK")
    if not np.isfinite(Jt).all():
        raise ValueError("M29_3_2_NONFINITE_TANGENT_JACOBIAN")
    output.mkdir(parents=True,exist_ok=False)
    stage="PREFLIGHT"
    completed=0
    start=time.monotonic()
    try:
        request_path_data=frozen
        import tempfile
        with tempfile.TemporaryDirectory(prefix="w1-m29-3-2-") as tmp:
            request_path=Path(tmp)/"prepared-request.json"
            request_path.write_bytes(request_path_data)
            request,settings,evidence=request_from_frozen(request_path)
            if evidence.get("original_author_cad") is not False:
                raise ValueError("M29_3_2_RECONSTRUCTED_CAD_SCOPE_DRIFT")
            q_check=np.asarray(initial_ellipsoid_q(request.target_origin),dtype=np.float64)
            if np.max(np.abs(q_check-q))>1e-14:
                raise ValueError("M29_3_2_BASE_Q_DIFFERS_FROM_FROZEN_REQUEST")
            historic=historic_h8c_anchor(archive,expected_q=q.tolist())
            expected=model_to_target_identity_ten(historic["model_moments"],
                request.target_origin,request.target_axes)
            historical_error=float(np.max(np.abs(np.asarray(base_row["ten"])-np.asarray(expected))))
            if historical_error>1e-10:
                raise ValueError("M29_3_2_BASE_TEN_HISTORICAL_REFERENCE_MISMATCH")
            old_ledger=__import__("m5_native_call_instrumentation").InclusiveExclusiveLedger()
            new_ledger=__import__("m5_native_call_instrumentation").InclusiveExclusiveLedger()
            Old,Candidate,labels,cache_stats=clone_paired_classes(
                InProcessCherchiEvaluator,old_ledger,new_ledger)
            engine_type=Candidate if mode=="candidate" else Old
            base_topology=base_row["topology_hash"]
            samples_path=output/"samples.jsonl"
            results_by_step={}
            def timeout_handler(signum,frame):
                raise TimeoutError("M29_3_2_NATIVE_FD_TIME_LIMIT")
            signal.signal(signal.SIGALRM,timeout_handler)
            signal.alarm(max_seconds)
            stage="FRESH_NATIVE_CENTRAL_DIFFERENCES"
            for h in steps:
                columns=[]
                for j in range(9):
                    plus_q=retract_unit(q,h*B[:,j])
                    minus_q=retract_unit(q,-h*B[:,j])
                    pair=[]
                    for side,qp in (("plus",plus_q),("minus",minus_q)):
                        receipt=_sample(engine_type,request,settings,qp,native,
                                        independent_ten_raw_moments,strict_audit)
                        receipt.update({"step":h,"direction":j,"side":side,"mode":mode,
                                        "topology_matches_base":receipt["topology_hash"]==base_topology})
                        _append_jsonl(samples_path,receipt)
                        pair.append(receipt)
                        completed+=1
                    pair_ok=all(x["topology_matches_base"] for x in pair)
                    pair_ok=pair_ok and pair[0]["topology_hash"]==pair[1]["topology_hash"]
                    if pair_ok:
                        columns.append(central_difference(pair[0]["ten"],pair[1]["ten"],h))
                    else:
                        columns.append(None)
                if all(x is not None for x in columns):
                    Jfd=np.column_stack(columns)
                    metrics=compare_jacobians(Jt,Jfd)
                    results_by_step[h]={"status":"BRANCH_STABLE","metrics":metrics,
                        "jacobian_fd":[[float(v) for v in row] for row in Jfd]}
                else:
                    results_by_step[h]={"status":"BRANCH_CHANGE_OR_INVALID_PAIR",
                        "valid_directions":sum(x is not None for x in columns),
                        "total_directions":9}
            refinements=[]
            valid_steps=[h for h in steps if results_by_step[h]["status"]=="BRANCH_STABLE"]
            for h0,h1 in zip(valid_steps,valid_steps[1:]):
                a=np.asarray(results_by_step[h0]["jacobian_fd"])
                b=np.asarray(results_by_step[h1]["jacobian_fd"])
                refinements.append({"coarse_step":h0,"fine_step":h1,
                    "relative_change":float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-15))})
            passing=[]
            for h in valid_steps:
                m=results_by_step[h]["metrics"]
                if (m["global_relative_frobenius_error"]<=global_tol and
                    m["max_column_relative_error"]<=column_tol):
                    passing.append(h)
            all_valid=len(valid_steps)==len(steps)
            status=("LOCAL_JACOBIAN_FD_WITHIN_TOLERANCE" if passing and all_valid
                    else "BRANCH_STABLE_BUT_FD_TOLERANCE_NOT_MET" if all_valid
                    else "BRANCH_CHANGE_DETECTED")
            summary={
              "schema":"w1-m29-3-2-fresh-native-tangent-fd-v1",
              "status":status,"mode":mode,"steps":list(steps),
              "fresh_native_function_evaluations":completed,
              "expected_function_evaluations":2*9*len(steps),
              "all_evaluations_independently_ten_verified":True,
              "all_evaluations_exact_boundary_audited":True,
              "all_steps_branch_stable":all_valid,
              "base_m9_run":str(m9_run),
              "base_m9_topology_hash":base_topology,
              "base_m9_material_sha256":base_row["material_sha256"],
              "base_q":q.tolist(),"tangent_basis":[[float(v) for v in row] for row in B],
              "analytic_tangent_jacobian":[[float(v) for v in row] for row in Jt],
              "historical_base_ten_max_abs_error":historical_error,
              "relative_tolerance_global":global_tol,
              "relative_tolerance_per_column":column_tol,
              "passing_steps":passing,"step_results":results_by_step,
              "refinement_between_valid_steps":refinements,
              "candidate_parser_cache_calls":len(cache_stats.calls) if mode=="candidate" else None,
              "candidate_parser_cache_all_cleared":(
                  len(cache_stats.calls)==completed and cache_stats.cache_info().currsize==0)
                  if mode=="candidate" else None,
              "native_module_sha256":{
                "_make_it_stand":_sha_file(native.__file__),
                "_cherchi_core_boolean":_sha_file(boolean.__file__),
                "_cherchi_rational_moments":_sha_file(arithmetic.__file__)},
              "archive_sha256":ARCHIVE_SHA,"request_sha256":REQUEST_SHA,
              "production_source_blob":SOURCE_BLOB,
              "memory_available_at_start_bytes":mem,"disk_free_at_start_bytes":disk_free,
              "resource_limits":limits,"elapsed_seconds":time.monotonic()-start,
              "formal_derivative_admission":False,"newton_admission":False,
              "full_solver_speedup":None,"paper_speed_qualified":False,
              "interpretation":"Local finite-difference evidence at one frozen q only; not a neighborhood proof or Newton admission."
            }
            (output/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+"\n")
            print(json.dumps({"status":status,"completed":completed,
                "passing_steps":passing,"elapsed_seconds":summary["elapsed_seconds"]},sort_keys=True))
            return summary
    except BaseException as exc:
        output.mkdir(parents=True,exist_ok=True)
        (output/"failure.json").write_text(json.dumps({
          "schema":"w1-m29-3-2-failure-v1","status":"FAILED_CLOSED",
          "stage":stage,"error":f"{type(exc).__name__}: {exc}",
          "completed_fresh_native_evaluations":completed,
          "full_solver_speedup":None,"formal_derivative_admission":False
        },indent=2,sort_keys=True)+"\n")
        raise
    finally:
        signal.alarm(0)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--m9-run",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--mode",choices=("candidate","original"),default="candidate")
    p.add_argument("--steps",default="1e-3,1e-4,1e-5,1e-6")
    p.add_argument("--max-seconds",type=int,default=3600)
    p.add_argument("--global-tolerance",type=float,default=1e-4)
    p.add_argument("--column-tolerance",type=float,default=1e-3)
    a=p.parse_args()
    steps=tuple(float(x) for x in a.steps.split(","))
    result=run(a.root,a.archive,a.m9_run,a.output,steps,a.mode,
               a.max_seconds,a.global_tolerance,a.column_tolerance)
    if result["status"]!="LOCAL_JACOBIAN_FD_WITHIN_TOLERANCE":
        raise SystemExit(2)

if __name__=="__main__":main()

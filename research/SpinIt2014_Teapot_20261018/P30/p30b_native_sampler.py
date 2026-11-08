#!/usr/bin/env python3
"""P30-B: approved-only, append-only, resumable real Cherchi 12-point pilot.

No public/private Python API here authorizes the sample on its own: two
independent, owner-branch tracked diagnostic approvals, P27 source/input pins,
the private P30 plan SHA, and a separately registered P30-B lock digest are
checked before EVERY real native worker. No Newton, no automatic training
release, no smooth-neighborhood certification.

Run only on the qualified 24GiB/swap0 P27-like Docker host after approvals.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

import p30_neighborhood_preflight as seed
import p30b_authority as auth
import p30b_moment_frame as moment_frame

SCHEMA = "W4_P30B_REAL_NATIVE_PROBE_RECEIPT_V2"
RUN_SCHEMA = "W4_P30B_APPEND_ONLY_PILOT_JOURNAL_V2"
PILOT_SCHEMA = "W4_P30B_PILOT_COLLECTION_V2"
CORE_SHA = "58fd12c1306c1c01679a19172e276eef0cb30542"
P30_MAX_SECONDS = 3600
POINT_MAX_SECONDS = 900
ADDRESS_BYTES = 24 * 1024**3
N_PILOT = 12
P20_REL = "research/SpinIt2014_Teapot_20261018/P1"
LOCK_NAME = "P21_PRERUN_LOCK.json"
PINS_NAME = "P20_NATIVE_SIX_PINS.json"
MODULES = {
    "_make_it_stand": "30409c25260355e63e827486ca058067e2a6bd312ac7d2c809e2f74c7454e413",
    "_cherchi_core_boolean": "e6913eea1db74305a37b00b7fbb23237134e76f04da5f1553d0ca903fde11e22",
    "_cherchi_rational_moments": "8deaf8b187f12f43ce0f9f955f59c38eeb997c82baf5586e4f05269bf1c87bfa",
}
CLOSED = dict(native_derivative_neighborhood_certified=False, W0_owner_admitted=False,
              W2_teacher_training_allowed=False, Newton_accepted=False,
              training_admissible=False, Faster_optimization_executed=False,
              MuJoCo_optimized_before_after_executed=False,
              independent_teacher_admission=False)

class SampleRejected(ValueError):
    pass

def need(condition, code):
    if not condition:
        raise SampleRejected(code)

def digest(b):
    return hashlib.sha256(b).hexdigest()

def new_json(path, data):
    path=Path(path)
    need(not path.exists() and not path.is_symlink() and
         not any(p.is_symlink() for p in path.parents), "OUTPUT_EXISTS_OR_SYMLINK")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as output:
        json.dump(data,output,indent=2,sort_keys=True,allow_nan=False)
        output.write("\n")

def sha(path):
    return digest(Path(path).read_bytes())

def resource_report():
    values={}
    for row in Path("/proc/meminfo").read_text().splitlines():
        parts=row.split()
        if len(parts)==3 and parts[1].isdigit():
            values[parts[0].rstrip(":")]=int(parts[1])*1024
    root=Path("/sys/fs/cgroup")
    cg={}
    for name in ("memory.max","memory.swap.max","memory.current","memory.peak"):
        p=root/name
        cg[name]=p.read_text().strip() if p.is_file() else None
    return {"physical_memory_bytes":values.get("MemTotal",0),
            "host_swap_bytes":values.get("SwapTotal",0),
            "host_available_bytes":values.get("MemAvailable",0),
            "cgroup":cg}

def require_real_resources(resources):
    need(resources["physical_memory_bytes"] >= 20 * 1024**3,
         "PHYSICAL_RAM_BELOW_20_GIB")
    need(resources["host_swap_bytes"] == 0, "HOST_SWAP_NOT_ZERO")
    need(resources["cgroup"]["memory.max"] == str(ADDRESS_BYTES),
         "P30B_REQUIRES_24_GIB_CGROUP")
    need(resources["cgroup"]["memory.swap.max"] == "0",
         "P30B_REQUIRES_CGROUP_ZERO_SWAP")

def read_auth_and_bind(a):
    """No native imports, no factory calls. Rechecked inside every child."""
    plan_raw=a.plan.read_bytes()
    need(digest(plan_raw)==auth.P30_PRIVATE_PLAN_SHA,
         "PRIVATE_P30_TANGENT_PLAN_SHA_MISMATCH")
    plan=auth.validate_plan(auth.strict_json(plan_raw))
    archive=seed.verify_archive(a.archive)
    rebuild=seed.plan(archive,step=plan["step_radians"])
    need(auth.canonical(rebuild)==auth.canonical(plan),
         "P30_PLAN_DIFFERS_FROM_P27_FORMAL_ARCHIVE")
    request=a.p20_request.read_bytes()
    need(digest(request)==auth.EXPECTED_REQUEST_SHA,
         "P20_REQUEST_SHA_CHANGED")
    approvals=auth.read_authorities(a.w0_review_root,a.w2_review_root)
    frame_report_path=a.w4_root/P20_REL/"P20_EXACT_FRAME_AND_PHYSICS_REPORT.json"
    frame_contract,frame_provenance=moment_frame.load_contract(a.p20_request,frame_report_path)
    readiness=auth.evaluate(plan,approvals,request,plan_raw,frame_contract,frame_provenance)
    need(readiness["status"]=="DIAGNOSTIC_PILOT_APPROVALS_PRESENT_NOT_EXECUTED",
         "INDEPENDENT_OWNER_TEACHER_PILOT_APPROVALS_MISSING")
    need(a.moment_coordinate_frame==readiness["moment_frame_binding"]["moment_coordinate_frame"],
         "REQUESTED_FRAME_DIFFERS_FROM_INDEPENDENT_W0_W2_APPROVALS")
    frame_meta=moment_frame.frame_metadata(frame_contract,frame_provenance,a.moment_coordinate_frame)
    for key,value in frame_meta.items():
        need(readiness["moment_frame_binding"].get(key)==value,
             "OWNER_LOCK_FRAME_BINDING_MISMATCH:"+key)
    registered_lock=a.registered_lock.read_bytes()
    need(digest(registered_lock)==a.external_lock_sha,
         "EXTERNAL_P30B_LOCK_SHA_MISMATCH")
    expected=auth.make_lock(readiness)
    locked=auth.strict_json(registered_lock)
    need(locked==expected and locked.get("scientific_admission") is False,
         "P30B_REGISTERED_LOCK_DIFFERS_FROM_CURRENT_APPROVALS")
    p27_lock=a.p27_run_dir / LOCK_NAME
    p27_pins=a.p27_run_dir / PINS_NAME
    need(sha(p27_lock)==seed.LOCK_SHA,
         "PRECOMMITTED_P27_LOCK_CHANGED")
    saved_pins=auth.strict_json(p27_pins.read_bytes())
    need(saved_pins==archive["pins"] and
         saved_pins["c_sha256"]==seed.C_SHA and
         saved_pins["context_sha256"]==plan["evidence"]["evaluator_context_sha256"],
         "P27_SIX_REAL_NATIVE_PINS_CHANGED")
    need(auth.git(a.w0_source_root.resolve(strict=True),"rev-parse","HEAD")==auth.EXPECTED_W0_FROZEN,
         "W0_FROZEN_SOURCE_COMMIT_CHANGED")
    need(auth.git(a.core_root.resolve(strict=True),"rev-parse","HEAD")==CORE_SHA,
         "CORE_FROZEN_SOURCE_COMMIT_CHANGED")
    need((a.w4_root/P20_REL/"P20_native_request.json").read_bytes()==request,
         "W4_P20_REQUEST_NO_LONGER_IDENTICAL")
    return {"plan":plan,"archive":archive,"approvals":approvals,
            "readiness":readiness,"expected_lock":expected,"pins":saved_pins,
            "frame_contract":frame_contract,"frame_provenance":frame_provenance,
            "frame_metadata":frame_meta,"external_lock_sha":a.external_lock_sha}

def resolved_native_module_paths(p27_root):
    return {
        "_make_it_stand":next((p27_root/"native-build/core/python").glob("_make_it_stand*.so"),None),
        "_cherchi_core_boolean":next((p27_root/"native-build/cherchi/python").glob("_cherchi_core_boolean*.so"),None),
        "_cherchi_rational_moments":next((p27_root/"native-build/cherchi/python").glob("_cherchi_rational_moments*.so"),None),
    }

def verify_modules(p27_root):
    found=resolved_native_module_paths(p27_root)
    for name, expected in MODULES.items():
        path=found[name]
        need(path is not None and path.is_file() and not path.is_symlink(),
             "REQUIRED_COMPILED_NATIVE_MODULE_MISSING:"+name)
        need(sha(path)==expected,"NATIVE_BINARY_MISMATCH:"+name)
    return {name:{"path":str(path.resolve()),"sha256":MODULES[name]}
            for name,path in found.items()}

def validate_native_output(material, coefficients, pins, counts, expected_base_feature):
    need(type(material) is dict, "NATIVE_MATERIAL_OBJECT_REQUIRED")
    need(material.get("derivative_defined") is True,
         "REAL_NATIVE_DERIVATIVE_UNDEFINED")
    need(material.get("quadric_coefficients")==tuple(coefficients) or
         material.get("quadric_coefficients")==list(coefficients),
         "REAL_SAME_CALL_C_MISMATCH")
    need(material.get("evaluation_map_identity")==pins["context_sha256"],
         "EVALUATION_CONTEXT_CHANGED")
    need(type(material.get("topology_hash")) is str and len(material["topology_hash"])==64 and
         all(c in "0123456789abcdef" for c in material["topology_hash"]),
         "BRANCH_IDENTITY_MISSING")
    need(type(material.get("geometry_hash")) is str and len(material["geometry_hash"])==64,
         "GEOMETRY_IDENTITY_MISSING")
    values=material.get("variable_raw_moments")
    jac=material.get("moment_jacobian")
    def finite(x):
        return type(x) in (int,float) and math.isfinite(float(x))
    need(type(values) is list and len(values)==10 and all(finite(x) for x in values),
         "REAL_R10_NOT_FINITE")
    need(type(jac) is list and len(jac)==10 and
         all(type(row) is list and len(row)==10 and all(finite(x) for x in row) for row in jac),
         "REAL_JC_NOT_FINITE_10X10")
    need(all(type(counts.get(key)) is int and counts[key]==1
             for key in ("source","boolean","integration","derivative")),
         "ONE_FRESH_SOURCE_BOOLEAN_DERIVATIVE_INTEGRATION_REQUIRED")
    need(type(expected_base_feature) is str and len(expected_base_feature)==64,
         "APPROVED_BASE_FEATURE_MISSING")
    return {
        "schema":SCHEMA,
        "status":"REAL_CHERCHI_TANGENT_POINT_OBSERVED_DIAGNOSTIC_ONLY",
        "branch_identity":material["topology_hash"],
        "base_feature_branch_matches":material["topology_hash"]==expected_base_feature,
        "geometry_hash":material["geometry_hash"],
        "r_design":values,
        "Jc_native_capture":jac,
        "call_counts":{k:counts[k] for k in ("source","boolean","derivative","integration")},
        "scientific_admission":False,
        **CLOSED,
    }

def verify_receipt(attempt, index, plan, external_sha, frame_contract,
                   frame_provenance, expected_frame):
    attempt=Path(attempt)
    receipt=attempt/"SAMPLE_RECEIPT.json"
    material=attempt/"MATERIAL_SAME_CALL.json"
    need(receipt.is_file() and material.is_file() and
         not receipt.is_symlink() and not material.is_symlink(),
         "SAMPLE_RECEIPT_OR_MATERIAL_MISSING")
    row=auth.strict_json(receipt.read_bytes())
    need(row.get("schema")==SCHEMA and
         row.get("status")=="REAL_CHERCHI_TANGENT_POINT_OBSERVED_DIAGNOSTIC_ONLY" and
         row.get("sample_index")==index and
         row.get("native_c_sha256")==plan["probes"][index]["native_c_sha256"] and
         row.get("registered_lock_sha256")==external_sha and
         row.get("material_sha256")==sha(material) and
         row.get("newton_evaluations")==0 and row.get("training_admissible") is False and
         row.get("moment_coordinate_frame")==expected_frame and
         row.get("coordinate_transform_applied")== (expected_frame==moment_frame.SI_FRAME),
         "PREVIOUS_SAMPLE_RECEIPT_TAMPERED")
    saved=auth.strict_json(material.read_bytes())
    need(saved.get("topology_hash")==row["branch_identity"] and
         saved.get("variable_raw_moments")==row["r_design"] and
         saved.get("moment_jacobian")==row["Jc_native_capture"] and
         saved.get("geometry_hash")==row["geometry_hash"],
         "PREVIOUS_SAMPLE_MATERIAL_TAMPERED")
    view_path=attempt/"MOMENT_FRAME_VIEW.json"
    need(view_path.is_file() and not view_path.is_symlink() and
         row.get("moment_frame_view_sha256")==sha(view_path),
         "PREVIOUS_SAMPLE_MOMENT_FRAME_VIEW_MISSING_OR_TAMPERED")
    view=auth.strict_json(view_path.read_bytes())
    verified_view=moment_frame.validate_moment_view(
        view,saved["variable_raw_moments"],saved["moment_jacobian"],
        frame_contract,frame_provenance,expected_frame)
    meta=moment_frame.frame_metadata(frame_contract,frame_provenance,expected_frame)
    for key,value in meta.items():
        need(row.get(key)==value,"PREVIOUS_SAMPLE_FRAME_METADATA_TAMPERED:"+key)
    need(row.get("r_design_in_frame_sha256")==moment_frame.sha256_bytes(
             moment_frame.canonical_bytes(verified_view["r_design_in_frame"])) and
         row.get("Jc_in_frame_sha256")==moment_frame.sha256_bytes(
             moment_frame.canonical_bytes(verified_view["Jc_in_frame"])),
         "PREVIOUS_SAMPLE_FRAME_ARRAY_HASH_MISMATCH")
    need(row.get("call_counts")=={"source":1,"boolean":1,"derivative":1,"integration":1}
         and row.get("scientific_admission") is False
         and all(row.get(k) is False for k in CLOSED),
         "PREVIOUS_SAMPLE_NATIVE_COUNTS_OR_RELEASE_FLAGS_CHANGED")
    final=attempt/"ATTEMPT_RESULT.json"
    need(final.is_file() and not final.is_symlink(),
         "SAMPLE_NOT_COMPLETED_SUCCESSFULLY")
    result=auth.strict_json(final.read_bytes())
    need(result.get("schema")=="W4_P30B_ATTEMPT_RESULT_V1" and
         result.get("status")=="SUCCESS_DIAGNOSTIC_ONLY" and
         result.get("worker_exit_code")==0 and
         result.get("sample_index")==index and
         result.get("material_sha256")==row["material_sha256"] and
         result.get("scientific_admission") is False and
         result.get("stdout_sha256")==sha(attempt/"stdout.log") and
         result.get("stderr_sha256")==sha(attempt/"stderr.log"),
         "SUCCESS_ATTEMPT_EXECUTION_RECEIPT_MISMATCH")
    return row

def next_attempt(point_dir):
    point_dir=Path(point_dir)
    attempts=sorted(p for p in point_dir.iterdir() if p.is_dir() and p.name.startswith("attempt-")) if point_dir.exists() else []
    for i,p in enumerate(attempts):
        need(p.name==f"attempt-{i:03d}" and not p.is_symlink(),
             "NONCANONICAL_OR_MISSING_ATTEMPT_SLOT")
    return point_dir/f"attempt-{len(attempts):03d}",attempts

def existing_verified_success(point_dir,index,plan,external_sha,
                             frame_contract,frame_provenance,expected_frame):
    if not point_dir.exists():return None
    _, attempts=next_attempt(point_dir)
    success=[]
    for attempt in attempts:
        final=attempt/"ATTEMPT_RESULT.json"
        if not final.is_file():
            # Power loss may leave BEGIN or even a fully serialized material.
            # Neither is a successful sample. Preserve; retry in next slot.
            continue
        outcome=auth.strict_json(final.read_bytes())
        need(outcome.get("schema")=="W4_P30B_ATTEMPT_RESULT_V1" and
             outcome.get("sample_index")==index,
             "ATTEMPT_RESULT_IDENTITY_DRIFT")
        if outcome.get("status")=="SUCCESS_DIAGNOSTIC_ONLY":
            success.append(verify_receipt(attempt,index,plan,external_sha,
                                               frame_contract,frame_provenance,expected_frame))
        else:
            need(outcome.get("status")=="FAILED_OR_TIMED_OUT_PRESERVE_FOR_INDEPENDENT_REVIEW" and
                 type(outcome.get("worker_exit_code")) is int and
                 outcome["worker_exit_code"]!=0 and
                 outcome.get("scientific_admission") is False,
                 "FAILED_ATTEMPT_RECORD_FALSIFIED")
    need(len(success)<=1,"MULTIPLE_ACCEPTED_SUCCESSES_AT_ONE_POINT")
    return success[0] if success else None

def worker(a, bound, index, output_dir):
    require_real_resources(resource_report())
    verify_modules(a.p27_run_dir)
    output_dir=Path(output_dir).resolve()
    need(output_dir.name.startswith("attempt-") and
         output_dir.parent.name==f"point-{index:03d}",
         "WORKER_MUST_RUN_INSIDE_REGISTERED_ATTEMPT")
    state_path=output_dir.parent.parent/"RUN_STATE.json"
    need(state_path.is_file(),"MISSING_BATCH_RUN_STATE")
    state=auth.strict_json(state_path.read_bytes())
    need(state.get("schema")==RUN_SCHEMA and
         state.get("registered_lock_sha256")==a.external_lock_sha and
         state.get("plan_sha256")==auth.P30_PRIVATE_PLAN_SHA and
         state.get("pilot_count")==N_PILOT and
         state.get("moment_coordinate_frame")==a.moment_coordinate_frame,
         "BATCH_STATE_CHANGED_OR_UNREGISTERED")
    for key,value in bound["frame_metadata"].items():
        need(state.get(key)==value,"BATCH_STATE_FRAME_BINDING_CHANGED:"+key)
    begin_path=output_dir/"BEGIN.json"
    need(begin_path.is_file(),"MISSING_APPEND_ONLY_ATTEMPT_BEGIN")
    begin=auth.strict_json(begin_path.read_bytes())
    need(begin.get("index")==index and
         begin.get("lock_sha256")==a.external_lock_sha and
         begin.get("native_c_sha256")==bound["plan"]["probes"][index]["native_c_sha256"],
         "ATTEMPT_BEGIN_OR_C_MISMATCH")
    plan=bound["plan"]
    need(type(index) is int and 0<=index<N_PILOT, "ONLY_12_REGISTERED_PILOT_INDICES_ALLOWED")
    item=plan["probes"][index]
    need(item["stage"]=="PILOT_3_DIR" and
         seed.canonical_hash(item["native_c"])==item["native_c_sha256"],
         "REGISTERED_PILOT_COEFFICIENT_CHANGED")
    resource.setrlimit(resource.RLIMIT_AS,(ADDRESS_BYTES,ADDRESS_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU,(POINT_MAX_SECONDS,POINT_MAX_SECONDS+1))
    p1=a.w4_root/P20_REL
    sys.path.insert(0,str(p1))
    import p20_native_factory
    need(Path(p20_native_factory.__file__).resolve()==(p1/"p20_native_factory.py").resolve(),
         "UNTRUSTED_P20_FACTORY_IMPORTED")
    started=time.monotonic()
    bundle=p20_native_factory.prepare_context()
    evaluator=bundle["evaluator"]
    pre_counts=dict(evaluator.call_counts)
    need(all(pre_counts.get(k)==0 for k in ("source","boolean","integration","derivative")),
         "NATIVE_EVALUATOR_NOT_FRESH")
    pins=p20_native_factory.observed_pins(bundle)
    need(pins==bound["pins"],"REAL_PRE_EVALUATION_SIX_PINS_CHANGED")
    need(getattr(evaluator,"branch_identity_policy",None)=="SOURCE_FEATURE_BRANCH_V2",
         "FEATURE_BRANCH_POLICY_NOT_V2")
    q=item["native_c"]
    result=evaluator(q)  # GENUINE Cherchi source/Boolean/derivative/integration, one fresh c
    material=evaluator.material(q)
    evaluator.validate_same_call_material(material,q,bundle["prepared"].request)
    counts=dict(evaluator.call_counts)
    digest_result=validate_native_output(material,q,pins,counts,
                    bound["readiness"]["teacher"]["base_feature_branch_sha256"])
    view=moment_frame.make_moment_view(
        material["variable_raw_moments"],material["moment_jacobian"],
        bound["frame_contract"],bound["frame_provenance"],a.moment_coordinate_frame)
    need(result["geometry_hash"]==material["geometry_hash"] and
         result["topology_hash"]==material["topology_hash"],
         "NATIVE_RETURNED_MATERIAL_DIFFERS_FROM_SAVED_SAME_CALL")
    need(p20_native_factory.observed_pins(bundle)==pins,
         "POST_EVALUATION_MODULE_OR_CONTEXT_IDENTITY_DRIFT")
    p20_native_factory.recheck_inputs(bundle["input_identity"])
    need(not (Path(output_dir)/"MATERIAL_SAME_CALL.json").exists(),
         "MATERIAL_OUTPUT_ALREADY_EXISTS")
    new_json(Path(output_dir)/"MATERIAL_SAME_CALL.json",material)
    view_path=Path(output_dir)/"MOMENT_FRAME_VIEW.json"
    new_json(view_path,view)
    frame_meta=moment_frame.frame_metadata(
        bound["frame_contract"],bound["frame_provenance"],a.moment_coordinate_frame)
    receipt={**digest_result,**frame_meta,"sample_index":index,
             "native_c_sha256":item["native_c_sha256"],
             "registered_lock_sha256":a.external_lock_sha,
             "material_sha256":sha(Path(output_dir)/"MATERIAL_SAME_CALL.json"),
             "moment_frame_view_sha256":sha(view_path),
             "r_design_in_frame_sha256":moment_frame.sha256_bytes(
                 moment_frame.canonical_bytes(view["r_design_in_frame"])),
             "Jc_in_frame_sha256":moment_frame.sha256_bytes(
                 moment_frame.canonical_bytes(view["Jc_in_frame"])),
             "source_formal_M6_manifest_sha256":seed.MANIFEST_SHA,
             "reference_context_sha256":pins["context_sha256"],
             "native_module_shas":dict(MODULES),
             "worker_elapsed_seconds":time.monotonic()-started,
             "peak_rss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             "newton_evaluations":0,
             "training_admissible":False}
    new_json(Path(output_dir)/"SAMPLE_RECEIPT.json",receipt)
    print(json.dumps({"status":receipt["status"],"index":index,
                      "feature_branch_matches":receipt["base_feature_branch_matches"],
                      "new_native_calls":1,"Newton_accepted":False},sort_keys=True))
    return 0

def batch(a,bound):
    require_real_resources(resource_report())
    verify_modules(a.p27_run_dir)
    output=Path(a.output_dir).resolve()
    state={"schema":RUN_SCHEMA,"status":"IN_PROGRESS_DIAGNOSTIC_ONLY",
           "moment_coordinate_frame":a.moment_coordinate_frame,
           **bound["frame_metadata"],
           "registered_lock_sha256":a.external_lock_sha,
           "plan_sha256":auth.P30_PRIVATE_PLAN_SHA,
           "p27_run":seed.RUN,
           "pilot_count":N_PILOT,
           "owner_review_commit":bound["approvals"]["w0"]["head"],
           "teacher_review_commit":bound["approvals"]["w2"]["head"],
           "newton_executed":False,"training_admissible":False}
    if a.resume:
        need(output.is_dir() and auth.strict_json((output/"RUN_STATE.json").read_bytes())==state,
             "RESUME_REQUIRES_IMMUTABLE_SAME_RUN_STATE")
    else:
        need(not output.exists(),"RUN_DIRECTORY_ALREADY_EXISTS")
        output.mkdir(parents=True,exist_ok=False)
        new_json(output/"RUN_STATE.json",state)
    lockfile=output.parent/"P30B_SERIAL_GLOBAL.lock"
    with lockfile.open("a") as lock:
        try: fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as err:
            raise SampleRejected("ANOTHER_P30B_NATIVE_RUN_IN_PROGRESS") from err
        deadline=time.monotonic()+P30_MAX_SECONDS
        for i in range(N_PILOT):
            point=output/f"point-{i:03d}"
            verified=existing_verified_success(
                point,i,bound["plan"],a.external_lock_sha,bound["frame_contract"],
                bound["frame_provenance"],a.moment_coordinate_frame)
            if verified is not None:
                print(json.dumps({"status":"SKIP_ALREADY_VERIFIED","sample":i},sort_keys=True),flush=True)
                continue
            new,prior=next_attempt(point)
            new.mkdir(parents=True,exist_ok=False)
            # All attempts are preserved even if the subprocess dies before
            # writing its formal status. Resume never rewrites them.
            new_json(new/"BEGIN.json",{"index":i,"attempt":len(prior),
                    "native_c_sha256":bound["plan"]["probes"][i]["native_c_sha256"],
                    "lock_sha256":a.external_lock_sha,
                    "scope":"DIAGNOSTIC_NOT_NEWTON_OR_TRAINING"})
            remaining=int(deadline-time.monotonic())
            need(remaining>0,"PILOT_TOTAL_3600_S_LIMIT_EXHAUSTED")
            seconds=min(POINT_MAX_SECONDS,remaining)
            args=[sys.executable,str(Path(__file__).resolve()),"--mode","worker",
                "--plan",str(a.plan),"--archive",str(a.archive),
                "--p20-request",str(a.p20_request),
                "--registered-lock",str(a.registered_lock),
                "--external-lock-sha",a.external_lock_sha,
                "--p27-run-dir",str(a.p27_run_dir),
                "--w0-review-root",str(a.w0_review_root),
                "--w2-review-root",str(a.w2_review_root),
                "--w0-source-root",str(a.w0_source_root),
                "--core-root",str(a.core_root),"--w4-root",str(a.w4_root),
                "--index",str(i),"--output-dir",str(new),
                "--moment-coordinate-frame",a.moment_coordinate_frame]
            environ=dict(os.environ, PYTHONNOUSERSITE="1",PYTHONDONTWRITEBYTECODE="1",
                         OMP_NUM_THREADS="1",OPENBLAS_NUM_THREADS="1",MKL_NUM_THREADS="1")
            with (new/"stdout.log").open("xb") as stdout, (new/"stderr.log").open("xb") as stderr:
                child=subprocess.Popen(args,stdout=stdout,stderr=stderr,
                                       env=environ,start_new_session=True)
                try:code=child.wait(timeout=seconds)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid,signal.SIGKILL)
                    code=child.wait()
            outcome={"schema":"W4_P30B_ATTEMPT_RESULT_V1","sample_index":i,
                     "attempt":len(prior),"worker_exit_code":code,
                     "stdout_sha256":sha(new/"stdout.log"),
                     "stderr_sha256":sha(new/"stderr.log"),"scientific_admission":False}
            if code==0:
                # Worker produced its material and receipt, but the enclosing
                # final success receipt is deliberately written last. Failure
                # before that point remains incomplete and must not be skipped.
                material=new/"MATERIAL_SAME_CALL.json"
                receipt=new/"SAMPLE_RECEIPT.json"
                view_path=new/"MOMENT_FRAME_VIEW.json"
                need(material.is_file() and receipt.is_file() and view_path.is_file(),
                     "SUCCESS_WORKER_WITH_MISSING_EVIDENCE")
                row=auth.strict_json(receipt.read_bytes())
                need(row.get("material_sha256")==sha(material) and
                     row.get("sample_index")==i and
                     row.get("registered_lock_sha256")==a.external_lock_sha,
                     "SUCCESS_WORKER_EVIDENCE_IDENTITY_MISMATCH")
                outcome["status"]="SUCCESS_DIAGNOSTIC_ONLY"
                outcome["material_sha256"]=row["material_sha256"]
                outcome["moment_frame_view_sha256"]=row["moment_frame_view_sha256"]
            else:
                outcome["status"]="FAILED_OR_TIMED_OUT_PRESERVE_FOR_INDEPENDENT_REVIEW"
            new_json(new/"ATTEMPT_RESULT.json",outcome)
            if code==0:
                verify_receipt(new,i,bound["plan"],a.external_lock_sha,
                               bound["frame_contract"],bound["frame_provenance"],
                               a.moment_coordinate_frame)
            print(json.dumps({"sample":i,"status":outcome["status"],"exit":code},
                             sort_keys=True),flush=True)
            if code!=0:return 4
    accepted=[]
    for i in range(N_PILOT):
        item=existing_verified_success(
            output/f"point-{i:03d}",i,bound["plan"],a.external_lock_sha,
            bound["frame_contract"],bound["frame_provenance"],a.moment_coordinate_frame)
        need(item is not None,"PILOT_COMPLETION_MISSING_REAL_SAMPLE")
        accepted.append({"sample_index":i,"receipt":item})
    summary={"schema":PILOT_SCHEMA,"status":"TWELVE_GENUINE_DIAGNOSTIC_POINTS_COLLECTED_NOT_CERTIFIED",
             "moment_coordinate_frame":a.moment_coordinate_frame,
             **bound["frame_metadata"],
             "moment_frame_views_transformed":N_PILOT if a.moment_coordinate_frame==moment_frame.SI_FRAME else 0,
             "precommitted_lock_sha256":a.external_lock_sha,
             "accepted":accepted,"observed_real_samples":len(accepted),
             "newton_executed":False,"scientific_admission":False,**CLOSED}
    completed=output/"PILOT_COMPLETION.json"
    if completed.exists():
        need(auth.strict_json(completed.read_bytes())==summary,
             "EXISTING_PILOT_COMPLETION_DIFFERENT_DO_NOT_OVERWRITE")
    else:
        new_json(completed,summary)
    return 0

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--mode",choices=("batch","worker"),required=True)
    for name in ("plan","archive","p20_request","registered_lock","p27_run_dir",
                 "w0_review_root","w2_review_root","w0_source_root","core_root","w4_root"):
        p.add_argument("--"+name.replace("_","-"),type=Path,required=True)
    p.add_argument("--external-lock-sha",required=True)
    p.add_argument("--index",type=int)
    p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--resume",action="store_true")
    p.add_argument("--moment-coordinate-frame",
                   choices=(moment_frame.NATIVE_FRAME,moment_frame.SI_FRAME),
                   default=moment_frame.NATIVE_FRAME)
    a=p.parse_args(argv)
    try:
        need(bool(auth.HEX64.fullmatch(a.external_lock_sha)),"INVALID_EXTERNAL_LOCK_SHA")
        bound=read_auth_and_bind(a)
        if a.mode=="worker":
            need(a.index is not None and a.resume is False,
                 "WORKER_REQUIRES_INDEX_NO_RESUME")
            return worker(a,bound,a.index,a.output_dir)
        need(a.index is None,"BATCH_INDEX_NOT_ALLOWED")
        return batch(a,bound)
    except (SampleRejected,auth.GateRejected,seed.PlanRejected,
            OSError,KeyError,TypeError,ValueError,OverflowError,
            subprocess.SubprocessError) as exc:
        print(json.dumps({"status":"P30B_REJECTED_NO_PROMOTION","error":str(exc),
                          "training_admissible":False,"Newton_accepted":False},
                         sort_keys=True),file=sys.stderr)
        return 4

if __name__=="__main__":
    raise SystemExit(main())

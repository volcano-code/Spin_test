"""M6 accelerated *independent* exact tetra validation of archived H8e materials.

Native GMP tetra formula is independent of the production surface-divergence
routine. It NEVER substitutes archived geometry proof for a fresh proof, never
changes acceptance states, and never claims a new Cherchi Boolean/Newton run.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from fractions import Fraction
import gzip
from hashlib import sha256
import json
import math
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tempfile
import time
from zipfile import ZipFile

from m4_25point_attribution import (  # frozen local W1 archival protocol
    ARCHIVE_SHA, H8E_ROOT, REQ, POINTS, PAIRS, exact_member, strict_archive,
    to_stream, five_weights,
)

BACKEND = "cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:"
STAGES = (
    "read_archive", "decompress_packet", "parse_packet", "authenticate_same_call",
    "write_checked_stream", "native_exact_tetra", "exact_python_fraction", "parity",
)


def sha(data: bytes) -> str:
    return sha256(data).hexdigest()


class ExclusiveClock:
    def __init__(self):
        self.start = time.perf_counter_ns()
        self.active = None
        self.stages = []

    @contextmanager
    def stage(self, name):
        if name not in STAGES or self.active is not None:
            raise ValueError("M6_OVERLAPPING_OR_UNREGISTERED_STAGE")
        self.active = name
        tic = time.perf_counter_ns()
        state = "PASS"
        try:
            yield
        except BaseException:
            state = "FAIL"
            raise
        finally:
            self.stages.append(dict(stage=name, elapsed_ns=time.perf_counter_ns()-tic,
                                    status=state))
            self.active = None

    def summary(self):
        if self.active is not None:
            raise ValueError("M6_ACTIVE_TIMING_STAGE")
        wall = time.perf_counter_ns()-self.start
        stage_sum = sum(x["elapsed_ns"] for x in self.stages)
        if stage_sum > wall:
            raise ValueError("M6_NEGATIVE_UNATTRIBUTED_TIME")
        return dict(wall_ns=wall, stages=list(self.stages),
                    unattributed_ns=wall-stage_sum,
                    all_passed=all(x["status"]=="PASS" for x in self.stages))


def rational(s, *, max_length=2048):
    # Independent Python Fraction parser; all archive tokens must be reduced
    # canonical base-10 n/d. GMP native also checks this separately.
    if type(s) is not str or len(s)>max_length or s.count("/")!=1:
        raise ValueError("M6_INVALID_RATIONAL_TOKEN")
    a,b=s.split("/")
    if (not a or not b or not a.lstrip("-").isdigit() or not b.isdigit()
            or a.startswith("+") or int(b)<=0):
        raise ValueError("M6_INVALID_RATIONAL_PAIR")
    f=Fraction(int(a),int(b))
    if f"{f.numerator}/{f.denominator}"!=s:
        raise ValueError("M6_NONCANONICAL_RATIONAL_TOKEN")
    return f


def python_fraction_ten(vertices, faces):
    """Original independent tetra formula, preserved for exact A/B tests."""
    xyz=[tuple(rational(x) for x in row) for row in vertices]
    totals=[Fraction(0) for _ in range(10)]
    for face in faces:
        if (len(face)!=3 or any(type(v) is not int or v<0 or v>=len(xyz) for v in face)
                or len(set(face))!=3):
            raise ValueError("M6_INVALID_EXACT_FACE")
        a,b,c=(xyz[i] for i in face)
        det=(a[0]*(b[1]*c[2]-b[2]*c[1])+
             a[1]*(b[2]*c[0]-b[0]*c[2])+
             a[2]*(b[0]*c[1]-b[1]*c[0]))
        if det==0:
            continue
        totals[0]+=det/6
        s=[a[k]+b[k]+c[k] for k in range(3)]
        for k in range(3):
            totals[k+1]+=det*s[k]/24
        for k,(x,y) in enumerate(PAIRS):
            totals[k+4]+=det*(s[x]*s[y]+a[x]*a[y]+b[x]*b[y]+c[x]*c[y])/120
    if totals[0]<=0:
        raise ValueError("M6_NONPOSITIVE_MASS")
    return totals


def run_binary(executable: Path, stream: Path):
    def memory_guard():
        target=24*1024**3
        soft,hard=resource.getrlimit(resource.RLIMIT_AS)
        limit=min([target]+[v for v in (soft,hard) if v!=resource.RLIM_INFINITY])
        resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    with stream.open("r",encoding="ascii") as source:
        result=subprocess.run([str(executable)],stdin=source,capture_output=True,
            text=True,timeout=300,preexec_fn=memory_guard)
    if result.returncode:
        raise RuntimeError("M6_INDEPENDENT_NATIVE_REJECTED:"+result.stderr[:160])
    obj=json.loads(result.stdout)
    if (obj.get("schema")!="w1-m6-exact-independent-tetra-v1" or
            obj.get("scope")!="ARCHIVED_H8_EXACT_TETRA_INDEPENDENT_OF_PRODUCTION_SURFACE" or
            obj.get("fresh_boolean") is not False or
            obj.get("new_self_intersection_audit") is not False or
            obj.get("full_solver_speedup") is not None):
        raise ValueError("M6_INVALID_NATIVE_SCOPE")
    exact=obj["exact_ten"]
    if len(exact)!=10 or any(type(t) is not str or not t for t in exact):
        raise ValueError("M6_INVALID_NATIVE_TEN")
    return obj


def independent_fd(rows, report):
    if len(rows)!=25:
        return dict(status="INCOMPLETE_NO_FD", numeric_stencils=0)
    q0=rows[0]["q"]
    analytic=report["analytic_10_by_10_jacobian"]
    if len(analytic)!=10 or any(len(r)!=10 for r in analytic):
        raise ValueError("M6_MISSING_ARCHIVED_BASE_JACOBIAN")
    numeric=[]
    for old in report["numeric_checks"]:
        ids=old["sample_indices"];c=old["column"]
        if len(ids)!=5 or any(i not in rows for i in ids):
            raise ValueError("M6_INVALID_STENCIL_INDICES")
        positions=[rows[i]["q"][c]-q0[c] for i in ids]
        weights=five_weights(positions)
        # Floating point formula identical to M4 (numpy BLAS order).
        import numpy as np
        computed=weights@np.asarray([rows[i]["moments"] for i in ids])
        basis=np.asarray(analytic)[:,c]
        scaled=float(np.max(np.abs(computed-basis)/np.maximum(1.0,np.abs(basis))))
        stable=all(rows[i]["topology_hash"]==rows[0]["topology_hash"] for i in ids)
        if (scaled>1e-6 or abs(scaled-old["max_scaled_derivative_error"])>1e-8
                or stable is not old["feature_hash_stable"]):
            raise ValueError("M6_NUMERICAL_OR_BRANCH_HISTORY_CHANGED")
        numeric.append(dict(column=c,step=old["step"],scaled_error=scaled,
                            history_hash_stable=stable))
    n_changed=sum(rows[i]["topology_hash"]!=rows[0]["topology_hash"] for i in range(1,25))
    if len(numeric)!=9 or n_changed!=8:
        raise ValueError("M6_H8E_ORIGINAL_FAILURE_NOT_PRESERVED")
    return dict(status="NUMERICAL_FD_ONLY_NO_SMOOTH_NEIGHBORHOOD_PROOF",numeric_stencils=9,
                max_scaled_error=max(x["scaled_error"] for x in numeric),
                originally_changed_feature_hash_points=8,
                archived_jacobian_not_recomputed=True,checks=numeric)


def run(archive, binary, output, *, count=25, reference_indices=(0,12,24)):
    archive,binary,output=Path(archive),Path(binary),Path(output)
    if not 1<=count<=25 or len(set(reference_indices))!=len(reference_indices) or any(
            type(i) is not int or i<0 or i>=count for i in reference_indices):
        raise ValueError("M6_UNSAFE_SAMPLE_SELECTION")
    output.mkdir(parents=True,exist_ok=False)
    records=[]
    wall=time.perf_counter_ns()
    try:
        if len(Path("/proc/swaps").read_text().splitlines())!=1:
            raise RuntimeError("M6_SWAP_MUST_BE_ZERO")
        if not binary.is_file():
            raise FileNotFoundError("M6_NATIVE_BINARY_REQUIRED")
        binary=binary.resolve()
        bsha=sha(binary.read_bytes())
        if sha(archive.read_bytes())!=ARCHIVE_SHA:
            raise ValueError("M6_ARCHIVED_H8E_ZIP_SHA_DRIFT")
        with ZipFile(archive) as z:
            historical=strict_archive(z)
            with tempfile.TemporaryDirectory(prefix="w1-m6-archive-") as tmp:
                for i in range(count):
                    clock=ExclusiveClock()
                    path=H8E_ROOT+f"point-{i:03d}-material.json.gz"
                    with clock.stage("read_archive"):
                        packed=exact_member(z,path,max_size=3_000_000)
                        raw=exact_member(z,H8E_ROOT+f"point-{i:03d}.json",max_size=200_000)
                    with clock.stage("decompress_packet"):
                        unpacked=gzip.decompress(packed)
                        if len(unpacked)>20_000_000:
                            raise ValueError("M6_PACKET_DECOMPRESSION_LIMIT")
                    with clock.stage("parse_packet"):
                        packet=json.loads(unpacked)
                        reference=json.loads(raw)
                    with clock.stage("authenticate_same_call"):
                        if (sha(packed)!=reference["exact_same_call_material_archive_sha256"] or
                            reference["index"]!=i or
                            len(packet["variable_rational_vertices"])!=8455 or
                            len(packet["variable_faces"])!=16910 or
                            reference["vertex_count"]!=8455 or reference["triangle_count"]!=16910 or
                            packet["quadric_coefficients"]!=reference["coefficients"] or
                            packet["geometry_hash"]!=reference["material_geometry_hash"] or
                            packet["topology_hash"]!=reference["feature_branch_hash"] or
                            not packet["boolean_backend_identity"].startswith(BACKEND) or
                            reference["exact_native_material_boundary_passed"] is not True or
                            reference.get("independent_moments_max_scaled_error",1)>1e-10 or
                            packet.get("derivative_defined") is not True):
                            raise ValueError("M6_SAME_CALL_ARCHIVED_PROOF_DRIFT")
                        jac=packet.get("moment_jacobian")
                        if (len(jac)!=10 or any(len(row)!=10 or any(not math.isfinite(v) for v in row) for row in jac)):
                            raise ValueError("M6_ARCHIVED_JACOBIAN_INVALID")
                        if packet["material_proof"].get("schema")!="cherchi-same-call-material-v1":
                            raise ValueError("M6_MATERIAL_PROOF_SCHEMA_CHANGED")
                    stream=Path(tmp)/f"point-{i:03d}.txt"
                    with clock.stage("write_checked_stream"):
                        to_stream(packet["variable_rational_vertices"],packet["variable_faces"],stream)
                    with clock.stage("native_exact_tetra"):
                        independent=run_binary(binary,stream)
                        if independent["vertices"]!=8455 or independent["faces"]!=16910:
                            raise ValueError("M6_NATIVE_OUTPUT_SHAPE_MISMATCH")
                    old_fraction_elapsed=None
                    old_exact=None
                    if i in reference_indices:
                        with clock.stage("exact_python_fraction"):
                            t=time.perf_counter_ns()
                            old_exact=python_fraction_ten(packet["variable_rational_vertices"],packet["variable_faces"])
                            old_fraction_elapsed=time.perf_counter_ns()-t
                    with clock.stage("parity"):
                        original_limit=sys.get_int_max_str_digits()
                        try:
                            sys.set_int_max_str_digits(max(20000, original_limit))
                            new_exact=[rational(t,max_length=16000) for t in independent["exact_ten"]]
                        finally:
                            sys.set_int_max_str_digits(original_limit)
                        if old_exact is not None and new_exact!=old_exact:
                            raise ValueError("M6_PYTHON_FRACTION_VS_GMP_EXACT_PARITY_FAILED")
                        # All points validate 10/10 native results against the
                        # historical *independently* obtained Fraction moments.
                        floats=[float(v) for v in new_exact]
                        for k in range(10):
                            source=float(reference["independent_variable_raw_moments"][k])
                            produced=float(reference["production_variable_raw_moments"][k])
                            if not(math.isfinite(source) and math.isfinite(produced)):
                                raise ValueError("M6_ARCHIVED_NONFINITE_TEN")
                            if abs(floats[k]-source)>1e-12 or abs(floats[k]-produced)>1e-12:
                                raise ValueError("M6_ARCHIVED_TEN_MOMENTS_NOT_EQUAL")
                    t=clock.summary()
                    if not t["all_passed"]:
                        raise ValueError("M6_INCOMPLETE_POINT_STAGE")
                    records.append(dict(index=i,archive_material_sha256=sha(packed),
                        topology_hash=packet["topology_hash"],q=packet["quadric_coefficients"],
                        moments=floats,exact_python_fraction_matched=old_exact is not None,
                        native_parse_ns=independent["input_parse_ns"],
                        native_boundary_gate_ns=independent["full_boundary_gate_ns"],
                        native_tetra_math_ns=independent["independent_tetra_ns"],
                        old_python_fraction_ns=old_fraction_elapsed,
                        stage_timing=t))
                    print("M6_ARCHIVED_H8",i+1,"/",count,"GMP TETRA OK",flush=True)
        fd=independent_fd({r["index"]:r for r in records},historical)
        totals={stage:sum(next((t["elapsed_ns"] for t in rec["stage_timing"]["stages"]
                                if t["stage"]==stage),0) for rec in records)
                for stage in STAGES}
        replay_wall=time.perf_counter_ns()-wall
        measured_old=[x["old_python_fraction_ns"] for x in records if x["old_python_fraction_ns"] is not None]
        selected_native=[x["stage_timing"]["stages"] for x in records if x["old_python_fraction_ns"] is not None]
        selected_native_ns=[next(t["elapsed_ns"] for t in entry if t["stage"]=="native_exact_tetra")
                            for entry in selected_native]
        # Only paired sample subset is valid for speed claims, not 25-point solver!
        speed_pairs=[float(a)/b for a,b in zip(measured_old,selected_native_ns)]
        report=dict(schema="w1-m6-archived-exact-tetra-accelerated-validation-v1",
            scope="ARCHIVED_H8E_VALIDATION_ONLY_NOT_FRESH_CHERCHI_OR_NEWTON",
            input_archive_sha256=ARCHIVE_SHA,source_historical_run_id=39121571756,
            native_binary_sha256=bsha,point_count=len(records),all_points_parity_passed=True,
            full_old_new_exact_python_sample_count=len(measured_old),
            exact_python_fraction_gmp_parity_on_samples=True,
            ten_component_historical_parity_count=10*len(records),
            end_to_end_wall_ns=replay_wall,stage_exclusive_ns=totals,
            all_timed_point_stages_closed=all(x["stage_timing"]["all_passed"] for x in records),
            independent_native_tetra_time_ns=sum(x["native_tetra_math_ns"] for x in records),
            sample_fraction_vs_gmp_subprocess_speedup_ratios=speed_pairs,
            independent_fd=fd,original_h8e_ci_failure_preserved=True,
            hardware=dict(platform=platform.platform(),cpu_count=__import__('os').cpu_count(),
                          rss_process_peak_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                          rss_child_peak_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                          swap_entries=0,memory_limit_gib=24,max_compile_workers=1,
                          max_single_job_seconds=3600),
            fresh_cherchi_boolean_calls=0,new_independent_self_intersection_audits=0,
            new_production_jacobian_evaluations=0,full_newton_solver_measured=False,
            new_optimization_applied_to_production=False,
            full_solver_before_after_speedup=None,paper_speed_qualified=False)
        (output/"baseline-performance.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
        (output/"before_after.json").write_text(json.dumps(dict(
            schema="w1-m6-before-after-v1",scope="MATCHED_ARCHIVED_VALIDATOR_SUBSET_NOT_SOLVER",
            paired_python_fraction_vs_gmp_samples=len(measured_old),
            exact_ten_rational_equal_on_paired_samples=True,
            paired_independent_verifier_speedup_ratios=speed_pairs,
            full_solver_end_to_end_speedup=None,production_code_changed=False,
            strong_same_call_geometry_newly_certified=False,paper_speed_qualified=False),indent=2)+"\n")
        with (output/"points.jsonl").open("x") as f:
            for row in records:
                f.write(json.dumps(row,allow_nan=False,sort_keys=True)+"\n")
        return report
    except BaseException as ex:
        (output/"failure.json").write_text(json.dumps(dict(schema="w1-m6-replay-failure-v1",
            status="FAILED_NO_NEW_NATIVE_SOLVE",error=f"{type(ex).__name__}: {ex}",
            completed=len(records),original_h8e_ci_failure_preserved=True,
            full_solver_speedup=None,paper_speed_qualified=False),indent=2)+"\n")
        raise


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--binary",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--points",type=int,default=25)
    p.add_argument("--fraction-points",default="0,12,24")
    a=p.parse_args()
    samples=tuple(int(x) for x in a.fraction_points.split(",") if x)
    r=run(a.archive,a.binary,a.output,count=a.points,reference_indices=samples)
    print("W1_M6",r["point_count"],"archived packets with exact tetra parity",flush=True)

if __name__=="__main__":
    main()

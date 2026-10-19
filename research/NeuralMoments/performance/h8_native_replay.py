"""W1 M2: one real frozen Heart H8 same-call Cherchi/GMP evaluation profiler.

Requires an externally built native toolchain and the exact frozen H8 request.
Every geometric and independent Fraction validation remains enabled.
One sampled q is NOT a Faster Newton solve, material seal, or paper-speed result.
"""
from __future__ import annotations

import argparse
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import resource
import signal
import sys
import time

FREEZE = "0bcc187b3005478baa586a6d6f450e73811ca342"
EXPECTED_REQUEST_SHA256 = "1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c"
H8 = "research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018"
PINNED_CHERCHI_PREFIX = "cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:"
NATIVE_STAGE_NAMES = frozenset((
    "source", "physical_source_boundary", "boolean", "intersection_motion",
    "prepare_arithmetic_boundary", "derivative", "integration",
    "material_attachment_serialization",
))
EXTRA_STAGE_NAMES = frozenset((
    "material_decode", "same_call_validation", "native_exact_boundary_audit",
    "independent_fraction_ten", "json_snapshot",
))
AUDIT_TRUE = (
    "boundary_valid", "closed", "edge_manifold", "vertex_manifold",
    "consistently_oriented", "component_orientations_valid",
    "self_intersection_completed", "self_intersection_free",
)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write_new(path, data):
    with Path(path).open("x", encoding="utf-8") as fp:
        json.dump(data, fp, indent=2, sort_keys=True, allow_nan=False)
        fp.write("\n")


class ExclusiveLedger:
    """Observe strictly sequential operations; never flatten nested durations."""
    def __init__(self):
        self.start_ns = time.monotonic_ns()
        self.entries = []
        self._active = None

    def observe(self, name, fn):
        if name not in NATIVE_STAGE_NAMES | EXTRA_STAGE_NAMES:
            raise ValueError("UNREGISTERED_W1_NATIVE_STAGE:" + str(name))
        if self._active is not None:
            raise ValueError("W1_STAGE_OVERLAP:" + self._active + ":" + name)
        self._active = name
        t = time.monotonic_ns()
        status = "RETURNED"
        try:
            return fn()
        except BaseException:
            status = "FAILED"
            raise
        finally:
            self.entries.append(dict(stage=name, elapsed_ns=time.monotonic_ns()-t,
                                     status=status))
            self._active = None

    def summary(self):
        if self._active is not None:
            raise ValueError("W1_LEDGER_UNFINISHED_STAGE")
        wall = time.monotonic_ns()-self.start_ns
        stages_total = sum(x["elapsed_ns"] for x in self.entries)
        if stages_total > wall:
            raise ValueError("W1_LEDGER_OVERLAPPING_TIME")
        return dict(setup_and_sample_wall_ns=wall, exclusive_stages=self.entries,
                    unattributed_ns=wall-stages_total,
                    all_stages_passed=all(x["status"]=="RETURNED" for x in self.entries))


def resource_guard():
    swap = Path("/proc/swaps")
    if not swap.is_file() or len(swap.read_text().splitlines()) != 1:
        raise RuntimeError("W1_SWAP_MUST_BE_ZERO")
    requested = 24*1024**3
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS,
                       (min(requested,soft) if soft != resource.RLIM_INFINITY else requested,hard))
    return dict(max_memory_bytes=requested, swap_entries=0, timeout_seconds=3600,
                max_compile_workers=4)


def validate_native_audit(audit):
    if not isinstance(audit, dict) or any(audit.get(key) is not True for key in AUDIT_TRUE):
        raise ValueError("W1_EXACT_BOUNDARY_REQUIRED_FLAGS_FAILED")
    if audit.get("intersecting_pairs") or audit.get("degenerate_faces") or audit.get("intersection_error"):
        raise ValueError("W1_EXACT_BOUNDARY_INTERSECTION_OR_DEGENERACY")


def checked_parity(material, evaluated, fraction_ten):
    """Only a SAME-CALL independent ten-moment check, not old/new code parity."""
    import numpy as np
    produced = np.asarray(evaluated["variable_raw_moments"], dtype=np.float64)
    reference = np.asarray([float(v) for v in fraction_ten], dtype=np.float64)
    jacobian = np.asarray(evaluated["moment_jacobian"], dtype=np.float64)
    if (produced.shape != (10,) or reference.shape != (10,)
            or jacobian.shape != (10,10) or not np.isfinite(produced).all()
            or not np.isfinite(reference).all() or not np.isfinite(jacobian).all()):
        raise ValueError("W1_BAD_TEN_OR_JACOBIAN")
    scaled = float(np.max(np.abs(produced-reference)/np.maximum(1.,np.abs(reference))))
    if scaled > 1e-10:
        raise ValueError("W1_FRACTION_VS_GMP_DISAGREEMENT")
    if (material.get("geometry_hash") != evaluated.get("geometry_hash")
            or material.get("topology_hash") != evaluated.get("topology_hash")
            or material.get("quadric_source_identity") is None):
        raise ValueError("W1_SAME_CALL_MATERIAL_IDENTITY_MISMATCH")
    return dict(independent_scaled_error=scaled, moments=produced.tolist(),
                jacobian=jacobian.tolist(), geometry_hash=material["geometry_hash"],
                topology_hash=material["topology_hash"],
                quadric_source_identity=material["quadric_source_identity"])


def evaluate(root: Path, request_file: Path, output: Path):
    output.mkdir(parents=True, exist_ok=False)
    ledger = ExclusiveLedger()
    run_status = dict(schema="w1-h8-sample-failure-v1", scope="H8_RECONSTRUCTED_NOT_AUTHOR_CAD",
                      status="FAILED_CLOSED", paper_speed_qualified=False)
    try:
        if not request_file.is_file():
            raise FileNotFoundError("W1_H8_FROZEN_REQUEST_NOT_AVAILABLE")
        request_sha = digest(request_file)
        if request_sha != EXPECTED_REQUEST_SHA256:
            raise ValueError("W1_H8_REQUEST_SHA_DRIFT:" + request_sha)
        limits = resource_guard()
        import numpy as np
        import _make_it_stand as native
        import _cherchi_core_boolean as boolean
        import _cherchi_rational_moments as arithmetic
        from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
        sys.path.insert(0,str(root / H8 / "source"))
        from probe_h8_native_cherchi import initial_ellipsoid_q, request_from_frozen
        from verify_h8_exact_moments import independent_ten_raw_moments
        request, settings, evidence = request_from_frozen(request_file)
        if evidence.get("original_author_cad") is not False:
            raise ValueError("W1_H8_AUTHOR_OR_CAD_SCOPE_DRIFT")
        q = np.asarray(initial_ellipsoid_q(request.target_origin),dtype=np.float64)
        signal.alarm(3600)
        evaluator = InProcessCherchiEvaluator(
            request, settings, normalization={"origin": [0.,0.,0.], "L":1.},
            branch_identity_policy="SOURCE_FEATURE_BRANCH_V2",
            rational_arithmetic_backend="NATIVE_GMP_SURFACE_V1", fixed_boundary_reuse=False,
            integral_profile="EXACT_GMP_V1", stage_observer=ledger.observe)
        if not evaluator.backend_identity.startswith(PINNED_CHERCHI_PREFIX):
            raise ValueError("W1_UNPINNED_CHERCHI_BACKEND")
        sample_started = time.monotonic_ns()
        evaluated = evaluator(q)
        material = ledger.observe("material_decode",lambda: evaluator.material(q))
        ledger.observe("same_call_validation",lambda:
                       evaluator.validate_same_call_material(material,q,request))
        faces = np.asarray(material["variable_faces"],dtype=np.int32)
        rational = material["variable_rational_vertices"]
        audit = ledger.observe("native_exact_boundary_audit",lambda:dict(
            native.audit_exact_rational_triangle_boundary(rational,faces,"AnyNonzero")))
        validate_native_audit(audit)
        fraction_ten = ledger.observe("independent_fraction_ten",lambda:
             independent_ten_raw_moments(rational,faces.tolist()))
        parity = checked_parity(material,evaluated,fraction_ten)
        def snapshot():
            with gzip.open(output/"same-call-material.json.gz","wt",encoding="utf-8",compresslevel=5) as fp:
                json.dump(material,fp,sort_keys=True,allow_nan=False)
        ledger.observe("json_snapshot",snapshot)
        sampled_wall_ns=time.monotonic_ns()-sample_started
        summary = ledger.summary()
        summary["strict_same_call_sample_wall_ns"] = sampled_wall_ns
        summary["setup_wall_ns"] = summary["setup_and_sample_wall_ns"]-sampled_wall_ns
        if sum(e["elapsed_ns"] for e in summary["exclusive_stages"])>sampled_wall_ns:
            raise ValueError("W1_EXCLUSIVE_STAGE_OVERLAP")
        if not summary["all_stages_passed"]:
            raise ValueError("W1_STAGE_FAILURE_NOT_ADMITTED")
        baseline = dict(schema="w1-baseline-performance-v1",
            scope="ONE_REAL_H8_SINGLE_Q_NOT_COMPLETE_SOLVER",
            input_request_sha256=request_sha, frozen_source_commit=FREEZE,
            native_binary_sha256=digest(native.__file__),
            cherchi_binary_sha256=digest(boolean.__file__),
            arithmetic_binary_sha256=digest(arithmetic.__file__),
            sample_count=1, samples=[dict(q=q.tolist(), timing=summary, checks=parity,
                exact_boundary_flags={k:audit[k] for k in AUDIT_TRUE},
                snapshot_sha256=digest(output/"same-call-material.json.gz"))],
            machine=dict(platform=platform.platform(),cpu_count=os.cpu_count(),
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                resource_limits=limits),
            run_status="PASSED_SINGLE_Q_STRICT_AUDIT", before_after_parity=None,
            completed_newton_solver=False, full_material_seal=False,
            paper_speed_qualified=False)
        write_new(output/"baseline-performance.json",baseline)
        write_new(output/"before_after.json",dict(schema="w1-before-after-v1",
            before=None,after=None,parity=None,end_to_end_speedup=None,
            completed=False,reason="No paired full native old/new runs or W0/W2 admission"))
        return baseline
    except BaseException as error:
        run_status.update(error=f"{type(error).__name__}: {error}", timing=ledger.summary())
        write_new(output/"failure.json",run_status)
        raise
    finally:
        signal.alarm(0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",required=True,type=Path)
    parser.add_argument("--request",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    report=evaluate(args.root,args.request,args.output)
    print(json.dumps({"status":report["run_status"],"samples":report["sample_count"]}))


if __name__=="__main__":
    main()

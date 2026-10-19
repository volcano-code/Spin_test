"""Single-request Cherchi adapter. Never silently promotes a derivative to ground truth.

Caller provides an already constructed InProcessCherchiEvaluator (or test double).
No solver runs, no shared core modifications, no hidden extra Cherchi evaluations.
"""
import hashlib
import math
import resource
import time
from pathlib import Path

try:
    from .native_cherchi_teacher import seal, vector
except ImportError:
    from native_cherchi_teacher import seal, vector

def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _rss_bytes():
    # Linux getrusage reports KiB; ru_maxrss is a process high-water mark,
    # NOT per-call peak allocation. Explicitly labelled in timing metadata.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)*1024

def evaluate_one(evaluator, q, *, model_path, native_module_path,
                 geometry, density, frame, derivative_contract=None,
                 split="excluded", exclusion_reason=None):
    """Return a sealed label even when the native call raises.

    This wrapper checks the frozen model/module bytes and does not infer
    smoothness from the evaluator's pointwise derivative_defined flag.
    Supply a separately established branch-neighborhood certificate as
    derivative_contract to admit J_D, otherwise it is withheld.
    """
    model_sha=sha256_file(model_path)
    native_sha=sha256_file(native_module_path)
    q=vector(q)
    native_authenticated=(
        type(evaluator).__module__=="make_it_stand.verification.cherchi_inprocess"
        and type(evaluator).__name__=="InProcessCherchiEvaluator"
        and hasattr(evaluator,"native")
        and Path(evaluator.native.__file__).resolve()==Path(native_module_path).resolve()
    )
    start=time.perf_counter()
    rss_before=_rss_bytes()
    output=None
    failure=None
    try:
        output=evaluator(tuple(q))
        if not isinstance(output,dict):
            raise ValueError("EVALUATOR_RETURN_NOT_MAPPING")
        variable=vector(output["variable_raw_moments"])
        total=vector(output["raw_moments"])
        fixed=vector(evaluator.fixed)
        if any(not math.isclose(total[i],variable[i]+fixed[i],rel_tol=1e-11,abs_tol=1e-11)
               for i in range(10)):
            raise ValueError("DOUBLE_COUNT_OR_FIXED_MISMATCH")
        if output.get("evaluation_map_identity")!=evaluator.context_identity:
            raise ValueError("EVALUATION_MAP_IDENTITY_MISMATCH")
        if not output.get("geometry_hash") or not output.get("topology_hash"):
            raise ValueError("MISSING_GEOMETRY_TOPOLOGY_PROOF")
        topology="OBSERVED_DISCRETE_MAP"
        derivative="UNKNOWN"
        jacobian=None
        if output.get("derivative_defined") and derivative_contract is not None:
            if not native_authenticated:
                raise ValueError("MOCK_OR_UNAUTHENTICATED_DERIVATIVE_NOT_ADMISSIBLE")
            if not isinstance(derivative_contract,dict) or not derivative_contract.get("verified_neighborhood"):
                raise ValueError("UNVERIFIED_DERIVATIVE_CONTRACT")
            # W0's contract is not released: provisional certificates must not
            # create training labels or valid Jacobians.
            if derivative_contract.get("schema")!="MomentContractV1" or not derivative_contract.get("contract_sha256"):
                raise ValueError("W0_MOMENT_CONTRACT_REQUIRED")
            jacobian=[vector(row) for row in output["moment_jacobian"]]
            derivative="VALID"
            topology="VALID"
        proof={"kind":"cherchi_same_call_discrete_map",
               "geometry_hash":output["geometry_hash"],
               "topology_hash":output["topology_hash"],
               "evaluation_map_identity":evaluator.context_identity,
               "boolean_backend_identity":output.get("boolean_backend_identity"),
               "derivative_identity":output.get("derivative_identity"),
               "native_cherchi":native_authenticated}
    except Exception as exc:
        variable=jacobian=fixed=None
        topology="FAILED"
        derivative="INVALID"
        proof={"kind":"failed_same_call","native_cherchi":native_authenticated}
        failure=f"{type(exc).__name__}: {exc}"
    elapsed=time.perf_counter()-start
    stages=dict(getattr(evaluator,"stage_seconds",{}) or {})
    stages["w2_total_wall_seconds"]=elapsed
    stages["w2_rss_process_hwm_before_bytes"]=float(rss_before)
    stages["w2_rss_process_hwm_after_bytes"]=float(_rss_bytes())
    if exclusion_reason:
        stages["w2_excluded_sample"]=0.0
    if failure is not None:
        split="excluded"
    # A successful numerical value with UNKNOWN derivative is not training truth.
    if derivative!="VALID":
        split="excluded"
    return seal(model_sha256=model_sha,native_module_sha256=native_sha,
        geometry=geometry,density=density,frame=frame,q=q,r_d=variable,j_d=jacobian,
        r_f=fixed,topology_status=topology,derivative_status=derivative,
        derivative_contract=derivative_contract if derivative=="VALID" else None,
        stage_seconds=stages,peak_rss_bytes=_rss_bytes(),exact_proof=proof,
        split=split,failure_reason=failure or exclusion_reason)

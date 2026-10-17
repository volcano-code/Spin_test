"""H7c benchmark statistics on real captured stage-profile reports; no fake timings."""
import argparse
import json
from pathlib import Path
from statistics import median
import math

def summarize(report):
    if report.get("schema")!="heart-h7-stage-profile-v1" or report.get("scope")!="HISTORICAL_V4_PROXY_NOT_ORIGINAL_EVAL60":
        raise ValueError("UNKNOWN_PROFILE_SCHEMA_OR_SCOPE")
    if report.get("formal_heart_qualified") is not False:
        raise ValueError("FORMAL_HEART_BENCHMARK_CLAIM_FORBIDDEN")
    groups=report.get("timings",{})
    if not groups or any(name not in ("python","native") for name in groups):
        raise ValueError("MISSING_OR_UNKNOWN_ARITHMETIC_BACKEND")
    results={}
    for backend,rows in groups.items():
        if not rows or any(not math.isfinite(r["wall_seconds"]) or r["wall_seconds"]<=0 for r in rows):
            raise ValueError("INVALID_REAL_WALL_TIME")
        stages=set().union(*(r.get("stages_seconds",{}).keys() for r in rows))
        if any(not math.isfinite(v) or v<0 for r in rows for v in r.get("stages_seconds",{}).values()):
            raise ValueError("INVALID_STAGE_TIME")
        wall=median(r["wall_seconds"] for r in rows)
        results[backend]=dict(repeats=len(rows),wall_median_seconds=wall,
            cpu_median_seconds=median(r["cpu_seconds"] for r in rows),
            stage_median_seconds={stage:median(r.get("stages_seconds",{}).get(stage,0.) for r in rows)
                                  for stage in sorted(stages)},
            unattributed_median_seconds=median(r["unattributed_seconds"] for r in rows),
            peak_rss_kib_max=max(r["process_peak_rss_kib"] for r in rows))
    ratio=None
    if len(results)==2:
        parity=report.get("backend_parity",{})
        if not parity.get("geometry_hash_equal") or not parity.get("backend_equal"):
            raise ValueError("NATIVE_GMP_GEOMETRY_OR_BACKEND_MISMATCH")
        if max(parity.get("moment_max_abs_delta",float("inf")),
               parity.get("jacobian_max_abs_delta",float("inf")))>1e-8:
            raise ValueError("NATIVE_GMP_MOMENT_OR_JACOBIAN_NOT_COMPARABLE")
        ratio=results["python"]["wall_median_seconds"]/results["native"]["wall_median_seconds"]
    return dict(schema="heart-h7c-descriptive-profile-summary-v1",
        historical_v4_proxy_only=True,formal_native_heart_performance_qualified=False,
        full_solve_measured=False,matched_environment_speed_ratio_python_over_native=ratio,
        arithmetic_backends=results,
        warning="Use only on native reports with pinned modules; CPU/RSS and wall time depend on the host.")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--report",required=True,type=Path)
    p.add_argument("--output",required=True,type=Path)
    a=p.parse_args()
    result=summarize(json.loads(a.report.read_text()))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open("x") as f:json.dump(result,f,indent=2,allow_nan=False);f.write("\n")
    print(json.dumps(result,indent=2))

if __name__=="__main__":main()

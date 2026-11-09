#!/usr/bin/env python3
"""Offline audit of valid M29.3.2 finite-difference columns.

Does not call Cherchi. Preserves partial branch-stable columns rather than
discarding an entire step because one or more directions cross a branch.
"""
from __future__ import annotations
import argparse, json, math
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np

def audit(summary_path,samples_path,output_path):
    summary=json.loads(Path(summary_path).read_text())
    if summary.get("schema")!="w1-m29-3-2-fresh-native-tangent-fd-v1":
        raise ValueError("M29_3_2_1_SUMMARY_SCHEMA_MISMATCH")
    rows=[json.loads(x) for x in Path(samples_path).read_text().splitlines() if x.strip()]
    if len(rows)!=summary.get("expected_function_evaluations"):
        raise ValueError("M29_3_2_1_SAMPLE_COUNT_MISMATCH")
    steps=[float(x) for x in summary["steps"]]
    B=np.asarray(summary["tangent_basis"],dtype=float)
    J=np.asarray(summary["analytic_tangent_jacobian"],dtype=float)
    if B.shape!=(10,9) or J.shape!=(10,9):
        raise ValueError("M29_3_2_1_BASE_MATRIX_SHAPE")
    grouped=defaultdict(dict)
    for row in rows:
        key=(float(row["step"]),int(row["direction"]))
        side=row["side"]
        if side not in ("plus","minus") or side in grouped[key]:
            raise ValueError("M29_3_2_1_DUPLICATE_OR_INVALID_SIDE")
        grouped[key][side]=row
    if len(grouped)!=len(steps)*9 or any(set(v)!={"plus","minus"} for v in grouped.values()):
        raise ValueError("M29_3_2_1_INCOMPLETE_PERTURBATION_PAIRS")
    per_step={}
    valid_by_step={}
    mismatch_counters=defaultdict(Counter)
    for h in steps:
        valid=[];columns={};reasons=Counter()
        for j in range(9):
            pair=grouped[(h,j)]
            p,m=pair["plus"],pair["minus"]
            same_base=bool(p.get("topology_matches_base")) and bool(m.get("topology_matches_base"))
            same_pair=p.get("topology_hash")==m.get("topology_hash")
            same_operation=p.get("operation")==m.get("operation")
            same_surface=p.get("surface_type")==m.get("surface_type")
            same_cap=p.get("cap_face_count")==m.get("cap_face_count")
            checks={"base_topology":same_base,"pair_topology":same_pair,
                    "operation":same_operation,"surface_type":same_surface,"cap_count":same_cap}
            for name,ok in checks.items():
                if not ok: reasons[name]+=1
            if not all(checks.values()):
                continue
            fp=np.asarray(p["ten"],dtype=float);fm=np.asarray(m["ten"],dtype=float)
            if fp.shape!=(10,) or fm.shape!=(10,) or not np.isfinite(fp).all() or not np.isfinite(fm).all():
                reasons["invalid_ten"]+=1;continue
            col=(fp-fm)/(2*h)
            columns[j]=col;valid.append(j)
        metrics={}
        if valid:
            fd=np.column_stack([columns[j] for j in valid])
            ana=J[:,valid]
            diff=fd-ana
            col_den=np.maximum(np.linalg.norm(ana,axis=0),1e-12)
            metrics={
              "global_relative_frobenius_error_on_valid_columns":float(np.linalg.norm(diff)/max(np.linalg.norm(ana),1e-15)),
              "per_direction_relative_error":{str(j):float(np.linalg.norm(columns[j]-J[:,j])/max(np.linalg.norm(J[:,j]),1e-12)) for j in valid},
              "max_direction_relative_error":float(np.max(np.linalg.norm(diff,axis=0)/col_den)),
              "valid_direction_count":len(valid)}
        per_step[str(h)]={"valid_directions":valid,"invalid_direction_count":9-len(valid),
                          "invalid_reasons":dict(reasons),"partial_metrics":metrics}
        valid_by_step[h]=columns
        mismatch_counters[str(h)]=reasons
    common=[]
    refinement=[]
    for h0,h1 in zip(steps,steps[1:]):
        dirs=sorted(set(valid_by_step[h0])&set(valid_by_step[h1]))
        for j in dirs:
            a=valid_by_step[h0][j];b=valid_by_step[h1][j]
            refinement.append({"coarse_step":h0,"fine_step":h1,"direction":j,
                "relative_change":float(np.linalg.norm(a-b)/max(np.linalg.norm(b),1e-12))})
    for h in steps:
        common=sorted(set(common)|set(valid_by_step[h]))
    # Summarize which recorded discrete feature fields change against the M9 anchor.
    base_hash=summary["base_m9_topology_hash"]
    against=Counter()
    for row in rows:
        if row.get("topology_hash")!=base_hash:
            against["topology_hash_mismatch"]+=1
        for field in ("operation","surface_type","cap_face_count"):
            # All are expected to be stable in this particular run.
            if field=="operation" and row.get(field)!="difference": against[field+"_changed"]+=1
            if field=="surface_type" and row.get(field)!="ELLIPSOID": against[field+"_changed"]+=1
            if field=="cap_face_count" and row.get(field)!=0: against[field+"_changed"]+=1
    result={
      "schema":"w1-m29-3-2-1-partial-fd-audit-v1",
      "source_summary":str(summary_path),"source_samples":str(samples_path),
      "sample_count":len(rows),"step_results":per_step,
      "directions_valid_at_any_step":common,
      "directions_never_valid":sorted(set(range(9))-set(common)),
      "cross_step_refinement":refinement,
      "all_operations_difference":all(x.get("operation")=="difference" for x in rows),
      "all_surface_types_ellipsoid":all(x.get("surface_type")=="ELLIPSOID" for x in rows),
      "all_cap_counts_zero":all(x.get("cap_face_count")==0 for x in rows),
      "topology_hash_mismatches":against["topology_hash_mismatch"],
      "important_limit":"This offline audit computes errors only for columns whose plus and minus evaluations both match the frozen base feature-branch hash. It cannot identify which omitted topology-hash component changed because M29.3.2 receipts did not persist source-face and output-feature-face component hashes. It does not certify a neighborhood or Newton."
    }
    Path(output_path).write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps({
      "status":"PARTIAL_COLUMNS_AUDITED",
      "valid_by_step":{h:v["valid_directions"] for h,v in per_step.items()},
      "directions_valid_at_any_step":common,
      "directions_never_valid":result["directions_never_valid"],
      "output":str(output_path)},indent=2))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--summary",required=True)
    p.add_argument("--samples",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args();audit(a.summary,a.samples,a.output)
if __name__=="__main__":main()

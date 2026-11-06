#!/usr/bin/env python3
"""W1 M29.0: one read-only gate for the pinned native numerical campaign.

This orchestrator ONLY runs existing M13/M19/M23 preflights. It does not fetch
sources, compile extensions, call Cherchi Boolean, evaluate moments, or run
Newton. A green result means the native campaign may be launched manually;
it is not a scientific admission or a speedup result.
"""
from __future__ import annotations
import argparse, importlib.util, json, sys
from pathlib import Path

EXPECTED_BRANCH="research/neuralmoments-w1-native-20261019"
H8C_SHA="78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7"
H8E_SHA="14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38"
NATIVE=("_make_it_stand","_cherchi_core_boolean","_cherchi_rational_moments")
M13_STATE="READY_TO_BUILD"
M19_STATE="READY_FOR_REAL_H8E_PROFILING"
M23_STATE="READY_TO_RUN_FOUR_INDEPENDENT_SOLVER_PROCESSES"

def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    if spec is None or spec.loader is None:
        raise ImportError("M29_PREFLIGHT_MODULE_LOAD_FAILED:"+str(path))
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

def _module_hashes_m19(report):
    try:
        mods=report["checks"]["native_modules"]["modules"]
        return {name:mods[name]["sha256"] for name in NATIVE}
    except (KeyError,TypeError):
        return {}

def _module_hashes_m23(report):
    try:
        return {name:report["module_sha256"][name] for name in NATIVE}
    except (KeyError,TypeError):
        return {}

def aggregate(m13_report,m19_report,m23_report):
    blockers=[]
    checks={}
    def check(name,ok,reason):
        checks[name]={"status":"PASS" if ok else "BLOCKED"}
        if not ok:
            checks[name]["reason"]=reason
            blockers.append(name+":"+reason)
    check("m13_pinned_native_build_preflight",
          m13_report.get("state")==M13_STATE and not m13_report.get("blockers"),
          "M13_NOT_READY")
    check("m19_real_h8e_profile_preflight",
          m19_report.get("state")==M19_STATE and not m19_report.get("blockers"),
          "M19_NOT_READY")
    check("m23_full_newton_abba_preflight",
          m23_report.get("status")==M23_STATE and not m23_report.get("blockers"),
          "M23_NOT_READY")
    h8c=m19_report.get("archive_sha256") or m19_report.get("checks",{}).get("archive",{}).get("details",{}).get("zip_sha256")
    h8e=m23_report.get("archive_sha256")
    check("h8c_archive_identity",h8c==H8C_SHA,"H8C_ARCHIVE_SHA_MISMATCH_OR_UNVERIFIED")
    check("h8e_archive_identity",h8e==H8E_SHA,"H8E_ARCHIVE_SHA_MISMATCH_OR_UNVERIFIED")
    m19mods=_module_hashes_m19(m19_report)
    m23mods=_module_hashes_m23(m23_report)
    check("three_native_modules_unique",
          set(m19mods)==set(NATIVE) and set(m23mods)==set(NATIVE),
          "NATIVE_MODULES_MISSING_OR_NONUNIQUE")
    check("native_module_hashes_stable",
          bool(m19mods) and m19mods==m23mods,
          "M19_M23_NATIVE_MODULE_SHA_MISMATCH")
    return {
      "schema":"w1-m29-native-campaign-readiness-v1",
      "state":"READY_FOR_M29_NATIVE_NUMERICAL_CAMPAIGN" if not blockers else "BLOCKED",
      "checks":checks,"blockers":blockers,
      "expected":{"branch":EXPECTED_BRANCH,"h8c_archive_sha256":H8C_SHA,
                  "h8e_archive_sha256":H8E_SHA,"native_modules":list(NATIVE)},
      "production_native_calls":0,"production_moment_comparisons":0,
      "jacobian_certified":False,"newton_runs":0,
      "production_admitted":False,"full_solver_speedup":None,
      "interpretation":"Readiness only. Does not prove numerical correctness or admit W0/W2."
    }

def run(root,h8c,h8e,module_dirs,output):
    root=Path(root).resolve(strict=True)
    h8c=Path(h8c).resolve(strict=True);h8e=Path(h8e).resolve(strict=True)
    output=Path(output)
    if output.exists():raise FileExistsError("M29_OUTPUT_ALREADY_EXISTS")
    perf=root/"research/NeuralMoments/performance"
    if not perf.is_dir():raise FileNotFoundError("M29_W1_PERFORMANCE_DIRECTORY_MISSING")
    sys.path.insert(0,str(perf))
    m13=load_module(perf/"m13_pinned_native_build.py","m29_m13")
    m19=load_module(perf/"m19_real_h8e_profiler.py","m29_m19")
    m23=load_module(perf/"m23_real_newton_abba.py","m29_m23")
    # allow_source_fetch=True only changes a read-only status to NEEDS_PINNED_FETCH;
    # it does not clone, checkout, write, or mutate any source tree.
    r13=m13.preflight(root,h8c,allow_source_fetch=True)
    r19=m19.environment_preflight(root,h8c,module_dirs)
    r23=m23.preflight(root,h8e,module_dirs)
    result=aggregate(r13,r19,r23)
    output.mkdir(parents=True)
    (output/"m13-preflight.json").write_text(json.dumps(r13,indent=2,sort_keys=True)+"\n")
    (output/"m19-preflight.json").write_text(json.dumps(r19,indent=2,sort_keys=True)+"\n")
    (output/"m23-preflight.json").write_text(json.dumps(r23,indent=2,sort_keys=True)+"\n")
    (output/"m29-readiness.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",required=True)
    p.add_argument("--h8c-archive",required=True)
    p.add_argument("--h8e-archive",required=True)
    p.add_argument("--module-dir",action="append",default=[])
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=run(a.root,a.h8c_archive,a.h8e_archive,a.module_dir,a.output)
    print(json.dumps({"state":result["state"],"blockers":result["blockers"]},sort_keys=True))
    raise SystemExit(0 if result["state"]=="READY_FOR_M29_NATIVE_NUMERICAL_CAMPAIGN" else 2)

if __name__=="__main__":main()

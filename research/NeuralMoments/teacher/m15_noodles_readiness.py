"""W2 M15 Noodles V7 admission: evidence gate, not native execution.

Finite 81-point geometry equivalence and recorded numerical convergence do
not establish a complete frozen one-request native teacher.
"""
import json,hashlib
from pathlib import Path

BASE="experiments/faster_core_repair_20261012"
REQUIRED={
 "finite":BASE+"/noodles-formal-finite-sample-summary-01.json",
 "request":BASE+"/noodles-balanced-request-freeze-job-01/output/request.json",
 "derivatives":BASE+"/noodles-formal-cherchi-derivatives-job-01/output/report.json",
 "connection":BASE+"/noodles-formal-cherchi-connection-job-01/output/report.json",
}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def inspect(root):
    root=Path(root)
    missing=[name for name,path in REQUIRED.items() if not (root/path).is_file()]
    result={"schema":"w2-m15-noodles-v7-native-preflight-v1",
        "status":"BLOCKED_MISSING_FROZEN_DATA" if missing else "REQUIRES_NATIVE_VERIFICATION",
        "missing_required_sources":missing,"new_native_cherchi_calls":0,
        "new_native_teacher_labels":0,"J_D":None,"training_admitted":False,
        "historical_finite_point_data_is_native_teacher_certification":False}
    finite=root/REQUIRED["finite"]
    if finite.is_file():
        f=json.loads(finite.read_text())
        result["finite_sample"]={"count":f.get("point_count"),
            "maximum_fd_error":f.get("maximum_fd_error"),
            "neighborhood_certification":f.get("neighborhood_certification"),
            "case_admission":f.get("case_admission"),"file_sha256":sha(finite)}
        if f.get("neighborhood_certification") is not False or f.get("case_admission") is not False:
            raise ValueError("NOODLES_FROZEN_FINITE_SCIENTIFIC_FLAGS_CHANGED")
    if not missing:
        frozen=json.loads((root/REQUIRED["request"]).read_text())
        numeric=json.loads((root/REQUIRED["derivatives"]).read_text())
        link=json.loads((root/REQUIRED["connection"]).read_text())
        if frozen.get("classification")!="RECONSTRUCTED_METHOD_VALIDATION":
            raise ValueError("NOODLES_FROZEN_CASE_SCOPE_CHANGED")
        if numeric.get("neighborhood_certification") is True or link.get("case_admission") is True:
            raise ValueError("UNVERIFIED_NOODLES_TRAINING_PROMOTION")
        result["request_sha256"]=sha(root/REQUIRED["request"])
        result["status"]="FROZEN_FILES_PRESENT_NATIVE_BINARY_AND_ONE_CALL_STILL_REQUIRED"
    return result
def main(argv=None):
    import argparse
    p=argparse.ArgumentParser();p.add_argument("--repo-root",required=True);p.add_argument("--output",required=True)
    a=p.parse_args(argv)
    output=Path(a.output)
    with output.open("x") as f:
        json.dump(inspect(a.repo_root),f,indent=2,sort_keys=True,allow_nan=False);f.write("\n")
if __name__=="__main__":main()

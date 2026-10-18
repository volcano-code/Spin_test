"""Cloud-hosted, freshly compiled *one-point* Heart V4 Cherchi smoke probe.

This probe never claims the byte-identical old H6 binary, formal eval60,
neighborhood derivative admission, Newton convergence, or author CAD reproduction.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parents[1]
H6 = HERE.parent / "Cherchi_H6"
sys.path.insert(0, str(H6 / "source"))
from heart_h6_authority import verify_v4_proxy
from probe_h6_feature_branches import packet_features
from replay_25_cherchi import exact_rational_audit, source_fingerprint, BACKEND


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(fixture, registration, report):
    import _make_it_stand as native
    import _cherchi_core_boolean as cherchi
    doc, reg = verify_v4_proxy(fixture, registration)
    original = json.loads((H6/"evidence/three-column-feature-classification.json").read_text())["rows"][0]
    raw=doc["requests"][1]["request"]
    opts=doc["evaluator_settings"]
    q=np.asarray(reg["event"]["quadric_coefficients"],dtype=np.float64)
    design=np.asarray(raw["design_vertices"],dtype=np.float64)
    faces=np.asarray(raw["design_faces"],dtype=np.int32)
    origin=np.asarray(raw["target_origin"],dtype=np.float64)
    axes=np.asarray(raw["target_axes"],dtype=np.float64)
    target_design=(design-origin)@axes.T
    settings=native.SpinTriangulationSettings()
    for name in ("icosphere_subdivisions","maximum_radius_doublings",
                 "truncation_radius","algebraic_finite_map"):
        setattr(settings,name,opts[name])
    settings.maximum_icosphere_subdivisions=settings.icosphere_subdivisions
    settings.retain_fixed_normal_provenance=True
    settings.paper_projective_hyperboloid=True

    t=time.perf_counter()
    source=native.evaluate_spin_it_faster_source_motion(q,target_design,settings)
    src_t=time.perf_counter()-t
    if not source["defined"] or not source["side_selection_defined"]:
        raise ValueError("NATIVE_SOURCE_UNDEFINED:"+str(source.get("diagnostic")))
    sv=(np.asarray(source["vertices"])@axes.T+origin)
    sf=np.asarray(source["faces"],dtype=np.int32)
    operation="intersection" if source["interior_is_positive"] else "difference"
    t=time.perf_counter()
    packet=cherchi.boolean(design.tolist(),faces.tolist(),sv.tolist(),sf.tolist(),operation)
    bool_t=time.perf_counter()-t
    if packet.get("backend")!=BACKEND:raise ValueError("NON_CHERCHI_BACKEND")
    t=time.perf_counter()
    audit=exact_rational_audit(native,packet)
    audit_t=time.perf_counter()-t
    observed={**source_fingerprint(source,sf),
              **packet_features(packet,design,sv,operation)}
    differ={name:{"historical":original[name],"cloud":observed[name]}
            for name in observed if name in original and original[name]!=observed[name]}
    result={
        "schema":"heart-h7-cloud-native-new-build-single-q-v1",
        "scope":"HISTORICAL_V4_PROXY_NOT_AUTHENTIC_EVAL60",
        "native_source_and_cherc_boolean_and_rational_audit_ran":True,
        "fresh_native_identity_not_old_h6":True,
        "original_eval60_reproduced":False,
        "formal_heart_newton_converged":False,
        "derivative_branch_certified":False,
        "native_sha256":digest(native.__file__),
        "cherchi_sha256":digest(cherchi.__file__),
        "fixture_sha256":digest(fixture),
        "q":q.tolist(),
        "dimensions":{"design_faces":len(faces),"source_faces":len(sf),
                      "material_faces":len(packet["faces"]),
                      "material_vertices":len(packet["exact_vertices"])},
        "native_exact_rational_audit":audit,
        "stages_wall_seconds":{"source":src_t,"cherchi_boolean":bool_t,
                               "native_rational_audit":audit_t},
        "h6_historical_base_feature_equal":not bool(differ),
        "h6_historical_base_feature_differences":differ,
        "hostname":os.environ.get("RUNNER_OS","unknown"),
        "backend":packet["backend"]
    }
    report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
    with report.open("x") as f:json.dump(result,f,indent=2,allow_nan=False);f.write("\n")
    print("CLOUD_CHERCHI_RESULT",json.dumps({
        k:result[k] for k in ("dimensions","stages_wall_seconds",
                    "h6_historical_base_feature_equal")}),flush=True)
    return result

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--fixture",type=Path,required=True)
    parser.add_argument("--registration",type=Path,
        default=H6/"input/registered-eval60-coefficients.json")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    run(args.fixture,args.registration,args.output)

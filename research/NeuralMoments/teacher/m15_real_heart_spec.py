"""W2 M15: produce source-pinned H8f native one-call spec, never invent a run.

The frozen source OBJ uses millimetres; Faster requests use source / 25.
This materializer does not authorize derivatives, Newton, or CAD equivalence.
"""
import hashlib,json,zipfile
from pathlib import Path

ARCHIVE_SHA="99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9"
REQUEST_SHA="1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c"
REPORT_SHA="28e5a641da153b08a7f15f4abb87336c797f1e85b6f2742fc025274c231f53c5"
SOURCE_SHA="0bcc187b3005478baa586a6d6f450e73811ca342"

def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(",",":"),allow_nan=False)
def require(ok,error):
    if not ok:raise ValueError(error)

def create_heart_spec(archive,directory):
    try:
        from .native_cherchi_teacher import digest
        from .frozen_model_binding import validate_model_binding
    except ImportError:
        from native_cherchi_teacher import digest
        from frozen_model_binding import validate_model_binding
    import numpy as np
    archive=Path(archive)
    require(archive.is_file() and sha(archive.read_bytes())==ARCHIVE_SHA,"UNPINNED_H8F_HISTORIC_ARCHIVE")
    with zipfile.ZipFile(archive) as z:
        request_raw=z.read("artifacts/h8-request/prepared-request.json")
        report_raw=z.read("artifacts/h8f-all81-points/report.json")
        point_raw=z.read("artifacts/h8f-all81-points/point-000.json")
        original_obj=z.read("artifacts/h8-input/initial_top.obj")
    require(sha(request_raw)==REQUEST_SHA and sha(report_raw)==REPORT_SHA,
            "FROZEN_H8F_REQUEST_REPORT_SHA_DRIFT")
    frozen=json.loads(request_raw);report=json.loads(report_raw)
    point=json.loads(point_raw)
    require(report["production_cherchi_calls"]==81 and
            report["qualified_branch_neighborhood"] is False and
            report["complete_eighty_one_samples"] is False,
            "UNEXPECTED_H8F_SCIENTIFIC_STATE")
    require(point["index"]==0 and len(point["coefficients"])==10,"POINT000_NOT_FROZEN")
    outer=frozen["request"]
    scale=frozen["evidence"]["normalized_scale_mm_per_unit"]
    require(scale==25.0 and outer["original_units_per_normalized_unit"]==0.025,
            "H8F_MM_TO_METER_FRAME_DRIFT")
    verts=[];faces=[]
    for line in original_obj.decode("utf-8").splitlines():
        tokens=line.split()
        if not tokens or tokens[0].startswith("#"):continue
        if tokens[0]=="v" and len(tokens)==4:
            verts.append([float(s) for s in tokens[1:]])
        elif tokens[0]=="f" and len(tokens)==4 and all(s.isdigit() for s in tokens[1:]):
            faces.append([int(s)-1 for s in tokens[1:]])
        else:raise ValueError("UNSUPPORTED_FROZEN_OBJ_RECORD")
    v=np.asarray(verts,dtype=np.float64)/scale
    original=np.asarray(outer["outer_vertices"],dtype=np.float64)
    require(v.shape==original.shape and v.tobytes()==original.tobytes(),
            "H8F_SOURCE_TO_REQUEST_VERTICES_NOT_IDENTICAL")
    require(faces==outer["outer_faces"],"H8F_SOURCE_TO_REQUEST_FACES_NOT_IDENTICAL")
    output=Path(directory);output.mkdir(parents=True,exist_ok=False)
    model=output/"normalized_h8f_point000_outer.obj"
    with model.open("x",encoding="utf-8") as stream:
        stream.write("# H8f derived normalized OBJ; never author CAD\n")
        for row in original:stream.write("v "+" ".join(repr(float(t)) for t in row)+"\n")
        for row in faces:stream.write("f "+" ".join(str(int(t)+1) for t in row)+"\n")
    proof=validate_model_binding(model,outer,
        {"mode":"OBJ_IS_INPUT_NORMALIZED_OUTER_V1"})
    require(proof["status"]=="EXACT_BINARY64_ORDERED_OUTER_MESH_MATCH",
            "NORMALIZED_OBJ_RELOAD_MISMATCH")
    c=point["coefficients"]
    spec={
        "schema":"w2-one-cherchi-request-v3","source_sha":SOURCE_SHA,
        "model_path":str(model.resolve()),"expected_model_sha256":sha(model.read_bytes()),
        "expected_native_module_sha256":report["actual_native_sha256"],
        "request":outer,"evaluator_settings":frozen["evaluator_settings"],
        "native_c":c,"expected_native_c_sha256":digest(c),
        "reference_absolute_tolerances":[1e-10]*10,
        "model_geometry_binding":{"mode":"OBJ_IS_INPUT_NORMALIZED_OUTER_V1"},
        "normalization":{"origin":[0.,0.,0.],"L":1.},
        "geometry":{"case":"H8F_RECONSTRUCTED_CAD_NOT_AUTHOR","original_obj_sha256":sha(original_obj),
                    "historical_zip_sha256":ARCHIVE_SHA,"historical_point_sha256":sha(point_raw)},
        "frame":{"kind":"INPUT_NORMALIZED_TARGET_V1","source_unit":"millimetres",
                 "original_unit_metres_per_normalized":0.025},
    }
    specfile=output/"single_native_heart_spec.json"
    with specfile.open("x",encoding="utf-8") as f:json.dump(spec,f,sort_keys=True,indent=2,allow_nan=False)
    attestation={"schema":"w2-m15-real-heart-preparation-v1",
        "historical_workflow_conclusion":"failure","new_native_calls":0,
        "original_source_obj_sha256":sha(original_obj),
        "normalized_model_sha256":sha(model.read_bytes()),
        "model_vertices":len(verts),"model_faces":len(faces),
        "exact_outer_binding_verified":True,
        "frozen_request_sha256":REQUEST_SHA,"source_zip_sha256":ARCHIVE_SHA,
        "spec_file_sha256":sha(specfile.read_bytes()),"J_D":None,"training_admitted":False}
    with (output/"preparation_attestation.json").open("x") as f:
        json.dump(attestation,f,sort_keys=True,indent=2,allow_nan=False)
    return attestation


def main(argv=None):
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--archive",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args(argv)
    result=create_heart_spec(a.archive,a.output)
    print(canonical(result))

if __name__=="__main__":main()

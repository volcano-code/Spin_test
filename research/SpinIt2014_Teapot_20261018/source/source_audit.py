"""Audit the UNMODIFIED Utah Teapot OBJ before any remeshing or mass evaluation.
This stage does not claim the mesh is watertight or reproduce original paper CAD.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from collections import Counter
import numpy as np
import trimesh
SOURCE_COMMIT="8a4f8642acaf43f9cd7b67858a1502e1055ef202"
SOURCE_BLOB_SHA="c839837bfc09f5d5bac4aa757fcbd9f16ddd7ec1"
def audit(input_path:Path,output_dir:Path):
    mesh=trimesh.load(input_path,force="mesh",process=False)
    if not isinstance(mesh,trimesh.Trimesh):raise ValueError("TEAPOT_NOT_TRIANGLE_MESH")
    pts=np.asarray(mesh.vertices)
    face=np.asarray(mesh.faces)
    if pts.ndim!=2 or pts.shape[1]!=3 or face.ndim!=2 or face.shape[1]!=3 or not np.isfinite(pts).all():
        raise ValueError("TEAPOT_INVALID_COORDINATES")
    if (face<0).any() or (face>=len(pts)).any():raise ValueError("TEAPOT_BAD_FACE_INDICES")
    # Count geometric edges after exactly matching OBJ coordinate keys; face
    # indices may intentionally duplicate points across patch seams.
    _,inverse=np.unique(pts,axis=0,return_inverse=True)
    geom_faces=inverse[face]
    directed=np.vstack((geom_faces[:,[0,1]],geom_faces[:,[1,2]],geom_faces[:,[2,0]]))
    edges=np.sort(directed,axis=1)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    counts_by_multiplicity={str(k):int(v) for k,v in sorted(Counter(map(int,counts)).items())}
    connected=mesh.split(only_watertight=False)
    report=dict(schema="spin-it-2014-teapot-original-obj-v1",
         classification="PUBLIC_NEWELL_TEAPOT_NOT_VERIFIED_AUTHOR_EXACT_CAD",
         source_url="https://github.com/alecjacobson/common-3d-test-models/blob/"+SOURCE_COMMIT+"/data/teapot.obj",
         upstream_commit=SOURCE_COMMIT,upstream_git_blob_sha1=SOURCE_BLOB_SHA,
         input_sha256=hashlib.sha256(input_path.read_bytes()).hexdigest(),
         source_bytes=input_path.stat().st_size,vertices=len(pts),faces=len(face),
         source_mesh_bounds=mesh.bounds.tolist(),source_axis_up="Y_UP",
         original_indexed_watertight=bool(mesh.is_watertight),
         winding_consistent_original=bool(mesh.is_winding_consistent),
         geographic_unique_vertices=len(np.unique(pts,axis=0)),
         geographic_edge_incidence=counts_by_multiplicity,
         geometric_closed_under_exact_identical_vertices=bool(np.all(counts==2)),
         original_indexed_connected_components=len(connected),
         output_design_domain_created=False,
         mass_integral_authoritative=False,spin_it_paper_optimizer_executed=False)
    output_dir.mkdir(parents=True,exist_ok=True)
    (output_dir/"original-source-audit.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    return report
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();print(json.dumps(audit(a.input,a.output),indent=2))

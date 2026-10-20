#!/usr/bin/env python3
"""W4 P13 native CSG failure audit: reads saved native OBJ, never repairs it.

Zero process exit is not a geometry proof. Do not call this an optimized or
W0-approved material. This diagnostic is deliberately independent of CGAL.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
import trimesh

SCHEMA="W4P13NativeShaftJunctionForensicsV1"


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audit(mesh_path, native_log=None):
    mesh_path=Path(mesh_path)
    mesh=trimesh.load_mesh(mesh_path,process=False)
    v=np.asarray(mesh.vertices,dtype=np.float64)
    f=np.asarray(mesh.faces,dtype=np.int64)
    if f.ndim!=2 or f.shape[1]!=3 or not np.isfinite(v).all():
        raise ValueError("NATIVE_OUTPUT_MALFORMED")
    keys=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]],axis=0),axis=1)
    edges,count=np.unique(keys,axis=0,return_counts=True)
    hist={str(int(k)):int(n) for k,n in zip(*np.unique(count,return_counts=True))}
    abnormal=np.flatnonzero(count!=2)
    areas=np.asarray(mesh.area_faces)
    bad_face_ids=np.flatnonzero(areas<=1e-14)
    witness=[]
    for i in abnormal[:24]:
        a,b=map(int,edges[i])
        witness.append(dict(vertex_indices=[a,b],incidence=int(count[i]),
                            a=v[a].tolist(),b=v[b].tolist()))
    native=None
    if native_log is not None:
        native=json.loads(Path(native_log).read_text())
        if native.get('exit')!=0:
            raise ValueError('NATIVE_PROCESS_FAILED_NOT_GEOMETRY_AUDIT')
        if native.get('sha256') and native['sha256']!=sha256(mesh_path):
            raise ValueError('NATIVE_OUTPUT_AND_RECEIPT_SHA_MISMATCH')
    result=dict(schema=SCHEMA,
        status='NUMERIC_CLOSED_SURFACE' if not len(abnormal) and mesh.is_volume and not len(bad_face_ids)
               else 'REJECTED_NONMANIFOLD_OR_DEGENERATE_NATIVE_OUTPUT',
        actual_native_result_sha256=sha256(mesh_path),
        native_producer='PINNED_CHERCHI_7bd6c269_REFERENCE_CLI' if native is not None else 'UNVERIFIED_CLI',
        native_exit_code=native.get('exit') if native else None,
        vertices=int(len(v)),triangles=int(len(f)),
        edge_incidence_histogram=hist,
        non_two_incident_edges=int(len(abnormal)),
        low_area_triangles=int(len(bad_face_ids)),
        minimum_triangle_area=float(min(areas)),
        watertight=bool(mesh.is_watertight),
        consistent_winding=bool(mesh.is_winding_consistent),
        is_volume=bool(mesh.is_volume),
        signed_surface_tetra_volume=float(mesh.volume),
        bbox=v.min(axis=0).tolist()+v.max(axis=0).tolist(),
        bad_edge_witnesses=witness,
        small_face_witnesses=[dict(face_index=int(i),area=float(areas[i]),
                                   vertices=v[f[i]].tolist()) for i in bad_face_ids[:12]],
        declared_mesh_legal=False,
        exact_native_material_certified=False,
        W0_design_authorized=False,
        material_partition_admitted=False,
        optimized=False)
    return result


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--mesh',type=Path,required=True)
    p.add_argument('--native-log',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=audit(a.mesh,a.native_log)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:result[k] for k in
       ('status','non_two_incident_edges','low_area_triangles','watertight','is_volume')}))
    if result['status']!='NUMERIC_CLOSED_SURFACE':
        raise SystemExit(2)


if __name__=='__main__':main()

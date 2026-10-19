#!/usr/bin/env python3
"""Single pinned Cherchi reference *CLI* three-mesh union on W4 Teapot P1.

Runs the 2022 Cherchi booleans algorithm via its original main.cpp executable.
It never invokes CGAL/OpenSCAD, including on native failure. Upstream uses
exact-predicate constructions; its OBJ output is floating-point, NOT an exact
rational solids certificate. F/D optimization and MuJoCo remain separate gates.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import numpy as np
import trimesh

from p2_self_intersection import check_nonincident_triangle_contacts

P0_SHA = '1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4'
P1_SHA = '3b13a006976093f86b733cd1a00c57d70a66e2fc8dca1c4a157bb18f93a7db47'
UPSTREAM_COMMIT = '7bd6c2697695f555f9a15d7e154e084d841316f0'
UPSTREAM_MAIN_BLOB = '3f65d2a0f83b10629f99ed5dcd2781409cdca4b5'
SCHEMA = 'W4P7CherchiReferenceNativeUnionV1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def native_identity(binary, source):
    binary,source = Path(binary).resolve(),Path(source).resolve()
    if not binary.is_file() or not os.access(binary,os.X_OK):
        raise ValueError('NATIVE_CHERCHI_REFERENCE_BINARY_REQUIRED')
    if binary.name!='w4_cherchi_reference_native':
        raise ValueError('UNEXPECTED_CHERCHI_REFERENCE_BINARY_NAME')
    if not (source/'main.cpp').is_file():
        raise ValueError('PINNED_REFERENCE_MAIN_MISSING')
    revision=subprocess.run(['git','-C',str(source),'rev-parse','HEAD'],
            capture_output=True,text=True,check=True).stdout.strip()
    blob=subprocess.run(['git','-C',str(source),'hash-object','main.cpp'],
            capture_output=True,text=True,check=True).stdout.strip()
    if revision!=UPSTREAM_COMMIT or blob!=UPSTREAM_MAIN_BLOB:
        raise ValueError('PINNED_CHERCHI_REFERENCE_REVISION_OR_MAIN_MISMATCH')
    return dict(upstream_repository='gcherchi/InteractiveAndRobustMeshBooleans',
                upstream_commit=revision,upstream_main_git_blob=blob,
                binary_sha256=sha(binary),binary_name=binary.name,
                operation='UNION',algorithm='CHERCHI_INTERACTIVE_ROBUST_MESH_BOOLEANS_2022')


def write_obj(path,mesh):
    """Non-mutating export with precise vertex decimal formatting."""
    vv=np.asarray(mesh.vertices,dtype=np.float64)
    ff=np.asarray(mesh.faces,dtype=np.int64)
    if len(vv)<4 or len(ff)<4 or not np.isfinite(vv).all():
        raise ValueError('EMPTY_OR_NONFINITE_INPUT_MESH')
    with Path(path).open('w',encoding='ascii',newline='\n') as f:
        f.write('# W4 P7 Cherchi source operand; do not identify as author original\n')
        for xyz in vv:f.write('v '+' '.join(format(float(x),'.17g') for x in xyz)+'\n')
        for a,b,c in ff:f.write(f'f {a+1} {b+1} {c+1}\n')


def validate_input(p0,p1):
    if sha(p0)!=P0_SHA or sha(p1)!=P1_SHA:
        raise ValueError('PINNED_P0_OR_P1_SHA_MISMATCH')
    mesh=trimesh.load_mesh(p1,process=False)
    components=sorted(mesh.split(only_watertight=False),
                      key=lambda m:(-len(m.faces),-m.volume))
    if sorted(len(x.faces) for x in components)!=[840,840,4800]:
        raise ValueError('PINNED_P1_COMPONENT_COUNTS_MISMATCH')
    for i,m in enumerate(components):
        if not m.is_volume or m.volume<=0:
            raise ValueError(f'P1_COMPONENT_{i}_NOT_CLOSED_ORIENTED')
    return components


def check_native_output(path,*,strict=True):
    mesh=trimesh.load_mesh(path,process=False)
    if not isinstance(mesh,trimesh.Trimesh) or mesh.faces.size==0:
        raise ValueError('NATIVE_CHERCHI_OUTPUT_EMPTY')
    v=np.asarray(mesh.vertices,dtype=np.float64)
    f=np.asarray(mesh.faces,dtype=np.int64)
    edges=np.asarray(mesh.edges_sorted)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    contact=check_nonincident_triangle_contacts(v,f,max_witnesses=15)
    record=dict(vertices=len(v),faces=len(f),indexed_open_or_nonmanifold_edges=int(np.count_nonzero(counts!=2)),
                components=len(mesh.split(only_watertight=False)),
                is_watertight=bool(mesh.is_watertight),
                winding_consistent=bool(mesh.is_winding_consistent),
                is_volume=bool(mesh.is_volume),
                positive_volume=float(mesh.volume),
                nonincident_contact_preflight=contact,
                saved_obj_sha256=sha(path))
    okay=(record['indexed_open_or_nonmanifold_edges']==0 and record['is_volume'] and
          record['positive_volume']>0 and record['components']==1 and
          contact['exhaustive'] and not contact['witnesses'])
    record['float_independent_preflight_pass']=bool(okay)
    if strict and not okay:raise ValueError('CHERCHI_NATIVE_OUTPUT_FAILED_INDEPENDENT_FLOAT_GATE')
    return mesh,record


def moments_crosscheck(mesh):
    v=np.asarray(mesh.vertices,dtype=np.float64)
    a,b,c=v[mesh.faces].transpose((1,0,2))
    w=np.einsum('ij,ij->i',a,np.cross(b,c))/6.
    m=float(w.sum()); l=(w[:,None]*(a+b+c)/4).sum(axis=0)
    s=a+b+c
    Q=np.empty((3,3))
    for i in range(3):
        for j in range(3):
            Q[i,j]=(w*(s[:,i]*s[:,j]+a[:,i]*a[:,j]+b[:,i]*b[:,j]+c[:,i]*c[:,j])/20).sum()
    gm=float(mesh.volume);cg=np.asarray(mesh.center_mass)
    ic=np.asarray(mesh.moment_inertia)
    i0=ic+gm*(np.dot(cg,cg)*np.eye(3)-np.outer(cg,cg))
    Q2=np.trace(i0)/2*np.eye(3)-i0
    err=max(abs(m-gm),float(np.max(np.abs(l-gm*cg))),float(np.max(np.abs(Q-Q2))))
    if m<=0 or err>1e-8:raise ValueError('CHERCHI_NATIVE_TEN_MOMENT_CROSSCHECK_FAILED')
    return dict(order=['M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY'],
                unit_density_raw_ten=[m,*map(float,l),float(Q[0,0]),float(Q[1,1]),
                    float(Q[2,2]),float(Q[1,2]),float(Q[0,2]),float(Q[0,1])],
                max_abs_independent_tetra_vs_trimesh=err,
                frame='SOURCE_ORIGINAL_Y_UP_UNIT_UNSPECIFIED',
                physical_density_authorized=False)


def run_native(p0,p1,binary,source,out,*,timeout=180):
    p0,p1,binary,source,out=map(Path,(p0,p1,binary,source,out))
    if not 0<timeout<=600:raise ValueError('PER_CALL_TIMEOUT_OUT_OF_BOUNDS')
    components=validate_input(p0,p1)
    identity=native_identity(binary,source)
    out.mkdir(parents=True,exist_ok=True)
    entry=dict(schema=SCHEMA,status='NOT_COMPLETED',native=identity,
               P0_sha256=sha(p0),P1_sha256=sha(p1),
               operations=[],geometry_authoritative=False,
               cherchi_geometry_executed=False,original_paper_cad=False,
               F_D_partition_certified=False,W0_case_approved=False,
               W2_teacher_authenticated=False,mujoco_physics_executed=False,
               optimized=False,independent_exact_rational_boundary_proof=False)
    record=out/'p7-cherchi-native-receipt.json'
    def persist():record.write_text(json.dumps(entry,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    persist()
    paths=[]
    for i,m in enumerate(components):
        fn=out/f'input-component-{i}.obj'
        write_obj(fn,m)
        paths.append(fn)
    # Official upstream main.cpp takes an arbitrary number of inputs between
    # operation and output; this invokes ONE real Cherchi variadic union.
    current=out/'cherchi-variadic-union-p7.obj'
    argv=[str(binary.resolve()),'union',*[str(q.resolve()) for q in paths],str(current.resolve())]
    time0=time.perf_counter()
    record_op=dict(stage=1,input_meshes=len(paths),argv_operation='union',
                   input_sha256=[sha(q) for q in paths],timeout_s=timeout)
    entry['operations'].append(record_op);persist()
    try:
        result=subprocess.run(argv,capture_output=True,text=True,timeout=timeout,check=False,
                              env={**os.environ,'OMP_NUM_THREADS':'1'})
        record_op.update(exit_code=result.returncode,wall_seconds=time.perf_counter()-time0,
                         stdout_tail=result.stdout[-10000:],stderr_tail=result.stderr[-10000:])
        if result.returncode!=0 or not current.is_file():
            raise RuntimeError('CHERCHI_REFERENCE_NATIVE_VARIADIC_UNION_FAILED')
        mesh,audit=check_native_output(current,strict=False)
        record_op['geometry_audit']=audit
        if not audit['float_independent_preflight_pass']:
            raise RuntimeError('CHERCHI_REFERENCE_NATIVE_UNION_GEOMETRY_GATE_FAILED')
        persist()
    except Exception as exc:
        entry['status']='FAILED_NATIVE_OR_GEOMETRY_GATE'
        entry['failed_stage']=1
        entry['failure']=f'{type(exc).__name__}: {exc}'
        persist()
        raise
    final,geometry=check_native_output(current,strict=True)
    moments=moments_crosscheck(final)
    entry.update(status='CHERCHI_REFERENCE_UNION_NUMERIC_GEOMETRY_PASS',
                 geometry_authoritative=True,cherchi_geometry_executed=True,
                 output_final_obj=current.name,
                 output_final_sha256=sha(current),final_geometry=geometry,moments=moments)
    persist()
    return entry


def main():
    root=Path(__file__).resolve().parent
    ap=argparse.ArgumentParser()
    ap.add_argument('--p0',type=Path,default=root.parent/'input'/'teapot-public-original.obj')
    ap.add_argument('--p1',type=Path,default=root/'teapot-topology-candidate-p1.obj')
    ap.add_argument('--native-bin',required=True,type=Path)
    ap.add_argument('--upstream-checkout',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--timeout',type=int,default=180)
    args=ap.parse_args()
    print(json.dumps(run_native(args.p0,args.p1,args.native_bin,args.upstream_checkout,args.out,
         timeout=args.timeout),indent=2,allow_nan=False))

if __name__=='__main__':main()

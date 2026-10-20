#!/usr/bin/env python3
"""W4 P8: forensic Cherchi-native union permutations; never use CGAL as solver.

All candidates come exclusively from the fixed Cherchi 7bd6c269 CLI. A zero
native exit status is not a solid certificate. Every candidate receives
independent topology, closedness, self-contact and volume-union bounds checks.
No state is promoted to an optimized Teapot or an author-original CAD.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import numpy as np
import trimesh
from p7_cherchi_native_union import (validate_input, native_identity, write_obj,
                                     sha, moments_crosscheck, P0_SHA, P1_SHA)
from p2_self_intersection import check_nonincident_triangle_contacts
from p1_geometry import vertex_fans

SCHEMA = "W4P8CherchiOnlyUnionForensicsV1"
WHOLE_TEAPOT_CASES = frozenset({
    'all-three','all-reversed',
    'body-handle-then-spout','body-spout-then-handle'
})


def indexed_components(vertices_count, faces):
    """Independent union-find: no networkx and no mesh repair are allowed."""
    parent = np.arange(vertices_count, dtype=np.int64)
    def root(i):
        i = int(i)
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = int(parent[i])
        return i
    for a,b,c in faces:
        ra=root(a)
        for d in (b,c):
            rd=root(d)
            if ra!=rd: parent[rd]=ra;ra=root(ra)
    sizes={}
    for face in faces:
        key=root(face[0]);sizes[key]=sizes.get(key,0)+1
    return sorted(sizes.values(),reverse=True)


def inspect_obj(path, full_contact_scan=True):
    mesh=trimesh.load_mesh(path,process=False)
    vertices=np.asarray(mesh.vertices,dtype=np.float64)
    faces=np.asarray(mesh.faces,dtype=np.int64)
    if len(faces)==0 or not np.isfinite(vertices).all():
        raise ValueError("NATIVE_MESH_EMPTY_OR_NONFINITE")
    edges,incidence=np.unique(np.sort(mesh.edges,axis=1),axis=0,return_counts=True)
    abnormal=edges[incidence!=2]
    facesizes=indexed_components(len(vertices),faces)
    area=np.linalg.norm(np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],
                                 vertices[faces[:,2]]-vertices[faces[:,0]]),axis=1)/2.
    edge_witness=[dict(a=vertices[a].tolist(),b=vertices[b].tolist(),
                      multiplicity=int(incidence[k]))
                  for k,(a,b) in enumerate(edges) if incidence[k]!=2][:12]
    bowties=vertex_fans(faces,len(vertices)) if len(abnormal)==0 else {}
    topo=(len(abnormal)==0 and len(bowties)==0 and
          bool(mesh.is_watertight) and bool(mesh.is_winding_consistent) and
          len(facesizes)==1 and bool(mesh.is_volume) and
          bool(np.all(area>1e-14)))
    contacts=({'status':'NOT_RUN_TOPOLOGY_FIRST','witnesses':[],
               'exhaustive':False}
              if not topo or not full_contact_scan else
              check_nonincident_triangle_contacts(vertices,faces,max_witnesses=16))
    result=dict(vertices=len(vertices),faces=len(faces),
        incidence_histogram={str(int(k)):int(v) for k,v in
                             zip(*np.unique(incidence,return_counts=True))},
        non_two_incidence_edges=int(len(abnormal)),bad_edge_witnesses=edge_witness,
        index_components=len(facesizes),component_face_counts=facesizes,
        winding_consistent=bool(mesh.is_winding_consistent),
        watertight=bool(mesh.is_watertight),signed_volume=float(mesh.volume),
        is_volume=bool(mesh.is_volume),pinched_vertex_count=len(bowties),
        small_triangle_count=int(np.sum(area<=1e-14)),
        conservative_float_contacts=contacts,
        independent_numeric_geometry_pass=bool(topo and contacts['exhaustive'] and
                                                not contacts['witnesses']),
        source_obj_sha256=sha(path))
    return mesh,result


def run_case(name, operands, executable, out, timeout):
    path=out/(name+'.obj')
    args=[str(executable.resolve()),'union']+[str(x.resolve()) for x in operands]+[str(path.resolve())]
    elapsed=time.monotonic()
    result=dict(name=name,operation="CHERCHI_NATIVE_UNION_NO_ALTERNATE",
        input_sha256=[sha(x) for x in operands],native_exit_code=None,
        output_obj=path.name,geometry_status='UNKNOWN',wall_seconds=None)
    try:
        proc=subprocess.run(args,capture_output=True,text=True,check=False,
                            timeout=timeout,env={**os.environ,'OMP_NUM_THREADS':'1'})
        result.update(native_exit_code=proc.returncode,wall_seconds=time.monotonic()-elapsed,
                      native_stdout=proc.stdout[-4000:],native_stderr=proc.stderr[-4000:])
        if proc.returncode!=0 or not path.is_file():
            result.update(geometry_status='NATIVE_FAILED',reason='CLI_NO_VALID_OUTPUT')
            return result,path
        mesh,geom=inspect_obj(path)
        result['geometry']=geom
        result['geometry_status']=('NUMERIC_SURFACE_PASS' if
                  geom['independent_numeric_geometry_pass'] else
                  'REJECTED_INVALID_TOPOLOGY_OR_CONTACT')
    except Exception as exc:
        result.update(geometry_status='EXCEPTION_FAIL_CLOSED',
                      reason=f'{type(exc).__name__}: {exc}',
                      wall_seconds=time.monotonic()-elapsed)
    return result,path


def run(p0,p1,source,binary,output,*,timeout=120):
    p0,p1,source,binary,output=map(Path,(p0,p1,source,binary,output))
    if not 0<timeout<=240:raise ValueError('INVALID_PER_CALL_LIMIT')
    parts=validate_input(p0,p1)
    identity=native_identity(binary,source)
    input_volumes=[float(x.volume) for x in parts]
    output.mkdir(parents=True,exist_ok=True)
    operands=[]
    for i,mesh in enumerate(parts):
        filename=output/f'source-part-{i}.obj'
        write_obj(filename,mesh)
        operands.append(filename)
    report=dict(schema=SCHEMA,status='RUNNING_NOT_ACCEPTED',
        native=identity,P0_sha256=sha(p0),P1_sha256=sha(p1),
        input_face_counts=[len(x.faces) for x in parts],
        input_volumes=input_volumes,
        accepted=False,optimized=False,original_paper_CAD=False,
        source_does_not_contain_F_D=True,
        W0_physical_case_authorized=False,W2_teacher_admitted=False,
        strict_exact_boolean_proof=False,runs=[],best_valid_obj=None)
    receipt=output/'p8-cherchi-permutations.json'
    def save():receipt.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    save()
    experiments=[
        ('all-three', [0,1,2]),
        ('body-plus-handle', [0,2]),
        ('body-plus-spout', [0,1]),
        ('spout-plus-handle', [1,2]),
        ('all-reversed', [2,1,0]),
    ]
    existing={}
    for name,inds in experiments:
        rec,out=run_case(name,[operands[i] for i in inds],binary,output,timeout)
        report['runs'].append(rec);existing[name]=(rec,out);save()
    for name,first,other in (
            ('body-handle-then-spout','body-plus-handle',1),
            ('body-spout-then-handle','body-plus-spout',2)):
        old,oldpath=existing[first]
        if old.get('geometry_status')!='NUMERIC_SURFACE_PASS':
            rec=dict(name=name,geometry_status='SKIPPED_FIRST_PAIR_INVALID',
                     prerequisite=first)
        else:
            rec,_=run_case(name,[oldpath,operands[other]],binary,output,timeout)
        report['runs'].append(rec);save()
    minimum=max(input_volumes)-1e-6
    maximum=sum(input_volumes)+1e-6
    # Pairwise UNIONs are diagnostic operands, NOT completed Teapot solids:
    # never accept body+handle or body+spout while the third piece is absent.
    for rec in report['runs']:
        if rec.get('geometry_status')!='NUMERIC_SURFACE_PASS' or rec['name'] not in WHOLE_TEAPOT_CASES:
            continue
        candidate=output/rec['output_obj']
        mesh,geom=inspect_obj(candidate)
        vol=float(mesh.volume)
        if not minimum<=vol<=maximum:
            rec['geometry_status']='REJECTED_UNION_VOLUME_BOUNDS'
            rec['union_volume_expected_range']=[minimum,maximum]
            save()
            continue
        try:
            oracle=moments_crosscheck(mesh)
        except Exception as exc:
            rec['geometry_status']='REJECTED_TEN_MOMENT_ORACLE'
            rec['reason']=f'{type(exc).__name__}: {exc}'
            save()
            continue
        rec['moments']=oracle
        rec['union_volume_expected_range']=[minimum,maximum]
        rec['geometry_status']='INDEPENDENT_FLOAT_GEOMETRY_PASS'
        report['status']='CHERCHI_NATIVE_FLOAT_GEOMETRY_PASS_EXACT_NOT_CERTIFIED'
        report['best_valid_obj']=candidate.name
        report['best_valid_sha256']=sha(candidate)
        report['accepted']=True
        report['strict_exact_boolean_proof']=False
        report['optimized']=False
        save()
        return report
    report['status']='CHERCHI_REAL_NATIVE_EXECUTED_BUT_NO_VALID_SOLID'
    report['accepted']=False
    save()
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--p0',type=Path,required=True)
    p.add_argument('--p1',type=Path,required=True)
    p.add_argument('--native-bin',type=Path,required=True)
    p.add_argument('--upstream-checkout',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=120)
    a=p.parse_args()
    report=run(a.p0,a.p1,a.upstream_checkout,a.native_bin,a.out,timeout=a.timeout)
    print(json.dumps(dict(status=report['status'],native_calls=len([r for r in report['runs']
            if r.get('native_exit_code') is not None]),
            accepted=report['accepted'],candidate=report['best_valid_obj'],
            runs=[dict(name=r['name'],status=r['geometry_status'],
                       edges=r.get('geometry',{}).get('non_two_incidence_edges'),
                       components=r.get('geometry',{}).get('index_components'))
                  for r in report['runs']]),indent=2))
    if not report['accepted']:
        raise SystemExit(2)


if __name__=='__main__':main()

#!/usr/bin/env python3
"""P10 pinned Cherchi P9 numeric boundary and exact-decimal-OBJ ten-moment seal.

Exact Fractions describe SERIALIZED OBJ decimal coordinates only, not the
underlying native Cherchi implicit exact rational arrangement. No physical
units, source-CAD identity, W0 F/D authority or optimization are certified.
"""
from __future__ import annotations
import argparse,hashlib,json
from fractions import Fraction as F
from pathlib import Path
from collections import defaultdict
import numpy as np
import trimesh
from p2_self_intersection import check_nonincident_triangle_contacts

P0_SHA='1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4'
P1_SHA='3b13a006976093f86b733cd1a00c57d70a66e2fc8dca1c4a157bb18f93a7db47'
P9_SHA='154cdfc9ec94b6885a95e596c36ac1382dd2d36ed99e19d0b36c2b9de80b6df4'
SOURCE_CHERCHI_REV='7bd6c2697695f555f9a15d7e154e084d841316f0'
R=np.array([[1,0,0],[0,0,-1],[0,1,0]],dtype=float)
MOMENTS=('M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY')
SCHEMA='W4P10PinnedCherchiNumericalMaterialSealV1'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def read_decimal_obj(path):
    vertices=[];faces=[]
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        t=line.split()
        if not t:continue
        if t[0]=='v':
            if len(t)<4:raise ValueError('BAD_OBJ_VERTEX')
            vertices.append(tuple(F(x) for x in t[1:4]))
        if t[0]=='f':
            indices=[int(x.split('/')[0])-1 for x in t[1:]]
            if len(indices)!=3:raise ValueError('NOT_TRIANGULAR_OBJ')
            faces.append(tuple(indices))
    if not vertices or not faces or min(map(min,faces))<0 or max(map(max,faces))>=len(vertices):
        raise ValueError('INVALID_DECIMAL_OBJ')
    return vertices,faces

def exact_decimal_ten(vertices,faces):
    z=F(0);m=z;first=[z,z,z];q=[[z,z,z],[z,z,z],[z,z,z]]
    for i,j,k in faces:
        a,b,c=vertices[i],vertices[j],vertices[k]
        det=(a[0]*(b[1]*c[2]-b[2]*c[1])+
             a[1]*(b[2]*c[0]-b[0]*c[2])+
             a[2]*(b[0]*c[1]-b[1]*c[0]))
        w=det/6;m+=w
        s=tuple(a[t]+b[t]+c[t] for t in range(3))
        for axis in range(3):first[axis]+=w*s[axis]/4
        for x in range(3):
            for y in range(x,3):
                dq=w*(s[x]*s[y]+a[x]*a[y]+b[x]*b[y]+c[x]*c[y])/20
                q[x][y]+=dq
                if x!=y:q[y][x]+=dq
    return [m,*first,q[0][0],q[1][1],q[2][2],q[1][2],q[0][2],q[0][1]]

def independently_check_topology(mesh):
    v=np.asarray(mesh.vertices);f=np.asarray(mesh.faces,dtype=np.int64)
    if v.ndim!=2 or v.shape[1:]!=(3,) or f.ndim!=2 or f.shape[1:]!=(3,) or not np.isfinite(v).all():
        raise ValueError('INVALID_MESH_INPUT')
    if np.any(f[:,0]==f[:,1]) or np.any(f[:,1]==f[:,2]) or np.any(f[:,0]==f[:,2]):
        raise ValueError('INDEX_DEGENERATE_TRIANGLE')
    tri=v[f]
    area=.5*np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)
    key=np.sort(np.stack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]],axis=1).reshape(-1,2),axis=1)
    _,cnt=np.unique(key,axis=0,return_counts=True)
    e2=np.all(cnt==2)
    directed=np.stack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]],axis=1).reshape(-1,2)
    oriented=defaultdict(int)
    for a,b in directed:
        oriented[(min(int(a),int(b)),max(int(a),int(b)))]+=1 if a<b else -1
    zero_winding=all(k==0 for k in oriented.values())
    incident=[[] for _ in range(len(v))]
    adj={i:set() for i in range(len(f))}
    edgemap=defaultdict(list)
    for fi,abc in enumerate(f):
        for node in abc:incident[int(node)].append(fi)
        for a,b in ((abc[0],abc[1]),(abc[1],abc[2]),(abc[2],abc[0])):
            edgemap[(min(int(a),int(b)),max(int(a),int(b)))].append(fi)
    for matches in edgemap.values():
        if len(matches)==2:
            i,j=matches;adj[i].add(j);adj[j].add(i)
    remain=set(range(len(f)));components=[]
    while remain:
        i=remain.pop();stack=[i];n=1
        while stack:
            k=stack.pop()
            for j in adj[k]:
                if j in remain:remain.remove(j);stack.append(j);n+=1
        components.append(n)
    pinched=[]
    for vi,face_indices in enumerate(incident):
        if not face_indices:continue
        sub=set(face_indices);first=next(iter(sub));todo=[first];visited={first}
        while todo:
            face=todo.pop()
            for j in adj[face]:
                if j in sub and j not in visited:visited.add(j);todo.append(j)
        if len(visited)!=len(sub):pinched.append(vi)
    if e2 and zero_winding and not pinched:
        contact=check_nonincident_triangle_contacts(v,f,max_witnesses=12)
    else:
        contact={'witnesses':[],'exhaustive':False,'status':'NOT_EXECUTED_TOPOLOGY_BLOCKED'}
    status=(e2 and zero_winding and not pinched and len(components)==1 and
            np.min(area)>1e-14 and mesh.is_volume and contact['exhaustive'] and
            not contact['witnesses'])
    return dict(connected_components=len(components),
                component_face_counts=sorted(components,reverse=True),
                non_two_edges=int((cnt!=2).sum()),
                winding_edge_disagreements=int(sum(x!=0 for x in oriented.values())),
                pinch_vertices=len(pinched),min_area=float(np.min(area)),
                is_watertight=bool(mesh.is_watertight),is_volume=bool(mesh.is_volume),
                winding_consistent=bool(mesh.is_winding_consistent),
                conservative_float_contacts=contact,one_component_closed_preflight=bool(status))

def certify(source,p0,p1,journal,output):
    source,p0,p1,journal,output=map(Path,(source,p0,p1,journal,output))
    if (sha(source),sha(p0),sha(p1))!=(P9_SHA,P0_SHA,P1_SHA):
        raise ValueError('PINNED_REAL_CHERCHI_P9_OR_P0_P1_SHA_MISMATCH')
    j=json.loads(journal.read_text())
    if j.get('status')!='SOURCE_DEVIATING_CHERCHI_NUMERIC_CANDIDATE_AVAILABLE':
        raise ValueError('P9_VALID_CANDIDATE_NOT_PRESENT')
    p9=j.get('recommended_candidate') or {}
    if p9.get('obj_sha256')!=P9_SHA or p9.get('shift')!=.005:
        raise ValueError('P9_HANDLE_VARIANT_IDENTITY_MISMATCH')
    if j.get('native',{}).get('upstream_commit')!=SOURCE_CHERCHI_REV:
        raise ValueError('NATIVE_CHERCHI_SOURCE_REVISION_MISMATCH')
    decimals,indices=read_decimal_obj(source)
    mesh=trimesh.load_mesh(source,process=False)
    if len(decimals)!=len(mesh.vertices) or len(indices)!=len(mesh.faces):
        raise ValueError('OBJ_REPRESENTATION_NOT_CONSISTENT')
    geom=independently_check_topology(mesh)
    if not geom['one_component_closed_preflight']:
        raise ValueError('P10_INVALID_NUMERICAL_SURFACE')
    exact=exact_decimal_ten(decimals,indices)
    if exact[0]<=0:raise ValueError('P10_NONPOSITIVE_EXACT_DECIMAL_VOLUME')
    values=[float(v) for v in exact]
    expected=np.asarray(p9['independent_ten_moments'],dtype=float)
    errors=np.abs(np.array(values)-expected)
    if errors.max()>1e-9:raise ValueError('DECIMAL_EXACT_TEN_MOMENT_MISMATCH')
    m=float(mesh.volume);com=np.asarray(mesh.center_mass)
    if abs(m-values[0])>1e-10 or np.max(np.abs(m*com-np.array(values[1:4])))>1e-10:
        raise ValueError('INDEPENDENT_MESH_MASS_OR_FIRST_MOMENT_MISMATCH')
    vertices=np.asarray(mesh.vertices);faces=np.asarray(mesh.faces)
    zup=vertices@R.T
    transformed=trimesh.Trimesh(vertices=zup,faces=faces,process=False)
    if not np.isclose(transformed.volume,m,atol=1e-10):
        raise ValueError('FRAME_ROTATION_VOLUME_CHANGED')
    if not np.allclose(transformed.center_mass,R@com,atol=1e-10):
        raise ValueError('FRAME_ROTATION_CENTER_CHANGED')
    I=np.asarray(mesh.moment_inertia)
    if not np.allclose(transformed.moment_inertia,R@I@R.T,atol=1e-10):
        raise ValueError('FRAME_ROTATION_INERTIA_CHANGED')
    output.mkdir(parents=True,exist_ok=True)
    stable=output/'cherchi-p9-numeric-original-yup.obj'
    stable.write_bytes(source.read_bytes())
    zfile=output/'cherchi-p10-proposed-zup.obj'
    with zfile.open('w') as fp:
        fp.write('# PROPOSED Z_UP; no W0 physical scale; Cherchi source-deviated\n')
        for xyz in zup:fp.write('v '+' '.join(format(float(x),'.17g') for x in xyz)+'\n')
        for a,b,c in faces:fp.write(f'f {a+1} {b+1} {c+1}\n')
    imported=trimesh.load_mesh(zfile,process=False)
    if not imported.is_volume or len(imported.faces)!=len(faces):
        raise ValueError('ZUP_SAVED_RELOAD_FAILED')
    report=dict(schema=SCHEMA,status='NUMERIC_CLOSED_DECIMAL_EXACT_MOMENTS_ONLY',
        geometry_source='CHERCHI_REFERENCE_NATIVE_REAL_RUN_39362437035',
        authoritative_original_CAD=False,source_deviation_handle_x_original_units=.005,
        source_deviation_relative_diagonal=p9['relative_deviation'],
        original_P0_sha256=sha(p0),P1_topology_sha256=sha(p1),
        native_revision=SOURCE_CHERCHI_REV,native_binary_sha256=j['native']['binary_sha256'],
        source_obj_sha256=sha(stable),proposed_zup_sha256=sha(zfile),
        topology=geom,volume_in_original_units=m,source_center_of_mass=com.tolist(),
        source_inertia_com=I.tolist(),
        exact_saved_OBJ_decimal_raw_ten={k:str(v) for k,v in zip(MOMENTS,exact)},
        exact_saved_OBJ_decimal_projected_ten=dict(zip(MOMENTS,values)),
        max_abs_error_vs_P9_production_ten=float(np.max(errors)),
        frame=dict(input='Y_UP',proposed='Z_UP',rotation=R.tolist(),det=float(np.linalg.det(R))),
        native_implicit_exact_rational_vertices_available=False,
        native_exact_set_identity_certified=False,
        W0_tip_axis_scale_density_F_D_approved=False,W2_teacher_derivatives_admitted=False,
        physical_printability_validated=False,SpinIt_optimization_performed=False,
        formally_certified_source_compatible=False)
    (output/'p10-numeric-source-seal.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

def main():
    p=argparse.ArgumentParser()
    for n in ('source','p0','p1','journal','output'):p.add_argument('--'+n,required=True,type=Path)
    a=p.parse_args()
    r=certify(a.source,a.p0,a.p1,a.journal,a.output)
    print(json.dumps({'status':r['status'],'components':r['topology']['connected_components'],
                      'raw_volume':r['volume_in_original_units'],
                      'max_ten_moment_error':r['max_abs_error_vs_P9_production_ten'],
                      'source_sha256':r['source_obj_sha256']},indent=2))
if __name__=='__main__':main()

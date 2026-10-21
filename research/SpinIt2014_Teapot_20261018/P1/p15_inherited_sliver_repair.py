#!/usr/bin/env python3
"""W4 P15: strictly bounded micro-weld of inherited native Cherchi face slivers.

Only post-processes explicitly sourced, saved native P14 OBJ; it does NOT
change Cherchi's implicit exact arrangement, original M/F/D, or W0 approval.
Never silently replace Cherchi Boolean with another backend.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
import trimesh

SCHEMA='W4P15InheritedNativeSliverRepairV1'
BOUND=1e-15
AREA=1e-14
TEN_TOL=1e-10
MESH_COUNT=28
CASES=('rotate_1p5','translate_y_008','translate_xy_012_m008')
UPSTREAM='7bd6c2697695f555f9a15d7e154e084d841316f0'
MOMENT_ORDER=['M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY']

def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load(path):
    mesh=trimesh.load_mesh(path,process=False)
    if not isinstance(mesh,trimesh.Trimesh) or not len(mesh.faces):raise ValueError('MESH_EMPTY')
    if not np.isfinite(mesh.vertices).all():raise ValueError('MESH_NONFINITE')
    return mesh

def oriented_triangle(mesh,tri):
    points=[tuple(float(0 if x==0 else x).hex() for x in mesh.vertices[int(i)]) for i in tri]
    return min((tuple(points),tuple(points[1:]+points[:1]),tuple(points[2:]+points[:2])))

def sliver_signatures(mesh):
    indices=np.flatnonzero(mesh.area_faces<=AREA)
    sig=[oriented_triangle(mesh,mesh.faces[i]) for i in indices]
    return indices,set(sig)

def raw_ten(mesh):
    t=np.asarray(mesh.vertices)[np.asarray(mesh.faces)]
    a,b,c=t.transpose(1,0,2)
    w=np.einsum('ij,ij->i',a,np.cross(b,c))/6.
    s=a+b+c;first=(w[:,None]*s/4.).sum(axis=0)
    Q=np.empty((3,3))
    for i in range(3):
        for j in range(3):
            Q[i,j]=np.sum(w*(s[:,i]*s[:,j]+a[:,i]*a[:,j]+b[:,i]*b[:,j]+c[:,i]*c[:,j])/20.)
    return np.array([w.sum(),*first,Q[0,0],Q[1,1],Q[2,2],Q[1,2],Q[0,2],Q[0,1]])

def edge_incidence(mesh):
    edges=np.sort(np.asarray(mesh.edges),axis=1)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    return int(np.count_nonzero(counts!=2))

def triangle_contacts(a,bs,tol=1e-11):
    ea=np.roll(a,-1,axis=0)-a
    eb=np.roll(bs,-1,axis=1)-bs
    na=np.cross(ea[0],ea[1]);nb=np.cross(eb[:,0],eb[:,1])
    axes=np.concatenate((
        np.broadcast_to(na,(len(bs),1,3)),nb[:,None,:],
        np.cross(ea[None,:,None,:],eb[:,None,:,:]).reshape(-1,9,3),
        np.cross(np.broadcast_to(na,(len(bs),1,3)),eb),
        np.cross(nb[:,None,:],np.broadcast_to(ea,(len(bs),3,3))),
    ),axis=1)
    norms=np.linalg.norm(axes,axis=2)
    pa=np.einsum('bjd,id->bji',axes,a)
    pb=np.einsum('bjd,bid->bji',axes,bs)
    separated=((pa.max(axis=2)<pb.min(axis=2)-tol*norms)|
               (pb.max(axis=2)<pa.min(axis=2)-tol*norms))&(norms>1e-17)
    return ~separated.any(axis=1)

def independent_contact_scan(mesh,max_witness=12):
    v=np.asarray(mesh.vertices);f=np.asarray(mesh.faces)
    triangles=v[f]
    lower=triangles.min(axis=1);upper=triangles.max(axis=1)
    order=np.argsort(lower[:,0],kind='stable');lo=lower[order,0]
    pairs=0;seen=[]
    for ix,face in enumerate(order):
        i=int(face)
        end=int(np.searchsorted(lo,upper[i,0]+1e-11,side='right'))
        js=order[ix+1:end]
        if not len(js):continue
        ok=(lower[js,1]<=upper[i,1]+1e-11)&(upper[js,1]>=lower[i,1]-1e-11)&(lower[js,2]<=upper[i,2]+1e-11)&(upper[js,2]>=lower[i,2]-1e-11)
        js=js[ok]
        if not len(js):continue
        adjacent=np.any(np.any(f[js,:,None]==f[i,None,:],axis=2),axis=1)
        js=js[~adjacent]
        pairs+=len(js)
        if not len(js):continue
        for j in js[triangle_contacts(triangles[i],triangles[js])]:
            seen.append([i,int(j)])
            if len(seen)>=max_witness:
                return dict(exhaustive=False,pairs_tested=int(pairs),witnesses=seen)
    return dict(exhaustive=True,pairs_tested=int(pairs),witnesses=seen)

def weld_inherited(mesh,tol=BOUND):
    if not (0<tol<=BOUND):raise ValueError('UNAUTHORIZED_VERTEX_MOVEMENT_LIMIT')
    original_v=np.asarray(mesh.vertices,dtype=np.float64)
    original_f=np.asarray(mesh.faces,dtype=np.int64)
    bad_ids,_=sliver_signatures(mesh)
    if len(bad_ids)!=MESH_COUNT:raise ValueError('UNEXPECTED_SOURCE_SLIVER_FACE_COUNT')
    pairs={tuple(map(int,sorted(p))) for p in cKDTree(original_v).query_pairs(tol)}
    if len(pairs)!=MESH_COUNT//2:raise ValueError('UNEXPECTED_NEAR_COINCIDENT_PAIR_COUNT')
    sliver_edges=set();per_pair={p:0 for p in pairs}
    for fi in bad_ids:
        a,b,c=map(int,original_f[fi])
        for x,y in ((a,b),(b,c),(c,a)):
            pair=tuple(sorted((x,y)))
            if pair in pairs:
                sliver_edges.add(pair)
                per_pair[pair]+=1
    if sliver_edges!=pairs or set(per_pair.values())!={2}:
        raise ValueError('WELD_PAIRS_NOT_EXCLUSIVELY_INHERITED_SLIVER_EDGES')
    endpoints=[i for pair in pairs for i in pair]
    if len(set(endpoints))!=2*len(pairs):raise ValueError('WELD_VERTEX_CHAINS_NOT_ALLOWED')
    index=np.arange(len(original_v))
    for a,b in sorted(pairs):index[b]=a
    changed=index[original_f]
    keep=(changed[:,0]!=changed[:,1])&(changed[:,1]!=changed[:,2])&(changed[:,2]!=changed[:,0])
    if not np.array_equal(np.flatnonzero(~keep),bad_ids):
        raise ValueError('WELD_REMOVED_NON_SLIVER_FACE')
    active,inv=np.unique(changed[keep],return_inverse=True)
    fixed=trimesh.Trimesh(vertices=original_v[active],faces=inv.reshape(-1,3),process=False)
    non2=edge_incidence(fixed)
    if non2 or not fixed.is_volume or not fixed.is_winding_consistent or np.any(fixed.area_faces<=AREA):
        raise ValueError('NUMERIC_MICRO_WELD_NOT_CLOSED_OR_DEGENERATE')
    moment_max=float(np.max(np.abs(raw_ten(fixed)-raw_ten(mesh))))
    if moment_max>TEN_TOL:raise ValueError('MICROWELD_CHANGED_RAW_TEN_MOMENTS')
    displacement=max(float(np.linalg.norm(original_v[b]-original_v[a])) for a,b in pairs)
    return fixed,dict(merged_near_vertex_pairs=len(pairs),removed_exact_sliver_faces=int((~keep).sum()),
        maximum_vertex_representative_displacement=displacement,max_allowed_displacement=BOUND,
        material_raw_ten_change_max_abs=moment_max,non_two_incidence_edges=non2,
        remaining_small_triangles=int(np.sum(fixed.area_faces<=AREA)),
        min_remaining_area=float(fixed.area_faces.min()),
        before_triangles=len(mesh.faces),after_triangles=len(fixed.faces),
        before_vertices=len(mesh.vertices),after_vertices=len(fixed.vertices))

def write_obj(path,mesh):
    with Path(path).open('w',encoding='ascii',newline='\n') as out:
        out.write('# P15 FLOAT64 MICROWELD OF NATIVE CHERCHI OUTPUT; NOT AN EXACT CHERCHI BOOLEAN CERTIFICATE\n')
        for p in np.asarray(mesh.vertices):out.write('v '+' '.join(f'{float(x):.17g}' for x in p)+'\n')
        for a,b,c in np.asarray(mesh.faces):out.write(f'f {a+1} {b+1} {c+1}\n')

def valid_native_case(case,root,source_outer):
    if case.get('status')!='REJECTED_F_NONMANIFOLD_OR_CONTACT' or case.get('D_geometry',{}).get('strict_numeric_preflight') is not True:
        raise ValueError('INELIGIBLE_NATIVE_P14_CASE')
    for op,fn in [('D_native','D_minus_shaft_cherchi.obj'),('F_native','F_retained_cherchi.obj')]:
        k=case[op];p=root/case['name']/fn
        if k.get('returncode')!=0 or k.get('output_sha256')!=digest(p):
            raise ValueError('NATIVE_BINARY_MATERIAL_PROVENANCE_MISMATCH')
        rfile=Path(str(p)+'.native.json')
        r=json.loads(rfile.read_text())
        if r.get('output_sha256')!=digest(p) or r.get('returncode')!=0:
            raise ValueError('NATIVE_SAME_CALL_RECEIPT_MISMATCH')
    if case['F_native']['source_sha256'][0]!=digest(source_outer):
        raise ValueError('WRONG_F_OUTER_SOURCE')
    if case['F_native']['source_sha256'][1]!=case['D_native']['output_sha256']:
        raise ValueError('F_NOT_SUBTRACTING_SAME_CALL_D')
    if case.get('rod_core_D_winding',99)!=0 and abs(case['rod_core_D_winding'])>1e-7:
        raise ValueError('D_HAS_NONZERO_SHAFT_CORE_WINDING')
    if abs(case.get('off_axis_D_winding',0)-1)>1e-7:
        raise ValueError('D_HAS_NO_OFF_AXIS_REMOVABLE_MATERIAL')
    if case.get('numerical_outer_surface_clearance_lower_bound',0)<=0:
        raise ValueError('NO_OUTER_CLEARANCE')

def study(root,out,cases=CASES):
    root=Path(root);out=Path(out)
    audit=json.loads((root/'p14-junction-native-study.json').read_text())
    if audit.get('schema')!='W4P14CherchiShaftCavityJunctionStudyV1' or audit.get('real_D_native_trials')!=11:
        raise ValueError('REAL_P14_NATIVE_STUDY_NOT_COMPLETE')
    if audit.get('current_native',{}).get('upstream_commit')!=UPSTREAM or audit.get('W0_approved') is not False:
        raise ValueError('WRONG_CHERCHI_PROVENANCE_OR_FALSE_APPROVAL')
    if audit['admissible_candidate'] is not None or audit['status']!='COMPLETED_NEGATIVE_NATIVE_JUNCTION_STUDY':
        raise ValueError('DO_NOT_OVERWRITE_P14_ADMISSION')
    outer=root.parent/'p13-native-Cherchi-domain'/'p13-outer-cherchi-union.obj'
    if digest(outer)!=audit['source_sha256']['outer']:
        raise ValueError('INPUT_OUTER_HASH_MISMATCH')
    original=load(outer)
    ids,original_sigs=sliver_signatures(original)
    if len(ids)!=MESH_COUNT or len(original_sigs)!=MESH_COUNT or edge_incidence(original)!=0 or not original.is_volume:
        raise ValueError('ORIGINAL_OUTER_INVALID_OR_UNEXPECTED_SLIVERS')
    clean_outer,metadata_outer=weld_inherited(original)
    scan_o=independent_contact_scan(clean_outer)
    if not scan_o['exhaustive'] or scan_o['witnesses']:
        raise ValueError('CLEAN_OUTER_HAS_INDEPENDENT_CONTACTS')
    out.mkdir(parents=True,exist_ok=True)
    outer_name=out/'outer_numeric_microweld.obj'
    write_obj(outer_name,clean_outer)
    receipt=dict(schema=SCHEMA,status='EVALUATING_FLOAT_POSTPROCESS_NOT_NATIVE_EXACT_CERT',
        source_P14_report_sha256=digest(root/'p14-junction-native-study.json'),
        original_Cherchi_outer_sha256=digest(outer),native_source_commit=UPSTREAM,
        inherited_sliver_count=MESH_COUNT,source_faces_changed_without_explicit_justification=False,
        upstream_P14_strict_native_result_was_negative=True,
        outer_cleaned_sha256=digest(outer_name),outer_micro_weld=metadata_outer,
        outer_independent_contact_scan=scan_o,cases=[],selected=None,
        original_CAD_shape_certified=False,exact_Cherchi_implicit_geometry_certified=False,
        W0_physical_tip_or_FD_approved=False,printable_wall_thickness_certified=False,
        SpinIt_Faster_optimization_executed=False,MuJoCo_before_after_optimization_run=False)
    logfile=out/'p15-inherited-sliver-study.json'
    def save():logfile.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    save()
    for name in cases:
        item=next((c for c in audit['cases'] if c['name']==name),None)
        entry=dict(name=name,status='NOT_VALIDATED')
        try:
            if item is None:raise ValueError('CASE_NOT_IN_P14_STUDY')
            valid_native_case(item,root,outer)
            p=root/name
            original_F=load(p/'F_retained_cherchi.obj')
            D=load(p/'D_minus_shaft_cherchi.obj')
            dids,dsigs=sliver_signatures(D)
            fids,fsigs=sliver_signatures(original_F)
            if len(dids) or not D.is_volume or edge_incidence(D)!=0:
                raise ValueError('SAVED_NATIVE_D_INVALID')
            if len(fids)!=MESH_COUNT or fsigs!=original_sigs or not original_F.is_volume or edge_incidence(original_F)!=0:
                raise ValueError('F_SLIVERS_NOT_EXACTLY_INHERITED_FROM_OUTER')
            fixed,metadata_F=weld_inherited(original_F)
            scan_F=independent_contact_scan(fixed)
            scan_D=independent_contact_scan(D)
            if (not scan_F['exhaustive'] or scan_F['witnesses'] or
                    not scan_D['exhaustive'] or scan_D['witnesses']):
                raise ValueError('SAVED_NATIVE_MATERIAL_HAS_FLOAT_CONTACTS')
            raw_residual=raw_ten(clean_outer)-raw_ten(fixed)-raw_ten(D)
            maxerr=float(np.max(np.abs(raw_residual)))
            if maxerr>TEN_TOL:raise ValueError('AFTER_MICROWELD_FULL_MATERIAL_TEN_MOMENT_NONADDITIVE')
            target=out/name;target.mkdir(exist_ok=True)
            Ffile=target/'F_numeric_microweld.obj'
            write_obj(Ffile,fixed)
            rr=load(Ffile)
            if (not rr.is_volume or edge_incidence(rr)!=0 or
                    np.max(np.abs(raw_ten(rr)-raw_ten(fixed)))>TEN_TOL):
                raise ValueError('SAVED_POSTPROCESS_MATERIAL_REREAD_FAILED')
            entry.update(status='FLOAT_MESH_POSTPROCESS_CONDITIONAL_PASS_NOT_NATIVE_EXACT',
                F_original_native_sha256=digest(p/'F_retained_cherchi.obj'),
                D_original_native_sha256=digest(p/'D_minus_shaft_cherchi.obj'),
                F_postprocessed_sha256=digest(Ffile),native_input_D_displacement=item['max_vertex_displacement'],
                inherited_sliver_face_count=len(fsigs),all_slivers_from_outer=True,
                F_postprocess=metadata_F,F_independent_contact_scan=scan_F,
                D_independent_contact_scan=scan_D,
                max_abs_full_raw_ten_material_additivity_residual=maxerr,
                raw_ten_component_order=MOMENT_ORDER,
                outer_volume=float(clean_outer.volume),F_volume=float(fixed.volume),D_volume=float(D.volume),
                F_boundary_components=int(len(fixed.split(only_watertight=False))),
                no_W0_approval=True)
            if receipt['selected'] is None:
                receipt['selected']=name
        except Exception as e:
            entry.update(status='REJECTED_P15_INDEPENDENT_GATE',reason=f'{type(e).__name__}: {e}')
        receipt['cases'].append(entry);save()
    receipt['status']=('FLOAT64_MICROWELD_CANDIDATE_AVAILABLE_NOT_EXACT_CHERCHI' if receipt['selected'] else
                       'P15_ALL_CANDIDATES_REJECTED')
    save()
    return receipt

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--p14-root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    result=study(a.p14_root,a.out)
    print(json.dumps(dict(status=result['status'],selected=result['selected'],cases=[{k:v for k,v in c.items() if k in ('name','status','reason','max_abs_full_raw_ten_material_additivity_residual')} for c in result['cases']]),indent=2))
    if not result['selected']:raise SystemExit(2)

if __name__=='__main__':main()

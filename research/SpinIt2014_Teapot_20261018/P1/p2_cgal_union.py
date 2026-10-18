#!/usr/bin/env python3
"""W4: source-pinned solid union using OpenSCAD CGAL/Nef, with two independent gates.

Never mutate the P0 OBJ or P1 candidate. The delivered mesh is a numerical
STL/OBJ discretization of the CGAL result, not an exact author-original CAD.
Geometry clearance is distinct from W0 spin-axis, tip, F/D and W2 teacher.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import numpy as np
import trimesh

try:
    from .p2_self_intersection import check_nonincident_triangle_contacts
except ImportError:
    from p2_self_intersection import check_nonincident_triangle_contacts

P0_SHA256 = '1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4'
P1_SHA256 = '3b13a006976093f86b733cd1a00c57d70a66e2fc8dca1c4a157bb18f93a7db47'
ORIGINAL_BLOB = 'c839837bfc09f5d5bac4aa757fcbd9f16ddd7ec1'
Y_TO_Z = np.array([[1., 0., 0.], [0., 0., -1.], [0., 1., 0.]])
MOMENT_NAMES = ('M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY')


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_check(source, candidate):
    if sha256(source) != P0_SHA256:
        raise ValueError('P0_SOURCE_SHA256_MISMATCH')
    if sha256(candidate) != P1_SHA256:
        raise ValueError('P1_CANDIDATE_SHA256_MISMATCH')


def write_off(path, mesh):
    # OpenSCAD parses OFF binary64 decimal coordinates into its CGAL geometry.
    with Path(path).open('w', encoding='utf-8', newline='\n') as stream:
        stream.write(f'OFF\n{len(mesh.vertices)} {len(mesh.faces)} 0\n')
        for p in mesh.vertices:
            stream.write(' '.join(f'{x:.17g}' for x in p) + '\n')
        for tri in mesh.faces:
            stream.write('3 ' + ' '.join(str(int(i)) for i in tri) + '\n')


def write_obj(path, vertices, faces, header='W4 P2 CGAL union numerical OBJ'):
    with Path(path).open('w', encoding='utf-8', newline='\n') as out:
        out.write('# ' + header + '\n')
        for v in vertices:
            out.write('v ' + ' '.join(f'{x:.17g}' for x in v) + '\n')
        for face in faces:
            out.write('f ' + ' '.join(str(int(j)+1) for j in face) + '\n')


def canonical_mesh(mesh):
    unique, inverse = np.unique(np.asarray(mesh.vertices), axis=0, return_inverse=True)
    faces = inverse[np.asarray(mesh.faces, dtype=np.int64)]
    if len(set(map(tuple, faces))) != len(faces):
        raise ValueError('DUPLICATE_FACE')
    turns = np.argmin(faces, axis=1)
    faces = np.asarray([np.roll(row, -int(turn)) for row, turn in zip(faces, turns)], dtype=np.int64)
    sorter = np.lexsort((faces[:, 2], faces[:, 1], faces[:, 0]))
    return trimesh.Trimesh(vertices=unique, faces=faces[sorter], process=False)


def independent_tetra_moments(mesh):
    v = np.asarray(mesh.vertices, dtype=np.float64)
    f = np.asarray(mesh.faces, dtype=np.int64)
    tri = v[f]
    a,b,c = tri[:,0], tri[:,1], tri[:,2]
    signed = np.einsum('ij,ij->i', a, np.cross(b,c)) / 6.
    m = float(np.sum(signed))
    first = np.sum(signed[:, None] * (a+b+c) / 4., axis=0)
    s = a+b+c
    raw = np.empty((3,3))
    for i in range(3):
        for j in range(3):
            raw[i,j] = np.sum(signed * (s[:,i]*s[:,j] +
                                 a[:,i]*a[:,j] + b[:,i]*b[:,j] + c[:,i]*c[:,j]) / 20.)
    inertia0 = np.trace(raw) * np.eye(3) - raw
    return m,first,raw,inertia0


def trimesh_oracle(mesh):
    # Reconstruct raw Q from trimesh's independently implemented mass-property
    # COM tensor rather than using our tetrahedral raw-Q evaluator.
    m=float(mesh.volume)
    center=np.asarray(mesh.center_mass,dtype=np.float64)
    inertia_com=np.asarray(mesh.moment_inertia,dtype=np.float64)
    inertia_origin = inertia_com + m * (np.dot(center,center)*np.eye(3)-np.outer(center,center))
    q = np.trace(inertia_origin)*np.eye(3)/2. - inertia_origin
    return m,m*center,q,inertia_origin


def moments_list(m, first, second):
    return [float(m),*map(float,first),float(second[0,0]),float(second[1,1]),
            float(second[2,2]),float(second[1,2]),float(second[0,2]),float(second[0,1])]


def geometry_gate(mesh):
    edges=np.sort(np.asarray(mesh.edges,dtype=np.int64),axis=1)
    unique, counts=np.unique(edges,axis=0,return_counts=True)
    if len(mesh.faces)==0 or len(mesh.vertices)==0:
        raise ValueError('EMPTY_RESULT')
    faces=np.asarray(mesh.faces, dtype=int)
    if np.any(faces[:,0]==faces[:,1]) or np.any(faces[:,0]==faces[:,2]) or np.any(faces[:,1]==faces[:,2]):
        raise ValueError('COLLAPSED_FACES')
    area=np.asarray(mesh.area_faces)
    contact=check_nonincident_triangle_contacts(mesh.vertices,mesh.faces)
    pieces=mesh.split(only_watertight=False)
    report=dict(vertices=len(mesh.vertices),faces=len(mesh.faces),
        boundary_or_nonmanifold_edges=int(np.count_nonzero(counts!=2)),
        nonpositive_face_areas=int(np.count_nonzero(area<=1e-14)),
        consistent_winding=bool(mesh.is_winding_consistent),
        watertight=bool(mesh.is_watertight),
        positive_volume=bool(mesh.volume>0),
        trimesh_is_volume=bool(mesh.is_volume),
        components=len(pieces),euler_characteristic=int(mesh.euler_number),
        nonincident_triangle_contacts=contact)
    success=(report['boundary_or_nonmanifold_edges']==0 and
             report['nonpositive_face_areas']==0 and
             report['consistent_winding'] and report['watertight'] and
             report['positive_volume'] and report['trimesh_is_volume'] and
             report['components']==1 and
             contact['exhaustive'] and not contact['witnesses'])
    return report,success


def native_union(candidate, binary, timeout=300):
    if not shutil.which('openscad'):
        raise RuntimeError('OPENSCAD_NOT_INSTALLED: cannot replace CGAL with silent fallback')
    source=trimesh.load(candidate,force='mesh',process=False)
    components=source.split(only_watertight=False)
    if len(components)!=3 or [len(x.faces) for x in components]!=[4800,840,840]:
        raise ValueError('EXPECTED_EXACTLY_P1_THREE_COMPONENTS')
    if not all(x.is_volume for x in components):
        raise ValueError('P1_COMPONENT_NOT_CLOSED_POSITIVE_VOLUME')
    with tempfile.TemporaryDirectory(prefix='w4-p2-cgal-') as d:
        wd=Path(d)
        names=['body.off','handle.off','spout.off']
        for part,name in zip(components,names):
            write_off(wd/name,part)
        (wd/'union.scad').write_text('union() {\n' + ''.join(
            f'  import("{name}", convexity=10);\n' for name in names) + '}\n',encoding='utf-8')
        cmd=['openscad','--hardwarnings','--export-format','binstl','-o','union.stl','union.scad']
        t0=time.monotonic()
        try:
            proc=subprocess.run(cmd,cwd=wd,capture_output=True,text=True,timeout=timeout,check=False)
        except subprocess.TimeoutExpired as ex:
            raise RuntimeError('CGAL_NATIVE_TIMEOUT') from ex
        duration=time.monotonic()-t0
        log=proc.stdout+'\n'+proc.stderr
        if proc.returncode!=0 or 'Simple:        yes' not in log or not (wd/'union.stl').exists():
            raise RuntimeError(f'CGAL_UNION_FAILED rc={proc.returncode}: {log[-3000:]}')
        shutil.copyfile(wd/'union.stl',binary)
        return dict(engine='OpenSCAD CGAL Nef',returncode=proc.returncode,
                    duration_seconds=round(duration,4),stdout_stderr=log,
                    native_simple_yes=True,
                    native_reported_volumes=int(re.search(r'Volumes:\s*(\d+)',log).group(1))
                    if re.search(r'Volumes:\s*(\d+)',log) else None,
                    binary_stl_sha256=sha256(binary))


def prepare(source, candidate, output, timeout=300, require_optimization_ready=False,
            verify_existing=False):
    source=Path(source);candidate=Path(candidate);output=Path(output)
    source_check(source,candidate)
    output.mkdir(parents=True,exist_ok=True)
    path_y=output/'p2-teapot-cgal-union-y-up.obj'
    path_z=output/'p2-teapot-cgal-union-z-up.obj'
    binary=output/'p2-native-cgal-union.stl'
    if verify_existing:
        if not all(p.exists() for p in (path_y,path_z,binary)):
            raise ValueError('P2_SAVED_ARTIFACTS_MISSING')
        native=dict(engine='OpenSCAD CGAL Nef',native_mode='SAVED_REPLAY_NO_CGAL_RERUN',
                    binary_stl_sha256=sha256(binary),native_simple_yes=None)
        mesh=trimesh.load(path_y,force='mesh',process=False)
    else:
        native=native_union(candidate,binary,timeout)
        mesh=canonical_mesh(trimesh.load(binary,force='mesh',process=True))
        write_obj(path_y,mesh.vertices,mesh.faces,'P2 CGAL union Y_UP; not original Spin-It CAD')
        write_obj(path_z,mesh.vertices@Y_TO_Z.T,mesh.faces,'P2 proposed Z_UP; not physical scale')
    verify_y=trimesh.load(path_y,force='mesh',process=False)
    verify_z=trimesh.load(path_z,force='mesh',process=False)
    reloaded_binary=canonical_mesh(trimesh.load(binary,force='mesh',process=True))
    if not np.array_equal(mesh.vertices,verify_y.vertices) or not np.array_equal(mesh.faces,verify_y.faces):
        raise ValueError('OBJ_Y_RELOAD_CHANGED_MATERIAL')
    if not np.array_equal(mesh.vertices,reloaded_binary.vertices) or not np.array_equal(mesh.faces,reloaded_binary.faces):
        raise ValueError('STL_OBJ_GEOMETRY_MISMATCH')
    if not np.array_equal(verify_y.vertices@Y_TO_Z.T,verify_z.vertices) or not np.array_equal(verify_y.faces,verify_z.faces):
        raise ValueError('OBJ_Z_RELOAD_WRONG_FRAME')
    y_status,ok_y=geometry_gate(verify_y)
    z_status,ok_z=geometry_gate(verify_z)
    if not ok_y or not ok_z: raise ValueError('P2_GEOMETRY_INDEPENDENT_GATE_FAILED')
    if not verify_existing and native.get('native_reported_volumes')!=2:
        raise ValueError('CGAL_NEf_NOT_ONE_FILLED_SOLID')
    m, L, Q, J=independent_tetra_moments(verify_y)
    tm, tL, tQ, tJ=trimesh_oracle(verify_y)
    errors=dict(mass=abs(m-tm),first_moment=float(np.max(np.abs(L-tL))),
                raw_second=float(np.max(np.abs(Q-tQ))),inertia_origin=float(np.max(np.abs(J-tJ))))
    if max(errors.values()) > 1e-8: raise ValueError(f'MOMENT_INDEPENDENT_ORACLE_MISMATCH: {errors}')
    mz,Lz,Qz,_=independent_tetra_moments(verify_z)
    affine_error=max(abs(mz-m),float(np.max(np.abs(Lz-Y_TO_Z@L))),
                     float(np.max(np.abs(Qz-Y_TO_Z@Q@Y_TO_Z.T))))
    if affine_error>1e-8: raise ValueError(f'AFFINE_FRAME_MOMENT_MISMATCH: {affine_error}')
    p1=trimesh.load(candidate,force='mesh',process=False)
    volume_delta=float(m-p1.volume)
    report=dict(schema='w4-teapot-p2-cgal-union-preflight-v1',
        source=dict(P0_sha256=P0_SHA256,P0_git_blob=ORIGINAL_BLOB,P1_candidate_sha256=P1_SHA256,
                    source_unchanged=True,public_teapot_not_paper_author_cad=True),
        native=native,
        output=dict(y_up_obj_sha256=sha256(path_y),z_up_obj_sha256=sha256(path_z),
                    binary_stl_sha256=sha256(binary),y_up=y_status,z_up=z_status,
                    volume_unit_density=float(m),center_of_mass_unit_density=(L/m).tolist(),
                    connected_genus=(2-y_status['euler_characteristic'])//2,
                    P1_component_volume_sum=float(p1.volume),
                    P2_union_minus_P1_sum_volume=volume_delta,
                    P2_union_minus_P1_sum_relative=volume_delta/p1.volume,
                    original_raw_open_pseudovolume=25.770106073456354,
                    original_open_surface_volume_comparison_valid=False),
        independent_mass_audit=dict(moment_names=list(MOMENT_NAMES),
            y_up_tetra_moments=moments_list(m,L,Q),
            y_up_trimesh_oracle_moments=moments_list(tm,tL,tQ),
            z_up_tetra_moments=moments_list(mz,Lz,Qz),
            max_abs_oracle_error=errors,max_abs_proper_rotation_transform_error=affine_error,
            unit_density_only=True,physical_density_unspecified=True),
        frame=dict(input='Y_UP',exported_proposal='Z_UP',rotation_original_xyz_to_proposal=Y_TO_Z.tolist(),
                   det_rotation=float(np.linalg.det(Y_TO_Z)),
                   physical_scale='UNSPECIFIED_REQUIRES_W0_CASE',
                   tip='UNSPECIFIED_REQUIRES_W0_CASE',
                   spin_axis='UNSPECIFIED_REQUIRES_W0_CASE',
                   fixed_F_obj=None,removable_D_obj=None,material_partition_certified=False),
        figure9_ablations=[dict(name=n,status='NOT_RUN_WAIT_W0_W2_AND_FD')
                           for n in ('INERTIA_ONLY','LOWER_COM_ONLY','MASS_REDUCTION_ONLY')],
        acceptance=dict(numerical_mesh_geometry_gate='PASS',native_cgal_simple_yes=native.get('native_simple_yes'),
                        exact_rational_output_preserved=False,
                        paper_geometry_match=False,
                        optimization_ready=False,
                        blocker_reasons=['W0_PHYSICAL_TEAPOT_AXIS_TIP_SCALE_NOT_AUTHORIZED',
                                         'F_D_EXACT_PARTITION_NOT_CONSTRUCTED',
                                         'W2_REAL_CHERCHI_TEACHER_NOT_ADMITTED']))
    if require_optimization_ready:
        raise RuntimeError('OPTIMIZATION_BLOCKED: '+';'.join(report['acceptance']['blocker_reasons']))
    # Verification must not overwrite the original native execution provenance.
    receipt = 'p2-replay-verification.json' if verify_existing else 'p2-cgal-union-audit.json'
    (output/receipt).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--timeout',type=int,default=300)
    p.add_argument('--verify-existing',action='store_true')
    p.add_argument('--require-optimization-ready',action='store_true')
    a=p.parse_args()
    r=prepare(a.source,a.candidate,a.output,a.timeout,a.require_optimization_ready,a.verify_existing)
    print(json.dumps(dict(status=r['acceptance']['numerical_mesh_geometry_gate'],
                          volume=r['output']['volume_unit_density'],
                          components=r['output']['y_up']['components'],
                          self_contacts=r['output']['y_up']['nonincident_triangle_contacts'],
                          blockers=r['acceptance']['blocker_reasons']),indent=2))

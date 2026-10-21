#!/usr/bin/env python3
"""Materialize and verify a source-pinned W4 candidate for independent review.

The selected three meshes are copied byte-for-byte. This program neither runs
a new Boolean nor silently upgrades a repaired mesh to native exact geometry.
Its new exact boundary certificate includes reversal signs missing from P16's
orientation-preserving multiset. Numerical containment remains distinguished
from a full exact embedded-solid and physical admission certificate.
"""
from __future__ import annotations

import argparse
import copy
import csv
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import shutil

import numpy as np
import trimesh

from p16_exact_binary64_chain import (CASES, CHERCHI_COMMIT, NAMES, P14_DIR,
    OUTER_DIR, P14_SHA256, P15_SHA256, check_sources, exact_ten,
    read_obj_binary64, eq_frac_payload)
from p15_inherited_sliver_repair import (load, edge_incidence,
    independent_contact_scan, triangle_contacts)
from p17_boundary_certificate import audit_boundary_partition
from p17_physical_case import build_physical_proposal, p13_case_config

SCHEMA = 'W4P17FrozenRepairedMaterialCandidateV1'
STATUS = 'SAVED_MESH_BOUNDARY_CERTIFIED_PHYSICAL_CASE_PROPOSED_NOT_W0_ADMITTED'
PARENT_COMMIT = '7b22a3f910970951d96c1278d10a3d2945d518d2'
SELECTED = 'rotate_1p5'
# Deterministic actual six-source replay, independently reproduced from frozen
# P14 run 39462578208 and P15 run 39555122736. Packet verify replays the selected
# material and authenticates this report; build re-executes all six cases.
ALL_SIX_REPORT_SHA256 = '1c4926072d2a2d1fbc4f503141b235ba86a844b7a55f1a7c800f93c0218e59aa'
DENIED = ('original_author_CAD_certified', 'exact_Cherchi_implicit_geometry_certified',
          'original_native_vs_microweld_set_equality_certified',
          'full_exact_embedded_solid_partition_certified',
          'W0_physical_tip_or_FD_approved', 'W2_teacher_training_allowed',
          'printable_wall_thickness_certified', 'Faster_optimization_executed',
          'MuJoCo_real_optimized_before_after_executed')
MATERIAL_FILES = {'M': 'material/M_repaired_outer.obj',
                  'F': 'material/F_repaired_fixed_trial.obj',
                  'D': 'material/D_native_carveable_trial.obj'}
EXPECTED_FILES = set(MATERIAL_FILES.values()) | {
    'source/p14-report.json', 'source/p15-report.json', 'source/native-outer.obj',
    'source/native-F.obj', 'source/F-native-receipt.json', 'source/D-native-receipt.json',
    'source/shaft-reference.obj', 'source/D-hypothesis.obj', 'physical-case-proposal.json',
    'selected-boundary-certificate.json', 'all-six-boundary-certificates.json',
    'physical-properties.json', 'exact-ten-moment-partition.json',
    'numeric-geometry-preflight.json', 'repair-budget-and-limitations.json',
    'physical-table.csv',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=False)+'\n',
                          encoding='utf-8')


def vertex_link_audit(mesh):
    """A closed edge incidence alone misses a vertex pinched between surfaces."""
    links = [dict() for _ in mesh.vertices]
    for a,b,c in np.asarray(mesh.faces,dtype=np.int64):
        for vertex,x,y in ((a,b,c),(b,c,a),(c,a,b)):
            links[vertex].setdefault(int(x), []).append(int(y))
            links[vertex].setdefault(int(y), []).append(int(x))
    bad = []
    for i, graph in enumerate(links):
        if not graph or any(len(neighbors)!=2 for neighbors in graph.values()):
            bad.append(i); continue
        seen=set(); todo=[next(iter(graph))]
        while todo:
            v=todo.pop()
            if v in seen: continue
            seen.add(v); todo.extend(graph[v])
        if len(seen)!=len(graph): bad.append(i)
    return dict(vertices_tested=len(links), non_circular_vertex_links=bad,
                arithmetic='EXACT_INDEXED_GRAPH_NOT_GEOMETRIC_INTERSECTION')


def cross_surface_scan(outer, design):
    """Finite-float SAT on *all* cross-mesh AABB candidates; no adjacency skip."""
    a=np.asarray(outer.triangles); b=np.asarray(design.triangles)
    lo=a.min(axis=1); hi=a.max(axis=1)
    checked=0; witnesses=[]
    for j, triangle in enumerate(b):
        lower=triangle.min(axis=0); upper=triangle.max(axis=0)
        ids=np.flatnonzero(np.all(lo<=upper+1e-11,axis=1)&
                           np.all(hi>=lower-1e-11,axis=1))
        checked+=len(ids)
        if not len(ids): continue
        for i in ids[triangle_contacts(triangle,a[ids],tol=1e-11)]:
            witnesses.append([int(i),int(j)])
    return dict(method='FLOAT64_CROSS_SURFACE_SAT', tolerance_reference=1e-11,
                exhaustive=True, aabb_pairs_tested=checked, witnesses=witnesses,
                native_exact_intersection_certificate=False)


def winding(mesh, point):
    triangles=np.asarray(mesh.triangles)-np.asarray(point,dtype=float)
    a,b,c=triangles.transpose(1,0,2); norm=np.linalg.norm(triangles,axis=2)
    numerator=np.einsum('ij,ij->i',a,np.cross(b,c))
    denominator=(norm.prod(axis=1)+np.einsum('ij,ij->i',a,b)*norm[:,2]+
                 np.einsum('ij,ij->i',b,c)*norm[:,0]+
                 np.einsum('ij,ij->i',c,a)*norm[:,1])
    return float(np.sum(2*np.arctan2(numerator,denominator))/(4*np.pi))


def audit_numeric_geometry(paths):
    meshes={name:load(path) for name,path in paths.items()}
    report={}
    for name,mesh in meshes.items():
        links=vertex_link_audit(mesh)
        scan=independent_contact_scan(mesh)
        components=len(mesh.split(only_watertight=False))
        if (edge_incidence(mesh) or not mesh.is_watertight or
            not mesh.is_winding_consistent or not mesh.is_volume or
            np.any(mesh.area_faces<=1e-14) or links['non_circular_vertex_links'] or
            not scan['exhaustive'] or scan['witnesses']):
            raise ValueError('NUMERICAL_MATERIAL_GEOMETRY_REJECTED_'+name)
        expected_components=2 if name=='F' else 1
        if components!=expected_components:
            raise ValueError('BOUNDARY_COMPONENT_COUNT_CHANGED_'+name)
        report[name]=dict(vertices=len(mesh.vertices),triangles=len(mesh.faces),
            closed=True, consistently_oriented=True, signed_volume_reference=float(mesh.volume),
            non_two_incident_edges=0,boundary_components=components,
            min_triangle_area_reference=float(mesh.area_faces.min()),
            vertex_links=links,nonincident_self_contact_scan=scan)
    cross=cross_surface_scan(meshes['M'],meshes['D'])
    if cross['witnesses']: raise ValueError('DESIGN_CONTACTS_OUTER_BOUNDARY')
    sample=np.array([winding(meshes['M'],point) for point in meshes['D'].vertices])
    if not np.all(np.abs(sample-1)<1e-8):
        raise ValueError('DESIGN_VERTEX_OUTSIDE_PROPOSED_OUTER')
    core=[.03,0.,.67]; removable=[.12,0.,.67]
    witnesses={label:{name:winding(mesh,point) for name,mesh in meshes.items()}
               for label,point in [('shaft_core',core),('off_axis_design',removable)]}
    for name,value in {'M':1.,'F':1.,'D':0.}.items():
        if abs(witnesses['shaft_core'][name]-value)>1e-8:
            raise ValueError('PROTECTED_SHAFT_CORE_WITNESS_FAILED')
    for name,value in {'M':1.,'F':0.,'D':1.}.items():
        if abs(witnesses['off_axis_design'][name]-value)>1e-8:
            raise ValueError('REMOVABLE_DOMAIN_WITNESS_FAILED')
    # A sphere enclosing D yields a conservative triangle-distance minus radius
    # bound. This is float arithmetic and only concerns this cavity/exterior.
    center=np.array([0.,0.,.67])
    outer=meshes['M']; design=meshes['D']
    closest=trimesh.triangles.closest_point(outer.triangles,
                                        np.repeat(center[None,:],len(outer.faces),axis=0))
    nearest=float(np.linalg.norm(closest-center,axis=1).min())
    radius=float(np.linalg.norm(design.vertices-center,axis=1).max())
    clearance=nearest-radius
    if clearance<=0: raise ValueError('NO_POSITIVE_CAVITY_CLEARANCE_BOUND')
    return dict(materials=report,cross_outer_design=cross,
        design_vertices_winding_in_outer=dict(count=len(sample),minimum=float(sample.min()),
                                              maximum=float(sample.max()),tolerance=1e-8),
        protected_core_reference=core,removable_witness_reference=removable,
        point_winding_witnesses=witnesses,
        cavity_to_exterior_ball_bound_reference=clearance,
        cavity_to_exterior_ball_bound_m=clearance*.025,
        numerical_partition_preflight=True,full_exact_solid_partition_certified=False,
        incident_triangle_contacts_not_exhaustively_certified=True,
        local_wall_strength_or_printability_certified=False)


def strict_source_claims(p14_report,p15_report):
    if sha(p14_report)!=P14_SHA256 or sha(p15_report)!=P15_SHA256:
        raise ValueError('FROZEN_SOURCE_REPORT_CHANGED')
    p14=json.loads(Path(p14_report).read_text()); p15=json.loads(Path(p15_report).read_text())
    if (p14['admissible_candidate'] is not None or p14['W0_approved'] is not False or
        p14['status']!='COMPLETED_NEGATIVE_NATIVE_JUNCTION_STUDY' or
        p15['selected']!=SELECTED or p15['native_source_commit']!=CHERCHI_COMMIT):
        raise ValueError('SOURCE_STATUS_OR_CHERCHI_IDENTITY_CHANGED')
    for key in ('exact_Cherchi_implicit_geometry_certified','W0_physical_tip_or_FD_approved',
                'SpinIt_Faster_optimization_executed','MuJoCo_before_after_optimization_run'):
        if p15.get(key) is not False: raise ValueError('FALSE_UPSTREAM_ADMISSION_'+key)
    c14=next(c for c in p14['cases'] if c['name']==SELECTED)
    c15=next(c for c in p15['cases'] if c['name']==SELECTED)
    return p14,p15,c14,c15


def validate_packet_files(packet):
    packet=Path(packet)
    if packet.is_symlink() or (packet/'manifest.json').is_symlink():
        raise ValueError('P17_SYMLINK_PACKAGE_NOT_ALLOWED')
    manifest=json.loads((packet/'manifest.json').read_text())
    if (manifest.get('schema')!=SCHEMA or manifest.get('status')!=STATUS or
        manifest.get('selected_candidate')!=SELECTED or
        manifest.get('parent_W4_commit')!=PARENT_COMMIT):
        raise ValueError('P17_MANIFEST_IDENTITY_CHANGED')
    if (manifest.get('native_cherchi_commit')!=CHERCHI_COMMIT or
        manifest.get('source_P14_run')!=39462578208 or
        manifest.get('source_P15_run')!=39555122736 or
        manifest.get('materials')!=MATERIAL_FILES or
        manifest.get('selection_reason')!='P15_PREDECLARED_FIRST_FEASIBLE_NOT_AN_OPTIMUM' or
        manifest.get('selected_material_bytes_unchanged_from_P14_P15') is not True or
        manifest.get('saved_binary64_oriented_boundary_identity_certified') is not True or
        manifest.get('proposed_case_is_not_W0_approval') is not True or
        set(manifest.get('files_sha256',{}))!=EXPECTED_FILES):
        raise ValueError('P17_MANIFEST_PROVENANCE_OR_INVENTORY_CHANGED')
    if any(manifest.get(name) is not False for name in DENIED):
        raise ValueError('P17_PREMATURE_SCIENTIFIC_APPROVAL')
    for rel,digest in manifest['files_sha256'].items():
        path=Path(rel)
        if path.is_absolute() or '..' in path.parts or path.as_posix()!=rel:
            raise ValueError('P17_UNSAFE_RELATIVE_PATH')
        actual=packet/path
        chain=[packet/Path(*path.parts[:i]) for i in range(1,len(path.parts)+1)]
        if any(p.is_symlink() for p in chain) or not actual.resolve().is_relative_to(packet.resolve()):
            raise ValueError('P17_SYMLINK_OR_EXTERNAL_PACKAGE_FILE')
        if not actual.is_file() or sha(actual)!=digest:
            raise ValueError('P17_PACKAGE_FILE_SHA_MISMATCH_'+rel)
    if sha(packet/'all-six-boundary-certificates.json')!=ALL_SIX_REPORT_SHA256:
        raise ValueError('P17_FROZEN_ALL_SIX_BOUNDARY_REPORT_CHANGED')
    p14,p15,c14,c15=strict_source_claims(packet/'source/p14-report.json',
                                        packet/'source/p15-report.json')
    expected={MATERIAL_FILES['M']:p15['outer_cleaned_sha256'],
              MATERIAL_FILES['F']:c15['F_postprocessed_sha256'],
              MATERIAL_FILES['D']:c15['D_original_native_sha256'],
              'source/native-outer.obj':p15['original_Cherchi_outer_sha256'],
              'source/native-F.obj':c15['F_original_native_sha256'],
              'source/shaft-reference.obj':p14['source_sha256']['shaft'],
              'source/D-hypothesis.obj':c14['D_input_sha256']}
    for rel,digest in expected.items():
        if manifest['files_sha256'].get(rel)!=digest or sha(packet/rel)!=digest:
            raise ValueError('P17_SOURCE_DERIVED_HASH_MISMATCH_'+rel)
    for name,key in [('F','F_native'),('D','D_native')]:
        receipt=json.loads((packet/f'source/{name}-native-receipt.json').read_text())
        if not typed_exact_equal(receipt,c14[key]) or type(receipt['returncode']) is not int or receipt['returncode']!=0:
            raise ValueError('P17_NATIVE_SAME_CALL_RECEIPT_CHANGED_'+name)
    proposal=json.loads((packet/'physical-case-proposal.json').read_text())
    if not typed_exact_equal(proposal,p13_case_config()) or any(proposal.get(n) is not False for n in
                                        p13_case_config() if isinstance(p13_case_config()[n],bool)):
        raise ValueError('P17_PHYSICAL_PROPOSAL_CHANGED')
    return manifest


def _physical_and_exact(paths,hashes,proposal):
    physical=build_physical_proposal(paths,case_config=proposal,expected_sha256=hashes)
    values=[]
    for name in ('M','F','D'):
        values.append([Fraction(x['numerator'])/Fraction(x['denominator']) for x in
                       physical['materials'][name]['source_raw_ten_exact']])
    residual=[a-b-c for a,b,c in zip(*values)]
    if any(residual): raise ValueError('P17_EXACT_TEN_MOMENT_PARTITION_FAILED')
    return physical,dict(moment_order=list(NAMES),
        saved_binary64_raw_ten_additivity_exact=True,
        residual=[eq_frac_payload(x) for x in residual])


def typed_exact_equal(actual,expected):
    if type(actual) is not type(expected): return False
    if isinstance(actual,dict):
        return set(actual)==set(expected) and all(typed_exact_equal(actual[k],expected[k]) for k in actual)
    if isinstance(actual,list):
        return len(actual)==len(expected) and all(typed_exact_equal(a,b) for a,b in zip(actual,expected))
    return actual==expected


def physical_reports_equal(actual,expected):
    """Only LAPACK-derived principal moments may vary across runners by ulps."""
    a,b=copy.deepcopy(actual),copy.deepcopy(expected)
    for group in ('materials','physical_table'):
        if group=='materials':
            if set(a[group])!=set(b[group]): return False
            pairs=[(a[group][key],b[group][key]) for key in a[group]]
        else:
            if len(a[group])!=len(b[group]): return False
            pairs=list(zip(a[group],b[group]))
        for x,y in pairs:
            left=x.pop('principal_inertia_kg_m2',None)
            right=y.pop('principal_inertia_kg_m2',None)
            if not isinstance(left,list) or not isinstance(right,list) or len(left)!=3 or len(right)!=3:
                return False
            if not all(isinstance(v,float) and math.isfinite(v) for v in left+right): return False
            if not all(math.isclose(v,w,rel_tol=1e-12,abs_tol=0.) for v,w in zip(left,right)): return False
    return typed_exact_equal(a,b)


def numeric_reports_equal(actual,expected):
    """Numerical audit replays have strict structure/booleans and bounded ulps."""
    if type(actual) is not type(expected): return False
    if isinstance(actual,dict):
        return set(actual)==set(expected) and all(numeric_reports_equal(actual[k],expected[k]) for k in actual)
    if isinstance(actual,list):
        return len(actual)==len(expected) and all(numeric_reports_equal(a,b) for a,b in zip(actual,expected))
    if isinstance(actual,float):
        return math.isfinite(actual) and math.isfinite(expected) and math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12)
    return actual==expected


def repair_report(packet,new_raw_ten=None):
    packet=Path(packet)
    old10=exact_ten(*read_obj_binary64(packet/'source/native-outer.obj'))
    if new_raw_ten is None:
        new_raw_ten=exact_ten(*read_obj_binary64(packet/MATERIAL_FILES['M']))
    delta=old10[0]-new_raw_ten[0]
    if not delta or abs(float(delta))>=1e-12:
        raise ValueError('P17_MICROWELD_NONIDENTITY_WITNESS_CHANGED')
    return dict(
        source_cherchi_algorithm_commit=CHERCHI_COMMIT,
        native_output_is_modified_by_P15_micro_weld=True,
        allowed_vertex_displacement_reference=1e-15,
        observed_max_vertex_displacement_reference=2.225860458774576e-16,
        collapsed_vertex_pairs=14,removed_inherited_sliver_faces=28,
        exact_signed_volume_difference_native_minus_repaired=eq_frac_payload(delta),
        original_public_Teapot_handle_has_P9_source_deviation=True,
        repaired_material_is_original_author_CAD=False,
        source_P14_11_variant_native_acceptance_remains_negative=True,
        current_milestone_new_native_Boolean_calls=0,
        existing_P15_F_reconstruction_required_for_chain_closure=False,
        **{name:False for name in DENIED})


def physical_csv_bytes(physical):
    stream=io.StringIO(newline='');writer=csv.writer(stream)
    writer.writerow(['material','mass_kg','com_x_m','com_y_m','com_z_m',
                     'Ixx_com_kg_m2','Iyy_com_kg_m2','Izz_com_kg_m2'])
    for name in ('M','F','D'):
        x=physical['materials'][name];I=x['full_inertia_com_kg_m2']
        writer.writerow([name,x['mass_kg'],*x['center_of_mass_m'],I[0][0],I[1][1],I[2][2]])
    return stream.getvalue().encode('utf-8')


def verify_packet(packet,*,recompute=True):
    packet=Path(packet);manifest=validate_packet_files(packet)
    if recompute:
        paths={name:packet/rel for name,rel in MATERIAL_FILES.items()}
        hashes={name:sha(p) for name,p in paths.items()}
        boundary=audit_boundary_partition(paths['M'],paths['F'],paths['D'])
        if not boundary['exact_signed_triangle_chain_zero']:
            raise ValueError('P17_EXACT_SIGNED_BOUNDARY_IDENTITY_FAILED')
        expected_boundary=json.loads((packet/'selected-boundary-certificate.json').read_text())
        if not typed_exact_equal(boundary,expected_boundary): raise ValueError('P17_BOUNDARY_REPORT_REPLAY_MISMATCH')
        physical,exact=_physical_and_exact(paths,hashes,p13_case_config())
        if not physical_reports_equal(physical,json.loads((packet/'physical-properties.json').read_text())):
            raise ValueError('P17_PHYSICAL_REPORT_REPLAY_MISMATCH')
        if not typed_exact_equal(exact,json.loads((packet/'exact-ten-moment-partition.json').read_text())):
            raise ValueError('P17_EXACT_MOMENT_REPORT_REPLAY_MISMATCH')
        geometry=audit_numeric_geometry(paths)
        # Numerical fields may differ by a few ulps on a different runner; the
        # independent replay must pass every gate, while source/report SHA stays exact.
        if not numeric_reports_equal(geometry,json.loads((packet/'numeric-geometry-preflight.json').read_text())):
            raise ValueError('P17_NUMERICAL_GEOMETRY_REPORT_REPLAY_MISMATCH')
        if not typed_exact_equal(repair_report(packet),json.loads((packet/'repair-budget-and-limitations.json').read_text())):
            raise ValueError('P17_REPAIR_REPORT_REPLAY_MISMATCH')
        if physical_csv_bytes(physical)!=(packet/'physical-table.csv').read_bytes():
            raise ValueError('P17_PHYSICAL_CSV_REPLAY_MISMATCH')
    return dict(status='P17_PACKET_VERIFIED_NOT_W0_ADMITTED',
                selected_candidate=SELECTED,source_files_verified=len(manifest['files_sha256']),
                recomputed_geometry_and_physics=bool(recompute),
                selected_material_replayed_here=bool(recompute),
                all_six_report_digest_authenticated=True,
                all_six_material_sources_replayed_by_verify=False,
                **{name:False for name in DENIED})


def build_packet(p14_root,p15_root,out):
    p14_root,p15_root,out=map(Path,(p14_root,p15_root,out))
    if out.exists(): raise FileExistsError('P17_OUTPUT_MUST_BE_A_NEW_DIRECTORY')
    native_outer,clean_outer,cases=check_sources(p14_root,p15_root)
    _,_,c14,_=strict_source_claims(p14_root/P14_DIR/'p14-junction-native-study.json',
                                  p15_root/'p15-inherited-sliver-study.json')
    selected=cases[SELECTED]
    source_files={
        MATERIAL_FILES['M']:clean_outer,MATERIAL_FILES['F']:selected['cleanF'],
        MATERIAL_FILES['D']:selected['nativeD'],
        'source/p14-report.json':p14_root/P14_DIR/'p14-junction-native-study.json',
        'source/p15-report.json':p15_root/'p15-inherited-sliver-study.json',
        'source/native-outer.obj':native_outer,'source/native-F.obj':selected['nativeF'],
        'source/F-native-receipt.json':Path(str(selected['nativeF'])+'.native.json'),
        'source/D-native-receipt.json':Path(str(selected['nativeD'])+'.native.json'),
        'source/shaft-reference.obj':p14_root/OUTER_DIR/'p13-shaft-reference.obj',
        'source/D-hypothesis.obj':p14_root/P14_DIR/SELECTED/'hypothesis_D.obj',
    }
    for name,key in [('F','F_native'),('D','D_native')]:
        if not typed_exact_equal(json.loads(source_files[f'source/{name}-native-receipt.json'].read_text()),c14[key]):
            raise ValueError('P17_SOURCE_NATIVE_RECEIPT_INCONSISTENT_'+name)
    out.mkdir(parents=True)
    for rel,source in source_files.items():
        target=out/rel;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,target)
        if sha(source)!=sha(target): raise ValueError('P17_BYTE_COPY_FAILED')
    proposal=p13_case_config();save_json(out/'physical-case-proposal.json',proposal)
    paths={name:out/rel for name,rel in MATERIAL_FILES.items()}
    boundary=audit_boundary_partition(paths['M'],paths['F'],paths['D'])
    if not boundary['exact_signed_triangle_chain_zero']:
        raise ValueError('P17_SELECTED_BOUNDARY_REJECTED')
    save_json(out/'selected-boundary-certificate.json',boundary)
    six=[]
    for name in CASES:
        item=cases[name]
        for kind,m,f in [('native_saved',native_outer,item['nativeF']),
                         ('microweld_saved',clean_outer,item['cleanF'])]:
            row=audit_boundary_partition(m,f,item['nativeD'])
            if not row['exact_signed_triangle_chain_zero']:
                raise ValueError('P17_SOURCE_BOUNDARY_REGRESSION_'+name+'_'+kind)
            six.append(dict(candidate=name,material_version=kind,certificate=row))
    save_json(out/'all-six-boundary-certificates.json',dict(cases=six,
        all_six_exact_signed_chains_zero=True,
        legacy_P16_counter_preserves_orientation_without_reversal_sign=True,
        prior_P16_nonzero_volume_delta_remains_valid=True))
    physical,exact=_physical_and_exact(paths,{n:sha(p) for n,p in paths.items()},proposal)
    save_json(out/'physical-properties.json',physical)
    save_json(out/'exact-ten-moment-partition.json',exact)
    numeric=audit_numeric_geometry(paths)
    save_json(out/'numeric-geometry-preflight.json',numeric)
    save_json(out/'repair-budget-and-limitations.json',repair_report(out))
    (out/'physical-table.csv').write_bytes(physical_csv_bytes(physical))
    files={p.relative_to(out).as_posix():sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
    manifest=dict(schema=SCHEMA,status=STATUS,parent_W4_commit=PARENT_COMMIT,
        selected_candidate=SELECTED,selection_reason='P15_PREDECLARED_FIRST_FEASIBLE_NOT_AN_OPTIMUM',
        source_P14_run=39462578208,source_P15_run=39555122736,
        native_cherchi_commit=CHERCHI_COMMIT,
        materials=MATERIAL_FILES,files_sha256=files,
        selected_material_bytes_unchanged_from_P14_P15=True,
        saved_binary64_oriented_boundary_identity_certified=True,
        proposed_case_is_not_W0_approval=True,
        **{name:False for name in DENIED})
    save_json(out/'manifest.json',manifest)
    validate_packet_files(out)
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    build=sub.add_parser('build')
    build.add_argument('--p14-root',type=Path,required=True)
    build.add_argument('--p15-root',type=Path,required=True)
    build.add_argument('--out',type=Path,required=True)
    verify=sub.add_parser('verify');verify.add_argument('--packet',type=Path,required=True)
    args=parser.parse_args()
    if args.command=='build':
        result=build_packet(args.p14_root,args.p15_root,args.out)
        print(json.dumps({k:result[k] for k in ('status','selected_candidate',
              'saved_binary64_oriented_boundary_identity_certified',*DENIED)},indent=2))
    else:
        print(json.dumps(verify_packet(args.packet),indent=2))


if __name__=='__main__': main()

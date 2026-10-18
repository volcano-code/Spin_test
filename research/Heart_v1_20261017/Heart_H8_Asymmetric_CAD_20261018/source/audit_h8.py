"""Independent H8 exported OBJ audit, including a rigorous conservative bound.

Never treats a positive mesh distance bound as proof of no mesh self-intersection
within either surface; full native exact audits remain separate admission gates.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
import trimesh


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical_mesh(path):
    mesh=trimesh.load(path,force='mesh',process=False)
    if not isinstance(mesh,trimesh.Trimesh) or not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
        raise ValueError('RELOADED_MESH_INVALID:'+str(path))
    return mesh


def triangle_sphere_distance_bound(a,b):
    """Every triangle lives in radius max ||vertex-centroid|| around centroid.

    For all pairs (A_i,B_j): distance >= ||cA_i-cB_j||-rA_i-rB_j.
    cKDTree finds nearest cB_j, and rB_max is >= every rB_j, hence
    min_i [nearest-centroid-distance(i)-rA_i-rB_max] is a valid global
    lower bound on minimum surface-to-surface Euclidean distance.
    This does not require rtree or any approximate closest-point search.
    """
    A=a.triangles;B=b.triangles
    ca=A.mean(axis=1);cb=B.mean(axis=1)
    ra=np.linalg.norm(A-ca[:,None,:],axis=2).max(axis=1)
    rb=np.linalg.norm(B-cb[:,None,:],axis=2).max(axis=1)
    d=cKDTree(cb).query(ca,k=1,eps=0,workers=-1)[0]
    if not np.all(np.isfinite(d)):
        raise ValueError('INVALID_TRIANGLE_BALL_SPATIAL_DISTANCE')
    return float(np.min(d-ra-np.max(rb)))


def exact_oriented_partition(outer,design,fixed):
    na=len(outer.vertices);fa=len(outer.faces);nd=len(design.vertices)
    if len(fixed.vertices)!=na+nd or len(fixed.faces)!=fa+len(design.faces):
        raise ValueError('F_D_EXPORTED_FACE_COUNTS_MISMATCH')
    if (not np.array_equal(fixed.vertices[:na],outer.vertices) or
        not np.array_equal(fixed.vertices[na:],design.vertices) or
        not np.array_equal(fixed.faces[:fa],outer.faces) or
        not np.array_equal(fixed.faces[fa:]-na,design.faces[:,::-1])):
        raise ValueError('F_D_GLOBAL_EXACT_ORIENTED_CHAIN_NOT_CANCELLING')
    return True


def independent_raw_moments(mesh):
    # Independent of original surface tensor routine: integrate signed
    # tetrahedra via trimesh.mass_properties (center, inertia and volume).
    props=mesh.mass_properties
    return dict(volume=float(props['volume']),center_mass=np.asarray(props['center_mass']).tolist(),
                inertia=np.asarray(props['inertia']).tolist())


def audit(output,claimed_min_wall_mm=.375):
    output=Path(output)
    paths={k:output/(k+'.obj') for k in ['heart_input','shaft','initial_top','fixed_shell','design_domain']}
    original=json.loads((output/'H8_CAD_AUDIT.json').read_text())
    if original.get('classification')!='PAPER_INSPIRED_RECONSTRUCTED_CAD_NOT_AUTHOR_CAD_NOT_OPTIMIZED' or original.get('faster_newton_converged') is not False:
        raise ValueError('INVALID_OR_MISLABELED_H8_INPUT_SCOPE')
    meshes={k:canonical_mesh(v) for k,v in paths.items()}
    for name,path in paths.items():
        if original['sha256'].get(path.name)!=sha(path):
            raise ValueError('OBJ_SHA256_DRIFT:'+name)
    outer=meshes['initial_top'];design=meshes['design_domain'];fixed=meshes['fixed_shell']
    if len(outer.split(only_watertight=False))!=1 or len(design.split(only_watertight=False))!=1 or len(fixed.split(only_watertight=False))!=2:
        raise ValueError('INVALID_REGION_COMPONENT_COUNTS')
    if not exact_oriented_partition(outer,design,fixed):raise ValueError('REGION_PARTITION_FAIL')
    bound=triangle_sphere_distance_bound(design,outer)
    if bound<=max(0.,claimed_min_wall_mm)+1e-6:
        raise ValueError('NO_CONFIDENT_BOUNDARY_CLEARANCE_BEYOND_MINIMUM')
    v=independent_raw_moments(outer)
    vf=independent_raw_moments(fixed)
    vd=independent_raw_moments(design)
    scale=max(v['volume'],1)
    volume_residual=abs(v['volume']-vf['volume']-vd['volume'])/scale
    moment_num=np.asarray(v['center_mass'])*v['volume']-(np.asarray(vf['center_mass'])*vf['volume']+np.asarray(vd['center_mass'])*vd['volume'])
    moment_err=float(np.linalg.norm(moment_num)/max(scale,1))
    if volume_residual>1e-10 or moment_err>1e-9:
        raise ValueError('INDEPENDENT_MASS_MOMENT_ADDITIVITY_FAILED')
    if np.linalg.norm(np.asarray(v['center_mass'])[:2])<1.:raise ValueError('INITIAL_HEART_NOT_OFF_AXIS')
    # Restated claims stay restricted: no new native exact geometry, dynamics.
    result=dict(schema='heart-h8-independent-export-audit-v1',
      retained_source_classification=original['classification'],
      success=True,ordinary_mesh_export_qualified=True,
      original_author_cad_qualified=False,formal_newton_qualified=False,
      actual_point_point_minimum_not_claimed=True,
      full_self_intersection_native_audit_performed=False,
      native_Cherchi_boolean_performed=False,
      geometric_nesting_from_common_implicit_field=True,
      exact_oriented_face_chain_cancelled=True,
      conservative_all_triangle_pair_distance_lower_bound_mm=bound,
      required_min_surface_clearance_mm=claimed_min_wall_mm,
      conservative_wall_clearance_gate_passed=bound>=claimed_min_wall_mm,
      volume_additivity_relative_error=float(volume_residual),
      first_moment_additivity_error_mm=float(moment_err),
      exterior_com_axis_offset_mm=float(np.linalg.norm(np.asarray(v['center_mass'])[:2])),
      original_data_sha256=sha(output/'H8_CAD_AUDIT.json'),
      exported_file_sha256={k:sha(p) for k,p in paths.items()})
    (output/'H8_INDEPENDENT_AUDIT.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();print(json.dumps(audit(a.output),indent=2))
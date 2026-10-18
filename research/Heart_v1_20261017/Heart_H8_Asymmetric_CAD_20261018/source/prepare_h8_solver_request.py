"""Reproducible adapter: H8 CAD OBJ files -> frozen SpinItFasterRequest JSON.
This prepares inputs only. It never performs Cherchi or Newton optimization.
For the complete offline, independently tested snapshot see H8 Stage2 ZIP.
"""
import argparse,hashlib,json
from pathlib import Path
import numpy as np
import trimesh

FILES=('heart_input.obj','shaft.obj','initial_top.obj','fixed_shell.obj','design_domain.obj')
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def raw_moments(mesh):
    t=np.asarray(mesh.triangles,dtype=float);a,b,c=t[:,0],t[:,1],t[:,2]
    v=np.einsum('ij,ij->i',a,np.cross(b,c))/6;s=t.sum(axis=1)
    q=np.einsum('i,ijk->jk',v,np.einsum('ni,nj->nij',s,s)+np.einsum('nki,nkj->nij',t,t))/20
    first=np.einsum('i,ij->j',v,s)/4
    return np.asarray([v.sum(),*first,*np.diag(q),q[1,2],q[0,2],q[0,1]])
def build(cad,output):
    cad=Path(cad);output=Path(output)
    if output.exists():raise FileExistsError('FROZEN_REQUEST_EXISTS')
    info=json.loads((cad/'H8_CAD_AUDIT.json').read_text())
    audit=json.loads((cad/'H8_INDEPENDENT_AUDIT.json').read_text())
    if info['classification']!='PAPER_INSPIRED_RECONSTRUCTED_CAD_NOT_AUTHOR_CAD_NOT_OPTIMIZED' or not audit['success']:
        raise ValueError('INVALID_H8_CAD_SCOPE')
    scale=float(info['parameters']['length_mm']);rho=float(info['parameters']['density_kg_m3'])
    meshes={}
    for name in FILES:
        if digest(cad/name)!=info['sha256'][name]:raise ValueError('H8_SHA256_DRIFT:'+name)
        mesh=trimesh.load(cad/name,force='mesh',process=False)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:raise ValueError('H8_MESH_INVALID:'+name)
        meshes[name]=mesh
    o=meshes['initial_top.obj'];d=meshes['design_domain.obj'];f=meshes['fixed_shell.obj']
    power=np.asarray([scale**3]+[scale**4]*3+[scale**5]*6)
    om,dm,fm=[raw_moments(x) for x in (o,d,f)]
    error=float(np.max(np.abs((om-dm-fm)/power)))
    if error>1e-9:raise ValueError('F_D_MOMENT_PARTITION_FAILED')
    def geom(m):return dict(vertices=(np.asarray(m.vertices)/scale).tolist(),faces=np.asarray(m.faces,dtype=int).tolist())
    outer=geom(o);design=geom(d)
    z=float(np.min(meshes['shaft.obj'].vertices[:,2])/scale)
    request=dict(outer_vertices=outer['vertices'],outer_faces=outer['faces'],
      design_vertices=design['vertices'],design_faces=design['faces'],
      fixed_shell_moments=(fm/power).tolist(),target_origin=[0.,0.,z],
      target_axes=[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]],mode='SPINNING_TOP',
      material_density=1.,original_units_per_normalized_unit=scale/1000.,
      minimum_wall_thickness=audit['conservative_all_triangle_pair_distance_lower_bound_mm']/scale,
      evidence='RECONSTRUCTED_ASSET',center_of_mass_weight=0.,
      spinning_top_objective='INERTIA_AND_LOWERING',
      settings=dict(maximum_iterations=60,maximum_restarts=8,
        maximum_function_evaluations_per_restart=60,equation_tolerance=1e-12,
        physical_relative_tolerance=1e-6,deterministic_seed=0,
        equation_profile='DUAL_MONOMIAL_RAW_V1',capture_evaluation_payload=True))
    evaluator=dict(derivative_method='DISCRETE_FULL_RANK_QUADRIC',
       icosphere_subdivisions=2,maximum_icosphere_subdivisions=2,
       maximum_radius_doublings=8,retain_fixed_normal_provenance=True,
       paper_projective_hyperboloid=True,algebraic_finite_map=False)
    report=dict(schema='spin-heart-h8-faster-request-v1',
      scope='H8_RECONSTRUCTED_CAD_ONLY_NOT_NATIVE_CERTIFIED_NOT_SOLVED',
      normalized_scale_mm_per_unit=scale,
      native_exact_boundary_admitted=False,newton_converged=False,
      original_author_cad=False,
      source_sha256={n:digest(cad/n) for n in FILES},
      source_length_mm=scale,density_kg_m3=rho,
      normalized_ten_moment_residual=error,
      initial_COM_axis_offset_mm=info['initial_physical']['COM_axis_offset_mm'],
      native_boundary_certified=False,cherchi_boolean_completed=False,
      jacobian_certified=False,author_CAD=False)
    output.mkdir(parents=True)
    (output/'prepared-request.json').write_text(json.dumps(dict(
       schema='spin-heart-h8-faster-preparation-v1',request=request,
       evaluator_settings=evaluator,evidence=report),indent=2,allow_nan=False)+'\n')
    report['request_sha256']=digest(output/'prepared-request.json')
    (output/'manifest.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--cad',required=True,type=Path)
    ap.add_argument('--output',required=True,type=Path);a=ap.parse_args()
    print(json.dumps(build(a.cad,a.output),indent=2))

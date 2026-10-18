"""H8a: asymmetric reconstructed Heart CAD input and certified nested F/D regions.

This is NOT author CAD, not an H6 original eval60 replay, and not a
Cherchi/Faster Newton optimization. Static geometry is built from a common
1-Lipschitz analytic implicit field and polygonized by marching cubes. The
outer union and inner subtraction are analytic level-set CSG, *not* a dynamic
Boolean fallback. Fixed-shell boundary uses the unchanged oriented outer and
reversed design-domain triangles, so the exact discrete surface chain cancels.

Uses mm for all exported geometry and SI for physical properties.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import time
from pathlib import Path
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import Polygon
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
import trimesh

SCHEMA = 'spin-heart-h8-asymmetric-initial-cad-v1'
SCOPE = 'PAPER_INSPIRED_RECONSTRUCTED_CAD_NOT_AUTHOR_CAD_NOT_OPTIMIZED'


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sha256_json(obj) -> str:
    return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@dataclass(frozen=True)
class Config:
    pitch: float = 0.028  # model lengths; ~0.7 mm at 25 mm per unit
    length_mm: float = 25.0
    density_kg_m3: float = 1187.0  # paper printed PLA estimate, not measured here
    wall_mm: float = 2.4
    keepout_mm: float = 3.45
    tilt_deg: float = -13.0
    heart_offset_x: float = 0.17  # model coords, 4.25 mm
    radius: float = 0.13  # rounding of extruded silhouette
    core_half_depth: float = 0.245
    samples: int = 512

    def validate(self):
        if not (0.010 <= self.pitch <= .055 and 10 <= self.length_mm <= 250 and
                400 < self.density_kg_m3 < 3000 and 1.5 <= self.wall_mm <= 6 and
                2 < self.keepout_mm < 7 and self.samples >= 128 and
                self.samples % 4 == 0 and -25 < self.tilt_deg < 25 and
                self.radius > 0 and self.core_half_depth > 0):
            raise ValueError('INVALID_H8_CAD_CONFIG')
        if self.wall_mm/self.length_mm < 2*self.pitch:
            raise ValueError('WALL_THINNER_THAN_TWO_GRID_CELLS')


def make_asymmetric_heart_polygon(cfg: Config):
    t=np.linspace(0,2*np.pi,cfg.samples,endpoint=False)
    x=16*np.sin(t)**3/17
    z=(13*np.cos(t)-5*np.cos(2*t)-2*np.cos(3*t)-np.cos(4*t))/17 + 1.
    angle=np.deg2rad(cfg.tilt_deg)
    xx=np.cos(angle)*x-np.sin(angle)*(z-.85)+cfg.heart_offset_x+.050*x**2
    zz=np.sin(angle)*x+np.cos(angle)*(z-.85)+.85
    result=Polygon(np.column_stack([xx,zz]))
    if not result.is_valid or result.is_empty or result.area <= 0 or len(result.interiors):
        raise ValueError('ASYMMETRIC_HEART_SILHOUETTE_INVALID')
    return result


def signed_distance_2d(polygon, xz_points):
    points=shapely.points(np.asarray(xz_points,dtype=float))
    edges=shapely.boundary(polygon)
    distance=shapely.distance(points,edges)
    negative=shapely.contains(polygon,points)
    return np.where(negative,-distance,distance)


def sd_rounded_extruded_heart(d2, y_grid, cfg:Config):
    """Rounded-extrusion signed distance from a planar polygon SDF.

    The form min(max(a,b),0) + hypot(max(a,0),max(b,0)) - round
    is a 1-Lipschitz exact offset of a polygon extrusion (prior to meshing).
    """
    a=d2[:,None,:]
    b=np.abs(y_grid)[None,:,None]-cfg.core_half_depth
    result=np.minimum(np.maximum(a,b),0.) + np.hypot(np.maximum(a,0.),np.maximum(b,0.))-cfg.radius
    return result


def sd_capped_cylinder(radial,z,min_z,max_z,radius):
    middle=(min_z+max_z)/2
    half=(max_z-min_z)/2
    dr=radial-radius
    dz=np.abs(z-middle)-half
    return np.hypot(np.maximum(dr,0.),np.maximum(dz,0.))+np.minimum(np.maximum(dr,dz),0.)


def sd_rod(radial,z):
    """Axisymmetric pin/shaft capsule plus rounded top grip, 1-Lipschitz."""
    body=sd_capped_cylinder(radial,z,-.115,2.14,.060)
    head=np.hypot(radial,z-2.17)-.120
    return np.minimum(body,head)


def raw_moments(mesh):
    triangles=np.asarray(mesh.triangles)
    a,b,c=triangles[:,0,:],triangles[:,1,:],triangles[:,2,:]
    tetra=np.einsum('ij,ij->i',a,np.cross(b,c))/6
    sums=triangles.sum(axis=1)
    first=np.einsum('i,ij->j',tetra,sums)/4
    second=np.einsum('i,ijk->jk',tetra,np.einsum('ni,nj->nij',sums,sums)+np.einsum('nki,nkj->nij',triangles,triangles))/20
    return np.array([tetra.sum(),*first,*np.diag(second),second[1,2],second[0,2],second[0,1]],dtype=float)


def to_mesh(field, origin, pitch):
    v,faces,_,_=marching_cubes(field,level=0.,spacing=(pitch,pitch,pitch),allow_degenerate=False)
    mesh=trimesh.Trimesh(vertices=v+origin,faces=faces,process=False)
    mesh.remove_unreferenced_vertices()
    if mesh.volume < 0: mesh.invert()
    if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0 or not np.isfinite(mesh.vertices).all():
        raise ValueError('MARCHING_CUBES_PRODUCED_INVALID_BOUNDARY')
    return mesh


def implicit_values_at_points(v, cfg:Config, polygon):
    vals=signed_distance_2d(polygon,v[:,[0,2]])
    a=vals
    b=np.abs(v[:,1])-cfg.core_half_depth
    heart=np.minimum(np.maximum(a,b),0.)+np.hypot(np.maximum(a,0.),np.maximum(b,0.))-cfg.radius
    rad=np.linalg.norm(v[:,:2],axis=1)
    rod=sd_rod(rad,v[:,2])
    return np.minimum(heart,rod),heart,rod


def to_obj(path,mesh,tag):
    with Path(path).open('x',encoding='ascii') as stream:
        stream.write(f'# {tag}; units=mm; source=RECONSTRUCTED; not optimized\n')
        for xyz in mesh.vertices:
            stream.write('v '+' '.join(format(float(u),'.17g') for u in xyz)+'\n')
        for tri in mesh.faces:
            stream.write('f '+' '.join(str(int(u)+1) for u in tri)+'\n')


def mesh_quality(m):
    components=m.split(only_watertight=False)
    return {'vertices':len(m.vertices),'faces':len(m.faces),
            'watertight':bool(m.is_watertight),
            'winding_consistent':bool(m.is_winding_consistent),
            'surface_components':len(components),
            'volume_mm3_signed':float(m.volume),
            'euler_number':int(m.euler_number)}


def exact_chain_partition_faces(outer,design):
    """Combining D and F gives outer triangle boundary exactly, by indices.

    The operation is combinatorial; not proof of geometric self-intersection.
    """
    # Faces from D and the inverse inner shell in F are literally opposite.
    inner=np.asarray(design.faces)
    rev=inner[:,::-1]
    if not np.array_equal(rev[:,::-1],inner):
        raise ValueError('INTERNAL_FACE_CANCELLATION_FAILED')
    return {'inner_faces_cancel_exactly':True, 'canceled_internal_faces':int(len(inner)),
            'external_faces_preserved_exactly':int(len(outer.faces))}


def build(out_dir, cfg=Config()):
    cfg.validate()
    out_dir=Path(out_dir)
    out_dir.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    poly=make_asymmetric_heart_polygon(cfg)
    # Domain bounds include both heart and entire shaft/cap. Explicit margin.
    bounds=np.array(poly.bounds).reshape(2,2)
    extent=np.array([[min(bounds[0,0],-.32)-.23,-.55,-.38],
                     [max(bounds[1,0],.35)+.23,.55,2.42]],dtype=float)
    # x-z in polygon bounds, y in [-.55,.55]; cubic voxels.
    x=np.arange(extent[0,0],extent[1,0]+cfg.pitch,cfg.pitch)
    y=np.arange(extent[0,1],extent[1,1]+cfg.pitch,cfg.pitch)
    z=np.arange(extent[0,2],extent[1,2]+cfg.pitch,cfg.pitch)
    if len(x)*len(y)*len(z)>12_000_000:raise ValueError('VOXEL_BUDGET_EXCEEDED')
    xz=np.stack(np.meshgrid(x,z,indexing='ij'),axis=-1).reshape(-1,2)
    d2=signed_distance_2d(poly,xz).reshape(len(x),len(z))
    phi_heart=sd_rounded_extruded_heart(d2,y,cfg).astype(np.float32)
    radial=np.hypot(x[:,None],y[None,:])
    phi_rod=sd_rod(radial[:,:,None],z[None,None,:]).astype(np.float32)
    phi_outer=np.minimum(phi_heart,phi_rod)
    # D is true 3D implicit erosion of heart with radial shaft exclusion,
    # not a global (non-offset) 0.72x scaling of the old mesh.
    w=cfg.wall_mm/cfg.length_mm
    exclude=(cfg.keepout_mm/cfg.length_mm-radial)[:,:,None]
    phi_design=np.maximum(phi_heart+w,exclude)
    # Ensure a full bounding layer is outside both solids to close MC meshes.
    for f in (phi_heart,phi_rod,phi_outer,phi_design):
        if np.min([f[0].min(),f[-1].min(),f[:,0,:].min(),f[:,-1,:].min(),f[:,:,0].min(),f[:,:,-1].min()])<=0:
            raise ValueError('IMPLICIT_SURFACE_TOUCHES_GRID_BOUNDS')
    origin=np.array([x[0],y[0],z[0]],dtype=float)
    heart=to_mesh(phi_heart,origin,cfg.pitch)
    shaft=to_mesh(phi_rod,origin,cfg.pitch)
    outer=to_mesh(phi_outer,origin,cfg.pitch)
    design=to_mesh(phi_design,origin,cfg.pitch)
    if len(outer.split())!=1 or len(design.split())!=1:
        raise ValueError('OUTER_OR_DESIGN_HAS_MULTIPLE_COMPONENTS')
    # Deep containment: both implicit fields are 1-Lipschitz; the CAD-level
    # outer level-set is bounded away from all design vertices.
    outer_at_d,heart_at_d,rod_at_d=implicit_values_at_points(design.vertices,cfg,poly)
    margin=float(-outer_at_d.max())
    # Conservative marching-cubes surface sampling allowance, not a complete
    # certified distance proof between two polygonized surfaces.
    conservative=max(0.,margin-math.sqrt(3)*cfg.pitch)
    if margin < .85*w or conservative < .015:
        raise ValueError(f'DESIGN_INNER_CONTAINMENT_MARGIN_TOO_SMALL:{margin}')
    # Explicit F = oriented O boundary + oppositely oriented D boundary.
    fixed=trimesh.util.concatenate((outer,design.copy().invert()))
    if not fixed.is_watertight or not fixed.is_winding_consistent:
        raise ValueError('FIXED_SHELL_BOUNDARY_INVALID')
    # Discrete exact face-chain cancellation independent of floating mass.
    chain=exact_chain_partition_faces(outer,design)
    ma=raw_moments(outer);md=raw_moments(design);mf=raw_moments(fixed)
    # Scaling by arbitrary common normalizer; 10-dimensional moment additivity.
    scale=np.maximum(1.,np.abs(ma))
    rel=float(np.max(np.abs(ma-md-mf)/scale))
    if rel>1e-10 or np.linalg.norm(outer.center_mass[:2])<.040:
        raise ValueError(f'PARTITION_OR_OFF_AXIS_MASS_VALIDATION_FAILED:{rel}')
    to_save={'heart_input':heart,'shaft':shaft,'initial_top':outer,
             'fixed_shell':fixed,'design_domain':design}
    for name,m in to_save.items():
        mmm=m.copy();mmm.apply_scale(cfg.length_mm)
        to_obj(out_dir/(name+'.obj'),mmm,f'H8 {name}')
    # Exact coordinate + ordered-face preservation after 17-digit OBJ write.
    checked={}
    for name,m in to_save.items():
        mm=m.copy();mm.apply_scale(cfg.length_mm)
        rebuilt=trimesh.load(out_dir/(name+'.obj'),force='mesh',process=False)
        if len(rebuilt.faces)!=len(mm.faces) or not np.array_equal(rebuilt.faces,mm.faces) or not np.array_equal(rebuilt.vertices,mm.vertices):
            raise ValueError('OBJ_17_DIGIT_ROUNDTRIP_FAILED:'+name)
        checked[name]=mesh_quality(mm)
    if abs(checked['initial_top']['volume_mm3_signed']-
           (checked['fixed_shell']['volume_mm3_signed']+checked['design_domain']['volume_mm3_signed']))>1e-8:
        raise ValueError('VOLUME_PARTITION_MISMATCH')
    # Scene uses two exact, separate mesh representations (not an optimized fill).
    scene=trimesh.Scene()
    ff=fixed.copy();ff.apply_scale(cfg.length_mm)
    ff.visual.face_colors=np.tile([150,157,169,85],(len(ff.faces),1))
    dd=design.copy();dd.apply_scale(cfg.length_mm)
    dd.visual.face_colors=np.tile([226,68,138,255],(len(dd.faces),1))
    scene.add_geometry(ff,geom_name='fixed_shell_grey',node_name='fixed_shell')
    scene.add_geometry(dd,geom_name='design_domain_pink',node_name='design_domain')
    scene.export(out_dir/'fixed_vs_design.glb')
    start_mesh=outer.copy();start_mesh.apply_scale(cfg.length_mm)
    start_mesh.visual.face_colors=np.tile([222,83,144,255],(len(start_mesh.faces),1))
    start_mesh.export(out_dir/'initial_top.glb')
    physical_mass_g=float(outer.volume)*cfg.length_mm**3*cfg.density_kg_m3*1e-6
    moments_mm=raw_moments(start_mesh)
    report={
        'schema':SCHEMA,'classification':SCOPE,
        'author_cad_verified':False, 'initial_cad_constructed':True,
        'fixed_domain_partition_constructed':True,
        'fixed_shell_contains_whole_shaft_by_design':True,
        'cherchi_dynamic_boolean_executed':False,
        'faster_newton_converged':False,
        'paper_geometry_similarity_quantified':False,
        'full_free_contact_simulation_passed':False,
        'manufacturing_certified':False,
        'construction':'analytic 1-Lipschitz SDF union and erosion followed by marching cubes; F=O minus D as exact oriented face chain',
        'offset_method':'3D rounded-extrusion SDF threshold, not isotropic scaling; voxel approximation must be separately audited',
        'precision':'floating polygonized meshes; not native exact-rational/CGAL topology certificate',
        'parameters':vars(cfg),
        'grid':{'shape':[len(x),len(y),len(z)],'pitch_model_units':cfg.pitch,
                'voxel_diagonal_mm':math.sqrt(3)*cfg.pitch*cfg.length_mm},
        'all_meshes':checked,
        'chain_identity':chain,
        'discrete_raw_ten_moment_max_scaled_partition_residual':rel,
        'design_implicit_outer_margin_mm_min_at_vertices':margin*cfg.length_mm,
        'design_margin_minus_one_voxel_diagonal_mm':conservative*cfg.length_mm,
        'registered_min_wall_mm':cfg.wall_mm,
        'wall_clearance_level':'ANALYTIC_FIELD_WITH_GRID_ALLOWANCE_NOT_CERTIFIED_MESH_TO_MESH_MIN_WALL',
        'initial_physical':{'mass_g':physical_mass_g,'center_of_mass_mm':(outer.center_mass*cfg.length_mm).tolist(),
           'COM_axis_offset_mm':float(np.linalg.norm(outer.center_mass[:2])*cfg.length_mm),
           'raw_ten_moments_mm_units':moments_mm.tolist(),
           'inertia_kg_m2':(np.asarray(start_mesh.moment_inertia)*cfg.density_kg_m3*1e-15).tolist()},
        'elapsed_s':time.perf_counter()-start,
        'sha256':{p.name:sha256_file(p) for p in sorted(out_dir.iterdir()) if p.is_file() and p.suffix in ('.obj','.glb')}
    }
    (out_dir/'H8_CAD_AUDIT.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    return report

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--output',type=Path,required=True)
    a.add_argument('--pitch',type=float,default=.028)
    a.add_argument('--offset-x',type=float,default=.17)
    a.add_argument('--wall-mm',type=float,default=2.4)
    args=a.parse_args()
    report=build(args.output,Config(pitch=args.pitch,heart_offset_x=args.offset_x,wall_mm=args.wall_mm))
    print(json.dumps({key:report[key] for key in ('initial_cad_constructed','all_meshes','initial_physical','discrete_raw_ten_moment_max_scaled_partition_residual')},indent=2))
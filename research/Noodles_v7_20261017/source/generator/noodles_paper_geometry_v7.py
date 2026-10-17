"""Noodles v7: photo-guided *input hypothesis*, never a solved/optimized result.

This is a versioned alternative to v6. It does not edit the Cherchi backend,
Newton objective, mass-moment equations or convergence settings. The paper's
original CAD is unavailable; these spline choices are unverified hypotheses.

Materials: F = exact UNION(fixed_parts); D = E\\F; A = E UNION F.
These expressions must be realized and independently audited by a Boolean
backend before attempting any optimization.
"""
from __future__ import annotations
import hashlib
import json
from copy import deepcopy
from pathlib import Path
import numpy as np
import trimesh
import noodles_dense_v5_input as old
from noodles_input import mesh_audit, write_obj

SPEC = deepcopy(old.SPEC)
SPEC.update(
    schema='noodles-paper-photo-hypothesis-v7', classification='RECONSTRUCTED_METHOD_VALIDATION',
    author_original=False, paper_cad_available=False, permanent_ellipsoid_shell=False,
    hypothesis_frozen_before_optimization=True,
    parent='noodles-paper-domain-v6',
    design_envelope='outer-ellipsoid',
    z_flatten_scale=0.60,  # reduced body thickness to model the flattened photo silhouette
    centerline_y_preservation=0.78,  # old y(s)=y0*s^2 produced radial spokes
    strand_y_weave_amplitude=.034, strand_z_weave_amplitude=.018,
    strand_y_fine_wave=.011,
    rib_radius_model=.017, axial_rib_radius_model=.022, rib_sections=12,
    grip_knob_flutes=12, grip_flute_depth_fraction=.055,
    ellipsoid_radii_model=[.98, .82, .42],
    source_hypotheses=(
        'flattened-envelope inferred from a perspective photo, not measured CAD',
        'mostly parallel serpentine surface strands in place of strict radial spokes',
        'separate 11 horizontal rib pieces plus one axial rib, exact union pending',
        'fluted cylindrical hand grip in place of spherical button',
        '79 strand count inherited from reconstructed v6, not documented author geometry'),
    expected_physics='UNTESTED',
    active_boolean_solver='CHERCHI_ONLY_AFTER_EXACT_INPUT_ADMISSION',
    independent_boolean_reference='CGAL',
)


def centerline(index: int) -> np.ndarray:
    r = old.tube_layout()[index]
    u = np.linspace(0., 1., SPEC['tube_samples'])
    s = 2*u-1
    phase = SPEC['tube_wave_phase_increment'] * index
    x = s * r['half_length_model']
    y0 = r['y_model']
    y = (y0 * (SPEC['centerline_y_preservation'] +
            (1-SPEC['centerline_y_preservation'])*s*s) +
         SPEC['strand_y_weave_amplitude']*np.sin(2*np.pi*u + phase)*np.sin(np.pi*u) +
         SPEC['strand_y_fine_wave']*np.sin(6*np.pi*u + .17*index)*np.sin(np.pi*u))
    z = (SPEC['ellipsoid_center_model'][2] + SPEC['z_flatten_scale']*(r['z_model']-SPEC['ellipsoid_center_model'][2]) +
         SPEC['strand_z_weave_amplitude']*np.sin(4*np.pi*u + .29*index)*np.sin(np.pi*u))
    return np.column_stack((x, y, z))


def rib_centerlines() -> dict[str, np.ndarray]:
    """Two straight, round-cap rib families; robust per-part geometry.

    Each tube center at x=0 is within its tube radius of the rib centerline
    assigned by the original z-row. Eleven y-direction ribs cross one z rib.
    This is a *geometric reachability hypothesis*, not a proof of the final
    Boolean-united solid's connectedness or printability.
    """
    rows=old.tube_layout()
    levels=sorted(set(round(row['z_model'],12) for row in rows))
    out={}
    for k,z_orig in enumerate(levels):
        members=[i for i,row in enumerate(rows) if abs(row['z_model']-z_orig)<1e-9]
        centers=np.asarray([centerline(i)[len(centerline(i))//2] for i in members])
        lowest=float(centers[:,1].min())-.026
        highest=float(centers[:,1].max())+.026
        z=SPEC['ellipsoid_center_model'][2]+SPEC['z_flatten_scale']*(z_orig-SPEC['ellipsoid_center_model'][2])
        out[f'rib-row-{k:02d}-fixed']=np.column_stack((np.zeros(17),np.linspace(lowest,highest,17),np.full(17,z)))
    zlo=SPEC['ellipsoid_center_model'][2]+SPEC['z_flatten_scale']*(levels[0]-SPEC['ellipsoid_center_model'][2])
    zhi=SPEC['ellipsoid_center_model'][2]+SPEC['z_flatten_scale']*(levels[-1]-SPEC['ellipsoid_center_model'][2])
    out['rib-axial-fixed']=np.column_stack((np.zeros(45),np.zeros(45),np.linspace(zlo-.025,zhi+.025,45)))
    return out


def fluted_grip_pin() -> trimesh.Trimesh:
    # Keep the same bottom tip and shaft, replace only unverified upper grip.
    profile=[(0.,-.16),(.015,-.151),(.025,-.137),(.034,-.088),(.045,-.038),
             (.045,1.580),(.075,1.580),(.089,1.603),(.094,1.622),
             (.094,1.800),(.088,1.825),(.074,1.842),(.0,1.842)]
    m=trimesh.creation.revolve(np.asarray(profile,float),sections=48)
    verts=np.asarray(m.vertices).copy()
    z=verts[:,2];ang=np.arctan2(verts[:,1],verts[:,0]);radius=np.linalg.norm(verts[:,:2],axis=1)
    mask=(z>1.59)&(z<1.835)&(radius>.07)
    radial_scale=1.+SPEC['grip_flute_depth_fraction']*np.cos(SPEC['grip_knob_flutes']*ang)
    verts[mask,:2]*=radial_scale[mask,None]
    m.vertices=verts
    if m.volume<0:m.invert()
    return m


def components():
    # Use original source tessellation but the new shape envelope; do not keep
    # an inner ellipsoid or permanent outer shell as fixed material.
    sphere=trimesh.creation.icosphere(subdivisions=SPEC['ellipsoid_subdivisions'])
    sphere.vertices=sphere.vertices*np.asarray(SPEC['ellipsoid_radii_model'])+np.asarray(SPEC['ellipsoid_center_model'])
    hub=trimesh.creation.cylinder(radius=SPEC['hub_radius_model'],
             height=np.diff(SPEC['hub_interval_model'])[0],sections=24)
    hub.apply_translation([0,0,np.mean(SPEC['hub_interval_model'])])
    parts={'outer-ellipsoid':sphere,'hub-fixed':hub,'pin-fixed':fluted_grip_pin()}
    for i in range(len(old.tube_layout())):
        parts[f'tube-{i:03d}-fixed']=old.base.rounded_tube(centerline(i),SPEC['tube_radius_model'],SPEC['tube_sections'])
    for name,points in rib_centerlines().items():
        radius=SPEC['axial_rib_radius_model'] if name=='rib-axial-fixed' else SPEC['rib_radius_model']
        parts[name]=old.base.rounded_tube(points,radius,SPEC['rib_sections'])
    return parts


def construction_recipe():
    return dict(fixed_parts=['hub-fixed','pin-fixed'] + list(rib_centerlines()) +
                [f'tube-{i:03d}-fixed' for i in range(len(old.tube_layout()))],
                design_envelope='outer-ellipsoid',
                fixed='EXACT_UNION(ALL fixed_parts)',
                variable='EXACT_DIFFERENCE(outer-ellipsoid, fixed)',
                initial='EXACT_UNION(outer-ellipsoid, fixed)',
                permanent_ellipsoid_shell=False,
                optimized_material='NOT_COMPUTED')


def prepare(folder, *, model_and_si=True):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=False)
    parts=components();entries={}
    for name,m in parts.items():
        a=mesh_audit(m)
        if not (a['closed'] and a['winding_consistent'] and a['components']==1 and
                a['signed_volume_model3']>0 and a['minimum_triangle_area_model2']>0):
            raise ValueError(f'INVALID_SOURCE_PART: {name}: {a}')
        path=folder/(name+'-model.obj');write_obj(path,m)
        entry=dict(model_obj=path.name,sha256_model=hashlib.sha256(path.read_bytes()).hexdigest(), audit=a)
        if model_and_si:
            si=m.copy();si.vertices*=SPEC['model_unit_m'];si_path=folder/(name+'-si.obj');write_obj(si_path,si)
            entry.update(si_obj=si_path.name,sha256_si=hashlib.sha256(si_path.read_bytes()).hexdigest())
        entries[name]=entry
    manifest=dict(spec=SPEC,parts=entries,construction=construction_recipe(),
           status='SOURCE_PARTS_ONLY_EXACT_BOOLEAN_AND_SOLVER_NOT_RUN',
           source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           optimization_invocations=0,simulation_invocations=0,
           note='Paper-photo-inspired reconstruction, not author CAD and not optimized result')
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False))
    return manifest

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True)
    ar=ap.parse_args();prepare(ar.output)

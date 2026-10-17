"""Independent input/planar/moment/OBJ regression for protected Flower v4.

Checks binary64 planar geometry and exported mesh identity only. It does not
replace full exact 3D positive-volume pair audit or a physics simulation.
"""
import json,math,hashlib
from pathlib import Path
from shapely.geometry import Polygon,LineString
import trimesh
from paper_flower_fixture import build_fixture as original_fixture
from paper_flower_output import profile_geometry

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def check(base,source):
    base,source=Path(base),Path(source)
    R=base/'results';inputdir=R/'frozen-input-v4'
    record=json.loads((inputdir/'input.json').read_text())
    doc=json.loads((inputdir/'flower-cases.json').read_text())
    case=doc['cases'][0]
    assert record['case_id']==case['id']
    assert record['middle_guard_policy']=='CENTER_AND_OUTER_RIM_FROZEN_BEFORE_OPTIMIZATION_NOT_POSTSOLVE_PATCH'
    original=Polygon(record['retained_original_loops'][0],record['retained_original_loops'][1:])
    design=profile_geometry(case['planar_problem']['design_region_loops'])
    fixed_layer=next(layer for layer in record['layers'] if layer['id']=='fixed-middle-boundary-rim')
    guard=profile_geometry(fixed_layer['loops'])
    assert original.is_valid and design.is_valid and guard.is_valid
    checks={}
    def ok(key,value):
        checks[key]=bool(value)
        if not checks[key]:raise ValueError('FAILED '+key)
    ok('source_has_48_holes',len(original.interiors)==48)
    ok('design_has_48_holes',design.geom_type=='Polygon' and len(design.interiors)==48)
    ok('original_equals_design_plus_fixed_rims_planar',original.symmetric_difference(design.union(guard)).area==0)
    ok('design_and_guard_no_area_overlap',design.intersection(guard).area==0)
    bore=Polygon(record['retained_original_loops'][record['bearing_loop_index']])
    width=record['middle_guard_width_model_units']
    outer_width=record['outer_guard_width_model']
    center_ref=original.intersection(bore.buffer(width,join_style=2))
    outer_ref=original.intersection(LineString(original.exterior.coords).buffer(outer_width,join_style=2))
    ok('center_guard_whole_band_preserved_in_fixed_material',center_ref.difference(guard).area==0)
    ok('outer_guard_whole_band_preserved_in_fixed_material',outer_ref.difference(guard).area==0)
    ok('decorative_hole_boundaries_not_all_fixed',len(guard.geoms)==2)
    ok('fixed_layer_density_positive',fixed_layer['volume_density']==1. and fixed_layer['z_interval']==[-.06,.06])
    app=json.loads((R/'v4-flower-main.json').read_text());repeat=json.loads((R/'v4-flower-repeat.json').read_text())
    attempts=app['cases'][0]['attempts']
    ok('two_seeds_qualified',len(attempts)==2 and all(a['status']=='CONVERGED' and a['numerical_acceptance']['passed'] and a['normalized_equation_residual']<=1e-10 for a in attempts))
    ok('independent_repeat_scientific_equal',app['scientific_hash']==repeat['scientific_hash'] and all(a['solver_result']==b['solver_result'] and a['evaluation_ledger']==b['evaluation_ledger'] for a,b in zip(attempts,repeat['cases'][0]['attempts'])))
    selected=next(a for a in attempts if a['seed']==1)
    sol=selected['solver_result'];cx,cy=sol['center'];rad=sol['radius']
    # This is a DISCRETE preview circle, not the exact analytic arc authority.
    cutter=Polygon([(cx+rad*math.cos(2*math.pi*k/4096),cy+rad*math.sin(2*math.pi*k/4096)) for k in range(4096)])
    cuttable=design.intersection(cutter)
    ok('cavity_cannot_include_fixed_center_guard',cuttable.intersection(center_ref).area==0)
    ok('cavity_cannot_include_fixed_outer_guard',cuttable.intersection(outer_ref).area==0)
    ok('cuttable_material_nonempty',cuttable.area>0)
    export=json.loads((R/'flower-v4-optimized-seed1/output-preparation.json').read_text())
    ok('export_from_selected_seed1',export['selected_seed']==1 and export['circle_center']==sol['center'] and export['circle_radius']==sol['radius'])
    ok('export_moment_gate_pass',export['moment_gate_pass'] and max(export['independent_triangle_moment_error'])<1e-6)
    ok('source_matched',export['input_sha256']==sha(inputdir/'input.json'))
    ok('export_remains_pending_independent_exact_solid_gate',export['full_material_gate']=='PENDING_EXACT_REGION_AUDIT')
    for name,entry in export['files'].items():
        path=R/'flower-v4-optimized-seed1'/entry['file']
        ok('mesh_legal_'+name,path.is_file() and sha(path)==entry['sha256'] and entry['watertight'] and entry['winding_consistent'] and entry['positive_volume'] and entry['exact_zero_area_face_count']==0)
    assembly=json.loads((R/'flower-v4-assembly-protected/assembly-check.json').read_text())
    for name,entry in assembly['assembly_files'].items():
        path=R/'flower-v4-assembly-protected'/name
        ok('assembly_reload_'+name,path.is_file() and sha(path)==entry['sha256'] and entry['coordinates_and_faces_unchanged'] and entry['watertight_components'])
    ok('middle_visual_has_protected_rims',assembly['assembly_files']['flower-middle-protected.obj']['parts']==['retained','fixed-middle-boundary-rim'])
    ok('rotor_contains_fixed_rim', 'fixed-middle-boundary-rim' in assembly['assembly_files']['flower-rotor-protected.obj']['parts'])
    before=export['original'];after=export['optimized'];derived=export['derived_optimized']
    dx=math.hypot(*before['center_m'][:2]);dy=math.hypot(*after['center_m'][:2]);dd=math.hypot(*derived['center_m'][:2]);
    ok('analytical_com_improved',dy<dx)
    ok('exported_com_improved',dd<dx)
    report=dict(schema='protected-flower-v4-independent-lightweight-check-v1',checks=checks,
                passed_count=sum(checks.values()),passed=all(checks.values()),
                residuals={str(a['seed']):a['normalized_equation_residual'] for a in attempts},
                masses_g={'before':1000*before['mass_kg'],'after_analytic':1000*after['mass_kg'],'after_mesh':1000*derived['mass_kg']},
                mass_change_percent=100*(after['mass_kg']/before['mass_kg']-1),
                com_eccentricity_mm={'before':1000*dx,'after_analytic':1000*dy,'after_mesh':1000*dd},
                fixed_rim_model_area=guard.area,center_rim_model_area=center_ref.area,outer_rim_model_area=outer_ref.area,
                physical_strength_certified=False,full_exact_3d_material_partition_certified=False,
                dynamics_rerun=False,original_author_CAD=False,
                scope='SHAPELY_PLANAR_EXACT_INPUT_POLYGON_COORDS_AND_MESH_RELOAD_NOT_3D_EXACT_PARTITION')
    (R/'protected-flower-v4-lightweight-audit.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    return report

if __name__=='__main__':
    B=Path('/mnt/data/Spin_flower_center_guard_20261017')
    source=Path('/mnt/data/Spin_flower_rebuild_20261017/source/project/experiments/quadric_physics_demo_20261011/paper-outline-flower-preview-v3')
    r=check(B,source)
    print(json.dumps({k:r[k] for k in ['passed','passed_count','mass_change_percent','masses_g','com_eccentricity_mm']},indent=2))

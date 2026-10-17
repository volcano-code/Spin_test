"""Flower v4: protect bearing-bore *middle* support annulus before optimizing.

This is an INPUT-CONSTRAINT revision, not a modification of the planar Dogleg
solver or a post hoc overlay of material on a previously optimized shape.
The width is a registered engineering parameter of the reconstructed fixture,
not a value claimed to be the authors' original CAD dimension.
"""
from pathlib import Path
import hashlib
import json
from fractions import Fraction as F
import sys
from shapely.geometry import Polygon, LineString
from paper_flower_fixture_v2 import freeze as _legacy_freeze  # not called; retained for context
from paper_flower_fixture import (build_fixture as build_legacy_fixture,
    boundary_loops, exact_extrusion_moments, polygons)

# Explicit, reproducible reconstructed engineering assumption:
# 0.04 model units * 0.020 metres per model unit = 0.8 mm radial support.
CENTER_GUARD_WIDTH_MODEL = 0.04
OUTER_GUARD_WIDTH_MODEL = 0.015


def build_fixture(source):
    problem, record, geometry = build_legacy_fixture(source)
    original = geometry['original']
    bore = Polygon(record['retained_original_loops'][record['bearing_loop_index']])
    center_guard = original.intersection(bore.buffer(CENTER_GUARD_WIDTH_MODEL, join_style=2))
    outer_guard = original.intersection(LineString(original.exterior.coords).buffer(
        OUTER_GUARD_WIDTH_MODEL, join_style=2))
    guard = center_guard.union(outer_guard)
    if center_guard.intersection(outer_guard).area > 1e-12:
        raise ValueError("FIXED_CENTER_AND_OUTER_BANDS_OVERLAP")
    design = original.difference(guard)
    if any(not g.is_valid or g.is_empty for g in (guard,design)):
        raise ValueError('INVALID_PROTECTED_CENTER_GUARD_OR_DESIGN')
    if len(polygons(guard))!=2 or len(polygons(design))!=1:
        raise ValueError('CENTRAL_GUARD_SPLITS_MIDDLE_OR_DISCONNECTS_DESIGN')
    if len(polygons(design)[0].interiors)!=48:
        raise ValueError('CENTRAL_GUARD_CHANGED_48_SOURCE_HOLES')
    overlap=design.intersection(guard).area
    mismatch=original.symmetric_difference(design.union(guard)).area
    if overlap>1e-12 or mismatch>1e-12 or guard.area<=0:
        raise ValueError('CENTER_GUARD_MIDDLE_PARTITION_FAILED')
    # Keep exactly the legacy component identities for the exporter;
    # protect ONLY material in the bore-neighborhood, not every flower hole.
    guard_layer=dict(id='fixed-middle-boundary-rim',
        loops=boundary_loops(guard),z_interval=[-.06,.06],volume_density=1.)
    layers=[]
    for layer in record['layers']:
        if layer['id']=='fixed-middle-boundary-rim':
            layers.append(guard_layer)
        else:
            layers.append(layer)
    if [x['id'] for x in layers]!=['bottom','top','fixed-middle-boundary-rim','bearing-seat','outer-race']:
        raise ValueError('UNEXPECTED_FIXED_LAYER_IDENTITIES')
    problem.update(design_region_loops=boundary_loops(design),
        fixed_extrusion_layers=[{k:v for k,v in layer.items() if k!='id'} for layer in layers])
    fixed=[F(0)]*10
    for layer in layers:
        fixed=[a+b for a,b in zip(fixed,exact_extrusion_moments(layer))]
    record.update(schema='paper-flower-method-input-v3-center-guard',
        case_id='paper-image-derived-flower-two-guard-rims-v4',
        rim_width=CENTER_GUARD_WIDTH_MODEL,
        outer_guard_width_model=OUTER_GUARD_WIDTH_MODEL,
        outer_guard_width_mm=OUTER_GUARD_WIDTH_MODEL*record['meters_per_model_unit']*1000,
        rim_rule='FIXED_CENTRAL_BORE_AND_OUTER_PERIMETER; interior decorative holes editable',
        middle_guard_width_model_units=CENTER_GUARD_WIDTH_MODEL,
        middle_guard_width_mm=CENTER_GUARD_WIDTH_MODEL*record['meters_per_model_unit']*1000,
        middle_guard_policy='CENTER_AND_OUTER_RIM_FROZEN_BEFORE_OPTIMIZATION_NOT_POSTSOLVE_PATCH',
        input_revision_reason='preserve paper-described central bearing ring and outer rim; optimize remainder using exact fixed moments',
        layers=layers,
        fixed_exact_rational_moments=[str(x) for x in fixed],
        fixed_model_mass_moments=[float(x) for x in fixed],
        mechanical_strength_status='NOT_VERIFIED')
    geometry.update(design=design,fixed_middle=guard)
    record['admission'].update(design_component_count=1,design_area=design.area,
        fixed_middle_area=guard.area,
        design_rim_overlap_area=overlap,
        middle_partition_symmetric_difference_area=mismatch,
        middle_boundary_policy='CENTRAL_BORE_FIXED_GUARD_DESIGN_MEETS_REST_OF_SOURCE_BOUNDARIES',
        middle_guard_around_center_only=False,
        center_guard_area=center_guard.area,outer_guard_area=outer_guard.area)
    return problem,record,geometry


def freeze(source,out):
    """Write versioned, input-only manifest with independent partition checks.

    Do not construct an optimized circle or load an old optimizer result.
    """
    source,out=Path(source),Path(out)
    problem,record,geometry=build_fixture(source)
    out.mkdir(parents=True,exist_ok=False)
    manifest=dict(schema='faster-planar-method-fixture-v1',
        scope='RECONSTRUCTED_METHOD_VALIDATION',
        cases=[dict(id=record['case_id'],mode='FIDGET_SPINNER',
                    asset_class='RECONSTRUCTED',planar_problem=problem)])
    for filename, data in (('flower-cases.json',manifest),('input.json',record)):
        (out/filename).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
    (out/'input-sha256.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.json'))},indent=2)+'\n')
    print(json.dumps({k:record['admission'][k] for k in ('design_area','fixed_middle_area','design_rim_overlap_area','middle_partition_symmetric_difference_area')},indent=2))
    return record

if __name__=='__main__':
    import argparse
    a=argparse.ArgumentParser()
    a.add_argument('--source',type=Path,required=True)
    a.add_argument('--output',type=Path,required=True)
    x=a.parse_args()
    freeze(x.source,x.output)

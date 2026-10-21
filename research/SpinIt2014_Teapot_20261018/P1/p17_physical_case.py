#!/usr/bin/env python3
"""Physical moments of reread meshes under one explicit P13 case proposal.

The integrals are exact for saved binary64 vertices, not for Cherchi's
implicit intersection points. A closed-edge audit and positive inertia do
not establish region equality, printability, or W0/W2 scientific admission.
No geometry, mass, center of mass, or inertia tensor is edited here.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
from numbers import Integral, Real
from pathlib import Path
from typing import Mapping

import numpy as np

from p16_exact_binary64_chain import NAMES, exact_ten, read_obj_binary64


SCHEMA = 'W4P17UnifiedPhysicalCaseProposalV1'
EXPONENTS = (3, 4, 4, 4, 5, 5, 5, 5, 5, 5)
DENIED_FLAGS = (
    'W0_physical_tip_or_FD_approved', 'W2_teacher_training_allowed',
    'native_implicit_point_exact_identity_certified',
    'full_boolean_region_equality_certified', 'printability_certified',
    'Faster_optimization_executed', 'MuJoCo_real_optimized_before_after_executed',
)


def p13_case_config() -> dict:
    """The sole frozen physical proposal; these are reconstruction assumptions."""
    return dict(
        schema='W4P17P13PhysicalConfigurationV1',
        case_id='P13_RECONSTRUCTED_REFERENCE_UNIFORM_SOLID_PROPOSAL',
        scale_m_per_unit=0.025, density_kg_m3=1200.0,
        coordinate_frame='P13_REFERENCE_ALREADY_Z_UP',
        spin_axis_reference=[0.0, 0.0, 1.0], tip_reference=[0.0, 0.0, 0.0],
        density_model='ASSUMED_UNIFORM_SOLID_NOT_PRINTED_MATERIAL_CERTIFICATE',
        source_parameter_document='P13_REFERENCE_SHAFT_AND_DESIGN_GATE.md',
        **{name: False for name in DENIED_FLAGS},
    )


def _positive_scalar(value, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(name + '_MUST_BE_FINITE_POSITIVE_REAL')
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(name + '_MUST_BE_FINITE_POSITIVE_REAL')
    return value


def _finite_float(value) -> float:
    try:
        answer = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError('PHYSICAL_FLOAT_PROJECTION_NOT_FINITE') from exc
    if not math.isfinite(answer):
        raise ValueError('PHYSICAL_FLOAT_PROJECTION_NOT_FINITE')
    return answer


def _fraction_payload(value: Fraction) -> dict:
    return dict(numerator=str(value.numerator), denominator=str(value.denominator))


def _validate_mesh(vertices, faces):
    try:
        vv = np.asarray(vertices, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError('MESH_VERTICES_INVALID') from exc
    if vv.ndim != 2 or vv.shape[1:] != (3,) or len(vv) < 4:
        raise ValueError('MESH_VERTEX_SHAPE_INVALID')
    if not np.all(np.isfinite(vv)):
        raise ValueError('MESH_NONFINITE_VERTEX')
    face_rows = list(faces)
    if not face_rows:
        raise ValueError('MESH_EMPTY_FACES')
    ff = []
    edge_uses = defaultdict(list)
    for row in face_rows:
        if len(row) != 3 or any(isinstance(i, (bool, np.bool_)) or
                                not isinstance(i, Integral) for i in row):
            raise ValueError('MESH_FACE_MUST_HAVE_THREE_INTEGER_INDICES')
        face = tuple(int(i) for i in row)
        if len(set(face)) != 3 or min(face) < 0 or max(face) >= len(vv):
            raise ValueError('MESH_FACE_INDEX_INVALID')
        ff.append(face)
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edge_uses[tuple(sorted((a, b)))].append((a, b))
    if any(len(uses) != 2 for uses in edge_uses.values()):
        raise ValueError('MESH_EDGE_BOUNDARY_OR_NONMANIFOLD')
    if any(uses[0] != uses[1][::-1] for uses in edge_uses.values()):
        raise ValueError('MESH_INCONSISTENT_FACE_ORIENTATION')
    return [tuple(float(x) for x in row) for row in vv], ff


def analyze_mesh(vertices, faces, *, scale_m_per_unit, density_kg_m3) -> dict:
    """Integrate ordinary r10 and SI inertia; all physical parameters explicit.

    Coordinates must already be in the intended reference frame. The function
    only scales lengths: it never applies an additional P13 .4 scaling, Y-up
    rotation, or translation. QYZ/QXZ/QXY are ordinary undoubled integrals.
    """
    scale = _positive_scalar(scale_m_per_unit, 'SCALE')
    density = _positive_scalar(density_kg_m3, 'DENSITY')
    vv, ff = _validate_mesh(vertices, faces)
    raw = exact_ten(vv, ff)
    if raw[0] <= 0:
        raise ValueError('MESH_SIGNED_VOLUME_MUST_BE_POSITIVE')
    s, rho = Fraction.from_float(scale), Fraction.from_float(density)
    si = tuple(value * rho * s ** power for value, power in zip(raw, EXPONENTS))
    mass = si[0]
    center = tuple(value / mass for value in si[1:4])
    second = ((si[4], si[9], si[8]),
              (si[9], si[5], si[7]),
              (si[8], si[7], si[6]))
    central_second = tuple(tuple(second[i][j] - mass * center[i] * center[j]
                                 for j in range(3)) for i in range(3))

    def inertia(q):
        trace = sum(q[i][i] for i in range(3))
        return tuple(tuple((trace if i == j else Fraction(0)) - q[i][j]
                           for j in range(3)) for i in range(3))

    origin_inertia, center_inertia = inertia(second), inertia(central_second)
    origin_float = [[_finite_float(x) for x in row] for row in origin_inertia]
    center_float = [[_finite_float(x) for x in row] for row in center_inertia]
    mass_float = _finite_float(mass)
    eigenvalues = np.linalg.eigvalsh(np.asarray(center_float, dtype=np.float64))
    if mass_float <= 0 or not np.all(np.isfinite(eigenvalues)) or np.min(eigenvalues) <= 0:
        raise ValueError('PHYSICAL_MASS_OR_INERTIA_NOT_POSITIVE_REPRESENTABLE')
    bounds = np.stack((np.min(vv, axis=0), np.max(vv, axis=0))) * scale
    if not np.all(np.isfinite(bounds)):
        raise ValueError('PHYSICAL_BOUNDS_NOT_FINITE')
    return dict(
        schema='W4P17SavedMeshPhysicalMomentsV1',
        status='DIAGNOSTIC_PHYSICAL_MOMENTS_ONLY_NOT_APPROVED',
        arithmetic='EXACT_FRACTION_OF_SAVED_BINARY64_VERTICES_AND_EXPLICIT_SI_PARAMETERS',
        source_coordinates_are_native_implicit_rationals=False,
        moment_order=list(NAMES), cross_moment_convention='ORDINARY_UNDOUBLED',
        scale_m_per_unit=scale, density_kg_m3=density,
        source_raw_ten=[_finite_float(value) for value in raw],
        source_raw_ten_exact=[_fraction_payload(value) for value in raw],
        si_raw_ten=[_finite_float(value) for value in si],
        si_raw_ten_exact=[_fraction_payload(value) for value in si],
        si_moment_units=['kg'] + ['kg*m'] * 3 + ['kg*m^2'] * 6,
        mass_kg=mass_float, center_of_mass_m=[_finite_float(x) for x in center],
        full_inertia_origin_kg_m2=origin_float,
        full_inertia_com_kg_m2=center_float,
        principal_inertia_kg_m2=eigenvalues.tolist(),
        bounds_m=bounds.tolist(), vertex_count=len(vv), triangle_count=len(ff),
        closed_consistently_oriented_edge_audit=True,
        closed_edge_audit_is_not_full_solid_region_certificate=True,
        **{name: False for name in DENIED_FLAGS},
    )


def analyze_obj(path, *, scale_m_per_unit, density_kg_m3,
                expected_sha256: str | None = None) -> dict:
    """Reread the saved OBJ without welding; optionally enforce a frozen hash."""
    path = Path(path)
    before = path.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    if expected_sha256 is not None and digest != expected_sha256:
        raise ValueError('FROZEN_OBJ_SHA256_MISMATCH')
    vertices, faces = read_obj_binary64(path)
    if path.read_bytes() != before:
        raise ValueError('OBJ_CHANGED_DURING_REREAD')
    result = analyze_mesh(vertices, faces, scale_m_per_unit=scale_m_per_unit,
                          density_kg_m3=density_kg_m3)
    result.update(source_file_name=path.name, source_obj_sha256=digest,
                  frozen_input_sha256_verified=expected_sha256 is not None)
    return result


def build_physical_proposal(mesh_paths: Mapping, *, case_config: Mapping,
                            expected_sha256: Mapping) -> dict:
    """Build a consistent table using the frozen P13 proposal and pinned OBJs.

    This does not sum overlapping M and shaft meshes and does not infer F/D
    set equality from moment additivity. W0 authorization cannot be supplied
    through this proposal builder.
    """
    expected_config = p13_case_config()
    if set(case_config) != set(expected_config):
        raise ValueError('PHYSICAL_CASE_CONFIG_KEYS_CHANGED')
    if any(case_config.get(flag) is not False for flag in DENIED_FLAGS):
        raise ValueError('PHYSICAL_CASE_PREMATURE_APPROVAL')
    if json.dumps(dict(case_config),sort_keys=True,allow_nan=False) != json.dumps(expected_config,sort_keys=True,allow_nan=False):
        raise ValueError('PHYSICAL_CASE_NOT_FROZEN_P13_PROPOSAL')
    if not mesh_paths or set(mesh_paths) != set(expected_sha256):
        raise ValueError('MESH_AND_FROZEN_HASH_NAMES_MISMATCH')
    if any(not isinstance(name, str) or not name for name in mesh_paths):
        raise ValueError('MESH_NAME_INVALID')
    if any(not isinstance(value, str) or len(value) != 64 or
           any(c not in '0123456789abcdef' for c in value)
           for value in expected_sha256.values()):
        raise ValueError('FROZEN_OBJ_SHA256_INVALID')
    results = {name: analyze_obj(path, scale_m_per_unit=case_config['scale_m_per_unit'],
                                density_kg_m3=case_config['density_kg_m3'],
                                expected_sha256=expected_sha256[name])
               for name, path in mesh_paths.items()}
    table = [dict(material=name, source_obj_sha256=item['source_obj_sha256'],
                  mass_kg=item['mass_kg'], center_of_mass_m=item['center_of_mass_m'],
                  full_inertia_com_kg_m2=item['full_inertia_com_kg_m2'],
                  principal_inertia_kg_m2=item['principal_inertia_kg_m2'])
             for name, item in results.items()]
    report = dict(schema=SCHEMA, status='P13_UNIFIED_PHYSICAL_CASE_PROPOSAL_NOT_W0_APPROVED',
                  case_config=expected_config, materials=results, physical_table=table,
                  spin_axis_reference=expected_config['spin_axis_reference'],
                  tip_m=[0.0, 0.0, 0.0],
                  overlapping_material_masses_not_summed=True,
                  geometry_or_inertial_parameters_modified=False,
                  old_P12_15cm_or_0_25kg_case_not_used=True,
                  **{name: False for name in DENIED_FLAGS})
    json.dumps(report, allow_nan=False)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh', action='append', required=True, metavar='NAME=OBJ')
    parser.add_argument('--sha256', action='append', required=True, metavar='NAME=SHA256')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()

    def pairs(values):
        output = {}
        for value in values:
            name, sep, item = value.partition('=')
            if not sep or name in output:
                raise ValueError('CLI_DUPLICATE_OR_INVALID_NAMED_INPUT')
            output[name] = item
        return output

    report = build_physical_proposal(pairs(args.mesh), case_config=p13_case_config(),
                                     expected_sha256=pairs(args.sha256))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    if args.out.exists():
        raise FileExistsError('P17_PHYSICAL_REPORT_OUTPUT_ALREADY_EXISTS')
    args.out.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print(json.dumps(dict(status=report['status'], physical_table=report['physical_table']), indent=2))


if __name__ == '__main__':
    main()

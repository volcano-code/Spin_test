#!/usr/bin/env python3
"""Exact P20 reference-unit, moment and coefficient contracts.

This module does not load a native extension or issue an evaluation.  It keeps
the P19 saved binary64 geometry in its existing Z-up reference coordinates.
One reference length is the *binary64 value* .025 metres; one reference mass
is exactly 1200 times that length cubed kilograms.  The locked problem can
therefore use density 1.0 without rounding 1200*s**3 into a second float.

The actual core's coefficient convention is NATIVE_MATRIX_ENTRY_P: the last
three coefficients multiply 2yz, 2xz, 2xy.  The raw moment cross terms are
ordinary undoubled yz, xz, xy.  No helper silently normalizes a coefficient
vector, identifies positive multiples for derivative purposes, or grants a
native material, derivative, optimization, training or physical approval.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from numbers import Integral, Real
from pathlib import Path
from typing import Mapping


SCHEMA = 'W4P20ExactPhysicalContractV1'
CORE_COMMIT = '58fd12c1306c1c01679a19172e276eef0cb30542'
RAW10_ORDER = ('M', 'LX', 'LY', 'LZ', 'QXX', 'QYY', 'QZZ', 'QYZ', 'QXZ', 'QXY')
RAW10_DEGREES = (0, 1, 1, 1, 2, 2, 2, 2, 2, 2)
NATIVE_BASIS = 'NATIVE_MATRIX_ENTRY_P'
LITERAL_BASIS = 'LITERAL_MONOMIAL_COEFFICIENTS'
REFERENCE_FRAME = 'P19_REFERENCE_ALREADY_Z_UP'
TARGET_FRAME = 'INPUT_NORMALIZED_TARGET_V1'
SI_FRAME = 'P19_PROPOSED_SI_Z_UP'
LENGTH_UNIT = 'P19_REFERENCE_LENGTH_UNIT'
MASS_UNIT = 'P19_REFERENCE_MASS_UNIT'
SCALE_M_PER_REFERENCE = Fraction.from_float(0.025)
DENSITY_KG_M3 = Fraction(1200)
MASS_KG_PER_REFERENCE = DENSITY_KG_M3 * SCALE_M_PER_REFERENCE**3
P19_MANIFEST_SHA256 = 'c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6'
P19_REPORT_SHA256 = 'f30fabc8ce348b9b8f42ff20649e683557349582ef31baf6c05d35e17b448601'
P19_MATERIAL_SHA256 = {
    'M': '0b59fd6f41079ab507af3e31673f94472b0d6f849df981b52c1ea667994ad704',
    'F': '5c5db73792bd8d6566a954e6d0eef6d22e248a7ad2f8a7a8d8e6d4f2ad9d86a8',
    'D': 'd64a3163c886cb06ade6f366e8ff5e475934816343a5be429b55c5832951b073',
    'S': '65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0',
}
CORE_SOURCE_SHA256 = {
    'python/make_it_stand/spin.py': 'c4aa751027617d3e7a95631c27c2bd2105ab25917b94f848dc6da42ff633913f',
    'python/make_it_stand/verification/spin_problem.py': 'adcd25778d21b82285cba9e6596a523ccffa41ffc6f84f159e5b98bbd9b0d022',
    'python/make_it_stand/verification/spin_common.py': '37c7ad42f70da68a5cea25da46f143371bfa3d078e8279103479dc64186b5cb9',
    'python/make_it_stand/verification/faster_material.py': 'b048434b1c4812c21d61844b68b9710fff71c105a9a86cb27a765f771d185c86',
    'python/make_it_stand/verification/cherchi_inprocess.py': '6cdd03ad9bd1c55f2c40c72ac77c5cd3bc822bd8fb609bdd92cf2cf45162fa37',
    'include/physics/RawMassMoments10.h': '43c734ed351be7df01c150487e22e07b5b6c5535bd1ca3b62c61d157434b2aec',
    'include/spin/QuadricCoefficients.h': 'd08fb7d20a86501b637ee38c80e0f50a30d9193b01dcba2cb4e8e30581af7c3b',
    'src/spin/QuadricCoefficients.cpp': 'd3ea749a0207e0c53ffd770e2f0cb8d051538efd8b66608236dbd2c752ae1365',
    'src/spin/DualMonomialCoordinates.cpp': '8af08a341bfc24cecdd94218fdafe4d31fec7d64672c3b03de53f2c719739ae7',
    'bindings/pybind_module.cpp': '48018801aaa22fb41e32181994d2f9713c9d328908e4546ca718ce24671428a5',
}
DENIED_FLAGS = (
    'W0_physical_tip_or_FD_approved', 'W2_teacher_training_allowed',
    'native_M6_material_partition_certified', 'native_implicit_identity_certified',
    'derivative_identity_certified', 'stable_derivative_neighborhood_certified',
    'optimization_admitted', 'training_admitted', 'physical_material_validated',
    'printability_certified', 'MuJoCo_real_optimized_before_after_executed',
)


def scientific_flags() -> dict:
    return {name: False for name in DENIED_FLAGS}


def _fraction(value, name='number') -> Fraction:
    if isinstance(value, bool):
        raise ValueError(name + ': boolean is not a numeric value')
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Integral):
        return Fraction(int(value))
    if isinstance(value, Real):
        if hasattr(value, 'dtype') and value.dtype.itemsize > 8:
            raise ValueError(name + ': precision beyond binary64 is unsupported')
        number = float(value)
        if math.isfinite(number):
            return Fraction.from_float(number)
    raise ValueError(name + ': expected an exact Fraction, integer or finite binary64 real')


def _binary64(value, name='number') -> float:
    if isinstance(value, Fraction):
        raise ValueError(name + ': actual core input must be binary64, not an unprojected Fraction')
    exact = _fraction(value, name)
    try:
        rounded = float(exact)
    except OverflowError as exc:
        raise ValueError(name + ': binary64 overflow') from exc
    if not math.isfinite(rounded) or Fraction.from_float(rounded) != exact:
        raise ValueError(name + ': lossy binary64 input conversion')
    return float(value)


def _vector(values, size, name='vector') -> tuple:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(name + ': expected a numeric sequence')
    try:
        rows = tuple(values)
    except TypeError as exc:
        raise ValueError(name + ': expected a numeric sequence') from exc
    if len(rows) != size:
        raise ValueError(name + ': incorrect dimension')
    return tuple(_fraction(x, name) for x in rows)


def _matrix(values, size, name='matrix') -> tuple:
    if isinstance(values, (str, bytes, Mapping)):
        raise ValueError(name + ': expected a square numeric matrix')
    rows = tuple(values)
    if len(rows) != size:
        raise ValueError(name + ': incorrect dimension')
    return tuple(_vector(row, size, name) for row in rows)


def _identity(size=3):
    return tuple(tuple(Fraction(int(i == j)) for j in range(size)) for i in range(size))


def _transpose(a):
    return tuple(zip(*a))


def _matmul(a, b):
    return tuple(tuple(sum((a[i][k] * b[k][j] for k in range(len(b))), Fraction())
                       for j in range(len(b[0]))) for i in range(len(a)))


def _matvec(a, b):
    return tuple(sum((x*y for x, y in zip(row, b)), Fraction()) for row in a)


def _determinant(a):
    return (a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
            - a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
            + a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]))


def _inverse(a):
    rows = [list(row) + list(unit) for row, unit in zip(a, _identity())]
    for j in range(3):
        pivot = next((i for i in range(j, 3) if rows[i][j]), None)
        if pivot is None:
            raise ValueError('affine map is singular')
        rows[j], rows[pivot] = rows[pivot], rows[j]
        value = rows[j][j]
        rows[j] = [x/value for x in rows[j]]
        for i in range(3):
            if i != j:
                value = rows[i][j]
                rows[i] = [x-value*y for x, y in zip(rows[i], rows[j])]
    return tuple(tuple(row[3:]) for row in rows)


def fraction_payload(value) -> dict:
    q = _fraction(value)
    return {'numerator': str(q.numerator), 'denominator': str(q.denominator)}


def fraction_from_payload(value) -> Fraction:
    if type(value) is not dict or set(value) != {'numerator', 'denominator'}:
        raise ValueError('invalid exact rational payload')
    if any(type(value[k]) is not str for k in value):
        raise ValueError('rational numerator and denominator must be canonical integer strings')
    try:
        n, d = int(value['numerator']), int(value['denominator'])
    except ValueError as exc:
        raise ValueError('invalid rational integer strings') from exc
    if d <= 0 or str(n) != value['numerator'] or str(d) != value['denominator']:
        raise ValueError('noncanonical rational integer strings')
    q = Fraction(n, d)
    if q.numerator != n or q.denominator != d:
        raise ValueError('rational payload must be reduced')
    return q


def _exact_tree(value):
    if isinstance(value, Fraction):
        return fraction_payload(value)
    if isinstance(value, (tuple, list)):
        return [_exact_tree(x) for x in value]
    if isinstance(value, dict):
        return {key: _exact_tree(item) for key, item in value.items()}
    return value


def _strict_equal(a, b):
    if type(a) is not type(b):
        return False
    if type(a) is dict:
        return set(a) == set(b) and all(_strict_equal(a[k], b[k]) for k in a)
    if type(a) in (tuple, list):
        return len(a) == len(b) and all(_strict_equal(x, y) for x, y in zip(a, b))
    if type(a) is float:
        return math.isfinite(a) and math.isfinite(b) and a.hex() == b.hex()
    return a == b


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     allow_nan=False).encode('utf8')).hexdigest()


def _json_from_bytes(payload):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    def bad_constant(value):
        raise ValueError('nonfinite JSON token: ' + value)
    return json.loads(payload, object_pairs_hook=pairs, parse_constant=bad_constant)


def unit_contract() -> dict:
    """The sole P20 physical proposal; neither geometry nor density is rounded."""
    return dict(
        schema='W4P20ReferenceUnitsV1', length_unit=LENGTH_UNIT, mass_unit=MASS_UNIT,
        input_coordinate_frame=REFERENCE_FRAME, input_density=1.0,
        reference_length_in_m_exact=fraction_payload(SCALE_M_PER_REFERENCE),
        reference_mass_in_kg_exact=fraction_payload(MASS_KG_PER_REFERENCE),
        proposed_density_kg_m3=1200.0, proposed_length_m_per_reference=0.025,
        proposed_density_kg_m3_exact=fraction_payload(DENSITY_KG_M3),
        tip_reference=[0.0, 0.0, 0.0], spin_axis_reference=[0.0, 0.0, 1.0],
        additional_reference_linear=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        additional_reference_translation=[0.0, 0.0, 0.0],
        historical_p13_transform_already_applied=True,
        density_is_reference_mass_per_reference_length_cubed=True,
        physical_material_validated=False,
    )


def validate_unit_contract(units: Mapping) -> dict:
    if not _strict_equal(units, unit_contract()):
        raise ValueError('P20_UNIT_CONTRACT_CHANGED_OR_REFERENCE_FRAME_TRANSFORM_REAPPLIED')
    return unit_contract()


def affine_raw10(raw10, linear, translation, *, mass_scale=Fraction(1)) -> tuple:
    """Push a mass measure by x=A*u+t and multiply its mass by mass_scale.

    There is deliberately no hidden determinant or density factor.  For a
    geometric volume integral use ``mass_scale=abs(det(A))`` explicitly; for
    unit conversion of an already density-weighted moment use the mass-unit
    conversion.  Ordinary cross terms are retained in RAW10_ORDER.
    """
    r, a, t = _vector(raw10, 10, 'raw10'), _matrix(linear, 3), _vector(translation, 3)
    factor = _fraction(mass_scale, 'mass_scale')
    if factor <= 0 or not _determinant(a):
        raise ValueError('positive mass scale and invertible affine map required')
    mass, first = r[0], _matvec(a, r[1:4])
    q = ((r[4], r[9], r[8]), (r[9], r[5], r[7]), (r[8], r[7], r[6]))
    aq = _matmul(_matmul(a, q), _transpose(a))
    second = tuple(tuple(aq[i][j] + first[i]*t[j] + t[i]*first[j] + mass*t[i]*t[j]
                         for j in range(3)) for i in range(3))
    result = (mass, *(first[i]+mass*t[i] for i in range(3)),
              second[0][0], second[1][1], second[2][2],
              second[1][2], second[0][2], second[0][1])
    return tuple(factor*x for x in result)


def raw10_reference_to_si(raw10, *, units=None) -> tuple:
    validate_unit_contract(unit_contract() if units is None else units)
    values = _vector(raw10, 10, 'raw10')
    return tuple(x*MASS_KG_PER_REFERENCE*SCALE_M_PER_REFERENCE**degree
                 for x, degree in zip(values, RAW10_DEGREES))


def raw10_si_to_reference(raw10, *, units=None) -> tuple:
    validate_unit_contract(unit_contract() if units is None else units)
    values = _vector(raw10, 10, 'raw10')
    return tuple(x/(MASS_KG_PER_REFERENCE*SCALE_M_PER_REFERENCE**degree)
                 for x, degree in zip(values, RAW10_DEGREES))


def core_normalization_from_vertices(vertices, *, densities=(1.0,)) -> dict:
    """Reproduce spin_problem.py's binary64 bbox arithmetic, without native."""
    rows = [tuple(_binary64(x, 'vertex') for x in row) for row in vertices]
    if not rows or any(len(row) != 3 for row in rows):
        raise ValueError('nonempty three-dimensional vertices required')
    lo = [min(row[i] for row in rows) for i in range(3)]
    hi = [max(row[i] for row in rows) for i in range(3)]
    spans = [hi[i]-lo[i] for i in range(3)]
    center = [lo[i]+spans[i]*0.5 for i in range(3)]
    length = max(spans)
    rho = tuple(_binary64(x, 'density') for x in densities)
    if not rho or any(x <= 0 for x in rho):
        raise ValueError('density must be positive')
    density = max(rho)
    if not math.isfinite(length) or length <= 0 or not all(map(math.isfinite, center)):
        raise ValueError('invalid normalization bbox')
    try:
        scales = [length**degree*density for degree in (3, 4, 5)]
    except OverflowError as exc:
        raise ValueError('normalization units are unrepresentable') from exc
    if not all(math.isfinite(x) and x > 0 for x in scales) or any(x/density <= 0 for x in rho):
        raise ValueError('normalization units are unrepresentable')
    return dict(origin=center, L=length, R=density,
                axes=[[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
                authority='IMPLEMENTATION_DEFAULT', frame='INPUT_NORMALIZED_V1')


@dataclass(frozen=True)
class Frame:
    """Exact reading of an actual normalized-target frame's binary64 values.

    x_original = origin + L*(target_axes*y_target + target_origin).
    Non-exactly orthonormal axes fail closed.  The P20 +Z axes are the exact
    identity; this certificate does not pretend arbitrary rounded rotations
    are exactly rigid.  requested_tip is kept distinct from represented_tip.
    """
    origin: tuple
    length: Fraction
    density_scale: Fraction
    target_origin: tuple
    target_axes: tuple
    requested_tip: tuple

    def __post_init__(self):
        for name in ('origin', 'target_origin', 'requested_tip'):
            object.__setattr__(self, name, _vector(getattr(self, name), 3, name))
        object.__setattr__(self, 'length', _fraction(self.length, 'length'))
        object.__setattr__(self, 'density_scale', _fraction(self.density_scale, 'density_scale'))
        object.__setattr__(self, 'target_axes', _matrix(self.target_axes, 3, 'target_axes'))
        if self.length <= 0 or self.density_scale <= 0:
            raise ValueError('frame length and density scale must be positive')
        if (_matmul(_transpose(self.target_axes), self.target_axes) != _identity()
                or _determinant(self.target_axes) != 1):
            raise ValueError('EXACT_RIGHT_HANDED_ORTHONORMAL_AXES_REQUIRED')

    @classmethod
    def from_core(cls, normalization, target_origin, target_axes, *, requested_tip=(0.0, 0.0, 0.0)):
        if type(normalization) is not dict or set(normalization) != {'origin', 'L', 'R', 'axes', 'authority', 'frame'}:
            raise ValueError('actual core normalization has unknown or missing fields')
        if normalization['authority'] != 'IMPLEMENTATION_DEFAULT' or normalization['frame'] != 'INPUT_NORMALIZED_V1':
            raise ValueError('unsupported core normalization authority/frame')
        if _matrix(normalization['axes'], 3) != _identity():
            raise ValueError('core input-normalization axes changed')
        o = tuple(_binary64(x, 'normalization origin') for x in normalization['origin'])
        l, r = _binary64(normalization['L'], 'L'), _binary64(normalization['R'], 'R')
        tip = tuple(_binary64(x, 'requested tip') for x in requested_tip)
        target = tuple(_binary64(x, 'target origin') for x in target_origin)
        axes = tuple(tuple(_binary64(x, 'target axis') for x in row) for row in target_axes)
        if len(o) != 3 or len(tip) != 3 or len(target) != 3 or l <= 0 or r <= 0:
            raise ValueError('invalid core frame dimensions or scale')
        expected_target = tuple((tip[i]-o[i])/l for i in range(3))
        if tuple(x.hex() for x in target) != tuple(x.hex() for x in expected_target):
            raise ValueError('TARGET_ORIGIN_IS_NOT_CORE_REQUEST_OR_TIP_TRANSFORM_REAPPLIED')
        return cls(o, l, r, target, axes, tip)

    @property
    def original_from_target_linear(self):
        return tuple(tuple(self.length*x for x in row) for row in self.target_axes)

    @property
    def represented_tip(self):
        return tuple(o+self.length*t for o, t in zip(self.origin, self.target_origin))

    @property
    def target_from_original_linear(self):
        return tuple(tuple(x/self.length for x in row) for row in _transpose(self.target_axes))

    @property
    def target_from_original_translation(self):
        return tuple(-x for x in _matvec(self.target_from_original_linear, self.represented_tip))

    def original_point_to_target(self, point):
        p = _matvec(self.target_from_original_linear, _vector(point, 3, 'point'))
        return tuple(x+t for x, t in zip(p, self.target_from_original_translation))

    def target_point_to_original(self, point):
        p = _matvec(self.original_from_target_linear, _vector(point, 3, 'point'))
        return tuple(x+t for x, t in zip(p, self.represented_tip))

    def identity(self):
        return _digest(self.report(include_identity=False))

    def report(self, *, include_identity=True):
        result = dict(
            schema='W4P20ExactCoreFrameV1', original_frame=REFERENCE_FRAME,
            coefficient_frame=TARGET_FRAME, normalization_origin_exact=_exact_tree(self.origin),
            length_original_per_normalized_exact=fraction_payload(self.length),
            density_original_per_normalized_exact=fraction_payload(self.density_scale),
            actual_target_origin_exact=_exact_tree(self.target_origin),
            actual_target_axes_exact=_exact_tree(self.target_axes),
            requested_tip_reference_exact=_exact_tree(self.requested_tip),
            represented_tip_reference_exact=_exact_tree(self.represented_tip),
            represented_tip_minus_requested_exact=_exact_tree(tuple(a-b for a, b in zip(self.represented_tip, self.requested_tip))),
            represented_tip_is_exact_requested_tip=self.represented_tip == self.requested_tip,
            original_from_target_linear_exact=_exact_tree(self.original_from_target_linear),
            original_from_target_translation_exact=_exact_tree(self.represented_tip),
            native_length_scale_is_bbox_L_not_SI_0025=True,
            original_P19_mesh_or_tip_changed=False,
            numerical_frame_is_not_physical_approval=True,
        )
        if include_identity:
            result['frame_identity_sha256'] = self.identity()
        return result


def raw10_original_to_target(raw10, frame: Frame) -> tuple:
    if not isinstance(frame, Frame):
        raise ValueError('expected Frame')
    return affine_raw10(raw10, frame.target_from_original_linear,
                        frame.target_from_original_translation,
                        mass_scale=1/(frame.density_scale*frame.length**3))


def raw10_target_to_original(raw10, frame: Frame) -> tuple:
    if not isinstance(frame, Frame):
        raise ValueError('expected Frame')
    return affine_raw10(raw10, frame.original_from_target_linear, frame.represented_tip,
                        mass_scale=frame.density_scale*frame.length**3)


def convert_coefficients(coefficients, *, from_basis, to_basis) -> tuple:
    if from_basis not in (NATIVE_BASIS, LITERAL_BASIS) or to_basis not in (NATIVE_BASIS, LITERAL_BASIS):
        raise ValueError('unknown coefficient basis')
    values = _vector(coefficients, 10, 'coefficients')
    if not any(values):
        raise ValueError('zero polynomial has no coefficient identity')
    if from_basis == to_basis:
        return values
    factor = Fraction(2) if from_basis == NATIVE_BASIS else Fraction(1, 2)
    return values[:7] + tuple(factor*x for x in values[7:])


def coefficients_to_homogeneous(coefficients, *, basis=NATIVE_BASIS) -> tuple:
    p = convert_coefficients(coefficients, from_basis=basis, to_basis=NATIVE_BASIS)
    return ((p[4], p[9], p[8], p[1]/2), (p[9], p[5], p[7], p[2]/2),
            (p[8], p[7], p[6], p[3]/2), (p[1]/2, p[2]/2, p[3]/2, p[0]))


def homogeneous_to_coefficients(homogeneous, *, basis=NATIVE_BASIS) -> tuple:
    h = _matrix(homogeneous, 4, 'homogeneous quadric')
    if h != _transpose(h):
        raise ValueError('homogeneous quadric must be exactly symmetric')
    p = (h[3][3], 2*h[0][3], 2*h[1][3], 2*h[2][3], h[0][0], h[1][1],
         h[2][2], h[1][2], h[0][2], h[0][1])
    return convert_coefficients(p, from_basis=NATIVE_BASIS, to_basis=basis)


def quadric_pullback(coefficients, linear, translation, *, basis=NATIVE_BASIS) -> tuple:
    """Return q(A*y+t) without normalization, sign flipping or hidden rounding."""
    a, t = _matrix(linear, 3), _vector(translation, 3)
    if not _determinant(a):
        raise ValueError('quadric pullback requires an invertible map')
    transform = tuple(tuple(a[i])+(t[i],) for i in range(3)) + ((Fraction(), Fraction(), Fraction(), Fraction(1)),)
    h = coefficients_to_homogeneous(coefficients, basis=basis)
    return homogeneous_to_coefficients(_matmul(_matmul(_transpose(transform), h), transform), basis=basis)


def quadric_original_to_target(coefficients, frame: Frame, *, basis=NATIVE_BASIS) -> tuple:
    return quadric_pullback(coefficients, frame.original_from_target_linear, frame.represented_tip, basis=basis)


def quadric_target_to_original(coefficients, frame: Frame, *, basis=NATIVE_BASIS) -> tuple:
    return quadric_pullback(coefficients, frame.target_from_original_linear,
                            frame.target_from_original_translation, basis=basis)


def evaluate_quadric(coefficients, point, *, basis=NATIVE_BASIS) -> Fraction:
    p = convert_coefficients(coefficients, from_basis=basis, to_basis=LITERAL_BASIS)
    x, y, z = _vector(point, 3, 'quadric point')
    monomials = (Fraction(1), x, y, z, x*x, y*y, z*z, y*z, x*z, x*y)
    return sum((a*b for a, b in zip(p, monomials)), Fraction())


def coefficient_identity(coefficients, *, basis, frame_identity) -> str:
    p = convert_coefficients(coefficients, from_basis=basis, to_basis=basis)
    if type(frame_identity) is not str or not frame_identity:
        raise ValueError('explicit coefficient frame identity required')
    return _digest(dict(schema='W4P20ExactCoefficientIdentityV1', basis=basis,
                        frame_identity=frame_identity, vector_exact=_exact_tree(p),
                        positive_scale_quotienting=False))


def compare_coefficient_identity(first, second, *, basis, frame_identity) -> dict:
    a = convert_coefficients(first, from_basis=basis, to_basis=basis)
    b = convert_coefficients(second, from_basis=basis, to_basis=basis)
    index = next(i for i, x in enumerate(a) if x)
    ratio = b[index]/a[index]
    proportional = ratio > 0 and all(y == ratio*x for x, y in zip(a, b))
    return dict(first_identity_sha256=coefficient_identity(a, basis=basis, frame_identity=frame_identity),
                second_identity_sha256=coefficient_identity(b, basis=basis, frame_identity=frame_identity),
                coefficient_identity_equal=a == b, positive_proportional_polynomial=proportional,
                positive_scale_factor_exact=fraction_payload(ratio) if proportional else None,
                same_geometry_does_not_establish_same_J_identity=True,
                derivative_identity_certified=False)


def binary64_coefficient_projection(coefficients, *, basis, frame_identity) -> dict:
    """Expose an explicit proposed projection; this is not a native dispatch."""
    exact = convert_coefficients(coefficients, from_basis=basis, to_basis=basis)
    try:
        values = tuple(float(x) for x in exact)
    except OverflowError as exc:
        raise ValueError('coefficient binary64 projection overflow') from exc
    if not all(map(math.isfinite, values)) or not any(values):
        raise ValueError('coefficient binary64 projection nonfinite or all zero')
    projected = tuple(Fraction.from_float(x) for x in values)
    return dict(
        vector=list(values), vector_hex=[x.hex() for x in values],
        vector_exact=_exact_tree(projected), proposed_exact_vector=_exact_tree(exact),
        rounding_delta_exact=_exact_tree(tuple(a-b for a, b in zip(projected, exact))),
        projection_was_exact=projected == exact,
        exact_proposal_identity_sha256=coefficient_identity(exact, basis=basis, frame_identity=frame_identity),
        binary64_vector_identity_sha256=_digest(dict(basis=basis, frame_identity=frame_identity,
                                                     vector_hex=[x.hex() for x in values])),
        unit_norm_not_applied=True, native_dispatch_performed=False,
        actual_native_normalized_vector_observed=False, derivative_identity_certified=False,
    )


def register_unit_native_coefficients(coefficients, *, frame: Frame) -> dict:
    """Explicitly register one NEW normalized binary64 c, never rescale a J.

    The exact affine pullback is projected once to binary64.  Its positive
    norm is computed by sqrt(fsum(p_i*p_i)), with each product binary64, and
    every p_i/norm is saved as binary64.  Those saved bits are the proposed
    native input; they need their own evaluation/J receipt.  An implementation
    may normalize again internally, whose actual vector must be observed.
    """
    exact = convert_coefficients(coefficients, from_basis=NATIVE_BASIS, to_basis=NATIVE_BASIS)
    projection = binary64_coefficient_projection(exact, basis=NATIVE_BASIS, frame_identity=frame.identity())
    values = tuple(projection['vector'])
    squares = tuple(x*x for x in values)
    if not all(map(math.isfinite, squares)):
        raise ValueError('unit coefficient norm overflow')
    norm = math.sqrt(math.fsum(squares))
    if not math.isfinite(norm) or norm <= 0:
        raise ValueError('unit coefficient norm must be positive finite')
    c = tuple(x/norm for x in values)
    represented = tuple(Fraction.from_float(x) for x in c)
    norm_exact = Fraction.from_float(norm)
    scaled_proposal = tuple(x/norm_exact for x in exact)
    error = tuple(x-y for x, y in zip(represented, scaled_proposal))
    reference_actual = quadric_target_to_original(represented, frame)
    reference_proposed = quadric_target_to_original(scaled_proposal, frame)
    reference_error = tuple(x-y for x, y in zip(reference_actual, reference_proposed))
    norm_squared = sum((x*x for x in represented), Fraction())
    if abs(math.sqrt(math.fsum(x*x for x in c))-1.0) > 1e-12:
        raise ValueError('registered normalized c does not satisfy W0 norm tolerance')
    return dict(
        schema='W4P20ExplicitUnitNativeCoefficientRegistrationV1',
        registration='NEW_BINARY64_C_REQUIRES_NEW_NATIVE_EVALUATION_AND_J',
        source_unnormalized_exact_p=_exact_tree(exact), source_binary64_projection=projection,
        normalization_algorithm='BINARY64_SQRT_FSUM_OF_BINARY64_SQUARES_THEN_BINARY64_DIVISION',
        positive_norm_binary64=norm, positive_norm_hex=norm.hex(),
        positive_norm_binary64_exact=fraction_payload(norm_exact),
        exact_scaled_proposal_before_final_rounding=_exact_tree(scaled_proposal),
        native_c=list(c), native_c_hex=[x.hex() for x in c],
        native_c_exact=_exact_tree(represented), native_c_sha256=_digest(list(c)),
        native_c_sha256_algorithm='SHA256_CANONICAL_ASCII_JSON_LIST_OF_ACTUAL_BINARY64_C',
        native_c_norm_squared_exact=fraction_payload(norm_squared),
        native_c_norm_squared_minus_one_exact=fraction_payload(norm_squared-1),
        native_c_euclidean_norm_float=math.sqrt(math.fsum(x*x for x in c)),
        W0_unit_norm_absolute_tolerance=1e-12,
        scaled_proposal_to_native_c_delta_exact=_exact_tree(error),
        max_absolute_target_coefficient_rounding_error_exact=fraction_payload(max(map(abs, error))),
        represented_reference_native_p_exact=_exact_tree(reference_actual),
        ideal_scaled_reference_p_exact=_exact_tree(reference_proposed),
        represented_reference_coefficient_delta_exact=_exact_tree(reference_error),
        max_absolute_reference_coefficient_rounding_error_exact=fraction_payload(max(map(abs, reference_error))),
        coefficient_error_is_not_global_polynomial_error_bound=True,
        analytic_seed_positive_scale_is_not_native_c_or_J_identity=True,
        native_normalized_vector_after_internal_normalization_observed=False,
        native_dispatch_performed=False, derivative_identity_certified=False,
    )


def polynomial_difference_bound_on_box(first, second, bounds, *, basis=NATIVE_BASIS) -> Fraction:
    """Exact conservative sup |q1-q2| on an entire axis-aligned box."""
    a = convert_coefficients(first, from_basis=basis, to_basis=LITERAL_BASIS)
    b = convert_coefficients(second, from_basis=basis, to_basis=LITERAL_BASIS)
    if len(bounds) != 2:
        raise ValueError('box requires lower and upper corners')
    lo, hi = _vector(bounds[0], 3), _vector(bounds[1], 3)
    if any(x > y for x, y in zip(lo, hi)):
        raise ValueError('box bounds reversed')
    x, y, z = tuple(max(abs(p), abs(q)) for p, q in zip(lo, hi))
    terms = (Fraction(1), x, y, z, x*x, y*y, z*z, y*z, x*z, x*y)
    return sum((abs(p-q)*t for p, q, t in zip(a, b, terms)), Fraction())


def register_p20_dyadic_seed(frame: Frame) -> dict:
    """New P20 single-evaluation proposal, never a claimed optimized result."""
    center, radius = (Fraction(), Fraction(), Fraction(43, 64)), Fraction(1, 8)
    original = (Fraction(1785, 4096), Fraction(), Fraction(), Fraction(-43, 32),
                Fraction(1), Fraction(1), Fraction(1), Fraction(), Fraction(), Fraction())
    target = quadric_original_to_target(original, frame)
    native_registration = register_unit_native_coefficients(target, frame=frame)
    anchors = []
    for name, point in (('P20_D_NEGATIVE_POLYNOMIAL_ANCHOR', (Fraction(3, 32), Fraction(), center[2])),
                        ('P20_D_POSITIVE_POLYNOMIAL_ANCHOR', (Fraction(3, 16), Fraction(), center[2]))):
        target_point = frame.original_point_to_target(point)
        value = evaluate_quadric(original, point)
        represented_value = evaluate_quadric(native_registration['native_c'], target_point)
        if value != evaluate_quadric(target, target_point):
            raise AssertionError('exact coefficient/frame pullback failed')
        if value*represented_value <= 0:
            raise ValueError('NATIVE_C_PROJECTION_CHANGED_A_PREREGISTERED_ANCHOR_SIGN')
        anchors.append(dict(name=name, reference_exact=_exact_tree(point), target_exact=_exact_tree(target_point),
                            polynomial_value_exact=fraction_payload(value), sign=-1 if value < 0 else 1,
                            registered_native_c_value_exact=fraction_payload(represented_value),
                            registered_native_c_has_same_anchor_sign=True,
                            D_membership='NOT_CHECKED_BY_POLYNOMIAL_REGISTRATION'))
    return dict(
        schema='W4P20NewDyadicSphereProbeV1', registration='P20_NEW_PREREGISTRATION_NOT_OPTIMIZATION_RESULT',
        seed_name='P20_DYADIC_SPHERE_Z43_OVER64_RADIUS1_OVER8',
        reference_frame=REFERENCE_FRAME, coefficient_frame=TARGET_FRAME,
        coefficient_convention=NATIVE_BASIS,
        native_polynomial_basis=['1', 'x', 'y', 'z', 'x^2', 'y^2', 'z^2', '2yz', '2xz', '2xy'],
        center_reference_exact=_exact_tree(center), radius_reference_exact=fraction_payload(radius),
        reference_coefficients_exact=_exact_tree(original), target_coefficients_exact=_exact_tree(target),
        target_frame_identity_sha256=frame.identity(),
        target_binary64_projection=binary64_coefficient_projection(target, basis=NATIVE_BASIS, frame_identity=frame.identity()),
        explicit_unit_normalization=native_registration,
        native_c=native_registration['native_c'], native_c_sha256=native_registration['native_c_sha256'],
        anchors=anchors, polynomial_positive_side='OUTSIDE_SPHERE', polynomial_negative_side='INSIDE_SPHERE',
        future_native_retained_side='REQUIRES_ACTUAL_SAME_CALL_SIDE_SELECTION_RECEIPT',
        native_fromUnnormalized_will_normalize_its_input=True,
        actual_native_source_internal_normalization_not_predicted=True,
        source_sphere_triangulation_is_not_the_analytic_sphere=True,
        D_region_partition_certified=False, coefficients_sent_to_native=False,
        scientific_flags=scientific_flags(),
    )


def observe_core_sources(source_root) -> dict:
    """Hash the actual fixed source bytes; do not import or execute the core."""
    root = Path(source_root)
    result = {}
    for relative, expected in CORE_SOURCE_SHA256.items():
        path = root/relative
        payload = path.read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected:
            raise ValueError('P20_FIXED_CORE_SOURCE_SHA256_MISMATCH:' + relative)
        if path.read_bytes() != payload:
            raise ValueError('CORE_SOURCE_CHANGED_DURING_OBSERVATION:' + relative)
        result[relative] = actual
    return dict(commit=CORE_COMMIT, source_sha256=result, source_bytes_observed=True,
                registered_commit_git_HEAD_not_observed_by_this_function=True,
                whole_commit_tree_verified=False, native_binary_observed=False, native_core_executed=False)


def _bound_p19_packet(case_root):
    root = Path(case_root)
    manifest_path = root/'manifest.json'
    payload = manifest_path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != P19_MANIFEST_SHA256:
        raise ValueError('P19_MANIFEST_EXTERNAL_SHA256_MISMATCH')
    manifest = _json_from_bytes(payload)
    expected_files = {'M': 'material/M_native.obj', 'F': 'material/F_native.obj',
                      'D': 'material/D_native.obj', 'S': 'source/shaft-reference.obj'}
    if manifest['material_files'] != expected_files:
        raise ValueError('P19_MATERIAL_ROLES_CHANGED')
    paths, snapshots = {}, {manifest_path: payload}
    for name, relative in expected_files.items():
        path = root/relative
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != P19_MATERIAL_SHA256[name] or manifest['files_sha256'][relative] != digest:
            raise ValueError('P19_MATERIAL_EXTERNAL_SHA256_MISMATCH:' + name)
        paths[name], snapshots[path] = path, data
    return paths, snapshots


def _check_after(snapshots):
    for path, payload in snapshots.items():
        if path.read_bytes() != payload:
            raise ValueError('BOUND_INPUT_CHANGED_DURING_P20_AUDIT:' + str(path))


def _inertial_quantities(raw10):
    r = _vector(raw10, 10, 'raw10')
    if r[0] <= 0:
        raise ValueError('positive mass required for inertial quantities')
    center = tuple(x/r[0] for x in r[1:4])
    q = ((r[4], r[9], r[8]), (r[9], r[5], r[7]), (r[8], r[7], r[6]))
    central = tuple(tuple(q[i][j]-r[0]*center[i]*center[j] for j in range(3)) for i in range(3))
    def inertia(second):
        trace = sum(second[i][i] for i in range(3))
        return tuple(tuple((trace if i == j else Fraction())-second[i][j] for j in range(3)) for i in range(3))
    return center, inertia(q), inertia(central)


def replay_p19_physics(report_path, case_root) -> dict:
    """Independently replay P19 exact physical algebra, not its geometry audit."""
    paths, snapshots = _bound_p19_packet(case_root)
    report_path = Path(report_path)
    report_bytes = report_path.read_bytes()
    if hashlib.sha256(report_bytes).hexdigest() != P19_REPORT_SHA256:
        raise ValueError('P19_CANONICAL_REPORT_EXTERNAL_SHA256_MISMATCH')
    snapshots[report_path] = report_bytes
    report = _json_from_bytes(report_bytes)
    physical = report['physical_proposal']
    config = physical['case_config']
    if (not _strict_equal(config['scale_m_per_unit'], 0.025)
            or not _strict_equal(config['density_kg_m3'], 1200.0)
            or config['coordinate_frame'] != 'P13_REFERENCE_ALREADY_Z_UP'
            or not _strict_equal(config['tip_reference'], [0.0, 0.0, 0.0])
            or not _strict_equal(config['spin_axis_reference'], [0.0, 0.0, 1.0])):
        raise ValueError('P19_PHYSICAL_CONFIGURATION_CHANGED')
    if set(physical['materials']) != set(P19_MATERIAL_SHA256):
        raise ValueError('P19_PHYSICAL_MATERIAL_NAMES_CHANGED')
    materials, raw_by_name = {}, {}
    for name, row in physical['materials'].items():
        if (row['source_obj_sha256'] != P19_MATERIAL_SHA256[name]
                or row['moment_order'] != list(RAW10_ORDER)
                or row['cross_moment_convention'] != 'ORDINARY_UNDOUBLED'):
            raise ValueError('P19_RAW_MOMENT_IDENTITY_MISMATCH:' + name)
        raw = tuple(fraction_from_payload(x) for x in row['source_raw_ten_exact'])
        si = raw10_reference_to_si(raw)
        supplied_si = tuple(fraction_from_payload(x) for x in row['si_raw_ten_exact'])
        if si != supplied_si or raw10_si_to_reference(si) != raw:
            raise ValueError('P19_EXACT_SI_REPLAY_MISMATCH:' + name)
        center, origin_inertia, central_inertia = _inertial_quantities(si)
        checks = {
            'source_raw_ten': [float(x) for x in raw], 'si_raw_ten': [float(x) for x in si],
            'mass_kg': float(si[0]), 'center_of_mass_m': [float(x) for x in center],
            'full_inertia_origin_kg_m2': [[float(x) for x in line] for line in origin_inertia],
            'full_inertia_com_kg_m2': [[float(x) for x in line] for line in central_inertia],
        }
        if any(not _strict_equal(row[key], value) for key, value in checks.items()):
            raise ValueError('P19_FLOAT_PHYSICAL_REPLAY_MISMATCH:' + name)
        raw_by_name[name] = raw
        materials[name] = dict(source_obj_sha256=P19_MATERIAL_SHA256[name],
                               reference_raw10_exact=_exact_tree(raw), si_raw10_exact=_exact_tree(si),
                               center_of_mass_m_exact=_exact_tree(center),
                               full_inertia_origin_kg_m2_exact=_exact_tree(origin_inertia),
                               full_inertia_com_kg_m2_exact=_exact_tree(central_inertia),
                               **checks)
    residual = tuple(m-f-d for m, f, d in zip(raw_by_name['M'], raw_by_name['F'], raw_by_name['D']))
    if any(residual):
        raise ValueError('P19_RAW10_PARTITION_ADDITIVITY_MISMATCH')
    _check_after(snapshots)
    return dict(schema='W4P20IndependentP19PhysicalAlgebraReplayV1', status='EXACT_PHYSICAL_ALGEBRA_REPLAY_PASS',
                source_report_sha256=P19_REPORT_SHA256, source_manifest_sha256=P19_MANIFEST_SHA256,
                source_material_sha256=dict(P19_MATERIAL_SHA256), materials=materials,
                raw10_M_minus_F_minus_D_exact=_exact_tree(residual),
                density_reference=1.0, unit_contract=unit_contract(),
                source_meshes_reintegrated=False, P19_geometric_proofs_reexecuted=False,
                native_owned_regions_examined=False, shaft_already_in_F_not_added_to_mass=True,
                scientific_flags=scientific_flags())


def verify_seed_anchors(design_path) -> dict:
    """Exact D point-membership replay; nonemptiness witnesses, not a partition."""
    from p17_boundary_certificate import read_binary64_obj
    from p18_solid_domain import classify_point
    path = Path(design_path)
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != P19_MATERIAL_SHA256['D']:
        raise ValueError('P20_ANCHOR_DESIGN_SHA256_MISMATCH')
    mesh = read_binary64_obj(path)
    rows = []
    for name, point in (('P20_D_NEGATIVE_POLYNOMIAL_ANCHOR', (Fraction(3, 32), Fraction(), Fraction(43, 64))),
                        ('P20_D_POSITIVE_POLYNOMIAL_ANCHOR', (Fraction(3, 16), Fraction(), Fraction(43, 64)))):
        result = classify_point(mesh, point)
        if result['classification'] != 'INSIDE':
            raise ValueError('P20_D_ANCHOR_NOT_STRICTLY_INSIDE:' + name)
        rows.append(dict(name=name, reference_exact=_exact_tree(point), classification=result))
    if path.read_bytes() != payload:
        raise ValueError('P20_ANCHOR_DESIGN_CHANGED_DURING_REPLAY')
    return dict(status='BOTH_NEW_POLYNOMIAL_SIDE_ANCHORS_STRICTLY_INSIDE_P19_D',
                design_sha256=P19_MATERIAL_SHA256['D'], anchors=rows,
                relies_on_separately_proved_P19_embedded_closed_D=True,
                proof_scope='POINT_MEMBERSHIP_AND_NONEMPTY_ANALYTIC_POLYNOMIAL_SIDES_ONLY',
                native_source_triangulation_side_membership_certified=False,
                full_native_partition_certified=False)


def build_contract_report(frame: Frame, *, core_source_root, p19_case_root, p19_report_path) -> dict:
    """Bind mathematical proposals and replay to frozen sources and P19 inputs."""
    sources = observe_core_sources(core_source_root)
    paths, snapshots = _bound_p19_packet(p19_case_root)
    vertices = []
    for line in snapshots[paths['M']].decode('utf8').splitlines():
        tokens = line.split()
        if tokens and tokens[0] == 'v':
            if len(tokens) != 4:
                raise ValueError('P19_M_VERTEX_ROW_INVALID')
            vertices.append(tuple(float(x) for x in tokens[1:]))
    norm = core_normalization_from_vertices(vertices)
    actual = Frame.from_core(norm, [float(x) for x in frame.target_origin],
                             [[float(x) for x in row] for row in frame.target_axes])
    if frame != actual or frame.target_axes != _identity():
        raise ValueError('P20_FRAME_DOES_NOT_MATCH_FROZEN_P19_M_AND_ORIGINAL_TIP')
    replay = replay_p19_physics(p19_report_path, p19_case_root)
    seed = register_p20_dyadic_seed(frame)
    anchors = verify_seed_anchors(paths['D'])
    design_vertices = []
    for line in snapshots[paths['D']].decode('utf8').splitlines():
        tokens = line.split()
        if tokens and tokens[0] == 'v':
            design_vertices.append(tuple(Fraction.from_float(float(x)) for x in tokens[1:]))
    bounds = (tuple(min(row[i] for row in design_vertices) for i in range(3)),
              tuple(max(row[i] for row in design_vertices) for i in range(3)))
    registration = seed['explicit_unit_normalization']
    actual_p = tuple(fraction_from_payload(x) for x in registration['represented_reference_native_p_exact'])
    ideal_p = tuple(fraction_from_payload(x) for x in registration['ideal_scaled_reference_p_exact'])
    registration['fixed_D_reference_bbox_exact'] = _exact_tree(bounds)
    registration['max_polynomial_representation_error_bound_on_entire_D_bbox_exact'] = fraction_payload(
        polynomial_difference_bound_on_box(actual_p, ideal_p, bounds))
    exact_target_replays = {}
    for name, material in replay['materials'].items():
        raw = tuple(fraction_from_payload(x) for x in material['reference_raw10_exact'])
        target = raw10_original_to_target(raw, frame)
        returned = raw10_target_to_original(target, frame)
        exact_target_replays[name] = dict(
            exact_affine_target_raw10=_exact_tree(target),
            exact_inverse_reference_raw10=_exact_tree(returned),
            original_round_trip_exact=raw == returned,
            is_actual_request_rounded_vertex_fixed_moments=False,
        )
    observe_core_sources(core_source_root)
    _check_after(snapshots)
    return dict(schema=SCHEMA, status='P20_EXACT_MATHEMATICAL_PHYSICAL_CONTRACT_READY_NOT_NATIVE_ADMISSION',
                actual_core_sources=sources, units=unit_contract(), actual_frame=frame.report(),
                raw10_order=list(RAW10_ORDER), raw_cross_moments='ORDINARY_UNDOUBLED',
                coefficient_convention=NATIVE_BASIS, physical_replay=replay,
                exact_affine_target_moment_replays=exact_target_replays,
                new_probe_registration=seed, new_probe_anchor_replay=anchors,
                material_roles={'M': 'whole original solid', 'F': 'fixed retained material',
                                'D': 'variable design domain', 'S': 'protected shaft already inside F'},
                required_same_call_native_partitions=['M=F+ D', 'D=retained+cavity', 'M=F+retained+cavity'],
                native_partitions_require_owned_regions_and_set_predicates=True,
                raw10_additivity_alone_is_not_region_equality=True,
                spin_artifact_problem_constructed_by_this_module=False,
                native_dispatch_performed=False, scientific_flags=scientific_flags())

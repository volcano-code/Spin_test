"""W0 M21: explicit P20 native-target and conditional SI moment/Jacobian frames.

P20 Cherchi r_D and J_c are emitted in INPUT_NORMALIZED_TARGET_V1 at the
normalized request density. They are NOT already in SI. Native-frame tangent
checks use L_ref=1 and rho_ref=request.material_density (1 for frozen P20).
An SI audit must push forward EVERY r sample and EVERY column of J_c by the
same affine map before using SI L_ref/rho_ref. This module does not approve
physical units, a finite-difference budget, a derivative or a pilot.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math

import numpy as np

from .moment_coordinates import checked, pushforward_raw
from .tangent_neighborhood import audit_tangent_neighborhood


NATIVE_FRAME = "INPUT_NORMALIZED_TARGET_V1"
SI_FRAME = "P19_PROPOSED_SI_Z_UP"
EXPECTED_NATIVE_LENGTH_REF = 1.0
EXPECTED_SCALE_M_PER_REFERENCE = Fraction(3602879701896397, 144115188075855872)
EXPECTED_FRAME_LENGTH = Fraction(723841050109123, 281474976710656)
EXPECTED_NATIVE_DENSITY = 1.0
EXPECTED_PHYSICAL_DENSITY = Fraction(1200)


class MomentFrameRejected(ValueError):
    """Coordinate-frame mismatch or malformed raw-moment/Jacobian data."""


def _need(condition, reason):
    if not condition:
        raise MomentFrameRejected(reason)


def _fraction(payload, label):
    _need(type(payload) is dict and set(payload) == {"numerator", "denominator"},
          "INVALID_EXACT_FRACTION:" + label)
    n, d = payload["numerator"], payload["denominator"]
    _need(type(n) is str and type(d) is str and n.lstrip("-").isdigit()
          and d.isdigit() and int(d) > 0, "INVALID_EXACT_FRACTION_TOKENS:" + label)
    return Fraction(int(n), int(d))

def _fraction_or_token(payload, label):
    if type(payload) is str:
        parts = payload.split("/")
        _need(len(parts) == 2 and all(x.lstrip("-").isdigit() for x in parts)
              and int(parts[1]) > 0, "INVALID_EXACT_FRACTION_TOKEN:" + label)
        return Fraction(int(parts[0]), int(parts[1]))
    return _fraction(payload, label)


def _identity3(matrix):
    return matrix == [
        [{"numerator":"1","denominator":"1"},{"numerator":"0","denominator":"1"},{"numerator":"0","denominator":"1"}],
        [{"numerator":"0","denominator":"1"},{"numerator":"1","denominator":"1"},{"numerator":"0","denominator":"1"}],
        [{"numerator":"0","denominator":"1"},{"numerator":"0","denominator":"1"},{"numerator":"1","denominator":"1"}],
    ]


@dataclass(frozen=True)
class P20MomentFrameContract:
    native_frame: str
    native_length_ref: float
    native_density_ref: float
    si_frame: str
    si_length_ref: float
    si_density_ref: float
    native_material_density: float
    original_per_native_length: float
    original_per_native_density: float
    scale_m_per_reference: float
    target_to_si_linear: tuple
    target_to_si_translation: tuple
    native_to_si_density_ratio: float
    physical_parameters_approved: bool
    frame_identity_sha256: str

    def report(self):
        return {
            "schema":"W0_P20_NATIVE_SI_MOMENT_FRAME_CONTRACT_M21_V1",
            "status":"FRAME_MAPPING_VERIFIED_NO_PHYSICAL_OR_SCIENTIFIC_ADMISSION",
            "native_frame":self.native_frame,
            "native_normalization":{"length_ref":self.native_length_ref,
                                    "density_ref":self.native_density_ref},
            "si_frame":self.si_frame,
            "si_normalization":{"length_ref":self.si_length_ref,
                                "density_ref":self.si_density_ref},
            "native_material_density":self.native_material_density,
            "original_per_native_length":self.original_per_native_length,
            "original_per_native_density":self.original_per_native_density,
            "scale_m_per_reference":self.scale_m_per_reference,
            "target_to_si_linear":[list(row) for row in self.target_to_si_linear],
            "target_to_si_translation":list(self.target_to_si_translation),
            "native_to_si_density_ratio":self.native_to_si_density_ratio,
            "frame_identity_sha256":self.frame_identity_sha256,
            "physical_parameters_approved":self.physical_parameters_approved,
            "P30B_diagnostic_authorized":False,
            "derivative_neighborhood_certified":False,
            "Newton_accepted":False,
            "training_admissible":False,
        }


def build_p20_moment_frame_contract(request, frame_report):
    """Derive both valid audit modes from the actual frozen P20 request/frame."""
    _need(type(request) is dict and type(frame_report) is dict, "P20_OBJECTS_REQUIRED")
    units = request.get("units")
    target = request.get("target")
    admission = request.get("admission")
    frame = frame_report.get("actual_frame")
    _need(type(units) is dict and type(target) is dict and
          type(admission) is dict and type(frame) is dict,
          "P20_FRAME_OR_UNIT_CONTRACT_MISSING")
    _need(frame.get("coefficient_frame") == NATIVE_FRAME,
          "P20_NATIVE_COEFFICIENT_FRAME_MISMATCH")
    _need(_identity3(frame.get("actual_target_axes_exact")),
          "P20_FRAME_AXES_NOT_EXACT_IDENTITY")
    _need(frame.get("native_length_scale_is_bbox_L_not_SI_0025") is True,
          "P20_NATIVE_LENGTH_IS_NOT_BBOX_NORMALIZATION")
    _need(units.get("fixed_density") == 1 and units.get("design_density") == 1,
          "P20_REQUEST_DENSITIES_NOT_ONE")
    _need(units.get("physical_parameters_approved") is False
          and admission.get("W0_owner_admitted") is False
          and admission.get("original_author_CAD") is False,
          "P20_PHYSICAL_ADMISSION_STATE_CHANGED")
    _need(frame_report.get("physical_replay", {}).get("density_reference") == 1.0,
          "P20_PHYSICAL_REPLAY_DENSITY_REFERENCE_CHANGED")
    _need(target.get("mode") == "SPINNING_TOP" and target.get("axis") == [0,0,1],
          "P20_TARGET_MODE_OR_AXIS_CHANGED")

    native_density = float(units["design_density"])
    frame_length = _fraction(frame["length_original_per_normalized_exact"],
                             "length_original_per_normalized_exact")
    frame_density = _fraction(frame["density_original_per_normalized_exact"],
                              "density_original_per_normalized_exact")
    scale = _fraction_or_token(units["length_m_per_reference_exact"],
                                "length_m_per_reference_exact")
    physical_density = Fraction(int(units["physical_density_kg_m3"]), 1)
    _need(frame_length == EXPECTED_FRAME_LENGTH, "P20_FRAME_LENGTH_CHANGED")
    _need(frame_density == Fraction(1), "P20_FRAME_DENSITY_SCALE_CHANGED")
    _need(scale == EXPECTED_SCALE_M_PER_REFERENCE,
          "P20_REFERENCE_TO_SI_SCALE_CHANGED")
    _need(native_density == EXPECTED_NATIVE_DENSITY,
          "P20_NATIVE_DENSITY_CHANGED")
    _need(physical_density == EXPECTED_PHYSICAL_DENSITY,
          "P20_PROPOSED_PHYSICAL_DENSITY_CHANGED")

    # x_SI = s * (L * axes * x_target + represented_tip_reference).
    # The tip residual is retained exactly; it is not silently replaced by zero.
    tip = tuple(_fraction(v, "represented_tip_reference")
                for v in frame["represented_tip_reference_exact"])
    axes = frame["actual_target_axes_exact"]
    axes_float = [[float(_fraction(v, "target_axis")) for v in row] for row in axes]
    linear_scale = scale * frame_length
    linear = tuple(tuple(float(linear_scale) * axes_float[i][j]
                         for j in range(3)) for i in range(3))
    translation = tuple(float(scale * value) for value in tip)
    density_ratio = float(physical_density * frame_density)
    si_density = density_ratio * native_density
    si_length = float(linear_scale)

    _need(math.isfinite(si_length) and si_length > 0 and
          math.isfinite(si_density) and si_density > 0,
          "P20_SI_NORMALIZATION_NOT_REPRESENTABLE")
    return P20MomentFrameContract(
        native_frame=NATIVE_FRAME,
        native_length_ref=EXPECTED_NATIVE_LENGTH_REF,
        native_density_ref=native_density,
        si_frame=SI_FRAME,
        si_length_ref=si_length,
        si_density_ref=si_density,
        native_material_density=native_density,
        original_per_native_length=float(frame_length),
        original_per_native_density=float(frame_density),
        scale_m_per_reference=float(scale),
        target_to_si_linear=linear,
        target_to_si_translation=translation,
        native_to_si_density_ratio=density_ratio,
        physical_parameters_approved=False,
        frame_identity_sha256=frame["frame_identity_sha256"],
    )


def normalization_for_frame(contract, moment_coordinate_frame):
    _need(isinstance(contract, P20MomentFrameContract), "P20_FRAME_CONTRACT_REQUIRED")
    if moment_coordinate_frame == NATIVE_FRAME:
        return contract.native_length_ref, contract.native_density_ref
    if moment_coordinate_frame == SI_FRAME:
        return contract.si_length_ref, contract.si_density_ref
    raise MomentFrameRejected("UNKNOWN_MOMENT_COORDINATE_FRAME")


def validate_normalization(contract, moment_coordinate_frame, length_ref, density_ref):
    expected_l, expected_r = normalization_for_frame(contract, moment_coordinate_frame)
    _need(type(length_ref) in (int,float) and math.isfinite(length_ref)
          and type(density_ref) in (int,float) and math.isfinite(density_ref),
          "INVALID_EXPLICIT_NORMALIZATION")
    _need(math.isclose(float(length_ref), expected_l, rel_tol=0.0, abs_tol=2e-16)
          and math.isclose(float(density_ref), expected_r, rel_tol=0.0, abs_tol=2e-13),
          "MOMENT_FRAME_NORMALIZATION_MISMATCH")
    return expected_l, expected_r


def transform_raw10_native_to_si(raw10, contract):
    _need(isinstance(contract, P20MomentFrameContract), "P20_FRAME_CONTRACT_REQUIRED")
    values = checked(raw10, (10,), "native_target_raw10")
    return pushforward_raw(values, contract.target_to_si_linear,
                           contract.target_to_si_translation,
                           density_ratio=contract.native_to_si_density_ratio)


def transform_jacobian_native_to_si(J_native, contract):
    """Push forward each output-moment column; coefficient coordinates stay native."""
    J = checked(J_native, (10,10), "native_target_Jc")
    return np.column_stack([
        transform_raw10_native_to_si(J[:, column], contract)
        for column in range(10)
    ])


def transform_probe_native_to_si(probe, contract):
    _need(type(probe) is dict and set(probe) == {
        "c_native", "r_design", "feature_branch_sha256"},
        "MALFORMED_NATIVE_PROBE")
    return {
        "c_native": checked(probe["c_native"], (10,), "probe_c").tolist(),
        "r_design": transform_raw10_native_to_si(probe["r_design"], contract).tolist(),
        "feature_branch_sha256":probe["feature_branch_sha256"],
    }


def audit_tangent_neighborhood_in_frame(*, contract, moment_coordinate_frame,
                                        normalization_L, normalization_R,
                                        native_c, Jc, tangent_basis, probes,
                                        base_feature_branch_sha256, step_radians,
                                        max_normalized_jacobian_error):
    """Audit one frame explicitly; never compare native r/J against SI scales."""
    length_ref, density_ref = validate_normalization(
        contract, moment_coordinate_frame, normalization_L, normalization_R)
    if moment_coordinate_frame == NATIVE_FRAME:
        audit_J = checked(Jc, (10,10), "native_target_Jc")
        audit_probes = probes
    elif moment_coordinate_frame == SI_FRAME:
        audit_J = transform_jacobian_native_to_si(Jc, contract)
        _need(type(probes) in (list,tuple), "TANGENT_PROBES_REQUIRED")
        audit_probes = []
        for direction in probes:
            _need(type(direction) is dict and set(direction) ==
                  {"plus_h","minus_h","plus_half","minus_half"},
                  "TANGENT_DIRECTION_PACKET_INVALID")
            audit_probes.append({
                name: transform_probe_native_to_si(sample, contract)
                for name, sample in direction.items()
            })
    else:
        raise MomentFrameRejected("UNKNOWN_MOMENT_COORDINATE_FRAME")

    result = audit_tangent_neighborhood(
        native_c=native_c, Jc=audit_J, tangent_basis=tangent_basis,
        probes=audit_probes,
        base_feature_branch_sha256=base_feature_branch_sha256,
        step_radians=step_radians,
        length_ref=length_ref, density_ref=density_ref,
        max_normalized_jacobian_error=max_normalized_jacobian_error,
    )
    result["moment_coordinate_frame"] = moment_coordinate_frame
    result["normalization_L"] = length_ref
    result["normalization_R"] = density_ref
    result["coordinate_transform_applied"] = moment_coordinate_frame == SI_FRAME
    result["physical_parameters_approved"] = False
    result["smooth_neighborhood_certified"] = False
    result["training_admissible"] = False
    return result

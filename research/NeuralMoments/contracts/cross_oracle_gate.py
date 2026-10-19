"""M5: independently reconcile W0 and frozen W2 exact mathematical r10 oracles.

The W2 source is a byte-identical, READ-ONLY snapshot of W2's
independent_reference.py from research/neuralmoments-w2-teacher-20261019.
A passing comparison is numeric/topological sanity, NOT a Cherchi geometry,
material partition, Jacobian, Newton, or training certificate.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import re

from .native_teacher_replay import (ReplayRejected, boundary_rows,
                                    exact_raw_moments)

W2_ORACLE_SOURCE_SHA = "d734398292e1fdaf839db3413c537de2474df3e1"
W2_ORACLE_SOURCE_SHA256 = "3238fb14d4cbf85d7754551689fa40cbb08653bf3a9bf631faf16138f9c6bea9"
W2_ORACLE_PIN_BRANCH = "research/neuralmoments-w2-teacher-20261019"
W2_ORACLE_PATH = "research/NeuralMoments/teacher/independent_reference.py"
R_ORDER = ("M", "LX", "LY", "LZ", "QXX", "QYY", "QZZ", "QYZ", "QXZ", "QXY")


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_pinned_w2_oracle(path=None):
    """Only execute already-pinned source bytes; reject prior to import on drift."""
    if path is None:
        path = Path(__file__).with_name("w2_reference_snapshot.py")
    path = Path(path)
    data = path.read_bytes()
    if (git_blob_sha1(data) != W2_ORACLE_SOURCE_SHA or
            hashlib.sha256(data).hexdigest() != W2_ORACLE_SOURCE_SHA256):
        raise ReplayRejected("W2_ORACLE_SOURCE_SHA_MISMATCH")
    spec = importlib.util.spec_from_file_location("_w0_pinned_w2_reference", path)
    if spec is None or spec.loader is None:
        raise ReplayRejected("PINNED_W2_REFERENCE_CANNOT_IMPORT")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canon_tokens(values):
    # Standard rational form; W2 accepts strings and exact Fraction/int.
    if not isinstance(values, (list, tuple)):
        raise ReplayRejected("INVALID_BOUNDARY_SHAPE")
    rows = []
    for row in values:
        if not isinstance(row, (list, tuple)) or len(row) != 3:
            raise ReplayRejected("INVALID_BOUNDARY_VERTEX")
        coords = []
        for v in row:
            if isinstance(v, bool) or type(v) is not str:
                raise ReplayRejected("ONLY_FROZEN_RATIONAL_STRINGS_ACCEPTED")
            coords.append(v)
        rows.append(coords)
    return rows


def cross_check_exact_boundary(vertices, faces, density_token, *, oracle_path=None):
    """Exact W0-vs-W2 independent arithmetic parity, all 10 mass moments.

    Density must be an exact rational string; never silently infer from floats.
    The original ordered/position-indexed mesh is not canonicalized away.
    """
    vertices = _canon_tokens(vertices)
    if not isinstance(faces, (list, tuple)):
        raise ReplayRejected("INVALID_TRIANGLE_INDEX_LIST")
    faces = [list(f) if isinstance(f, (list, tuple)) else f for f in faces]
    if type(density_token) is not str or not re.fullmatch(r"-?[0-9]+/[1-9][0-9]*", density_token):
        raise ReplayRejected("EXACT_RATIONAL_DENSITY_REQUIRED")
    density = Fraction(density_token)
    if density <= 0:
        raise ReplayRejected("DENSITY_MUST_BE_POSITIVE")
    points, triangles = boundary_rows(vertices, faces)
    w0 = exact_raw_moments(points, triangles, density)
    w2_mod = load_pinned_w2_oracle(oracle_path)
    try:
        w2, proof = w2_mod.integrate_exact_boundary(vertices, faces, density)
    except (ValueError, TypeError, IndexError, ZeroDivisionError) as exc:
        raise ReplayRejected("W2_REFERENCE_REJECTED_SAME_INPUT") from exc
    if len(w2) != 10 or tuple(w2) != w0:
        raise ReplayRejected("W0_W2_TEN_MOMENT_EXACT_MISMATCH")
    if proof.get("schema") != "w2-independent-tetra-integral-v1" or \
            proof.get("reference_scope") != "CLOSED_ORIENTED_TRIANGLE_BOUNDARY_NOT_EMBEDDING_CERTIFICATE" or \
            proof.get("vertex_count") != len(points) or proof.get("face_count") != len(triangles):
        raise ReplayRejected("W2_REFERENCE_PROOF_SEMANTICS_MISMATCH")
    encoded = [f"{x.numerator}/{x.denominator}" for x in w0]
    if proof.get("reference_raw_moments_exact") != encoded:
        raise ReplayRejected("W2_REFERENCE_PROOF_VALUES_MISMATCH")
    return {
        "schema": "W0_M5_TWO_ORACLE_MATHEMATICAL_PARITY_V1",
        "order": list(R_ORDER),
        "exact_r10": encoded,
        "independent_w2_source_blob_sha1": W2_ORACLE_SOURCE_SHA,
        "independent_w2_source_sha256": W2_ORACLE_SOURCE_SHA256,
        "independent_w2_proof": proof,
        "identical_all_ten": True,
        "independent_cherchi_boolean_proof": False,
        "smooth_jacobian_proof": False,
        "complete_material_partition_proof": False,
        "training_admissible": False,
    }


def compare_frozen_fd(*, fixed_boundary, design_boundary, fixed_density, design_density, total_raw_exact):
    """Validate exact fixed+design accounting using both pinned oracles.

    Independent input F/D boundaries must already be supplied. Their spatial
    disjointness and correct Boolean relationship need external Nef proof.
    """
    if (type(total_raw_exact) not in (list,tuple) or
        len(total_raw_exact) != 10 or
        any(type(x) is not str or
            re.fullmatch(r"-?[0-9]+/[1-9][0-9]*",x) is None
            for x in total_raw_exact)):
        raise ReplayRejected("TEN_CANONICAL_EXACT_TOTAL_COMPONENTS_REQUIRED")
    f = cross_check_exact_boundary(*fixed_boundary, fixed_density)
    d = cross_check_exact_boundary(*design_boundary, design_density)
    expected = [Fraction(x) + Fraction(y) for x,y in zip(f["exact_r10"], d["exact_r10"])]
    try:
        actual = [Fraction(x) for x in total_raw_exact]
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ReplayRejected("INVALID_EXACT_TOTAL_R") from exc
    if actual != expected:
        raise ReplayRejected("FIXED_DESIGN_TOTAL_MOMENTS_MISMATCH")
    return {
        "schema": "W0_M5_EXACT_FIXED_DESIGN_ACCOUNTING_V1",
        "r_F_exact": f["exact_r10"],
        "r_D_exact": d["exact_r10"],
        "r_total_exact": [f"{x.numerator}/{x.denominator}" for x in expected],
        "fixed_added_once": True,
        "geometric_disjointness_proved": False,
        "training_admissible": False,
    }

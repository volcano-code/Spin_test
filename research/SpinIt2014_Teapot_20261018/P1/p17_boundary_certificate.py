"""Exact signed boundary-chain identity of saved W4 binary64 OBJ surfaces.

An oriented triangle [a,b,c] equals [b,c,a] and -[a,c,b].  P16's cyclic-only
counter implemented the first relation but not the second.  Oppositely oriented
cavity faces therefore appeared as distinct residual keys even when their true
signed chain cancelled exactly.  P17 retains the historical P16 result and uses
both orientation relations explicitly, with no tolerance or geometric edits.

Scope: finite oriented simplicial chains at saved IEEE-754 coordinates.  This
does NOT certify Cherchi internal implicit rational points, embeddedness, set
equality of pre/post-microweld solids, W0 physics, or optimization readiness.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path


Point = tuple[Fraction, Fraction, Fraction]
Triangle = tuple[Point, Point, Point]
FALSE_FLAGS = {
    "native_Cherchi_implicit_geometry_certified": False,
    "native_provenance_authenticated_by_chain_audit": False,
    "ordinary_solid_region_equality_certified": False,
    "original_native_vs_microweld_set_equality_certified": False,
    "W0_physical_tip_or_FD_approved": False,
    "W2_teacher_training_allowed": False,
    "Faster_optimization_executed": False,
    "MuJoCo_real_optimized_before_after_executed": False,
    "printability_certified": False,
}


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


@dataclass(frozen=True)
class ExactMesh:
    path: str
    sha256: str
    vertices: tuple[Point, ...]
    faces: tuple[tuple[int, int, int], ...]

    @property
    def triangles(self):
        return tuple(tuple(self.vertices[i] for i in face) for face in self.faces)


def read_binary64_obj(path: str | Path) -> ExactMesh:
    """Parse each OBJ coordinate to binary64, then its exact rational value.

    This intentionally differs from treating the decimal token itself as an
    exact real number.  No tolerance grouping, near-point welding, winding
    correction, remeshing, or face deletion is performed.
    """
    path = Path(path)
    data = path.read_bytes()
    vertices, faces = [], []
    for line_no, raw in enumerate(data.decode("utf-8").splitlines(), 1):
        words = raw.split("#", 1)[0].split()
        if not words:
            continue
        if words[0] == "v":
            if len(words) != 4:
                raise ValueError(f"line {line_no}: exactly three coordinates required")
            values = tuple(float(x) for x in words[1:])
            if not all(math.isfinite(x) for x in values):
                raise ValueError(f"line {line_no}: nonfinite vertex coordinate")
            vertices.append(tuple(Fraction.from_float(x) for x in values))
        elif words[0] == "f":
            if len(words) != 4:
                raise ValueError(f"line {line_no}: triangular faces required")
            indices = []
            for token in words[1:]:
                index = int(token.split("/", 1)[0])
                if index == 0:
                    raise ValueError(f"line {line_no}: OBJ index zero")
                index = index - 1 if index > 0 else len(vertices) + index
                if not 0 <= index < len(vertices):
                    raise ValueError(f"line {line_no}: face index out of range")
                indices.append(index)
            faces.append(tuple(indices))
    if not vertices or not faces:
        raise ValueError("empty triangle mesh")
    mesh = ExactMesh(str(path), hashlib.sha256(data).hexdigest(), tuple(vertices), tuple(faces))
    for face_index, tri in enumerate(mesh.triangles):
        if not any(_cross(_sub(tri[1], tri[0]), _sub(tri[2], tri[0]))):
            raise ValueError(f"face {face_index}: exact zero-area triangle")
    return mesh


def cyclic_key(tri: Triangle):
    """Legacy key: cyclic equivalence only; reverse remains a separate key."""
    return min(tri, tri[1:] + tri[:1], tri[2:] + tri[:2])


def signed_triangle_key(tri: Triangle):
    """Canonical unoriented support and its sign; all six permutations covered."""
    forward = cyclic_key(tri)
    backward = cyclic_key((tri[0], tri[2], tri[1]))
    if forward == backward:
        raise ValueError("repeated triangle point has undefined orientation")
    return (forward, 1) if forward < backward else (backward, -1)


def triangle_chain(terms):
    """Return nonzero integer coefficients in the actual oriented-simplex basis."""
    result = Counter()
    for mesh, coefficient in terms:
        if not isinstance(coefficient, int):
            raise ValueError("integer chain coefficients required")
        for tri in mesh.triangles:
            key, sign = signed_triangle_key(tri)
            result[key] += coefficient * sign
    return {tri: coefficient for tri, coefficient in result.items() if coefficient}


def _legacy_chain(terms):
    result = Counter()
    for mesh, coefficient in terms:
        for tri in mesh.triangles:
            result[cyclic_key(tri)] += coefficient
    return {tri: coefficient for tri, coefficient in result.items() if coefficient}


def _triangle_json(tri):
    return [[str(c) for c in p] for p in tri]


def certify_triangle_chain(terms):
    """Check exact literal signed chain identity; do not infer solid legality.

    This is a sufficient certificate. Different coplanar subdivisions can
    represent equal surfaces while failing this literal simplicial test. A
    failure is therefore NOT a proof that continuous solid sets differ.
    """
    terms = tuple(terms)
    signed = triangle_chain(terms)
    legacy = _legacy_chain(terms)
    lifted_legacy = Counter()
    orientation_pairs = 0
    for tri, coefficient in legacy.items():
        key, sign = signed_triangle_key(tri)
        lifted_legacy[key] += sign * coefficient
        if sign == 1 and cyclic_key((tri[0], tri[2], tri[1])) in legacy:
            orientation_pairs += 1
    if {t: c for t, c in lifted_legacy.items() if c} != signed:
        raise AssertionError("legacy-to-signed quotient must agree with direct accumulation")
    passed = not signed
    witnesses = [{"signed_coefficient": coefficient,
                  "exact_binary64_triangle": _triangle_json(tri)}
                 for tri, coefficient in sorted(signed.items())[:4]]
    return {
        "status": "EXACT_SAVED_BINARY64_SIGNED_CHAIN_PASS" if passed else "SIGNED_CHAIN_IDENTITY_NOT_DEMONSTRATED",
        "certificate": "EXACT_SAVED_BINARY64_ORIENTED_SIMPLICIAL_CHAIN",
        "exact_signed_triangle_chain_zero": passed,
        "signed_triangle_residual_terms": len(signed),
        "signed_triangle_residual_l1_multiplicity": sum(abs(c) for c in signed.values()),
        "legacy_cyclic_multiset_residual_terms": len(legacy),
        "legacy_reverse_orientation_pairs": orientation_pairs,
        "residual_witnesses": witnesses,
        "tolerance_used": None,
        "proof_scope": "Exact finite oriented triangle chain at saved binary64 coordinates; no claim about native implicit points or ordinary solid regions.",
        "orientation_relations": ["[a,b,c]=[b,c,a]=[c,a,b]", "[a,b,c]=-[a,c,b]"],
        "geometry_modified": False,
        "scientific_flags": dict(FALSE_FLAGS),
    }


def audit_boundary_partition(outer_path, retained_path, design_path, expected_sha256=None):
    """Prove boundary(O)-boundary(F)-boundary(D)=0, with optional frozen hashes.

    The optional dictionary must provide all of outer/retained/design.  Recorded
    input hashes alone establish identity of this audit's bytes, not upstream
    native provenance. The caller remains responsible for authenticating source
    archives and their original native execution receipts.
    """
    names = ("outer", "retained", "design")
    meshes = tuple(map(read_binary64_obj, (outer_path, retained_path, design_path)))
    if expected_sha256 is not None:
        if set(expected_sha256) != set(names):
            raise ValueError("expected_sha256 must pin all three input meshes")
        for name, mesh in zip(names, meshes):
            if mesh.sha256 != expected_sha256[name]:
                raise ValueError(f"{name}: frozen SHA256 mismatch")
    result = certify_triangle_chain(zip(meshes, (1, -1, -1)))
    result["inputs"] = {name: {"sha256": mesh.sha256, "vertices": len(mesh.vertices),
                               "faces": len(mesh.faces)} for name, mesh in zip(names, meshes)}
    result["frozen_sha256_manifest_checked"] = expected_sha256 is not None
    result["partition_identity"] = "boundary(outer)-boundary(retained)-boundary(design)=0"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outer", required=True)
    parser.add_argument("--retained", required=True)
    parser.add_argument("--design", required=True)
    parser.add_argument("--expected-sha256-json", help="JSON object pinning outer, retained, design")
    parser.add_argument("--output", help="new report path; existing files are never overwritten")
    args = parser.parse_args()
    expected = json.loads(Path(args.expected_sha256_json).read_text()) if args.expected_sha256_json else None
    report = audit_boundary_partition(args.outer, args.retained, args.design, expected)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output)
        if output.exists():
            raise FileExistsError("preserve historical reports; use a new output path")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            stream.write(text + "\n")
    print(text)
    return 0 if report["exact_signed_triangle_chain_zero"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

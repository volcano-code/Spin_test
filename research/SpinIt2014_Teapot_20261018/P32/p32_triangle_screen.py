#!/usr/bin/env python3
"""Reproducible, tolerance-explicit P19 triangle screen for W4 P32.

This is a floating-point diagnostic screen, NOT an exact/robust solid certificate.
It checks mesh self-intersections among nonincident triangles and cross-mesh
triangle contacts. Coplanar contacts are retained and reported, never silently
called volumetric penetration.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path

BASE = Path("research/SpinIt2014_Teapot_20261018/P1/P19_material_case")
FILES = {
    "M": BASE / "material/M_native.obj",
    "D": BASE / "material/D_native.obj",
    "S": BASE / "source/shaft-reference.obj",
}
BLOBS = {
    "M": "e2651b8a2efcc89fee3e69f9ebb78ddffb8f942e",
    "D": "9820f3d73d15a4cdd0c504a0264f934aefd40df1",
    "S": "9fe9f78257c7a90970095f6bb54c5148198a33d1",
}
TOL = 1e-11
AXIS_EPS = 1e-14


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def parse_obj(raw: bytes, label: str):
    vertices, faces = [], []
    for lineno, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        fields = line.strip().split()
        if not fields or fields[0].startswith("#"):
            continue
        if fields[0] == "v":
            if len(fields) < 4:
                raise ValueError(f"{label}: malformed vertex at line {lineno}")
            point = tuple(float(x) for x in fields[1:4])
            if not all(math.isfinite(x) for x in point):
                raise ValueError(f"{label}: nonfinite vertex at line {lineno}")
            vertices.append(point)
        elif fields[0] == "f":
            ids = []
            for token in fields[1:]:
                idx = int(token.split("/")[0])
                ids.append(idx - 1 if idx > 0 else len(vertices) + idx)
            if len(ids) != 3 or any(i < 0 or i >= len(vertices) for i in ids):
                raise ValueError(f"{label}: expected valid triangle at line {lineno}")
            faces.append(tuple(ids))
    return vertices, faces


def sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def dot(a, b):
    return sum(a[i] * b[i] for i in range(3))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def tri_record(index, ids, vertices):
    pts = tuple(vertices[i] for i in ids)
    return {
        "index": index, "ids": ids, "pts": pts,
        "lo": tuple(min(p[k] for p in pts) for k in range(3)),
        "hi": tuple(max(p[k] for p in pts) for k in range(3)),
    }


def separated(a, b, axis):
    length = math.sqrt(dot(axis, axis))
    if length < AXIS_EPS:
        return False
    pa = [dot(p, axis) for p in a]
    pb = [dot(p, axis) for p in b]
    margin = TOL * length
    return max(pa) < min(pb) - margin or max(pb) < min(pa) - margin


def triangles_sat_intersect(a, b):
    ea = [sub(a[1], a[0]), sub(a[2], a[1]), sub(a[0], a[2])]
    eb = [sub(b[1], b[0]), sub(b[2], b[1]), sub(b[0], b[2])]
    na = cross(ea[0], sub(a[2], a[0]))
    nb = cross(eb[0], sub(b[2], b[0]))
    axes = [na, nb]
    axes.extend(cross(x, y) for x in ea for y in eb)
    # In-plane edge normals are required for coplanar triangle separation.
    axes.extend(cross(na, x) for x in ea)
    axes.extend(cross(nb, x) for x in eb)
    return not any(separated(a, b, axis) for axis in axes)


def aabb_overlap(a, b):
    return all(a["hi"][k] >= b["lo"][k] - TOL and
               b["hi"][k] >= a["lo"][k] - TOL for k in range(3))


def screen(left, right, same_mesh=False):
    right_sorted = sorted(right, key=lambda x: x["lo"][0])
    aabb_candidates = 0
    tested = 0
    intersections = []
    for a in sorted(left, key=lambda x: x["lo"][0]):
        for b in right_sorted:
            if b["lo"][0] > a["hi"][0] + TOL:
                break
            if b["hi"][0] < a["lo"][0] - TOL or not aabb_overlap(a, b):
                continue
            aabb_candidates += 1
            shared = len(set(a["ids"]) & set(b["ids"]))
            if same_mesh and (b["index"] <= a["index"] or shared > 0):
                continue
            tested += 1
            if triangles_sat_intersect(a["pts"], b["pts"]):
                intersections.append((a, b, shared))
    return aabb_candidates, tested, intersections


def all_triangles(vertices, faces):
    return [tri_record(i, f, vertices) for i, f in enumerate(faces)]


def classify_contacts(intersections):
    top = apex = other = 0
    for a, b, _ in intersections:
        atop = all(abs(p[2] - 1.71) <= 1e-12 for p in a["pts"])
        btop = all(abs(p[2] - 1.71) <= 1e-12 for p in b["pts"])
        a_apex = any(math.dist(p, (0.0, 0.0, 0.0)) <= 1e-12 for p in a["pts"])
        b_apex = any(math.dist(p, (0.0, 0.0, 0.0)) <= 1e-12 for p in b["pts"])
        if atop or btop:
            top += 1
        elif a_apex and b_apex:
            apex += 1
        else:
            other += 1
    return {"top_plane_pairs": top, "common_apex_pairs": apex, "other_pairs": other}


def run(root: Path):
    meshes, identities = {}, {}
    for name, rel in FILES.items():
        raw = (root / rel).read_bytes()
        blob = git_blob_sha1(raw)
        if blob != BLOBS[name]:
            raise ValueError(f"{name}: source Git blob SHA1 mismatch: {blob}")
        v, f = parse_obj(raw, name)
        meshes[name] = all_triangles(v, f)
        identities[name] = {"git_blob_sha1": blob, "vertices": len(v), "faces": len(f)}
    M, D, S = (meshes[k] for k in ("M", "D", "S"))
    checks = {}
    for name, mesh in (("M", M), ("D", D), ("S", S)):
        aa, tested, hits = screen(mesh, mesh, same_mesh=True)
        checks[name + "_self"] = {
            "aabb_candidates": aa, "nonincident_pairs_tested": tested,
            "sat_intersections": len(hits),
        }
    for label, a, b in (("M_D", M, D), ("D_S", D, S), ("M_S", M, S)):
        aa, tested, hits = screen(a, b)
        row = {"aabb_candidates": aa, "pairs_tested": tested,
               "sat_intersections": len(hits)}
        if label == "M_S":
            row["contact_localization"] = classify_contacts(hits)
        checks[label] = row
    return {
        "schema": "W4_P32_FLOATING_POINT_TRIANGLE_SCREEN_V1",
        "status": "DIAGNOSTIC_SCREEN_ONLY_NOT_ROBUST_CERTIFICATE",
        "tolerance": TOL, "axis_epsilon": AXIS_EPS,
        "sources": identities, "checks": checks,
        "scientific_admission": False,
        "robust_solid_containment_certified": False,
        "printability_certified": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run(args.repo.resolve())
    rendered = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()

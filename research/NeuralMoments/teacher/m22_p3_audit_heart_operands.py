#!/usr/bin/env python3
"""Reproduce exact self-intersection and signed-volume audit of Heart Boolean operands.

This is a source-bound offline audit. It does not rerun Cherchi and does not
prove global Boolean set equality or derivative continuity.
"""
from __future__ import annotations
import argparse
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

H8F_SHA = "99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9"
M21_SHA = "259b9f288b629415bafa42e4e09d6503e4f474e0e2253e6cc9eb1cd775a64dfd"
REQUEST_SHA = "1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c"
POINT000_MEMBER = "artifacts/h8f-all81-points/point-000-material.json.gz"
POINT000_GZIP_SHA = "c372f749bf7b85015e2dcdad4a445aeab4f2f6fbd25d622089ec58d471992973"
M26_SOURCE_SHA = "2536f7783ff6552ac930c294879e69b8430fc8e527873859b3ec1187d39c6ea0"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rational_from_binary64(value) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("EXPECTED_BINARY64_COORDINATE")
    return Fraction.from_float(float(value))


def token(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def rational_coordinate(value) -> Fraction:
    if isinstance(value, str):
        return Fraction(value)
    return rational_from_binary64(value)


def exact_volume(vertices, faces) -> Fraction:
    points = [tuple(rational_coordinate(x) for x in row) for row in vertices]
    total = Fraction(0)
    for face in faces:
        if len(face) != 3:
            raise ValueError("TRIANGLE_REQUIRED")
        i, j, k = face
        if min(i, j, k) < 0 or max(i, j, k) >= len(points) or len({i, j, k}) != 3:
            raise ValueError("BAD_FACE_INDEX")
        a, b, c = points[i], points[j], points[k]
        det = (a[0]*(b[1]*c[2]-b[2]*c[1])
             + a[1]*(b[2]*c[0]-b[0]*c[2])
             + a[2]*(b[0]*c[1]-b[1]*c[0]))
        total += det / 6
    return total


def make_checker_input(vertices, faces, path: Path) -> str:
    if len(vertices) < 4 or len(faces) < 4:
        raise ValueError("CLOSED_SOLID_REQUIRED")
    with path.open("w", encoding="ascii", newline="\n") as stream:
        stream.write(f"{len(vertices)} {len(faces)}\n")
        for row in vertices:
            stream.write(" ".join(token(rational_coordinate(x)) for x in row) + "\n")
        for row in faces:
            if len(row) != 3:
                raise ValueError("TRIANGLE_REQUIRED")
            stream.write(" ".join(str(int(x)) for x in row) + "\n")
    return sha256(path.read_bytes())


def parse_checker_output(text: str, returncode: int) -> dict:
    values = {}
    for line in text.splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    if returncode != 0 or values.get("status") != "EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE":
        raise ValueError("EXACT_SURFACE_SELF_INTERSECTION_CHECK_FAILED:" + text.strip())
    required = ("vertices", "faces", "candidate_pairs", "exact_pairs_checked",
                "adjacent_pairs", "nonadjacent_pairs", "elapsed_seconds")
    if any(k not in values for k in required):
        raise ValueError("CHECKER_OUTPUT_INCOMPLETE")
    return {
        "status": values["status"],
        "vertices": int(values["vertices"]),
        "faces": int(values["faces"]),
        "candidate_pairs": int(values["candidate_pairs"]),
        "exact_pairs_checked": int(values["exact_pairs_checked"]),
        "adjacent_pairs": int(values["adjacent_pairs"]),
        "nonadjacent_pairs": int(values["nonadjacent_pairs"]),
        "elapsed_seconds": float(values["elapsed_seconds"]),
    }


def tarfile_open(path):
    import tarfile
    return tarfile.open(path, "r:gz")


def load_inputs(h8f_zip: Path, m21_tar: Path):
    if sha256(h8f_zip.read_bytes()) != H8F_SHA:
        raise ValueError("H8F_ARCHIVE_SHA_MISMATCH")
    if sha256(m21_tar.read_bytes()) != M21_SHA:
        raise ValueError("M21_ARCHIVE_SHA_MISMATCH")
    with zipfile.ZipFile(h8f_zip) as archive:
        request_raw = archive.read("artifacts/h8-request/prepared-request.json")
        if sha256(request_raw) != REQUEST_SHA:
            raise ValueError("FROZEN_REQUEST_SHA_MISMATCH")
        prepared = json.loads(request_raw)
        member = archive.read(POINT000_MEMBER)
        if sha256(member) != POINT000_GZIP_SHA:
            raise ValueError("POINT000_MEMBER_SHA_MISMATCH")
        point0 = json.loads(gzip.decompress(member))
    import tarfile
    with tarfile.open(m21_tar, "r:gz") as archive:
        spec_member = next((x for x in archive.getmembers()
                            if x.name.endswith("/M21_PILOT_SPEC.json")), None)
        if spec_member is None:
            raise ValueError("M21_SPEC_MISSING")
        spec = json.load(archive.extractfile(spec_member))
    if prepared.get("request") != spec.get("request"):
        raise ValueError("M21_REQUEST_NOT_SEMANTICALLY_BOUND_TO_H8F_REQUEST")
    return prepared["request"], point0


def audit(h8f_zip: Path, m21_tar: Path, checker_source: Path,
          output: Path, timeout: int = 600) -> dict:
    if sha256(checker_source.read_bytes()) != M26_SOURCE_SHA:
        raise ValueError("M26_CHECKER_SOURCE_SHA_MISMATCH")
    request, point0 = load_inputs(h8f_zip, m21_tar)
    surfaces = {
        "design": (request["design_vertices"], request["design_faces"]),
        "quadric_source": (point0["quadric_source_vertices"], point0["quadric_source_faces"]),
        "boolean_output": (point0["variable_rational_vertices"], point0["variable_faces"]),
    }
    with tempfile.TemporaryDirectory(prefix="w2-m22-m26-build-") as tmp:
        tmp = Path(tmp)
        binary = tmp / "m26_exact_intersection"
        build = subprocess.run([
            "g++", "-std=c++17", "-O2", "-Wall", "-Wextra",
            "-Wno-deprecated-declarations", str(checker_source), "-o", str(binary),
            "-lgmpxx", "-lgmp"], capture_output=True, text=True, timeout=180)
        if build.returncode:
            raise RuntimeError("M26_BUILD_FAILED:" + build.stderr[-4000:])
        results = {}
        for name, (vertices, faces) in surfaces.items():
            stream = tmp / f"{name}.m26"
            stream_sha = make_checker_input(vertices, faces, stream)
            run = subprocess.run([str(binary), "--max-seconds", str(timeout)],
                                 input=stream.read_bytes(), capture_output=True,
                                 timeout=timeout + 30)
            result = parse_checker_output(run.stdout.decode("utf-8", "replace"), run.returncode)
            volume = exact_volume(vertices, faces)
            result.update({
                "input_stream_sha256": stream_sha,
                "signed_volume_exact": token(volume),
                "signed_volume_binary64": float(volume),
                "positive_orientation": volume > 0,
            })
            results[name] = result
    if not all(v["positive_orientation"] for v in results.values()):
        raise ValueError("SURFACE_ORIENTATION_NOT_POSITIVE")
    design_volume = Fraction(results["design"]["signed_volume_exact"])
    output_volume = Fraction(results["boolean_output"]["signed_volume_exact"])
    report = {
        "schema": "w2-m22-p3-heart-operand-embedding-audit-v1",
        "status": "DESIGN_QUADRIC_AND_OUTPUT_EMBEDDED_SURFACE_CHECKS_PASS",
        "h8f_archive_sha256": H8F_SHA,
        "m21_archive_sha256": M21_SHA,
        "prepared_request_sha256": REQUEST_SHA,
        "point000_member_sha256": POINT000_GZIP_SHA,
        "m26_checker_source_sha256": M26_SOURCE_SHA,
        "m26_checker_binary_rebuilt": True,
        "surfaces": results,
        "volume_accounting": {
            "design_volume_exact": token(design_volume),
            "quadric_source_volume_exact": results["quadric_source"]["signed_volume_exact"],
            "boolean_output_volume_exact": token(output_volume),
            "design_minus_output_volume_exact": token(design_volume-output_volume),
            "design_volume_binary64": float(design_volume),
            "quadric_source_volume_binary64": results["quadric_source"]["signed_volume_binary64"],
            "output_volume_binary64": float(output_volume),
            "removed_design_volume_binary64": float(design_volume-output_volume),
            "note": "The global QuadricSource volume is not subtracted from Design volume; the QuadricSource extends outside Design. This bookkeeping is not a proof of Boolean set equality."
        },
        "scope": "exact rational self-intersection audit of Design, QuadricSource and Boolean output surfaces, plus exact signed-volume orientation",
        "not_proven": [
            "global Boolean set equality",
            "complete M21 same-call material object provenance",
            "continuous derivative neighborhood or Jacobian",
            "Newton convergence",
            "training admission"
        ],
        "new_cherchi_calls": 0,
        "J_D": None,
        "split": "excluded",
        "training_admitted": False,
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h8f-zip", type=Path, required=True)
    parser.add_argument("--m21-tar", type=Path, required=True)
    parser.add_argument("--m26-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("REFUSE_OVERWRITE_EXISTING_AUDIT")
    try:
        result = audit(args.h8f_zip, args.m21_tar, args.m26_source, args.output, args.timeout)
    except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile,
            json.JSONDecodeError, subprocess.SubprocessError, RuntimeError) as exc:
        parser.exit(2, "M22 operand audit blocked: " + str(exc) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()

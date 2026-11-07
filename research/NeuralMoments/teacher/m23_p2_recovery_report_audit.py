"""Read-only, fail-closed M23-P2 audit of a user-host Noodles recovery scan.

Accepts `find /data` + sha256sum text. The report is untrusted evidence of
filename checksums, NOT access to the local JSON bytes. No training release.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

PACKETS = {
    "design-rational.json": "48e8d3008bba746823eafd9c3704b52d597595b802066450a921ecc0dcb7f611",
    "envelope-rational.json": "92f46d68025467961fcc8b2b52353b4a18c2a981a09ad654ad6af3fb128b73fd",
    "fixed-rational.json": "71f9df91fca12fde4f4f2c80dc26e2d1229e8209e09db46e680d0de7baee264a",
    "fixed-inside-envelope-rational.json": "a944da4e36e5fe386cee3b28e4acf5800fc3942cde4eb35ba54f5de626f55dc7",
    "fixed-outside-envelope-rational.json": "8c66f71da99773fbc9a76b4f82fc43c55816df1876b643634ae64768f72ba262",
    "initial-rational.json": "640877647134a54152a8e1f63c1f356d752e6c66f7913301580c1e85a356d83b",
}
HISTORICAL_BACKEND_SHA = "d6803f184047f6172b177b9f436b16f22cdb6a949126d1df88a5d084f3dd9df3"
SUM_LINE = re.compile(r"^([0-9a-f]{64})  (/.+)$")


def audit_report(text: str, *, actual_files: bool = False) -> dict:
    records = []
    backend = []
    archives = []
    section = ""
    pending = None

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("====="):
            if pending is not None:
                raise ValueError("FOUND_PATH_MISSING_SHA:" + pending["path"])
            if "六份精确材料" in line:
                section = "materials"
            elif "原始 CGAL 后端" in line:
                section = "backend"
            elif "Noodles 历史压缩包" in line:
                section = "archives"
            continue

        if line.startswith("FOUND: "):
            if section != "materials" or pending is not None:
                raise ValueError("INVALID_FOUND_LINE")
            path = line.removeprefix("FOUND: ").strip()
            name = Path(path).name
            if not path.startswith("/") or name not in PACKETS:
                raise ValueError("UNEXPECTED_MATERIAL_PATH")
            pending = {"path": path, "name": name}
            continue

        m = SUM_LINE.fullmatch(line)
        if pending is not None:
            if m is None or m.group(2) != pending["path"]:
                raise ValueError("FOUND_CHECKSUM_BINDING_INVALID")
            pending["reported_sha256"] = m.group(1)
            pending["historical_sha256"] = PACKETS[pending["name"]]
            pending["sha_matches_historical"] = (m.group(1) == PACKETS[pending["name"]])
            if actual_files:
                p = Path(pending["path"])
                if not p.is_file():
                    raise ValueError("LOCAL_FILE_UNAVAILABLE:" + str(p))
                h = hashlib.sha256()
                with p.open("rb") as fh:
                    for chunk in iter(lambda: fh.read(1024*1024), b""):
                        h.update(chunk)
                if h.hexdigest() != m.group(1):
                    raise ValueError("LOCAL_FILE_DIFFERS_FROM_REPORT:" + str(p))
            pending["verification"] = ("LOCAL_BYTES_REHASHED" if actual_files
                                       else "TEXT_REPORT_ONLY_NOT_LOCAL_BYTES")
            records.append(pending)
            pending = None
            continue
        if section == "backend":
            if line.startswith("BACKEND: "):
                backend.append({"path": line.removeprefix("BACKEND: ").strip(),
                                "historical_backend_match": False})
            elif m:
                if not backend or m.group(2) != backend[-1]["path"]:
                    raise ValueError("BACKEND_CHECKSUM_BINDING_INVALID")
                backend[-1]["reported_sha256"] = m.group(1)
                backend[-1]["historical_backend_match"] = (m.group(1) == HISTORICAL_BACKEND_SHA)
            else:
                raise ValueError("UNKNOWN_BACKEND_LINE")
            continue
        if section == "archives":
            archives.append(line)
            continue
        raise ValueError("UNEXPECTED_REPORT_LINE:" + line[:70])

    if pending is not None:
        raise ValueError("UNFINISHED_MATERIAL_RECORD")
    if section != "archives":
        raise ValueError("TRUNCATED_REPORT_SECTIONS")

    groups = {}
    for rec in records:
        groups.setdefault(rec["name"], []).append(rec)
    summary = {}
    for name, target in PACKETS.items():
        rows = groups.get(name, [])
        summary[name] = {
            "expected_sha256": target,
            "status": ("FOUND_MATCH" if any(x["sha_matches_historical"] for x in rows)
                       else "FOUND_DIFFERENT_SHA" if rows else "NOT_REPORTED"),
            "candidates": rows,
        }

    matches = sum(x["status"] == "FOUND_MATCH" for x in summary.values())
    return {
        "schema": "w2-m23-p2-noodles-host-recovery-report-audit-v1",
        "status": "HISTORICAL_SIX_PACKET_BYTES_NOT_VERIFIED",
        "source_scope": "USER_HOST_FIND_REPORT; NO_CLAIM_OF_EXHAUSTIVE_ARCHIVE_SEARCH",
        "scan_report_is_not_original_material": True,
        "local_bytes_rehashed": actual_files,
        "historical_exact_matches_by_report": matches,
        "historical_exact_matches_independently_rehashed": matches if actual_files else 0,
        "found_candidate_count": len(records),
        "unreported_names": [name for name, item in summary.items()
                             if item["status"] == "NOT_REPORTED"],
        "packets": summary,
        "backend_candidates": backend,
        "backend_historical_sha_matches_by_report": sum(
            bool(x["historical_backend_match"]) for x in backend),
        "archive_candidates_reported": archives,
        "historical_fixed_backend_restored": False,
        "new_CGAL_calls": 0,
        "new_Cherchi_calls": 0,
        "J_D": None,
        "split": "excluded",
        "training_samples": 0,
        "training_admitted": False,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--verify-local-files", action="store_true")
    args = ap.parse_args()
    if args.out.exists():
        ap.error("REFUSE_OVERWRITE_EXISTING_OUTPUT")
    res = audit_report(args.report.read_text(encoding="utf-8"),
                       actual_files=args.verify_local_files)
    args.out.write_text(json.dumps(res, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "status": res["status"], "candidate_count": res["found_candidate_count"],
        "historical_sha_matches": res["historical_exact_matches_by_report"],
        "local_bytes_rehashed": res["local_bytes_rehashed"],
        "training_samples": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()

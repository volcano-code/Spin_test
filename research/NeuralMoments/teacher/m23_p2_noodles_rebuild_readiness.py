#!/usr/bin/env python3
"""Fail-closed readiness audit for a fresh, separately identified Noodles V7 CSG rebuild.

The historical exact packet bodies are absent from the GitHub text checkpoint.
This tool verifies whether a local source checkout has all prerequisites to run
the frozen 96-operation builder. It never launches CGAL or Cherchi.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path

EXPECTED_SOURCE_MANIFEST_SHA = "67364abba55c74ccd377eef6174b8c96ee04e4af1aadbd7e505466bafabd2a3a"
EXPECTED_BACKEND_SHA = "d6803f184047f6172b177b9f436b16f22cdb6a949126d1df88a5d084f3dd9df3"
EXPECTED_PARTS = 94
EXPECTED_FIXED = 93
EXPECTED_OPERATIONS = 96
REQUIRED_OUTPUTS = (
    "fixed-rational.json", "envelope-rational.json", "design-rational.json",
    "initial-rational.json", "fixed-inside-envelope-rational.json",
    "fixed-outside-envelope-rational.json",
)
REQUIRED_SOURCE_FILES = ("common.py", "build_exact_v7.py", "prove_v7_chain.py")
REQUIRED_EXTERNAL_FILES = ("exact_planar_patches.py",)


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def audit(source: Path, output: Path, backend: Path, external_code: Path,
          source_audit: Path, free_bytes: int) -> dict:
    errors=[]
    manifest_path=source/"manifest.json"
    manifest=None
    if not manifest_path.is_file():
        errors.append("SOURCE_MANIFEST_MISSING")
    else:
        manifest=json.loads(manifest_path.read_text())
        if sha(manifest_path)!=EXPECTED_SOURCE_MANIFEST_SHA:
            errors.append("SOURCE_MANIFEST_SHA_MISMATCH")
        if manifest.get("spec",{}).get("schema")!="noodles-paper-photo-hypothesis-v7":
            errors.append("SOURCE_SCHEMA_MISMATCH")
        parts=manifest.get("parts",{})
        recipe=manifest.get("construction",{})
        if len(parts)!=EXPECTED_PARTS:
            errors.append("SOURCE_PART_COUNT_MISMATCH")
        if len(recipe.get("fixed_parts",[]))!=EXPECTED_FIXED:
            errors.append("FIXED_PART_COUNT_MISMATCH")
        for name,item in parts.items():
            p=source/item["model_obj"]
            if not p.is_file():
                errors.append("SOURCE_MODEL_MISSING:"+name)
            elif sha(p)!=item["sha256_model"]:
                errors.append("SOURCE_MODEL_SHA_MISMATCH:"+name)
            si=source/item.get("si_obj","")
            if not si.is_file():
                errors.append("SOURCE_SI_MODEL_MISSING:"+name)
            elif sha(si)!=item.get("sha256_si"):
                errors.append("SOURCE_SI_MODEL_SHA_MISMATCH:"+name)

    repo_root=source.parent
    source_root=repo_root/"source"
    for name in REQUIRED_SOURCE_FILES:
        if not (source_root/name).is_file():
            errors.append("REQUIRED_BUILDER_SOURCE_MISSING:"+str(source_root/name))
    for name in REQUIRED_EXTERNAL_FILES:
        if not (external_code/name).is_file():
            errors.append("REQUIRED_EXACT_CHAIN_DEPENDENCY_MISSING:"+str(external_code/name))

    if not backend.is_file():
        errors.append("PINNED_CGAL_BACKEND_MISSING")
        backend_sha=None
    else:
        backend_sha=sha(backend)
        if backend_sha!=EXPECTED_BACKEND_SHA:
            errors.append("PINNED_CGAL_BACKEND_SHA_MISMATCH")
        if not shutil.which("ldd"):
            errors.append("LDD_UNAVAILABLE")
        else:
            import subprocess
            p=subprocess.run(["ldd",str(backend)],capture_output=True,text=True)
            if "not found" in p.stdout or "not found" in p.stderr:
                errors.append("CGAL_BACKEND_UNRESOLVED_SHARED_LIBRARY")

    if not source_audit.is_file():
        errors.append("94_PART_SOURCE_AUDIT_MISSING")
    else:
        a=json.loads(source_audit.read_text())
        if a.get("full_source_parts_passed") is not True or a.get("parts_completed")!=EXPECTED_PARTS:
            errors.append("94_PART_SOURCE_AUDIT_NOT_PASS")
    if free_bytes < 24*(1024**3):
        errors.append("FREE_DISK_BELOW_24_GIB_REBUILD_RESERVE")

    existing={name:{"exists":(output/name).is_file(),
                    "sha256":sha(output/name) if (output/name).is_file() else None}
              for name in REQUIRED_OUTPUTS}
    ready=not errors
    return {
      "schema":"w2-m23-p2-noodles-v7-rebuild-readiness-v1",
      "status":"READY_FOR_LOCAL_96_OP_REBUILD" if ready else "BLOCKED_PREREQUISITES_INCOMPLETE",
      "source_manifest_sha256":sha(manifest_path) if manifest_path.is_file() else None,
      "expected_source_manifest_sha256":EXPECTED_SOURCE_MANIFEST_SHA,
      "source_parts_expected":EXPECTED_PARTS,
      "fixed_parts_expected":EXPECTED_FIXED,
      "csg_operations_expected":EXPECTED_OPERATIONS,
      "backend_path":str(backend),
      "backend_sha256":backend_sha,
      "expected_backend_sha256":EXPECTED_BACKEND_SHA,
      "builder_source_files":{n:(source_root/n).is_file() for n in REQUIRED_SOURCE_FILES},
      "external_dependencies":{n:(external_code/n).is_file() for n in REQUIRED_EXTERNAL_FILES},
      "source_audit_path":str(source_audit),
      "source_audit_present":source_audit.is_file(),
      "free_disk_bytes":free_bytes,
      "minimum_free_disk_bytes":24*(1024**3),
      "historical_packet_outputs":existing,
      "errors":errors,
      "cgal_launched":False,
      "cherchi_launched":False,
      "training_admitted":False,
      "J_D":None,
      "split":"excluded"
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=Path,required=True,help="directory with frozen 94 source-part OBJ files and manifest.json")
    ap.add_argument("--output",type=Path,required=True,help="exact_v7c output directory")
    ap.add_argument("--backend",type=Path,required=True,help="pinned historical CGAL executable")
    ap.add_argument("--external-code",type=Path,required=True,help="directory containing exact_planar_patches.py")
    ap.add_argument("--source-audit",type=Path,required=True)
    ap.add_argument("--free-bytes",type=int,required=True,help="current free bytes on target filesystem")
    ap.add_argument("--report",type=Path,required=True)
    args=ap.parse_args()
    if args.report.exists(): ap.error("REFUSE_OVERWRITE_EXISTING_REPORT")
    result=audit(args.source,args.output,args.backend,args.external_code,args.source_audit,args.free_bytes)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"status":result["status"],"errors":len(result["errors"]),
                      "missing_outputs":sum(not x["exists"] for x in result["historical_packet_outputs"].values()),
                      "cgal_launched":False,"cherchi_launched":False},sort_keys=True))
    return 0 if result["status"]=="READY_FOR_LOCAL_96_OP_REBUILD" else 2

if __name__=="__main__":
    raise SystemExit(main())

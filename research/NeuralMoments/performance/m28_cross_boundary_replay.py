#!/usr/bin/env python3
"""M28.2 exact cross-boundary audit of saved Cherchi output triangles."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, time
from pathlib import Path
from zipfile import ZipFile
import importlib.util

ARCHIVE_SHA="0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976"
EXPECTED_OPS={4:"intersection",116:"difference",117:"difference",123:"difference"}

def sha(b): return hashlib.sha256(b).hexdigest()
def load_m28(path):
    spec=importlib.util.spec_from_file_location("m28_saved_boolean_set_semantics",path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def mesh_stream(mesh):
    vertices,faces=mesh
    lines=[f"{len(vertices)} {len(faces)}"]
    for v in vertices: lines.append(" ".join(f"{x.numerator}/{x.denominator}" for x in v))
    lines.extend(" ".join(map(str,f)) for f in faces)
    return "\n".join(lines)+"\n"

def combined_stream(output,other):
    ov,of=output;bv,bf=other
    lines=[f"{len(ov)} {len(of)} {len(bv)} {len(bf)}"]
    for v in ov:lines.append(" ".join(f"{x.numerator}/{x.denominator}" for x in v))
    lines.extend(" ".join(map(str,f)) for f in of)
    for v in bv:lines.append(" ".join(f"{x.numerator}/{x.denominator}" for x in v))
    lines.extend(" ".join(map(str,f)) for f in bf)
    return "\n".join(lines)+"\n"

def run_one(index,owner,archive,m28_path,certificate,binary,output_path,max_seconds=300):
    archive=Path(archive).resolve(strict=True);raw=archive.read_bytes()
    if sha(raw)!=ARCHIVE_SHA:raise ValueError("ORIGINAL_ARCHIVE_SHA_MISMATCH")
    m28=load_m28(m28_path)
    _,cert_points,cert_sha=m28.load_m26_certificate(certificate,ARCHIVE_SHA)
    with ZipFile(archive) as z:
        manifest=json.loads(z.read("material-evidence-manifest.json"))
        for item in manifest["files"]:
            b=z.read(item["file"])
            if len(b)!=item["bytes"] or sha(b)!=item["sha256"]:raise ValueError("ARCHIVE_MEMBER_MANIFEST_MISMATCH:"+item["file"])
        design=m28.load_mesh(json.loads(z.read("physical-design-input.json")))
        source_doc=json.loads(z.read(f"physical-source-input-{index:06d}.json"))
        source=m28.load_mesh(source_doc)
        operation=source_doc["boolean_operation"]
        if operation!=EXPECTED_OPS[index]:raise ValueError("OPERATION_MISMATCH")
        packet_bytes=z.read(f"boolean-packet-{index:06d}.json")
        packet_doc=json.loads(packet_bytes);output=m28.load_packet(packet_doc)
        point_doc=json.loads(z.read(f"point-{index:06d}.json"))
        packet_raw=z.read(point_doc["raw_packet_file"])
        if sha(packet_raw)!=point_doc["raw_packet_sha256"]:raise ValueError("RAW_PACKET_SHA_MISMATCH")
        cert=m28.verify_m26_point_certificate(index,operation,output,sha(packet_raw),cert_points[index])
        if index==123:raise ValueError("EMPTY_OUTPUT_HAS_NO_TRIANGLES_TO_CROSS_AUDIT")
        design_index=m28.PlaneIndex(design);source_index=m28.PlaneIndex(source)
        selected=[];owner_face_counts={"design":0,"source":0}
        for fi,face in enumerate(output[1]):
            tri=tuple(output[0][k] for k in face)
            dm=design_index.locate(tri);sm=source_index.locate(tri)
            if dm and sm:raise ValueError(f"FACE_{fi}_AMBIGUOUS_BOTH_INPUTS")
            if len(dm)>1 or len(sm)>1:raise ValueError(f"FACE_{fi}_MULTIPLE_INPUT_OWNERS")
            if not dm and not sm:raise ValueError(f"FACE_{fi}_NO_INPUT_OWNER")
            actual="design" if dm else "source"
            if actual==owner:
                selected.append(face);owner_face_counts[actual]+=1
        other=source if owner=="design" else design
        if not selected:raise ValueError("NO_OUTPUT_FACES_FOR_OWNER")
        stream=combined_stream((output[0],selected),other)
        started=time.monotonic()
        proc=subprocess.run([str(Path(binary).resolve(strict=True)),"--max-seconds",str(max_seconds)],
            input=stream,text=True,capture_output=True,timeout=max_seconds+10)
        elapsed=time.monotonic()-started
        lines=proc.stdout.splitlines();fields={}
        for line in lines:
            if "=" in line:
                k,v=line.split("=",1)
                try:fields[k]=int(v)
                except ValueError:
                    try:fields[k]=float(v)
                    except ValueError:fields[k]=v
        status=fields.get("status","NO_STATUS")
        report={"schema":"w1-m28-cross-boundary-replay-v1","evaluation":index,"operation":operation,
            "output_owner":owner,"opposite_operand":"source" if owner=="design" else "design",
            "archive_sha256":ARCHIVE_SHA,"m26_certificate_sha256":cert_sha,
            "raw_packet_sha256":sha(packet_raw),"output_packet_sha256":sha(packet_bytes),
            "output_vertices":len(output[0]),"output_faces_total":len(output[1]),
            "output_faces_tested":len(selected),"owner_face_counts":owner_face_counts,
            "m26_certificate_reused":cert["repeated_expensive_surface_audit"] is False,
            "new_boolean_calls":0,"new_newton_runs":0,"wall_seconds":elapsed,
            "returncode":proc.returncode,"checker":fields,"stderr":proc.stderr[-2000:],
            "status":status,"passed":proc.returncode==0 and status=="EXACT_NO_INTERIOR_CROSS_BOUNDARY_INTERSECTION",
            "production_admitted":False,"full_triangle_interior_cross_boundary_tested":proc.returncode==0 and status=="EXACT_NO_INTERIOR_CROSS_BOUNDARY_INTERSECTION",
            "full_solver_speedup":None}
        out=Path(output_path);out.parent.mkdir(parents=True,exist_ok=True);m28.atomic_json(out,report)
        print(json.dumps({"status":status,"evaluation":index,"owner":owner,"faces":len(selected),
            "candidate_pairs":fields.get("candidate_pairs"),"exact_pairs_checked":fields.get("exact_pairs_checked"),
            "wall_seconds":elapsed,"output":str(out)},indent=2),flush=True)
        return report

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--archive",required=True);p.add_argument("--m28",required=True)
    p.add_argument("--certificate",required=True);p.add_argument("--binary",required=True);p.add_argument("--output",required=True)
    p.add_argument("--evaluation",type=int,choices=(4,116,117),required=True);p.add_argument("--owner",choices=("design","source"),required=True)
    p.add_argument("--max-seconds",type=int,default=300);a=p.parse_args()
    r=run_one(a.evaluation,a.owner,a.archive,a.m28,a.certificate,a.binary,a.output,a.max_seconds)
    raise SystemExit(0 if r["passed"] else (2 if r["returncode"] else 3))
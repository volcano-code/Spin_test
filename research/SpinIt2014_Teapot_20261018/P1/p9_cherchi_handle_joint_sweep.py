#!/usr/bin/env python3
"""W4 P9: controlled handle-joint perturbation using Cherchi ONLY.

This is a deliberate, source-deviating experiment in UNITLESS OBJ coordinates.
No original mesh is modified. Never claim author-exact teapot, shape preserving
exactly, Cherchi optimization, W0/W2 admission or a real printed object.
The two native unions are the pinned Cherchi 7bd6c269 reference executable.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import time
import numpy as np
import trimesh
from p7_cherchi_native_union import (validate_input,native_identity,write_obj,sha,
                                     moments_crosscheck)
from p8_cherchi_union_forensics import run_case,inspect_obj

SCHEMA="W4P9ControlledHandleClearanceExperimentV1"
SHIFTS=(0.0,0.0005,0.002,0.005,0.01,-0.0005,-0.002,-0.005)
MAX_SHIFT_ABS=0.01


def translated_handle(mesh,delta):
    delta=float(delta)
    if not np.isfinite(delta) or abs(delta)>MAX_SHIFT_ABS:
        raise ValueError("HANDLE_SHIFT_EXCEEDS_EXPLICIT_LIMIT")
    vv=np.asarray(mesh.vertices,dtype=np.float64).copy()
    f=np.asarray(mesh.faces,dtype=np.int64).copy()
    vv[:,0]+=delta
    moved=trimesh.Trimesh(vertices=vv,faces=f,process=False)
    if not moved.is_volume or len(moved.faces)!=len(mesh.faces):
        raise ValueError("TRANSLATED_HANDLE_INVALID")
    max_error=float(np.max(np.linalg.norm(vv-np.asarray(mesh.vertices),axis=1)))
    if max_error>abs(delta)+1e-12:
        raise ValueError("TRANSLATION_EXCEEDS_DECLARED_DISPLACEMENT")
    return moved,max_error


def run(p0,p1,binary,source,out,*,timeout=120,shifts=SHIFTS):
    p0,p1,binary,source,out=map(Path,(p0,p1,binary,source,out))
    if not 0<timeout<=240:raise ValueError("INVALID_NATIVE_TIMEOUT")
    if not shifts or len(set(map(float,shifts)))!=len(shifts):
        raise ValueError("INVALID_SHIFT_SWEEP")
    parts=validate_input(p0,p1)
    if not (parts[1].bounds[0,0]>0 and parts[2].bounds[1,0]<0):
        raise ValueError("SOURCE_COMPONENT_LABELS_NOT_SPout_AND_HANDLE")
    identity=native_identity(binary,source)
    out.mkdir(parents=True,exist_ok=True)
    body=out/"body-p1-unchanged.obj"
    spout=out/"spout-p1-unchanged.obj"
    write_obj(body,parts[0]);write_obj(spout,parts[1])
    journal=dict(schema=SCHEMA,status="RUNNING",
                 native=identity,source_sha256=sha(p0),topology_candidate_sha256=sha(p1),
                 source_meshes_unchanged=True,
                 input_body_face_count=len(parts[0].faces),
                 input_spout_face_count=len(parts[1].faces),
                 input_handle_face_count=len(parts[2].faces),
                 physical_units="NOT_DEFINED_BY_W0",
                 original_paper_CAD=False,exact_source_conformance=False,
                 geometry_deviation_is_intentional=True,
                 W0_F_D_partition_certified=False,W2_teacher_admitted=False,
                 actual_optimization_performed=False,
                 trials=[],accepted_candidates=[],
                 recommended_candidate=None)
    path=out/"p9-source-deviation-sweep.json"
    def save():path.write_text(json.dumps(journal,indent=2,allow_nan=False)+"\n")
    save()
    src,src_path=run_case("body-spout-authenticated",[body,spout],binary,out,timeout)
    journal["body_spout_stage"]=src
    save()
    if src["geometry_status"]!="NUMERIC_SURFACE_PASS":
        journal["status"]="BLOCKED_PRECURSOR_BODY_SPOUT_NOT_VALID"
        save()
        return journal
    body_spout,first_geom=inspect_obj(src_path)
    bvolume=float(body_spout.volume)
    origin_volume=float(parts[0].volume+parts[1].volume+parts[2].volume)
    full_bounds=np.ptp(np.vstack([x.vertices for x in parts]),axis=0)
    diagonal=float(np.linalg.norm(full_bounds))
    if diagonal<=0:raise ValueError("INVALID_SOURCE_DIAGONAL")
    for order,raw_shift in enumerate(shifts):
        shift=float(raw_shift)
        handle,error=translated_handle(parts[2],shift)
        handle_path=out/f"handle-shift-{order:02d}.obj"
        write_obj(handle_path,handle)
        trial,probe_path=run_case(f"cherchi-body-spout-handle-{order:02d}",
                                  [src_path,handle_path],binary,out,timeout)
        trial.update(shift_axis="SOURCE_X",shift_original_mesh_units=shift,
                     handle_max_vertex_displacement=error,
                     relative_source_diagonal_deviation=error/diagonal,
                     full_source_untouched=True,
                     type="COUNTERFACTUAL_GEOMETRY_PERTURBATION_NOT_REPAIR_CERTIFICATE")
        if trial["geometry_status"]=="NUMERIC_SURFACE_PASS":
            candidate,geometry=inspect_obj(probe_path)
            lo=bvolume-1e-6;hi=origin_volume+1e-6
            if not lo<=candidate.volume<=hi:
                trial["geometry_status"]="REJECTED_UNION_VOLUME_BOUNDS"
                trial["expected_volume_range"]=[lo,hi]
            else:
                try:
                    moments=moments_crosscheck(candidate)
                    trial["independent_moments"]=moments
                    trial["geometry_status"]="CHERCHI_NUMERIC_GEOMETRY_PASS_SOURCE_DEVIATED"
                    journal["accepted_candidates"].append(dict(
                        name=probe_path.name,obj_sha256=sha(probe_path),
                        shift=shift,relative_deviation=error/diagonal,
                        volume=float(candidate.volume),
                        input_body_spout_sha256=sha(src_path),
                        handle_sha256=sha(handle_path),
                        independent_ten_moments=moments["unit_density_raw_ten"]))
                except Exception as exc:
                    trial["geometry_status"]="REJECTED_TEN_MOMENT_INDEPENDENT_ORACLE"
                    trial["validation_failure"]=f"{type(exc).__name__}: {exc}"
        journal["trials"].append(trial)
        save()
    if journal["accepted_candidates"]:
        journal["accepted_candidates"].sort(key=lambda x:(abs(x["shift"]),x["shift"]<0))
        journal["recommended_candidate"]=journal["accepted_candidates"][0]
        journal["status"]="SOURCE_DEVIATING_CHERCHI_NUMERIC_CANDIDATE_AVAILABLE"
    else:
        journal["status"]="NO_CHERCHI_CLOSED_SOLID_WITHIN_DOCUMENTED_SHIFT_SWEEP"
    save()
    return journal


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--p0",required=True,type=Path)
    p.add_argument("--p1",required=True,type=Path)
    p.add_argument("--native-bin",required=True,type=Path)
    p.add_argument("--upstream-checkout",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--timeout",type=int,default=120)
    a=p.parse_args()
    result=run(a.p0,a.p1,a.native_bin,a.upstream_checkout,a.out,timeout=a.timeout)
    print(json.dumps(dict(status=result["status"],accepted_count=len(result["accepted_candidates"]),
                          recommended_candidate=result["recommended_candidate"],
                          trial_outcomes=[dict(shift=t["shift_original_mesh_units"],
                                               status=t["geometry_status"],
                                               bad_edges=t.get("geometry",{}).get("non_two_incidence_edges"),
                                               component_count=t.get("geometry",{}).get("index_components"))
                                          for t in result["trials"]]),indent=2))
    if not result["accepted_candidates"]:raise SystemExit(2)


if __name__=="__main__":main()

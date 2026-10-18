"""Build a static, NON-OPTIMIZED reconstructed Heart + shaft reference assembly.

This is not original Heart CAD or a Cherchi/Faster Newton output. The static
OpenSCAD Boolean prepares a reference model only; the formal dynamic Boolean
backend of the research project remains Cherchi.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "experiments/reconstructed_heart_top"))
from heart_top import heart_mesh

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def rod_mesh(sections=48):
    # The established stem_geometry.py rounded pin and upper-shaft profile,
    # resampled for a smoother static preview only.
    angles = np.linspace(-np.pi/2, 0, 7)
    profile = [(0,-.16)] + [(.025*np.cos(a), -.135+.025*np.sin(a)) for a in angles[1:]]
    profile += [(.065,-.03), (.065,2.25), (0,2.25)]
    result = trimesh.creation.revolve(np.asarray(profile), sections=sections)
    if result.volume < 0: result.invert()
    return result

def write_off(path, mesh):
    with Path(path).open("x") as stream:
        stream.write(f"OFF\n{len(mesh.vertices)} {len(mesh.faces)} 0\n")
        for xyz in mesh.vertices:
            stream.write(" ".join(format(float(x), ".17g") for x in xyz)+"\n")
        for row in mesh.faces:
            stream.write("3 "+" ".join(str(int(i)) for i in row)+"\n")

def write_obj(path, mesh):
    with Path(path).open("x") as stream:
        stream.write("# Reconstructed NON-OPTIMIZED Heart+shaft; mm; NOT Cherchi Newton terminal\n")
        for xyz in mesh.vertices:
            stream.write("v "+" ".join(format(float(x), ".17g") for x in xyz)+"\n")
        for face in mesh.faces:
            stream.write("f "+" ".join(str(int(i)+1) for i in face)+"\n")

def build(output, samples=128, layers=24, length_mm=25.0, density=1200.0):
    if samples<16 or samples%4 or layers<4 or layers%2 or length_mm<=0 or density<=0:
        raise ValueError("INVALID_REFERENCE_GEOMETRY_OPTIONS")
    output=Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start=time.perf_counter()
    heart=trimesh.Trimesh(*heart_mesh(samples,layers), process=False)
    shaft=rod_mesh()
    for name,part in (("heart",heart),("shaft",shaft)):
        if part.volume<0: part.invert()
        if not part.is_watertight or not part.is_winding_consistent or part.volume<=0:
            raise ValueError("INPUT_PART_NOT_VALID:"+name)
        write_off(output/(name+".off"),part)
    (output/"union.scad").write_text(
        "// Static reconstructed reference CSG ONLY; formal dynamic Boolean remains Cherchi.\n"
        'union(){import("heart.off",convexity=10);import("shaft.off",convexity=10);}\n'
    )
    command=["openscad","-o","union.off","union.scad"]
    run=subprocess.run(command,cwd=output,text=True,capture_output=True,timeout=240)
    (output/"openscad-build.log").write_text(run.stdout+run.stderr)
    if run.returncode or not re.search(r"Simple:\s+yes",run.stdout+run.stderr):
        raise RuntimeError("STATIC_CSG_BUILD_NOT_SIMPLE_OR_FAILED")
    fused=trimesh.load(output/"union.off",force="mesh",process=True)
    if fused.volume<0:fused.invert()
    components=fused.split(only_watertight=False)
    if (not fused.is_watertight or not fused.is_winding_consistent
        or len(components)!=1 or fused.volume<=max(heart.volume,shaft.volume)
        or fused.volume>=heart.volume+shaft.volume
        or not np.isfinite(fused.vertices).all()
        or min(fused.area_faces)<=0):
        raise ValueError("STATIC_FUSED_MESH_REJECTED")
    mm=fused.copy()
    mm.apply_scale(length_mm)
    obj=output/"heart-with-shaft-reference-mm.obj"
    stl=output/"heart-with-shaft-reference-mm.stl"
    glb=output/"heart-with-shaft-reference.glb"
    write_obj(obj,mm)
    mm.export(stl)
    obj_back=trimesh.load(obj,force="mesh",process=True)
    stl_back=trimesh.load(stl,force="mesh",process=True)
    for name,roundtrip in (("OBJ",obj_back),("STL",stl_back)):
        if (not roundtrip.is_watertight or not roundtrip.is_winding_consistent
            or len(roundtrip.split(only_watertight=False))!=1
            or abs(roundtrip.volume-mm.volume)>1e-6*mm.volume):
            raise ValueError(name+"_ROUNDTRIP_REJECTED")
    preview=mm.copy()
    facez=preview.triangles_center[:,2]
    silver=(facez<-.01)|(facez>42.52)
    colors=np.tile(np.asarray([210,68,96,255],dtype=np.uint8),(len(preview.faces),1))
    colors[silver]=[117,126,142,255]
    preview.visual.face_colors=colors
    preview.export(glb)
    # Trimesh inertia is unit-density mm^5; SI requires (1e-3 m/mm)^5.
    center_inertia_kg_m2=np.asarray(mm.moment_inertia)*density*1e-15
    audit=dict(schema="heart-static-reference-v1",
        classification="RECONSTRUCTED_GEOMETRY_UNOPTIMIZED_NOT_AUTHOR_CAD",
        original_eval60_reproduced=False,cherchi_dynamic_boolean_executed=False,
        faster_newton_converged=False,ground_contact_qualified=False,
        manufacturing_qualified=False,
        static_boolean_backend="OPENSCAD_CGAL_REFERENCE_ONLY_NOT_OPTIMIZER",
        source_design="experiments/reconstructed_heart_top/heart_top.py",
        source_shaft="experiments/heart_stem_contact/stem_geometry.py profile (48 sections)",
        source_sha256=dict(heart=sha(ROOT/"experiments/reconstructed_heart_top/heart_top.py"),
                           shaft=sha(ROOT/"experiments/heart_stem_contact/stem_geometry.py")),
        samples=samples,layers=layers,length_mm_per_model_unit=length_mm,
        assumed_density_kg_m3=density,
        vertices=len(mm.vertices),faces=len(mm.faces),
        connected_components=len(components),watertight=True,winding_consistent=True,
        static_cgal_simple=True,minimum_triangle_area_mm2=float(mm.area_faces.min()),
        volume_mm3=float(mm.volume),mass_g_estimate=float(mm.volume)*density*1e-6,
        bounds_mm=mm.bounds.tolist(),center_of_mass_mm=mm.center_mass.tolist(),
        center_of_mass_radial_offset_mm=float(np.linalg.norm(mm.center_mass[:2])),
        center_inertia_kg_m2=center_inertia_kg_m2.tolist(),
        obj_roundtrip=True,stl_roundtrip=True,elapsed_wall_seconds=time.perf_counter()-start,
        output_sha256={p.name:sha(p) for p in (obj,stl,glb)})
    (output/"geometry-audit.json").write_text(json.dumps(audit,indent=2,allow_nan=False)+"\n")
    return audit

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--samples",type=int,default=128)
    p.add_argument("--layers",type=int,default=24)
    args=p.parse_args()
    print(json.dumps(build(args.output,args.samples,args.layers),indent=2))

if __name__=="__main__":
    main()

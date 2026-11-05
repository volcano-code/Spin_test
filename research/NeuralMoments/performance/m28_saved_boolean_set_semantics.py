#!/usr/bin/env python3
"""W1 M28: exact saved-Boolean boundary provenance and side-of-solid audit.

Offline audit of an immutable evidence ZIP. It does not call Cherchi, change
solver policy, compute production moments/Jacobians, or run Newton.
Requires Python >=3.10, shapely >=2.0, GCC, GMP and Boost headers for M26.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
import time
from zipfile import ZipFile
from shapely.geometry import box as shp_box
from shapely.strtree import STRtree

ARCHIVE_SHA256 = "0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976"
M26_SUMMARY_SHA256 = "44867677606ea8437a5d94777df8214b879aca31ccb2fb047dd0e27cef3d79ff"
EXPECTED_OPS = {4: "intersection", 116: "difference", 117: "difference", 123: "difference"}
RAY_M_VALUES = (101,103,107,109,113,127,131,137,139,149,151,157,163,167,173,179,181,191,193,197)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def qfloat(value: float) -> Fraction:
    return Fraction(*float(value).as_integer_ratio())


def qtoken(token: str) -> Fraction:
    numerator, denominator = token.split("/")
    return Fraction(int(numerator, 0), int(denominator, 0))


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def sub(a, b):
    return tuple(x-y for x,y in zip(a,b))


def dot(a, b):
    return sum(x*y for x,y in zip(a,b))


def orient2(a,b,c):
    return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])


def project_axis(p, axis):
    return (p[1],p[2]) if axis==0 else ((p[0],p[2]) if axis==1 else (p[0],p[1]))


def plane_key(triangle):
    a,b,c=triangle
    n=cross(sub(b,a),sub(c,a))
    if n==(0,0,0): raise ValueError("DEGENERATE_EXACT_TRIANGLE")
    values=list(n)+[-dot(n,a)]
    den=1
    for value in values: den=math.lcm(den,value.denominator)
    ints=[int(value*den) for value in values]
    common=0
    for value in ints: common=math.gcd(common,abs(value))
    ints=[value//common for value in ints]
    for value in ints:
        if value:
            if value<0: ints=[-x for x in ints]
            break
    return tuple(ints)


def outward_low(value):
    result=float(value)
    if qfloat(result)>value: result=math.nextafter(result,-math.inf)
    return math.nextafter(result,-math.inf)


def outward_high(value):
    result=float(value)
    if qfloat(result)<value: result=math.nextafter(result,math.inf)
    return math.nextafter(result,math.inf)


def bbox2(points):
    xs=[p[0] for p in points]; ys=[p[1] for p in points]
    return (outward_low(min(xs)),outward_low(min(ys)),
            outward_high(max(xs)),outward_high(max(ys)))


def inside_projected_triangle(point, triangle2, sign):
    return all(orient2(triangle2[i],triangle2[(i+1)%3],point)*sign>=0 for i in range(3))


class PlaneIndex:
    """Exact plane hash, outward-rounded 2D AABB broad phase, exact containment."""
    def __init__(self, mesh):
        vertices,faces=mesh
        groups=defaultdict(list)
        for face_index,face in enumerate(faces):
            tri=tuple(vertices[k] for k in face)
            key=plane_key(tri)
            axis=max(range(3),key=lambda item:abs(key[item]))
            tri2=tuple(project_axis(p,axis) for p in tri)
            area=orient2(*tri2)
            if area==0: raise ValueError("DEGENERATE_INPUT_PROJECTION")
            groups[key].append((face_index,tri2,1 if area>0 else -1,tri))
        self.groups={}
        for key,items in groups.items():
            self.groups[key]=(max(range(3),key=lambda item:abs(key[item])),
                              items,STRtree([shp_box(*bbox2(x[1])) for x in items]))

    def locate(self, triangle):
        key=plane_key(triangle)
        entry=self.groups.get(key)
        if entry is None: return []
        axis,items,tree=entry
        tri2=tuple(project_axis(p,axis) for p in triangle)
        candidates=tree.query(shp_box(*bbox2(tri2)))
        return [(items[int(ix)][0],items[int(ix)][3])
                for ix in candidates
                if all(inside_projected_triangle(p,items[int(ix)][1],items[int(ix)][2])
                       for p in tri2)]


def project_ray(point,m):
    return (point[1]-point[0]/m,point[2]-point[0]/(m*m))


def choose_ray_m(mesh):
    vertices,faces=mesh
    normals=[plane_key(tuple(vertices[k] for k in f))[:3] for f in faces]
    for m in RAY_M_VALUES:
        if all(a*m*m+b*m+c!=0 for a,b,c in normals): return m
    raise ValueError("NO_GENERIC_EXACT_RAY_DIRECTION")


class _RayDirection:
    def __init__(self,mesh,m):
        self.m=m
        self.direction=(Fraction(1),Fraction(1,m),Fraction(1,m*m))
        vertices,faces=mesh
        self.items=[]; boxes=[]
        for face_index,face in enumerate(faces):
            tri=tuple(vertices[k] for k in face)
            tri2=tuple(project_ray(p,m) for p in tri)
            area=orient2(*tri2)
            if area==0: raise ValueError("RAY_DIRECTION_PARALLEL_TO_INPUT_FACE")
            normal=cross(sub(tri[1],tri[0]),sub(tri[2],tri[0]))
            self.items.append((face_index,tri,tri2,1 if area>0 else -1,normal))
            boxes.append(shp_box(*bbox2(tri2)))
        self.tree=STRtree(boxes)

    def classify_once(self,point):
        q=project_ray(point,self.m)
        query=shp_box(outward_low(q[0]),outward_low(q[1]),
                      outward_high(q[0]),outward_high(q[1]))
        crossings=0; boundary=False; edge_degenerate=False
        for candidate in self.tree.query(query):
            _,tri,tri2,sign,normal=self.items[int(candidate)]
            sides=[orient2(tri2[i],tri2[(i+1)%3],q)*sign for i in range(3)]
            if min(sides)<0: continue
            denom=dot(normal,self.direction)
            if denom==0: raise ValueError("RAY_DIRECTION_PARALLEL_TO_CANDIDATE_FACE")
            t=dot(normal,sub(tri[0],point))/denom
            if t==0: boundary=True
            elif t>0:
                if any(side==0 for side in sides): edge_degenerate=True
                else: crossings+=1
        if boundary: return "ON_BOUNDARY",crossings
        if edge_degenerate: return "RAY_EDGE_DEGENERATE",crossings
        return ("INSIDE" if crossings%2 else "OUTSIDE"),crossings


class RayIndex:
    """Exact rational parity classifier; retries with another generic ray on edge hits."""
    def __init__(self,mesh):
        self.mesh=mesh
        self.first_m=choose_ray_m(mesh)
        self.directions={}

    def _direction(self,m):
        if m not in self.directions: self.directions[m]=_RayDirection(self.mesh,m)
        return self.directions[m]

    def classify(self,point):
        start=RAY_M_VALUES.index(self.first_m)
        for retry,m in enumerate(RAY_M_VALUES[start:]):
            result,crossings=self._direction(m).classify_once(point)
            if result!="RAY_EDGE_DEGENERATE": return result,crossings,retry
        return "RAY_DEGENERATE",None,len(RAY_M_VALUES)-start


def load_mesh(document):
    return ([tuple(qfloat(x) for x in v) for v in document["vertices"]],
            [tuple(map(int,f)) for f in document["faces"]])


def load_packet(document):
    return ([tuple(qtoken(x) for x in v) for v in document["exact_vertices"]],
            [tuple(map(int,f)) for f in document["faces"]])


def signed_volume(mesh):
    vertices,faces=mesh
    return sum((dot(vertices[f[0]],cross(vertices[f[1]],vertices[f[2]]))/6
                for f in faces),Fraction(0))


def topology_summary(mesh):
    vertices,faces=mesh
    edge_faces=defaultdict(list)
    for fi,face in enumerate(faces):
        for a,b in ((face[0],face[1]),(face[1],face[2]),(face[2],face[0])):
            edge_faces[tuple(sorted((a,b)))].append(fi)
    adjacency=[set() for _ in faces]
    for uses in edge_faces.values():
        if len(uses)==2:
            a,b=uses; adjacency[a].add(b); adjacency[b].add(a)
    seen=set(); components=[]
    for start in range(len(faces)):
        if start in seen: continue
        todo=[start]; seen.add(start); count=0
        while todo:
            current=todo.pop(); count+=1
            for nxt in adjacency[current]:
                if nxt not in seen: seen.add(nxt); todo.append(nxt)
        components.append(count)
    return dict(vertices=len(vertices),edges=len(edge_faces),faces=len(faces),
                connected_components=len(components),component_face_counts=sorted(components,reverse=True),
                euler_characteristic=len(vertices)-len(edge_faces)+len(faces))


def validate_input_audit(document,name):
    required=("boundary_valid","closed","self_intersection_free","edge_manifold",
              "vertex_manifold","consistently_oriented")
    for key in required:
        if document.get(key) is not True:
            raise ValueError(f"{name}_AUDIT_FAILED:{key}")
    components=sorted(set(document.get("face_components",[])))
    if len(components)!=1:
        raise ValueError(f"{name}_MUST_HAVE_ONE_CONNECTED_BOUNDARY_COMPONENT")
    if document.get("component_volume_signs")!=[1]:
        raise ValueError(f"{name}_MUST_HAVE_POSITIVE_ORIENTATION")


def mesh_stream(mesh):
    vertices,faces=mesh
    lines=[f"{len(vertices)} {len(faces)}"]
    for vertex in vertices:
        lines.append(" ".join(f"{x.numerator}/{x.denominator}" for x in vertex))
    lines.extend(" ".join(map(str,face)) for face in faces)
    return "\n".join(lines)+"\n"


def combine_meshes(first,second):
    av,af=first; bv,bf=second
    return av+bv,af+[tuple(index+len(av) for index in face) for face in bf]


def ensure_m26_binary(source,binary):
    if binary and Path(binary).is_file():
        return str(Path(binary).resolve())
    source=Path(source).resolve()
    if not source.is_file(): raise FileNotFoundError(f"M26_SOURCE_MISSING:{source}")
    target=source.with_name("m26_exact_intersection")
    command=["g++","-std=c++17","-O2","-Wno-deprecated-declarations",
             str(source),"-o",str(target),"-lgmpxx","-lgmp"]
    result=subprocess.run(command,capture_output=True,text=True,timeout=180)
    if result.returncode:
        raise RuntimeError("M26_COMPILE_FAILED:"+result.stderr[-4000:])
    return str(target)


def run_m26(binary,mesh,max_seconds=180):
    result=subprocess.run([binary,"--max-seconds",str(max_seconds)],
                          input=mesh_stream(mesh),capture_output=True,text=True,timeout=max_seconds+10)
    lines=result.stdout.splitlines()
    status=next((line.split("=",1)[1] for line in lines if line.startswith("status=")),"NO_STATUS")
    fields={}
    for line in lines:
        if "=" in line:
            key,value=line.split("=",1)
            if key!="status":
                try: fields[key]=int(value)
                except ValueError:
                    try: fields[key]=float(value)
                    except ValueError: fields[key]=value
    return dict(returncode=result.returncode,status=status,fields=fields,
                stderr=result.stderr[-2000:])


def volume_summary(mesh):
    value=signed_volume(mesh)
    token=f"{value.numerator}/{value.denominator}"
    return dict(positive=value>0,zero=value==0,binary64=float(value),
                exact_fraction_sha256=sha256(token.encode()))


def load_m26_certificate(path, archive_sha):
    path=Path(path).resolve(strict=True)
    data=path.read_bytes()
    if sha256(data)!=M26_SUMMARY_SHA256:
        raise ValueError("M26_CERTIFICATE_FILE_SHA256_MISMATCH")
    document=json.loads(data)
    if document.get("schema")!="w1-m26-replayed-real-saved-geometry-summary-v1":
        raise ValueError("M26_CERTIFICATE_SCHEMA_MISMATCH")
    if document.get("archive_sha256")!=archive_sha:
        raise ValueError("M26_CERTIFICATE_ARCHIVE_MISMATCH")
    if document.get("saved_output_replay_status")!="COMPLETE_SAVED_OUTPUT_SELF_INTERSECTION_CERTIFICATION":
        raise ValueError("M26_CERTIFICATE_NOT_COMPLETE")
    if document.get("test_failures")!=0 or document.get("test_count",0)<14:
        raise ValueError("M26_CERTIFICATE_TESTS_NOT_GREEN")
    if document.get("same_saved_material_and_candidate_pair_checks") is not True:
        raise ValueError("M26_CERTIFICATE_NOT_SAME_MATERIAL")
    points={int(item["evaluation"]):item for item in document.get("points",[])}
    if set(points)!={4,116,117,123}:
        raise ValueError("M26_CERTIFICATE_POINT_SET_MISMATCH")
    return document,points,sha256(data)


def verify_m26_point_certificate(index,operation,output,raw_packet_sha,m26_entry):
    vertices,faces=output
    expected_status=("STRICT_EMPTY_NO_POSITIVE_MASS" if index==123
                     else "EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE")
    if m26_entry.get("status")!=expected_status:
        raise ValueError(f"EVAL_{index}_M26_CERTIFICATE_STATUS_MISMATCH")
    if m26_entry.get("operation")!=operation:
        raise ValueError(f"EVAL_{index}_M26_CERTIFICATE_OPERATION_MISMATCH")
    if m26_entry.get("packet_sha256")!=raw_packet_sha:
        raise ValueError(f"EVAL_{index}_M26_CERTIFICATE_PACKET_SHA_MISMATCH")
    if m26_entry.get("vertices")!=len(vertices) or m26_entry.get("faces")!=len(faces):
        raise ValueError(f"EVAL_{index}_M26_CERTIFICATE_GEOMETRY_SIZE_MISMATCH")
    if index!=123 and m26_entry.get("candidate_pairs",0)<=0:
        raise ValueError(f"EVAL_{index}_M26_CERTIFICATE_MISSING_PAIR_AUDIT")
    return dict(source="committed-M26-exact-post-Boolean-audit",
        archive_sha256=ARCHIVE_SHA256,packet_sha256=raw_packet_sha,
        m26_certificate_status=expected_status,
        m26_candidate_pairs=m26_entry.get("candidate_pairs",0),
        repeated_expensive_surface_audit=False)


def atomic_json(path,value):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+".tmp")
    temporary.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n")
    temporary.replace(path)


def audit_nonempty_point(index,operation,design,source,output,m26_certificate,sample_level="full"):
    out_vertices,out_faces=output
    source_index=PlaneIndex(source)
    print(f"M28 {index}: build plane/ray indices", flush=True)
    design_index=PlaneIndex(design)
    ray_source=RayIndex(source)
    ray_design=RayIndex(design)
    print(f"M28 {index}: indices ready", flush=True)
    owner_counts=Counter()
    orientation_counts=Counter()
    sample_counts=Counter()
    ray_retries=Counter()
    cache={}
    face_owner=[]
    for face_index,face in enumerate(out_faces):
        triangle=tuple(out_vertices[k] for k in face)
        design_matches=design_index.locate(triangle)
        source_matches=source_index.locate(triangle)
        if design_matches and source_matches:
            raise ValueError(f"EVAL_{index}_FACE_{face_index}_AMBIGUOUS_BOTH_OPERANDS")
        if len(design_matches)>1 or len(source_matches)>1:
            raise ValueError(f"EVAL_{index}_FACE_{face_index}_MULTIPLE_INPUT_TRIANGLES")
        if not design_matches and not source_matches:
            raise ValueError(f"EVAL_{index}_FACE_{face_index}_NO_INPUT_TRIANGLE_OWNER")
        if design_matches:
            owner="design"; input_face=design_matches[0][1]
            expected_orientation="same"
            expected_side="INSIDE" if operation=="intersection" else "OUTSIDE"
            other_operand="source"; ray_index=ray_source
        else:
            owner="source"; input_face=source_matches[0][1]
            expected_orientation="same" if operation=="intersection" else "opposite"
            expected_side="INSIDE"
            other_operand="design"; ray_index=ray_design
        out_normal=cross(sub(triangle[1],triangle[0]),sub(triangle[2],triangle[0]))
        input_normal=cross(sub(input_face[1],input_face[0]),sub(input_face[2],input_face[0]))
        alignment=dot(out_normal,input_normal)
        if alignment==0:
            raise ValueError(f"EVAL_{index}_FACE_{face_index}_ZERO_ORIENTATION_ALIGNMENT")
        actual_orientation="same" if alignment>0 else "opposite"
        if actual_orientation!=expected_orientation:
            raise ValueError(f"EVAL_{index}_FACE_{face_index}_ORIENTATION_MISMATCH")
        owner_counts[owner]+=1
        orientation_counts[(owner,actual_orientation)]+=1
        face_owner.append(owner)

        samples=[]
        if sample_level=="full":
            samples.extend(("vertex",point) for point in triangle)
            samples.extend(("edge_midpoint",tuple((triangle[j][axis]+triangle[(j+1)%3][axis])/2
                                                  for axis in range(3))) for j in range(3))
        samples.append(("centroid", tuple(sum(point[axis] for point in triangle)/3
                                           for axis in range(3))))
        for kind,point in samples:
            cache_key=(other_operand,point)
            if cache_key not in cache:
                cache[cache_key]=ray_index.classify(point)
            classification,_,retry=cache[cache_key]
            ray_retries[retry]+=1
            sample_counts[(owner,kind,classification)]+=1
            if classification not in (expected_side,"ON_BOUNDARY"):
                raise ValueError(
                    f"EVAL_{index}_FACE_{face_index}_{kind}_{classification}_EXPECTED_{expected_side}"
                )

    print(f"M28 {index}: side samples complete ({len(cache)} unique points)", flush=True)
    surface_audit=m26_certificate
    topology=topology_summary(output)
    if topology["connected_components"]!=1 or topology["euler_characteristic"]!=2:
        raise ValueError(f"EVAL_{index}_OUTPUT_TOPOLOGY_UNEXPECTED:{topology}")
    volume=volume_summary(output)
    if not volume["positive"]:
        raise ValueError(f"EVAL_{index}_OUTPUT_VOLUME_NOT_POSITIVE")
    return dict(evaluation=index,operation=operation,
        output_topology=topology,output_signed_volume=volume,
        exact_output_self_intersection_audit=surface_audit,
        output_face_owner_counts=dict(owner_counts),
        output_face_orientation_counts={f"{a}:{b}":v for (a,b),v in orientation_counts.items()},
        side_sample_counts={f"{a}:{b}:{c}":v for (a,b,c),v in sample_counts.items()},
        unique_operand_point_classifications=len(cache),
        ray_direction_retry_counts=dict(ray_retries),
        all_output_faces_owned_by_exactly_one_input_triangle=True,
        all_output_face_orientations_match_boolean_rule=True,
        all_vertex_edge_midpoint_centroid_samples_on_expected_side=True,
        full_triangle_interior_cross_boundary_tested=False,
        production_admitted=False)


def audit_empty_difference(design,source,output,source_audit,design_audit,m26_binary,m26_certificate):
    if output[0] or output[1]:
        raise ValueError("EVAL_123_EXPECTED_EMPTY_OUTPUT")
    strict_empty=m26_certificate
    combined=combine_meshes(design,source)
    cross_boundary=run_m26(m26_binary,combined)
    if cross_boundary["returncode"]!=0 or cross_boundary["status"]!="EXACT_POST_BOOLEAN_SELF_INTERSECTION_FREE":
        raise ValueError(f"EVAL_123_INPUT_BOUNDARIES_INTERSECT_OR_INVALID:{cross_boundary}")
    source_ray=RayIndex(source)
    point_classification=source_ray.classify(design[0][0])
    if point_classification[0]!="INSIDE":
        raise ValueError(f"EVAL_123_DESIGN_NOT_INSIDE_SOURCE:{point_classification}")
    if len(set(design_audit["face_components"]))!=1 or len(set(source_audit["face_components"]))!=1:
        raise ValueError("EVAL_123_NESTED_BOUNDARIES_REQUIRE_CONNECTED_COMPONENTS")
    if not volume_summary(design)["positive"] or not volume_summary(source)["positive"]:
        raise ValueError("EVAL_123_INPUT_ORIENTATION_OR_VOLUME_INVALID")
    return dict(evaluation=123,operation="difference",
        empty_output_audit=strict_empty,
        combined_design_source_boundary_audit=cross_boundary,
        design_boundary_sample_classification_in_source=point_classification[0],
        design_boundary_connected_components=1,source_boundary_connected_components=1,
        exact_input_boundary_nonintersection=True,
        nested_boundary_argument="The connected design boundary is disjoint from the connected source boundary and one design boundary point is inside the source; therefore the whole design solid is contained in the source solid.",
        empty_difference_semantics_supported=True,
        production_admitted=False)


def run_audit(archive_path,m26_source,m26_binary,output_path,sample_level="full",
              evaluation=None,resume=False,checkpoint_dir=None,m26_summary_path=None):
    archive_path=Path(archive_path).resolve(strict=True)
    archive_bytes=archive_path.read_bytes()
    archive_sha=sha256(archive_bytes)
    if archive_sha!=ARCHIVE_SHA256:
        raise ValueError("ORIGINAL_MATERIAL_EVIDENCE_ARCHIVE_SHA256_MISMATCH")
    summary_path=Path(m26_summary_path) if m26_summary_path else Path(__file__).with_name("m26-saved-post-boolean-summary.json")
    m26_document,m26_points,m26_summary_sha=load_m26_certificate(summary_path,archive_sha)
    selected=(4,116,117,123) if evaluation is None else (int(evaluation),)
    if any(index not in EXPECTED_OPS for index in selected):
        raise ValueError("UNKNOWN_M28_EVALUATION")
    binary=ensure_m26_binary(m26_source,m26_binary) if 123 in selected else None
    output_path=Path(output_path)
    checkpoint_dir=Path(checkpoint_dir) if checkpoint_dir else output_path.with_suffix(".checkpoints")
    checkpoint_dir.mkdir(parents=True,exist_ok=True)
    report=dict(schema="w1-m28-saved-boolean-boundary-patch-semantics-v2",
        input_archive_sha256=archive_sha,source_archive_bytes=len(archive_bytes),
        m26_certificate_sha256=m26_summary_sha,m26_certificate_reused=True,
        selected_evaluations=list(selected),new_boolean_calls=0,new_newton_runs=0,
        production_admitted=False,production_native_ten_moment_equality=False,
        jacobian_certified=False,smooth_neighborhood_certified=False,full_solver_speedup=None,
        side_sample_policy=sample_level,points=[])
    with ZipFile(archive_path) as zf:
        manifest=json.loads(zf.read("material-evidence-manifest.json"))
        for item in manifest["files"]:
            data=zf.read(item["file"])
            if len(data)!=item["bytes"] or sha256(data)!=item["sha256"]:
                raise ValueError("ARCHIVE_MEMBER_MANIFEST_MISMATCH:"+item["file"])
        design=load_mesh(json.loads(zf.read("physical-design-input.json")))
        design_audit=json.loads(zf.read("physical-design-boundary-audit.json"))
        validate_input_audit(design_audit,"DESIGN")
        design_volume=volume_summary(design)
        if not design_volume["positive"]:
            raise ValueError("DESIGN_VOLUME_NOT_POSITIVE")
        report["design_operand"]=dict(vertices=len(design[0]),faces=len(design[1]),
            signed_volume=design_volume,connected_boundary_components=1)
        for index in selected:
            checkpoint=checkpoint_dir/f"evaluation-{index:06d}.json"
            if resume and checkpoint.is_file():
                cached=json.loads(checkpoint.read_text())
                if (cached.get("schema")!="w1-m28-point-checkpoint-v1" or
                    cached.get("archive_sha256")!=archive_sha or
                    cached.get("m26_certificate_sha256")!=m26_summary_sha or
                    cached.get("sample_level")!=sample_level or
                    cached.get("evaluation")!=index):
                    raise ValueError(f"EVAL_{index}_CHECKPOINT_IDENTITY_MISMATCH")
                source_sha=sha256(zf.read(f"physical-source-input-{index:06d}.json"))
                packet_doc=json.loads(zf.read(f"point-{index:06d}.json"))
                if cached.get("source_input_sha256")!=source_sha or cached.get("packet_sha256")!=packet_doc["raw_packet_sha256"]:
                    raise ValueError(f"EVAL_{index}_CHECKPOINT_INPUT_SHA_MISMATCH")
                point_result=cached["result"]
                print(f"M28 evaluation {index}: restored verified checkpoint",flush=True)
            else:
                print(f"M28 evaluation {index}: start",flush=True)
                source_bytes=zf.read(f"physical-source-input-{index:06d}.json")
                source_sha=sha256(source_bytes)
                source_doc=json.loads(source_bytes)
                source=load_mesh(source_doc)
                source_audit=json.loads(zf.read(f"physical-source-audit-{index:06d}.json"))
                validate_input_audit(source_audit,f"SOURCE_{index}")
                operation=source_doc["boolean_operation"]
                if operation!=EXPECTED_OPS[index]:
                    raise ValueError(f"EVAL_{index}_OPERATION_MISMATCH")
                packet_doc=json.loads(zf.read(f"boolean-packet-{index:06d}.json"))
                packet=load_packet(packet_doc)
                point_doc=json.loads(zf.read(f"point-{index:06d}.json"))
                packet_sha=sha256(zf.read(point_doc["raw_packet_file"]))
                if packet_sha!=point_doc["raw_packet_sha256"]:
                    raise ValueError(f"EVAL_{index}_RAW_PACKET_SHA_MISMATCH")
                cert=verify_m26_point_certificate(index,operation,packet,packet_sha,m26_points[index])
                if index==123:
                    point_result=audit_empty_difference(design,source,packet,
                        source_audit,design_audit,binary,cert)
                else:
                    point_result=audit_nonempty_point(index,operation,design,source,packet,cert,sample_level)
                checkpoint_data=dict(schema="w1-m28-point-checkpoint-v1",evaluation=index,
                    archive_sha256=archive_sha,m26_certificate_sha256=m26_summary_sha,
                    source_input_sha256=source_sha,packet_sha256=packet_sha,
                    sample_level=sample_level,result=point_result)
                atomic_json(checkpoint,checkpoint_data)
                print(f"M28 evaluation {index}: checkpoint saved",flush=True)
            report["points"].append(point_result)
            report["completed_evaluations"]=[x["evaluation"] for x in report["points"]]
            atomic_json(output_path,report)
            print(f"M28 evaluation {index}: complete",flush=True)
    report["status"]=("COMPLETE_SELECTED_EVALUATION" if len(selected)==1
                       else "COMPLETE_SAVED_BOOLEAN_BOUNDARY_PATCH_AND_SIDE_AUDIT")
    report["scientific_limit"]=(
        "For nonempty outputs, every output triangle is exactly contained in one input triangle, "
        "has the Boolean-required orientation, and its vertices, edge midpoints and centroid are "
        "exactly classified on the expected side or on the opposite boundary. The exact M26 "
        "post-Boolean self-intersection certificate is reused only for the same archive and packet SHA. "
        "This is not a proof that no opposite-operand boundary crosses the interior of an output triangle; "
        "that requires a separate exact cross-triangle interior-intersection audit. Evaluation 123 has a "
        "nested-boundary argument from disjoint input boundaries and a certified interior point."
    )
    atomic_json(output_path,report)
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--archive",required=True)
    parser.add_argument("--m26-source",default=str(Path(__file__).with_name("m26_exact_intersection.cpp")))
    parser.add_argument("--m26-binary",default=None)
    parser.add_argument("--m26-summary",default=str(Path(__file__).with_name("m26-saved-post-boolean-summary.json")))
    parser.add_argument("--output",required=True)
    parser.add_argument("--checkpoint-dir",default=None)
    parser.add_argument("--evaluation",type=int,choices=(4,116,117,123),default=None)
    parser.add_argument("--resume",action="store_true")
    parser.add_argument("--sample-level",choices=("centroid","full"),default="full")
    args=parser.parse_args()
    report=run_audit(args.archive,args.m26_source,args.m26_binary,args.output,
        args.sample_level,args.evaluation,args.resume,args.checkpoint_dir,args.m26_summary)
    print(json.dumps({"status":report["status"],"output":args.output,
        "completed_evaluations":report.get("completed_evaluations",[]),
        "m26_certificate_reused":True,"new_boolean_calls":0,"new_newton_runs":0,
        "full_solver_speedup":None},indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
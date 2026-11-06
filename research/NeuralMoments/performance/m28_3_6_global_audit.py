#!/usr/bin/env python3
"""W1 M28.3.6 global saved-Boolean inventory/topology/seam audit.

Consumes the frozen evidence ZIP, M28 exact classifier, M28.3.5 cut receipts,
and M28.3.6 uncut-face receipts. It does not call Cherchi or Newton.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json
from collections import defaultdict, Counter
from fractions import Fraction as Q
from pathlib import Path
from zipfile import ZipFile

ARCHIVE_SHA="0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976"
EVALS=(4,116,117)
OPS={4:"intersection",116:"difference",117:"difference"}

def sha(b): return hashlib.sha256(b).hexdigest()
def qstr(s):
    a,b=s.split("/")
    return Q(int(a),int(b))
def fracstr(q): return f"{q.numerator}/{q.denominator}"
def loadmod(path):
    spec=importlib.util.spec_from_file_location("m28_saved_boolean_set_semantics",path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod

def exact_area2(tri,mod):
    n=mod.cross(mod.sub(tri[1],tri[0]),mod.sub(tri[2],tri[0]))
    axis=max(range(3),key=lambda i:abs(n[i]))
    p=[mod.project_axis(x,axis) for x in tri]
    return abs(mod.orient2(*p))

def point_on_segment(p,a,b,mod):
    d=mod.sub(b,a);w=mod.sub(p,a)
    return mod.cross(d,w)==(0,0,0) and 0<=mod.dot(w,d)<=mod.dot(d,d)

def point_in_triangle(p,tri,mod):
    a,b,c=tri;n=mod.cross(mod.sub(b,a),mod.sub(c,a))
    if mod.dot(n,mod.sub(p,a))!=0:return False
    signs=[mod.dot(mod.cross(mod.sub(tri[(i+1)%3],tri[i]),mod.sub(p,tri[i])),n) for i in range(3)]
    return min(signs)>=0

def topology_audit(mesh):
    vertices,faces=mesh
    edge_uses=defaultdict(list)
    vertex_links=[defaultdict(set) for _ in vertices]
    for fi,f in enumerate(faces):
        a,b,c=f
        for x,y in ((a,b),(b,c),(c,a)):
            edge_uses[tuple(sorted((x,y)))].append((fi,x,y))
        for v,x,y in ((a,b,c),(b,c,a),(c,a,b)):
            vertex_links[v][x].add(y);vertex_links[v][y].add(x)
    id_bad=[(e,len(u)) for e,u in edge_uses.items() if len(u)!=2]
    id_orientation_bad=[]
    for e,u in edge_uses.items():
        if len(u)==2 and not(u[0][1]==u[1][2] and u[0][2]==u[1][1]):
            id_orientation_bad.append(e)
    geometric=defaultdict(list)
    for fi,f in enumerate(faces):
        for x,y in ((f[0],f[1]),(f[1],f[2]),(f[2],f[0])):
            a,b=vertices[x],vertices[y]
            geometric[tuple(sorted((a,b)))].append((fi,a,b))
    geom_bad=[(e,len(u)) for e,u in geometric.items() if len(u)!=2]
    geom_orientation_bad=[]
    for e,u in geometric.items():
        if len(u)==2 and not(u[0][1]==u[1][2] and u[0][2]==u[1][1]):
            geom_orientation_bad.append(e)
    link_bad=[]
    for v,g in enumerate(vertex_links):
        if not g:
            link_bad.append((v,"UNUSED"));continue
        if any(len(ns)!=2 for ns in g.values()):
            link_bad.append((v,"LINK_DEGREE"));continue
        start=next(iter(g));seen={start};stack=[start]
        while stack:
            q=stack.pop()
            for n in g[q]:
                if n not in seen:seen.add(n);stack.append(n)
        if len(seen)!=len(g):link_bad.append((v,"LINK_DISCONNECTED"))
    adj=[set() for _ in faces]
    for uses in edge_uses.values():
        if len(uses)==2:
            a,b=uses[0][0],uses[1][0];adj[a].add(b);adj[b].add(a)
    seen=set();components=[]
    for i in range(len(faces)):
        if i in seen:continue
        stack=[i];seen.add(i);count=0
        while stack:
            x=stack.pop();count+=1
            for y in adj[x]:
                if y not in seen:seen.add(y);stack.append(y)
        components.append(count)
    duplicate_coordinates=len(vertices)-len(set(vertices))
    return {
      "vertices":len(vertices),"edges":len(edge_uses),"faces":len(faces),
      "edge_incidence_bad":len(id_bad),"edge_orientation_bad":len(id_orientation_bad),
      "geometric_edge_incidence_bad":len(geom_bad),
      "geometric_edge_orientation_bad":len(geom_orientation_bad),
      "vertex_link_bad":len(link_bad),"duplicate_coordinate_vertices":duplicate_coordinates,
      "connected_components":len(components),"component_face_counts":sorted(components,reverse=True),
      "euler_characteristic":len(vertices)-len(edge_uses)+len(faces),
      "passes":not(id_bad or id_orientation_bad or geom_bad or geom_orientation_bad or link_bad or duplicate_coordinates)
    },edge_uses

def read_jsonl(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]

def verify_cut_receipts(ev,work,cut_index,output_area,output_count):
    all_rows=[]
    for owner in ("design","source"):
        path=Path(work)/f"eval-{ev}-{owner}-receipts.jsonl"
        rows=read_jsonl(path)
        expected_ids=set(map(int,cut_index["design_parent_faces" if owner=="design" else "source_parent_faces"]))
        by_id={}
        for r in rows:
            key=int(r["parent_face_index"])
            if r["evaluation"]!=ev or r["owner"]!=owner or key in by_id:
                raise ValueError("CUT_RECEIPT_IDENTITY_OR_DUPLICATE")
            signature=sha(json.dumps({k:v for k,v in r.items() if k!="receipt_sha256"},sort_keys=True,separators=(",",":")).encode())
            if signature!=r.get("receipt_sha256"):raise ValueError("CUT_RECEIPT_SHA_MISMATCH")
            if r["archive_sha256"]!=ARCHIVE_SHA or r["cut_pair_index_sha256"]!=cut_index["cut_pair_index_sha256"]:
                raise ValueError("CUT_RECEIPT_ARCHIVE_OR_INDEX_MISMATCH")
            if not r["passes"] or any(r[k]!="0/1" for k in ("missing_area_exact","extra_area_exact","overlap_area_exact")):
                raise ValueError("CUT_RECEIPT_AREA_NOT_CERTIFIED")
            actual=qstr(r["actual_covered_area_exact"])
            if output_area.get((owner,key),Q(0))!=actual:
                raise ValueError("CUT_RECEIPT_OUTPUT_AREA_MISMATCH")
            if output_count.get((owner,key),0)!=r["saved_output_triangle_count"]:
                raise ValueError("CUT_RECEIPT_OUTPUT_FACE_COUNT_MISMATCH")
            by_id[key]=r
        if set(by_id)!=expected_ids:raise ValueError("CUT_RECEIPT_PARENT_INVENTORY_MISMATCH")
        all_rows.extend(rows)
    return all_rows

def verify_uncut_receipts(ev,work,design_count,source_count,cut_d,cut_s,output_area):
    all_rows=[]
    for owner,nfaces,cut in (("design",design_count,cut_d),("source",source_count,cut_s)):
        files=sorted(Path(work).glob(f"eval-{ev}-{owner}-uncut-*.json"))
        rows=[]
        for f in files:rows.extend(json.loads(f.read_text())["records"])
        ids=[int(r["parent_face_index"]) for r in rows]
        expected=set(range(nfaces))-cut
        if len(ids)!=len(set(ids)) or set(ids)!=expected:
            raise ValueError(f"UNCUT_PARENT_INVENTORY_MISMATCH:{ev}:{owner}")
        for r in rows:
            if r["evaluation"]!=ev or r["owner"]!=owner or r["centroid_class"] not in ("INSIDE","OUTSIDE"):
                raise ValueError("UNCUT_RECEIPT_IDENTITY_OR_CLASSIFICATION")
            expected_keep = (r["centroid_class"]=="INSIDE") if owner=="source" or ev==4 else (r["centroid_class"]=="OUTSIDE")
            if r["expected_kept"] is not expected_keep:
                raise ValueError("UNCUT_KEEP_POLICY_MISMATCH")
            expected_area=qstr(r["expected_area_exact"]);actual=qstr(r["actual_output_area_exact"])
            if expected_area!=actual or not r["matches"]:
                raise ValueError("UNCUT_EXACT_AREA_MISMATCH")
            if output_area.get((owner,int(r["parent_face_index"])),Q(0))!=actual:
                raise ValueError("UNCUT_OUTPUT_PARENT_AREA_MISMATCH")
        all_rows.extend(rows)
    return all_rows

def audit_seams(faces,vertices,face_owner,design,source,edge_uses,mod):
    counts=Counter();bad=[]
    for edge,uses in edge_uses.items():
        if len(uses)!=2:continue
        f0,f1=uses[0][0],uses[1][0]
        o0=face_owner[f0];o1=face_owner[f1]
        if o0==o1:
            counts["same_parent"]+=1;continue
        k0,p0=o0;k1,p1=o1
        pa,pb=vertices[edge[0]],vertices[edge[1]]
        if k0==k1:
            mesh=design if k0=="design" else source
            fa=set(mesh[1][p0]);fb=set(mesh[1][p1]);common=fa&fb
            if len(common)!=2:
                bad.append("PARENT_NOT_EDGE_ADJACENT");continue
            a,b=(mesh[0][i] for i in common)
            if not all(point_on_segment(p,a,b,mod) for p in (pa,pb)):
                bad.append("SAME_OPERAND_SEAM_NOT_ON_PARENT_EDGE");continue
            counts["same_operand_parent_seam"]+=1
        else:
            m0=design if k0=="design" else source;m1=design if k1=="design" else source
            t0=tuple(m0[0][i] for i in m0[1][p0]);t1=tuple(m1[0][i] for i in m1[1][p1])
            if not all(point_in_triangle(p,t0,mod) and point_in_triangle(p,t1,mod) for p in (pa,pb)):
                bad.append("CROSS_OPERAND_SEAM_NOT_ON_BOTH_PARENTS");continue
            counts["cross_operand_intersection_seam"]+=1
    return {"seam_edge_counts":dict(counts),"checked_seam_edges":sum(counts.values()),
            "invalid_seams":len(bad),"passes":not bad}

def audit_eval(ev,z,mod,work):
    source_doc=json.loads(z.read(f"physical-source-input-{ev:06d}.json"))
    source=mod.load_mesh(source_doc);operation=source_doc["boolean_operation"]
    packet=mod.load_packet(json.loads(z.read(f"boolean-packet-{ev:06d}.json")))
    design=mod.load_mesh(json.loads(z.read("physical-design-input.json")))
    ov,of=packet
    if operation!=OPS[ev]:raise ValueError("BOOLEAN_OPERATION_MISMATCH")
    cut_index=json.loads((Path(work)/f"eval-{ev}-exact-cut-index.json").read_text())
    if cut_index["archive_sha256"]!=ARCHIVE_SHA:raise ValueError("CUT_INDEX_ARCHIVE_MISMATCH")
    cut_d=set(map(int,cut_index["design_parent_faces"]));cut_s=set(map(int,cut_index["source_parent_faces"]))
    dindex=mod.PlaneIndex(design);sindex=mod.PlaneIndex(source)
    face_owner={};output_area=defaultdict(Q);output_count=Counter();ambiguous=[]
    for oi,f in enumerate(of):
        tri=tuple(ov[k] for k in f)
        dm=dindex.locate(tri);sm=sindex.locate(tri)
        if len(dm)>1 or len(sm)>1 or (bool(dm)==bool(sm)):
            ambiguous.append((oi,len(dm),len(sm)));continue
        owner="design" if dm else "source";pid=dm[0][0] if dm else sm[0][0]
        face_owner[oi]=(owner,pid);output_count[(owner,pid)]+=1
        output_area[(owner,pid)]+=Q(exact_area2(tri,mod),2)
    if ambiguous:raise ValueError(f"OUTPUT_FACE_PARENT_AMBIGUOUS:{ambiguous[:3]}")
    if len(face_owner)!=len(of):raise ValueError("OUTPUT_FACE_UNMAPPED")
    cut_rows=verify_cut_receipts(ev,work,cut_index,output_area,output_count)
    uncut_rows=verify_uncut_receipts(ev,work,len(design[1]),len(source[1]),cut_d,cut_s,output_area)
    if len(cut_rows)+len(uncut_rows)!=len(design[1])+len(source[1]):
        raise ValueError("INPUT_PARENT_FACE_INVENTORY_NOT_EXHAUSTIVE")
    topo,edge_uses=topology_audit(packet)
    seam=audit_seams(of,ov,face_owner,design,source,edge_uses,mod)
    expected=sum((qstr(r["expected_area_exact"]) for r in uncut_rows),Q(0))
    expected+=sum((qstr(r["expected_kept_area_exact"]) for r in cut_rows),Q(0))
    actual=sum(output_area.values(),Q(0))
    packet_area=sum((Q(exact_area2(tuple(ov[k] for k in f),mod),2) for f in of),Q(0))
    if expected!=actual or actual!=packet_area:raise ValueError("GLOBAL_EXACT_AREA_BALANCE_MISMATCH")
    return {
      "evaluation":ev,"operation":operation,
      "input_parent_faces":len(design[1])+len(source[1]),
      "cut_parent_faces":len(cut_rows),"uncut_parent_faces":len(uncut_rows),
      "cut_parent_faces_passed":sum(r["passes"] for r in cut_rows),
      "uncut_parent_faces_passed":sum(r["matches"] for r in uncut_rows),
      "output_faces":len(of),"output_faces_uniquely_mapped":len(face_owner),
      "output_faces_unmapped_or_ambiguous":len(of)-len(face_owner),
      "output_parent_area_exact":fracstr(actual),
      "expected_parent_area_exact":fracstr(expected),
      "global_exact_area_balance":True,
      "topology":topo,"seams":seam,
      "all_parent_faces_accounted":True,
      "global_boolean_completeness_certified":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",required=True);ap.add_argument("--m28",required=True)
    ap.add_argument("--work",required=True);ap.add_argument("--output",required=True)
    a=ap.parse_args()
    if sha(Path(a.archive).read_bytes())!=ARCHIVE_SHA:raise ValueError("ARCHIVE_SHA_MISMATCH")
    mod=loadmod(a.m28)
    with ZipFile(a.archive) as z:
        manifest=json.loads(z.read("material-evidence-manifest.json"))
        for item in manifest["files"]:
            b=z.read(item["file"])
            if len(b)!=item["bytes"] or sha(b)!=item["sha256"]:
                raise ValueError("ARCHIVE_MEMBER_MANIFEST_MISMATCH")
        results=[audit_eval(ev,z,mod,a.work) for ev in EVALS]
        pkt123=json.loads(z.read("boolean-packet-000123.json"))
        empty123=(not pkt123["vertices"] and not pkt123["exact_vertices"] and
                  not pkt123["faces"] and not pkt123["construction_records"])
    result={"schema":"w1-m28-3-6-global-inventory-topology-seam-audit-v1",
      "archive_sha256":ARCHIVE_SHA,"evaluations":results,
      "evaluation_123":{"strict_empty_packet":empty123,"operation":"difference",
        "production_admitted":False,"containment_reproved_in_this_stage":False},
      "global_boolean_completeness_certified":False,"production_admitted":False,
      "new_boolean_calls":0,"new_newton_runs":0,"full_solver_speedup":None}
    Path(a.output).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps(result,indent=2))
    return 0 if all(r["global_exact_area_balance"] and r["topology"]["passes"] and r["seams"]["passes"] for r in results) else 2
if __name__=="__main__":raise SystemExit(main())

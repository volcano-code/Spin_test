#!/usr/bin/env python3
"""W1 M28.3.7 exhaustive exact cut-pair discovery replay."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path
from zipfile import ZipFile

ARCHIVE_SHA="0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976"
EXPECTED={4:(416,1,416),116:(560,8,578),117:(562,8,580),123:(0,0,0)}

def sha(b):return hashlib.sha256(b).hexdigest()
def loadmod(path,name):
    import importlib.util
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def make_scaled_input(design,source,path):
    vals=[float(x) for row in design["vertices"] for x in row]
    vals += [float(x) for row in source["vertices"] for x in row]
    ratios=[x.as_integer_ratio() for x in vals]
    k=max(d.bit_length()-1 for _,d in ratios)
    nums=[n << (k-(d.bit_length()-1)) for n,d in ratios]
    it=iter(nums)
    lines=[f'{len(design["vertices"])} {len(design["faces"])} {len(source["vertices"])} {len(source["faces"])} {k}']
    lines.extend(" ".join(str(next(it)) for _ in range(3)) for _ in design["vertices"])
    lines.extend(" ".join(map(str,f)) for f in design["faces"])
    lines.extend(" ".join(str(next(it)) for _ in range(3)) for _ in source["vertices"])
    lines.extend(" ".join(map(str,f)) for f in source["faces"])
    data=("\n".join(lines)+"\n").encode();Path(path).write_bytes(data)
    return {"scale_power_of_two":k,"input_bytes":len(data),"input_sha256":sha(data)}
def parse_binary_output(text):
    header={};pairs=set()
    for line in text.splitlines():
        p=line.split()
        if len(p)==2 and p[0] in ("aabb_candidates","sat_contact_candidates","positive_dim_cut_pairs","elapsed_seconds"):
            header[p[0]]=float(p[1]) if p[0]=="elapsed_seconds" else int(p[1])
        elif len(p)==2:
            try:pairs.add((int(p[0]),int(p[1])))
            except ValueError:pass
    required={"aabb_candidates","sat_contact_candidates","positive_dim_cut_pairs","elapsed_seconds"}
    if not required.issubset(header):raise ValueError("EXACT_PAIR_BINARY_OUTPUT_INCOMPLETE")
    if len(pairs)!=header["positive_dim_cut_pairs"]:raise ValueError("PAIR_COUNT_OUTPUT_MISMATCH")
    return header,pairs
def load_frozen_pairs(index_path):
    d=json.loads(Path(index_path).read_text())
    left={(int(di),int(sj)) for di,item in d["design_parent_faces"].items() for sj in item["opposite_faces"]}
    right={(int(di),int(sj)) for sj,item in d["source_parent_faces"].items() for di in item["opposite_faces"]}
    if left!=right:raise ValueError("FROZEN_INDEX_ASYMMETRY")
    return d,left
def run_one(ev,z,binary,index_dir,out_dir):
    design=json.loads(z.read("physical-design-input.json"))
    source=json.loads(z.read(f"physical-source-input-{ev:06d}.json"))
    if ev==123:index={"archive_sha256":ARCHIVE_SHA};expected=set()
    else:
        index,expected=load_frozen_pairs(Path(index_dir)/f"eval-{ev}-exact-cut-index.json")
        if index["archive_sha256"]!=ARCHIVE_SHA:raise ValueError("FROZEN_INDEX_ARCHIVE_MISMATCH")
    if source["boolean_operation"] not in ("intersection","difference"):raise ValueError("OPERATION_MISMATCH")
    input_path=Path(out_dir)/f"eval-{ev}-exact-integer-input.txt"
    input_info=make_scaled_input(design,source,input_path)
    cp=subprocess.run([str(binary)],input=input_path.read_text(),text=True,capture_output=True,timeout=180)
    if cp.returncode:raise RuntimeError(f"EXACT_PAIR_BINARY_FAILED:{ev}:{cp.stderr}:{cp.stdout}")
    header,found=parse_binary_output(cp.stdout)
    missing=sorted(found-expected);extra=sorted(expected-found)
    result={"evaluation":ev,"operation":source["boolean_operation"],
      "design_input_faces":len(design["faces"]),"source_input_faces":len(source["faces"]),
      **input_info,**header,"independent_positive_dim_cut_pairs":len(found),
      "frozen_cut_pairs":len(expected),"independent_design_cut_faces":len({i for i,_ in found}),
      "independent_source_cut_faces":len({j for _,j in found}),
      "expected_cut_face_counts":[EXPECTED[ev][0],EXPECTED[ev][1]],
      "expected_cut_pair_count":EXPECTED[ev][2],
      "missing_frozen_pairs":len(missing),"extra_frozen_pairs":len(extra),
      "missing_pair_examples":missing[:20],"extra_pair_examples":extra[:20],
      "pair_sets_equal":found==expected,
      "proof_basis":"exhaustive closed AABB-overlap enumeration + exact GMP integer SAT + exact rational intersection dimension",
      "all_input_faces_checked_for_degeneracy":True}
    Path(out_dir,f"m28.3.7-eval-{ev}.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    Path(out_dir,f"m28.3.7-eval-{ev}-pairs.txt").write_text("".join(f"{i} {j}\n" for i,j in sorted(found)))
    return result
def verify_prior_global_evidence(global_audit_path,compact_path,receipt_manifest_path,work):
    full_raw=Path(global_audit_path).read_bytes();full=json.loads(full_raw)
    compact=json.loads(Path(compact_path).read_text())
    manifest_raw=Path(receipt_manifest_path).read_bytes();manifest=json.loads(manifest_raw)
    if sha(full_raw)!=compact["full_audit_json_sha256"]:raise ValueError("M28_3_6_FULL_AUDIT_SHA_MISMATCH")
    if sha(manifest_raw)!=full["receipt_manifest_sha256"]:raise ValueError("M28_3_6_RECEIPT_MANIFEST_SHA_MISMATCH")
    checked=[]
    for item in manifest["files"]:
        p=Path(work)/item["path"]
        if not p.exists() or p.stat().st_size!=item["bytes"] or sha(p.read_bytes())!=item["sha256"]:
            raise ValueError("M28_3_6_RECEIPT_FILE_SHA_MISMATCH:"+item["path"])
        checked.append(item["path"])
    for r in full["evaluations"]:
        if not (r["all_parent_faces_accounted"] and r["global_exact_area_balance"] and
                r["output_faces"]==r["output_faces_uniquely_mapped"] and
                r["topology"]["passes"] and r["seams"]["passes"] and r["seams"]["invalid_seams"]==0):
            raise ValueError("M28_3_6_GLOBAL_AUDIT_NOT_PASS:"+str(r["evaluation"]))
    return {"full_audit_sha256":sha(full_raw),"receipt_manifest_sha256":sha(manifest_raw),
            "receipt_files_verified":len(checked),"prior_global_audit_all_pass":True}
def verify_mesh_boundary_certificates(z,m28,ga):
    design=m28.load_mesh(json.loads(z.read("physical-design-input.json")))
    design_audit=json.loads(z.read("physical-design-boundary-audit.json"))
    def validate_audit(a,name):
        required=("boundary_valid","closed","edge_manifold","vertex_manifold",
                  "self_intersection_completed","self_intersection_free","consistently_oriented",
                  "component_orientations_valid")
        if not all(a.get(k) is True for k in required):raise ValueError("INPUT_BOUNDARY_CERTIFICATE_FAILED:"+name)
        if a.get("degenerate_faces") or a.get("intersecting_pair_count")!=0:
            raise ValueError("INPUT_BOUNDARY_DEGENERACY_OR_INTERSECTION:"+name)
    validate_audit(design_audit,"design")
    def signed_volume(mesh):
        v,f=mesh;total=m28.Fraction(0)
        for face in f:
            a,b,c=(v[i] for i in face);total+=m28.dot(a,m28.cross(b,c))
        return total/6
    dtop,_=ga.topology_audit(design);dvol=signed_volume(design)
    if not dtop["passes"] or dtop["connected_components"]!=1 or dvol<=0:
        raise ValueError("DESIGN_BOUNDARY_TOPOLOGY_OR_VOLUME_FAILED")
    rows=[]
    for ev in (4,116,117,123):
        source=m28.load_mesh(json.loads(z.read(f"physical-source-input-{ev:06d}.json")))
        sa=json.loads(z.read(f"physical-source-audit-{ev:06d}.json"));validate_audit(sa,f"source-{ev}")
        stop,_=ga.topology_audit(source);svol=signed_volume(source)
        if not stop["passes"] or stop["connected_components"]!=1 or svol<=0:
            raise ValueError("SOURCE_BOUNDARY_TOPOLOGY_OR_VOLUME_FAILED:"+str(ev))
        row={"evaluation":ev,"design_components":1,"source_components":1,
             "design_signed_volume_positive":True,"source_signed_volume_positive":True,
             "input_boundary_certificates_valid":True}
        if ev in (4,116,117):
            out=m28.load_packet(json.loads(z.read(f"boolean-packet-{ev:06d}.json")))
            otop,_=ga.topology_audit(out);ovol=signed_volume(out)
            if not otop["passes"] or otop["connected_components"]!=1 or ovol<=0:
                raise ValueError("OUTPUT_TOPOLOGY_OR_VOLUME_FAILED:"+str(ev))
            row.update({"output_components":1,"output_signed_volume_positive":True})
        rows.append(row)
    return rows
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--archive",required=True);ap.add_argument("--binary",required=True)
    ap.add_argument("--index-dir",required=True);ap.add_argument("--out-dir",required=True)
    ap.add_argument("--m28",required=True);ap.add_argument("--global-audit",required=True)
    ap.add_argument("--compact-summary",required=True);ap.add_argument("--receipt-manifest",required=True)
    ap.add_argument("--work",required=True);ap.add_argument("--ga",required=True)
    a=ap.parse_args();raw=Path(a.archive).read_bytes()
    if sha(raw)!=ARCHIVE_SHA:raise ValueError("FROZEN_ARCHIVE_SHA_MISMATCH")
    Path(a.out_dir).mkdir(parents=True,exist_ok=True)
    with ZipFile(a.archive) as z:
        manifest=json.loads(z.read("material-evidence-manifest.json"))
        for item in manifest["files"]:
            b=z.read(item["file"])
            if len(b)!=item["bytes"] or sha(b)!=item["sha256"]:raise ValueError("ARCHIVE_MEMBER_SHA_MISMATCH")
        results=[run_one(ev,z,a.binary,a.index_dir,a.out_dir) for ev in (4,116,117,123)]
    import importlib.util
    m28=loadmod(a.m28,"m28_saved_boolean_set_semantics")
    with ZipFile(a.archive) as z:
        design=m28.load_mesh(json.loads(z.read("physical-design-input.json")))
        source123=m28.load_mesh(json.loads(z.read("physical-source-input-000123.json")))
        tri=[design[0][i] for i in design[1][0]]
        sample=tuple(sum((v[k] for v in tri),m28.Fraction(0))/3 for k in range(3))
        status,ray_count,retries=m28.RayIndex(source123).classify(sample)
        design_audit=json.loads(z.read("physical-design-boundary-audit.json"))
        source_audit=json.loads(z.read("physical-source-audit-000123.json"))
        if status!="INSIDE":raise ValueError("EMPTY_DIFFERENCE_CONTAINMENT_SAMPLE_NOT_INSIDE")
        if not design_audit.get("boundary_valid") or not design_audit.get("self_intersection_free"):raise ValueError("DESIGN_BOUNDARY_NOT_CERTIFIED")
        if not source_audit.get("boundary_valid") or not source_audit.get("self_intersection_free"):raise ValueError("SOURCE_123_BOUNDARY_NOT_CERTIFIED")
        def signed_volume(mesh):
            v,f=mesh;total=m28.Fraction(0)
            for face in f:
                a,b,c=(v[i] for i in face);total+=m28.dot(a,m28.cross(b,c))
            return total/6
        design_vol=signed_volume(design);source_vol=signed_volume(source123)
        if design_vol<=0 or source_vol<=0:raise ValueError("EMPTY_DIFFERENCE_ORIENTATION_OR_VOLUME_INVALID")
        def face_components(mesh):
            _,faces=mesh;edges={}
            for fi,f in enumerate(faces):
                for x,y in ((f[0],f[1]),(f[1],f[2]),(f[2],f[0])):edges.setdefault(tuple(sorted((x,y))),[]).append(fi)
            adj=[set() for _ in faces]
            for uses in edges.values():
                if len(uses)==2:adj[uses[0]].add(uses[1]);adj[uses[1]].add(uses[0])
            seen=set();count=0
            for i in range(len(faces)):
                if i in seen:continue
                count+=1;stack=[i];seen.add(i)
                while stack:
                    x=stack.pop()
                    for y in adj[x]:
                        if y not in seen:seen.add(y);stack.append(y)
            return count
        dc=face_components(design);sc=face_components(source123)
        if dc!=1 or sc!=1:raise ValueError("EMPTY_DIFFERENCE_BOUNDARY_NOT_CONNECTED")
        containment={"evaluation":123,"operation":"difference","exact_boundary_pair_count":0,
          "design_boundary_sample_face":0,"sample_classification_against_source":"INSIDE",
          "ray_count":ray_count,"ray_retries":retries,
          "design_signed_volume_exact":f"{design_vol.numerator}/{design_vol.denominator}",
          "source_signed_volume_exact":f"{source_vol.numerator}/{source_vol.denominator}",
          "design_boundary_valid":True,"source_boundary_valid":True,
          "design_boundary_components":dc,"source_boundary_components":sc,
          "strict_empty_boolean_packet":not json.loads(z.read("boolean-packet-000123.json"))["faces"],
          "containment_supported":True}
    ga=loadmod(a.ga,"m28_3_6_global_audit")
    prior=verify_prior_global_evidence(a.global_audit,a.compact_summary,a.receipt_manifest,a.work)
    with ZipFile(a.archive) as z: boundary=verify_mesh_boundary_certificates(z,m28,ga)
    certified=all(r["pair_sets_equal"] for r in results) and containment["containment_supported"] and prior["prior_global_audit_all_pass"] and all(x["input_boundary_certificates_valid"] for x in boundary)
    summary={"schema":"w1-m28-3-7-independent-exact-cut-discovery-v1","archive_sha256":ARCHIVE_SHA,
      "evaluations":results,"total_aabb_candidates":sum(r["aabb_candidates"] for r in results),
      "total_exact_positive_dim_cut_pairs":sum(r["independent_positive_dim_cut_pairs"] for r in results),
      "total_frozen_cut_pairs":sum(r["frozen_cut_pairs"] for r in results),
      "all_pair_sets_equal":all(r["pair_sets_equal"] for r in results),
      "total_missing_pairs":sum(r["missing_frozen_pairs"] for r in results),
      "total_extra_pairs":sum(r["extra_frozen_pairs"] for r in results),
      "evaluation_123_containment":containment,"prior_global_evidence":prior,
      "input_output_boundary_certificates":boundary,
      "saved_boolean_boundary_semantics_certified":certified,
      "global_boolean_completeness_certified":certified,
      "certification_scope":"only frozen packets 4, 116, 117 and 123; not production solver admission",
      "new_boolean_calls":0,"new_newton_runs":0,"production_admitted":False,"full_solver_speedup":None}
    Path(a.out_dir,"m28.3.7-summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n")
    print(json.dumps(summary,indent=2))
    return 0 if certified else 2
if __name__=="__main__":raise SystemExit(main())

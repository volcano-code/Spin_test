"""General exact rational, fail-closed redundant-vertex reduction diagnostic.

No model name/geometry is used for a decision. Partial mode only tests local
applicability. Final mode needs independent global oriented surface proof.
"""
from collections import defaultdict
from pathlib import Path
from fractions import Fraction as Q
import sys,json,hashlib,time,argparse
sys.path.insert(0,'/mnt/data/noodles_v6_newrun/C2/Noodles_v6_C2_review/code')
from exact_retriangulate import surface_plane,boundary,boundary_cycle,collinear_forward,earclip,sums_moments,sha


def attempt(input_path,analysis_path,out,max_groups):
    start=time.monotonic()
    src=json.loads(Path(input_path).read_text())
    diag=json.loads(Path(analysis_path).read_text())
    if diag['sha256']!=sha(input_path):raise ValueError('SOURCE_MISMATCH')
    faces=[tuple(map(int,x)) for x in src['faces']];raw=src['vertices']
    possible={int(i) for g in diag['alias_groups'] for i in g['vertices']}
    inc=defaultdict(set)
    for fi,f in enumerate(faces):
        for v in f:
            if v in possible:inc[v].add(fi)
    cache={}
    def point(i):
        if i not in cache:cache[i]=tuple(Q(s) for s in raw[i])
        return cache[i]
    groups=diag['alias_groups'][:max_groups]
    trace=[];failed=None
    for g in groups:
        verts=list(map(int,g['vertices']))
        todo=[v for v in verts if inc[v]]
        operations=[]
        while len(todo)>1:
            choices=[];rejects={}
            for v in todo:
                by=defaultdict(list)
                try:
                    for fi in inc[v]:
                        if faces[fi] is not None:
                            by[surface_plane(faces[fi],point)].append(fi)
                    if len(by)!=2:raise ValueError(f'PRESERVE_CORNER_{len(by)}_PLANES')
                    proposals=[]
                    for plane,ids in by.items():
                        tris=[faces[fi] for fi in ids]
                        cycle=boundary_cycle(boundary(tris))
                        if v not in cycle:raise ValueError('NOT_BOUNDARY_VERTEX')
                        k=cycle.index(v)
                        if not collinear_forward(point(cycle[k-1]),point(v),point(cycle[(k+1)%len(cycle)])):
                            raise ValueError('ACTUAL_CREASE_CORNER')
                        cycle.pop(k)
                        newtris=earclip(cycle,point,plane)
                        if sums_moments(tris,point)!=sums_moments(newtris,point):raise ValueError('EXACT_MOMENT_MISMATCH')
                        proposals.append((ids,newtris))
                    choices.append((v,proposals))
                except Exception as e:
                    rejects[str(v)]=str(e)
            if not choices:
                failed=dict(group=g['group'],vertices=verts,remaining=todo,reason='NO_SAFE_REMOVAL',rejects=rejects)
                break
            # Choose highest index to preserve stable original corner if possible.
            v,proposals=max(choices,key=lambda item:item[0])
            affected=set(i for ids,_ in proposals for i in ids)
            adds=[tri for _,newtris in proposals for tri in newtris]
            if sums_moments([faces[fi] for fi in affected],point)!=sums_moments(adds,point):raise ValueError('PATCH_SUM_MISMATCH')
            for fi in affected:
                for w in faces[fi]:
                    if w in possible:inc[w].discard(fi)
                faces[fi]=None
            for tri in adds:
                fi=len(faces);faces.append(tri)
                for w in tri:
                    if w in possible:inc[w].add(fi)
            operations.append(dict(removed=v,faces_removed=len(affected),faces_added=len(adds)))
            todo=[w for w in todo if w!=v and inc[w]]
        trace.append(dict(group=g['group'],size=len(verts),operations=operations,remaining=todo,success=failed is None))
        print('GROUP',g['group'],'initial',len(verts),'removed',len(operations),'status', 'FAIL' if failed else 'OK', 'elapsed',round(time.monotonic()-start,2),flush=True)
        if failed:break
    report=dict(schema='generic-exact-local-alias-repair-feasibility',checked=len(trace),total_alias_groups=len(diag['alias_groups']),all_checked_succeeded=failed is None,
        is_global_representation_certified=False,input_sha256=sha(input_path),elapsed_s=time.monotonic()-start,failed=failed,group_results=trace)
    if failed is None and len(trace)==len(diag['alias_groups']):
        usedfaces=[f for f in faces if f is not None]
        used=sorted({v for f in usedfaces for v in f})
        remap={v:i for i,v in enumerate(used)}
        payload=dict(schema='generic-exact-equivalent-input-retriangulation-v1',
                     vertices=[raw[i] for i in used],
                     faces=[[remap[v] for v in f] for f in usedfaces],
                     original_packet_sha256=sha(input_path),
                     original_vertex_ids=used,
                     note='Exact local moments + collinear boundaries, independent global proof still required')
        outpacket=Path(out).with_name(Path(out).stem+'-candidate-rational.json')
        outpacket.write_text(json.dumps(payload,separators=(',',':'),sort_keys=True)+'\n')
        sys.path.insert(0,'/mnt/data/noodles_v6_newrun/C2/Noodles_v6_C2_review/code')
        from cherchi_input_precision_guard import inspect_exact_to_binary64
        guard=inspect_exact_to_binary64(payload)
        guardout=Path(out).with_name(Path(out).stem+'-binary64-guard.json')
        guardout.write_text(json.dumps(guard,indent=2))
        report.update(candidate=outpacket.name,candidate_sha256=sha(outpacket),
                      candidate_vertices=len(payload['vertices']),candidate_faces=len(payload['faces']),
                      binary64_guard=guard,global_surface_proof_complete=False)
        print('CANDIDATE',outpacket.name,'nV',len(payload['vertices']),'nF',len(payload['faces']),'guard',
              {k:guard[k] for k in ('aliased_distinct_exact_coordinate_groups','binary64_zero_or_nonfinite_area_faces','ready_for_cherchi_float_input')},flush=True)
    Path(out).write_text(json.dumps(report,indent=2));return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=16);p=parser.parse_args()
    root=Path('/mnt/data/Noodles_v7_paper_geometry_candidate');attempt(root/'exact_v7c/design-rational.json',root/'alias_analysis/design-alias-analysis.json',root/f'local-alias-repair-feasibility-{p.limit}.json',p.limit)

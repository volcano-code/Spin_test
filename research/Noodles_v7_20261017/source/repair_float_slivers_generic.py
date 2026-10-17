"""Generic exact nonmoving retriangulation of float64 zero-area sliver wedges.

Rejects non-proven changes. Applies only redundant collinear vertex removals
whose two coplanar incident patches preserve their exact 10 mass moments and
whose local double-degenerate face count strictly decreases.
Not a geometry or native Cherchi PASS until independent global audit follows.
"""
from pathlib import Path
from fractions import Fraction as Q
import json,sys,collections,time
import numpy as np
R=Path(__file__).resolve().parent
sys.path.insert(0,'/mnt/data/noodles_v6_newrun/C2/Noodles_v6_C2_review/code')
from exact_retriangulate import surface_plane,boundary,boundary_cycle,collinear_forward,earclip,sums_moments,sha
from cherchi_input_precision_guard import inspect_exact_to_binary64
src=R/'local-alias-repair-feasibility-412-candidate-rational.json'
p=json.loads(src.read_text());raw=p['vertices'];faces=[tuple(int(x) for x in f) for f in p['faces']]
V=np.asarray([[float(Q(x)) for x in row] for row in raw],dtype=np.float64)
inc=collections.defaultdict(set)
for fi,f in enumerate(faces):
 for v in f:inc[v].add(fi)
points={}
def point(i):
 if i not in points:points[i]=tuple(Q(s) for s in raw[i])
 return points[i]
def float_invalid(f):
 a,b,c=V[list(f)]
 with np.errstate(under='ignore',over='ignore',invalid='ignore'):
  v=np.cross(b-a,c-a);x=np.linalg.norm(v)
 return not np.isfinite(x) or x==0
def all_bad():return [i for i,f in enumerate(faces) if f is not None and float_invalid(f)]

def proposal(v):
 by=collections.defaultdict(list)
 for fi in inc[v]:
  if faces[fi] is not None:by[surface_plane(faces[fi],point)].append(fi)
 if len(by)!=2:raise ValueError('MUST_PRESERVE_TRUE_NONCOLLINEAR_CORNER')
 proposals=[]
 for plane,ids in by.items():
  tris=[faces[fi] for fi in ids]
  cycle=boundary_cycle(boundary(tris))
  if v not in cycle:raise ValueError('NOT_PATCH_BOUNDARY')
  k=cycle.index(v)
  if not collinear_forward(point(cycle[k-1]),point(v),point(cycle[(k+1)%len(cycle)])):
   raise ValueError('NOT_EXACT_STRAIGHT_BOUNDARY')
  cycle.pop(k)
  newtris=earclip(cycle,point,plane)
  if sums_moments(tris,point)!=sums_moments(newtris,point):raise ValueError('EXACT_MOMENTS_NOT_EQUAL')
  proposals.append((ids,newtris))
 affected={i for ids,_ in proposals for i in ids}
 old=[faces[i] for i in affected];new=[f for _,a in proposals for f in a]
 if sums_moments(old,point)!=sums_moments(new,point):raise ValueError('BOTH_PATCHES_COMBINED_MOMENTS_DIFFER')
 before=sum(map(float_invalid,old));after=sum(map(float_invalid,new))
 if before<=after:raise ValueError(f'NO_FLOAT64_AREA_PROGRESS_{before}_{after}')
 return {'v':v,'ids':affected,'added':new,'before':before,'after':after,'gain':before-after}

report=[];start=time.monotonic()
for iteration in range(100):
 bad=all_bad();print('ITER',iteration,'bad',len(bad),flush=True)
 if not bad:break
 candidates={};failures={}
 for fi in bad:
  for v in faces[fi]:
   if v in candidates or str(v) in failures:continue
   try:candidates[v]=proposal(v)
   except Exception as e:failures[str(v)]=str(e)
 if not candidates:
  report.append({'failed':True,'bad':bad,'failures':failures});print('FAILED_NO_CANDIDATES',bad,flush=True);break
 c=max(candidates.values(),key=lambda x:(x['gain'],-len(x['added']),x['v']))
 for fi in c['ids']:
  for v in faces[fi]:inc[v].discard(fi)
  faces[fi]=None
 for tri in c['added']:
  fi=len(faces);faces.append(tri)
  for v in tri:inc[v].add(fi)
 report.append(dict(removed_vertex=c['v'],affected_faces=len(c['ids']),new_faces=len(c['added']),zero_float_faces_removed=c['before'],zero_float_faces_added=c['after'],source_bad_faces=len(bad)))
 print('ACCEPT',c['v'],'progress',c['gain'],'time',round(time.monotonic()-start,1),flush=True)
else:
 print('BUDGET_100_EXHAUSTED',flush=True)
endfaces=[f for f in faces if f is not None]
used=sorted({v for f in endfaces for v in f});remap={v:i for i,v in enumerate(used)}
packet=dict(schema='noodles-v7-generic-two-stage-exact-retriangulation-CANDIDATE',vertices=[raw[i] for i in used],faces=[[remap[v] for v in f] for f in endfaces],parent_sha256=sha(src),original_vertex_ids_from_first_candidate=used,note='Must pass independent global chain, float64 guard, native boundary check and all source binding')
out=R/'two-stage-generic-retriangulation-candidate-rational.json'
out.write_text(json.dumps(packet,separators=(',',':'),sort_keys=True)+'\n')
proof=dict(start_sha256=sha(src),result_sha256=sha(out),seconds=time.monotonic()-start,steps=report,iterations=len(report),full_float64_check_pending=True)
(R/'two-stage-generic-retriangulation-local-proof.json').write_text(json.dumps(proof,indent=2,default=int))
print('POSTPROCESS',len(packet['vertices']),len(packet['faces']),'start guard',flush=True)
guard=inspect_exact_to_binary64(packet)
(R/'two-stage-generic-retriangulation-f64-guard.json').write_text(json.dumps(guard,indent=2))
print('FINAL_GUARD',{k:guard[k] for k in ['aliased_distinct_exact_coordinate_groups','binary64_zero_or_nonfinite_area_faces','ready_for_cherchi_float_input']},'elapsed',round(time.monotonic()-start,1),flush=True)

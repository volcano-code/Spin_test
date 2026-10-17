"""Generic fail-closed exact surface retriangulation for scaled binary64 output.

A generic OBJ exporter can degenerate exact nonzero rational faces when scaled
and rounded to float64. This program removes ONLY exact collinear redundant
vertices shared by two planar patches, requiring both local exact moment
invariance and a strict decrease in bad scaled faces. It neither moves source
vertices nor changes Newton physics or objective.

Final qualification REQUIRES a separate global exact signed-surface-chain proof
AND an independent native binary64 audit of the *exported* OBJ.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,time,sys
from pathlib import Path
from fractions import Fraction as Q
import numpy as np
sys.path.insert(0,'/mnt/data/noodles_v6_newrun/C2/Noodles_v6_C2_review/code')
from exact_retriangulate import surface_plane,boundary,boundary_cycle,collinear_forward,earclip,sums_moments,sha

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--scale',type=str,required=True);ap.add_argument('--max-steps',type=int,default=100);args=ap.parse_args()
 if args.source.resolve()==args.output.resolve() or args.output.exists():raise RuntimeError('REFUSE_SOURCE_OVERWRITE')
 start=time.monotonic();scale=Q(args.scale)
 pkt=json.loads(args.source.read_text());raw=pkt['vertices'];faces=[tuple(map(int,x)) for x in pkt['faces']]
 V=np.asarray([[float(Q(x)*scale) for x in row] for row in raw],dtype=np.float64)
 inc=collections.defaultdict(set)
 for i,f in enumerate(faces):
  for v in f: inc[v].add(i)
 cache={}
 def point(i):
  if i not in cache:cache[i]=tuple(Q(x) for x in raw[i])
  return cache[i]
 def bad_face(tri):
  v=V[list(tri)];normal=np.cross(v[1]-v[0],v[2]-v[0]);size=np.linalg.norm(normal)
  return bool(not np.isfinite(size) or size==0.)
 def proposal(v):
  planes=collections.defaultdict(list)
  for fi in inc[v]:
   if faces[fi] is not None:planes[surface_plane(faces[fi],point)].append(fi)
  if len(planes)!=2:raise ValueError('NON_REDUNDANT_CREASE_OR_JUNCTION')
  proposals=[]
  for plane,ids in planes.items():
   tris=[faces[fi] for fi in ids]
   cycle=boundary_cycle(boundary(tris))
   if v not in cycle:raise ValueError('NON_BOUNDARY_VERTEX')
   k=cycle.index(v)
   if not collinear_forward(point(cycle[k-1]),point(v),point(cycle[(k+1)%len(cycle)])):
    raise ValueError('NOT_EXACT_STRAIGHT_BOUNDARY')
   cycle.pop(k);newtris=earclip(cycle,point,plane)
   if sums_moments(tris,point)!=sums_moments(newtris,point):raise ValueError('EXACT_PATCH_MOMENTS_CHANGED')
   proposals.append((ids,newtris))
  affected={i for ids,_ in proposals for i in ids};old=[faces[i] for i in affected]
  added=[tri for _,ts in proposals for tri in ts]
  if sums_moments(old,point)!=sums_moments(added,point):raise ValueError('EXACT_COMBINED_MOMENTS_CHANGED')
  before=sum(bad_face(f) for f in old);after=sum(bad_face(f) for f in added)
  if before<=after:raise ValueError('NO_SCALED_AREA_IMPROVEMENT')
  return {'vertex':v,'affected':affected,'added':added,'before':before,'after':after,'gain':before-after}
 bad={i for i,f in enumerate(faces) if bad_face(f)}
 init=len(bad);steps=[];print('START_SCALED_F64_RETRIANGULATION',init,'faces',len(faces),flush=True)
 for it in range(args.max_steps):
  if not bad:break
  candidates=[];fail={}
  for fi in sorted(bad):
   for v in faces[fi]:
    if v in fail or any(x['vertex']==v for x in candidates):continue
    try:candidates.append(proposal(v))
    except Exception as e:fail[v]=f'{type(e).__name__}: {e}'
  if not candidates:
   rep=dict(schema='generic-scaled-exact-retriangulation-v1',success=False,error='NO_SAFE_PROPOSAL',
            blocked_bad_face_indices=sorted(bad),diagnostics={str(k):v for k,v in fail.items()},
            source_sha256=sha(args.source),steps=steps,elapsed_seconds=time.monotonic()-start)
   args.output.with_suffix('.failure.json').write_text(json.dumps(rep,indent=2))
   print('NO_SAFE_PROPOSAL',len(bad),flush=True);raise RuntimeError('UNREPAIRED_SCALED_FLOAT_DEGENERACY')
  choice=max(candidates,key=lambda c:(c['gain'],-len(c['added']),-c['vertex']))
  for fi in choice['affected']:
   for v in faces[fi]: inc[v].discard(fi)
   faces[fi]=None
   bad.discard(fi)
  for f in choice['added']:
   fi=len(faces);faces.append(f)
   for v in f:inc[v].add(fi)
   if bad_face(f):bad.add(fi)
  step=dict(iteration=it,removed_exact_collinear_vertex_id=choice['vertex'],old_faces=len(choice['affected']),
            new_faces=len(choice['added']),bad_before=choice['before'],bad_after=choice['after'],bad_remaining=len(bad),
            exact_local_moments_and_collinearity_preserved=True)
  steps.append(step);print('REPAIR',step,'time',round(time.monotonic()-start,2),flush=True)
 if bad:raise RuntimeError('RETRIANGULATION_STEP_BUDGET_EXHAUSTED')
 resulting=[f for f in faces if f is not None];used=sorted({v for f in resulting for v in f});mapping={v:i for i,v in enumerate(used)}
 result={'schema':'generic-exact-scaled-mm-retriangulation-candidate-v1','vertices':[raw[v] for v in used],
         'faces':[[mapping[v] for v in f] for f in resulting], 'source_sha256':sha(args.source),
         'scale_factor':token(scale),'certification':'LOCAL_PATCH_EXACT_MOMENTS_ONLY_PENDING_GLOBAL_CHAIN_AND_FLOAT_NATIVE_AUDIT'}
 args.output.write_text(json.dumps(result,separators=(',',':'),sort_keys=True)+'\n')
 rep=dict(schema='generic-exact-scaled-retriangulation-proof-v1',success=True,source_sha256=sha(args.source),
          result_sha256=sha(args.output),scale=token(scale),original_vertices=len(raw),original_faces=len(pkt['faces']),
          result_vertices=len(used),result_faces=len(resulting),initial_scaled_float_zero_faces=init,final_scaled_float_zero_faces=0,
          steps=steps,elapsed_seconds=time.monotonic()-start,independent_global_surface_chain_verified=False,
          independent_native_binary64_verified=False)
 args.output.with_suffix('.local-proof.json').write_text(json.dumps(rep,indent=2))
 print('DONE',rep['result_faces'],'seconds',rep['elapsed_seconds'],flush=True)


def token(x):
 q=Q(x);return f'{q.numerator}/{q.denominator}'
if __name__=='__main__':main()

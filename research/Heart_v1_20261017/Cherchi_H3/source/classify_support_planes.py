"""Read-only exact rational plane and binary64 export clash classification."""
import argparse, hashlib, json
from collections import Counter, defaultdict
from fractions import Fraction
from math import gcd
from functools import reduce
from pathlib import Path


def plane_key(a,b,c):
    d=[b[k]-a[k] for k in range(3)]; e=[c[k]-a[k] for k in range(3)]
    n=[d[1]*e[2]-d[2]*e[1], d[2]*e[0]-d[0]*e[2], d[0]*e[1]-d[1]*e[0]]
    if not any(n):raise ValueError('EXACT_ZERO_AREA_FACE')
    p=n+[-sum(n[k]*a[k] for k in range(3))]
    pivot=next(v for v in p if v);return tuple(str(v/pivot) for v in p)


def classify(material_path, binary_audit_path, exact_audit_path):
    paths=[Path(i) for i in (material_path,binary_audit_path,exact_audit_path)]
    mat,fl,ex=[json.loads(p.read_text()) for p in paths]
    if not ex.get('boundary_valid') or not ex.get('self_intersection_free') or ex.get('intersecting_pair_count')!=0:
        raise ValueError('EXACT_INPUT_NOT_VALIDATED')
    if fl.get('boundary_valid') or fl.get('self_intersection_free') or not fl.get('intersecting_pairs'):
        raise ValueError('FLOAT_EXPORT_HAS_NO_RECORDED_FAILURE')
    faces=mat['faces']; coords=mat['exact_vertices']
    if len(coords)!=len(mat['vertices']) or any(len(v)!=3 for v in coords):raise ValueError('INVALID_COORDINATES')
    rational=[[Fraction(s) for s in v] for v in coords]
    groups=defaultdict(list); keys=[]
    for i,tri in enumerate(faces):
        if len(tri)!=3 or min(tri)<0 or max(tri)>=len(coords):raise ValueError('INVALID_FACE')
        key=plane_key(*[rational[v] for v in tri]);keys.append(key);groups[key].append(i)
    pairs=fl['intersecting_pairs']
    if len(pairs)!=fl.get('intersecting_pair_count'):raise ValueError('PAIR_COUNT_MISMATCH')
    same=[];other=[];affected=set()
    for pair in pairs:
        if len(pair)!=2 or any(not isinstance(i,int) or i<0 or i>=len(faces) for i in pair):raise ValueError('INVALID_INTERSECTION_PAIR')
        a,b=pair;affected.update(pair)
        (same if keys[a]==keys[b] else other).append(pair)
    result={'schema':'heart-h3-exact-support-classification-v1',
        'input_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'scope':'DIAGNOSTIC_ONLY_H1_V4_PROXY',
        'faces':len(faces),'exact_support_planes':len(groups),'same_plane_pairs':len(same),
        'different_plane_pairs':len(other),'float_intersections':len(pairs),
        'affected_faces':len(affected), 'single_face_planes':sum(len(v)==1 for v in groups.values()),
        'face_support_plane_multiplicity':dict(sorted(Counter(map(len,groups.values())).items())),
        'affected_faces_on_multiface_plane':sum(len(groups[keys[i]])>1 for i in affected),
        'same_plane_examples':same[:20],'different_plane_examples':other[:20],
        'candidate_created':False,'same_exact_material_proved':False,'float_output_qualified':False,
        'next':'Exact coplanar patch boundaries and cross-plane vertex/edge classifications; reject all unproven mesh edits'}
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for name in ('material','binary_audit','rational_audit','output'):ap.add_argument('--'+name.replace('_','-'),required=True)
    x=ap.parse_args();out=classify(x.material,x.binary_audit,x.rational_audit)
    Path(x.output).write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({k:out[k] for k in ('faces','exact_support_planes','same_plane_pairs','different_plane_pairs','candidate_created')}))

"""Exact rational-vs-binary64 supporting-plane side classification for H1.

A sign disagreement explains why a pair may newly intersect in the rounded
coordinate representation. It is not itself an intersection certificate.
No geometry is edited or silently approximated by this program.
"""
from fractions import Fraction
from collections import Counter
from hashlib import sha256
from pathlib import Path
import json
import argparse
from certify_h4_retriangulation import load_frozen, cross, sub, dot, face_plane

def side(qpoint,plane):
    n,d=plane
    return 1 if dot(qpoint,n)+d>0 else (-1 if dot(qpoint,n)+d<0 else 0)

def homogeneous_plane(face,coordinates):
    a,b,c=[coordinates[int(k)] for k in face]
    n=cross(sub(b,a),sub(c,a));return n,-dot(n,a)

def classify(material,binary_audit,rational_audit):
    data,v,faces,exact,old=load_frozen(material,binary_audit,rational_audit)
    rounded=[tuple(Fraction(float(x)) for x in row) for row in v]
    exact_planes=[homogeneous_plane(face,exact) for face in faces]
    rounded_planes=[homogeneous_plane(face,rounded) for face in faces]
    pairs=old['intersecting_pairs'];summary=Counter();events=[]
    for a,b in pairs:
        plane_a=face_plane(faces[a],exact)
        plane_b=face_plane(faces[b],exact)
        changed=[]
        for src,other in ((a,b),(b,a)):
            for vertex in faces[other]:
                exact_side=side(exact[int(vertex)],exact_planes[src])
                rounded_side=side(rounded[int(vertex)],rounded_planes[src])
                if exact_side!=rounded_side:
                    changed.append({'plane_face':int(src),'vertex':int(vertex),'exact_side':exact_side,'float_side':rounded_side})
        same=plane_a==plane_b
        shared=len(set(int(t) for t in faces[a])&set(int(t) for t in faces[b]))
        summary['same_exact_plane' if same else 'cross_exact_plane']+=1
        summary['shared_'+str(shared)+'_vertex_indices']+=1
        if changed:summary['with_at_least_one_side_change']+=1
        else:summary['with_no_side_change']+=1
        events.append({'face_pair':[int(a),int(b)],'shared_vertices_by_index':shared,'same_exact_support_plane':same,'side_change_count':len(changed),'changes':changed})
    return {'schema':'heart-h4-side-change-diagnostic-v1',
            'input_sha256':{'material':sha256(Path(material).read_bytes()).hexdigest(),
                            'binary_audit':sha256(Path(binary_audit).read_bytes()).hexdigest(),
                            'rational_audit':sha256(Path(rational_audit).read_bytes()).hexdigest()},
            'summary':dict(summary),'pairs':events,
            'notes':'Side differences occur on actual H1 proxy triangles after independent binary64 rounding; not original eval60 and not proof of material changes'}
if __name__=='__main__':
    ap=argparse.ArgumentParser()
    for k in ('material','binary_audit','rational_audit','output'):
        ap.add_argument('--'+k.replace('_','-'),type=Path,required=True)
    v=ap.parse_args();out=classify(v.material,v.binary_audit,v.rational_audit)
    v.output.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n')
    print(json.dumps(out['summary'],indent=2))

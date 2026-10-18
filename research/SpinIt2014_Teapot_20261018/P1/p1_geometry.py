#!/usr/bin/env python3
"""W4 P1: source-pinned Utah Teapot topology repair candidate and strict gates.

This prepares a CANDIDATE, not an author-original CAD or a certified solid.
No mesh Boolean, design-domain optimization or claimed physical truth is done.
"""
from __future__ import annotations
import argparse
import csv
from collections import Counter, defaultdict, deque
import hashlib
import json
from pathlib import Path
import numpy as np

SOURCE_SHA256 = '1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4'
SOURCE_UPSTREAM_BLOB = 'c839837bfc09f5d5bac4aa757fcbd9f16ddd7ec1'
SOURCE_UPSTREAM_COMMIT = '8a4f8642acaf43f9cd7b67858a1502e1055ef202'


def read_obj(path):
    vertices, faces = [], []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        tokens = line.split()
        if not tokens: continue
        if tokens[0] == 'v':
            if len(tokens) < 4: raise ValueError('BAD_VERTEX')
            vertices.append([float(x) for x in tokens[1:4]])
        elif tokens[0] == 'f':
            polygon = []
            for token in tokens[1:]:
                index = int(token.split('/')[0])
                polygon.append(index - 1 if index > 0 else len(vertices) + index)
            if len(polygon) < 3: raise ValueError('BAD_FACE')
            faces += [[polygon[0], polygon[i], polygon[i+1]] for i in range(1, len(polygon)-1)]
    v = np.asarray(vertices, dtype=np.float64).reshape(-1, 3)
    f = np.asarray(faces, dtype=np.int64).reshape(-1, 3)
    if not len(v) or not len(f) or not np.isfinite(v).all() or f.min() < 0 or f.max() >= len(v):
        raise ValueError('INVALID_OBJ')
    if np.any(f[:, 0] == f[:, 1]) or np.any(f[:, 1] == f[:, 2]) or np.any(f[:, 0] == f[:, 2]):
        raise ValueError('DEGENERATE_INDEXED_FACE')
    return v, f


def write_obj(path, v, f):
    with Path(path).open('w', encoding='utf-8', newline='\n') as out:
        out.write('# W4 P1 topology candidate, not a certified solid or author-original CAD\n')
        for x, y, z in v: out.write(f'v {x:.17g} {y:.17g} {z:.17g}\n')
        for a, b, c in f: out.write(f'f {a+1} {b+1} {c+1}\n')


def edge_map(f):
    edges = defaultdict(list)
    for i, (a, b, c) in enumerate(f):
        for x, y in ((a, b), (b, c), (c, a)):
            edges[(min(int(x), int(y)), max(int(x), int(y)))].append((int(x), int(y), i))
    return edges


def boundary_loops(f):
    edges = edge_map(f)
    if any(len(e) > 2 for e in edges.values()): raise ValueError('NONMANIFOLD_EDGE')
    if any(len(e) == 2 and e[0][:2] == e[1][:2] for e in edges.values()):
        raise ValueError('INCONSISTENT_WINDING')
    directed = [entry[0][:2] for entry in edges.values() if len(entry) == 1]
    outgoing, incoming = defaultdict(list), defaultdict(list)
    for a, b in directed:
        outgoing[a].append(b); incoming[b].append(a)
    if set(outgoing) != set(incoming) or any(len(outgoing[x]) != 1 or len(incoming[x]) != 1 for x in outgoing):
        raise ValueError('BRANCHED_OR_OPEN_BOUNDARY')
    next_vertex = {a: b[0] for a, b in outgoing.items()}
    loops = []
    while next_vertex:
        start = min(next_vertex); loop = []; at = start
        while at in next_vertex:
            loop.append(at); at = next_vertex.pop(at)
        if at != start: raise ValueError('OPEN_BOUNDARY')
        loops.append(loop)
    return loops, len(directed)


def vertex_fans(f, number_vertices):
    """Find nonmanifold/bow-tie vertex stars using shared incident mesh EDGES."""
    incidence = [[] for _ in range(number_vertices)]
    neighbors = defaultdict(list)
    for fi, tri in enumerate(f):
        for vi in tri: incidence[int(vi)].append(fi)
    for (a, b), entries in edge_map(f).items():
        if len(entries) == 2:
            i, j = entries[0][2], entries[1][2]
            neighbors[(a, i)].append(j); neighbors[(a, j)].append(i)
            neighbors[(b, i)].append(j); neighbors[(b, j)].append(i)
    result = {}
    for vi, indices in enumerate(incidence):
        unseen = set(indices); fans = []
        while unseen:
            at = unseen.pop(); fan = [at]; pending = [at]
            while pending:
                for adjacent in neighbors.get((vi, pending.pop()), []):
                    if adjacent in unseen:
                        unseen.remove(adjacent); fan.append(adjacent); pending.append(adjacent)
            fans.append(fan)
        if len(fans) > 1: result[vi] = fans
    return result


def signed_volume_and_moments(v, f):
    tri = v[f]; a, b, c = tri[:, 0, :], tri[:, 1, :], tri[:, 2, :]
    volume = np.einsum('ij,ij->i', a, np.cross(b, c)) / 6.
    total = float(volume.sum())
    first = (volume[:, None] * (a+b+c) / 4.).sum(axis=0)
    second = np.zeros((3, 3), dtype=float)
    all_sum = a+b+c
    for i in range(3):
        for j in range(3):
            second[i, j] = np.sum(volume * (all_sum[:, i]*all_sum[:, j] +
                                                 a[:, i]*a[:, j]+b[:, i]*b[:, j]+c[:, i]*c[:, j]) / 20.)
    cm = first / total if abs(total) > 1e-15 else np.full(3, np.nan)
    inertia = np.trace(second) * np.eye(3) - second
    return total, first, second, cm, inertia


def stitch_rings(v, loops):
    """Join the distinct 40-vertex coplanar body and lid rims by an annulus.

    The opposite winding and common plane are verified, and no rim is capped
    with a disk (which would double-fill the lid or obliterate the opening).
    """
    rings = [l for l in loops if len(l) == 40]
    if len(rings) != 2: raise ValueError('EXPECTED_TWO_40_VERTEX_RIMS')
    area = []
    for loop in rings:
        pts = v[loop]
        if np.ptp(pts[:, 1]) > 1e-10 or abs(pts[0, 1]-2.4) > 1e-8:
            raise ValueError('RIMS_NOT_COPLANAR')
        area.append(float(np.sum(pts[:, 0] * np.roll(pts[:, 2], -1) -
                                       np.roll(pts[:, 0], -1) * pts[:, 2])))
    if area[0]*area[1] >= 0: raise ValueError('RIM_ORIENTATIONS_NOT_OPPOSITE')
    radii = [float(np.mean(np.linalg.norm(v[l][:, [0,2]], axis=1))) for l in rings]
    outer, inner = (rings[0], rings[1]) if radii[0] > radii[1] else (rings[1], rings[0])
    inner_rev = inner[::-1]
    start = int(np.argmin(np.linalg.norm(v[inner_rev][:, [0,2]] - v[outer[0], [0,2]], axis=1)))
    inner_rev = inner_rev[start:]+inner_rev[:start]
    errors = [float(np.linalg.norm(v[o, [0,2]] / np.linalg.norm(v[o, [0,2]]) -
                                   v[i, [0,2]] / np.linalg.norm(v[i, [0,2]])))
              for o, i in zip(outer, inner_rev)]
    if max(errors) > 0.01 or min(radii) < 1: raise ValueError('RIM_MATCH_FAILED')
    f = []
    for i in range(len(outer)):
        j = (i+1) % len(outer)
        f.append([outer[j], outer[i], inner_rev[i]])
        f.append([outer[j], inner_rev[i], inner_rev[j]])
    return f, dict(loop_sizes=[len(x) for x in rings], radii=radii,
                   max_direction_matching_error=max(errors), added_triangles=len(f))


def split_bowties(v, f):
    fans = vertex_fans(f, len(v)); out_v=v.tolist(); out_f=f.copy()
    records = []
    for vertex in sorted(fans):
        for fan in fans[vertex][1:]:
            new_id = len(out_v); out_v.append(v[vertex].tolist())
            for face in fan:
                for corner in range(3):
                    if out_f[face, corner] == vertex: out_f[face, corner] = new_id
            records.append(dict(original_vertex=vertex, duplicate_vertex=new_id,
                                coordinate=v[vertex].tolist(), affected_faces=len(fan)))
    return np.asarray(out_v), out_f, records


def closed_surface_checks(v, f):
    edges = edge_map(f); bad_edges = sum(len(es)!=2 for es in edges.values())
    reversed_faces = sum(len(es)==2 and es[0][:2]==es[1][:2] for es in edges.values())
    bowties = vertex_fans(f, len(v))
    positive_area = bool(np.all(np.linalg.norm(np.cross(v[f[:, 1]]-v[f[:, 0]],
                                                     v[f[:, 2]]-v[f[:, 0]]), axis=1) > 1e-14))
    return dict(boundary_or_nonmanifold_edges=bad_edges, winding_conflicts=reversed_faces,
                bowtie_vertices=len(bowties), strictly_positive_triangle_areas=positive_area,
                topologically_closed=bool(bad_edges==0 and reversed_faces==0 and
                                          not bowties and positive_area))


def _tri_overlap(a, b, eps=1e-10):
    """Conservative triangle SAT; touching counts as potential intersection."""
    ea = np.roll(a, -1, axis=0)-a
    eb = np.roll(b, -1, axis=0)-b
    na = np.cross(ea[0], ea[1]); nb=np.cross(eb[0], eb[1])
    axes = [na, nb]
    axes += [np.cross(x, y) for x in ea for y in eb]
    axes += [np.cross(n, e) for n, edges in ((na, ea), (nb, eb)) for e in edges]
    for axis in axes:
        norm = float(np.linalg.norm(axis))
        if norm < 1e-15: continue
        pa = a @ axis; pb = b @ axis
        margin = eps * norm
        if pa.max() < pb.min() - margin or pb.max() < pa.min() - margin:
            return False
    return True


def intersection_witnesses(v, f, witness_limit=12):
    """Independent triangle overlap preflight (not an exact CGAL certificate)."""
    tri = v[f]; lo = tri.min(axis=1); hi = tri.max(axis=1)
    order = np.argsort(lo[:, 0], kind='stable'); witnesses=[]; pairs=0
    # Sweep-and-prune conservative AABB candidates, excluding incident pairs.
    for pos, i0 in enumerate(order):
        i = int(i0)
        for j0 in order[pos+1:]:
            j=int(j0)
            if lo[j,0] > hi[i,0]+1e-10: break
            if np.any(lo[i,1:] > hi[j,1:]+1e-10) or np.any(lo[j,1:] > hi[i,1:]+1e-10): continue
            if np.intersect1d(f[i], f[j]).size: continue
            pairs+=1
            if _tri_overlap(tri[i], tri[j]):
                witnesses.append([int(i),int(j)])
                if len(witnesses) >= witness_limit:
                    return dict(status='WITNESSES_FOUND_NOT_EXHAUSTIVE',
                                broadphase_checked_pairs=pairs, witness_face_pairs=witnesses)
    return dict(status='NO_SAT_WITNESSES_NOT_EXACT_PROOF',
                broadphase_checked_pairs=pairs, witness_face_pairs=witnesses)



def connected_components(v, f):
    parent = np.arange(len(v))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a,b,c in f:
        a,b,c = map(int,(a,b,c))
        for y in (b,c):
            ra, rb = root(a),root(y)
            if ra != rb: parent[rb]=ra
    pieces = defaultdict(list)
    for i, face in enumerate(f): pieces[root(int(face[0]))].append(i)
    volumes = [signed_volume_and_moments(v,f[np.asarray(ff, dtype=int)])[0]
               for ff in pieces.values()]
    return dict(count=len(pieces), face_counts=sorted(map(len,pieces.values())),
                signed_volumes=sorted(volumes),
                euler_characteristic=int(len(v)-len(edge_map(f))+len(f)))


def prepare(src, out, require_certified=False, strict_source=True):
    src=Path(src); out=Path(out); out.mkdir(parents=True, exist_ok=True)
    sha=hashlib.sha256(src.read_bytes()).hexdigest()
    if strict_source and sha != SOURCE_SHA256: raise ValueError('SOURCE_SHA256_MISMATCH')
    raw_v, raw_f = read_obj(src)
    verts, inverse = np.unique(raw_v, axis=0, return_inverse=True)
    faces = inverse[raw_f]
    loops, n_edges=boundary_loops(faces)
    if strict_source and (len(raw_v),len(raw_f),len(loops),n_edges)!=(3644,6320,6,160):
        raise ValueError('ORIGINAL_SOURCE_TOPOLOGY_CHANGED')
    original_fans = vertex_fans(faces,len(verts))
    annulus, annulus_meta = stitch_rings(verts, loops)
    rest = [l for l in loops if len(l) != 40]
    if len(rest)!=4 or any(len(l)!=20 for l in rest): raise ValueError('UNEXPECTED_SMALL_LOOPS')
    vv=verts.tolist(); ff=faces.tolist()+annulus
    caps=[]
    for loop in rest:
        center=np.mean(verts[loop], axis=0)
        index=len(vv);vv.append(center.tolist())
        for i,a in enumerate(loop): ff.append([loop[(i+1)%len(loop)],a,index])
        caps.append(dict(centroid=center.tolist(),loop_length=len(loop),
                         max_plane_x_deviation=float(np.max(np.abs(verts[loop,0]-center[0]))),
                         added_triangles=len(loop)))
    candidate_v, candidate_f, splits=split_bowties(np.asarray(vv),np.asarray(ff,dtype=np.int64))
    closed=closed_surface_checks(candidate_v,candidate_f)
    vol, first, second, cm, inertia=signed_volume_and_moments(candidate_v,candidate_f)
    source_pseudovol=signed_volume_and_moments(raw_v,raw_f)[0]
    components=connected_components(candidate_v,candidate_f)
    intersects=intersection_witnesses(candidate_v,candidate_f)
    # The known coincident bow-tie point and any SAT hit both prohibit certification.
    # Strict exact polyhedral Boolean/point-contact certification is NOT provided here.
    blockers=[]
    if not closed['topologically_closed']: blockers.append('TOPOLOGY_NOT_CLOSED')
    if vol <= 0: blockers.append('NONPOSITIVE_SIGNED_VOLUME')
    if intersects['witness_face_pairs']: blockers.append('SURFACE_INTERSECTION_WITNESSES')
    if splits: blockers.append('COINCIDENT_POINT_CONTACT_REQUIRES_TRUE_UNION')
    blockers.append('EXACT_SELF_INTERSECTION_AND_SOLID_UNION_UNCERTIFIED')
    blockers.append('W0_AXIS_TIP_FIXED_REMOVABLE_CONTRACT_PENDING')
    blockers.append('W2_REAL_CHERCHI_TEACHER_PENDING')
    obj=out/'teapot-topology-candidate-p1.obj'
    write_obj(obj,candidate_v,candidate_f)
    # Frame transformation is PROPOSED only. It is a proper rotation: (x,y,z)->(x,-z,y).
    # No physical axis tip is inferred from the bottom planar foot.
    report=dict(schema='w4-teapot-p1-candidate-preflight-v1',
        source=dict(sha256=sha,upstream_blob_sha1=SOURCE_UPSTREAM_BLOB,
                    upstream_commit=SOURCE_UPSTREAM_COMMIT,unmodified=True,
                    public_mesh_not_author_cad=True),
        input=dict(vertices=len(raw_v),faces=len(raw_f),geometric_vertices=len(verts),
                   open_edges=n_edges,boundary_loop_lengths=sorted(map(len,loops)),
                   bowtie_vertices=[dict(coordinate=verts[k].tolist(),fans=len(v)) for k,v in original_fans.items()]),
        repairs=dict(exact_position_weld_only=True,source_displacement=0.,
                     joined_lid_and_body_rims=annulus_meta,small_loop_fan_caps=caps,
                     split_nonmanifold_vertex_fans=splits),
        candidate=dict(vertices=len(candidate_v),faces=len(candidate_f),closed_checks=closed,
                       connected_components=components,
                       source_open_signed_pseudovolume=source_pseudovol,
                       pseudovolume_delta=vol-source_pseudovol,
                       pseudovolume_relative_delta=(vol-source_pseudovol)/abs(source_pseudovol),
                       pseudovolume_comparison_is_nonphysical=True,
                       diagnostic_signed_volume=vol,first_moment=first.tolist(),
                       second_raw_moment=second.tolist(),diagnostic_centroid=cm.tolist(),
                       diagnostic_inertia_origin=inertia.tolist(),
                       candidate_obj_sha256=hashlib.sha256(obj.read_bytes()).hexdigest(),
                       conservative_suspected_triangle_contacts=intersects),
        coordinate_plan=dict(original='Y_UP',proposed='Z_UP',proper_rotation_xyz=[[1,0,0],[0,0,-1],[0,1,0]],
                             units='UNDEFINED_AWAIT_W0',physical_axis='UNDEFINED_AWAIT_W0',
                             tip='UNDEFINED_AWAIT_W0',fixed_F='NOT_GENERATED',removable_D='NOT_GENERATED'),
        optimization_ablation_registry=[dict(name=n,status='BLOCKED_NOT_RUN') for n in
                                        ('FIG9_INERTIA_ONLY','FIG9_CENTER_LOWERING_ONLY','FIG9_MASS_REDUCTION_ONLY')],
        geometry_legal=False,physical_moments_authoritative=False,optimized=False,
        acceptance='BLOCKED_REPAIR_CANDIDATE_ONLY',blocking_reasons=blockers)
    (out/'p1-preflight.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    moment_values=[vol,*first.tolist(),second[0,0],second[1,1],second[2,2],
                   second[1,2],second[0,2],second[0,1]]
    with (out/'p1-diagnostic-moments.csv').open('w',newline='') as handle:
        writer=csv.writer(handle)
        writer.writerow(['status','frame','density','moment','value'])
        for name,value in zip(('M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY'), moment_values):
            writer.writerow(['NOT_AUTHORIZED_GEOMETRY','RAW_Y_UP','unit_test_density_1',name,f'{value:.17g}'])
    if require_certified and blockers: raise RuntimeError('CERTIFICATION_BLOCKED: '+','.join(blockers))
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--require-certified',action='store_true')
    p.add_argument('--allow-fixture',action='store_true')
    args=p.parse_args()
    result=prepare(args.input,args.output,args.require_certified,not args.allow_fixture)
    print(json.dumps(dict(status=result['acceptance'],source_sha256=result['source']['sha256'],
                          topological=result['candidate']['closed_checks'],
                          blockers=result['blocking_reasons'],
                          witnesses=result['candidate']['conservative_suspected_triangle_contacts']),indent=2))

"""W2 M20: independently test six *exact rational* Noodles CSG bodies.

There is no historical CGAL executable or six saved packets in this runtime.
Original byte identity and independent geometric/physical claims are separate.
Ten-moment inclusion-exclusion is NECESSARY, NOT a set equality or smoothness proof.
No Cherchi sampling/Jacobian/new training data is created by this module.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

try:
    from . import m19_noodles_fda_audit as m19
except ImportError:
    import m19_noodles_fda_audit as m19

PACKETS = m19.PACKETS
MAX_EXACT_PACKET_BYTES = 100_000_000
MAX_VERTICES = 600_000
MAX_FACES = 1_000_000
EXACT_ALGEBRA_RELATIONS = (
    ('envelope', 'design', 'fixed-inside-envelope'),
    ('fixed', 'fixed-inside-envelope', 'fixed-outside-envelope'),
    ('initial', 'envelope', 'fixed-outside-envelope'),
    ('initial', 'design', 'fixed'),
)


class AdmissionError(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise AdmissionError(message)


def frac(value):
    """Only exact integers and signed rational tokens; NO floats or booleans."""
    if type(value) is int:
        return Fraction(value)
    require(type(value) is str and re.fullmatch(r'-?(?:0|[1-9]\d*)/(?:[1-9]\d*)', value),
            'COORDINATE_REQUIRES_EXACT_RATIONAL_TOKEN')
    return Fraction(value)


def _packet(raw, name):
    """Parse an exact triangle-surface packet, never infer raster/float geometry."""
    obj=m19.json_strict(raw)
    require(type(obj) is dict,'PACKET_OBJECT_REQUIRED:'+name)
    require('vertices' in obj and 'faces' in obj, 'PACKET_VERTEX_FACE_ARRAYS_REQUIRED:'+name)
    vv=obj['vertices']; ff=obj['faces']
    require(type(vv) is list and type(ff) is list and
            4<=len(vv)<=MAX_VERTICES and 4<=len(ff)<=MAX_FACES,
            'PACKET_GEOMETRY_SIZE_INVALID:'+name)
    vertices=[]
    for p in vv:
        require(type(p) is list and len(p)==3,'EXACT_VERTEX_ARITY:'+name)
        vertices.append(tuple(frac(x) for x in p))
    faces=[]
    for face in ff:
        require(type(face) is list and len(face)==3 and
                all(type(v) is int and 0<=v<len(vertices) for v in face) and
                len(set(face))==3,'INVALID_TRIANGLE:'+name)
        faces.append(tuple(face))
    return vertices,faces


def _exact_signed_ten(vertices,faces):
    """Independent signed-tetra integration over precise CGAL fractions."""
    result=[Fraction(0) for _ in range(10)]
    for ia,ib,ic in faces:
        a,b,c=vertices[ia],vertices[ib],vertices[ic]
        det=(a[0]*(b[1]*c[2]-b[2]*c[1])+
             a[1]*(b[2]*c[0]-b[0]*c[2])+
             a[2]*(b[0]*c[1]-b[1]*c[0]))
        v=det/6
        result[0]+=v
        s=[a[i]+b[i]+c[i] for i in range(3)]
        for i in range(3):result[1+i]+=v*s[i]/4
        for pos,(i,j) in enumerate(m19.PAIR_ORDER,4):
            result[pos]+=v*(s[i]*s[j]+a[i]*a[j]+b[i]*b[j]+c[i]*c[j])/20
    require(result[0]>0,'NONPOSITIVE_OR_REVERSED_SOLID_MASS')
    return result


def _orientation(faces):
    oriented=Counter()
    for a,b,c in faces:
        oriented.update(((a,b),(b,c),(c,a)))
    require(all(n==1 and oriented[(b,a)]==1 for (a,b),n in oriented.items()),
            'NOT_CLOSED_OR_ORIENTED_TWO_MANIFOLD')
    return len(oriented)//2


def inspect_six_packets(directory,expected_sha,expected_faces,*,historic_sha_required):
    """When real packets exist, require original SHA/face count and exact math.

    Returns a necessary algebraic/topology audit only. It cannot certify that
    the bodies are the result of the frozen Boolean operations or embedded.
    """
    require(set(expected_sha)==set(PACKETS)==set(expected_faces),
            'SIX_EXTERNAL_PACKET_IDENTITIES_REQUIRED')
    root=Path(directory)
    require(root.is_dir() and not root.is_symlink(),'PACKET_DIRECTORY_MISSING')
    samples={}; sha_ledger={}
    for name in PACKETS:
        p=root/(name+'-rational.json')
        require(p.is_file() and not p.is_symlink(),'MISSING_OR_SYMLINK_CSG_PACKET:'+name)
        require(p.stat().st_size<=MAX_EXACT_PACKET_BYTES,'CSG_PACKET_TOO_LARGE:'+name)
        data=p.read_bytes()
        real_sha=hashlib.sha256(data).hexdigest()
        require(re.fullmatch(r'[0-9a-f]{64}',expected_sha[name]) is not None and
                real_sha==expected_sha[name],'CSG_PACKET_SHA_MISMATCH:'+name)
        verts,faces=_packet(data,name)
        require(len(faces)==expected_faces[name],'CSG_PACKET_FACE_COUNT_MISMATCH:'+name)
        edges=_orientation(faces)
        moments=_exact_signed_ten(verts,faces)
        samples[name]=(moments,len(verts),len(faces),edges)
        sha_ledger[name]=real_sha
    for whole,left,right in EXACT_ALGEBRA_RELATIONS:
        totals=samples[whole][0]
        a,b=samples[left][0],samples[right][0]
        require(all(t==x+y for t,x,y in zip(totals,a,b)),
                'EXACT_FDA_MOMENT_RELATION_FAILED:'+whole+'='+left+'+'+right)
    return {
      'schema':'w2-m20-exact-six-packet-necessary-algebra-audit-v1',
      'six_packet_sha_matched':6,'historical_receipt_sha_pinned':historic_sha_required,
      'oriented_closed_indexed_surfaces':6,'exact_ten_moment_components':60,
      'exact_additive_relations':len(EXACT_ALGEBRA_RELATIONS),
      'ratios_and_float_reprojection_used':False,
      'per_packet':{n:dict(sha256=sha_ledger[n],vertices=samples[n][1],
                 triangles=samples[n][2],undirected_edges=samples[n][3],
                 volume=str(samples[n][0][0])) for n in PACKETS},
      'boolean_semantics_independently_proven':False,
      'embedding_and_self_intersection_certified':False,
      'binary64_FDA_partition_certified':False,
      'native_cherchi_call_performed':False,
      'jacobian_J_D':None,
      'training_admitted':0,
    }


def historic_expectations(receipt_bytes):
    receipt=m19.pinned_json(receipt_bytes,m19.CSG_RECEIPT_SHA256,
             m19.CSG_RECEIPT_GIT_BLOB,'HISTORIC_CSG_RECEIPT')
    require(receipt['manifest_sha']==m19.SOURCE_MANIFEST_SHA256 and
            receipt['backend_sha']==m19.HISTORIC_CSG_BACKEND_SHA256 and
            receipt['csg_executed_current_process']==96 and
            receipt['independent_partition_verified'] is False,
            'HISTORICAL_RECEIPT_UNSUPPORTED_PROMOTION')
    require(set(receipt['outputs'])==set(PACKETS),'INCOMPLETE_HISTORIC_SIX')
    expected_sha={k:v['sha'] for k,v in receipt['outputs'].items()}
    expected_faces={k:v['faces'] for k,v in receipt['outputs'].items()}
    return expected_sha,expected_faces


def local_native_preflight(backend=None):
    """Observe real native availability, never invoke missing/unpinned CGAL."""
    cgroup=Path('/sys/fs/cgroup/memory.max')
    limit=None
    if cgroup.is_file():
        value=cgroup.read_text().strip()
        if value!='max':limit=int(value)
    backend_file=Path(backend) if backend else None
    existing=(backend_file is not None and backend_file.is_file() and
              not backend_file.is_symlink())
    backend_hash=m19.sha256_bytes(backend_file.read_bytes()) if existing else None
    return {'observed_cgroup_memory_bytes':limit,
            'required_effective_memory_bytes':24*1024**3,
            'historical_CGAL_backend_binary_present':bool(existing),
            'original_expected_backend_sha256':m19.HISTORIC_CSG_BACKEND_SHA256,
            'backend_sha_matches_historic':bool(existing and backend_hash==m19.HISTORIC_CSG_BACKEND_SHA256),
            'backend_protocol_and_compilation_provenance_verified':False,
            'native_launch_authorized':False,
            'reason':'MISSING_PINNED_CGAL_BACKEND_OR_MEMORY_OR_VERIFIED_COMMAND_PROTOCOL'}


def review(source_bundle, *, csg_dir=None, backend=None):
    begun=time.monotonic()
    inputs=m19.audit_source_bundle(source_bundle,exact_all_parts=False)
    require(inputs['source_parts_identity_checked']==94 and
            inputs['original_obj_sha256_verified']==188 and
            inputs['original_historic_exact_CSG_calls']==96,
            'FROZEN_SOURCE_ARCHIVE_IDENTITY_DRIFT')
    from zipfile import ZipFile
    with ZipFile(source_bundle) as z:
        receipt=m19.zip_member(z,m19.BUNDLE_CSG_RECEIPT)
    shas,faces=historic_expectations(receipt)
    report={'schema':'w2-m20-noodles-fda-historical-recovery-v1',
            'status':'BLOCKED_NO_SIX_PINNED_RATIONAL_CSG_PACKET_BYTES',
            'source_bundle_sha256':inputs['bundle_sha256'],
            'source_parts_verified':94,'model_and_SI_sources_verified':188,
            'source_binary64_exact_moments_covered_by_M19':940,
            'historical_CGAL_boolean_count_reported_not_reexecuted':96,
            'historic_6_outputs_expected':[
               dict(name=k,sha256=shas[k],faces=faces[k]) for k in PACKETS],
            'historic_source_manifest_sha256':m19.SOURCE_MANIFEST_SHA256,
            'historic_CSG_receipt_sha256':m19.CSG_RECEIPT_SHA256,
            'historical_CSG_partition_proof_exists':False,
            'current_native_preflight':local_native_preflight(backend),
            'native_new_CSG_operations':0,'new_Cherchi_teacher_calls':0,
            'training_admitted':0,'J_D':None,
            'required_next_proof':'RECOVER_OR_RECOMPUTE_EXACT_SIX_FDA_AND_CERTIFY_BOOLEAN_SEMANTICS_NOT_ONLY_MOMENTS'}
    if csg_dir:
        # Import historic packets ONLY if all six originally saved bytes match.
        # Do not continue on subset, drift, or unauthenticated candidate packets.
        report['six_packet_audit']=inspect_six_packets(
            csg_dir,shas,faces,historic_sha_required=True)
        report['status']='HISTORIC_SIX_REBOUND_MOMENT_ALGEBRA_PASSED_BUT_GEOMETRY_UNCERTIFIED'
    report['elapsed_seconds']=time.monotonic()-begun
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-bundle',required=True)
    p.add_argument('--csg-dir')
    p.add_argument('--backend')
    p.add_argument('--output',required=True)
    a=p.parse_args(argv)
    try:
        output=review(a.source_bundle,csg_dir=a.csg_dir,backend=a.backend)
        m19._atomic_exclusive_json(a.output,output)
        print(json.dumps({'status':output['status'],
          'six_historical_packets_accepted':output.get('six_packet_audit',{}).get('six_packet_sha_matched',0),
          'new_native_CGAL_operations':0,'training_admitted':0},sort_keys=True))
        # A math-only check cannot issue a native teacher even when packets exist.
        return 2
    except (AdmissionError,m19.GateError,KeyError,ValueError,FileNotFoundError) as exc:
        print(json.dumps({'status':'REJECTED','error':str(exc),
                          'new_native_CGAL_operations':0,'training_admitted':0}),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())

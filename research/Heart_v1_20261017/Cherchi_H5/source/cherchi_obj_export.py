"""Optional Cherchi retained-material postprocessor, never a Boolean fallback.

This lives OUTSIDE Newton's geometry evaluator: accepted q/material/derivative
and all scientific hashes must remain unchanged. The export is target-frame
only. A failed exact/float audit emits a rejection record but **no OBJ**.
"""
from __future__ import annotations
import argparse
import time
import hashlib
import json
import os
import re
from pathlib import Path
from fractions import Fraction

import numpy as np
from cherchi_exact_flip import (fractional_vertices, safe_flips, assert_local_flip,
                                pick_choices, exact_plane_chain, ten_moments)

CHERCHI_BOOL='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0-inprocess-v1'
CHERCHI_ID_PREFIX='cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def bound_packet(packet, *, formal):
    if not isinstance(packet,dict):raise ValueError('CHERCHI_PACKET_REQUIRED')
    if formal:
        if not isinstance(packet.get('boolean_backend_identity'),str) or not packet['boolean_backend_identity'].startswith(CHERCHI_ID_PREFIX):
            raise ValueError('FORMAL_CHERCHI_BACKEND_REQUIRED')
        proof=packet.get('material_proof')
        if not isinstance(proof,dict) or proof.get('schema')!='cherchi-same-call-material-v1' or not proof.get('construction_records'):
            raise ValueError('SAME_CALL_CHERCHI_PROVENANCE_REQUIRED')
        for field in ('geometry_hash','topology_hash','evaluation_map_identity','quadric_source_identity'):
            if not packet.get(field):raise ValueError('SAME_CALL_FIELD_MISSING:'+field)
        if packet.get('derivative_defined') is not True:
            raise ValueError('ACCEPTED_DERIVATIVE_REQUIRED')
        if len(packet.get('quadric_coefficients',[]))!=10 or len(packet.get('variable_raw_moments',[]))!=10:
            raise ValueError('SOLVER_MOMENT_AND_QUADRIC_REQUIRED')
        exact=packet.get('variable_rational_vertices');floats=packet.get('variable_vertices');faces=packet.get('variable_faces')
    else:
        if packet.get('backend')!=CHERCHI_BOOL:
            raise ValueError('CHERCHI_BACKEND_REQUIRED_NO_FALLBACK')
        if not isinstance(packet.get('construction_records'),list):
            raise ValueError('CHERCHI_CONSTRUCTION_RECORDS_REQUIRED')
        exact=packet.get('exact_vertices');floats=packet.get('vertices');faces=packet.get('faces')
    r=fractional_vertices(exact)
    v=np.asarray(floats,dtype=np.float64)
    f=np.asarray(faces)
    if v.shape!=(len(r),3) or not np.isfinite(v).all() or not np.array_equal(v,np.asarray([[float(y) for y in x] for x in r])):
        raise ValueError('RATIONAL_FLOAT_VIEW_NOT_IDENTICAL')
    if f.ndim!=2 or f.shape[1:]!=(3,) or not np.issubdtype(f.dtype,np.integer) or f.size==0 or f.min()<0 or f.max()>=len(v) or f.max()>2147483647:
        raise ValueError('INVALID_CHERCHI_FACE_INDICES')
    if formal and len(proof['construction_records'])!=len(v):
        raise ValueError('CHERCHI_PROVENANCE_LENGTH_MISMATCH')
    if not formal and len(packet['construction_records'])!=len(v):
        raise ValueError('CHERCHI_PROVENANCE_LENGTH_MISMATCH')
    return v,np.asarray(f,dtype=np.int32),r,exact

def native_audit(native,verts,faces,*,exact=False):
    tick=time.perf_counter()
    if exact:
        result=dict(native.audit_exact_rational_triangle_boundary(verts,np.asarray(faces,dtype=np.int32),'AnyNonzero'))
    else:
        result=dict(native.audit_exact_triangle_boundary(verts,np.asarray(faces,dtype=np.int32),'AnyNonzero'))
    if os.environ.get("HEART_H5_TRACE"):
        print(f"H5 native audit exact={exact} time={time.perf_counter()-tick:.3f}s intersections={len(result.get('intersecting_pairs',[]))} valid={result.get('boundary_valid')}",flush=True)
    return result

def complete(a):
    return a.get('self_intersection_completed') is True and not a.get('intersection_error')

def qualified(a):
    return a.get('boundary_valid') is True and a.get('self_intersection_free') is True and complete(a) and not a.get('intersecting_pairs') and not a.get('degenerate_faces')

def write_obj(path,v,f,classification):
    with Path(path).open('w',encoding='ascii',newline='\n') as out:
        out.write('# Cherchi certified retained material; frame=TARGET_NORMALIZED; scope='+classification+'\n')
        for row in v:out.write('v '+' '.join(format(float(x),'.17g') for x in row)+'\n')
        for row in f:out.write('f '+' '.join(str(int(x)+1) for x in row)+'\n')

def read_obj(path):
    vv=[];ff=[]
    for line in Path(path).read_text().splitlines():
        if line.startswith('v '):vv.append([float(t) for t in line.split()[1:]])
        elif line.startswith('f '):ff.append([int(t)-1 for t in line.split()[1:]])
    return np.asarray(vv,dtype=np.float64),np.asarray(ff,dtype=np.int32)

def certified_export(packet,output_dir,*,native,scope,formal=False,accepted_run=None,expected_native_sha256,max_rounds=18):
    """Produce one extra certified OBJ *without changing* packet or Newton records."""
    output_dir=Path(output_dir)
    if output_dir.exists():raise FileExistsError('OUTPUT_DIRECTORY_MUST_BE_NEW')
    output_dir.mkdir(parents=True)
    record={'schema':'heart-h5-cherchi-retained-sidecar-v1','qualified':False,
            'scope':scope,'formal_accepted':bool(formal),
            'original_eval60_reproduced':False,'heart_newton_run_performed_here':False,
            'complete_heart_assembly':False,'physical_contact_passed':False,
            'coordinate_frame':'TARGET_NORMALIZED','dynamic_boolean_backend':'CHERCHI_ONLY'}
    try:
        if formal:
            if accepted_run is None:
                raise ValueError('FORMAL_ACCEPTED_RUN_BINDING_REQUIRED')
            sealed=load_accepted_formal_record(accepted_run)
            if sealed!=packet:
                raise ValueError('FORMAL_RUN_PACKET_NOT_IDENTICAL_TO_LOCKED_TERMINAL_RECORD')
        if not isinstance(expected_native_sha256,str) or len(expected_native_sha256)!=64 or sha(native.__file__)!=expected_native_sha256:
            raise ValueError('NATIVE_BINARY_IDENTITY_MISMATCH')
        v,faces,r,exact_tokens=bound_packet(packet,formal=formal)
        print("H5 bound packet",flush=True) if os.environ.get("HEART_H5_TRACE") else None
        before=faces.copy();prev=native_audit(native,exact_tokens,faces,exact=True)
        if not qualified(prev):raise ValueError('ORIGINAL_RATIONAL_CHERCHI_BOUNDARY_INVALID')
        fl=native_audit(native,v,faces)
        initial_intersections=len(fl.get('intersecting_pairs',[]))
        if not complete(fl):raise ValueError('ORIGINAL_FLOAT_AUDIT_INCOMPLETE')
        operations=[];rounds=0
        while not qualified(fl):
            print(f"H5 round {rounds} intersections {len(fl.get('intersecting_pairs',[]))}",flush=True) if os.environ.get("HEART_H5_TRACE") else None
            if rounds>=max_rounds:raise ValueError('MAXIMUM_EXACT_FLIP_ROUNDS_EXCEEDED')
            clashes=fl.get('intersecting_pairs',[])
            if not clashes:raise ValueError('UNREPAIRABLE_FLOAT_GEOMETRY_NOT_COLLISIONS')
            choices=pick_choices(safe_flips(faces,v,r,clashes),initial=rounds==0)
            if not choices:raise ValueError('NO_EXACT_SAFE_FLIP_CANDIDATE')
            attempt=faces.copy()
            for choice in choices:
                i,j=choice['faces']
                attempt[i],attempt[j]=choice['after']
                assert_local_flip(faces,attempt,(i,j),r)
            next_audit=native_audit(native,v,attempt)
            if not complete(next_audit) or len(next_audit.get('intersecting_pairs',[]))>=len(clashes):
                raise ValueError('FLOAT_COLLISIONS_NOT_STRICTLY_REDUCED')
            operations.append({'round':rounds+1,'before_intersections':len(clashes),
                  'after_intersections':len(next_audit.get('intersecting_pairs',[])),
                  'flips':[{'face_indices':list(c['faces']), 'old':[list(t) for t in c['before']],
                    'new':[list(t) for t in c['after']]} for c in choices]})
            faces=attempt;fl=next_audit;rounds+=1
        print("H5 checking chains",flush=True) if os.environ.get("HEART_H5_TRACE") else None
        if exact_plane_chain(before,r)!=exact_plane_chain(faces,r):
            raise ValueError('GLOBAL_RATIONAL_PLANE_CHAIN_CHANGED')
        print("H5 original global moments",flush=True) if os.environ.get("HEART_H5_TRACE") else None
        # Every unmodified face appears identically in both complete sums;
        # cancel them symbolically *before* expensive GMP-sized rational adds.
        # This is exact GLOBAL moment equality, not a floating approximation.
        changed_ids=np.flatnonzero(np.any(before!=faces,axis=1))
        before_moments=ten_moments(before[changed_ids],r)
        print("H5 candidate changed-face moments",flush=True) if os.environ.get("HEART_H5_TRACE") else None
        after_moments=ten_moments(faces[changed_ids],r)
        if before_moments!=after_moments:raise ValueError('GLOBAL_TEN_EXACT_RAW_MOMENTS_CHANGED')
        print("H5 final rational audit",flush=True) if os.environ.get("HEART_H5_TRACE") else None
        final_exact=native_audit(native,exact_tokens,faces,exact=True)
        if not qualified(final_exact):raise ValueError('FINAL_RATIONAL_NATIVE_AUDIT_FAILED')
        candidate=output_dir/'retained-target-normalized.obj.tmp'
        write_obj(candidate,v,faces,scope)
        vl,flr=read_obj(candidate)
        if not np.array_equal(vl,v) or not np.array_equal(flr,faces):
            raise ValueError('FLOAT_OBJ_ROUNDTRIP_CHANGED')
        exported=native_audit(native,vl,flr)
        if not qualified(exported):raise ValueError('OBJ_NATIVE_FLOAT_AUDIT_FAILED')
        final_path=output_dir/'retained-target-normalized.obj'
        os.replace(candidate,final_path)
        record.update({'qualified':True,'initial_intersections':initial_intersections,
            'final_intersections':0,'flip_count':sum(len(x['flips']) for x in operations),
            'round_count':rounds,'vertex_count':len(v),'triangle_count':len(faces),
            'changed_face_rows':int(np.sum(np.any(before!=faces,axis=1))),
            'global_exact_plane_chain_equal':True,'exact_ten_raw_moments_equal':True,
            'exact_ten_moments_proof':'COMPLETE_SUM_DIFFERENCE_BY_CANCELING_IDENTICAL_UNCHANGED_FACE_ROWS',
            'final_rational_native_boundary_passed':True,'final_float_native_boundary_passed':True,
            'obj_sha256':sha(final_path),'obj_bytes':final_path.stat().st_size,
            'native_binary_sha256':expected_native_sha256})
        (output_dir/'operations.json').write_text(json.dumps(operations,indent=2)+'\n')
        (output_dir/'certification.json').write_text(json.dumps(record,indent=2)+'\n')
        return record
    except Exception as exc:
        for p in output_dir.glob('*.obj*'):
            p.unlink()
        record['rejection']=f'{type(exc).__name__}: {exc}'
        (output_dir/'rejected.json').write_text(json.dumps(record,indent=2)+'\n')
        raise

def load_accepted_formal_record(run):
    """Strict durable record binding; never reconstruct a missing q or evaluate another backend."""
    run=Path(run)
    def get(name):
        p=run/name
        if not p.is_file():raise ValueError('MISSING_ACCEPTED_RUN_FILE:'+name)
        return json.loads(p.read_text())
    result=get('result.json');done=get('complete.json');check=get('record-verification.json')
    native=get('native-result.json');ref=get('terminal-material-reference.json')
    conf=get('configuration.json')
    sealed_identity=result.get('identity',{})
    if not isinstance(sealed_identity,dict):raise ValueError('INVALID_FORMAL_SCIENTIFIC_IDENTITY')
    sealed_complement=sealed_identity.get('terminal_complement',{})
    binding=sealed_identity.get('external_terminal_binding',{})
    if (result.get('status')!='CONVERGED' or done.get('status')!='CONVERGED' or done.get('complete') is not True or
        not isinstance(sealed_complement,dict) or sealed_complement.get('status')!='PASSED' or
        not isinstance(binding,dict) or not binding.get('retained_geometry') or
        native.get('native_run',{}).get('status')!='CONVERGED' or
        check.get('record_integrity_valid') is not True or check.get('accepted_updates',0)<=0):
        raise ValueError('FORMAL_ACCEPTED_SEALED_EVIDENCE_REQUIRED')
    if sha(run/'configuration.json')!=native.get('configuration_sha256'):
        raise ValueError('FROZEN_FORMAL_CONFIGURATION_DIGEST_MISMATCH')
    fn=ref.get('evaluation_file')
    if not isinstance(fn,str) or re.fullmatch(r'evaluation-[0-9]{6}\.json',fn) is None:
        raise ValueError('INVALID_TERMINAL_EVALUATION_REFERENCE')
    packet=get(fn)
    if ref.get('sha256')!=sha(run/fn) or ref.get('geometry_hash')!=packet.get('geometry_hash') or binding['retained_geometry']!=packet.get('geometry_hash'):
        raise ValueError('TERMINAL_RECORD_MATERIAL_BINDING_MISMATCH')
    if ref.get('coefficients')!=packet.get('quadric_coefficients') or ref.get('coefficients')!=native['native_run'].get('quadric_coefficients'):
        raise ValueError('TERMINAL_NEWTON_COEFFICIENTS_MISMATCH')
    if not isinstance(conf.get('boolean_backend_identity'),str) or not conf['boolean_backend_identity'].startswith(CHERCHI_ID_PREFIX) or conf['boolean_backend_identity']!=packet.get('boolean_backend_identity'):
        raise ValueError('CHERCHI_FORMAL_PRODUCER_IDENTITY_MISMATCH')
    return packet

def main():
    ap=argparse.ArgumentParser(description='Fail-closed optional Cherchi retained OBJ export')
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--h1-proxy-packet',type=Path)
    group.add_argument('--formal-run',type=Path)
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--expected-native-sha256',required=True)
    args=ap.parse_args()
    import _make_it_stand as native
    if args.formal_run is not None:
        packet=load_accepted_formal_record(args.formal_run)
        scope='ACCEPTED_FORMAL_CHERCHI_RETAINED_TARGET_FRAME_ONLY_NOT_COMPLETE_HEART'
        formal=True
    else:
        packet=json.loads(args.h1_proxy_packet.read_text())
        scope='ARCHIVED_HEART_V4_PROXY_NOT_AUTHORITATIVE_EVAL60'
        formal=False
    print(json.dumps(certified_export(packet,args.output,native=native,scope=scope,formal=formal,
            expected_native_sha256=args.expected_native_sha256,accepted_run=args.formal_run),indent=2))
if __name__=='__main__':main()

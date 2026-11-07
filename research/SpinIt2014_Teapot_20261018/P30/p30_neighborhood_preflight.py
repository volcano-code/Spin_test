#!/usr/bin/env python3
"""W4 P30: freeze genuine P27 c/J and plan unexecuted W0 tangent probes.

A plan is NOT a derivative sample, smooth-neighborhood proof, Newton approval,
training sample, or owner approval. No native geometry is evaluated here.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import math
from pathlib import PurePosixPath, Path
import re
import struct
import tarfile

ARCHIVE_SHA = '6827a0951ce8201e4bea5585ba4e2b485b4652c830604b06592e5a0146583e89'
MANIFEST_SHA = '3a9b6b21d1d1185e00d1ef25a1bfc625d4696f554c3ab4a7719f5d85ca109773'
LOCK_SHA = '451d8b46cd047325b0b3e2d406f9e89dd0252cece677f5f310ca5abe3c8089a4'
C_SHA = '57ac958304df37ebfd36bc1dddeb32c81a113ed5440f65d959f4b45f2a12e6ca'
J_SHA = '26cf3b5dd53d45a4b80f14319b39d28fa9ef7b8d8be3a915189e90ba077a08a5'
RUN = 'formal-m6-run-20261107T050117Z'
SCHEMA = 'W4_P30_UNEXECUTED_TANGENT_PLAN_V1'
F64 = struct.Struct('<100d')

class PlanRejected(ValueError):
    pass

def need(ok, why):
    if not ok: raise PlanRejected(why)

def sha(b): return hashlib.sha256(b).hexdigest()

def strict_json(b):
    def pairs(rows):
        d = {}
        for k,v in rows:
            need(k not in d, 'DUPLICATE_JSON_KEY:'+k)
            d[k] = v
        return d
    return json.loads(b, object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(PlanRejected('NONFINITE:'+s)))

def canonical_hash(value):
    return sha(json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False).encode('ascii'))

def verify_archive(path):
    data=Path(path).read_bytes()
    need(sha(data)==ARCHIVE_SHA, 'PINNED_P27_ARCHIVE_MISMATCH')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        files = {}
        for item in archive:
            rel=PurePosixPath(item.name)
            need(not rel.is_absolute() and '..' not in rel.parts and
                 not item.issym() and not item.islnk() and
                 rel.as_posix()==item.name, 'UNSAFE_ARCHIVE_PATH')
            if item.isdir(): continue
            need(item.isfile() and item.size<=32*1024**2 and
                 item.name not in files, 'UNSAFE_ARCHIVE_FILE')
            files[item.name]=archive.extractfile(item).read()
    base=RUN+'/'
    def record(name):
        full=base+name
        need(full in files, 'MISSING_P27_ARTIFACT:'+name)
        return files[full]
    mb=record('manifest.json')
    need(sha(mb)==MANIFEST_SHA, 'EXTERNAL_MANIFEST_MISMATCH')
    manifest=strict_json(mb)
    need(manifest['schema']=='W4_P21_REPLAY_BUNDLE_V1' and
         manifest['formal_exit_code']==0 and manifest['formal_executed'] is True and
         manifest['test_only'] is False and
         manifest['collection_completed'] is True and
         manifest['collection_errors']==[] and
         manifest['prerun_lock_sha256']==LOCK_SHA,
         'P27_FORMAL_RECEIPT_INVALID')
    rows=manifest['files'];need(len(rows)==37,'INCOMPLETE_P27_INVENTORY')
    for row in rows:
        name=row['path']; raw=record(name)
        need(sha(raw)==row['sha256'] and len(raw)==row['bytes'],
             'P27_INVENTORY_ITEM_MISMATCH:'+name)
    context=strict_json(record('capture/context.json'))
    material=strict_json(record('capture/000008-material_attachment_serialization-001.json'))
    formal=strict_json(record('formal-report.json'))
    need(formal['status']=='REAL_NATIVE_M6_GEOMETRY_VERIFIED_NO_SCIENTIFIC_RELEASE'
         and formal['native_full_partition_certified'] is True and
         formal['native_call_counts_observed']=={'source':1,'boolean':2} and
         formal['source_files_unchanged'] is True and
         formal['W0_owner_adoption'] is False and
         formal['W2_teacher_training_allowed'] is False and
         formal['smooth_neighborhood_certified'] is False and
         formal['newton_terminal_certified'] is False,
         'FORMAL_M6_SCOPE_NOT_RETAINED')
    need(context['pins']==strict_json(record('inputs/pins.json')) and
         context['pins']['c_sha256']==C_SHA, 'UNPINNED_NATIVE_C')
    c=context['c']; need(type(c) is list and len(c)==10 and
                        all(type(x) is float and math.isfinite(x) for x in c) and
                        abs(math.sqrt(math.fsum(x*x for x in c))-1)<1e-12 and
                        canonical_hash(c)==C_SHA,
                        'NATIVE_C_INVALID')
    need(material['quadric_coefficients']==c and
         material['derivative_defined'] is True, 'SAVED_MATERIAL_COEFFICIENTS_MISMATCH')
    j=material['moment_jacobian'];
    need(type(j) is list and len(j)==10 and
         all(type(row) is list and len(row)==10 and
             all(type(v) is float and math.isfinite(v) for v in row) for row in j),
         'JACOBIAN_MATRIX_INVALID')
    raw=record('capture/000006-derivative-001.f64le')
    need(len(raw)==800 and sha(raw)==J_SHA and
         raw==F64.pack(*(v for row in j for v in row)),
         'SAME_CALL_100_JACOBIAN_BYTES_MISMATCH')
    need(re.fullmatch('[a-f0-9]{64}',material['topology_hash']) is not None,
         'INVALID_TOPOLOGY_DIAGNOSTIC_HASH')
    return {'c':c,'Jc':j,'pins':context['pins'],
            'saved_topology_hash':material['topology_hash'],
            'saved_geometry_hash':material['geometry_hash'],
            'normalization':context['normalization'],
            'material_density_ref':context['request']['material_density']}

def gram_schmidt(c):
    need(len(c)==10 and all(type(x) is float and math.isfinite(x) for x in c),
         'MALFORMED_C')
    norm=math.sqrt(math.fsum(x*x for x in c));need(abs(norm-1)<1e-12,'NONUNIT_C')
    basis=[]
    for axis in range(10):
        vector=[float(k==axis)-c[axis]*x for k,x in enumerate(c)]
        for prev in basis:
            projection=math.fsum(v*t for v,t in zip(vector,prev))
            vector=[v-projection*t for v,t in zip(vector,prev)]
        mag=math.sqrt(math.fsum(v*v for v in vector))
        if mag<1e-9:continue
        vector=[v/mag for v in vector]
        need(abs(math.fsum(x*y for x,y in zip(c,vector)))<1e-10,
             'BAD_TANGENT_ORTHOGONALITY')
        need(all(abs(math.fsum(x*y for x,y in zip(vector,t)))<1e-10 for t in basis),
             'BAD_BASIS_ORTHOGONALITY')
        basis.append(vector)
    need(len(basis)==9,'INCOMPLETE_9D_TANGENT_BASIS')
    return basis

def plan(base, step=0.002):
    need(type(step) is float and 0<step<=0.1, 'INVALID_PREDECLARED_STEP')
    c=base['c'];basis=gram_schmidt(c)
    points=[]
    for i,v in enumerate(basis):
        for name,angle in [('plus_h',step),('minus_h',-step),
                           ('plus_half',step/2),('minus_half',-step/2)]:
            coeff=[math.cos(angle)*a+math.sin(angle)*b for a,b in zip(c,v)]
            need(abs(math.sqrt(math.fsum(x*x for x in coeff))-1)<1e-12,
                 'NONUNIT_PROBE_COEFFICIENTS')
            points.append({'direction_index':i,'stage':'PILOT_3_DIR' if i<3 else 'FULL_9_DIR',
                           'name':name,'angle_radians':angle,
                           'native_c':coeff,'native_c_sha256':canonical_hash(coeff),
                           'observed_material':None,'sample_status':'NOT_EVALUATED'})
    return {
        'schema':SCHEMA,'status':'P30_PROBES_PLANNED_NOT_EVALUATED',
        'evidence':{'run':RUN,'archive_sha256':ARCHIVE_SHA,
                    'manifest_sha256':MANIFEST_SHA,'lock_sha256':LOCK_SHA,
                    'base_native_c_sha256':C_SHA,'same_call_Jc_binary_sha256':J_SHA,
                    'evaluator_context_sha256':base['pins']['context_sha256'],
                    'geometry_hash':base['saved_geometry_hash']},
        'native_c':c,'tangent_basis_columns':basis,
        'pilot_directions':3,'full_directions':9,'pilot_probe_count':12,
        'total_probe_count':36,'step_radians':step,'probes':points,
        'captured_single_point_Jc':base['Jc'],
        'observed_base_topology_hash_not_feature_branch_certificate':base['saved_topology_hash'],
        'verified_feature_branch_sha256':None,
        'owner_approved_physical_tolerances':None,
        'W0_predeclared_max_normalized_jacobian_error':None,
        'planned_native_evaluations':36,'completed_new_native_evaluations':0,
        'native_derivative_neighborhood_certified':False,
        'W0_owner_admitted':False,'W2_teacher_training_allowed':False,
        'Newton_accepted':False,'training_admissible':False,
        'scope':'PLANNING_ONLY_NO_NATIVE_CHERCHI_OR_SMOOTHNESS_PROOF',
    }

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    try:
        result=plan(verify_archive(args.archive))
        need(not args.output.exists(),'NO_OVERWRITE')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
        print(json.dumps({'status':result['status'],'probes':len(result['probes']),
                          'new_native_calls':0,'training_admissible':False},sort_keys=True))
        return 0
    except (PlanRejected,OSError,KeyError,TypeError,ValueError,tarfile.TarError) as e:
        parser.exit(4,'P30_REJECTED: '+str(e)+'\n')

if __name__=='__main__': raise SystemExit(main())

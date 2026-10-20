"""W0 M13: faithful *non-release* interpretation of H8f archived native c.

M1 MomentContractV1 remains a unit-c serialisation contract; DO NOT relax or
silently rewrite it.  A raw source-evaluation c may be nonunit (H8f literal
finite differences). Keep raw c's original numeric values, original source
packet and exact binary64 digest. The signed positive ray is only a separate
*computed diagnostic*, never a byte-identical replacement for the source.

The derivative/Jacobian of r at a re-normalized coordinate is NOT inferred
from the archived dr/dc, and normalized finite differences are NOT substituted
for the actual un-normalized experimental stencil.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
from hashlib import sha256
import gzip
import json
import math
from pathlib import Path
import re
import struct
from zipfile import ZipFile, BadZipFile

import numpy as np

ARCHIVE_SHA256 = '99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9'
REPORT_SHA256 = '28e5a641da153b08a7f15f4abb87336c797f1e85b6f2742fc025274c231f53c5'
REQUEST_SHA256 = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
ROOT = 'artifacts/h8f-all81-points/'
N = 81
UNIT_TOL = 1e-12
B_DIAG = (1.,)*7 + (2.,)*3
HISTORIC_RUN = 39123384402
CHANGED_INDEX = 60

class RawCRejected(ValueError):
    pass


def require(ok, code):
    if not ok:
        raise RawCRejected(code)


def _strict_json(data):
    def pairs(rows):
        obj={}
        for k,v in rows:
            require(k not in obj,'DUPLICATE_JSON_KEY')
            obj[k]=v
        return obj
    def bad_constant(c):
        raise RawCRejected('NONFINITE_JSON_NUMBER:'+c)
    try:
        return json.loads(data,object_pairs_hook=pairs,parse_constant=bad_constant)
    except (ValueError,UnicodeError,TypeError) as exc:
        if isinstance(exc, RawCRejected):raise
        raise RawCRejected('INVALID_JSON') from exc


def _binary64_vector(values):
    require(type(values) is list and len(values)==10,'RAW_C_REQUIRES_TEN_NUMBERS')
    require(all(type(x) in (int,float) for x in values),'RAW_C_BOOLEAN_STRING_OR_NESTING')
    try:
        arr=np.asarray(values,dtype=np.float64)
    except (ValueError,OverflowError,TypeError) as exc:
        raise RawCRejected('RAW_C_NOT_BINARY64') from exc
    require(np.isfinite(arr).all() and float(np.linalg.norm(arr))>0.,'RAW_C_ZERO_NONFINITE')
    return arr


def binary64_digest(c):
    a=_binary64_vector(c)
    # Big-endian IEEE binary64, including the sign bit of negative zero.
    return sha256(struct.pack('!10d',*a)).hexdigest()


def positive_ray_exact(a,b):
    """Positive projective equivalence of the actual exact binary64 inputs.

    Zero components must align and negative projective scaling is forbidden.
    No tolerance: a derived rounded unit vector is not necessarily exactly on
    the source's rational binary64 ray.
    """
    x=_binary64_vector(a);y=_binary64_vector(b)
    pairs=[(Fraction.from_float(float(v)),Fraction.from_float(float(w)))
           for v,w in zip(x,y)]
    pivots=[v/w for v,w in pairs if w]
    if not pivots:return False
    k=pivots[0]
    return k>0 and all(v==k*w for v,w in pairs)


def diagnose_native_c(c):
    c=_binary64_vector(c)
    norm=float(np.linalg.norm(c))
    require(math.isfinite(norm) and norm>0,'INVALID_NATIVE_C_NORM')
    # The unit-ray array is for inspection only, never a source c or saved J.
    u=c/norm
    require(np.isfinite(u).all(),'NONFINITE_UNIT_RAY_DIAGNOSTIC')
    return {'raw_native_c':[float(x) for x in c],
            'raw_binary64_sha256':binary64_digest(c.tolist()),
            'norm2':norm,
            'unit_norm_compatible_v1':abs(norm-1.)<=UNIT_TOL,
            'signed_unit_ray_for_display_only':[float(x) for x in u],
            'polynomial_q_from_raw_c':[float(x*v) for x,v in zip(c,B_DIAG)],
            'renormalized_source_evaluation_performed':False,
            'raw_c_rewritten':False,
            'native_Jc_reparameterized':False,
            'derivative_J_D':None,
            'training_admissible':False}


def _read(zipfile,name,max_size):
    require(type(name) is str and not name.startswith('/') and '..' not in name.split('/'),
            'ZIP_PATH_TRAVERSAL')
    try:info=zipfile.getinfo(name)
    except KeyError as exc:raise RawCRejected('MISSING_ARCHIVE_MEMBER:'+name) from exc
    require(0<info.file_size<=max_size and info.compress_size<=max_size,
            'UNBOUNDED_ARCHIVE_MEMBER:'+name)
    return zipfile.read(name)


def _gzip_json(raw,max_size=22_000_000):
    require(0<len(raw)<5_000_000,'UNBOUNDED_COMPRESSED_MATERIAL')
    # The *entire* ZIP is bound to the original GitHub SHA before decompressing.
    try:data=gzip.decompress(raw)
    except (OSError,EOFError) as exc:raise RawCRejected('CORRUPT_NATIVE_GZIP') from exc
    require(0<len(data)<=max_size,'UNBOUNDED_MATERIAL_JSON')
    return _strict_json(data)


def _sha_file(path):
    h=sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def audit_real_h8f_81(archive):
    """Read all 81 actual GitHub native source packets without recomputing CAD.

    This checks identity and coefficient serialisation, NOT source runtime
    attestation, independent solid geometry, unit-normalized Jacobian truth,
    or Newton acceptance. Point-60 original branch failure remains a denial.
    """
    path=Path(archive)
    require(path.is_file() and not path.is_symlink(),'MISSING_PINNED_ARCHIVE')
    require(_sha_file(path)==ARCHIVE_SHA256,'H8F_ARCHIVE_SHA256_MISMATCH')
    rows=[]
    try:
        with ZipFile(path) as z:
            report_raw=_read(z,ROOT+'report.json',1_000_000)
            request_raw=_read(z,'artifacts/h8-request/prepared-request.json',10_000_000)
            require(sha256(report_raw).hexdigest()==REPORT_SHA256 and
                    sha256(request_raw).hexdigest()==REQUEST_SHA256,
                    'ORIGINAL_REPORT_REQUEST_HASH_MISMATCH')
            report=_strict_json(report_raw)
            require(report.get('completed_samples')==N and
                    report.get('production_cherchi_calls')==N and
                    report.get('all_numerical_checks_passed') is True and
                    report.get('complete_eighty_one_samples') is False and
                    report.get('qualified_branch_neighborhood') is False and
                    report.get('formal_newton_converged') is False,
                    'ORIGINAL_H8F_FAILURE_OR_SAMPLES_NOT_PRESERVED')
            for i in range(N):
                prefix=ROOT+f'point-{i:03d}'
                meta_raw=_read(z,prefix+'.json',100_000)
                meta=_strict_json(meta_raw)
                require(type(meta) is dict and meta.get('index')==i,
                        'WRONG_SOURCE_SAMPLE_INDEX')
                blob=_read(z,prefix+'-material.json.gz',5_000_000)
                require(sha256(blob).hexdigest()==meta.get('exact_same_call_material_archive_sha256'),
                        'ARCHIVED_MATERIAL_SHA_MISMATCH')
                material=_gzip_json(blob)
                require(material.get('quadric_coefficients')==meta.get('coefficients') and
                        material.get('geometry_hash')==meta.get('material_geometry_hash') and
                        material.get('topology_hash')==meta.get('feature_branch_hash') and
                        material.get('boolean_backend_identity')==meta.get('native_boolean_backend') and
                        material.get('derivative_defined') is True,
                        'ARCHIVED_C_OR_MATERIAL_IDENTITY_DRIFT')
                diag=diagnose_native_c(meta['coefficients'])
                rows.append({'index':i,
                             'raw_native_c':diag['raw_native_c'],
                             'native_binary64_sha256':diag['raw_binary64_sha256'],
                             'source_point_json_sha256':sha256(meta_raw).hexdigest(),
                             'source_material_gzip_sha256':sha256(blob).hexdigest(),
                             'unit_norm_compatible_v1':diag['unit_norm_compatible_v1'],
                             'native_norm2':diag['norm2'],
                             'polynomial_q_from_raw_c':diag['polynomial_q_from_raw_c'],
                             'finite_feature_hash_changed':meta['feature_branch_hash']!=report.get('base_feature_hash',None)
                                 if 'base_feature_hash' in report else None,
                             'release_native_Jc':False,
                             'training_admissible':False})
    except (BadZipFile,RuntimeError,OSError) as exc:
        raise RawCRejected('INVALID_HISTORICAL_ARCHIVE_STRUCTURE') from exc
    valid=[v['index'] for v in rows if v['unit_norm_compatible_v1']]
    require(valid==[0,21,22,23,24,61,62,63,64,69,70,71,72,77,78,79,80],
            'SOURCE_C_UNIT_COMPATIBILITY_DRIFT')
    max_dev=max(abs(r['native_norm2']-1.) for r in rows)
    return {'schema':'W0_M13_ARCHIVED_RAW_NATIVE_COEFFICIENT_DIAGNOSTIC_V1',
            'frozen_source_commit':'0bcc187b3005478baa586a6d6f450e73811ca342',
            'source_archived_workflow_run':HISTORIC_RUN,
            'original_workflow_conclusion':'failure',
            'artifact_id':12135528290,
            'archive_sha256':ARCHIVE_SHA256,
            'report_sha256':REPORT_SHA256,
            'sample_count':N,
            'v1_unit_c_compatible_count':len(valid),
            'v1_nonunit_c_count':N-len(valid),
            'v1_compatible_indices':valid,
            'maximum_native_c_norm_deviation':max_dev,
            'point60_raw_c_digest':rows[CHANGED_INDEX]['native_binary64_sha256'],
            'point60_native_c7':rows[CHANGED_INDEX]['raw_native_c'][7],
            'point60_monomial_q7':rows[CHANGED_INDEX]['polynomial_q_from_raw_c'][7],
            'rows':rows,
            'v1_schema_unmodified':True,
            'raw_c_replaced_with_normalized_values':False,
            'J_D':None,
            'native_cherchi_new_calls':0,
            'complete_continuous_derivative_neighborhood':False,
            'original_Newton_converged':False,
            'newton_admitted':False,
            'training_admissible':False,
            'status':'ARCHIVED_C_RAW_COMPATIBILITY_ONLY_NO_TRAINING'}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args(argv)
    if args.output.exists():raise FileExistsError('DO_NOT_OVERWRITE_M13_DIAGNOSTIC')
    result=audit_real_h8f_81(args.archive)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf8') as stream:
        json.dump(result,stream,indent=2,allow_nan=False)
        stream.write('\n')
    print(result['status'],result['v1_unit_c_compatible_count'],result['v1_nonunit_c_count'])
    return 0


if __name__=='__main__':
    raise SystemExit(main())

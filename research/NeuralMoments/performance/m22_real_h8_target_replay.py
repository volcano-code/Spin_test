"""M22 same-real-material target coordinate replay of the solver-bound variant.

This is an offline exact-coordinate smoke, NOT a live Boolean/Newton speed test.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import gzip
from hashlib import sha256
import json
from pathlib import Path
import struct
import time
from zipfile import ZipFile
from m8_exact_construction_trial import target_coordinates, reference_fraction

H8E_ZIP_SHA='14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38'
ROOT='artifacts/h8e-jacobian-cols0-4-8/'


def probe(archive: Path, points=(0,8,17)):
    if sha256(archive.read_bytes()).hexdigest()!=H8E_ZIP_SHA:
        raise ValueError('M22_ARCHIVE_PIN_MISMATCH')
    if not points or len(set(points))!=len(points) or any(type(x) is not int or not 0<=x<25 for x in points):
        raise ValueError('M22_BAD_SELECTED_POINTS')
    result=[]
    with ZipFile(archive) as z:
        request=json.loads(z.read('artifacts/h8-request/prepared-request.json'))['request']
        for index in points:
            prefix=f'{ROOT}point-{index:03d}'
            evidence=json.loads(z.read(prefix+'.json'))
            raw=z.read(prefix+'-material.json.gz')
            if sha256(raw).hexdigest()!=evidence['exact_same_call_material_archive_sha256']:
                raise ValueError('M22_MATERIAL_BLOB_SHA_MISMATCH')
            material=json.loads(gzip.decompress(raw))
            if (material.get('geometry_hash')!=evidence['material_geometry_hash'] or
                    material.get('topology_hash')!=evidence['feature_branch_hash'] or
                    evidence.get('exact_native_material_boundary_passed') is not True):
                raise ValueError('M22_MATERIAL_IDENTITY_OR_ORIGINAL_EXACT_AUDIT_MISSING')
            physical=tuple(tuple(reference_fraction(s) for s in xyz)
                           for xyz in material['material_proof']['exact_vertices'])
            if len(physical)!=8455 or len(material['variable_rational_vertices'])!=8455:
                raise ValueError('M22_MATERIAL_VERTEX_COUNT')
            observations=[]
            for mode in ('original','optimized','optimized','original'):
                t=time.perf_counter_ns()
                rows,unit=target_coordinates(physical,request['target_axes'],
                    request['target_origin'],mode=mode,
                    normalization_origin=(0.,0.,0.),length=1.)
                elapsed=time.perf_counter_ns()-t
                if len(rows)!=8455:
                    raise ValueError('M22_FRAME_VERTEX_DRIFT')
                for exact,raw_exact,raw_float in zip(rows, material['variable_rational_vertices'],
                                                    material['variable_vertices']):
                    if ([f'{v.numerator}/{v.denominator}' for v in exact]!=raw_exact or
                        any(struct.pack('>d',float(v))!=struct.pack('>d',float(x))
                            for v,x in zip(exact,raw_float))):
                        raise ValueError('M22_NONEXACT_TARGET_FRAME_REPLAY')
                observations.append(dict(mode=mode,elapsed_ns=elapsed))
            old=sorted(o['elapsed_ns'] for o in observations if o['mode']=='original')
            new=sorted(o['elapsed_ns'] for o in observations if o['mode']=='optimized')
            result.append(dict(point=index,material_sha256=sha256(raw).hexdigest(),
                 exact_frame_coordinates_match=8455,byte_identical_binary64_coordinates=True,
                 identity_axes=unit,original_ns=sum(old)//2,candidate_ns=sum(new)//2,
                 measurements=observations))
    return dict(schema='w1-m22-genuine-archived-target-frame-runtime-candidate-v1',
                scope='REAL_ARCHIVED_EXACT_TARGET_COORDINATES_NOT_NATIVE_SOLVER',
                archive_sha256=H8E_ZIP_SHA,points=result,
                target_frame_exact_coordinates_checked=8455*len(result),
                native_boolean_evaluations=0,full_solver_speedup=None,
                W0_W2_admitted=False,terminal_Newton_verified=False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--points',default='0,8,17')
    a=parser.parse_args()
    selected=tuple(map(int,a.points.split(',')))
    result=probe(a.archive,selected)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print('M22_FROZEN_H8_TARGET_EXACT',result['target_frame_exact_coordinates_checked'],
          'point_count',len(result['points']),'all_exact=True',flush=True)

if __name__=='__main__':main()

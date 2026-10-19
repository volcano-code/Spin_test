"""W1 M8: real archived Heart H8 post-Boolean exact Python A/B.

Only reproduces the frozen Python evaluator's rational conversion, target
coordinate view and provenance resolution. It does NOT regenerate Boolean,
source-motion/Jacobian, exact self-intersection or a full Faster solution.
It fails closed unless its full outputs reproduce every archived original
construction record, float coordinate and exact target token.

Candidates use a per-evaluation bounded exact Fraction-token cache and an
algebraically identical identity-axis specialization. Production files, ABI,
geometry acceptance and native solver behavior are never changed.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from fractions import Fraction
from functools import lru_cache
from hashlib import sha1, sha256
import gzip
import json
import math
from pathlib import Path
import platform
import resource
import struct
import sys
import time
from zipfile import ZipFile

import numpy as np

ARCHIVE_SHA = '14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38'
REQUEST_SHA = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
SOURCE_BLOB = 'f9fa539f699df8baf8b8d30729048269a26ecb3c'
PREFIX = 'artifacts/h8e-jacobian-cols0-4-8/'
EXPECTED_BACKEND = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'
MAX_CACHED_TOKENS = 65536
STAGES = ('parse_exact_vertices', 'target_coordinates', 'source_lookup', 'resolve_construction', 'check_archive')


def digest(x):
    return sha256(x).hexdigest()


def git_blob(x):
    return sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()


def verify_pinned_python_source(path):
    source=Path(path).read_bytes()
    if git_blob(source)!=SOURCE_BLOB:
        raise ValueError('M8_UNPINNED_PRODUCTION_SOURCE')
    return True


def reference_fraction(token):
    """Same exact_fraction semantics as frozen cherchi_inprocess.py."""
    numerator, denominator = token.split('/')
    def integer(s):
        return int(s, 2 if s.lstrip('-').startswith('0b') else 10)
    return Fraction(integer(numerator), integer(denominator))


def fraction_parser(optimized):
    if type(optimized) is not bool:
        raise ValueError('M8_INVALID_MODE')
    return lru_cache(maxsize=MAX_CACHED_TOKENS)(reference_fraction) if optimized else reference_fraction


def target_coordinates(points, target_axes, target_origin, *, mode, normalization_origin=(0.,0.,0.),length=1.):
    """Exactly reproduce original _target_view; use identity fast-path only.

    Fraction algebra is exact and preserves binary64 rounding. Everything not
    mathematically proven identity goes through the original general formula.
    """
    origin = [Fraction(float(x)) for x in normalization_origin]
    target = [Fraction(float(x)) for x in target_origin]
    axes = [[Fraction(float(x)) for x in row] for row in target_axes]
    scale = Fraction(length)
    if len(origin)!=3 or len(target)!=3 or len(axes)!=3 or any(len(row)!=3 for row in axes) or scale<=0:
        raise ValueError('M8_INVALID_FRAME')
    unit = axes == [[Fraction(int(i==j)) for j in range(3)] for i in range(3)]
    result=[]
    for physical in points:
        model=[(physical[i]-origin[i])/scale-target[i] for i in range(3)]
        if mode=='optimized' and unit:
            result.append(tuple(model))
        else:
            result.append(tuple(sum(model[i]*axes[i][j] for i in range(3)) for j in range(3)))
    return result, unit


def build_lookup(design, source):
    """Original exact binary64 coordinates and duplicate correspondence semantics."""
    result={}
    for object_index, points in enumerate((design, source)):
        for vertex_index, point in enumerate(points):
            key=tuple(Fraction(float(x)) for x in point)
            result.setdefault(key,[]).append(dict(input_object=object_index,input_vertex=vertex_index))
    return result


def resolve_construction(original_records, lookup, parse):
    """Identical to the production __call__ provenance loop (same operand order)."""
    records=[]
    for item in original_records:
        operands=[];positions=[]
        for tokens in item['operand_coordinates_exact']:
            exact=tuple(parse(x) for x in tokens)
            candidates=lookup.get(exact,[])
            operands.append(dict(source_vertices=candidates,status='UNIQUE' if len(candidates)==1 else
                'UNMATCHED' if not candidates else 'AMBIGUOUS'))
            positions.append([float(x) for x in exact])
        records.append(dict(vertex_index=item['vertex_index'],point_type=item['point_type'],
            parameter_t=item['parameter_t'],operands=operands,operand_coordinates=positions))
    return records


class Clock:
    def __init__(self):
        self.start=time.perf_counter_ns();self.active=None;self.rows=[]
    @contextmanager
    def stage(self,name):
        if name not in STAGES or self.active is not None:
            raise ValueError('M8_STAGE_NESTING_OR_UNREGISTERED')
        self.active=name;t=time.perf_counter_ns();status='PASS'
        try:
            yield
        except BaseException:
            status='FAIL';raise
        finally:
            self.rows.append(dict(stage=name,elapsed_ns=time.perf_counter_ns()-t,status=status))
            self.active=None
    def finish(self):
        if self.active is not None:raise ValueError('M8_TIMER_ACTIVE')
        wall=time.perf_counter_ns()-self.start
        total=sum(x['elapsed_ns'] for x in self.rows)
        if total>wall:raise ValueError('M8_OVERLAP_TIMING')
        return dict(wall_ns=wall,stages=self.rows,unattributed_ns=wall-total,
            all_passed=all(x['status']=='PASS' for x in self.rows))


def floats_bit_equal(rows,reference):
    if len(rows)!=len(reference):return False
    for exact,saved in zip(rows,reference):
        if len(exact)!=3 or len(saved)!=3:return False
        for a,b in zip(exact,saved):
            if struct.pack('!d',float(a))!=struct.pack('!d',float(b)):
                return False
    return True


def evaluate_packet(packet, design, frame, mode):
    if mode not in ('original','optimized'):
        raise ValueError('M8_UNKNOWN_MODE')
    c=Clock();parse=fraction_parser(mode=='optimized')
    with c.stage('parse_exact_vertices'):
        rational=tuple(tuple(parse(x) for x in row) for row in packet['material_proof']['exact_vertices'])
    with c.stage('target_coordinates'):
        rows,is_unit=target_coordinates(rational,frame['target_axes'],frame['target_origin'],mode=mode)
    with c.stage('source_lookup'):
        lookup=build_lookup(design,packet['quadric_source_vertices'])
    with c.stage('resolve_construction'):
        records=resolve_construction(packet['material_proof']['construction_records'],lookup,parse)
    with c.stage('check_archive'):
        expected=packet['material_proof']['resolved_construction_records']
        if records!=expected:
            raise ValueError('M8_PROVENANCE_RECORD_DRIFT')
        as_strings=[[str(x.numerator)+'/'+str(x.denominator) for x in row] for row in rows]
        if as_strings != packet['variable_rational_vertices']:
            raise ValueError('M8_EXACT_TARGET_COORDINATE_DRIFT')
        if not floats_bit_equal(rows,packet['variable_vertices']):
            raise ValueError('M8_BINARY64_TARGET_COORDINATE_DRIFT')
    timings=c.finish()
    if not timings['all_passed']:
        raise ValueError('M8_UNEXPECTED_STAGE_FAILURE')
    return dict(timing=timings,vertex_count=len(rational),record_count=len(records),
        unit_axes=is_unit,parser_cache=parse.cache_info()._asdict() if mode=='optimized' else None)


def member(z,name,size_limit=8_000_000):
    hits=[i for i in z.infolist() if i.filename==name]
    if len(hits)!=1 or hits[0].file_size>size_limit or hits[0].file_size<=0:
        raise ValueError('M8_MISSING_DUPLICATE_OR_OVERSIZE_MEMBER:'+name)
    return z.read(hits[0])


def load_identity(z,archive_path):
    if digest(Path(archive_path).read_bytes())!=ARCHIVE_SHA:
        raise ValueError('M8_ARCHIVE_SHA_DRIFT')
    raw=member(z,'artifacts/h8-request/prepared-request.json',7_000_000)
    if digest(raw)!=REQUEST_SHA:
        raise ValueError('M8_REQUEST_SHA_DRIFT')
    request=json.loads(raw)
    if request.get('schema')!='spin-heart-h8-faster-preparation-v1' or request.get('evidence',{}).get('original_author_cad') is not False:
        raise ValueError('M8_NOT_RECONSTRUCTED_FROZEN_H8')
    data=request['request']
    # Frozen preflight uses unit normalization and supplied target frame.
    for k in ('target_axes','target_origin','design_vertices'):
        if k not in data:raise ValueError('M8_FROZEN_REQUEST_MISSING:'+k)
    report=json.loads(member(z,PREFIX+'report.json',1_000_000))
    if (report.get('production_cherchi_calls')!=25 or report.get('completed_samples')!=25 or
        report.get('changed_feature_hash_points')!=8 or report.get('all_tested_stencils_same_feature_hash') is not False or
        report.get('formal_newton_converged') is not False):
        raise ValueError('M8_HISTORICAL_FAILED_STATUS_CHANGED')
    return data,report


def load_point(z,index):
    if not 0<=index<25:raise ValueError('M8_POINT_OUT_OF_RANGE')
    prefix=PREFIX+f'point-{index:03d}'
    raw=member(z,prefix+'-material.json.gz',3_000_000)
    ref=json.loads(member(z,prefix+'.json',200_000))
    if digest(raw)!=ref.get('exact_same_call_material_archive_sha256'):
        raise ValueError('M8_MATERIAL_SHA_DRIFT')
    decompressed=gzip.decompress(raw)
    if len(decompressed)>20_000_000:raise ValueError('M8_DECOMPRESSED_PACKET_TOO_LARGE')
    p=json.loads(decompressed)
    if (ref.get('index')!=index or p['quadric_coefficients']!=ref['coefficients'] or
        p.get('geometry_hash')!=ref.get('material_geometry_hash') or
        p.get('topology_hash')!=ref.get('feature_branch_hash') or
        ref.get('exact_native_material_boundary_passed') is not True or
        p.get('derivative_defined') is not True or
        len(p.get('moment_jacobian',[]))!=10 or any(len(row)!=10 or not all(math.isfinite(float(x)) for x in row) for row in p['moment_jacobian']) or
        len(p.get('variable_rational_vertices',[]))!=8455 or
        len(p.get('variable_faces',[]))!=16910 or
        len(p.get('material_proof',{}).get('resolved_construction_records',[]))!=8455 or
        not p.get('boolean_backend_identity','').startswith(EXPECTED_BACKEND)):
        raise ValueError('M8_SAME_CALL_ARCHIVE_IDENTITY_DRIFT')
    return p,ref


def record_progress(path,line):
    with Path(path).open('a',encoding='utf-8') as f:
        json.dump(line,f,sort_keys=True,separators=(',',':'),allow_nan=False);f.write('\n')
        f.flush()


def run(archive, output, *, order=('original','optimized','optimized','original'),count=25,source_file=None):
    archive=Path(archive);output=Path(output)
    if count not in range(1,26) or len(order)<2 or any(x not in ('original','optimized') for x in order):
        raise ValueError('M8_BAD_SAMPLE_COUNT_OR_RUN_ORDER')
    if order.count('original')!=order.count('optimized'):
        raise ValueError('M8_UNBALANCED_AB_ORDER')
    output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter_ns()
    try:
        if len(Path('/proc/swaps').read_text().splitlines())!=1:
            raise RuntimeError('M8_REQUIRES_ZERO_SWAP')
        source_pinned=(verify_pinned_python_source(source_file) if source_file is not None else False)
        with ZipFile(archive) as z:
            frame,original_report=load_identity(z,archive)
            out=[];sum_points=0
            for sample,mode in enumerate(order):
                tic=time.perf_counter_ns();stages={};cache_hits=0;cache_misses=0
                for i in range(count):
                    packet,old=load_point(z,i)
                    result=evaluate_packet(packet,frame['design_vertices'],frame,mode)
                    for row in result['timing']['stages']:
                        stages[row['stage']]=stages.get(row['stage'],0)+row['elapsed_ns']
                    if mode=='optimized':
                        cache_hits+=result['parser_cache']['hits'];cache_misses+=result['parser_cache']['misses']
                    record_progress(output/'points.jsonl',dict(run=sample,mode=mode,index=i,
                        point_material_sha=old['exact_same_call_material_archive_sha256'],
                        geometry_hash=packet['geometry_hash'],topology_hash=packet['topology_hash'],
                        wall_ns=result['timing']['wall_ns'],stage_ns={x['stage']:x['elapsed_ns'] for x in result['timing']['stages']},
                        exact_equivalence=True,cache=result['parser_cache']))
                    sum_points+=1
                run_wall=time.perf_counter_ns()-tic
                row=dict(sample=sample,mode=mode,wall_ns=run_wall,stage_ns=stages,
                    cache_hits=cache_hits,cache_misses=cache_misses)
                out.append(row)
                record_progress(output/'runs.jsonl',row)
                print('M8_REPLAY',sample,mode,round(run_wall/1e9,3),'seconds',flush=True)
            from statistics import median
            original=median(r['wall_ns'] for r in out if r['mode']=='original')
            optimized=median(r['wall_ns'] for r in out if r['mode']=='optimized')
            ratio=original/optimized
            result=dict(schema='w1-m8-archived-exact-provenance-abba-v1',
                scope='HISTORICAL_REAL_H8E_POST_BOOLEAN_PYTHON_ONLY_NOT_NATIVE_SOLVER',
                frozen_source_git_blob=SOURCE_BLOB,source_on_disk_verified=source_pinned,
                archive_sha256=ARCHIVE_SHA,request_sha256=REQUEST_SHA,
                samples=len(out),points_per_sample=count,checked_point_evaluations=sum_points,
                all_original_resolved_records_equal=True,all_target_rational_tokens_equal=True,
                all_target_binary64_bitwise_equal=True,
                cached_exact_parser_bounded=MAX_CACHED_TOKENS,
                original_H8e_failed_hash_changes=8,original_H8e_ci_failure_preserved=True,
                timing_order=list(order),runs=out,median_original_wall_seconds=original/1e9,
                median_optimized_wall_seconds=optimized/1e9,
                isolated_post_boolean_ratio=ratio,
                native_cherchi_boolean_evaluations=0,native_jacobian_regenerations=0,
                original_complete_solver_optimized=False,production_changes_applied=False,
                production_speedup=None,paper_speed_qualified=False,
                environment=dict(python=sys.version.split()[0],platform=platform.platform(),
                    maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    swap_entries=max(0,len(Path('/proc/swaps').read_text().splitlines())-1)))
            with (output/'baseline-performance.json').open('x') as f:
                json.dump(result,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
            with (output/'before_after.json').open('x') as f:
                json.dump(dict(schema='w1-m8-before-after-v1',
                    before={'isolated_post_boolean_median_seconds':original/1e9},
                    after={'isolated_post_boolean_median_seconds':optimized/1e9},
                    same_archived_input_exact_parity=True,
                    isolated_post_boolean_ratio=ratio,
                    production_full_solve_speedup=None,optimizations_applied_to_production=False,
                    paper_speed_qualified=False),f,indent=2,sort_keys=True);f.write('\n')
            return result
    except BaseException as e:
        with (output/'failure.json').open('x') as f:
            json.dump(dict(status='FAILED_CLOSED',error=f'{type(e).__name__}: {e}',
                no_successful_baseline=True,production_speedup=None,paper_speed_qualified=False),f)
            f.write('\n')
        raise


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--points',type=int,default=25)
    p.add_argument('--source',type=Path,default=None,help='Optional pinned production cherchi_inprocess.py; reject drift')
    args=p.parse_args()
    record=run(args.archive,args.output,count=args.points,source_file=args.source)
    print(json.dumps({'status':'PASS_ARCHIVED_EXACT_CONSTRUCTION_ONLY',
      'ratio':record['isolated_post_boolean_ratio'],'records_checked':record['checked_point_evaluations']}))

if __name__=='__main__':main()

"""W1 M15: execute two REAL compiled C++/GMP integrals on authentic archived H8e materials.

The surface implementation is the existing W1 M3 production-algebra-derived
exact face-integral probe; the tetra implementation is independent W1 M6.
Both remain standalone executables. Neither is fresh Cherchi Boolean,
production module/ABI certification, Jacobian regeneration, or a Newton solve.
Never use these measurements to claim complete Faster speedup.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import gzip
import json
import math
from pathlib import Path
import sys
import platform
import resource
import statistics
import subprocess
import tempfile
import time
from zipfile import ZipFile

from m4_25point_attribution import ARCHIVE_SHA, H8E_ROOT, REQ, exact_member, strict_archive, to_stream

BACKEND = 'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'
M3_SCHEMA = 'w1-m3-real-h8-exact-gmp-v2'
M6_SCHEMA = 'w1-m6-exact-independent-tetra-v1'


def digest(b): return sha256(b).hexdigest()


def proc(binary, stream, argv, *, timeout=120):
    def limit():
        soft, hard = resource.getrlimit(resource.RLIMIT_AS)
        cap = min((3 * 1024**3, soft if soft != resource.RLIM_INFINITY else 3*1024**3))
        resource.setrlimit(resource.RLIMIT_AS,(cap,cap))
    with stream.open('r',encoding='ascii') as file:
        started=time.perf_counter_ns()
        p=subprocess.run([str(binary),*argv], stdin=file, capture_output=True,
                         text=True,timeout=timeout,preexec_fn=limit,check=False)
        wall=time.perf_counter_ns()-started
    if p.returncode:
        raise RuntimeError('M15_NATIVE_EXECUTION_FAILED:'+str(p.returncode)+':'+p.stderr[:200])
    obj=json.loads(p.stdout)
    return obj,wall


def scientific_check(old, new, reference):
    if (old.get('schema')!=M3_SCHEMA or new.get('schema')!=M6_SCHEMA or
            old.get('vertices')!=8455 or old.get('faces')!=16910 or
            new.get('vertices')!=8455 or new.get('faces')!=16910 or
            old.get('exact_ten_moments_equal') is not True or
            old.get('recomputed_cherchi_boolean') is not False or
            old.get('jacobian_recomputed') is not False):
        raise ValueError('M15_NATIVE_SCOPE_OR_SIZE_DRIFT')
    a,b=old.get('ten_exact'),new.get('exact_ten')
    if not (isinstance(a,list) and isinstance(b,list) and len(a)==len(b)==10 and
            all(type(x) is str for x in a+b) and a==b):
        raise ValueError('M15_INDEPENDENT_GMP_TEN_EXACT_DRIFT')
    from fractions import Fraction
    # Signed exact GMP outputs from actual H8 can exceed Python 3.13's default 4300-digit guard.
    # This only applies to trusted, pinned archive-generated native results.
    sys.set_int_max_str_digits(200000)
    doubles=[float(Fraction(t)) for t in a]
    if len(reference)!=10 or any(not math.isfinite(v) for v in doubles+reference):
        raise ValueError('M15_BAD_MOMENT_REFERENCE')
    error=max(abs(a-b)/max(1.0,abs(b)) for a,b in zip(doubles,reference))
    if error>1e-10:
        raise ValueError('M15_HISTORICAL_INDEPENDENT_MOMENTS_CHANGED')
    stages=old['stages']
    if (len(stages)!=4 or sorted([x['variant'] for x in stages]) !=
            ['legacy','legacy','prepared','prepared'] or
            any(any(type(x[k]) is not int or x[k]<0 for k in
                    ('reference_or_roundtrip_ns','boundary_gate_ns','gmp_ten_ns','total_ns'))
                for x in stages)):
        raise ValueError('M15_INCOMPLETE_EXCLUSIVE_SURFACE_TIMING')
    for x in stages:
        if sum(x[k] for k in ('reference_or_roundtrip_ns','boundary_gate_ns','gmp_ten_ns')) > x['total_ns']:
            raise ValueError('M15_NEGATIVE_TIMER_RESIDUAL')
    for k in ('input_parse_ns','full_boundary_gate_ns','independent_tetra_ns'):
        if not isinstance(new.get(k),int) or new[k]<0:
            raise ValueError('M15_INVALID_TETRA_STAGE')
    return error


def run(archive,binary_surface,binary_tetra,output,*,points=25,start=0):
    archive,binary_surface,binary_tetra,output=map(Path,(archive,binary_surface,binary_tetra,output))
    if (type(points) is not int or type(start) is not int or
            not 0<=start<points<=25): raise ValueError('M15_SAMPLE_RANGE_INVALID')
    output.mkdir(parents=True,exist_ok=False)
    events=[];t0=time.perf_counter_ns()
    try:
        if len(Path('/proc/swaps').read_text().splitlines())!=1:
            raise RuntimeError('M15_SWAP_MUST_BE_ZERO')
        bins={k:{'path':str(p.resolve()),'sha256':digest(p.read_bytes())}
              for k,p in (('surface',binary_surface),('tetra',binary_tetra))}
        if digest(archive.read_bytes())!=ARCHIVE_SHA:
            raise ValueError('M15_AUTHENTIC_ARCHIVE_SHA_MISMATCH')
        with ZipFile(archive) as z:
            historical=strict_archive(z)
            with tempfile.TemporaryDirectory(prefix='w1-m15-material-') as tmp:
                with (output/'point-events.jsonl').open('x') as logfile:
                    for i in range(start,points):
                        ts=time.perf_counter_ns()
                        member=H8E_ROOT+f'point-{i:03d}'
                        packed=exact_member(z,member+'-material.json.gz',max_size=3_000_000)
                        rec=json.loads(exact_member(z,member+'.json',max_size=200_000))
                        packet=json.loads(gzip.decompress(packed))
                        if (rec.get('index')!=i or
                                digest(packed)!=rec.get('exact_same_call_material_archive_sha256') or
                                packet.get('quadric_coefficients')!=rec.get('coefficients') or
                                packet.get('geometry_hash')!=rec.get('material_geometry_hash') or
                                packet.get('topology_hash')!=rec.get('feature_branch_hash') or
                                packet.get('boolean_backend_identity','').startswith(BACKEND) is not True or
                                rec.get('exact_native_material_boundary_passed') is not True or
                                packet.get('derivative_defined') is not True):
                            raise ValueError('M15_SAME_CALL_SOURCE_OR_GEOMETRY_DRIFT')
                        vs,fs=packet['variable_rational_vertices'],packet['variable_faces']
                        if not (len(vs)==rec.get('vertex_count')==8455 and
                                len(fs)==rec.get('triangle_count')==16910):
                            raise ValueError('M15_ARCHIVED_GEOMETRY_SIZE_DRIFT')
                        # Serial native executable calls, identical stdin geometry bytes.
                        stream=Path(tmp)/f'point-{i:03d}.txt'
                        to_stream(vs,fs,stream)
                        if i % 2 == 0:
                            s,s_wall=proc(binary_surface,stream,['--real-h8','2'])
                            t,t_wall=proc(binary_tetra,stream,[])
                        else:
                            t,t_wall=proc(binary_tetra,stream,[])
                            s,s_wall=proc(binary_surface,stream,['--real-h8','2'])
                        err=scientific_check(s,t,rec['independent_variable_raw_moments'])
                        row=dict(point=i,q_sha256=digest(json.dumps(rec['coefficients']).encode()),
                                 packet_sha256=digest(packed),geometry_hash=rec['material_geometry_hash'],
                                 feature_hash=rec['feature_branch_hash'],
                                 exact_ten_sha256=digest('\n'.join(s['ten_exact']).encode()),
                                 scaled_reference_error=err,
                                 surface=dict(process_wall_ns=s_wall,stages=s['stages'],
                                    source_parse_ns=s['input_parse_ns']),
                                 tetra=dict(process_wall_ns=t_wall,read_ns=t['input_parse_ns'],
                                    gate_ns=t['full_boundary_gate_ns'],math_ns=t['independent_tetra_ns']),
                                 overhead_ns=time.perf_counter_ns()-ts-s_wall-t_wall)
                        events.append(row)
                        logfile.write(json.dumps(row,allow_nan=False,separators=(',',':'))+'\n')
                        logfile.flush()
            overall=time.perf_counter_ns()-t0
            legacy=[x['total_ns'] for row in events for x in row['surface']['stages']
                    if x['variant']=='legacy']
            prepared=[x['total_ns'] for row in events for x in row['surface']['stages']
                      if x['variant']=='prepared']
            report=dict(schema='w1-m15-authentic-25point-two-compiled-native-integrals-v1',
                scope='ARCHIVED_CHERCHI_MATERIAL_GMP_COMPUTATION_ONLY_NOT_FRESH_BOOLEAN_OR_SOLVER',
                original_failed_h8e=True,original_feature_hash_changed_points=8,
                input_archive_sha256=ARCHIVE_SHA,
                compiled_native_binaries=bins,real_archived_points=len(events),
                sample_start_inclusive=start,sample_end_exclusive=points,
                exact_ten_equal_each_point=True,
                max_independent_reference_scaled_error=max(x['scaled_reference_error'] for x in events),
                surface_variant_old_median_ns=statistics.median(legacy),
                surface_variant_prepared_median_ns=statistics.median(prepared),
                isolated_surface_source_ref_ratio=statistics.median(legacy)/statistics.median(prepared),
                full_replay_wall_ns=overall,
                original_h8e_full_solver_speedup=None,fresh_boolean_calls=0,
                regenerated_jacobian=False,full_newton_runs=0,
                true_independent_self_intersection_audit_rerun=False,
                post_optimization_mathematical_admission=False,paper_speed_qualified=False,
                host=dict(platform=platform.platform(),python=platform.python_version(),swap_entries=0,
                          cgroup_memory_ceiling_bytes=int(Path('/sys/fs/cgroup/memory.max').read_text()),
                          serialized_native_processes=True))
            (output/'baseline-performance.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
            (output/'before_after.json').write_text(json.dumps(dict(
                schema='w1-m15-archived-gmp-before-after-v1',
                scope='CXX_GMP_MATERIAL_OWNERSHIP_SUBPATH_NOT_FULL_NEWTON',
                isolated_source_ref_ratio=report['isolated_surface_source_ref_ratio'],
                full_solver_speedup=None,paired_complete_newton_runs=0,
                no_omitted_boundary_validation=True,full_production_equivalence_certified=False),
                indent=2,allow_nan=False)+'\n')
            return report
    except BaseException as exc:
        (output/'failure.json').write_text(json.dumps(dict(schema='w1-m15-fail-closed-v1',
            status='FAILED_NO_NATIVE_CERTIFICATION',completed_packets=len(events),
            error=f'{type(exc).__name__}: {exc}',fresh_boolean_calls=0,
            full_solver_speedup=None))+'\n')
        raise


def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--archive',required=True,type=Path)
    a.add_argument('--surface',required=True,type=Path)
    a.add_argument('--tetra',required=True,type=Path)
    a.add_argument('--output',required=True,type=Path)
    a.add_argument('--points',type=int,default=25)
    a.add_argument('--start',type=int,default=0)
    v=a.parse_args()
    r=run(v.archive,v.surface,v.tetra,v.output,points=v.points,start=v.start)
    print(json.dumps({'scope':r['scope'],'points':r['real_archived_points'],
                     'source_ref_ratio':r['isolated_surface_source_ref_ratio'],
                     'fresh_boolean_calls':0},sort_keys=True))
if __name__=='__main__': main()

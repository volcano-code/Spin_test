"""W1 M4: independent 25-point archived H8 exact-material replay and time ledger.

Each packet is exactly tied to the original failed H8e CI run. Replays archived
geometry only; does NOT rerun Boolean, motion, native Jacobian or Newton.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from fractions import Fraction
from hashlib import sha256
import gzip
import json
import math
from pathlib import Path
import platform
import resource
import sys
import subprocess
import time
from zipfile import ZipFile

import numpy as np

# Frozen input keys verified against the existing M3 W1 historical archive audit.
EXPECTED_REQUEST_SHA = '1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c'
REQ = 'artifacts/h8-request/prepared-request.json'
H8E_ROOT = 'artifacts/h8e-jacobian-cols0-4-8/'


def sha(data: bytes) -> str:
    return sha256(data).hexdigest()


def exact_member(z: ZipFile, path: str, max_size=10_000_000) -> bytes:
    members=[e for e in z.infolist() if e.filename==path]
    if len(members)!=1 or members[0].file_size>max_size:
        raise ValueError('M4_MISSING_DUPLICATE_OR_OVERSIZED:'+path)
    return z.read(members[0])


def to_stream(vertices, faces, path: Path):
    with Path(path).open('x',encoding='ascii') as f:
        f.write(f'W1_REAL_H8_V1\n{len(vertices)} {len(faces)}\n')
        for v in vertices:
            if len(v)!=3 or any(type(t) is not str or len(t)>2048 for t in v):
                raise ValueError('INVALID_EXACT_VERTEX')
            f.write(' '.join(v)+'\n')
        for face in faces:
            if (len(face)!=3 or any(type(t) is not int or t<0 or t>=len(vertices) for t in face)):
                raise ValueError('INVALID_STREAM_FACE')
            f.write(' '.join(map(str,face))+'\n')


def run_cmd(args, *, stdin, timeout):
    def limits():
        target=24*1024**3
        soft,hard=resource.getrlimit(resource.RLIMIT_AS)
        limit=min([target]+[v for v in (soft,hard) if v!=resource.RLIM_INFINITY])
        resource.setrlimit(resource.RLIMIT_AS,(limit,hard))
    result=subprocess.run(args,stdin=stdin,capture_output=True,text=True,
                          timeout=timeout,preexec_fn=limits,check=False)
    if result.returncode:
        raise RuntimeError('STANDALONE_GMP_FAILED:'+str(result.returncode)+':'+result.stderr[:300])
    return result

ARCHIVE_SHA = '14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38'
H8C_SHA = '78749e99abd25ab2d2571440991ffa4e907a1565b4c7faf5210496431389cdd7'
POINTS = 25
PAIRS = ((0,0),(1,1),(2,2),(1,2),(0,2),(0,1))
STAGES = ('zip_read', 'packet_sha256', 'gzip_decode', 'json_decode',
          'archive_identity', 'fraction_token_parse', 'fraction_exact_ten',
          'standalone_native_gmp', 'parity_and_archived_jacobian', 'journal_write')


def exact(token):
    """Reject noncanonical or malformed decimal rational archive tokens."""
    if type(token) is not str or len(token) > 2048 or token.count('/') != 1:
        raise ValueError('INVALID_RATIONAL_TOKEN')
    a, b = token.split('/')
    if (not a or not b or not a.lstrip('-').isdigit() or not b.isdigit()
            or a in ('-0', '+0') or int(b) <= 0):
        raise ValueError('INVALID_RATIONAL_PAIR')
    n, d = int(a), int(b)
    if f'{n}/{d}' != token or math.gcd(n,d) != 1:
        raise ValueError('NONCANONICAL_RATIONAL_TOKEN')
    return Fraction(n, d)


def fraction_ten(points, faces):
    """Independent tetrahedron formula, unlike the C++ surface-divergence path."""
    sums = [Fraction(0) for _ in range(10)]
    for face in faces:
        if (len(face) != 3 or any(type(j) is not int or j < 0 or j >= len(points) for j in face)):
            raise ValueError('INVALID_FACE_INDEX')
        a, b, c = (points[j] for j in face)
        det = (a[0]*(b[1]*c[2]-b[2]*c[1])
               +a[1]*(b[2]*c[0]-b[0]*c[2])
               +a[2]*(b[0]*c[1]-b[1]*c[0]))
        if not det:
            continue
        sums[0] += det / 6
        s = tuple(a[k] + b[k] + c[k] for k in range(3))
        for k in range(3):
            sums[k+1] += det*s[k]/24
        for k, (x, y) in enumerate(PAIRS):
            sums[k+4] += det*(s[x]*s[y]+a[x]*a[y]+b[x]*b[y]+c[x]*c[y])/120
    if sums[0] <= 0:
        raise ValueError('NONPOSITIVE_MASS')
    return [float(x) for x in sums]


class Clock:
    def __init__(self):
        self.start = time.perf_counter_ns()
        self.active = None
        self.rows = []

    @contextmanager
    def stage(self, name):
        if name not in STAGES or self.active is not None:
            raise ValueError('W1_OVERLAPPING_OR_UNREGISTERED_STAGE')
        self.active = name
        start = time.perf_counter_ns()
        status = 'passed'
        try:
            yield
        except BaseException:
            status = 'failed'
            raise
        finally:
            self.rows.append(dict(name=name, ns=time.perf_counter_ns()-start,
                                  status=status))
            self.active = None

    def report(self):
        if self.active is not None:
            raise ValueError('W1_ACTIVE_STAGE')
        wall = time.perf_counter_ns()-self.start
        total = sum(x['ns'] for x in self.rows)
        if total > wall:
            raise ValueError('W1_OVERLAPPED_DURATION')
        return dict(wall_ns=wall, mutually_exclusive_stages=self.rows,
                    unattributed_ns=wall-total,
                    all_returned=all(x['status']=='passed' for x in self.rows))


def five_weights(positions):
    x = np.asarray(positions, dtype=np.float64)
    if x.shape != (5,) or not np.isfinite(x).all() or len(set(x)) != 5:
        raise ValueError('INVALID_FIVE_POINT_STENCIL')
    scale = max(abs(x))
    v = np.stack([(x/scale)**k for k in range(5)])
    w = np.linalg.solve(v, [0,1,0,0,0])/scale
    if np.max(np.abs(v @ (w*scale) - [0,1,0,0,0])) > 1e-10:
        raise ValueError('INVALID_STENCIL_WEIGHTS')
    return w


def verify_fd(rows, report):
    """Independent FD from independently recomputed Fraction ten, not cached point moments."""
    base = np.asarray(report['analytic_10_by_10_jacobian'], dtype=np.float64)
    if base.shape != (10,10) or not np.isfinite(base).all():
        raise ValueError('INVALID_BASE_JACOBIAN')
    if len(rows) != 25:
        return dict(status='INCOMPLETE_SUBSET', tested_stencils=0)
    q = np.asarray(rows[0]['q'], dtype=np.float64)
    checks=[]
    for old in report['numeric_checks']:
        ids=old['sample_indices']; col=old['column']
        if len(ids) != 5 or any(i not in rows for i in ids):
            raise ValueError('ARCHIVED_STENCIL_INDEX_INVALID')
        positions=[rows[i]['q'][col]-q[col] for i in ids]
        weights=five_weights(positions)
        values=np.asarray([rows[i]['fraction_ten'] for i in ids])
        computed=weights@values
        err=float(np.max(np.abs(computed-base[:,col])/np.maximum(1.,np.abs(base[:,col]))))
        if abs(err-old['max_scaled_derivative_error']) > 1e-8 or err>1e-6:
            raise ValueError('INDEPENDENT_FRACTION_FD_DISAGREEMENT')
        stable=all(rows[i]['topology_hash']==rows[0]['topology_hash'] for i in ids)
        if stable is not old['feature_hash_stable']:
            raise ValueError('ARCHIVED_BRANCH_HASH_CHECK_DISAGREEMENT')
        checks.append(dict(column=col,step=old['step'],max_scaled_error=err,
                           historical_max_scaled_error=old['max_scaled_derivative_error'],
                           numeric_passed=True,original_feature_hash_stable=stable))
    changed=sum(rows[i]['topology_hash']!=rows[0]['topology_hash'] for i in range(1,25))
    if changed!=8 or len(checks)!=9 or all(x['original_feature_hash_stable'] for x in checks):
        raise ValueError('HISTORICAL_FAILURE_NOT_PRESERVED')
    return dict(status='NINE_FRACTION_FINITE_STENCILS_REPLAYED_NOT_SMOOTH_CERTIFIED',
                tested_stencils=len(checks), original_changed_feature_hash_points=changed,
                analytic_jacobian_origin='ARCHIVED_BASE_ONLY_NOT_FRESHLY_COMPUTED',checks=checks)


def strict_archive(z):
    if len(z.infolist()) > 110 or sum(e.file_size for e in z.infolist()) > 60_000_000:
        raise ValueError('ARCHIVE_UNBOUNDED')
    names=[e.filename for e in z.infolist()]
    if len(set(names))!=len(names):
        raise ValueError('ARCHIVE_DUPLICATE_MEMBERS')
    frozen=exact_member(z,REQ,max_size=7_000_000)
    if sha(frozen)!=EXPECTED_REQUEST_SHA:
        raise ValueError('FROZEN_REQUEST_HASH_DRIFT')
    report=json.loads(exact_member(z,H8E_ROOT+'report.json'))
    if (report.get('input_request_sha256') != EXPECTED_REQUEST_SHA
            or report.get('production_cherchi_calls') != 25
            or report.get('completed_samples') != 25
            or report.get('all_numerical_checks_passed') is not True
            or report.get('all_tested_stencils_same_feature_hash') is not False
            or report.get('changed_feature_hash_points') != 8
            or report.get('formal_newton_converged') is not False):
        raise ValueError('ARCHIVED_H8E_FAILURE_STATE_DRIFT')
    return report


def replay(archive, output, binary, *, count=25, repeats=1, h8c=None):
    if not 1<=count<=25 or not 1<=repeats<=3:
        raise ValueError('RESOURCE_LIMITS')
    output=Path(output)
    output.mkdir(parents=True, exist_ok=False)
    try:
        if len(Path('/proc/swaps').read_text().splitlines()) != 1:
            raise RuntimeError('SWAP_NONZERO')
        source_bin=Path(binary)
        if not source_bin.is_file():
            raise FileNotFoundError('REAL_NATIVE_GMP_BINARY_REQUIRED')
        if sha(Path(archive).read_bytes()) != ARCHIVE_SHA:
            raise ValueError('ARCHIVED_25POINT_ZIP_SHA_MISMATCH')
    except BaseException as exc:
        (output/'failure.json').write_text(json.dumps(dict(schema='w1-m4-failure-v1',
            completed=0,error=type(exc).__name__+': '+str(exc),
            full_solver_speedup=None,paper_speed_qualified=False),indent=2)+'\n')
        raise
    rows={}
    run_start=time.perf_counter_ns()
    try:
        with ZipFile(archive) as z:
            report = strict_archive(z)
            journal=output/'events.jsonl'
            with journal.open('x') as out:
                for i in range(count):
                    clock=Clock()
                    index=f'{i:03d}'
                    with clock.stage('zip_read'):
                        row_raw=exact_member(z,H8E_ROOT+f'point-{index}.json')
                        packet_raw=exact_member(z,H8E_ROOT+f'point-{index}-material.json.gz')
                    with clock.stage('packet_sha256'):
                        packet_sha=sha(packet_raw)
                    with clock.stage('gzip_decode'):
                        raw=gzip.decompress(packet_raw)
                        if len(raw)>25_000_000:
                            raise ValueError('PACKET_TOO_LARGE')
                    with clock.stage('json_decode'):
                        row=json.loads(row_raw);material=json.loads(raw)
                    with clock.stage('archive_identity'):
                        if (row.get('index')!=i or row.get('exact_same_call_material_archive_sha256')!=packet_sha
                                or row.get('coefficients')!=material.get('quadric_coefficients')
                                or row.get('material_geometry_hash')!=material.get('geometry_hash')
                                or row.get('feature_branch_hash')!=material.get('topology_hash')
                                or row.get('exact_native_material_boundary_passed') is not True
                                or row.get('vertex_count')!=8455 or row.get('triangle_count')!=16910
                                or len(material['variable_rational_vertices'])!=8455
                                or len(material['variable_faces'])!=16910
                                or row.get('independent_moments_max_scaled_error')!=0):
                            raise ValueError('ARCHIVED_PACKET_IDENTITY_DRIFT')
                        if (not str(material.get('boolean_backend_identity','')).startswith(
                              'cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:')):
                            raise ValueError('NOT_PINNED_CHERCHI')
                        expected=list(row['production_variable_raw_moments'])
                        if len(expected)!=10 or len(row['independent_variable_raw_moments'])!=10:
                            raise ValueError('MOMENT_VECTOR_LENGTH')
                        expected_j=np.asarray(material['moment_jacobian'])
                        if (expected_j.shape!=(10,10) or not np.isfinite(expected_j).all()
                                or (i==0 and not np.array_equal(expected_j,np.asarray(report['analytic_10_by_10_jacobian'])))):
                            raise ValueError('JACOBIAN_SHAPE_OR_BASE_DRIFT')
                    with clock.stage('fraction_token_parse'):
                        coords=[tuple(exact(t) for t in vertex) for vertex in material['variable_rational_vertices']]
                    with clock.stage('fraction_exact_ten'):
                        moments=fraction_ten(coords,material['variable_faces'])
                    # The native side independently parses exactly the same material and checks
                    # complete oriented edge incidence; two code paths must agree exactly.
                    with clock.stage('standalone_native_gmp'):
                        import tempfile
                        with tempfile.TemporaryDirectory(prefix='w1-m4-packet-') as wd:
                            path=Path(wd)/'packet.stream'
                            to_stream(material['variable_rational_vertices'],material['variable_faces'],path)
                            with path.open('r',encoding='ascii') as f:
                                command=run_cmd([str(source_bin),'--real-h8',str(repeats)],stdin=f,
                                                timeout=180)
                        native=json.loads(command.stdout)
                    with clock.stage('parity_and_archived_jacobian'):
                        if (native.get('exact_ten_moments_equal') is not True
                                or native.get('topology_admitted_each_iteration') is not True
                                or native.get('recomputed_cherchi_boolean') is not False
                                or native.get('full_solver_measured') is not False):
                            raise ValueError('NATIVE_ISOLATED_PARITY_NOT_ADMITTED')
                        sys.set_int_max_str_digits(30_000)
                        if any(len(x)>30_000 for x in native['ten_exact']):
                            raise ValueError('OVERSIZE_NATIVE_EXACT_MOMENT')
                        native_exact=[float(Fraction(x)) for x in native['ten_exact']]
                        if moments!=native_exact or moments!=expected or moments!=list(row['independent_variable_raw_moments']):
                            raise ValueError('ARCHIVED_FRACTION_GMP_TEN_MISMATCH')
                        time_rows=native['stages']
                        if len(time_rows)!=2*repeats:
                            raise ValueError('NATIVE_REPEATS_INCOMPLETE')
                        for v in time_rows:
                            if sum(v[k] for k in ('reference_or_roundtrip_ns','boundary_gate_ns','gmp_ten_ns'))!=v['total_ns']:
                                raise ValueError('NATIVE_STAGE_NOT_EXCLUSIVE')
                        q=list(material['quadric_coefficients'])
                    with clock.stage('journal_write'):
                        entry=dict(index=i, archive_packet_sha256=packet_sha,
                                   q=q, geometry_hash=material['geometry_hash'],
                                   topology_hash=material['topology_hash'],
                                   fraction_ten=moments,
                                   native_stage_rows=time_rows,
                                   archived_jacobian_checked=i==0,
                                   original_h8e25_status='FAILURE_PRESERVED')
                        out.write(json.dumps(entry,allow_nan=False,sort_keys=True)+'\n');out.flush()
                    # Recalculate time after journal I/O so wall >= all recorded stages.
                    entry['replay_timing']=clock.report()
                    if not entry['replay_timing']['all_returned']:
                        raise ValueError('W1_INCOMPLETE_STAGE')
                    # Two-phase ledger: the second journal event persists the complete
                    # timing after write has completed; its own tiny write is unattributed.
                    out.write(json.dumps({'kind':'COMPLETE_TIMING','index':i,
                        'replay_timing':entry['replay_timing']},sort_keys=True)+'\n');out.flush()
                    rows[i]=entry
                    print('M4_ARCHIVED_H8',i+1,'/',count,'wall_s',round(entry['replay_timing']['wall_ns']/1e9,3),flush=True)
        checked=verify_fd(rows,report)
        total_elapsed=time.perf_counter_ns()-run_start
        hist_stages=report['stage_totals_seconds'];hist_total=float(report['wall_seconds'])
        if sum(hist_stages.values())>hist_total:
            raise ValueError('HISTORICAL_STAGE_OVERLAP')
        aggregated={s:sum(next(x['ns'] for x in row['replay_timing']['mutually_exclusive_stages'] if x['name']==s)
                          for row in rows.values())/1e9 for s in STAGES}
        if sum(aggregated.values())>total_elapsed/1e9:
            raise ValueError('W1_NEW_PROFILER_STAGE_OVERLAP')
        rs=resource.getrusage(resource.RUSAGE_SELF)
        baseline=dict(schema='w1-m4-archived-25point-stage-baseline-v1',
            scope='REAL_ARCHIVED_H8E_25POINT_INDEPENDENT_REPLAY_NO_NEW_BOOLEAN_OR_SOLVER',
            source_run_id=39121571756,source_artifact_id=12134772056,
            frozen_request_sha256=EXPECTED_REQUEST_SHA,archive_sha256=ARCHIVE_SHA,
            replay_binary_sha256=sha(source_bin.read_bytes()),
            completed_points=count,requested_points=count,standalone_gmp_repeats_per_point=repeats,
            all_25_replayed=count==25,all_ten_moments_exactly_equal=True,
            archived_jacobian_not_recomputed=True,fd=checked,
            archived_25point_status='FAILED_BRANCH_HASH_DRIFT_PRESERVED',
            historical_wall_seconds=hist_total,
            historical_named_stage_seconds=hist_stages,
            historical_unattributed_seconds=hist_total-sum(hist_stages.values()),
            replay_wall_seconds=total_elapsed/1e9,
            replay_stage_totals_seconds=aggregated,
            replay_unattributed_seconds=total_elapsed/1e9-sum(aggregated.values()),
            resources=dict(platform=platform.platform(),python=platform.python_version(),
                peak_self_rss_kib=rs.ru_maxrss,swap_entries=0,
                max_ram_gib=24,max_job_seconds=3600,max_compile_parallelism=4),
            native_cherchi_boolean_calls=0,fresh_geometric_self_intersection_audit=False,
            complete_solver_measured=False,paper_speed_qualified=False)
        (output/'baseline-performance.json').write_text(json.dumps(baseline,indent=2,allow_nan=False)+'\n')
        (output/'before_after.json').write_text(json.dumps(dict(
            schema='w1-m4-old-new-gate-v1',full_solver_old_new_speedup=None,
            native_cherchi_boolean_and_jacobian_parity=None,
            original_h8_25point_failure_preserved=True,
            scope='ARCHIVED_MOMENT_REPLAY_ONLY_NOT_FULL_NATIVE_PRODUCTION',
            result='BLOCKED_PENDING_FULL_MATCHED_SOLVES_AND_W0_W2_ADMISSION'),indent=2)+'\n')
        return baseline
    except BaseException as exc:
        (output/'failure.json').write_text(json.dumps(dict(schema='w1-m4-failure-v1',
            completed=len(rows),error=type(exc).__name__+': '+str(exc),
            full_solver_speedup=None,paper_speed_qualified=False),indent=2)+'\n')
        raise


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--archive',type=Path,required=True)
    ap.add_argument('--binary',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--points',type=int,default=25)
    ap.add_argument('--repeats',type=int,default=1)
    a=ap.parse_args()
    result=replay(a.archive,a.out,a.binary,count=a.points,repeats=a.repeats)
    print('M4_FINAL',json.dumps({k:result[k] for k in ('scope','completed_points','all_25_replayed','replay_wall_seconds')}))
if __name__=='__main__':main()

"""W0 M8: reproduce real 25-point Cherchi raw-moment evidence, fail closed.

This verifies two already-produced *real* GitHub Actions ZIP artifacts. It
never invokes Cherchi, never asserts a continuous smooth stratum, and never
promotes finite-difference numerical agreement to a Newton/teacher certificate.
No mutation of existing H8 evidence; all output paths use exclusive creation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gzip
from hashlib import sha256
import json
from math import isfinite
from pathlib import Path
import sys
import time
from zipfile import ZipFile

import numpy as np

NATIVE_ARCHIVE_SHA256 = "14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38"
CLASSIFICATION_ARCHIVE_SHA256 = "e17d90a8195637358d19e61fda3d8e1946cb33540f26190cead6723e7a36ef16"
NATIVE_WORKFLOW_RUN = 39121571756  # Failure is preserved.
NATIVE_ARTIFACT_ID = 12134772056
CLASSIFICATION_WORKFLOW_RUN = 39122997405  # Offline classification success only.
CLASSIFICATION_ARTIFACT_ID = 12134499573
NATIVE_REPORT_SHA256 = "7937da1e76a73612d71bc0d4352c292c2549655c770d024a06548eb8e8096d0f"
FROZEN_REQUEST_SHA256 = "1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c"
REPORT_DIR = "artifacts/h8e-jacobian-cols0-4-8/"
CLASSIFICATION_MEMBER = "twenty-five-exact-construction-classification.json"
SOURCE_PREFIX = "cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:"
STABLE_CATEGORY = "SYMBOLIC_PATCH_AND_TRIANGLE_IDENTITY_STABLE_NOT_CERTIFIED"


class ArchiveAuditError(ValueError):
    pass


def require(test, reason):
    if not bool(test):
        raise ArchiveAuditError(reason)


def digest_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def canonical_digest(value):
    return digest_bytes(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))


def read_json(data):
    def reject(constant):
        raise ArchiveAuditError("NONFINITE_JSON_TOKEN:" + constant)
    return json.loads(data, parse_constant=reject)


def open_pinned(path, expected_sha):
    path = Path(path)
    require(path.is_file() and not path.is_symlink(), "ARCHIVE_NOT_REGULAR_FILE")
    require(digest_bytes(path.read_bytes()) == expected_sha, "GITHUB_ARTIFACT_DIGEST_MISMATCH")
    zipf = ZipFile(path)
    names = zipf.namelist()
    require(len(names) == len(set(names)), "DUPLICATE_ZIP_MEMBER")
    require(all(not n.startswith("/") and ".." not in Path(n).parts for n in names),
            "UNSAFE_ZIP_MEMBER_PATH")
    return zipf


def read_member(z: ZipFile, name: str, max_bytes=50_000_000) -> bytes:
    require(name in z.namelist(), "MISSING_ARCHIVE_MEMBER:" + name)
    info = z.getinfo(name)
    require(0 < info.file_size <= max_bytes and not info.is_dir(), "UNSAFE_ARCHIVE_MEMBER_SIZE")
    raw = z.read(info)
    require(len(raw) == info.file_size, "TRUNCATED_ARCHIVE_MEMBER")
    return raw


def check_closed_indexed_surface(faces, n_vertices):
    """Every unoriented edge must appear exactly twice, in opposite directions.

    This is a combinatorial closure check, *not* exact self-intersection or
    correct semantic Boolean volume certification.
    """
    require(n_vertices >= 4 and len(faces) >= 4, "OPEN_OR_EMPTY_MATERIAL")
    edges = Counter()
    for face in faces:
        require(isinstance(face, list) and len(face) == 3 and all(type(x) is int for x in face),
                "NONINTEGER_TRIANGLE")
        a, b, c = face
        require(min(a, b, c) >= 0 and max(a, b, c) < n_vertices and len({a, b, c}) == 3,
                "OUT_OF_RANGE_OR_DEGENERATE_FACE")
        for e in ((a, b), (b, c), (c, a)):
            edges[e] += 1
    require(all(k != k[::-1] and n == 1 and edges.get(k[::-1]) == 1 for k, n in edges.items()),
            "EDGE_CLOSURE_OR_ORIENTATION_FAILED")
    return len(edges)//2


def exact_rational_ten_moments(vertices, faces, density):
    """Independent exact signed-tetrahedron integral; plain cross moments.

    Input rational strings are exact geometry (not a float mesh). A finite
    binary64 material density is interpreted as its exact Fraction.from_float.
    """
    require(isinstance(vertices, list) and len(vertices) >= 4, "INVALID_RATIONAL_VERTICES")
    require(type(density) in (int, float) and isfinite(density) and density > 0,
            "INVALID_MATERIAL_DENSITY")
    coords = []
    for row in vertices:
        require(isinstance(row, list) and len(row) == 3 and
                all(type(v) is str and '/' in v for v in row), "NON_RATIONAL_COORDINATE")
        try:
            p = tuple(Fraction(v) for v in row)
        except (ZeroDivisionError, ValueError) as exc:
            raise ArchiveAuditError("UNPARSABLE_RATIONAL_COORDINATE") from exc
        coords.append(p)
    rho = Fraction.from_float(float(density))
    result = [Fraction(0) for _ in range(10)]
    powers = ((0, 0), (1, 1), (2, 2), (1, 2), (0, 2), (0, 1))
    for i, j, k in faces:
        a, b, c = coords[i], coords[j], coords[k]
        six_vol = (a[0]*(b[1]*c[2]-b[2]*c[1])
                   + a[1]*(b[2]*c[0]-b[0]*c[2])
                   + a[2]*(b[0]*c[1]-b[1]*c[0]))
        v = rho*six_vol/6
        s = tuple(a[d]+b[d]+c[d] for d in range(3))
        result[0] += v
        for d in range(3):
            result[1+d] += v*s[d]/4
        for r, (x, y) in enumerate(powers, 4):
            result[r] += v*(s[x]*s[y]+a[x]*a[y]+b[x]*b[y]+c[x]*c[y])/20
    require(result[0] > 0, "NONPOSITIVE_SIGNED_MASS")
    return result


def target_fixed_moments(fixed, origin, axes):
    """Transform fixed raw moments model->target with real symmetric Q."""
    f=np.asarray(fixed,dtype=float)
    t=np.asarray(origin,dtype=float)
    a=np.asarray(axes,dtype=float)
    require(f.shape==(10,) and t.shape==(3,) and a.shape==(3,3,) and
            np.isfinite(f).all() and np.isfinite(t).all() and np.isfinite(a).all(),
            "INVALID_FIXED_FRAME")
    require(np.allclose(a.T@a,np.eye(3),atol=1e-12,rtol=0),"NONORTHOGONAL_FIXED_FRAME")
    m=f[0]; L=f[1:4]
    Q=np.array(((f[4],f[9],f[8]),(f[9],f[5],f[7]),(f[8],f[7],f[6])))
    lp=(L-m*t)@a.T
    qp=a@(Q-np.outer(L,t)-np.outer(t,L)+m*np.outer(t,t))@a.T
    return np.array([m,*lp,qp[0,0],qp[1,1],qp[2,2],qp[1,2],qp[0,2],qp[0,1]])


def verify_jacobian_stencils(points, report):
    J=np.asarray(report['analytic_10_by_10_jacobian'],dtype=float)
    require(J.shape == (10,10) and np.isfinite(J).all(),"INVALID_BASE_JACOBIAN")
    errors=[];feature_changes=[]
    base=points[0]
    for row in report['numeric_checks']:
        col=row['column'];indices=row['sample_indices']
        require(col in (0,4,8) and len(indices)==5 and len(set(indices))==5 and
                all(type(i) is int and 0 <= i < 25 for i in indices),
                "INVALID_FIVE_POINT_LAYOUT")
        x=np.array([points[i]['coefficients'][col]-base['coefficients'][col] for i in indices])
        require(len(set(x)) == 5 and np.isfinite(x).all(),"DUPLICATE_STENCIL_POSITION")
        scale=np.max(np.abs(x));V=np.vstack([(x/scale)**k for k in range(5)])
        w=np.linalg.solve(V,np.array([0.,1.,0.,0.,0.]))/scale
        y=np.array([points[i]['independent_variable_raw_moments'] for i in indices])
        value=w@y
        err=float(np.max(np.abs(value-J[:,col])/np.maximum(1.,np.abs(J[:,col]))))
        errors.append(err)
        stable=all(points[i]['feature_branch_hash']==base['feature_branch_hash'] for i in indices)
        feature_changes.append(not stable)
        require(abs(err-row['max_scaled_derivative_error']) <= 5e-9,
                "NUMERIC_FIVE_POINT_REPORT_MISMATCH")
        require(bool(row['numerical_passed']) == (err<=1e-6),"NUMERIC_ACCEPTANCE_FLAG_MISMATCH")
        require(row['feature_hash_stable'] is stable,"BRANCH_IDENTITY_FLAG_MISMATCH")
    q=np.asarray(base['coefficients'],dtype=float)
    null_norm=float(np.linalg.norm(J@q))
    require(abs(null_norm-report['scale_null_direction_norm'])<1e-12,
            "NULL_SCALE_JACOBIAN_MISMATCH")
    return dict(numerical_checks=len(errors),numerical_max_scaled_error=max(errors),
                check_reproduced_count=len(errors),feature_unstable_stencils=sum(feature_changes),
                scale_null_direction_norm=null_norm)


def audit(native_archive,classification_archive):
    t0=time.perf_counter()
    with open_pinned(native_archive,NATIVE_ARCHIVE_SHA256) as n, \
         open_pinned(classification_archive,CLASSIFICATION_ARCHIVE_SHA256) as cl:
        require(len(cl.namelist()) == 1 and cl.namelist()[0]==CLASSIFICATION_MEMBER,
                "INVALID_CLASSIFIER_ARCHIVE_MANIFEST")
        report_bytes=read_member(n,REPORT_DIR+'report.json')
        request_bytes=read_member(n,'artifacts/h8-request/prepared-request.json',max_bytes=10_000_000)
        classification=read_json(read_member(cl,CLASSIFICATION_MEMBER))
        report=read_json(report_bytes);request=read_json(request_bytes)
        require(digest_bytes(report_bytes)==NATIVE_REPORT_SHA256, "NATIVE_REPORT_SHA_MISMATCH")
        require(digest_bytes(request_bytes)==FROZEN_REQUEST_SHA256, "FROZEN_REQUEST_SHA_MISMATCH")
        require(report['input_request_sha256']==FROZEN_REQUEST_SHA256 and
                classification['source_report_sha256']==NATIVE_REPORT_SHA256 and
                classification['request_sha256']==FROZEN_REQUEST_SHA256,
                "CLASSIFICATION_SOURCE_REPORT_NOT_BOUND")
        require(report['schema']=='heart-h8e-real-cherchi-jacobian-pilot-v1' and
                report['scope']=='H8_RECONSTRUCTED_CAD_ONLY_NOT_AUTHOR_ORIGINAL' and
                report['columns_requested']==[0,4,8] and
                report['completed_samples']==report['planned_sample_count']==report['production_cherchi_calls']==25,
                "NOT_THE_FROZEN_25_POINT_NATIVE_JOB")
        require(report['formal_newton_converged'] is False and
                report['qualified_branch_neighborhood'] is False and
                report['objective_stationarity_certified'] is False and
                report['complete_eighty_one_samples'] is False and
                report['original_author_cad'] is False,
                "UNSUPPORTED_NATIVE_PROOF_PROMOTION")
        require(classification['complete_material_snapshots_verified']==25 and
                classification['exact_plane_diagnostics_resolved_points']==25 and
                classification['exact_plane_diagnostics_unresolved_points']==0 and
                classification['classifications']=={STABLE_CATEGORY:24} and
                classification['certified_smooth_neighborhood'] is False and
                classification['certified_newton_direction'] is False,
                "CLASSIFICATION_PROOF_PROMOTED")
        witnesses=classification['witnesses']
        require(len(witnesses)==25 and all(row['index']==i for i,row in enumerate(witnesses)),
                "CLASSIFICATION_MISSING_WITNESS")
        comparisons=classification['comparisons']
        require(len(comparisons)==24 and all(row['index']==i+1 and
                row['status']==STABLE_CATEGORY and
                row['qualified_smooth_derivative'] is False and
                row['qualified_boolean_set_continuity'] is False and
                row['exact_material_audit_performed'] is False for i,row in enumerate(comparisons)),
                "CLASSIFICATION_NONSUPPORT_OR_INDEX_DRIFT")
        r = request['request']; density=r['material_density'];fixed_target=target_fixed_moments(
            r['fixed_shell_moments'],r['target_origin'],r['target_axes'])
        points=[];per_sample=[];max_error=0.;max_fixed_error=0.;closed_meshes=0
        for i in range(25):
            base=REPORT_DIR+f'point-{i:03d}'
            meta=read_json(read_member(n,base+'.json'))
            zipped=read_member(n,base+'-material.json.gz',max_bytes=3_000_000)
            actual_sha=digest_bytes(zipped)
            require(actual_sha==meta['exact_same_call_material_archive_sha256']==witnesses[i]['archive_sha256'],
                    "MATERIAL_ARCHIVE_SHA_MISMATCH")
            require(meta['index']==i,"POINT_INDEX_CHANGED")
            raw=gzip.decompress(zipped)
            require(len(raw)<30_000_000,"UNSAFE_DECOMPRESSED_MATERIAL")
            m=read_json(raw)
            require(meta['vertex_count']==len(m['variable_rational_vertices'])==len(m['variable_vertices']) and
                    meta['triangle_count']==len(m['variable_faces']) and
                    m['quadric_coefficients']==meta['coefficients'] and
                    m['geometry_hash']==meta['material_geometry_hash'] and
                    m['topology_hash']==meta['feature_branch_hash'] and
                    m['boolean_backend_identity']==meta['native_boolean_backend'] and
                    m['boolean_backend_identity']==SOURCE_PREFIX+report['actual_cherchi_sha256'],
                    "MATERIAL_METADATA_IDENTITY_DRIFT")
            require(m['derivative_defined'] is True and
                    m['material_proof']['schema']=='cherchi-same-call-material-v1' and
                    np.array(m['moment_jacobian']).shape==(10,10),
                    "INCOMPLETE_SAME_CALL_DERIVATIVE")
            require(canonical_digest(dict(vertices=m['material_proof']['exact_vertices'],
                                          faces=m['variable_faces']))==m['geometry_hash'],
                    "RATIONAL_GEOMETRY_DIGEST_MISMATCH")
            require(canonical_digest(dict(vertices=m['quadric_source_vertices'],
                                          faces=m['quadric_source_faces'],
                                          coefficients=m['quadric_coefficients']))==m['quadric_source_identity'],
                    "QUADRIC_SOURCE_DIGEST_MISMATCH")
            directed_edges=check_closed_indexed_surface(m['variable_faces'],meta['vertex_count'])
            closed_meshes+=1
            exact=exact_rational_ten_moments(m['variable_rational_vertices'],m['variable_faces'],density)
            product=np.asarray([float(x) for x in exact],dtype=float)
            recorded=np.asarray(m['variable_raw_moments'],dtype=float)
            independently=np.asarray(meta['independent_variable_raw_moments'],dtype=float)
            produced=np.asarray(meta['production_variable_raw_moments'],dtype=float)
            all_expected=(recorded,independently,produced)
            require(all(row.shape==(10,) and np.isfinite(row).all() for row in all_expected),
                    "NONFINITE_OR_WRONG_MOMENTS")
            error=max(float(np.max(np.abs(product-row))) for row in all_expected)
            require(error<=1e-10, "INDEPENDENT_TEN_MOMENTS_DISAGREE")
            max_error=max(max_error,error)
            total=np.asarray(m['raw_moments'],dtype=float)
            require(np.max(np.abs(total-np.asarray(meta['full_raw_moments'],dtype=float)))<=1e-12,
                    "FULL_MOMENT_POINT_MISMATCH")
            ferr=float(np.max(np.abs((total-recorded)-fixed_target)))
            require(ferr<=1e-10,"FIXED_MATERIAL_TARGET_FRAME_MISMATCH")
            max_fixed_error=max(max_fixed_error,ferr)
            if i==0:
                require(np.max(np.abs(np.asarray(m['moment_jacobian'])-
                                   np.asarray(report['analytic_10_by_10_jacobian'])))<=1e-14,
                        "BASE_JACOBIAN_REPORT_NOT_BOUND")
            witness=witnesses[i]['witness']
            require(witness is not None and witness['vertex_count']==meta['vertex_count'] and
                    witness['face_count']==meta['triangle_count'] and
                    witnesses[i]['unresolved_error'] is None,
                    "CLASSIFICATION_MESH_WITNESS_MISMATCH")
            points.append(meta)
            per_sample.append(dict(index=i,archive_sha256=actual_sha,vertex_count=meta['vertex_count'],
                                   face_count=meta['triangle_count'],closed_undirected_edges=directed_edges,
                                   exact_ten_moment_max_abs_error=error,
                                   fixed_target_max_abs_error=ferr,feature_hash=meta['feature_branch_hash']))
        require(report['all_same_call_material_snapshots_sha256_saved'] is True and
                report['all_numerical_checks_passed'] is True and
                report['all_tested_stencils_same_feature_hash'] is False and
                report['changed_feature_hash_points']==sum(p['feature_branch_hash']!=points[0]['feature_branch_hash'] for p in points[1:]),
                "ORIGINAL_FAILURE_GATE_LOST")
        stencils=verify_jacobian_stencils(points,report)
        return dict(schema='W0_M8_REAL_H8E_25POINT_OFFLINE_AUDIT_V1',
                    source_workflow=dict(id=NATIVE_WORKFLOW_RUN,conclusion='failure',
                                         artifact_id=NATIVE_ARTIFACT_ID,archive_sha256=NATIVE_ARCHIVE_SHA256),
                    classification_workflow=dict(id=CLASSIFICATION_WORKFLOW_RUN,conclusion='success',
                                                 artifact_id=CLASSIFICATION_ARTIFACT_ID,
                                                 archive_sha256=CLASSIFICATION_ARCHIVE_SHA256),
                    raw_report_sha256=NATIVE_REPORT_SHA256,request_sha256=FROZEN_REQUEST_SHA256,
                    scope='RECONSTRUCTED_H8_FINITE_SAMPLES_NOT_ORIGINAL_AUTHOR_CAD',
                    completed_genuine_archive_points=len(per_sample),
                    closure_checked_points=closed_meshes,
                    independently_reintegrated_ten_moments=25,
                    maximum_ten_moment_abs_error=max_error,
                    maximum_fixed_target_abs_error=max_fixed_error,
                    original_feature_hash_changes=report['changed_feature_hash_points'],
                    classification_counts=classification['classifications'],
                    numerical_checks=stencils,
                    per_point=per_sample,
                    independent_native_boolean_executed=False,
                    open_smooth_neighborhood_certified=False,
                    newton_terminal_certified=False,
                    physically_valid_material_sealed=False,
                    training_admissible=False,
                    actual_zip_reaudit_wall_seconds=time.perf_counter()-t0)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-archive',required=True,type=Path)
    parser.add_argument('--classification-archive',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    a=parser.parse_args(argv)
    if a.output.exists() or a.output.is_symlink():
        print('OUTPUT_EXISTS_NO_OVERWRITE',file=sys.stderr)
        return 4
    try:
        result=audit(a.native_archive,a.classification_archive)
    except (ArchiveAuditError,ValueError,KeyError,TypeError,EOFError,OSError,gzip.BadGzipFile,IndexError) as error:
        result=dict(schema='W0_M8_REAL_H8E_25POINT_OFFLINE_AUDIT_V1',
                    status='AUDIT_REJECTED',failure=f'{type(error).__name__}: {error}',
                    training_admissible=False)
        exitcode=2
    else:
        result['status']='REAL_ARCHIVE_FINITE_POINT_MOMENTS_VERIFIED_NOT_NEWTON'
        exitcode=0
    try:
        with a.output.open('x',encoding='utf-8') as stream:
            json.dump(result,stream,indent=2,sort_keys=True,allow_nan=False)
            stream.write('\n')
    except FileExistsError:
        print('OUTPUT_EXISTS_NO_OVERWRITE',file=sys.stderr)
        return 4
    print(result['status'], 'points:',result.get('completed_genuine_archive_points',0),
          'training_admissible:',result['training_admissible'])
    return exitcode


if __name__=='__main__':
    raise SystemExit(main())

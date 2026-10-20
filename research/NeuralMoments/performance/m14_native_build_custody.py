"""W1 M14: independent *built-binary custody* and five-call evidence admission.

Only accepts a NEW, completed M13 host build and its actual M11/M5/M9
same-call material receipts. It does not execute geometry, and never labels
an archived packet, synthetic test, or missing native .so as a fresh solve.

M13/M11 remain the sole real-native build/execution paths. All inputs are
verified read-only. The new receipt certifies only source/build/evidence custody;
no full Newton speed, terminal printable part, teacher or paper claim follows.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import m10_native_host_runner as m10
import m13_pinned_native_build as m13
import m11_native_evidence_gate as m11

PROTECTED = (
    'src', 'bindings', 'python/make_it_stand',
    'research/Heart_v1_20261017', '.github/workflows', 'CMakeLists.txt',
)
BUILT_STAGES = ('configure-core', 'build-core', 'configure-cherchi', 'build-cherchi')
SCHEMA = 'w1-m14-native-build-and-five-call-custody-v1'
OWNED_PREFIX = 'research/NeuralMoments/performance/'
LAUNCH_FILE = 'research/ParallelLaunch/W1_START_HERE.md'


def _sha(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _git(root, *args):
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                       text=True, timeout=30, check=False)
    if p.returncode != 0:
        raise ValueError('M14_GIT_PROVENANCE_COMMAND_FAILED:'+' '.join(args[:2]))
    return p.stdout.strip()


def protected_checkout(root):
    """Prevent a dirty/forked production tree from being called frozen.

    Untracked build output stays permitted; tracked source modifications and
    *committed* drift relative to the frozen base are not.
    """
    root=Path(root).resolve()
    identity=m10.repo_identity(root)
    changes=_git(root,'diff','--name-only',m10.FREEZE,'HEAD')
    forbidden=[p for p in changes.splitlines() if not (
        p.startswith(OWNED_PREFIX) or p==LAUNCH_FILE)]
    if forbidden:
        raise ValueError('M14_COMMIT_OUTSIDE_W1_EXCLUSIVE_SCOPE:'+forbidden[0])
    changed=_git(root,'diff','--name-only',m10.FREEZE,'HEAD','--',*PROTECTED)
    if changed:
        raise ValueError('M14_COMMITTED_PRODUCTION_SOURCE_DRIFT:'+changed.splitlines()[0])
    unstaged=_git(root,'diff','--name-only','--',*PROTECTED)
    if unstaged:
        raise ValueError('M14_DIRTY_UNSTAGED_PRODUCTION_SOURCE:'+unstaged.splitlines()[0])
    staged=_git(root,'diff','--cached','--name-only','--',*PROTECTED)
    if staged:
        raise ValueError('M14_DIRTY_STAGED_PRODUCTION_SOURCE:'+staged.splitlines()[0])
    src=m10._source_identity(root)
    return dict(**identity,production_source=src,
                critical_paths_frozen=True,tracked_production_tree_clean=True)


def _json(path):
    return m11._load(path)


def _assert(condition, error):
    if not condition:
        raise ValueError('M14_'+error)


def custody(root, archive, artifacts):
    """Independently accept immutable M13 build + existing M11 science receipts.

    This function never substitutes itself for native Boolean or native exact
    self-intersection checks. If prerequisites don't exist, it raises.
    """
    root,archive,artifacts=Path(root).resolve(),Path(archive).resolve(),Path(artifacts).resolve()
    identity=protected_checkout(root)
    m10.archive_identity(archive)  # frozen original H8c ZIP and request
    pinned=m13._source_check(root)
    _assert(pinned.get('pinned') is True and
            pinned.get('cherchi_head')==m13.CHERCHI_COMMIT and
            pinned.get('cgal_head')==m13.CGAL_COMMIT,
            'CHERCHI_OR_CGAL_SOURCE_UNPINNED')
    m10._swap_guard()
    limits=m10._memory_limit()
    _assert(limits['process_address_space_cap_bytes']>=m13.MIN_BUILD_MEMORY,
            'BUILD_HOST_BUDGET_BELOW_SIX_GIB')

    build=_json(artifacts/'native-build-receipt.json')
    _assert(build.get('schema')=='w1-m13-pinned-native-build-v1',
            'M13_BUILD_RECEIPT_SCHEMA')
    _assert(build.get('git_branch')==m10.BRANCH and
            build.get('full_solver_speedup') is None and
            build.get('paper_speed_qualified') is False,
            'M13_BUILD_RECEIPT_SCOPE')
    _assert(build.get('pinned_revision')==pinned,
            'M13_BUILD_SOURCE_REVISION_DRIFT')
    _assert(build.get('compiled_native_import',{}).get('cpp_extensions_imported') is True and
            build['compiled_native_import'].get('validated_modules')==3,
            'M13_IMPORT_WAS_NOT_EXECUTED')
    logs=build.get('build_commands')
    _assert(isinstance(logs,list) and [x.get('stage') for x in logs]==list(BUILT_STAGES),
            'INCOMPLETE_OR_REORDERED_NATIVE_BUILD')
    for row in logs:
        name=row['stage']
        _assert(row.get('exit_code')==0 and isinstance(row.get('wall_ns'),int) and
                row['wall_ns']>0 and row.get('log_sha256')==_sha(artifacts/(name+'.log')),
                'BUILD_LOG_OR_EXIT_DRIFT:'+name)
    core=(root/m13.BUILD_CORE_REL).resolve()
    cherchi=(root/m13.BUILD_CHERCHI_REL).resolve()
    args={x['stage']:x.get('argv') for x in logs}
    # Prevent a legitimate-looking output directory with unrelated build commands.
    _assert(args['build-core']==['cmake','--build',str(core),'--target',
                 '_make_it_stand','--parallel',args['build-core'][-1]] and
            args['build-cherchi']==['cmake','--build',str(cherchi),
                 '--parallel',args['build-cherchi'][-1]],
            'BUILD_COMMAND_OR_TARGET_DRIFT')
    for name in ('build-core','build-cherchi'):
        count=args[name][-1]
        _assert(isinstance(count,str) and count in {'1','2','3','4'},
                'MAX_FOUR_NATIVE_BUILD_WORKERS')
    _assert(isinstance(args['configure-core'],list) and
            '-DMAKE_IT_STAND_BUILD_SPIN_IT_FASTER=ON' in args['configure-core'] and
            '-DMAKE_IT_STAND_BUILD_EXACT_GEOMETRY_CHECKS=ON' in args['configure-core'] and
            '-DMAKE_IT_STAND_BUILD_PYTHON=ON' in args['configure-core'] and
            isinstance(args['configure-cherchi'],list) and
            '-DMAKE_IT_STAND_CHERCHI_RATIONAL_ARITHMETIC=ON' in args['configure-cherchi'],
            'REQUIRED_NATIVE_BUILD_FLAGS_MISSING')
    rewrite=build.get('boost_ninja_rewrite',{})
    _assert(rewrite.get('host_libraries_untouched') is True and
            rewrite.get('after_sha256')==_sha(core/'build.ninja'),
            'NINJA_GRAPH_IDENTITY_DRIFT')

    modules=m10.module_inventory(root,[core/'python',cherchi/'python'])
    expected=build.get('actual_compiled_modules')
    _assert(isinstance(expected,dict) and set(expected)==set(m10.NATIVE),
            'INCOMPLETE_BUILD_BINARY_SET')
    for name in m10.NATIVE:
        row=modules.get(name,{})
        location=Path(row.get('path','/nonexistent')).resolve()
        owned_by_build=(location.is_relative_to((core/'python').resolve()) or
                        location.is_relative_to((cherchi/'python').resolve()))
        _assert(row.get('status')=='FOUND' and row.get('sha256')==expected[name] and
                location.is_file() and owned_by_build and
                _sha(location)==expected[name],
                'BUILT_EXTENSION_NOT_OWNED_BY_M13:'+name)
    before=_json(artifacts/'m11/work/preflight.json')
    _assert(before.get('state')=='READY_FOR_REAL_NATIVE_ABBA' and
            before.get('checks',{}).get('git',{}).get('details',{}).get('head')==identity['head'],
            'M11_REAL_SOURCE_PROVENANCE_DRIFT')
    _assert(before.get('checks',{}).get('archive',{}).get('details',{}).get('zip_sha256')==m10.ARCHIVE_SHA,
            'H8C_ARCHIVE_CUSTODY_DRIFT')
    saved_summary=_json(artifacts/'m11/m11-native-validation-summary.json')
    verified_file=artifacts/'m11/m11-verified-native-receipts.json'
    saved_proof=_json(verified_file)
    _assert(saved_summary.get('schema')=='w1-m11-native-receipt-suite-v1' and
            saved_summary.get('state')=='FIVE_REAL_CHERCHI_EVALUATIONS_AND_SAVED_RECEIPTS_ADMITTED' and
            saved_summary.get('native_samples')==5 and
            saved_summary.get('admission_document_sha256')==_sha(verified_file) and
            saved_summary.get('full_solver_speedup') is None and
            saved_summary.get('newton_terminal_verified') is False,
            'INCOMPLETE_M11_FIVE_CALL_SUMMARY')
    fresh=m11.verify(artifacts/'m11/work/preflight.json',
                     artifacts/'m11/work/m5',artifacts/'m11/work/m9')
    _assert(saved_proof==fresh and
            fresh.get('complete_native_ledger_rows')==5 and
            fresh.get('native_imports_attested_by_m10') is True,
            'SAVED_M11_INDEPENDENT_RECEIPT_DRIFT')
    _assert(protected_checkout(root)==identity and
            m13._source_check(root)==pinned,
            'SOURCE_CHANGED_DURING_CUSTODY_AUDIT')
    return dict(schema=SCHEMA,scope='M13_FROZEN_BUILT_BINARIES_AND_M11_FIVE_SAME_Q_RECEIPTS_ONLY',
                branch=m10.BRANCH,commit_sha=identity['head'],
                native_binary_sha256=expected,
                original_h8c_archive_sha256=m10.ARCHIVE_SHA,
                original_h8c_request_sha256=m10.REQUEST_SHA,
                pinned_cherchi_revision=m13.CHERCHI_COMMIT,
                pinned_cgal_revision=m13.CGAL_COMMIT,
                original_material_hash_preserved=True,
                build_receipt_sha256=_sha(artifacts/'native-build-receipt.json'),
                m11_original_receipt_sha256=_sha(verified_file),
                reproduced_abba_single_q_ratio=fresh['reproduced_abba_single_q_ratio'],
                certified_scientific_eval_calls=5,certified_newton_solves=0,
                full_solver_speedup=None,production_optimization_merged=False,
                w0_w2_teacher_admitted=False,paper_speed_qualified=False)


def _write_new(path, object_value):
    with Path(path).open('x',encoding='utf-8') as out:
        json.dump(object_value,out,indent=2,sort_keys=True,allow_nan=False)
        out.write('\n')


def execute(root, archive, artifacts, output):
    """Existing artifact verifier: writes success only after complete audit."""
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    try:
        result=custody(root,archive,artifacts)
        _write_new(output/'admission.json',result)
        return result
    except BaseException as ex:
        _write_new(output/'failure.json',dict(schema='w1-m14-fail-closed-v1',
            status='BLOCKED_OR_FAILED_NO_FRESH_NATIVE_CERTIFICATION',
            error=type(ex).__name__+': '+str(ex),
            verified_native_calls=0,full_solver_speedup=None,paper_speed_qualified=False))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--m13-artifacts',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    report=execute(args.root,args.archive,args.m13_artifacts,args.output)
    print(json.dumps(dict(status='FIVE_REAL_RECEIPT_CUSTODY_ADMITTED_NOT_NEWTON',
                          full_solver_speedup=report['full_solver_speedup']),sort_keys=True))

if __name__=='__main__':
    main()

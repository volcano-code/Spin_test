"""Fail-closed terminal delivery from a REAL v7 Cherchi/Faster convergence.

Re-evaluates q with actual Cherchi, constructs independent rational terminal
material with CGAL, and unites with the exact frozen fixed geometry.
Never converts RESOURCE_LIMIT_REACHED into CONVERGED and never modifies q.
"""
from __future__ import annotations
import argparse, gzip, hashlib, json, sys, time, traceback
from dataclasses import asdict
from pathlib import Path
from fractions import Fraction as Q
import numpy as np
from make_it_stand import spin
from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
sys.path.insert(0, '/mnt/data/Noodles_v6_C4_work/code')
from common import ExactBuilder, export_obj, write_json, sha, token, load_json

ROOT=Path(__file__).resolve().parent
BOOL=Path('/mnt/data/Noodles_v6_C4_work/native/noodles-exact-boolean')


def rolepath(role):
    return ROOT / ('two-stage-generic-retriangulation-candidate-rational.json' if role=='design'
                   else f'{role}-two-stage-retriangulation-candidate-rational.json')


def mesh(role):
    p=rolepath(role)
    packet=load_json(p)
    return packet, np.asarray([[float(Q(x)) for x in point] for point in packet['vertices']],dtype=np.float64), np.asarray(packet['faces'],dtype=np.int32)


def from_moving_source(mat):
    assert mat['quadric_source_vertices'] and mat['quadric_source_faces']
    return {'vertices': [[token(Q(float(x))) for x in pt] for pt in mat['quadric_source_vertices']],
            'faces': mat['quadric_source_faces']}


def run(args):
    start=time.monotonic(); out=args.output.resolve()
    out.mkdir(exist_ok=False,parents=True)
    log={'schema':'noodles-v7-terminal-reconstruction-gated-v1', 'status':'STARTED',
         'numerical_newton_converged':False,'independent_exact_export_passed':False,
         'no_GitHub_write':True, 'binary_source_checkpoint':'b0a13e3_not_latest_branch'}
    try:
        solver=load_json(args.solver/'solver-canonical-result.json')
        if solver.get('status')!='CONVERGED':raise RuntimeError('NUMERICAL_NEWTON_NOT_CONVERGED')
        q=solver.get('quadric_coefficients')
        if not isinstance(q,list) or len(q)!=10 or not np.isfinite(q).all():raise RuntimeError('NO_VALID_FINAL_Q')
        events=[json.loads(s) for s in (args.solver/'events.jsonl').read_text().splitlines()]
        accepted=[e for e in events if e.get('type')=='evaluation' and e.get('outcome')=='accepted']
        if not accepted or tuple(accepted[-1].get('quadric_coefficients',()))!=tuple(q):
            raise RuntimeError('SOLVER_Q_NOT_SAME_AS_LAST_ACCEPTED_EVENT')
        config=load_json(args.solver/'request.json')
        for role in ('design','fixed','initial'):
            if config['input_sha256'][role]!=sha(rolepath(role)):
                raise RuntimeError('SOURCE_DIGEST_CHANGED:'+role)
            proofpath=ROOT/('final-design-global-exact-chain-proof.json' if role=='design' else f'{role}-final-global-exact-chain-proof.json')
            proof=load_json(proofpath)
            if not proof.get('exact_surface_chain_equal',proof.get('success',False)):
                raise RuntimeError('MISSING_EQUIVALENCE_PROOF:'+role)
        fixedreport=load_json(ROOT/'fixed-v7-GMP-exact-moments.json')
        if fixedreport['status']!='COMPLETE' or fixedreport['source_sha256']!=sha(ROOT/'exact_v7c/fixed-rational.json'):
            raise RuntimeError('FIXED_MOMENTS_IDENTITY')
        F,FV,FF=mesh('fixed');D,DV,DF=mesh('design');A,AV,AF=mesh('initial')
        settings=spin.SpinSolverConfig(**config['settings']); ec=spin.SpinEvaluatorConfig(**config['evaluator'])
        req=spin.SpinItFasterRequest(outer_vertices=tuple(map(tuple,AV)),outer_faces=tuple(map(tuple,AF)),
            design_vertices=tuple(map(tuple,DV)),design_faces=tuple(map(tuple,DF)),
            fixed_shell_moments=tuple(fixedreport['mass_moments']),target_origin=(0.,0.,-.16),
            mode='SPINNING_TOP',material_density=1.,original_units_per_normalized_unit=.025,
            center_of_mass_weight=1.,settings=settings)
        if req.request_digest!=config['request_digest']:raise RuntimeError('REQUEST_CHANGED')
        log.update(numerical_newton_converged=True, solver_status='CONVERGED',
                   solver_sha=sha(args.solver/'solver-canonical-result.json'),q=q,request_digest=req.request_digest,
                   input_sha256={r:sha(rolepath(r)) for r in ('fixed','design','initial')})
        evaluator=InProcessCherchiEvaluator(req,ec,rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1')
        evaluator(tuple(float(x) for x in q))
        mat=evaluator.material(tuple(float(x) for x in q))
        if tuple(map(float,mat['quadric_coefficients']))!=tuple(q):raise RuntimeError('CHERCHI_MATERIAL_Q_MISMATCH')
        if not mat['boolean_backend_identity'].startswith('cherchi-reference'):
            raise RuntimeError('NOT_CHERCHI_BACKEND')
        with gzip.open(out/'cherchi-terminal-material.json.gz','wt',compresslevel=2) as f:
            json.dump(mat,f,allow_nan=False,default=lambda v:v.tolist() if isinstance(v,np.ndarray) else float(v))
        log.update(cherchi_material_sha256=sha(out/'cherchi-terminal-material.json.gz'),
                   cherchi_variable_faces=len(mat['variable_faces']),cherchi_geometry_hash=mat['geometry_hash'],
                   cherchi_topology_hash=mat['topology_hash'],material_replay_source='FRESH_CHERCHI_Q_NOT_ORIGINAL_SAME_CALL')
        op='intersection' if mat['boolean_operation']=='intersection' else 'difference'
        if mat['boolean_operation'] not in ('intersection','subtraction','difference'):raise RuntimeError('UNKNOWN_MATERIAL_SIDE')
        source=from_moving_source(mat)
        builder=ExactBuilder(BOOL,out/'exact-csg',timeout=args.operation_timeout)
        retained=builder.boolean(D,source,op)
        write_json(out/'retained-rational.json',retained)
        print('V7 TERMINAL EXACT RETAINED',len(retained['faces']),flush=True)
        complete=builder.boolean(F,retained,'union')
        write_json(out/'complete-rational.json',complete)
        print('V7 TERMINAL EXACT WHOLE',len(complete['faces']),flush=True)
        export_obj(out/'retained-mm.obj',retained,scale=25.0,label='V7_TRUE_CHERCHI_NEWTON_RETENTION_CGAL_OFFLINE')
        export_obj(out/'fixed-mm.obj',F,scale=25.0,label='V7_PAPER_GUIDED_FROZEN_STRANDS')
        export_obj(out/'initial-mm.obj',A,scale=25.0,label='V7_BEFORE_OPTIMIZATION')
        export_obj(out/'complete-mm.obj',complete,scale=25.0,label='V7_CONVERGED_CGAL_EXACT_UNION_PENDING_INDEPENDENT_AUDIT')
        log.update(status='EXACT_OBJECT_EXPORTED_PENDING_NATIVE_AND_PHYSICS_VERIFICATION',
                   independent_exact_export_passed=True, boolean_operations=builder.index,
                   faces={'retained':len(retained['faces']),'complete':len(complete['faces']),'fixed':len(F['faces'])},
                   output_sha256={p:sha(out/p) for p in ('complete-mm.obj','retained-mm.obj','fixed-mm.obj','initial-mm.obj')})
    except BaseException as exc:
        log.update(status='FAILED_NO_QUALIFIED_MODEL',exception=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc())
        raise
    finally:
        log['elapsed_seconds']=time.monotonic()-start
        (out/'export-status.json').write_text(json.dumps(log,indent=2,ensure_ascii=False,allow_nan=False))
    return log

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--solver',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--operation-timeout',type=int,default=600)
    print(run(ap.parse_args()))

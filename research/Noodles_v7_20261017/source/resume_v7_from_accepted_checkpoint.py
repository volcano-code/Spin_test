"""Noodles v7 REAL Cherchi+Faster numerical *pilot*, no final-case claim.

The model-specific inputs live in data files only; no model-specific solver
branches, objectives, thresholds, or guaranteed success declarations.
"""
from pathlib import Path
from fractions import Fraction as Q
from dataclasses import asdict
import hashlib,json,sys,time,traceback,os,argparse
import numpy as np
from make_it_stand import spin
from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
R=Path(__file__).resolve().parent
ap=argparse.ArgumentParser()
ap.add_argument('--iterations',type=int,default=12)
ap.add_argument('--continue-from',type=Path,required=True)
ap.add_argument('--evaluations',type=int,default=16)
ap.add_argument('--output',type=Path,default=R/'pilot-v7-newton-seed0')
a=ap.parse_args()
a.output.mkdir(parents=True,exist_ok=False)
start=time.monotonic();o=a.output

def log(*x):print('V7',round(time.monotonic()-start,2),*x,flush=True)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(role):
 p=R/('two-stage-generic-retriangulation-candidate-rational.json' if role=='design' else f'{role}-two-stage-retriangulation-candidate-rational.json')
 d=json.loads(p.read_text());V=np.asarray([[float(Q(x)) for x in row] for row in d['vertices']],dtype=np.float64);F=np.asarray(d['faces'],dtype=np.int64)
 return V,F,p
log('PREFLIGHT')
for role in ('design','fixed','initial'):
 guardpath=R/('two-stage-generic-retriangulation-f64-guard.json' if role=='design' else f'{role}-two-stage-retriangulation-f64-guard.json')
 guard=json.loads(guardpath.read_text())
 if not guard['ready_for_cherchi_float_input']:raise RuntimeError('UNSAFE_FLOAT64_INPUT:'+role)
 nativepath=R/('final-design-native-binary64-audit.json' if role=='design' else f'{role}-final-native-boundary-audit.json')
 audit=json.loads(nativepath.read_text())
 if not audit.get('success'):raise RuntimeError('NATIVE_BOUNDARY_NOT_PASSED:'+role)
 proofpath=R/('final-design-global-exact-chain-proof.json' if role=='design' else f'{role}-final-global-exact-chain-proof.json')
 proof=json.loads(proofpath.read_text())
 if not proof.get('exact_surface_chain_equal',proof.get('success',False)):raise RuntimeError('NO_GLOBAL_EXACT_EQUIVALENCE:'+role)
 log('PASS_ROLE',role)
F0,Ff,pfixed=load('fixed');D0,Df,pdesign=load('design');A0,Af,pinitial=load('initial')
fixed=json.loads((R/'fixed-v7-GMP-exact-moments.json').read_text());src=R/'exact_v7c/fixed-rational.json'
if fixed['status']!='COMPLETE' or fixed['source_sha256']!=sha(src):raise RuntimeError('FIXED_GMP_IDENTITY_INVALID')
log('LOADED',len(A0),len(Af),len(D0),len(Df),'fixed_mass',fixed['mass_moments'][0]);
settings=spin.SpinSolverConfig(maximum_iterations=a.iterations,maximum_restarts=1,maximum_function_evaluations_per_restart=a.evaluations,equation_tolerance=1e-12,deterministic_seed=0,equation_profile='DUAL_MONOMIAL_RAW_V1')
tri=spin.SpinEvaluatorConfig(derivative_method='DISCRETE_FULL_RANK_QUADRIC',icosphere_subdivisions=2,maximum_icosphere_subdivisions=2,retain_fixed_normal_provenance=True,algebraic_finite_map=True)
req=spin.SpinItFasterRequest(outer_vertices=tuple(map(tuple,A0)),outer_faces=tuple(map(tuple,Af)),design_vertices=tuple(map(tuple,D0)),design_faces=tuple(map(tuple,Df)),fixed_shell_moments=tuple(fixed['mass_moments']),target_origin=(0.,0.,-.16),mode='SPINNING_TOP',material_density=1.,original_units_per_normalized_unit=.025,center_of_mass_weight=1.,settings=settings)
config=dict(schema='noodles-v7-real-Cherchi-Faster-pilot',request_digest=req.request_digest,settings=asdict(settings),evaluator=asdict(tri),input_sha256={r:sha(p) for r,p in [('fixed',pfixed),('design',pdesign),('initial',pinitial)]},fixed_gmp_sha256=sha(src),static_rounded_partition_strictly_certified=False,original_paper_CAD=False,scientific_status='NUMERICAL_PILOT_NOT_FULL_CASE_ADMISSION')
(o/'request.json').write_text(json.dumps(config,indent=2,default=str))
# Resume from an actually *accepted* Newton checkpoint, never from last rejected trial.
parent=a.continue_from
parent_events_path=parent/'events.jsonl'
parent_summary_path=parent/'solver-result.json'
parent_summary=json.loads(parent_summary_path.read_text())
parent_events=[json.loads(line) for line in parent_events_path.read_text().splitlines() if line.strip()]
accepted=[e for e in parent_events if e.get('type')=='evaluation' and e.get('outcome')=='accepted' and e.get('quadric_coefficients') is not None]
if not accepted:raise RuntimeError('NO_ACCEPTED_CHECKPOINT')
last=accepted[-1]
if abs(float(last['normalized_equation_residual'])-float(parent_summary['normalized_equation_residual']))>1e-10:
 raise RuntimeError('PARENT_SOLVER_TRACE_MISMATCH')
if last.get('equation_profile')!='DUAL_MONOMIAL_RAW_V1':raise RuntimeError('EQUATION_PROFILE_CHANGED')
parent_req=json.loads((parent/'request.json').read_text())
# Digest covers runtime budgets: permit ONLY a longer maximum-iterations/evaluations budget.
for k in set(parent_req) | set(config):
 if k not in ('request_digest','settings') and parent_req.get(k)!=config.get(k):
  raise RuntimeError('PHYSICAL_REQUEST_CHANGED:'+k)
for k in set(parent_req['settings']) | set(config['settings']):
 if k not in ('maximum_iterations','maximum_function_evaluations_per_restart') and parent_req['settings'].get(k)!=config['settings'].get(k):
  raise RuntimeError('SCIENTIFIC_SETTING_CHANGED:'+k)
if config['settings']['maximum_iterations']<parent_req['settings']['maximum_iterations'] or config['settings']['maximum_function_evaluations_per_restart']<parent_req['settings']['maximum_function_evaluations_per_restart']:
 raise RuntimeError('BUDGET_DECREASED')
for role in ('fixed','design','initial'):
 if parent_req['input_sha256'][role]!=config['input_sha256'][role]:raise RuntimeError('INPUT_CHANGED:'+role)
q=np.asarray(last['quadric_coefficients'],dtype=np.float64)
if len(q)!=10 or not np.all(np.isfinite(q)) or not (abs(np.linalg.norm(q)-1.)<1e-9):
 raise RuntimeError('INVALID_CHECKPOINT_QUADRIC')
continuation=dict(parent=str(parent),parent_events_sha256=sha(parent_events_path),parent_summary_sha256=sha(parent_summary_path),parent_last_accepted_iteration=last.get('iteration'),parent_last_accepted_residual=last['normalized_equation_residual'],parent_last_accepted_quadric_hash=last.get('quadric_hash'),parent_solver_terminal=parent_summary['status'],parent_input_identity=parent_req['request_digest'],child_request_digest=req.request_digest,changed_budget_only=True,checkpoint_q=q.tolist(),resume_kind='NEW_NATIVE_SOLVE_FROM_VERIFIED_ACCEPTED_Q_NOT_UNBROKEN_RUN')
(o/'continuation.json').write_text(json.dumps(continuation,indent=2))
(o/'initial_q.json').write_text(json.dumps(q.tolist()))
def obs(stage,fn):
 tt=time.monotonic();log('BEGIN',stage)
 try:return fn()
 finally:log('END',stage,'sec',round(time.monotonic()-tt,2))
evaluator=InProcessCherchiEvaluator(req,tri,rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',stage_observer=obs)
events=[]
def sink(row):
 datum={k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in dict(row).items()};events.append(datum)
 record={k:datum.get(k) for k in ('type','reason','outcome','normalized_equation_residual','step','quadric_coefficients')};log('SOLVER_EVENT',str(record)[:650])
 with (o/'events.jsonl').open('a') as f:f.write(json.dumps(datum,default=str,allow_nan=False)+'\n');f.flush();os.fsync(f.fileno())
try:
 log('START_NATIVE_NEWTON','FROM_ACCEPTED_ITER',continuation['parent_last_accepted_iteration'],'RESIDUAL',continuation['parent_last_accepted_residual']);result=spin.solve_spin_it_faster_with_external_moment_evaluator(req,evaluator,initial_quadrics=(q,),event_sink=sink)
 want=('status','raw_equation_residual','normalized_equation_residual','physical_relative_residual','function_evaluations','quadric_coefficients','diagnostic','failure_reason')
 summary={k:result.get(k) for k in want}
 summary.update(elapsed_seconds=time.monotonic()-start,evaluator_counts=evaluator.call_counts,recorded_events=len(events),source='actual Cherchi backend through unmodified Faster Newton',full_paper_validation=False,not_claimed_model_delivery=True,complete_success=(result.get('status')=='CONVERGED'))
 (o/'solver-result.json').write_text(json.dumps(summary,indent=2,default=str,allow_nan=False));log('RESULT',summary)
except BaseException as exc:
 failure=dict(status='EXCEPTION',error=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),seconds=time.monotonic()-start)
 (o/'solver-error.json').write_text(json.dumps(failure,indent=2));log('FAIL',failure['error']);raise

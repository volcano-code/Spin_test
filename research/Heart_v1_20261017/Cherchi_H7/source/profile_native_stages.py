"""Run on the original native research host: genuine H6 Cherchi stage profiler.

No native library is bundled here. Requires SHA-verified archived V4 input,
existing H6 helper modules, and a matching installed Cherchi/native toolchain.
"""
import argparse,hashlib,json,resource,sys,time
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parents[1]
H6=HERE.parent/'Cherchi_H6'
sys.path.insert(0,str(H6/'source'))
from heart_h6_cherchi_jacobian import make_engine

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def measure(engine,q,repeats):
    result=[]
    for index in range(repeats):
        previous=dict(engine.stage_seconds)
        begin=time.perf_counter();cpu=time.process_time()
        material=engine(q)
        elapsed=time.perf_counter()-begin
        stages={name:round(value-previous.get(name,0.),8) for name,value in engine.stage_seconds.items()
                if value-previous.get(name,0.)>0}
        if sum(stages.values())>elapsed+0.05:raise ValueError('INVALID_STAGE_TIMING')
        if not str(material['boolean_backend_identity']).startswith('cherchi-reference-7bd6c2697695f555f9a15d7e154e084d841316f0:'):
            raise ValueError('NON_CHERCHI_BACKEND')
        result.append(dict(index=index,wall_seconds=elapsed,cpu_seconds=time.process_time()-cpu,
            stages_seconds=stages,unattributed_seconds=max(0,elapsed-sum(stages.values())),
            process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            backend=material['boolean_backend_identity'],
            geometry_hash=material['geometry_hash'],
            moments=list(map(float,material['raw_moments'])),
            jacobian=np.asarray(material['moment_jacobian'],dtype=float).tolist()))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--archived-v4',type=Path,required=True)
    p.add_argument('--registered-q',type=Path,default=H6/'input/registered-eval60-coefficients.json')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--backend',choices=('python','native','both'),default='python')
    p.add_argument('--repeats',type=int,default=3)
    args=p.parse_args()
    if not 1<=args.repeats<=30:raise ValueError('INVALID_REPEAT_COUNT')
    from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator
    baseline,q=make_engine(args.archived_v4,args.registered_q)
    engines={}
    if args.backend in ('python','both'):engines['python']=baseline
    if args.backend in ('native','both'):
        engines['native']=InProcessCherchiEvaluator(baseline.request,baseline.settings,
            branch_identity_policy='SOURCE_FEATURE_BRANCH_V2',
            normalization=baseline.normalization,
            rational_arithmetic_backend='NATIVE_GMP_SURFACE_V1',
            fixed_boundary_reuse=False,integral_profile='EXACT_GMP_V1')
    results={name:measure(engine,q,args.repeats) for name,engine in engines.items()}
    parity={}
    if len(results)==2:
        a,b=results['python'][0],results['native'][0]
        parity=dict(geometry_hash_equal=a['geometry_hash']==b['geometry_hash'],
            backend_equal=a['backend']==b['backend'],
            moment_max_abs_delta=float(np.max(np.abs(np.asarray(a['moments'])-np.asarray(b['moments'])))),
            jacobian_max_abs_delta=float(np.max(np.abs(np.asarray(a['jacobian'])-np.asarray(b['jacobian'])))))
        if not parity['geometry_hash_equal'] or not parity['backend_equal'] or parity['moment_max_abs_delta']>1e-8 or parity['jacobian_max_abs_delta']>1e-8:
            raise ValueError('A_B_GEOMETRY_OR_JACOBIAN_PARITY_FAILED')
    report=dict(schema='heart-h7-stage-profile-v1',
        scope='HISTORICAL_V4_PROXY_NOT_ORIGINAL_EVAL60',
        formal_heart_qualified=False,backend_selection=args.backend,
        native_core_sha256=digest(baseline.native.__file__),
        native_cherchi_sha256=digest(baseline.bridge.__file__),
        registered_input_sha256=digest(args.archived_v4),
        repetitions=args.repeats,
        timings=results,backend_parity=parity)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print('H7_PROFILE',json.dumps({'backend_selection':args.backend,'repetitions':args.repeats,'backend_parity':parity}))

if __name__=='__main__':main()

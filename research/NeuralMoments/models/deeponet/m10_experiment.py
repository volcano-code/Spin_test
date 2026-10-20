"""W5 M10: measured fair analytic-P0 training of positive-quadrature vs W6/W5.

NO W2 native J truth. W0 archived 81 real finite-point moments are excluded
because source point60 exhibits symbolic branch-change and no certified
smooth neighborhood / Newton terminal is available.

Run from an actual W5 branch checkout with read-only W6 files pinned by M9:
  python -m research.NeuralMoments.models.deeponet.m10_experiment \
    --w6-root /path/to/readonly_w6 --output /path/to/m10.json
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import platform
import resource
import statistics

import torch

from .m8_analytic_data import dataset, sha_dataset, independent_family_check, TEACHER
from .m8_fair_benchmark import (split_fit_validation, train as train_m8,
                                metrics as metrics_m8, real_parameters, latency)
from .m9_physical_benchmark import (create_model as m9_create_model,
                                    additional_physical_metrics,
                                    physically_guarded_decisions,
                                    query_budget_replay)
from .m9_readonly_w6 import load_m9_w6, W6_M6_SOURCE_COMMIT
from .m10_positive_quadrature import PositiveQuadratureMoment
from .m10_archive_gate import inspect_joint_historical_gate

NAMES=('w5_deeponet_voxel','w6_gauss_004',
       'w5_positive_quadrature_004','w5_positive_quadrature_012')
W0_REAL_H8F_M9_REPORT_GIT_BLOB='177fe9126d76d94236ecdca2d4750232f78f627a'


def make_model(name: str, seed: int, libraries):
    if name not in NAMES:
        raise ValueError('Unknown model, no hidden extra candidates')
    if not name.startswith('w5_positive'):
        return m9_create_model(name,seed,libraries)
    m4,m5,m6,guard=libraries
    torch.manual_seed(seed)
    eps=.04 if name.endswith('_004') else .12
    encoder=m6.GaussPotentialMoment(rule='gauss',points_per_axis=6,
                                     hidden=32,smoothing=.04,grid_size=8)
    return PositiveQuadratureMoment(encoder,smoothing=eps,certify_cube_sign=True)


def execute(*,w6_root: str|Path, seeds=(19,23,29), steps=100,
            per_family=20, repeats=3, names=NAMES,
            expected_m9_dir: str|Path|None=None,
            w0_report: str|Path|None=None, w2_manifest: str|Path|None=None) -> dict:
    if (not seeds or len(set(seeds))!=len(seeds) or
        type(steps) is not int or steps<1 or
        type(per_family) is not int or per_family<5 or
        type(repeats) is not int or repeats<1 or
        not names or len(set(names))!=len(names) or any(n not in NAMES for n in names)):
        raise ValueError('Invalid reproducible analytic benchmark protocol')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    libraries=load_m9_w6(w6_root)
    guard=libraries[3]
    if (w0_report is None) != (w2_manifest is None):
        raise ValueError('W0 and W2 archive paths must be supplied together')
    archive_gate=(inspect_joint_historical_gate(w0_report=w0_report,w2_manifest=w2_manifest)
                  if w0_report is not None else
                  {'checked':False,'certified_smooth_J_admitted_total':0,
                   'training_from_native_archived_labels':False})
    params={n:real_parameters(make_model(n,seeds[0],libraries)) for n in names}
    if max(params.values())/min(params.values())>1.05:
        raise ValueError('Models exceed +5 percent parameter parity')
    results=[]
    for seed in seeds:
        train_all=dataset(('box','sphere'),per_family=per_family,seed=seed)
        heldout=dataset(('ellipsoid',),per_family=per_family,seed=seed+1)
        fit,valid=split_fit_validation(train_all,seed,max(1,per_family//5))
        split=independent_family_check(fit,valid,heldout)
        training_sha=sha_dataset(train_all)
        heldout_sha=sha_dataset(heldout)
        if expected_m9_dir is not None:
            filepath=Path(expected_m9_dir)/f'm9_seed{seed}.json'
            source=json.loads(filepath.read_text(encoding='utf-8'))
            source_row=source['full_seed_experiments'][0]
            if (source_row['seed']!=seed or source_row['dataset_train_sha256']!=training_sha
                    or source_row['dataset_heldout_sha256']!=heldout_sha):
                raise ValueError('M9 and M10 teacher/input datasets are NOT identical')
        row={'seed':seed,'train_dataset_sha256':training_sha,
             'heldout_dataset_sha256':heldout_sha,'family_split':split,
             'models':{}}
        for name in names:
            model=make_model(name,seed,libraries)
            training=train_m8(model,fit,valid,seed=seed,steps=steps)
            metrics=metrics_m8(model,heldout)
            moment=additional_physical_metrics(model,heldout,guard)
            decision=physically_guarded_decisions(model,heldout,guard)
            timings=latency(model,heldout,repeats=repeats)
            actual_queries=query_budget_replay(model,heldout,repeats=repeats,
                                               budgets=(1,2,4,8))
            row['models'][name]={'training':training,'heldout':metrics,
                                 'moment_necessity':moment,'guarded_decision':decision,
                                 'cpu_latency':timings,'measured_query_costs':actual_queries}
        results.append(row)
    aggregate={}
    for name in names:
        rows=[r['models'][name] for r in results]
        metrics={
            'r_mae':lambda r:r['heldout']['r_mae'],
            'J_mae':lambda r:r['heldout']['J_mae'],
            'Jq_asymmetry':lambda r:r['heldout']['Jq_max_asymmetry'],
            'native_radial_Jc_c':lambda r:r['heldout']['native_radial_max'],
            'necessary_moment_pass_fraction':lambda r:r['moment_necessity']['necessary_support_pass_fraction'],
            'negative_mass_empty_fraction':lambda r:r['moment_necessity']['empty_cut_predicted_negative_mass_fraction'],
            'empty_predicted_mass_mean':lambda r:r['moment_necessity']['empty_cut_predicted_mass_mean'],
            'guarded_candidate_accept_fraction':lambda r:r['guarded_decision']['accepted_over_all_samples'],
            'cold_encode_plus_r_ms':lambda r:r['cpu_latency']['cold_r_ms'],
            'cached_J_ms':lambda r:r['cpu_latency']['warm_J_ms'],
            'fit_cpu_seconds':lambda r:r['training']['cpu_training_seconds'],
        }
        aggregate[name]={metric:{'mean':statistics.mean(fn(r) for r in rows),
                                 'sample_sd':statistics.stdev(fn(r) for r in rows) if len(rows)>1 else None,
                                 'per_seed':{str(seed):fn(r) for seed,r in zip(seeds,rows)}}
                         for metric,fn in metrics.items()}
        aggregate[name]['measured_8_queries_moment_J_ms']=statistics.mean(
            r['measured_query_costs']['8']['single_encode_q_moment_and_J_ms'] for r in rows)
    return {
        'schema':'W5_M10_POSITIVE_DISCRETE_MOMENT_CONE_ANALYTIC_V1',
        'source_branch':'research/neuralmoments-w5-deeponet-20261019',
        'reference_W6_readonly_commit':W6_M6_SOURCE_COMMIT,
        'W0_real_81point_report_git_blob':W0_REAL_H8F_M9_REPORT_GIT_BLOB,
        'archived_real_evidence_admission_gate':archive_gate,
        'W0_historical_real_archive_samples_reintegrated_by_W0':81,
        'W0_real_point60_symbolic_branch_change':True,
        'W0_original_H8f_workflow_conclusion':'failure',
        'W2_real_native_J_training_labels_admitted':0,
        'W5_new_native_cherchi_calls':0,
        'no_Cherchi_or_CAD_supervision_used':True,
        'labels':TEACHER,'dataset':'ANALYTIC_CONTINUUM_P0_NOT_8CUBED_VOXEL_BOOLEAN',
        'four_channel_input_parity':True,
        'true_cad_material_certification':False,
        'native_c_B_diagonal':[1]*7+[2]*3,
        'candidate_head_derivative':'CLOSED_FORM_DISCRETE_SURROGATE_NOT_NATIVE_CAD',
        'physical_support_box':[-1,1],
        'discrete_positive_measure_property':'PROVED_FOR_NONNEGATIVE_NODE_WEIGHTS_ONLY',
        'moment_cone_pass_does_not_certify_3d_material':True,
        'Jq_symmetry_required_for_this_discrete_head':False,
        'geometry_family_train':['box','sphere'],'geometry_family_holdout':['ellipsoid'],
        'seeds':list(seeds),'steps_upper_bound':steps,'per_family':per_family,
        'train_loss':'MSE(r)+0.5*MSE(Jc)','optimizer':'Adam lr=.003, batch=8, validation-only',
        'parameters_real':params,'max_min_parameter_ratio':max(params.values())/min(params.values()),
        'CPU_threads':torch.get_num_threads(),'device':'cpu','GPU_hours':0,
        'python':platform.python_version(),'torch':torch.__version__,
        'RSS_process_high_water_KiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        'models':list(names),'all_seed_records':results,'aggregate':aggregate}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--w6-root',required=True)
    ap.add_argument('--seeds',default='19,23,29')
    ap.add_argument('--steps',type=int,default=100)
    ap.add_argument('--per-family',type=int,default=20)
    ap.add_argument('--repeats',type=int,default=3)
    ap.add_argument('--expected-m9-dir')
    ap.add_argument('--w0-report')
    ap.add_argument('--w2-manifest')
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    report=execute(w6_root=args.w6_root,
                   seeds=tuple(int(x) for x in args.seeds.split(',')),
                   steps=args.steps,per_family=args.per_family,repeats=args.repeats,
                   expected_m9_dir=args.expected_m9_dir,
                   w0_report=args.w0_report,w2_manifest=args.w2_manifest)
    body=json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n'
    if args.output:args.output.write_text(body,encoding='utf8')
    print(json.dumps({'aggregate':report['aggregate'], 'seeds':report['seeds'],
                      'parameters_real':report['parameters_real']},indent=2))

if __name__=='__main__':main()

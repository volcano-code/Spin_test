"""W5 M11: true executed *analytic P0* training of cone-valued integrable heads.

Inputs: same 4-channel 8^3 density voxels and W0 signed c, r, Jc as M8–M10.
This does NOT access W2 original/archived native r/J labels or train Faster.
All comparisons use fresh dataset/geometry IDs, seeds, 100-step upper bound,
validation-only early stopping and an independent analytic post-step recheck.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics

import torch

from .m8_analytic_data import dataset, sha_dataset, independent_family_check, TEACHER
from .m8_fair_benchmark import (split_fit_validation, train as train_m8,
                                metrics as metrics_m8, real_parameters, latency)
from .m9_physical_benchmark import (additional_physical_metrics,
                                    physically_guarded_decisions,
                                    query_budget_replay)
from .m9_readonly_w6 import load_m9_w6, W6_M6_SOURCE_COMMIT
from .m10_experiment import make_model as m10_make_model
from .m11_cone_integrable import ConeIntegrableMoment

NAMES=('w5_deeponet_voxel','w5_positive_quadrature_012','w6_gauss_004',
       'w5_cone_integrable_025','w5_cone_integrable_075')
MIX={'w5_cone_integrable_025':.25,'w5_cone_integrable_075':.75}
TRAINING_ONLY_ANALYTIC=True


def create_model(name,seed,libraries):
    if name not in NAMES:
        raise ValueError('unknown candidate')
    if name not in MIX:
        return m10_make_model(name,seed,libraries)
    m4,m5,m6,guard=libraries
    torch.manual_seed(seed)
    encoder=m6.GaussPotentialMoment(rule='gauss',grid_size=8,points_per_axis=6,
                                    hidden=32,smoothing=.04)
    return ConeIntegrableMoment(encoder,mix=MIX[name])


def inspect_teacher_metadata(manifest, *, source_git_blob=None):
    """Fail closed for current published W2 v2, not an admission verifier.

    No runtime path from this function to a training dataset exists.
    Caller MUST source byte-pinned W2 record independently; dictionary-only
    fields are not evidence of an authorized teacher.
    """
    if not isinstance(manifest,dict) or manifest.get('schema')!='w2-cherchi-teacher-v2-pre-w0':
        raise ValueError('unknown W2 manifest schema')
    if (type(manifest.get('training_samples')) is not int or
        manifest['training_samples']!=0 or
        type(manifest.get('native_teacher_runs')) is not int or
        manifest['native_teacher_runs']!=0):
        raise ValueError('unknown W2 training/native state, do not auto-admit')
    history=manifest.get('m9_real_h8f_81_evidence')
    if not isinstance(history,dict) or (history.get('original_native_evaluations')!=81 or
            history.get('training_admitted')!=0 or
            history.get('certified_continuous_neighborhood') is not False or
            history.get('derivative_J_D_published') is not False or
            history.get('original_workflow_conclusion')!='failure' or
            history.get('point60',{}).get('added_LPI_features')!=2):
        raise ValueError('H8f native archive/point60 evidence changed')
    return {'source_kind':'H8F_81_ARCHIVED_EXCLUDED_METADATA_ONLY',
            'Git_blob_independently_verified_by_this_function':False,
            'source_git_blob_assertion_only':source_git_blob,
            'offline_native_moments_reverified_by_W0_W2':81,
            'real_native_derivative_training_admitted':0,
            'new_native_calls_by_W5':0,
            'archived_native_workflow':'failure',
            'point60_smooth_neighborhood_certified':False}


def run(*,w6_root,seed: int,steps: int=100,per_family: int=20,
        repeats: int=3,names=NAMES,reference_m10=None):
    if (type(seed) is not int or type(steps) is not int or steps<1 or
        type(per_family) is not int or per_family<5 or
        type(repeats) is not int or not 1<=repeats<=25 or
        not names or len(set(names))!=len(names) or any(n not in NAMES for n in names)):
        raise ValueError('invalid fixed experimental protocol')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    libs=load_m9_w6(w6_root)
    guard=libs[3]
    model_counts={n:real_parameters(create_model(n,seed,libs)) for n in names}
    if max(model_counts.values())/min(model_counts.values())>1.05:
        raise ValueError('parameter-budget parity >5%')
    alltrain=dataset(('box','sphere'),per_family=per_family,seed=seed)
    heldout=dataset(('ellipsoid',),per_family=per_family,seed=seed+1)
    fit,valid=split_fit_validation(alltrain,seed,max(1,per_family//5))
    splits=independent_family_check(fit,valid,heldout)
    train_sha=sha_dataset(alltrain);test_sha=sha_dataset(heldout)
    if reference_m10 is not None:
        previous=json.loads(Path(reference_m10).read_text(encoding='utf-8'))
        row=previous['all_seed_records'][0]
        if (row['seed']!=seed or row['train_dataset_sha256']!=train_sha or
            row['heldout_dataset_sha256']!=test_sha):
            raise ValueError('M11 dataset differs from pinned earlier control')
    results={}
    for name in names:
        model=create_model(name,seed,libs)
        trained=train_m8(model,fit,valid,seed=seed,steps=steps)
        observed=metrics_m8(model,heldout)
        support=additional_physical_metrics(model,heldout,guard)
        steps_audit=physically_guarded_decisions(model,heldout,guard)
        timing=latency(model,heldout,repeats=repeats)
        # Timed actual repeated queries, not additive estimates.
        queries=query_budget_replay(model,heldout,repeats=repeats,budgets=(1,8))
        z=model.encode_geometry(heldout[0])
        with torch.no_grad():
            J=model.jacobian(z,heldout[1])
            B=torch.as_tensor([1.]*7+[2.]*3,dtype=J.dtype,device=J.device)
            H=J/B[None,None,:]
            min_eig=float(torch.linalg.eigvalsh((H+H.transpose(-1,-2))*.5).amin())
            asym=float((H-H.transpose(-1,-2)).abs().amax())
        singular_count=0
        if name in MIX:
            singular_count=sum(s!='FIXED_ACTIVE_SET_SMOOTH_SURROGATE_ONLY'
                               for s in model.derivative_regime(z,heldout[1]))
        results[name]={'training':trained,'heldout':observed,
                       'necessary_support':support,'guarded_1D_decision':steps_audit,
                       'latency':timing,'measured_queries':queries,
                       'structural':{'Jq_min_symmetric_eigenvalue':min_eig,
                                     'Jq_max_asymmetry':asym,
                                     'nonsmooth_or_empty_evaluation_count':singular_count}}
    return {'schema':'W5_M11_POSITIVE_CONE_CONVEX_POTENTIAL_ANALYTIC_V1',
            'status':'ANALYTIC_ONLY_NO_REAL_W2_J_OR_NATIVE_SOLVER',
            'upstream_W6_source_commit':W6_M6_SOURCE_COMMIT,
            'original_W0_frozen_source':'0bcc187b3005478baa586a6d6f450e73811ca342',
            'W2_admissible_training_labels':0,'W5_new_native_cherchi_queries':0,
            'native_c_B_diagonal':[1]*7+[2]*3,
            'model_structure_scope':'CONVEX_HOMOGENEOUS_AND_MOMENT_CONE_ON_OPEN_NODAL_STRATA_ONLY',
            'global_native_Hessian_or_CAD_material_certified':False,
            'dataset_teacher_kind':TEACHER,'device':'cpu','gpu_hours':0.,
            'seed':seed,'seeds':[seed],'max_steps':steps,'per_family':per_family,
            'input_4channel_resolution':8,'train_per_seed_total_analytic_queries':len(alltrain[0]),
            'fit_analytic_queries':len(fit[0]),'val_analytic_queries':len(valid[0]),
            'heldout_analytic_queries':len(heldout[0]),
            'dataset_train_sha256':train_sha,'dataset_heldout_sha256':test_sha,
            'geometry_split':splits,'training_loss':'MSE(r)+0.5*MSE(Jc)',
            'optimizer':'Adam lr=.003 batch=8 validation-selected patience=5',
            'models':list(names),'real_parameter_counts':model_counts,
            'real_parameter_ratio':max(model_counts.values())/min(model_counts.values()),
            'torch_version':torch.__version__,'python':platform.python_version(),
            'results':results}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--w6-root',required=True)
    p.add_argument('--seed',type=int,required=True)
    p.add_argument('--steps',type=int,default=100)
    p.add_argument('--per-family',type=int,default=20)
    p.add_argument('--repeats',type=int,default=3)
    p.add_argument('--models',default=','.join(NAMES))
    p.add_argument('--reference-m10')
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    item=run(w6_root=args.w6_root,seed=args.seed,steps=args.steps,
             per_family=args.per_family,repeats=args.repeats,
             names=tuple(args.models.split(',')),reference_m10=args.reference_m10)
    args.output.write_text(json.dumps(item,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'seed':args.seed,'models':{k:{'r_mae':v['heldout']['r_mae'],
        'J_mae':v['heldout']['J_mae'],'accepted':v['guarded_1D_decision']['accepted_over_all_samples']}
        for k,v in item['results'].items()}},indent=2))


if __name__=='__main__':main()

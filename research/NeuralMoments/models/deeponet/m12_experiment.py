"""W5 M12: fresh-seed analytic saturation audit after matched P0 model training.

Train only on independent analytic box/sphere P0 c/r/J with the same M8
four-channel input budget. Hold out ellipsoids. M12 is a POST-PREDICTION
analytic-case certificate/bypass around one trained M11 model; it does NOT
add learned parameters or native Cherchi samples. Exact full moments cost
one independent analytic formula per heldout geometry (never 'free labels').
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import statistics
import time

import torch

from .m8_analytic_data import Shape, dataset, sha_dataset, independent_family_check
from .m8_fair_benchmark import (split_fit_validation, train as train_m8,
                                metrics as metrics_m8, real_parameters)
from .m9_physical_benchmark import physically_guarded_decisions
from .m9_readonly_w6 import load_m9_w6, W6_M6_SOURCE_COMMIT
from .m11_experiment import create_model as m11_create_model
from .m12_saturation import SaturationGuard, analytic_full_moments, strict_native_sign

TRAINED_NAMES=('w5_deeponet_voxel','w5_positive_quadrature_012',
               'w6_gauss_004','w5_cone_integrable_025')
ANALYTIC_MODE='ANALYTIC_P0_GROUND_TRUTH_ONLY_NOT_W2_REAL_MATERIAL'
B=(1.,)*7+(2.,)*3


def probes(dtype=torch.float32):
    """Four signed W0-native controls in strictly all-full/all-empty strata."""
    vectors=((1.,)+(0.,)*9,(-1.,)+(0.,)*9,
             (1.,.04,-.02,.05,.02,-.03,.01,.06,-.05,.03),
             (-1.,-.04,.02,-.05,-.02,.03,-.01,-.06,.05,-.03))
    out=[]
    for v in vectors:
        x=torch.tensor([v],dtype=dtype)
        out.append(x/x.norm(dim=-1,keepdim=True))
    return out


def _unique_shapes(heldout):
    byid={}
    for i,item in enumerate(heldout[4]):
        name=item['geometry_id']
        if name not in byid:
            spec=item['shape']
            shape=Shape(item['family'],tuple(spec['center']),tuple(spec['axes']),float(spec['density']))
            if shape.identity!=name:
                raise ValueError('HOLDOUT_GEOMETRY_IDENTITY_MISMATCH')
            byid[name]=(shape,heldout[0][i:i+1])
        elif not torch.equal(heldout[0][i:i+1],byid[name][1]):
            raise ValueError('DIFFERENT_VOXEL_BYTES_FOR_SAME_GEOMETRY_ID')
    return byid


def saturation_probe(model, heldout, *, guarded=False) -> dict:
    """Same 4 out-of-cut queries per heldout geometry. Guard requires new
    independently computed full analytic source formula, counted once per D.
    Direct model predicts without it; both see identical voxel and native c.
    """
    shapes=_unique_shapes(heldout)
    check= SaturationGuard(model) if guarded else None
    controls=probes()
    full_errors=[];empty_errors=[];full_J=[];empty_J=[]
    full=empty=undecided=0
    t0=time.perf_counter()
    for shape,D in shapes.values():
        cached=check.bind_analytic_geometry(D,shape) if guarded else None
        if not guarded:
            with torch.no_grad(): z=model.encode_geometry(D).detach()
        truth_full=torch.as_tensor(analytic_full_moments(shape),dtype=D.dtype)
        for c in controls:
            state=strict_native_sign(c[0],shape)
            if state=='UNDECIDED':
                undecided+=1
                raise AssertionError('PREDECLARED_SATURATION_PROBE_UNDECIDED')
            if guarded:
                output=check.predict(cached,c)
                if output['region']!=state or output['Jc'] is None:
                    raise AssertionError('GUARDED_ANALYTIC_SATURATION_INCONSISTENT')
                r,J=output['r'],output['Jc']
            else:
                with torch.no_grad():
                    r=model.moment(z,c)
                    J=model.jacobian(z,c)
            if not (torch.isfinite(r).all() and torch.isfinite(J).all()):
                raise ValueError('NONFINITE_MODEL_OR_ANALYTIC_OUTPUT')
            if state=='ANALYTIC_CERTIFIED_FULL':
                full+=1; full_errors.append(float((r[0]-truth_full).abs().mean()))
                full_J.append(float(J.abs().amax()))
            else:
                empty+=1;empty_errors.append(float(r.abs().mean()))
                empty_J.append(float(J.abs().amax()))
    elapsed=time.perf_counter()-t0
    return {
       'independent_analytic_geometry_count':len(shapes),
       'out_of_cut_queries':4*len(shapes),
       'full_queries':full,'empty_queries':empty,'undecided_queries':undecided,
       'full_raw_r_mae':statistics.mean(full_errors),
       'empty_raw_r_mae':statistics.mean(empty_errors),
       'max_full_abs_Jc':max(full_J),'max_empty_abs_Jc':max(empty_J),
       'measured_wall_ms_including_analytic_source_binding':1000*elapsed,
       'analytic_full_reference_evaluations':check.analytic_full_reference_calls if guarded else len(shapes),
       'new_native_cherchi_calls':check.native_teacher_calls if guarded else 0,
       'one_geometry_encoding_per_geometry':not guarded or check.encoding_calls==len(shapes),
       'source_restriction':'EXACT_ANALYTIC_SHAPE_AND_VOXEL_BINDING_ONLY',
       'real_CAD_derivative_certified':False,
    }


def interior_no_regression(model,heldout)->dict:
    """M12 guard MUST leave training task's interior predictor unchanged."""
    check=SaturationGuard(model)
    shapes=_unique_shapes(heldout)
    caches={k:check.bind_analytic_geometry(*reversed(item)) for k,item in shapes.items()}
    # reversed((shape,D)) yields (D,shape), with explicit identity binding.
    difference=[];jac_difference=[];j_withheld=0;noninterior=0
    with torch.no_grad():
        for D,c,meta in zip(heldout[0],heldout[1],heldout[4]):
            cache=caches[meta['geometry_id']]
            out=check.predict(cache,c.unsqueeze(0))
            if out['region']!='UNDECIDED':noninterior+=1
            r0=model.moment(cache.z,c.unsqueeze(0))
            difference.append(float((out['r']-r0).abs().max()))
            if out['Jc'] is None:j_withheld+=1
            else:
                J0=model.jacobian(cache.z,c.unsqueeze(0))
                jac_difference.append(float((out['Jc']-J0).abs().max()))
    return {'queries':len(heldout[4]),'max_r_difference':max(difference),
            'max_J_difference_where_defined':max(jac_difference) if jac_difference else None,
            'nodal_derivative_withheld':j_withheld,'already_full_or_empty':noninterior,
            'all_analytic_geometry_source_checks':len(shapes),'native_label_uses':0}


def run(*,w6_root:str|Path,seed:int,steps=100,per_family=20,
        names=TRAINED_NAMES) -> dict:
    if (type(seed) is not int or type(steps) is not int or steps<1 or
        type(per_family) is not int or per_family<5 or not names or
        len(set(names))!=len(names) or any(n not in TRAINED_NAMES for n in names) or
        'w5_cone_integrable_025' not in names):
        raise ValueError('INVALID_M12_ANALYTIC_PROTOCOL')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    lib=load_m9_w6(w6_root)
    trainall=dataset(('box','sphere'),per_family=per_family,seed=seed)
    heldout=dataset(('ellipsoid',),per_family=per_family,seed=seed+1)
    fit,valid=split_fit_validation(trainall,seed,max(1,per_family//5))
    split=independent_family_check(fit,valid,heldout)
    params={n:real_parameters(m11_create_model(n,seed,lib)) for n in names}
    if max(params.values())/min(params.values())>1.05:
        raise ValueError('TRAINABLE_PARAMETERS_EXCEED_FIVE_PERCENT_SPREAD')
    record={}
    for name in names:
        model=m11_create_model(name,seed,lib)
        training=train_m8(model,fit,valid,seed=seed,steps=steps)
        interior=metrics_m8(model,heldout)
        decision=physically_guarded_decisions(model,heldout,lib[3])
        ext=saturation_probe(model,heldout,guarded=False)
        item={'fit':training,'interior':interior,
              'guarded_one_dimensional_decision':decision,
              'strict_saturation_without_independent_full_moment':ext}
        if name=='w5_cone_integrable_025':
            item['M12_strict_saturation_with_independent_analytic_full_moment']=saturation_probe(model,heldout,guarded=True)
            item['interior_preservation']=interior_no_regression(model,heldout)
        record[name]=item
    return {'schema':'W5_M12_ANALYTIC_STRICT_SATURATION_V1',
            'seed':seed,'models':list(names),'parameter_counts':params,
            'train_sha256':sha_dataset(trainall),'heldout_sha256':sha_dataset(heldout),
            'geometry_family_split':split,'fit_samples':len(fit[0]),
            'validation_samples':len(valid[0]),'heldout_samples':len(heldout[0]),
            'max_optimizer_steps':steps,'optimizer':'ADAM_0.003_MSE_R_PLUS_HALF_MSE_J',
            'source_W6_commit':W6_M6_SOURCE_COMMIT,
            'teacher_kind':ANALYTIC_MODE,'real_w2_training_labels':0,
            'native_cherchi_calls':0,'native_real_CAD_certification':False,
            'normalization':'W0_SIGNED_NATIVE_C_AND_UNDOUBLED_RAW_R',
            'gpu_hours':0.,'compute_device':'cpu',
            'torch_version':torch.__version__,'python_version':platform.python_version(),
            'M12_distinction':'SAME_TRAINED_M11_WEIGHTS_WITH_POSTHOC_ANALYTIC_SATURATION_NOT_FIFTH_INDEPENDENT_MODEL',
            'results':record}


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--w6-root',required=True)
    ap.add_argument('--seed',type=int,required=True)
    ap.add_argument('--steps',type=int,default=100)
    ap.add_argument('--per-family',type=int,default=20)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    result=run(w6_root=args.w6_root,seed=args.seed,steps=args.steps,per_family=args.per_family)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'seed':args.seed,'strict_analytic_bypass':result['results']['w5_cone_integrable_025']['M12_strict_saturation_with_independent_analytic_full_moment'],'models':{k:v['interior']['r_mae'] for k,v in result['results'].items()}},indent=2))

if __name__=='__main__':main()

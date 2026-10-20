"""Reproducible independent analytic full-cube 0/1/2-query adapter smoke.

Randomly initialized M7, intentionally NOT a trained/Cherchi claim. Compare
independent heldout analytic plane cuts after giving 0/1/2 analytic supports;
never use the holdout labels to fit the bounded atom weights.
"""
from __future__ import annotations
import argparse
import json
import time

import numpy as np
import torch

from .analytic_cut import GeometrySpec,vertical_cut_truth
from .m7_realizable import RealizableUFNOMoment
from .m8_bounded_adapter import BoundedAtomAdapter
from .m6_moment_guard import physical_moment_diagnostic


def run():
    torch.set_num_threads(1)
    torch.manual_seed(19)
    model=RealizableUFNOMoment(points_per_axis=6,temperature=.12).eval()
    D=torch.zeros(1,4,8,8,8)
    D[:,0]=1
    D[:,1]=1
    spec=GeometrySpec('box',(0.,0.,0.),(1.,1.,1.))
    support=[vertical_cut_truth(spec,h) for h in (-.4,.22)]
    heldout=[vertical_cut_truth(spec,h) for h in (-.3,-.15,.1,.32,.46)]
    c_support=torch.from_numpy(np.stack([x[0] for x in support])).float()[None]
    r_support=torch.from_numpy(np.stack([x[1] for x in support])).float()[None]
    c_test=torch.from_numpy(np.stack([x[0] for x in heldout])).float()
    r_test=torch.from_numpy(np.stack([x[1] for x in heldout])).float()
    with torch.no_grad():
        start=time.perf_counter()
        z=model.encode_geometry(D).detach()
        encoding_ms=(time.perf_counter()-start)*1000
    result={'schema':'W6_M8_BOX_ANALYTIC_P0_SMOKE','status':'UNTRAINED_ANALYTIC_ONLY',
            'seed':19,'teacher':'closed-form full cube vertical cut, not W2',
            'support_h':[-.4,.22],'heldout_h':[-.3,-.15,.1,.32,.46],
            'encoding_once_ms':encoding_ms,'parameters_real':sum(p.numel()*(2 if p.is_complex() else 1) for p in model.parameters()),
            'native_Cherchi_calls':0,'training_steps':0,'queries':{}}
    for k in (0,1,2):
        with torch.no_grad():
            start=time.perf_counter()
            a=BoundedAtomAdapter(model,D,z,c_support[:,:k],r_support[:,:k],
                                 source='ANALYTIC_P0',ridge=1e-4)
            fit_ms=(time.perf_counter()-start)*1000
            preds=torch.cat([a.predict(x.unsqueeze(0)) for x in c_test])
            feasible=physical_moment_diagnostic(preds,tol=1e-6)
        result['queries'][str(k)]={'oracle_queries_used':k,
                'heldout_r_mae':float((preds-r_test).abs().mean()),
                'necessary_conditions_pass':bool(feasible['necessary_conditions_pass'].all()),
                'support_loss_before':a.audit.support_loss_before,
                'support_loss_after':a.audit.support_loss_after,
                'support_capacity_exceeded':a.audit.support_mass_exceeds_sampled_capacity,
                'fit_ms':fit_ms}
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True)
    args=p.parse_args()
    result=run()
    with open(args.output,'w',encoding='utf8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()

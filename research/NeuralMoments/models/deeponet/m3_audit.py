"""CPU-only W5 M3 geometry-input and W0 analytic P0 decision audit.

No W2 teacher execution, no neural training, no arbitrary-CAD correctness claim.
Measure cached inference/Jacobian cost, not Cherchi-vs-neural speedup.
"""
from __future__ import annotations

import argparse
import json
import platform
import statistics
import time

import numpy as np
import torch

from .mesh_features import cached_mesh_geometry, mesh_features
from .native_p0 import cap_moments, cap_jacobian_native, gauss_newton_decision, native_vertical_c
from .model import DeepONetMoment
from research.NeuralMoments.models.geometry_mlp.model import GeometryMLPMoment


def _demo_mesh():
    vertices=np.array([[-1.,-1.,-1.],[1.,-1.,-1.],[1.,1.,-1.],[-1.,1.,-1.],
                       [-1.,-1.,1.],[1.,-1.,1.],[1.,1.,1.],[-1.,1.,1.]])
    faces=np.array([(0,2,1),(0,3,2),(4,5,6),(4,6,7),
        (0,1,5),(0,5,4),(1,2,6),(1,6,5),(2,3,7),(2,7,6),(3,0,4),(3,4,7)])
    return vertices,faces


def _bench(action, *, repeats):
    durations=[]
    for _ in range(repeats):
        t=time.perf_counter_ns()
        action()
        durations.append((time.perf_counter_ns()-t)/1e6)
    return statistics.median(durations)


def run(seed: int = 101, repeats: int = 21) -> dict:
    if seed < 0 or repeats < 1:
        raise ValueError('nonnegative seed and positive repeats required')
    torch.set_num_threads(1)
    vertices,faces=_demo_mesh()
    geometry=mesh_features(vertices,faces)
    c_native=torch.tensor(native_vertical_c(.25),dtype=torch.float64)
    reference=gauss_newton_decision(1.2,.10,.03)
    perturbed=gauss_newton_decision(1.2,.10,.03,
        predicted_r=cap_moments(1.2,.10)+np.array([.01]+[0.]*9),
        predicted_jc=cap_jacobian_native(1.2,.10)*1.03)
    result={}
    for name,model_type in [('deeponet',DeepONetMoment),('geometry_mlp',GeometryMLPMoment)]:
        torch.manual_seed(seed)
        model=model_type(geometry_dim=24).double().eval()
        with torch.no_grad():
            z=cached_mesh_geometry(model,geometry,dtype=torch.float64)
            probe=model.moment(z,c_native).detach().numpy()
        j_probe=model.jacobian(z,c_native).detach().numpy()
        if probe.shape != (10,) or j_probe.shape != (10,10) or not (np.isfinite(probe).all() and np.isfinite(j_probe).all()):
            raise ValueError('nonfinite model interface probe')
        with torch.no_grad():
            cold=_bench(lambda:model.moment(cached_mesh_geometry(model,geometry,dtype=torch.float64),c_native),repeats=repeats)
            warm=_bench(lambda:model.moment(z,c_native),repeats=repeats)
        jac=_bench(lambda:model.jacobian(z,c_native),repeats=repeats)
        result[name]={
            'trainable_parameters':model.complexity()['parameters'],
            'estimated_linear_macs':model.complexity(),
            'cold_ms_cpu_median':cold,'warm_ms_cpu_median':warm,'jacrev_10x10_ms_cpu_median':jac,
            'finite_output_and_jacobian_shapes_verified':True,
        }
    return {
        'schema':'W5-M3-mesh-and-native-P0-smoke-v1',
        'status':'ANALYTIC_P0_AND_MESH_INPUT_ONLY_REAL_W2_TRAINING_BLOCKED',
        'mesh_kind':'triangular closed cube (no self-intersection or CAD Boolean certificate)',
        'source_sha256':geometry.source_sha256,
        'mesh_feature_dimension':len(geometry.geometry),
        'mesh_raw_mass':float(geometry.original_moments[0]),
        'W0_native_control_order':'CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY',
        'W0_monomial_B':[1]*7+[2]*3,
        'analytic_oracle':'continuous perfect sphere cap; isolated from triangulated cube network inputs',
        'P0_decision_reference':reference,
        'P0_decision_controlled_perturbation':perturbed,
        'non_comparable_inputs':True,
        'no_real_teacher_or_accuracy_or_speedup_claim':True,
        'train_steps':0,'gpu_seconds':0.,'cpu_threads':1,
        'seed':seed,'repeats':repeats,'torch_version':torch.__version__,
        'python_version':platform.python_version(),
        'models_untrained_interface_probes':result,
        'remaining_dependencies':['W0 full verified native material/coordinate exchange','W2 independently sealed real Cherchi r_D and Jacobian with held-out geometry families'],
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--seed',type=int,default=101)
    parser.add_argument('--repeats',type=int,default=21)
    args=parser.parse_args()
    print(json.dumps(run(args.seed,args.repeats),indent=2,sort_keys=True,allow_nan=False))


if __name__ == '__main__':
    main()

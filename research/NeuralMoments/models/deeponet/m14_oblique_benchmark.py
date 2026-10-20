"""M14 source-bound tilted-plane cell-volume study (analytic P0 ONLY).

Run: python -m research.NeuralMoments.models.deeponet.m14_oblique_benchmark
 --seeds 79,83,89 --per-family 2 --resolutions 8,16,24 --output path.json

We evaluate the declared piecewise-constant cell D from the same center
samples at each resolution. Independently integrated smooth ellipsoid oracles
are used ONLY for audit and numerical-bound demonstrations. No W2 real labels,
trainable model optimization, CAD proof or Cherchi native evaluation occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import statistics
import time

import numpy as np

from .m8_analytic_data import Shape
from .m13_resolution_benchmark import center_cell_voxel, w6_gauss_maximum_atomic_moments
from .m14_oblique_cell_integrals import ObliqueCellReference, plane_native_c, B
from .m14_oblique_analytic import ellipsoid_plane_oracle
from .m14_error_bounds import analytic_ellipsoid_uncertainty


def _sha_object(x)->str:
    return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def run(*,seeds=(79,83,89),per_family=2,queries=2,resolutions=(8,16,24)):
    if not seeds or len(set(seeds))!=len(seeds) or per_family<1 or queries<1 or not resolutions or any(type(n)is not int or n<4 for n in resolutions):
        raise ValueError('INVALID_BENCHMARK_PROTOCOL')
    rows=[];identity=[];cache_count=0
    for seed in seeds:
        rng=np.random.default_rng(seed)
        for family in ('sphere','ellipsoid'):
            for index in range(per_family):
                center=tuple(float(x) for x in rng.uniform(-.08,.08,3))
                if family=='sphere':
                    rad=float(rng.uniform(.54,.73));axes=(rad,)*3
                else:
                    axes=tuple(float(x) for x in rng.uniform(.48,.74,3))
                    if max(axes)-min(axes)<.05:
                        axes=(axes[0],axes[1]*.85,axes[2]*1.05)
                rho=float(rng.uniform(.85,1.25))
                shape=Shape(family,center,axes,rho)
                identity.append({'seed':seed,'geometry_id':shape.identity,'family':family})
                geometries={}
                for n in resolutions:
                    t0=time.perf_counter_ns()
                    data=center_cell_voxel(shape,n)
                    source=ObliqueCellReference.bind(data)
                    cache_ms=(time.perf_counter_ns()-t0)*1e-6
                    source.assert_same_voxel_source(data)
                    geometries[n]=(source,data,cache_ms)
                    cache_count+=1
                for qindex in range(queries):
                    normal=rng.uniform(-1.,1.,3)
                    # Ensure the plane is genuinely non-axis-aligned.
                    normal+=np.array([.23,-.39,.67])
                    normal/=np.linalg.norm(normal)
                    plane_offset=float(normal@np.asarray(center)+
                                       rng.uniform(-.4,.4)*np.linalg.norm(normal*np.asarray(axes)))
                    c=plane_native_c(normal,plane_offset)
                    truth=ellipsoid_plane_oracle(shape.center,shape.axes,shape.density,c)
                    if truth['status']!='SMOOTH_ELLIPSOID_PLANE':
                        raise RuntimeError('invalid independent smooth sample')
                    for n,(source,D,encode_ms) in geometries.items():
                        t0=time.perf_counter_ns()
                        estimated=source.evaluate(c)
                        query_ms=(time.perf_counter_ns()-t0)*1e-6
                        if estimated['Jc'] is None:
                            raise RuntimeError('grid contact: never interpolate a missing derivative')
                        limit=analytic_ellipsoid_uncertainty(shape.center,shape.axes,shape.density,n,c)
                        max_r=float(np.max(np.abs(estimated['r']-truth['r'])))
                        max_j=float(np.max(np.abs(estimated['Jc']-truth['Jc'])))
                        if max_r>limit['raw_ten_moment_max_abs_error_upper_bound']+1e-11 or max_j>limit['native_Jc_max_abs_error_upper_bound']+1e-11:
                            raise RuntimeError('INDEPENDENT_ANALYTIC_ERROR_EXCEEDS_CONSERVATIVE_BOUND')
                        w6_r=w6_gauss_maximum_atomic_moments(D,c)
                        H=estimated['Jc']/B[None,:]
                        rows.append({
                            'seed':seed,'family':family,'geometry_id':shape.identity,
                            'query_index':qindex,'resolution':n,
                            'source_sha256':source.source_sha256,
                            'plane_native_c':[float(z) for z in c],
                            'r_mae':float(np.mean(np.abs(estimated['r']-truth['r']))),
                            'Jc_mae':float(np.mean(np.abs(estimated['Jc']-truth['Jc']))),
                            'r_max_error':max_r,'Jc_max_error':max_j,
                            'Jq_asymmetry_max':float(np.max(np.abs(H-H.T))),
                            'Jc_radial_null_l2':float(np.linalg.norm(estimated['Jc']@c)),
                            'min_Jq_eigenvalue':float(np.linalg.eigvalsh((H+H.T)/2).min()),
                            'r_conservative_source_error_bound':limit['raw_ten_moment_max_abs_error_upper_bound'],
                            'J_conservative_source_error_bound':limit['native_Jc_max_abs_error_upper_bound'],
                            'ambiguous_source_cells':limit['ambiguous_boundary_cell_count'],
                            'w6_M7_untrained_max_capacity_hard_r_mae':float(np.abs(w6_r-truth['r']).mean()),
                            'w6_M7_comparison_has_no_J':True,
                            'geometry_binding_ms':encode_ms,
                            'cell_r_J_query_ms':query_ms,
                            'cut_cells':estimated['cut_cells'],
                            'source_error_bound_holds':True,
                            'native_teacher_runs':0,
                        })
    aggregate={}
    for n in resolutions:
        selected=[x for x in rows if x['resolution']==n]
        aggregate[str(n)]={}
        for key in ('r_mae','Jc_mae','w6_M7_untrained_max_capacity_hard_r_mae',
                    'cell_r_J_query_ms','geometry_binding_ms','r_conservative_source_error_bound',
                    'J_conservative_source_error_bound','ambiguous_source_cells'):
            values=[x[key] for x in selected]
            aggregate[str(n)][key]={'mean':float(statistics.mean(values)),
                                   'sample_sd':float(statistics.stdev(values)) if len(values)>1 else None,
                                   'count':len(values)}
        aggregate[str(n)]['actual_errors_within_declared_source_bounds']=True
    return {
        'schema':'W5_M14_OBLIQUE_PIECEWISE_VOXEL_CELLS_V1',
        'status':'INDEPENDENT_ANALYTIC_P0_CELL_REFERENCE_ONLY_NO_NATIVE_CHERCHI',
        'seeds':list(seeds),'per_family':per_family,'queries_per_geometry':queries,
        'resolutions':list(resolutions),'geometry_dataset_identity_sha256':_sha_object(identity),
        'independent_shapes':len({x['geometry_id'] for x in identity}),
        'evaluations':len(rows),'cache_builds':cache_count,
        'native_teacher_calls':0,'W2_admitted_J_training_labels':0,
        'trainable_models_trained_this_milestone':0,
        'native_coefficient_order':'CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY',
        'B_diag':[1.]*7+[2.]*3,
        'source_geometry_semantics':'CELL_CENTERED_PIECEWISE_CONSTANT_D_NOT_ORIGINAL_CAD',
        'exact_derivative_scope':'LOCAL_AMBIENT_10X10_AT_NONCONTACT_PLANE_BETA_A_PLUS_B_DOT_X',
        'general_nonplanar_native_quadric_evaluator':False,
        'w6_reference_kind':'UNTRAINED_M7_GAUSS_MAXIMUM_ATOMIC_CAPACITY_HARD_CUT_J_UNAVAILABLE',
        'continuous_truth_kind':'INDEPENDENT_ELLIPSOID_PLANE_CLOSED_FORM_AND_DISK_QUADRATURE',
        'bound_scope':'SOURCE_PRIVILEGED_FLOAT64_INTERVAL_MARGIN_NOT_FORMAL_CAD_CERTIFICATION',
        'python':platform.python_version(),'numpy':np.__version__,
        'rows':rows,'aggregate':aggregate,
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seeds',default='79,83,89')
    p.add_argument('--per-family',type=int,default=2)
    p.add_argument('--queries',type=int,default=2)
    p.add_argument('--resolutions',default='8,16,24')
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    report=run(seeds=tuple(map(int,a.seeds.split(','))),per_family=a.per_family,
               queries=a.queries,resolutions=tuple(map(int,a.resolutions.split(','))))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'evaluations':report['evaluations'],'independent_shapes':report['independent_shapes'],
                      'cache_builds':report['cache_builds'],'aggregate':report['aggregate']},
                     indent=2,sort_keys=True))

if __name__=='__main__':main()

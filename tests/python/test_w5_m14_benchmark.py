"""M14 oblique-resolution provenance and error-bound integration tests."""
import copy
import numpy as np
import pytest

from research.NeuralMoments.models.deeponet.m14_oblique_benchmark import run
from research.NeuralMoments.models.deeponet.m14_error_bounds import analytic_ellipsoid_uncertainty
from research.NeuralMoments.models.deeponet.m14_oblique_cell_integrals import plane_native_c


def test_small_oblique_benchmark_is_real_reproducible_and_source_bounded():
    a=run(seeds=(13,),per_family=1,queries=1,resolutions=(4,8))
    b=run(seeds=(13,),per_family=1,queries=1,resolutions=(4,8))
    assert a['schema']=='W5_M14_OBLIQUE_PIECEWISE_VOXEL_CELLS_V1'
    assert a['native_teacher_calls']==0
    assert a['W2_admitted_J_training_labels']==0
    assert a['trainable_models_trained_this_milestone']==0
    assert a['independent_shapes']==2
    assert a['evaluations']==4
    assert a['cache_builds']==4
    assert a['geometry_dataset_identity_sha256']==b['geometry_dataset_identity_sha256']
    for x in a['rows']:
        assert x['source_error_bound_holds']
        assert x['r_max_error']<x['r_conservative_source_error_bound']
        assert x['Jc_max_error']<x['J_conservative_source_error_bound']
        assert abs(x['Jq_asymmetry_max'])<1e-11
        assert x['min_Jq_eigenvalue']>-1e-9
        assert x['w6_M7_comparison_has_no_J']


@pytest.mark.parametrize('mode',('wrong_axes','bad_density','bad_c','bad_resolution','out_of_box'))
def test_analytic_source_bound_rejects_invalid_inputs(mode):
    c=plane_native_c([.23,-.2,.93],.19311)
    center=[0.,0.,0.];axes=[.65,.61,.7];density=1.;n=8
    if mode=='wrong_axes':axes[1]=-2.
    if mode=='bad_density':density=0.
    if mode=='bad_c':c=c.copy();c[5]=1e-4
    if mode=='bad_resolution':n=3
    if mode=='out_of_box':center[2]=.5
    with pytest.raises(ValueError):
        analytic_ellipsoid_uncertainty(center,axes,density,n,c)


def test_known_analytic_source_cannot_certify_native_CAD():
    row=run(seeds=(17,),per_family=1,queries=1,resolutions=(4,))
    assert not row['general_nonplanar_native_quadric_evaluator']
    assert row['bound_scope'].endswith('NOT_FORMAL_CAD_CERTIFICATION')
    assert row['native_teacher_calls']==0
    assert 'UNTRAINED' in row['w6_reference_kind']

"""Independent complex-step KKT arithmetic, including native cross coefficient B."""
import numpy as np
import pytest

from .native_teacher_replay import ReplayRejected
from .original_stationarity_m7 import recompute_original_kkt

NATIVE = np.array([0.1,0.,0.,0.1,0.,0.,0.,0.1,0.1,0.1])
NATIVE /= np.linalg.norm(NATIVE)
B=np.array([1.]*7+[2.]*3)
DUAL=B*NATIVE/np.linalg.norm(B*NATIVE)


def physics(v):
    # Synthetic *independent* quadratic objective; constraints exactly zero
    # at zero moment, so gradient is explicitly -mu*B*c/||B*c||.
    assert len(v)==10
    return -np.dot(DUAL,v), np.asarray((v[1],v[2]),dtype=v.dtype)


def run(**overrides):
    k=dict(total_r=[0.]*10,native_c=NATIVE.tolist(),multipliers=[0.,0.],
           mu=1.,objective=physics,equation_tolerance=1e-12,
           mode='SPINNING_TOP',original_objective_profile='SPIN2014_OBJECTIVES_QUADRIC_V1')
    k.update(overrides)
    return recompute_original_kkt(**k)


def test_exact_synthetic_stationarity_requires_double_cross_terms():
    r=run()
    assert r['equation_norm'] < 1e-15
    assert r['mathematical_KKT_recomputation_passed']
    assert not r['training_admissible']
    assert np.max(np.abs(r['objective_gradient']+DUAL))<1e-15


def test_without_B_cross_factor_fails_original_stationarity():
    wrong=NATIVE.copy()
    wrong[7:]=0
    wrong/=np.linalg.norm(wrong)
    with pytest.raises(ReplayRejected,match='KKT_RESIDUAL_EXCEEDS'):
        run(native_c=wrong.tolist())


@pytest.mark.parametrize('kwargs,needle',[
    ({'mu':0},'NONPOSITIVE_MU'),
    ({'mu':True},'NON_NUMERIC_OR_BOOL'),
    ({'equation_tolerance':1e-2},'RELAXED_TOLERANCE'),
    ({'equation_tolerance':0},'RELAXED_TOLERANCE'),
    ({'total_r':[0]*9},'TEN_VALUES_REQUIRED'),
    ({'native_c':[0.]*10},'NONUNIT_NATIVE'),
    ({'multipliers':[0.]},'DIMENSION'),
    ({'multipliers':[float('nan'),0]},'NONFINITE'),
    ({'mode':'STATIC_BALANCE'},'UNSUPPORTED_ORIGINAL_ROTATIONAL_OBJECTIVE'),
    ({'original_objective_profile':'LEGACY_V1'},'UNSUPPORTED_ORIGINAL_ROTATIONAL_OBJECTIVE'),
    ({'objective':None},'INDEPENDENT_ORIGINAL_OBJECTIVE_REQUIRED'),
])
def test_bad_constraints_and_settings_rejected(kwargs,needle):
    with pytest.raises(ReplayRejected,match=needle):run(**kwargs)


def test_explicit_nonzero_constraints_rejected():
    with pytest.raises(ReplayRejected,match='KKT_RESIDUAL_EXCEEDS'):
        run(total_r=[0.,1.,0.]+[0.]*7)


def test_reject_wrong_objective_even_at_matching_geometry():
    def bad(v):
        return 0.,np.zeros(2,dtype=v.dtype)
    with pytest.raises(ReplayRejected,match='KKT_RESIDUAL_EXCEEDS'):
        run(objective=bad)


def test_reject_drifting_complex_constraint_dimensions():
    def bad(v):
        return np.sum(v),np.zeros(2 if not np.iscomplexobj(v) else 3,dtype=v.dtype)
    with pytest.raises(ReplayRejected,match='INDEPENDENT_COMPLEX_STEP_FAILED'):
        run(objective=bad)


def test_reject_nonfinite_complex_derivative():
    def bad(v):
        return (np.nan * 1j) if np.iscomplexobj(v) else 1.,np.zeros(2,dtype=v.dtype)
    with pytest.raises(ReplayRejected,match='INDEPENDENT_COMPLEX_STEP_NONFINITE'):
        run(objective=bad)

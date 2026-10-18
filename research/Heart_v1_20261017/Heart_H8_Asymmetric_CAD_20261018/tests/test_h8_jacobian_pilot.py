"""Pure regression for H8e finite differences, not a native result."""
import sys
from pathlib import Path
import numpy as np
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
from probe_h8_jacobian import parse_columns,finite_checks,ten_by_ten_shape_check
from heart_h6_cherchi_jacobian import planned_samples

def test_column_contract():
    assert parse_columns('0,4,8')==[0,4,8]
    for bad in ('','0,0','10','-1','hello'):
        with pytest.raises(ValueError,match='INVALID_JACOBIAN_PILOT_COLUMNS'):parse_columns(bad)

def test_full_jacobian_must_be_real_finite_10x10():
    np.testing.assert_array_equal(ten_by_ten_shape_check(np.eye(10)),np.eye(10))
    for bad in (np.ones((9,10)),np.full((10,10),float('nan'))):
        with pytest.raises(ValueError,match='10_X_10'):ten_by_ten_shape_check(bad)

def test_fd_exact_quadratic_moment_function():
    q=np.r_[1.,np.zeros(9)]
    samples,layouts=planned_samples(q,[0])
    points=[]
    for sample in samples:
        x=sample[0]
        moments=np.asarray([x*x + (i+1)*x for i in range(10)])
        points.append(dict(independent_variable_raw_moments=moments.tolist(),feature_branch_hash='same'))
    jac=np.zeros((10,10));jac[:,0]=[3+i for i in range(10)]
    result=finite_checks(points,layouts,jac,'same')
    assert len(result)==3 and all(v['numerical_passed'] and v['feature_hash_stable'] for v in result)

def test_branch_hash_drift_never_admits_smoothness():
    q=np.r_[1.,np.zeros(9)]
    samples,layouts=planned_samples(q,[0])
    points=[dict(independent_variable_raw_moments=np.zeros(10).tolist(),feature_branch_hash='same') for s in samples]
    points[1]['feature_branch_hash']='different'
    result=finite_checks(points,layouts,np.zeros((10,10)),'same')
    assert all(v['numerical_passed'] for v in result)
    assert not all(v['feature_hash_stable'] for v in result)

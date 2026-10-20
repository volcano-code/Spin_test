"""M12 end-to-end source-bound analytic controls; NO native teacher admission."""
import math
import numpy as np
import pytest
import torch

from research.NeuralMoments.models.deeponet.m8_analytic_data import Shape
from research.NeuralMoments.models.deeponet.m12_saturation import strict_native_sign
from research.NeuralMoments.models.deeponet.m12_experiment import probes, run, TRAINED_NAMES


def test_strict_classifier_never_overstates_randomized_native_quadrics():
    rng=np.random.default_rng(5021)
    shape=Shape('ellipsoid',(.1,-.13,.19),(.59,.31,.45))
    corners=np.array(shape.center)
    axes=np.array(shape.axes)
    for _ in range(85):
        c=torch.from_numpy(rng.normal(size=10)).double()
        c/=c.norm()
        state=strict_native_sign(c,shape)
        if state=='UNDECIDED':continue
        positions=corners+(rng.uniform(-1,1,size=(200,3))*axes)
        x,y,z=positions.T
        native=c.numpy()
        values=(native[0]+native[1]*x+native[2]*y+native[3]*z+
                native[4]*x*x+native[5]*y*y+native[6]*z*z+
                2*native[7]*y*z+2*native[8]*x*z+2*native[9]*x*y)
        assert float(np.min(values))>0 if state=='ANALYTIC_CERTIFIED_FULL' else float(np.max(values))<0


def test_contact_is_not_false_full_or_empty():
    # Exactly representable signed linear beta=z (unit c, no normalization
    # rounding): top and bottom of *different* analytic boxes touch z=0.
    c=torch.tensor([0.,0.,0.,1.]+[0.]*6,dtype=torch.float64)
    neg=Shape('box',(0.,0.,-.375),(.5,.5,.375))
    pos=Shape('box',(0.,0.,+.375),(.5,.5,.375))
    assert strict_native_sign(c,neg)=='UNDECIDED'
    assert strict_native_sign(c,pos)=='UNDECIDED'


def test_four_predeclared_probe_controls_are_native_unit_and_signed():
    shapes=(Shape('box',(.1,0.,-.1),(.6,.55,.4)),
            Shape('sphere',(.0,.1,-.05),(.5,.5,.5)),
            Shape('ellipsoid',(.09,-.1,.12),(.6,.4,.48)))
    for c in probes():
        assert c.shape==(1,10)
        assert abs(float(c.norm())-1)<2e-6
    for s in shapes:
        assert [strict_native_sign(c[0],s) for c in probes()]==[
            'ANALYTIC_CERTIFIED_FULL','ANALYTIC_CERTIFIED_EMPTY',
            'ANALYTIC_CERTIFIED_FULL','ANALYTIC_CERTIFIED_EMPTY']


def test_invalid_runs_do_not_trigger_hidden_training():
    with pytest.raises(ValueError):run(w6_root='/nonexistent',seed=12,steps=0)
    with pytest.raises(ValueError):run(w6_root='/nonexistent',seed=12,names=('w5_deeponet_voxel',))
    with pytest.raises(ValueError):run(w6_root='/nonexistent',seed=12,names=TRAINED_NAMES+('w5_deeponet_voxel',))
    with pytest.raises(ValueError):run(w6_root='/nonexistent',seed=12,names=TRAINED_NAMES+('w2_real_cad_teacher',))


def test_actual_pinned_w6_cpu_end_to_end_tiny():
    import os
    root=os.environ.get('W5_M12_READONLY_W6_ROOT')
    if not root: pytest.skip('read-only pinned W6 source not supplied')
    out=run(w6_root=root,seed=79,steps=3,per_family=5)
    assert out['max_optimizer_steps']==3
    assert out['real_w2_training_labels']==0 and out['native_cherchi_calls']==0
    assert out['geometry_family_split']['heldout_families']==['ellipsoid']
    assert len(out['results'])==4
    control=out['results']['w5_cone_integrable_025']
    plain=control['strict_saturation_without_independent_full_moment']
    protected=control['M12_strict_saturation_with_independent_analytic_full_moment']
    assert protected['independent_analytic_geometry_count']==5
    assert protected['out_of_cut_queries']==20
    assert protected['full_raw_r_mae']==protected['empty_raw_r_mae']==0
    assert protected['max_full_abs_Jc']==protected['max_empty_abs_Jc']==0
    assert plain['full_raw_r_mae']>0
    assert control['interior_preservation']['max_r_difference']==0
    assert control['interior_preservation']['max_J_difference_where_defined']==0
    assert out['parameter_counts']['w5_cone_integrable_025']==13448
    assert out['teacher_kind']=='ANALYTIC_P0_GROUND_TRUTH_ONLY_NOT_W2_REAL_MATERIAL'

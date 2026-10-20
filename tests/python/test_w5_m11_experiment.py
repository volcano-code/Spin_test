"""M11 protocol checks; real W6 original source through SHA pin, no W2 labels."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import pytest
from research.NeuralMoments.models.deeponet import m11_experiment as m11


def _latest_w2_stub():
    return {'schema':'w2-cherchi-teacher-v2-pre-w0','training_samples':0,
            'native_teacher_runs':0,'m9_real_h8f_81_evidence':{
            'original_native_evaluations':81,'training_admitted':0,
            'certified_continuous_neighborhood':False,
            'derivative_J_D_published':False,'original_workflow_conclusion':'failure',
            'point60':{'added_LPI_features':2}}}


def test_current_h8f_metadata_is_excluded():
    result=m11.inspect_teacher_metadata(_latest_w2_stub())
    assert result['real_native_derivative_training_admitted']==0
    assert result['point60_smooth_neighborhood_certified'] is False
    assert result['Git_blob_independently_verified_by_this_function'] is False


@pytest.mark.parametrize('change',[
    ('training_samples',1),('native_teacher_runs',1),('schema','unsafe'),
    ('m9_real_h8f_81_evidence.original_native_evaluations',80),
    ('m9_real_h8f_81_evidence.derivative_J_D_published',True),
    ('m9_real_h8f_81_evidence.certified_continuous_neighborhood',True),
    ('m9_real_h8f_81_evidence.point60.added_LPI_features',0),
    ('m9_real_h8f_81_evidence.original_workflow_conclusion','success'),
])
def test_h8f_promotion_rejected(change):
    data=copy.deepcopy(_latest_w2_stub())
    a,b=change;keys=a.split('.');cur=data
    for key in keys[:-1]:cur=cur[key]
    cur[keys[-1]]=b
    with pytest.raises(ValueError):m11.inspect_teacher_metadata(data)


def test_frozen_protocol_and_zero_native_training():
    assert m11.TRAINING_ONLY_ANALYTIC is True
    assert m11.NAMES[0]=='w5_deeponet_voxel'
    assert m11.MIX['w5_cone_integrable_075']==.75
    with pytest.raises(ValueError):m11.create_model('other',19,None)


def test_live_cross_framework_2step_smoke():
    src=os.environ.get('W5_M11_READONLY_W6_ROOT')
    if not src:pytest.skip('Pinned W6 source missing')
    record=m11.run(w6_root=src,seed=41,steps=2,per_family=5,repeats=1,
                   names=('w5_deeponet_voxel','w5_cone_integrable_025'))
    assert record['W2_admissible_training_labels']==0
    assert record['W5_new_native_cherchi_queries']==0
    assert record['train_per_seed_total_analytic_queries']==20
    assert set(record['results'])=={'w5_deeponet_voxel','w5_cone_integrable_025'}
    assert record['real_parameter_ratio']<1.05
    for x in record['results'].values():
        assert x['training']['steps_executed']==2
        assert x['heldout']['J_mae']>=0
        assert x['measured_queries']['8']['actual_measured_not_additive_estimate']

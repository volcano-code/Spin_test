"""M5 orchestration contracts: fake M4 is explicitly mocked and never real truth."""
from __future__ import annotations
from unittest.mock import patch
import copy
import pytest

from . import native_m5_bridge
from .native_m5_bridge import audit_native_w0_w2_once
from .native_teacher_replay import ReplayRejected

V=[['0/1','0/1','0/1'],['1/1','0/1','0/1'],['0/1','1/1','0/1'],['0/1','0/1','1/1']]
F=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]

class SyntheticReplay:
    def __init__(self):
        self.request=type('Req',(),{'material_density':2.0})()
        self.saved={'variable_rational_vertices':copy.deepcopy(V),
                    'variable_faces':copy.deepcopy(F),
                    'variable_raw_moments':[1/3,1/12,1/12,1/12,1/30,1/30,1/30,1/60,1/60,1/60]}
        self.reads=0
    def material(self,c):
        self.reads+=1
        return self.saved

BASE={'native_execution_observed':True,'native_region_proved':True,
      'mathematical_replay_passed':True,'status':'SYNTHETIC_TEST_ONLY'}

def call(evaluator):
    return audit_native_w0_w2_once(evaluator=evaluator,problem=object(),c=[1.]*10,pins={})


def test_cross_window_bridge_does_not_rerun_native_or_promote():
    synthetic=SyntheticReplay()
    with patch.object(native_m5_bridge, 'audit_live_native_once',return_value=BASE) as m:
        result=call(synthetic)
        m.assert_called_once()
    assert synthetic.reads==1
    assert result['additional_cherchi_source_calls']==0
    assert result['native_w2_r10_max_absolute_error']==0
    assert not result['training_admissible']
    assert not result['complete_partition_certificate']
    assert not result['smooth_neighborhood_certificate']


@pytest.mark.parametrize('removed',["native_execution_observed","native_region_proved","mathematical_replay_passed"])
def test_missing_m4_physical_evidence_cannot_enter_w2_gate(removed):
    previous=dict(BASE);previous[removed]=False
    synthetic=SyntheticReplay()
    with patch.object(native_m5_bridge, 'audit_live_native_once',return_value=previous):
        with pytest.raises(ReplayRejected,match='M4_GENUINE'):
            call(synthetic)
    assert synthetic.reads==0


def test_tampered_saved_w2_moments_rejected():
    synthetic=SyntheticReplay();synthetic.saved['variable_raw_moments'][0]+=.1
    with patch.object(native_m5_bridge, 'audit_live_native_once',return_value=BASE):
        with pytest.raises(ReplayRejected,match='INDEPENDENT_MOMENT_MISMATCH'):
            call(synthetic)


def test_tampered_w2_topology_rejected():
    synthetic=SyntheticReplay();synthetic.saved['variable_faces'][0]=[0,1,2]
    with patch.object(native_m5_bridge, 'audit_live_native_once',return_value=BASE):
        with pytest.raises(ReplayRejected):call(synthetic)


def test_no_real_native_module_no_success():
    with pytest.raises(ReplayRejected,match='NATIVE_CHERCHI_RUNTIME_UNAVAILABLE'):
        call(SyntheticReplay())

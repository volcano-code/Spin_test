"""Cross architecture cached inference smoke. No trained weights or Cherchi truth."""
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np
import pytest
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.NeuralMoments.models.deeponet.model import DeepONetMoment
from research.NeuralMoments.models.geometry_mlp.model import GeometryMLPMoment
from research.NeuralMoments.models.deeponet.m6_model_adapter import cached_prediction
from research.NeuralMoments.models.deeponet.m6_analytic_rollout import guarded_analytic_step
from research.NeuralMoments.models.deeponet.native_p0 import native_vertical_c,cap_moments


@pytest.mark.parametrize("model_class",[DeepONetMoment,GeometryMLPMoment])
def test_single_encode_both_models_and_jacrev(model_class):
    torch.manual_seed(1701)
    model=model_class(geometry_dim=9).to(dtype=torch.float64).eval()
    geometry=np.linspace(-0.3,0.3,9)
    c=native_vertical_c(0.13)
    with patch.object(model,"encode_geometry",wraps=model.encode_geometry) as encode:
        output=cached_prediction(model,geometry,c)
        assert encode.call_count == 1
    assert output["predicted_r"].shape==(10,)
    assert output["predicted_Jc"].shape==(10,10)
    assert output["encoder_invocations"]==1
    assert output["parameter_count"]>10000
    assert output["weights_verified_for_native_cherchi"] is False
    for key in ("encode_seconds","warm_moment_seconds","warm_jacobian_seconds"):
        assert np.isfinite(output[key]) and output[key]>=0
    eps=1e-5
    cp,cm=c.copy(),c.copy()
    cp[0]+=eps;cm[0]-=eps
    # The unnormalized control perturbation is intentional for the Jacobian
    # test; the adapter guards native c but model.moment is defined on R^10.
    with torch.no_grad():
        z=model.encode_geometry(torch.tensor(geometry,dtype=torch.float64))
        fplus=model.moment(z,torch.tensor(cp,dtype=torch.float64)).numpy()
        fminus=model.moment(z,torch.tensor(cm,dtype=torch.float64)).numpy()
    np.testing.assert_allclose(output["predicted_Jc"][:,0],(fplus-fminus)/(2*eps),
                               rtol=1e-5,atol=1e-7)


@pytest.mark.parametrize("model_class",[DeepONetMoment,GeometryMLPMoment])
def test_model_output_enters_untrusted_gate_and_can_fallback(model_class):
    torch.manual_seed(17)
    model=model_class(geometry_dim=9).to(dtype=torch.float64).eval()
    c=native_vertical_c(0.25)
    source=cached_prediction(model,np.zeros(9),c)
    result=guarded_analytic_step(radius=1.2,density=1.3,current_h=.25,
              target_r=cap_moments(1.2,.1,density=1.3),
              predicted_r=source["predicted_r"],
              predicted_Jc=source["predicted_Jc"])
    assert isinstance(result["accepted"],bool)
    assert result["native_cherchi_calls"]==0
    assert result["truth_calls"]<=4
    assert result["truth_source"]=="ANALYTIC_P0_ONLY"
    assert result["teacher_training_admissible"] is False
    assert result["loss_after"]<=result["loss_before"] + 1e-12


def test_training_mode_not_auto_changed_and_invalid_coefficients_rejected():
    model=DeepONetMoment(geometry_dim=9)
    with pytest.raises(ValueError,match="EVAL_MODE"):
        cached_prediction(model,np.zeros(9),native_vertical_c(0))
    assert model.training is True
    model.eval()
    with pytest.raises(ValueError,match="NORMALIZED"):
        cached_prediction(model,np.zeros(9),np.ones(10))
    with pytest.raises(ValueError,match="FEATURES_OR_CONTROL"):
        cached_prediction(model,np.zeros(8),native_vertical_c(0))
    with pytest.raises(ValueError,match="FEATURES_OR_CONTROL"):
        cached_prediction(model,np.full(9,np.nan),native_vertical_c(0))

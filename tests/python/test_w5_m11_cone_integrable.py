"""W5 M11 independent math and pinned source integration; no native CAD teacher."""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn
from research.NeuralMoments.models.deeponet.m11_cone_integrable import ConeIntegrableMoment

B=torch.tensor([1.]*7+[2.]*3,dtype=torch.float64)

class FrozenQuadrature(nn.Module):
    rule='gauss'
    def __init__(self):
        super().__init__()
        xs=torch.tensor([[-.8,-.6,-.4],[-.5,.1,.3],[.2,.7,-.2],[.5,.3,.8],[.8,-.4,.5]],dtype=torch.float64)
        x,y,z=xs.unbind(-1)
        self.register_buffer('monomials',torch.stack([torch.ones_like(x),x,y,z,x*x,y*y,z*z,y*z,x*z,x*y],-1))
        self.register_buffer('native_B',B.clone())
        self.weights=nn.Parameter(torch.tensor([.5,.3,.7,.6,.4],dtype=torch.float64))
    def _validate(self,z,c):
        if z.shape!=(c.shape[0],5) or c.shape!=(z.shape[0],10) or z.dtype!=c.dtype:
            raise ValueError('shape or dtype')
        if not bool(torch.isfinite(z).all() and torch.isfinite(c).all() and (z>=0).all() and (c.norm(dim=-1)>0).all()):
            raise ValueError('bad data')
    def encode_geometry(self,D):
        return self.weights.clamp_min(0).expand(len(D),-1)

@pytest.fixture(params=[0.25,0.75,1.0])
def fixture_model(request):
    return ConeIntegrableMoment(FrozenQuadrature(),mix=request.param)

def _input(dtype=torch.float64):
    c=torch.tensor([[.2,.3,-.4,.6,.1,.12,-.1,.09,.03,-.15]],dtype=dtype)
    c=c/c.norm(dim=-1,keepdim=True)
    return c

def test_mass_and_moment_cone_all_signs(fixture_model):
    model=fixture_model
    z=model.encode_geometry(torch.zeros(4,1,dtype=torch.float64))
    c=torch.cat([_input(),- _input(),torch.tensor([[-1.]+[0.]*9],dtype=torch.float64),
                 torch.tensor([[1.]+[0.]*9],dtype=torch.float64)],0)
    r=model.moment(z,c)
    assert (r[:,0]>=0).all()
    assert torch.equal(r[2],torch.zeros(10,dtype=torch.float64))
    assert torch.allclose(r[3],z[3]@model.encoder.monomials,atol=1e-12)
    M=r[:,0];L=r[:,1:4]
    Q=torch.zeros(4,3,3,dtype=torch.float64)
    Q[:,0,0],Q[:,1,1],Q[:,2,2]=r[:,4],r[:,5],r[:,6]
    Q[:,1,2]=Q[:,2,1]=r[:,7];Q[:,0,2]=Q[:,2,0]=r[:,8];Q[:,0,1]=Q[:,1,0]=r[:,9]
    assert torch.linalg.eigvalsh(M[:,None,None]*Q-L[:,:,None]*L[:,None,:]).min()>=-1e-11
    assert ((L.abs()<=M[:,None]+1e-10).all())

def test_autograd_gradient_and_hessian(fixture_model):
    model=fixture_model
    z=model.encode_geometry(torch.zeros(1,1,dtype=torch.float64)).detach()
    c=_input()
    q=(c*B).squeeze(0).detach().clone().requires_grad_()
    potential=lambda qq:model.potential(z,(qq/B).unsqueeze(0)).sum()
    r_auto=torch.autograd.functional.jacobian(potential,q)
    Jq_auto=torch.autograd.functional.hessian(potential,q)
    r=model.moment(z,c).squeeze(0)
    Jq=(model.jacobian(z,c)/B.view(1,1,-1)).squeeze(0)
    assert torch.allclose(r_auto,r,atol=2e-12,rtol=2e-12)
    assert torch.allclose(Jq_auto,Jq,atol=5e-12,rtol=5e-12)
    assert torch.allclose(Jq,Jq.T,atol=5e-13)
    assert torch.linalg.eigvalsh(Jq).min()>-2e-12
    assert torch.allclose(Jq@q,torch.zeros(10,dtype=torch.float64),atol=5e-12)

def test_scale_invariance_and_signed_side(fixture_model):
    model=fixture_model; z=model.encode_geometry(torch.zeros(1,1,dtype=torch.float64));c=_input()
    assert torch.allclose(model.moment(z,c),model.moment(z,7*c),atol=1e-12)
    assert torch.allclose(model.jacobian(z,7*c)*7,model.jacobian(z,c),atol=5e-11)
    assert not torch.allclose(model.moment(z,c),model.moment(z,-c))

def test_fixed_smooth_region_and_nodal_boundary(fixture_model):
    model=fixture_model;z=model.encode_geometry(torch.zeros(1,1,dtype=torch.float64))
    c=_input()
    assert model.derivative_regime(z,c)==('FIXED_ACTIVE_SET_SMOOTH_SURROGATE_ONLY',)
    c0=torch.tensor([[-.5,1.,0.,0.,0.,0.,0.,0.,0.,0.]],dtype=torch.float64)
    assert model.derivative_regime(z,c0)==('NODE_SIGN_BOUNDARY_UNDEFINED',)
    with pytest.raises(ValueError,match='NODE_SIGN_BOUNDARY'):
        model.jacobian(z,c0)
    empty=torch.tensor([[-1.]+[0.]*9],dtype=torch.float64)
    assert model.derivative_regime(z,empty)==('STRICT_EMPTY_OR_ZERO_WEIGHT_LOCAL',)
    assert model.jacobian(z,empty).abs().max()==0

def test_training_gradients_and_cache(fixture_model):
    model=fixture_model
    D=torch.zeros(2,1,dtype=torch.float64)
    z=model.encode_geometry(D)
    c=torch.cat([_input(),-_input()],0)
    r=model.moment(z,c);j=model.jacobian(z,c)
    (r.square().mean()+.5*j.square().mean()).backward()
    assert model.encoder.weights.grad is not None
    assert torch.isfinite(model.encoder.weights.grad).all()
    assert model.encoder.weights.grad.abs().max()>0

def test_strict_input_validation():
    with pytest.raises(ValueError):ConeIntegrableMoment(FrozenQuadrature(),mix=0)
    with pytest.raises(ValueError):ConeIntegrableMoment(FrozenQuadrature(),mix=float('nan'))
    with pytest.raises(ValueError):ConeIntegrableMoment(FrozenQuadrature(),boundary_rtol=-1)
    model=ConeIntegrableMoment(FrozenQuadrature())
    with pytest.raises(ValueError):model.moment(torch.tensor([[float('nan')]*5],dtype=torch.float64),_input())
    assert model.derivative_contract()['native_cherchi_derivative_admitted'] is False

def test_real_w6_source_pinned_model():
    src=os.environ.get('W5_M11_READONLY_W6_ROOT')
    if not src:
        pytest.skip('W6 source root not supplied; no invented successful integration')
    from research.NeuralMoments.models.deeponet.m9_readonly_w6 import load_m9_w6
    *_,m6,_=load_m9_w6(src)
    torch.manual_seed(19)
    model=ConeIntegrableMoment(m6.GaussPotentialMoment(rule='gauss',grid_size=8,
                                                      points_per_axis=6,hidden=32,smoothing=.04),mix=.75)
    import research.NeuralMoments.models.deeponet.m8_analytic_data as a
    D,c,_,_,_=a.dataset(('sphere',),per_family=2,seed=19)
    z=model.encode_geometry(D)
    r=model.moment(z,c);J=model.jacobian(z,c)
    assert r.shape==(len(D),10) and J.shape==(len(D),10,10)
    assert model.real_parameter_count()==13448
    H=J/torch.tensor([1.]*7+[2.]*3)
    assert (H-H.transpose(-1,-2)).abs().max()<2e-5
    assert r[:,0].min()>=0

@pytest.mark.parametrize('mix',[.25,.75])
def test_known_full_region_still_approximate_not_exact(mix):
    """Adverse finding: convex norm can reweight even an entirely FULL region."""
    model=ConeIntegrableMoment(FrozenQuadrature(),mix=mix)
    z=model.encode_geometry(torch.zeros(1,1,dtype=torch.float64))
    c=torch.tensor([[1.,.1]+[0.]*8],dtype=torch.float64)
    c/=c.norm(dim=-1,keepdim=True)
    assert torch.min((c*B)@model.encoder.monomials.T)>0
    true_full=z@model.encoder.monomials
    pred=model.moment(z,c)
    assert torch.max(torch.abs(pred-true_full))>1e-5
    assert model.jacobian(z,c).abs().max()>1e-8
    assert model.derivative_contract()['CAD_geometry_or_3D_volume_certified'] is False

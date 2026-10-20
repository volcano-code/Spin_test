"""Read-only source-matched W5 4-channel DeepONet analytic comparator for W6 M10.

W5 M8 FourChannelSpatialEncoder source: original Git blob
  317bcf1c3965326ee56b5948b80b01bbd052b592
W5 original DeepONetMoment snapshot source:
  7aa363769c0baf9f843d50e268164e761b566977
No W5 branch, files or existing trained weights are modified. This small
composition is a comparator only, not a newly invented W6 candidate.
"""
from __future__ import annotations
import torch
from torch import nn
from torch.func import jacrev, vmap
from .w5_snapshot.deeponet.model import DeepONetMoment

class FourChannelSpatialEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.depthwise = nn.Conv3d(4,4,kernel_size=3,padding=1,groups=4)
        self.project = nn.Sequential(nn.Linear(16,9),nn.Tanh())
    def forward(self,D):
        if not isinstance(D,torch.Tensor) or D.ndim!=5 or D.shape[1]!=4:
            raise ValueError('expected D [B,4,X,Y,Z]')
        if D.shape[0]<1 or min(D.shape[-3:])<8 or not D.is_floating_point() or not bool(torch.isfinite(D).all()):
            raise ValueError('nonfinite/undersized 4-channel voxels')
        features=torch.nn.functional.gelu(self.depthwise(D))
        coords=[torch.linspace(-1.,1.,n,dtype=D.dtype,device=D.device) for n in D.shape[-3:]]
        basis=torch.stack(torch.meshgrid(*coords,indexing='ij'),dim=0)
        global_mean=features.mean((-3,-2,-1))
        signed_means=(features.unsqueeze(2)*basis.unsqueeze(0)).mean((-3,-2,-1))
        return self.project(torch.cat((global_mean,signed_means.flatten(1)),dim=1))

class W5VoxelDeepONet(nn.Module):
    """Original W5 M8 spatial encoder + pinned DeepONet, 13939 real DOFs."""
    def __init__(self):
        super().__init__()
        self.voxel_encoder=FourChannelSpatialEncoder()
        self.core=DeepONetMoment(geometry_dim=9)
    def encode_geometry(self,D):
        return self.core.encode_geometry(self.voxel_encoder(D))
    @staticmethod
    def _check(z,c):
        if c.ndim!=2 or c.shape[-1]!=10 or z.ndim!=2 or z.shape[0]!=c.shape[0]:
            raise ValueError('expected matching [B,latent] and [B,10]')
        if z.device!=c.device or z.dtype!=c.dtype or not bool(torch.isfinite(c).all()) or bool((torch.linalg.vector_norm(c,dim=-1)<=1e-12).any()):
            raise ValueError('invalid native c')
    def moment(self,z,c):
        self._check(z,c)
        return self.core.moment(z,c/torch.linalg.vector_norm(c,dim=-1,keepdim=True))
    def jacobian(self,z,c):
        self._check(z,c)
        def one(zz,cc):
            return self.core.moment(zz,cc/torch.linalg.vector_norm(cc))
        return vmap(jacrev(one,argnums=1))(z,c)
    def forward(self,D,c):
        return self.moment(self.encode_geometry(D),c)

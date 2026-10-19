"""M4 compact geometry-cached U-FNO variants: factorized FFTs only after pooling.

Independent candidate, NOT a modification of the M1 UFNO model. The shared
4-channel input, W0 signed native coefficient order, ten raw moments and J
interface are unchanged. ``model.encode_geometry`` runs once per geometry;
``model.moment(z,c)`` and ``model.jacobian(z,c)`` reuse cached z.

FFT variants place 1D frequency mixing at 4^3, 2^3 or both instead of the
64^3 FEM output decoder. The local-only ablation has no FFT trainable weights.
"""
from __future__ import annotations
import math
import torch
from torch import nn,Tensor
from torch.nn import functional as F
from torch.func import jacrev, vmap

VARIANTS={"dual":(True,True,72),"bottleneck":(False,True,76),"local_only":(False,False,92)}


def num_real_parameters(model:nn.Module)->int:
    return sum(p.numel()*(2 if p.is_complex() else 1) for p in model.parameters() if p.requires_grad)


def voxel_statistics9(x:Tensor)->Tensor:
    """A label-agnostic, non-learned 9-vector computed only from raw density voxels."""
    if x.ndim!=5 or x.shape[1]!=4 or not x.is_floating_point():raise ValueError("expected [B,4,X,Y,Z] voxels")
    if not bool(torch.isfinite(x).all()) or min(x.shape[-3:])<4:raise ValueError("invalid voxel values or resolution")
    rho=x[:,0]
    coords=[torch.linspace(-1,1,int(n),device=x.device,dtype=x.dtype) for n in x.shape[-3:]]
    xyz=torch.stack(torch.meshgrid(*coords,indexing="ij"),dim=0)
    mass=rho.sum((-3,-2,-1)).clamp_min(1e-8)
    mean=torch.einsum('bxyz,ixyz->bi',rho,xyz)/mass[:,None]
    diff=xyz[None]-mean[:,:,None,None,None]
    var=(rho[:,None]*diff.square()).sum((-3,-2,-1))/mass[:,None]
    xy=(rho*diff[:,0]*diff[:,1]).sum((-3,-2,-1))/mass
    xz=(rho*diff[:,0]*diff[:,2]).sum((-3,-2,-1))/mass
    return torch.cat([rho.mean((-3,-2,-1))[:,None],mean,var,xy[:,None],xz[:,None]],dim=-1)


class AxisFactorizedFFT(nn.Module):
    """Axiswise rFFT, kept modes clipped to Nyquist, no 3D Fourier field."""
    def __init__(self,channels:int,modes:int):
        super().__init__()
        self.channels=channels
        self.modes=modes
        self.weights=nn.ParameterList([nn.Parameter(torch.randn(channels,channels,modes,dtype=torch.cfloat)/channels**2) for _ in range(3)])

    def forward(self,x:Tensor)->Tensor:
        if x.ndim!=5 or x.shape[1]!=self.channels:raise ValueError("FFT input shape")
        x=x.float()
        out=torch.zeros_like(x)
        for axis,w in zip((2,3,4),self.weights):
            ft=torch.fft.rfft(x,dim=axis)
            m=min(self.modes,ft.shape[axis])
            moved=ft.movedim(axis,2)
            o=torch.zeros((x.shape[0],self.channels,*moved.shape[2:]),device=x.device,dtype=ft.dtype)
            o[:,:,:m]=torch.einsum('bimuv,iom->bomuv',moved[:,:,:m],w[:,:,:m])
            out=out+torch.fft.irfft(o.movedim(2,axis),n=x.shape[axis],dim=axis)/3
        return out


class TinySpectralBlock(nn.Module):
    def __init__(self,ch:int,modes:int,enabled:bool):
        super().__init__()
        self.spectral=AxisFactorizedFFT(ch,modes) if enabled else None
        self.local=nn.Conv3d(ch,ch,1)
        self.norm=nn.GroupNorm(1,ch)
    def forward(self,x:Tensor)->Tensor:
        value=self.local(x)
        if self.spectral is not None:value=value+self.spectral(x)
        return F.gelu(self.norm(value))


class LiteUFNOMoment(nn.Module):
    """2-level small-FFT encoder and 10-dimensional cached nonlinear moment head."""
    def __init__(self,variant:str="bottleneck",grid_size:int=8):
        super().__init__()
        if variant not in VARIANTS or grid_size<8 or grid_size%4:raise ValueError("unknown variant or invalid grid")
        s4,s2,hidden=VARIANTS[variant]
        self.variant=variant
        self.grid_size=grid_size
        self.lift=nn.Conv3d(4,8,1)
        self.level4=TinySpectralBlock(8,3,s4)
        self.down=nn.Conv3d(8,16,1)
        self.level2=TinySpectralBlock(16,2,s2)
        self.project=nn.Sequential(nn.Linear(8+16+9,24),nn.GELU())
        self.head=nn.Sequential(nn.Linear(24+10,hidden),nn.GELU(),
                                nn.Linear(hidden,hidden),nn.GELU(),nn.Linear(hidden,10))

    def encode_geometry(self,D:Tensor)->Tensor:
        if D.ndim!=5 or D.shape[1]!=4 or not D.is_floating_point():raise ValueError("geometry must be [B,4,X,Y,Z]")
        stats=voxel_statistics9(D)
        x=D
        if x.shape[-3:]!=(self.grid_size,)*3:
            x=F.interpolate(x,size=(self.grid_size,)*3,mode='trilinear',align_corners=False)
        x=F.avg_pool3d(self.lift(x),2)
        h4=self.level4(x)
        h2=self.level2(F.avg_pool3d(self.down(h4),2))
        pooled=torch.cat([h4.mean((-3,-2,-1)),h2.mean((-3,-2,-1)),stats],dim=-1)
        return self.project(pooled)

    @staticmethod
    def _normalize(c:Tensor)->Tensor:
        norms=torch.linalg.vector_norm(c,dim=-1,keepdim=True)
        return c/norms

    def moment(self,z:Tensor,c:Tensor)->Tensor:
        if z.ndim!=2 or z.shape[1]!=24 or c.shape!=(z.shape[0],10):raise ValueError("expected z[B,24], c[B,10]")
        if not torch.isfinite(c).all() or bool((torch.linalg.vector_norm(c,dim=-1)<=1e-12).any()):raise ValueError("invalid c")
        return self.head(torch.cat([z,self._normalize(c)],dim=-1))

    def jacobian(self,z:Tensor,c:Tensor)->Tensor:
        if z.ndim!=2 or z.shape[1]!=24 or c.shape!=(z.shape[0],10):raise ValueError("expected z[B,24], c[B,10]")
        if not bool(torch.isfinite(c).all()) or bool((c.norm(dim=-1)<=1e-12).any()):raise ValueError("invalid c")
        # Avoid data-dependent tensor bools *inside* vmap/jacrev.
        def one(zz,cc):return self.head(torch.cat([zz,cc/cc.norm()],dim=-1))
        return vmap(jacrev(one,argnums=1))(z,c)

    def forward(self,D:Tensor,c:Tensor)->Tensor:return self.moment(self.encode_geometry(D),c)

"""P13a genuinely coupled DensiCrafter -> PINO differentiable density design.

W6 uses pinned MIT DensiCrafter mass, CoM, and smooth ground contact
primitives. We parameterize the physical coordinates, gravity orientation
and nonperiodic smoothing without copying TRELLIS/Blender/MuJoCo pipeline.
P-CRAFT U-FNO/F-FNO and its ten-moment head stay the only neural operator.

This module optimizes rho(x) (material design), not the 10 coefficient c.
The PINO Jacobian d r / d c is diagnostic ONLY until Cherchi/W0/W2 formal
admission. The input-density gradient d L/d rho is a separate quantity.
"""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn, Tensor

from .third_party.densicrafter_core import (
    mass_penalty, compute_mass_center, get_smooth_bottom_contact_region,
)

def physical_grid(shape, *, device, dtype):
    if len(shape)!=3 or min(shape)<4:
        raise ValueError("shape must contain three axes with >=4 cells each")
    axes=[(torch.arange(n,device=device,dtype=dtype)+.5)*(2./n)-1.
          for n in shape]
    return torch.stack(torch.meshgrid(*axes,indexing="ij"),dim=-1)


def material_moments(density: Tensor) -> Tensor:
    """Differentiable *cell-centered* ten full-material moments in [-1,1]^3.

    These are discretized input-material statistics, not native Cherchi
    Boolean-cut r_D(c). Cross terms are undoubled in raw moment order.
    """
    if density.ndim!=5 or density.shape[1]!=1:
        raise ValueError("density must be [B,1,X,Y,Z]")
    if not bool(torch.isfinite(density).all()) or bool((density<0).any()):
        raise ValueError("density must be finite nonnegative")
    grid=physical_grid(density.shape[-3:],device=density.device,dtype=density.dtype)
    x,y,z=grid.unbind(-1)
    basis=torch.stack([torch.ones_like(x),x,y,z,x*x,y*y,z*z,y*z,x*z,x*y],-1)
    volume=8./float(density.shape[-3]*density.shape[-2]*density.shape[-1])
    return torch.einsum("bxyz,xyzi->bi",density[:,0],basis)*volume


def _contact_loss(density: Tensor, *, gravity_axis: int, grid: Tensor):
    """DensiCrafter bottom-contact idea in physical [-1,1] coordinates.

    Floor is the *minimum* coordinate of the declared gravity axis.
    Unlike original hard-coded 64^3 z plane, support can be any axis,
    with neither torch.roll periodic wrapping nor NumPy detach.
    """
    if gravity_axis not in (0,1,2):
        raise ValueError("gravity axis must be 0/1/2")
    b=density[:,0]
    if gravity_axis!=2:
        other=[axis for axis in range(3) if axis!=gravity_axis]
        reordered=b.permute(0,other[0]+1,other[1]+1,gravity_axis+1)
        plane_coords=grid.permute(other[0],other[1],gravity_axis,3)[...,0,:]
    else:
        reordered=b
        plane_coords=grid[...,0,:]
    contact=get_smooth_bottom_contact_region(reordered,0,exp=4.0)
    support_mass=contact.sum(dim=(1,2))
    if bool((support_mass<=1e-8).any()) or not bool(torch.isfinite(support_mass).all()):
        raise ValueError("empty/nonfinite bottom contact region")
    original_com=compute_mass_center(b,grid).transpose(0,1)
    plane=[i for i in range(3) if i!=gravity_axis]
    distances=torch.linalg.vector_norm(
        plane_coords[...,plane].unsqueeze(0)
        - original_com[:,None,None,plane],dim=-1
    )
    com_to_contact=(distances*contact).sum((1,2))/support_mass
    ground=float((-1.+1./density.shape[2+gravity_axis]))
    com_height=original_com[:,gravity_axis]-ground
    if not bool(torch.isfinite(com_to_contact).all()):
        raise FloatingPointError("nonfinite center/support contact loss")
    return com_to_contact.mean(),-contact.mean(),com_height.mean(),original_com


class DensiCrafterSpinPINOBridge(nn.Module):
    """Active trainable interior density with fixed protected shell and PINO.

    Density is guaranteed to be 1 on protected shell and zero outside
    the declared solid/support mask. This proof-of-interface is restricted
    to positive normalized material densities; it is NOT an FEM solver.
    """

    def __init__(self, pino: nn.Module, shell: Tensor, design: Tensor,
                 *, gravity_axis=2, smoothing=False):
        super().__init__()
        if not all(hasattr(pino,name) for name in (
            "encode_geometry","moment_from_weights","jacobian_from_weights",
        )):
            raise TypeError("P-CRAFT SpinPINO model is required")
        if shell.shape!=design.shape or shell.ndim!=5 or shell.shape[1]!=1:
            raise ValueError("shell and design masks must be [B,1,X,Y,Z]")
        if min(shell.shape[-3:])<8 or shell.device!=design.device:
            raise ValueError("PINO density design must be at least 8^3 on one device")
        if shell.dtype!=torch.bool or design.dtype!=torch.bool:
            raise TypeError("shell/design must be boolean")
        if bool((shell&design).any()):
            raise ValueError("protected shell and design cells must not overlap")
        if not bool(shell.any()) or not bool(design.any()):
            raise ValueError("nonempty shell and interior design required")
        if gravity_axis not in (0,1,2):
            raise ValueError("gravity_axis must be 0/1/2")
        self.pino=pino
        self.register_buffer("shell",shell.clone())
        self.register_buffer("design",design.clone())
        self.density_logits=nn.Parameter(torch.zeros_like(shell,dtype=torch.float32))
        self.gravity_axis=int(gravity_axis)
        self.smoothing=bool(smoothing)

    def density(self) -> Tensor:
        interior=torch.sigmoid(self.density_logits)
        if self.smoothing:
            interior=F.avg_pool3d(interior,kernel_size=3,stride=1,padding=1)
        # Non-periodic and exact shell protection; no density outside support.
        return torch.where(self.shell,torch.ones_like(interior),
                           torch.where(self.design,interior,torch.zeros_like(interior)))

    def forward(self,coefficients:Tensor, *,
                reference_cut_moments:Tensor|None=None,
                weights:dict|None=None):
        density=self.density()
        if coefficients.shape!=(density.shape[0],10):
            raise ValueError("native c must be [B,10]")
        if coefficients.device!=density.device or coefficients.dtype!=density.dtype:
            raise ValueError("native c must share density device and dtype")
        occupancy=(self.shell|self.design).to(density.dtype)
        zeros=torch.zeros_like(density)
        geometry=torch.cat((density,occupancy,zeros,zeros),dim=1)
        node_weights=self.pino.encode_geometry(geometry)
        r=self.pino.moment_from_weights(node_weights,coefficients)
        J=self.pino.jacobian_from_weights(node_weights,coefficients)
        grid=physical_grid(density.shape[-3:],device=density.device,dtype=density.dtype)
        com_penalty,neg_contact,com_height,com=_contact_loss(
            density,gravity_axis=self.gravity_axis,grid=grid,
        )
        terms={
            "mass":mass_penalty(density),
            "com_contact":com_penalty,
            "negative_contact_area":neg_contact,
            "com_height":com_height,
        }
        if reference_cut_moments is not None:
            if reference_cut_moments.shape!=r.shape:
                raise ValueError("reference r must be [B,10]")
            terms["cut_moment_error"]=(r-reference_cut_moments).square().mean()
        else:
            terms["cut_moment_error"]=r.new_zeros(())
        if weights is None:
            weights={
                "mass":1.0,"com_contact":.0,
                "negative_contact_area":.0,"com_height":.0,
                "cut_moment_error":1.0,
            }
        if any((k not in terms or not isinstance(v,(int,float)) or
                not (0<=float(v)<float("inf"))) for k,v in weights.items()):
            raise ValueError("all loss weights must be finite, nonnegative and known")
        total=sum((terms[k]*float(weights.get(k,0.)) for k in terms),
                  r.new_zeros(()))
        return {
            "density":density,
            "geometry":geometry,
            "full_material_moments":material_moments(density),
            "moments":r,
            "model_jacobian_diagnostic":J,
            "com":com,
            "terms":terms,
            "loss":total,
            "native_jacobian_admitted":False,
            "w0_w2_cherchi_training_admitted":False,
            "pino_primary":True,
        }

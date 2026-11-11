"""P30.0: material-measure slice mixing INSIDE the P-CRAFT F-FNO trunk.

Mechanism-level adaptation of learned slicing/unslicing (Transolver family),
positive measure aggregation (quadrature), and material support (Spin).
This is an independent small implementation, NOT the upstream Transolver++
model, a GINO/QuadrANN import, or a parallel pooled geometry encoder.

Only the pre-normalization block update changes. Original spectral/local
operators, U-shaped stages, positive moment head and logistic d r/d c remain.
Conservation below concerns a latent increment, NOT exact physical moments.
Dense grids remain dense; no 512^3, sparse-backend or native-J claim is made.
"""
from __future__ import annotations

import math
from functools import partial
import torch
from torch import Tensor, nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint

from ..model import canonical_geometry
from .pino_backbone import PINOFeatureEncoder
from .spin_pino import SpinPINO


def material_fields(geometry: Tensor) -> Tensor:
    """Compute rho*occupancy BEFORE coarsening; never multiply pooled fields.

    Channel 4 is a local occupancy-contrast indicator, not a measured SDF,
    thickness, curvature or topology certificate. Zero padding is nonperiodic.
    """
    d = canonical_geometry(geometry)
    rho, occ = d[:, :1], d[:, 1:2]
    if bool((rho < 0).any()) or bool(((occ < 0) | (occ > 1)).any()):
        raise ValueError("nonnegative density and occupancy in [0,1] required")
    boundary = (occ - F.avg_pool3d(occ, 3, stride=1, padding=1)).abs()
    return torch.cat((rho * occ, occ, d[:, 2:4], boundary), dim=1)


def scale_context(fields: Tensor, shape) -> Tensor:
    """Five material descriptors + normalized cell-center xyz at this scale."""
    if all(a >= b for a, b in zip(fields.shape[-3:], shape)):
        local = F.adaptive_avg_pool3d(fields, shape)
    else:
        local = F.interpolate(fields, size=shape, mode="trilinear", align_corners=False)
    axes = [(torch.arange(n, device=local.device, dtype=local.dtype) + .5) * (2/n) - 1
            for n in shape]
    xyz = torch.stack(torch.meshgrid(*axes, indexing="ij"), dim=0)
    return torch.cat((local, xyz[None].expand(local.shape[0], -1, -1, -1, -1)), dim=1)


class MaterialSliceMixer(nn.Module):
    """Weighted partition -> slice interaction -> support-limited zero-mean update.

    A_ik >= 0, sum_k A_ik=1. Tokens are averages w.r.t. A_ik*m_i*dV.
    The attention prior is slice mass. After unslicing, delta is centered so
    sum_i m_i*delta_i=0 (floating point tolerance) and delta=0 where m=0.
    'uniform' is a same-parameter ablation without material descriptors/mask.
    """
    def __init__(self, channels: int, slices: int = 8, *, measure: str = "material"):
        super().__init__()
        if channels < 2 or slices < 2 or measure not in {"material", "uniform"}:
            raise ValueError("channels/slices >=2; measure must be material or uniform")
        self.channels, self.slices, self.measure = channels, slices, measure
        self.norm = nn.LayerNorm(channels)
        self.assignment = nn.Linear(channels + 8, slices)
        self.value = nn.Linear(channels, channels, bias=False)
        self.query = nn.Linear(channels, channels, bias=False)
        self.key = nn.Linear(channels, channels, bias=False)
        self.slice_value = nn.Linear(channels, channels, bias=False)
        self.output = nn.Linear(channels, channels, bias=False)
        self.gate = nn.Parameter(torch.zeros(()))

    def increment(self, hidden: Tensor, context: Tensor) -> Tensor:
        if hidden.ndim != 5 or hidden.shape[1] != self.channels:
            raise ValueError("hidden must be [B,C,X,Y,Z]")
        if context.shape != (hidden.shape[0], 8, *hidden.shape[-3:]):
            raise ValueError("context must be [B,8,X,Y,Z] on the block grid")
        h = hidden.flatten(2).transpose(1, 2)
        ctx = context.to(hidden).flatten(2).transpose(1, 2)
        if self.measure == "uniform":
            ctx = torch.cat((torch.zeros_like(ctx[..., :5]), ctx[..., 5:]), dim=-1)
            mass = torch.ones_like(ctx[..., :1])
            mask = mass
        else:
            mass = ctx[..., :1].clamp_min(0)
            mask = ctx[..., 1:2].clamp(0, 1) * (mass > 0).to(hidden.dtype)
        normalized = self.norm(h)
        assignment = torch.softmax(self.assignment(torch.cat((normalized, ctx), -1)), -1)
        weighted = assignment * mass * (8.0 / h.shape[1])
        slice_mass = weighted.sum(dim=1)
        tokens = weighted.transpose(1, 2) @ self.value(normalized)
        tokens = tokens / slice_mass.clamp_min(1e-12).unsqueeze(-1)
        prior = slice_mass / slice_mass.sum(-1, keepdim=True).clamp_min(1e-12)
        scores = self.query(tokens) @ self.key(tokens).transpose(1, 2) / math.sqrt(self.channels)
        scores = scores + prior.clamp_min(1e-12).log().unsqueeze(1)
        mixed = tokens + torch.softmax(scores, dim=-1) @ self.slice_value(tokens)
        response = self.output(assignment @ mixed)
        centering_mass = mass * mask
        mean = (response * centering_mass).sum(1, keepdim=True)
        mean = mean / centering_mass.sum(1, keepdim=True).clamp_min(1e-12)
        delta = mask * (response - mean)
        return delta.transpose(1, 2).reshape_as(hidden)

    def forward(self, hidden: Tensor, context: Tensor) -> Tensor:
        return self.gate.tanh() * self.increment(hidden, context)


class MaterialPINOEncoder(PINOFeatureEncoder):
    """Same U-FNO stages; integrate a shared mixer within each stage's blocks.

    This is NOT features += external_encoder(D) after pooling. Each update is
    GELU(IN(spectral(h)+local(h)+material_mix(h,D))) BEFORE the next FNO block.
    """
    def __init__(self, *, slices=8, measure="material", **kwargs):
        super().__init__(**kwargs)
        w = self.width
        self.mixers = nn.ModuleDict({
            name: MaterialSliceMixer(channels, slices, measure=measure)
            for name, channels in (("enc1", w), ("enc2", 2*w),
                                   ("bottleneck", 4*w), ("dec2", 2*w), ("dec1", w))
        })

    @staticmethod
    def _block(x, context, *, block, mixer):
        combined = block.spectral_conv(x) + block.conv_skip(x) + mixer(x, context)
        return F.gelu(block.norm(combined))

    def _stage(self, name, x, context):
        mixer = self.mixers[name]
        for block in getattr(self, name):
            # Bind block/mixer now: delayed checkpoint recomputation must NOT
            # capture a loop variable that changes after this iteration.
            op = partial(self._block, block=block, mixer=mixer)
            if block.use_checkpoint and self.training and (x.requires_grad or context.requires_grad):
                x = checkpoint(op, x, context, use_reentrant=False)
            else:
                x = op(x, context)
        return x

    def forward(self, geometry: Tensor) -> Tensor:
        raw = canonical_geometry(geometry)
        fields = material_fields(raw)
        x = self._prepare_geometry(raw)
        context1 = scale_context(fields, x.shape[-3:])
        grid = self.coordinate_grid.to(x).expand(x.shape[0], -1, -1, -1, -1)
        h1 = self._stage("enc1", self.lifting(torch.cat((x, grid), 1)), context1)
        down = self.down1(h1)
        context2 = scale_context(fields, down.shape[-3:])
        h2 = self._stage("enc2", down, context2)
        down = self.down2(h2)
        context3 = scale_context(fields, down.shape[-3:])
        bot = self._stage("bottleneck", down, context3)
        x = self.up2(bot)
        if x.shape[-3:] != h2.shape[-3:]:
            x = F.interpolate(x, size=h2.shape[-3:], mode="trilinear", align_corners=False)
        x = self._stage("dec2", self.dec2_proj(torch.cat((x, h2), 1)), context2)
        x = self.up1(x)
        if x.shape[-3:] != h1.shape[-3:]:
            x = F.interpolate(x, size=h1.shape[-3:], mode="trilinear", align_corners=False)
        x = self._stage("dec1", self.dec1_proj(torch.cat((x, h1), 1)), context1)
        return torch.cat((F.adaptive_avg_pool3d(x, 1).flatten(1),
                          F.adaptive_max_pool3d(x, 1).flatten(1),
                          F.adaptive_avg_pool3d(bot, 1).flatten(1)), dim=-1)


class MaterialAwareSpinPINO(SpinPINO):
    """Explicit P30 research entry point; baseline SpinPINO is not overwritten.

    No external geometry branch is enabled. The existing logistic positive
    quadrature head is inherited unchanged. Passing c never invokes an encoder.
    Unknown checkpoints must be matched by configuration, not strict=False.
    """
    def __init__(self, *, slices=8, measure="material", **kwargs):
        if kwargs.get("geometry_adapter", "none") != "none":
            raise ValueError("P30 isolates the in-trunk mechanism; disable external geometry adapter")
        if kwargs.get("moment_parameterization", "logistic_atom") != "logistic_atom":
            raise ValueError("P30 derivative contract currently covers logistic_atom only")
        kwargs["moment_parameterization"] = "logistic_atom"
        super().__init__(**kwargs)
        old = self.encoder
        encoder_args = {key: kwargs[key] for key in (
            "width", "modes", "n_layers", "grid_size", "use_gradient_checkpoint") if key in kwargs}
        self.encoder = MaterialPINOEncoder(slices=slices, measure=measure, **encoder_args)
        result = self.encoder.load_state_dict(old.state_dict(), strict=False)
        if result.unexpected_keys or any(not k.startswith("mixers.") for k in result.missing_keys):
            raise RuntimeError("unexpected base encoder migration mismatch")
        self.p30_config = {**kwargs, "slices": slices, "measure": measure}

    def load_baseline(self, baseline: SpinPINO) -> None:
        if baseline.geometry_adapter_name != "none" or baseline.geometry_plugin is not None:
            raise ValueError("baseline must not contain external geometry plugins")
        if baseline.moment_parameterization != "logistic_atom":
            raise ValueError("baseline must use logistic_atom")
        if (baseline.temperature != self.temperature or
                baseline.quadrature_rule != self.quadrature_rule or
                baseline.encoder.grid_size != self.encoder.grid_size):
            raise ValueError("baseline temperature/quadrature/grid configuration mismatch")
        result = self.load_state_dict(baseline.state_dict(), strict=False)
        if result.unexpected_keys or any(not k.startswith("encoder.mixers.") for k in result.missing_keys):
            raise RuntimeError("baseline state differs beyond new material-mixing parameters")
        with torch.no_grad():
            for mixer in self.encoder.mixers.values():
                mixer.gate.zero_()

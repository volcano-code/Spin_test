"""W6 M11: source-bound, explicitly budgeted analytic P0 anchor-moment cache.

This is a DECISION diagnostic, not a material moment oracle. A cached closed-
form r_D at one or two c(h) queries can correct only the 1D GN residual used
for STEP SELECTION. The corrected 10-vector MUST NOT be sold as a physically
realizable M7 material prediction or fed to a native optimizer. Only the
original M7 bounded atomic output has the M7 discrete-measure guarantee.

The oracle in this module is deliberately hardwired to the frozen independent
analytic_cut.vertical_cut_truth; no W2 archive / training admission is possible.
Neither the local geometry SHA nor a cached source digest is a native CAD seal.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import struct
from typing import Literal

import numpy as np
import torch

from .analytic_cut import GeometrySpec, TEACHER_KIND, vertical_cut_truth
from .m10_decision import native_plane_c_and_tangent
from .m6_moment_guard import physical_moment_diagnostic

POLICIES = ("baseline", "one_anchor", "two_anchors")


class CacheBindingError(ValueError):
    """A cached feature/label cannot be used against a changed source."""


class NativeLabelsUnavailable(RuntimeError):
    """W2 source is not certified; analytic P0 is the only allowed oracle."""


def _tensor_digest(x: torch.Tensor) -> str:
    if not isinstance(x, torch.Tensor) or x.device.type != "cpu" or x.requires_grad:
        raise CacheBindingError("frozen CPU input without autograd required")
    if not x.is_floating_point() or not bool(torch.isfinite(x).all()):
        raise CacheBindingError("finite floating-point input required")
    data=x.detach().contiguous().numpy()
    h=hashlib.sha256()
    h.update(str((data.shape,str(data.dtype))).encode("ascii"))
    h.update(data.tobytes())
    return h.hexdigest()


def _model_digest(model: torch.nn.Module) -> str:
    h=hashlib.sha256(b"W6_M11_FROZEN_MODEL_STATE_V1\0")
    for key,value in sorted(model.state_dict().items()):
        if value.device.type != "cpu":
            raise CacheBindingError("CPU-only M11 experiment; GPU not certified")
        a=value.detach().contiguous().numpy()
        h.update(key.encode("utf-8")+b"\0")
        h.update(str((a.shape,str(a.dtype))).encode("ascii")+b"\0")
        h.update(a.tobytes())
    return h.hexdigest()


@dataclass(frozen=True)
class AnchorObservation:
    h_local: float
    c_native: tuple[float, ...]
    r_design: tuple[float, ...]
    geometry_sha256: str
    model_sha256: str
    source: str = TEACHER_KIND


@dataclass(frozen=True)
class CorrectedDecisionInput:
    """r_for_step is NOT a released material-moment prediction."""
    r_for_step: np.ndarray
    Jc_surrogate: np.ndarray
    raw_atomic_r: np.ndarray
    correction_used: bool
    candidate_cone_check_pass: bool
    fallback_reason: str | None
    source: str = "ANALYTIC_ONLY_DECISION_CORRECTION_NOT_MATERIAL_CERTIFICATE"


class AnalyticAnchorLedger:
    """One frozen model/geometry pair with exact oracle accounting.

    Geometry encoder is called once, not each time a distinct c is proposed.
    Observations contain only r, never J; a repeated exact h costs no second
    oracle query. The caller may not inject arbitrary r or call this a native
    teacher. Guard checks the frozen model and raw D SHA before every use.
    """

    def __init__(self, model: torch.nn.Module, D: torch.Tensor, geometry: GeometrySpec):
        if not isinstance(geometry,GeometrySpec):
            raise TypeError("analytic GeometrySpec required")
        if not isinstance(D,torch.Tensor) or D.shape[0]!=1 or D.ndim!=5 or D.shape[1]!=4:
            raise CacheBindingError("one frozen [1,4,X,Y,Z] geometry required")
        self.geometry=geometry
        self.geometry_identity=geometry.geometry_id
        self.model=model.eval()
        self._geometry_digest=_tensor_digest(D)
        self._model_digest=_model_digest(model)
        self._D=D.detach().clone()
        with torch.no_grad():
            self.z=self.model.encode_geometry(self._D).detach()
        if self.z.shape[0]!=1 or not bool(torch.isfinite(self.z).all()):
            raise CacheBindingError("geometry encoder returned invalid cache")
        self.geometry_encoder_calls=1
        self.analytic_oracle_calls=0
        self.surrogate_moment_calls=0
        self.surrogate_jacobian_calls=0
        self._observations: dict[bytes,AnchorObservation]={}
        self._anchor_bias: dict[bytes,np.ndarray]={}

    def assert_bound(self, *, model=None, D=None, geometry=None) -> None:
        if (model is not None and (model is not self.model or _model_digest(model)!=self._model_digest)):
            raise CacheBindingError("model/checkpoint identity changed; re-encode")
        if _model_digest(self.model)!=self._model_digest:
            raise CacheBindingError("model weights mutated; cached z and labels invalid")
        if D is not None and _tensor_digest(D)!=self._geometry_digest:
            raise CacheBindingError("supplied D differs from bound geometry")
        if geometry is not None and geometry.geometry_id!=self.geometry_identity:
            raise CacheBindingError("geometry ID changed")
        if _tensor_digest(self._D)!=self._geometry_digest:
            raise CacheBindingError("internal D unexpectedly mutated")

    @staticmethod
    def _key(h: float) -> bytes:
        if not isinstance(h,(float,int)) or isinstance(h,bool) or not math.isfinite(float(h)) or not (-.75<float(h)<.75):
            raise ValueError("analytic anchor must be finite and strictly inside (-.75,.75)")
        return struct.pack("!d",float(h))

    def obtain_r(self,h:float, *,source: str = TEACHER_KIND) -> AnchorObservation:
        self.assert_bound()
        if source != TEACHER_KIND:
            raise NativeLabelsUnavailable("W2 Cherchi H8f 81 are excluded; no accepted native teacher seal")
        key=self._key(h)
        if key not in self._observations:
            c,r,_=vertical_cut_truth(self.geometry,float(h))
            if not (np.isfinite(r).all() and r.shape==(10,) and np.isfinite(c).all()):
                raise CacheBindingError("invalid independent analytic oracle")
            self._observations[key]=AnchorObservation(float(h),tuple(map(float,c)),
                tuple(map(float,r)),self.geometry_identity,self._model_digest)
            with torch.no_grad():
                q=torch.as_tensor(c,dtype=self.z.dtype,device=self.z.device).view(1,10)
                pred=self.model.moment(self.z,q)[0].detach().double().cpu().numpy()
            self.surrogate_moment_calls+=1
            if not np.isfinite(pred).all():
                raise CacheBindingError("nonfinite anchor model output")
            self._anchor_bias[key]=np.asarray(r,dtype=np.float64)-pred
            self.analytic_oracle_calls+=1
        return self._observations[key]

    @property
    def anchor_count(self)->int:
        return len(self._observations)

    def _neural(self,h:float)->tuple[np.ndarray,np.ndarray]:
        self.assert_bound()
        self._key(h)
        c,_=native_plane_c_and_tangent(self.geometry,float(h))
        dtype=self.z.dtype
        with torch.no_grad():
            query=torch.tensor(c,dtype=dtype,device=self.z.device).view(1,10)
            r=self.model.moment(self.z,query).detach().double().cpu().numpy()[0]
            J=self.model.jacobian(self.z,query).detach().double().cpu().numpy()[0]
        self.surrogate_moment_calls+=1
        self.surrogate_jacobian_calls+=1
        if r.shape!=(10,) or J.shape!=(10,10) or not np.isfinite(r).all() or not np.isfinite(J).all():
            raise CacheBindingError("nonfinite model r/J")
        return r,J

    def decision_input(self,h:float,policy:Literal["baseline","one_anchor","two_anchors"],
                       *,max_distance:float=.55) -> CorrectedDecisionInput:
        """Use at most policy's cached r anchors; no oracle inside selection.

        For 2 anchors use nearest-residual outside bracket, linear residual
        interpolation strictly inside. No extrapolation across unknown strata.
        If corrected r violates checked moment-cone necessary conditions,
        fall back to raw M7 output. This does NOT prove corrected r physical.
        """
        if policy not in POLICIES:raise ValueError("unknown policy")
        if not (isinstance(max_distance,(float,int)) and 0<max_distance<=1):
            raise ValueError("invalid max-distance threshold")
        pred,J=self._neural(h)
        if policy=="baseline":
            return CorrectedDecisionInput(pred,J,pred,False,True,None)
        if self.anchor_count!=(1 if policy=="one_anchor" else 2):
            raise CacheBindingError("wrong number of independently queried analytic anchors")
        obs=sorted(self._observations.values(),key=lambda a:a.h_local)
        hvals=[a.h_local for a in obs]
        if min(abs(h-v) for v in hvals)>max_distance:
            return CorrectedDecisionInput(pred,J,pred,False,True,"OUTSIDE_ANCHOR_RADIUS")
        biases=[self._anchor_bias[self._key(item.h_local)] for item in obs]
        if len(biases)==1:
            delta=biases[0]
        elif h<=hvals[0]:
            delta=biases[0]
        elif h>=hvals[1]:
            delta=biases[1]
        else:
            t=(float(h)-hvals[0])/(hvals[1]-hvals[0])
            delta=(1-t)*biases[0]+t*biases[1]
        corrected=pred+delta
        diag=physical_moment_diagnostic(torch.tensor(corrected,dtype=torch.float64).view(1,10),tol=1e-8)
        cone=bool(diag["necessary_conditions_pass"][0])
        if not cone:
            return CorrectedDecisionInput(pred,J,pred,False,False,"NONREALIZABLE_CORRECTED_DECISION_VECTOR")
        return CorrectedDecisionInput(corrected,J,pred,True,True,None)

    def receipt(self)->dict:
        self.assert_bound()
        return {"geometry_sha256":self.geometry_identity,
                "raw_D_sha256":self._geometry_digest,"model_state_sha256":self._model_digest,
                "anchors":len(self._observations),"analytic_oracle_calls":self.analytic_oracle_calls,
                "encoder_calls":self.geometry_encoder_calls,
                "surrogate_moment_calls":self.surrogate_moment_calls,
                "surrogate_jacobian_calls":self.surrogate_jacobian_calls,
                "native_W2_calls":0,"native_training_admitted":False,
                "material_moment_certified":False,
                "cache_type":"IN_MEMORY_ANALYTIC_P0_SOURCE_BOUND_PER_MODEL_GEOMETRY"}

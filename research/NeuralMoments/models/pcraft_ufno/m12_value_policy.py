"""W6 M12: no-oracle geometry-level value-of-information risk and budget gate.

This module never imports the analytic truth oracle. It receives task goals as
external ten-moment targets, geometry voxels and *surrogate-only* predictions.
For vertical positive signed cuts on the *declared cellwise proxy volume* only.
A proxy-mass discrepancy is a risk heuristic, NOT a W0/W2 native certificate.

Policy thresholds are fitted on independent analytic calibration geometries in
m12_experiment.py. `select` receives no acceptance labels, true current r/J,
or post-step values. It may purchase 0, 1, or 2 new r-only anchors per geometry.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, math
from typing import Iterable
import numpy as np
import torch


def cellwise_positive_cut_mass(D: torch.Tensor, h_world: float) -> float:
    """Known piecewise-constant cell *proxy* mass above a vertical z plane.

    Source D[B=1,4,n,n,n] is interpreted as CELL-CENTERED data on [-1,1]^3,
    unlike old linspace node-sampled D. This integral is exact only for the
    proxy rho*occupancy, never for the original CAD solid/analytic shape.
    """
    if not isinstance(D,torch.Tensor) or D.shape[:2] != (1,4) or D.ndim != 5:
        raise ValueError('requires one center-cell 4-channel volume')
    if len(set(D.shape[2:])) != 1 or min(D.shape[2:]) < 4:
        raise ValueError('cubic grid of at least four cells required')
    if D.device.type != 'cpu' or D.requires_grad or not D.is_floating_point() or not bool(torch.isfinite(D).all()):
        raise ValueError('frozen finite CPU tensor required')
    if bool((D[:,0]<0).any() or (D[:,1]<0).any() or (D[:,1]>1).any()):
        raise ValueError('density/occupancy invalid')
    if not isinstance(h_world,(int,float)) or not math.isfinite(float(h_world)):
        raise ValueError('nonfinite height')
    n=D.shape[2]
    edges=np.linspace(-1.,1.,n+1,dtype=np.float64)
    clipped=np.clip(edges[1:]-max(float(h_world),-1.),0.,2./n)
    clipped=np.where(edges[:-1]>=float(h_world),2./n,clipped)
    masses=(D[0,0].double()*D[0,1].double()).numpy()
    return float(np.sum(masses*clipped[None,None,:])*(2./n)**2)


def _signed_step(r:np.ndarray,J:np.ndarray,dc:np.ndarray,goal:np.ndarray,*,damping=.01,trust=.12)->float:
    direction=J@dc
    return float(np.clip(-(direction@(r-goal))/(direction@direction+damping),-trust,trust))


@dataclass(frozen=True)
class ObservableRisk:
    score: float
    discrepancy: float
    direction_conflict: float
    near_target_fraction: float
    target_count: int
    sensor: str='CELL_CENTER_PROXY_AND_SURROGATE_ONLY_NO_ORACLE'


def observe_risk(model, z:torch.Tensor, D:torch.Tensor,
                 native_c:np.ndarray, tangent:np.ndarray,
                 goal_r:np.ndarray, h_world:np.ndarray)->ObservableRisk:
    """Compute pre-query risk for all declared future controls of ONE geometry.

    All input goal vectors are *prescribed task targets* supplied externally.
    The function never computes teacher r/J, post-step truth or acceptance.
    The surrogate encoder is assumed to have run once to produce frozen z.
    """
    cs=np.asarray(native_c,dtype=np.float64)
    dc=np.asarray(tangent,dtype=np.float64)
    goal=np.asarray(goal_r,dtype=np.float64)
    heights=np.asarray(h_world,dtype=np.float64)
    if (cs.ndim!=2 or cs.shape[1]!=10 or dc.shape!=cs.shape or
        goal.shape!=cs.shape or heights.shape!=(len(cs),) or len(cs)<1 or
        not all(np.isfinite(x).all() for x in (cs,dc,goal,heights))):
        raise ValueError('finite [Q,10] controls, tangents, external goals required')
    if (z.ndim!=2 or z.shape[0]!=1 or z.device.type!='cpu' or
        not bool(torch.isfinite(z).all())):
        raise ValueError('one frozen cached geometry required')
    with torch.no_grad():
        controls=torch.as_tensor(cs,dtype=z.dtype)
        zz=z.expand(len(cs),-1)
        r=model.moment(zz,controls).detach().double().cpu().numpy()
        J=model.jacobian(zz,controls).detach().double().cpu().numpy()
    if r.shape!=cs.shape or J.shape!=(len(cs),10,10) or not np.isfinite(r).all() or not np.isfinite(J).all():
        raise ValueError('invalid surrogate predictions')
    disc=[];conflict=[];near=[]
    proxy_full=cellwise_positive_cut_mass(D,-2.)
    for i in range(len(cs)):
        proxy=cellwise_positive_cut_mass(D,float(heights[i]))
        denom=max(proxy_full,.03)
        disc.append(abs(float(r[i,0])-proxy)/denom)
        step=_signed_step(r[i],J[i],dc[i],goal[i])
        # For a positive vertical cut, the proxy mass is nonincreasing in h.
        # The *goal mass*, unlike true current mass, is a known task input.
        gap=proxy-float(goal[i,0])
        conflict.append(float(abs(gap)>1e-5 and abs(step)>1e-8 and (gap*step<0)))
        near.append(float(abs(gap)/denom<.035))
    discrepancy=float(np.mean(disc))
    direction_conflict=float(np.mean(conflict))
    near_target_fraction=float(np.mean(near))
    score=discrepancy+.16*direction_conflict+.035*near_target_fraction
    return ObservableRisk(score,discrepancy,direction_conflict,near_target_fraction,len(cs))


@dataclass(frozen=True)
class FrozenVOIPolicy:
    """Two thresholds and one explicit abstract query-price per candidate."""
    low:float
    high:float
    unit_query_cost:float
    calibration_geometry_sha256:str
    calibration_seed:int
    protocol:str='W6_M12_VALIDATION_ONLY_P0_NO_NATIVE'

    def __post_init__(self):
        if (not all(math.isfinite(float(x)) for x in (self.low,self.high,self.unit_query_cost))
             or self.low<0 or self.high<self.low or self.unit_query_cost<0):
            raise ValueError('invalid monotone thresholds/cost')
        if not isinstance(self.calibration_seed,int) or len(self.calibration_geometry_sha256)!=64:
            raise ValueError('missing frozen calibration identity')

    def select(self,risk:ObservableRisk)->int:
        if not isinstance(risk,ObservableRisk) or not math.isfinite(risk.score):
            raise ValueError('observable risk required')
        if risk.score<=self.low:return 0
        if risk.score<=self.high:return 1
        return 2


def calibration_identity(geometry_ids:Iterable[str])->str:
    ids=sorted(str(v) for v in geometry_ids)
    if not ids or len(set(ids))!=len(ids) or any(len(x)!=64 for x in ids):
        raise ValueError('distinct full geometry SHA-256 identities required')
    return hashlib.sha256('\n'.join(ids).encode('ascii')).hexdigest()


def select_thresholds(rows:list[dict],*,price:float,seed:int)->tuple[FrozenVOIPolicy,dict]:
    """Offline validation-only tuning, using truth *solely in calibration rows*.

    Every row represents a unique CALIBRATION geometry, supplies a no-truth
    risk score, target_count, and independent analytic acceptance for K=0/1/2.
    Selection never sees the heldout set. The calibration's oracle labels
    are development expenditure, NOT zero-cost online W2 queries.
    """
    if not rows or price<0 or not math.isfinite(price):raise ValueError('invalid calibration data/price')
    ids=[x['geometry_id'] for x in rows]
    sha=calibration_identity(ids)
    all_scores=sorted(set(float(x['risk_score']) for x in rows))
    if not all(math.isfinite(x) and x>=0 for x in all_scores):raise ValueError('invalid score')
    for row in rows:
        if (set(('geometry_id','risk_score','cases','acceptances'))-set(row) or
            int(row['cases'])<1 or len(row['acceptances'])!=3 or
            not all(isinstance(v,(float,int)) and 0<=v<=1 for v in row['acceptances'])):
            raise ValueError('malformed validation record')
    # Candidate thresholds are observed score order statistics, with all-K0
    # and all-K2 extremes. Penalize every paid oracle anchor per geometry.
    possible=[0.]+all_scores+[max(all_scores)+1.]
    best=(-float('inf'),float('inf'),0.,0.)
    ranking=[]
    for low in possible:
        for high in possible:
            if high<low:continue
            pol=FrozenVOIPolicy(low,high,price,sha,seed)
            weight=sum(row['cases'] for row in rows)
            acc=sum(row['cases']*row['acceptances'][pol.select(ObservableRisk(row['risk_score'],0,0,0,row['cases']))] for row in rows)/weight
            query_rate=sum(pol.select(ObservableRisk(row['risk_score'],0,0,0,row['cases'])) for row in rows)/weight
            utility=acc-price*query_rate
            ranking.append({'low':low,'high':high,'acceptance':acc,'calls_per_candidate':query_rate,'utility':utility})
            # Deterministic cheaper-policy tie break, no heldout access.
            if (utility, -query_rate, -high, -low)>(best[0],-best[1],-best[3],-best[2]):
                best=(utility,query_rate,low,high)
    policy=FrozenVOIPolicy(best[2],best[3],price,sha,seed)
    return policy,{'calibration_geometry_count':len(rows),'calibration_cases':sum(x['cases'] for x in rows),
        'calibration_selected_utility':best[0], 'calibration_selected_calls_per_candidate':best[1],
        'candidate_threshold_pairs':len(ranking), 'calibration_analytic_truth_evaluated':True,
        'calibration_only_not_test':True}

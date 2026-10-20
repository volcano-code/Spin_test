"""W6 M10: observable 1D analytic P0 optimization decisions and fail modes.

This is deliberately restricted to positive vertical native planes. No general
10-dimensional quadric Newton/KKT, no continuous CAD derivative admission.
All policies use the same *declared* goal r*(h+.12). For no-oracle policies,
true r at candidate is evaluation-only, NEVER used to choose the step. A
'checked_backtrack' policy explicitly counts each extra oracle evaluation;
it is not a claimed accelerated native solver.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import numpy as np
import torch

from .analytic_cut import GeometrySpec, vertical_cut_truth

STRATEGIES=('gn','predicted_backtrack','mass_sign_guard','checked_backtrack')


def native_plane_c_and_tangent(spec: GeometrySpec, h: float):
    """c(h) and dc/dh in saved native matrix-entry coefficient convention."""
    wh=spec.center[2]+spec.axes[2]*float(h)
    scale=(1+wh*wh)**1.5
    c=np.zeros(10, dtype=np.float64)
    c[0]=-wh/math.hypot(wh,1.0);c[3]=1/math.hypot(wh,1.0)
    dc=np.zeros(10,dtype=np.float64)
    dc[0]=-spec.axes[2]/scale
    dc[3]=-wh*spec.axes[2]/scale
    return c,dc


def objective(r,goal):
    a=np.asarray(r,dtype=np.float64)-np.asarray(goal,dtype=np.float64)
    if a.shape!=(10,) or not np.all(np.isfinite(a)):
        raise ValueError('ten finite moment components required')
    return .5*float(a@a)


def gn_step(r, jac, tangent, goal, *, damping=.01, trust=.12):
    """Exactly the W5 M13 1D regularized/clipped GN candidate."""
    r,jac,tangent,goal=(np.asarray(x,dtype=np.float64) for x in (r,jac,tangent,goal))
    if r.shape!=(10,) or jac.shape!=(10,10) or tangent.shape!=(10,) or goal.shape!=(10,):
        raise ValueError('r,J,dc/dh,goal shape mismatch')
    if not all(np.isfinite(x).all() for x in (r,jac,tangent,goal)):
        raise ValueError('nonfinite solver inputs')
    if not (math.isfinite(damping) and damping>0 and math.isfinite(trust) and 0<trust<=.2):
        raise ValueError('positive damping and strict trust radius required')
    direction=jac@tangent
    numerator=float(direction@(r-goal))
    denominator=float(direction@direction)+damping
    return float(np.clip(-numerator/denominator,-trust,trust))


@dataclass(frozen=True)
class DecisionRecord:
    strategy: str
    step: float
    additional_selection_oracle_calls: int
    additional_surrogate_moment_calls: int
    predicted_rejections: int
    actual_accept: bool
    actual_improvement: float
    actual_loss_before: float
    actual_loss_after: float
    oracle_step_abs_error: float
    oracle_step_objective_gap: float
    gradient_sign_wrong: bool
    direction_sign_wrong: bool
    trust_clipped: bool
    predicted_false_descent: bool


def choose_and_evaluate(spec:GeometrySpec,h:float,r_pred,j_pred,goal,*,
                        strategy:str,oracle_r=None,oracle_j=None,
                        trust=.12,damping=.01,backtrack=(1.,.5,.25,.125),
                        min_improvement=1e-12):
    """One-step validation with explicit oracle budget and failure attribution.

    oracle_r/J are supplied ONLY for retrospective diagnostic metrics, NEVER
    passed into a no-oracle policy's selection. Strict `actual_accept` uses
    independently evaluated analytic truth (evaluation-only except in checked
    backtracking). No test truth appears inside the other decision branches.
    """
    if strategy not in STRATEGIES:raise ValueError('invalid strategy')
    if not -1<h<1 or not math.isfinite(h):raise ValueError('interior h required')
    if abs(h)+trust>=1:raise ValueError('trust region crosses analytic boundary')
    if not backtrack or backtrack[0]!=1. or any(not 0<x<=1 for x in backtrack):
        raise ValueError('backtrack must begin at 1 and stay in (0,1]')
    c,dc=native_plane_c_and_tangent(spec,h)
    r_pred=np.asarray(r_pred,dtype=np.float64)
    j_pred=np.asarray(j_pred,dtype=np.float64)
    goal=np.asarray(goal,dtype=np.float64)
    initial=gn_step(r_pred,j_pred,dc,goal,trust=trust,damping=damping)
    r_true,j_true=(vertical_cut_truth(spec,h)[1:]) if oracle_r is None else (np.asarray(oracle_r),np.asarray(oracle_j))
    if oracle_r is not None and oracle_j is None:raise ValueError('oracle pair must be complete')
    true_loss=objective(r_true,goal)
    truth_step=gn_step(r_true,j_true,dc,goal,trust=trust,damping=damping)
    oracle_loss=objective(vertical_cut_truth(spec,h+truth_step)[1],goal)
    analytic_gradient=float(((r_true-goal)@(j_true@dc)))
    predicted_gradient=float(((r_pred-goal)@(j_pred@dc)))
    grad_flip=bool(predicted_gradient*analytic_gradient<0)
    direction_flip=bool(initial*truth_step<0)
    selected=initial
    extra_surrogate=0
    extra_oracle=0
    rejected=0
    if strategy=='predicted_backtrack':
        # NO truth used, even when model selects a catastrophically bad step.
        # Use the same cached z through the passed forward predictor.
        raise ValueError('use evaluate_decision with cached model for predicted_backtrack')
    if strategy=='mass_sign_guard':
        # On a nonnegative volume sliced by a positive vertical plane, mass
        # decreases with increasing h. This special-domain extra prior is
        # NOT valid for generic quadrics or unrestricted 10D geometry.
        mass_delta=float(r_pred[0]-goal[0])
        if abs(mass_delta)>1e-8:
            expected_sign=np.sign(mass_delta)
            if np.sign(selected)!=expected_sign or abs(selected)<trust*.25:
                selected=float(expected_sign*max(abs(selected),trust*.25))
        selected=float(np.clip(selected,-trust,trust))
    if strategy=='checked_backtrack':
        selected=0.
        for factor in backtrack:
            step=initial*float(factor)
            if abs(step)<1e-12:break
            proposed=vertical_cut_truth(spec,h+step)[1]
            extra_oracle+=1
            if objective(proposed,goal)<true_loss-min_improvement:
                selected=step
                break
            rejected+=1
    truth_after=objective(vertical_cut_truth(spec,h+selected)[1],goal)
    predicted_improvement=bool(predicted_gradient*selected<0)
    return DecisionRecord(strategy,float(selected),extra_oracle,extra_surrogate,
          rejected,bool(truth_after<true_loss-min_improvement),float(true_loss-truth_after),
          float(true_loss),float(truth_after),abs(float(selected-truth_step)),
          float(truth_after-oracle_loss),grad_flip,direction_flip,
          abs(initial)>=trust-1e-10,bool(predicted_improvement and truth_after>=true_loss-min_improvement))


def predicted_backtrack_decision(spec:GeometrySpec,h:float,z,model,goal,*,
                                 trust=.12,damping=.01,backtrack=(1.,.5,.25,.125)):
    """Surrogate-only selection + independent truth measured only afterwards."""
    c,dc=native_plane_c_and_tangent(spec,h)
    tensor_c=torch.as_tensor(c,dtype=z.dtype,device=z.device).reshape(1,10)
    with torch.no_grad():
        r_pred=model.moment(z,tensor_c).reshape(-1).detach().double().cpu().numpy()
        j_pred=model.jacobian(z,tensor_c).reshape(10,10).detach().double().cpu().numpy()
    initial=gn_step(r_pred,j_pred,dc,goal,trust=trust,damping=damping)
    baseline_pred_loss=objective(r_pred,goal)
    selected=0.
    extra_surrogate=0;rejected=0
    with torch.no_grad():
        for factor in backtrack:
            trial=initial*float(factor)
            if abs(trial)<1e-12:break
            new_c=native_plane_c_and_tangent(spec,h+trial)[0]
            next_pred=model.moment(z,torch.as_tensor(new_c,dtype=z.dtype,device=z.device).view(1,10))
            extra_surrogate+=1
            if objective(next_pred.reshape(-1).detach().double().cpu().numpy(),goal)<baseline_pred_loss-1e-12:
                selected=trial
                break
            rejected+=1
    baseline=choose_and_evaluate(spec,h,r_pred,j_pred,goal,strategy='gn',trust=trust,damping=damping)
    true_loss=baseline.actual_loss_before
    actual_after=objective(vertical_cut_truth(spec,h+selected)[1],goal)
    oracle_r,oracle_j=vertical_cut_truth(spec,h)[1:]
    oracle_step=gn_step(oracle_r,oracle_j,dc,goal,trust=trust,damping=damping)
    oracle_post=objective(vertical_cut_truth(spec,h+oracle_step)[1],goal)
    return DecisionRecord('predicted_backtrack',float(selected),0,extra_surrogate,
       rejected,bool(actual_after<true_loss-1e-12),float(true_loss-actual_after),
       true_loss,float(actual_after),abs(float(selected-oracle_step)),
       float(actual_after-oracle_post),baseline.gradient_sign_wrong,
       baseline.direction_sign_wrong,baseline.trust_clipped,
       bool(selected and actual_after>=true_loss-1e-12))

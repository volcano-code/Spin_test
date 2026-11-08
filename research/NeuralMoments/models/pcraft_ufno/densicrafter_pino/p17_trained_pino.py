"""P17: DensiCrafter material design coupled to a genuinely trained 64^3 PINO.

The 64^3 P-CRAFT PINO is loaded from the P14 Actions artifact and frozen.
Only density logits are optimized. The four arms compare Densi-only,
PINO-only, soft joint, and independently feasible joint material design.
All acceptance checks use an independent cell-centered hard-cut moment
integral in addition to the trained PINO prediction.
"""
from __future__ import annotations
import argparse,json,resource,time
from pathlib import Path
import torch
import torch.nn.functional as F

from ..analytic_cut import sample_dataset
from ..spin_pino.spin_pino import SpinPINO
from ..densicrafter_pino.bridge import (
    DensiCrafterSpinPINOBridge,material_moments,
)
from ..densicrafter_pino.p13b_highres import exact_discrete_cut_moments


def _surface_masks(occupancy:torch.Tensor,wall_cells=2):
    if occupancy.ndim!=5 or occupancy.shape[1]!=1:
        raise ValueError("occupancy must be [B,1,X,Y,Z]")
    if wall_cells<1:
        raise ValueError("wall_cells must be positive")
    occ=occupancy.bool()
    interior=occ
    for _ in range(wall_cells):
        padded=F.pad(interior.float(),(1,1,1,1,1,1),value=0.)
        outside=F.max_pool3d(1.-padded,kernel_size=3,stride=1)
        interior=interior & (outside<.5)
    shell=occ & ~interior
    design=interior
    if not bool(shell.any()) or not bool(design.any()):
        raise ValueError("solid too small for selected protected shell")
    if bool((shell&design).any()) or not bool((shell|design).equal(occ)):
        raise AssertionError("surface mask partition failure")
    return shell,design


def _normalised_material_moments(rho):
    m=material_moments(rho)
    return m[:,1:]/m[:,:1].clamp_min(1e-8)


def _relative(a,b):
    return float((a-b).norm()/b.norm().clamp_min(1e-8))


def _feasibility(model,c,model_ref,cut_ref,normal_ref,tolerances):
    with torch.no_grad():
        out=model(c)
        independent=exact_discrete_cut_moments(out["density"],c)
        norm=_normalised_material_moments(out["density"])
        metrics={
            "model_r_rel":_relative(out["moments"],model_ref),
            "independent_cut_r_rel":_relative(independent,cut_ref),
            "normalized_material_9moment_l2":float((norm-normal_ref).norm()),
        }
        ok=all(metrics[k] <= v+1e-8 for k,v in tolerances.items())
        return ok,metrics


def _run_arm(pino,shell,design,c,model_ref,cut_ref,norm_ref,arm,
             steps,lr,tolerances):
    model=DensiCrafterSpinPINOBridge(
        pino,shell,design,gravity_axis=2,smoothing=False
    )
    # Start at nearly full-density solid, matching the P14 PINO training
    # occupancy-density distribution; shell remains exactly 1.
    with torch.no_grad():
        model.density_logits.fill_(4.0)
    if arm=="densicrafter_only":
        weights={"mass":1.,"com_contact":.2,"negative_contact_area":.02,
                 "com_height":.05,"cut_moment_error":0.}
    elif arm=="pino_only":
        weights={"mass":0.,"com_contact":0.,"negative_contact_area":0.,
                 "com_height":0.,"cut_moment_error":25.}
    else:
        weights={"mass":1.,"com_contact":.2,"negative_contact_area":.02,
                 "com_height":.05,"cut_moment_error":25.}
    with torch.no_grad():
        initial=model(c,reference_cut_moments=model_ref,weights=weights)
        mass0=float(initial["full_material_moments"][0,0])
        loss0=float(initial["loss"])
    accepted=0;rejected=0
    start=time.perf_counter()
    if arm!="pino_only":
        optimizer=torch.optim.Adam([model.density_logits],lr=lr)
        for _ in range(steps):
            out=model(c,reference_cut_moments=model_ref,weights=weights)
            optimizer.zero_grad(set_to_none=True)
            out["loss"].backward()
            grad=model.density_logits.grad
            if grad is None or not bool(torch.isfinite(grad).all()):
                raise FloatingPointError("invalid material design gradient")
            before=model.density_logits.detach().clone()
            optimizer.step()
            if arm=="feasible_joint":
                proposal=model.density_logits.detach().clone()
                admitted=False
                for backtrack in range(10):
                    alpha=2.**(-backtrack)
                    with torch.no_grad():
                        model.density_logits.copy_(before+(proposal-before)*alpha)
                    good,_=_feasibility(model,c,model_ref,cut_ref,norm_ref,tolerances)
                    if good:
                        accepted+=1;admitted=True;break
                if not admitted:
                    with torch.no_grad():
                        model.density_logits.copy_(before)
                    rejected+=1
    elapsed=time.perf_counter()-start
    with torch.no_grad():
        final=model(c,reference_cut_moments=model_ref,weights=weights)
        independent=exact_discrete_cut_moments(final["density"],c)
        normal=_normalised_material_moments(final["density"])
        mass1=float(final["full_material_moments"][0,0])
        good,metrics=_feasibility(model,c,model_ref,cut_ref,norm_ref,tolerances)
        com_shift=float((final["com"]-initial["com"]).norm())
        shell_ok=bool((final["density"][shell]==1.).all())
        if not shell_ok: raise AssertionError("protected shell changed")
        if arm=="feasible_joint" and not good:
            raise AssertionError("independent hard constraints violated")
        return {
            "arm":arm,"steps":steps if arm!="pino_only" else 0,
            "initial_loss":loss0,"final_loss":float(final["loss"]),
            "mass_initial":mass0,"mass_final":mass1,
            "mass_reduction_fraction":1.-mass1/max(mass0,1e-8),
            "model_cut_moment_relative_error":metrics["model_r_rel"],
            "independent_hard_cut_relative_error":metrics["independent_cut_r_rel"],
            "normalized_material_9moment_l2":metrics["normalized_material_9moment_l2"],
            "center_of_mass_shift":com_shift,
            "feasible_under_predeclared_tolerances":good,
            "accepted_steps":accepted if arm=="feasible_joint" else None,
            "rejected_steps":rejected if arm=="feasible_joint" else None,
            "outer_shell_preserved":shell_ok,
            "native_Cherchi_J_admitted":False,
            "seconds":elapsed,
            "final_density":final["density"].detach().cpu(),
            "final_independent_cut":independent.detach().cpu(),
            "final_material_moments":final["full_material_moments"].detach().cpu(),
        }


def run(*,checkpoint_dir,seed=271,steps=12,lr=.06,wall_cells=2):
    torch.set_num_threads(1)
    ckpt=Path(checkpoint_dir)/f"w6_p14_grid64_seed{seed}.pt"
    if not ckpt.is_file(): raise FileNotFoundError(ckpt)
    pkg=torch.load(ckpt,map_location="cpu",weights_only=False)
    if pkg.get("seed")!=seed or pkg.get("grid_size")!=64:
        raise ValueError("wrong P14 checkpoint identity")
    pino=SpinPINO(width=8,modes=4,n_layers=4,grid_size=64,
        points_per_axis=8,hidden_dim=48,smoothing=.04,
        moment_parameterization="logistic_atom",temperature=.12,
        geometry_adapter="none").eval()
    pino.load_state_dict(pkg["state_dict"],strict=True)
    for param in pino.parameters(): param.requires_grad_(False)

    data=sample_dataset(("sphere",),per_family=1,seed=seed+707,
                        grid_size=64,queries_per_geometry=1)
    D,c,_,_,meta=data
    occupancy=D[:,1:2]>0
    shell,design=_surface_masks(occupancy,wall_cells=wall_cells)
    baseline=DensiCrafterSpinPINOBridge(
        pino,shell,design,gravity_axis=2,smoothing=False
    )
    with torch.no_grad():
        baseline.density_logits.fill_(4.)
        init=baseline(c)
        model_ref=init["moments"].detach().clone()
        cut_ref=exact_discrete_cut_moments(init["density"],c).detach().clone()
        norm_ref=_normalised_material_moments(init["density"]).detach().clone()
    tolerances={"model_r_rel":.02,"independent_cut_r_rel":.02,
                "normalized_material_9moment_l2":.02}
    rows=[]
    for arm in ("densicrafter_only","pino_only","soft_joint","feasible_joint"):
        rows.append(_run_arm(pino,shell,design,c,model_ref,cut_ref,norm_ref,
                             arm,steps,lr,tolerances))
    save={}
    for row in rows:
        density=row.pop("final_density")
        cut=row.pop("final_independent_cut")
        moments=row.pop("final_material_moments")
        save[row["arm"]]={"density":density,"independent_cut":cut,
                          "material_moments":moments}
    artifact=Path(f"/tmp/w6_p17_densicrafter_pino64_seed{seed}.pt")
    torch.save({"seed":seed,"resolution":64,"pino_grid":64,
        "source_checkpoint":str(ckpt),"wall_cells":wall_cells,
        "geometry_id":meta[0]["geometry_id"],"coefficient":c,
        "arms":save,"source":"P14_ANALYTIC_P0_NOT_W2_CHERCHI"},artifact)
    return {
        "schema":"W6_P17_TRAINED64_PINO_DENSICRAFTER_COUPLING_V1",
        "seed":seed,"resolution":64,"PINO_internal_Fourier_grid":64,
        "PINO_source":"P14 trained 64^3 seed checkpoint",
        "all_PINO_parameters_frozen":True,
        "DensiCrafter_density_logits_trainable":True,
        "geometry_family":"sphere","geometry_id":meta[0]["geometry_id"],
        "wall_cells":wall_cells,"protected_shell_cells":int(shell.sum()),
        "design_cells":int(design.sum()),"queries":1,
        "reference_model_moments":model_ref[0].tolist(),
        "reference_independent_cut_moments":cut_ref[0].tolist(),
        "predeclared_tolerances":tolerances,
        "results":rows,"artifact":str(artifact),
        "peak_process_ru_maxrss_kib":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claims":{"trained_PINO_used":True,"DensiCrafter_original_loss_core":True,
            "independent_voxel_hard_cut_checked":True,
            "continuum_Cherchi":False,"mechanical_strength_FEM":False,
            "native_Newton_admitted":False,"512_cube":False},
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--seed",type=int,default=271)
    p.add_argument("--steps",type=int,default=12)
    p.add_argument("--lr",type=float,default=.06)
    p.add_argument("--wall-cells",type=int,default=2)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=run(checkpoint_dir=a.checkpoint_dir,seed=a.seed,steps=a.steps,
          lr=a.lr,wall_cells=a.wall_cells)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps([{k:v for k,v in x.items() if k!="history"} for x in r["results"]],indent=2))


if __name__=="__main__":
    main()

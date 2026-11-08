"""P18: three-seed independent geometry confirmation of trained-PINO DensiCrafter design."""
from __future__ import annotations
import argparse,json,statistics
from pathlib import Path
from .p17_trained_pino import run as run_one


def run(*,checkpoint_dir,seeds=(271,277,281),steps=12,lr=.06,wall_cells=2):
    results=[]
    for seed in seeds:
        results.append(run_one(checkpoint_dir=checkpoint_dir,seed=seed,
                               steps=steps,lr=lr,wall_cells=wall_cells))
    for r in results:
        if not r["claims"]["trained_PINO_used"]:
            raise AssertionError("not a trained PINO checkpoint")
        if not r["claims"]["independent_voxel_hard_cut_checked"]:
            raise AssertionError("independent hard cut missing")
        feasible=next(x for x in r["results"] if x["arm"]=="feasible_joint")
        if not feasible["feasible_under_predeclared_tolerances"]:
            raise AssertionError("feasible joint design violated independent tolerance")
        if not feasible["outer_shell_preserved"]:
            raise AssertionError("protected shell was not preserved")
    def mean(arm,key):
        return statistics.mean(next(x for x in r["results"] if x["arm"]==arm)[key]
                               for r in results)
    return {
        "schema":"W6_P18_THREE_SEED_TRAINED64_PINO_DENSICRAFTER_CONFIRMATION_V1",
        "seeds":list(seeds),"resolution":64,"PINO_internal_Fourier_grid":64,
        "steps_per_arm":steps,"learning_rate":lr,"wall_cells":wall_cells,
        "independent_geometry_per_seed":True,
        "predeclared_tolerances":{"model_r_rel":.02,
            "independent_cut_r_rel":.02,"normalized_material_9moment_l2":.02},
        "aggregate":{
            "mean_feasible_joint_mass_reduction":mean("feasible_joint","mass_reduction_fraction"),
            "mean_feasible_joint_model_cut_error":mean("feasible_joint","model_cut_moment_relative_error"),
            "mean_feasible_joint_independent_cut_error":mean("feasible_joint","independent_hard_cut_relative_error"),
            "mean_feasible_joint_normalized_9moment_l2":mean("feasible_joint","normalized_material_9moment_l2"),
            "mean_densicrafter_only_mass_reduction":mean("densicrafter_only","mass_reduction_fraction"),
        },
        "per_seed":results,
        "claims":{"trained_PINO_checkpoints_used":True,
            "DensiCrafter_density_logits_optimized":True,
            "continuous_Cherchi":False,"FEM_strength":False,
            "millimeter_wall_certified":False,"native_Newton_admitted":False,
            "512_cube":False},
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--seeds",default="271,277,281")
    p.add_argument("--steps",type=int,default=12)
    p.add_argument("--lr",type=float,default=.06)
    p.add_argument("--wall-cells",type=int,default=2)
    p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=run(checkpoint_dir=a.checkpoint_dir,
          seeds=tuple(int(x) for x in a.seeds.split(",")),
          steps=a.steps,lr=a.lr,wall_cells=a.wall_cells)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(r["aggregate"],indent=2,sort_keys=True))


if __name__=="__main__":
    main()

from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
from .p19_native128_design import run as run_p19

def run(*,checkpoint_dir,seed,steps=6,lr=.06,wall_cells=4):
    source=Path(checkpoint_dir)/f"w6_p14_grid64_seed{seed}.pt"
    if not source.is_file(): raise FileNotFoundError(source)
    source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    r=run_p19(checkpoint_dir=checkpoint_dir,seed=seed,steps=steps,lr=lr,wall_cells=wall_cells)
    f=next(x for x in r["results"] if x["arm"]=="feasible_joint")
    if not f["feasible_under_predeclared_tolerances"] or not f["outer_shell_preserved"]:
        raise AssertionError(f"seed {seed}: final independent screen failed")
    if f["accepted_steps"]+f["rejected_steps"]!=steps: raise AssertionError("step accounting mismatch")
    return {"schema":"W6_P20_NATIVE128_THREE_SEED_CONFIRMATION_V1","seed":seed,
      "source_checkpoint_sha256":source_sha,"source_resolution":64,"target_input_and_fourier_grid":128,
      "PINO":"P-CRAFT SpinPINO factorized F-FNO/U-FNO","PINO_parameters_frozen":True,
      "DensiCrafter_density_logits_trainable":True,"wall_cells":wall_cells,
      "steps_per_active_arm":steps,"learning_rate":lr,"geometry_id":r["geometry_id"],
      "protected_shell_cells":r["protected_shell_cells"],"design_cells":r["design_cells"],
      "peak_process_ru_maxrss_kib":r["peak_process_ru_maxrss_kib"],
      "predeclared_tolerances":r["predeclared_tolerances"],"arms":r["results"],
      "feasible_joint":{"mass_reduction_fraction":f["mass_reduction_fraction"],
        "model_cut_moment_relative_error":f["model_cut_moment_relative_error"],
        "independent_hard_cut_relative_error":f["independent_hard_cut_relative_error"],
        "normalized_material_9moment_l2":f["normalized_material_9moment_l2"],
        "accepted_steps":f["accepted_steps"],"rejected_steps":f["rejected_steps"],
        "feasible":f["feasible_under_predeclared_tolerances"],
        "outer_shell_preserved":f["outer_shell_preserved"]},
      "density_checkpoint":r["checkpoint"],
      "claims":{"native_128_input_and_Fourier_grid":True,"trained_PINO_strictly_transferred":True,
        "independent_hard_cut_screen":True,"Cherchi":False,"FEM":False,"millimeter_wall":False,"512_cube":False}}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--checkpoint-dir",type=Path,required=True)
    p.add_argument("--seed",type=int,required=True,choices=(271,277,281))
    p.add_argument("--steps",type=int,default=6);p.add_argument("--lr",type=float,default=.06)
    p.add_argument("--wall-cells",type=int,default=4);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args()
    r=run(checkpoint_dir=a.checkpoint_dir,seed=a.seed,steps=a.steps,lr=a.lr,wall_cells=a.wall_cells)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(r["feasible_joint"],indent=2,sort_keys=True))
if __name__=="__main__": main()

from __future__ import annotations
import argparse,json,statistics
from pathlib import Path

def aggregate(input_dir):
    root=Path(input_dir);rows=[]
    for seed in (271,277,281):
        path=root/f"w6_p20_native128_seed{seed}.json"
        if not path.is_file(): raise FileNotFoundError(path)
        d=json.loads(path.read_text())
        if d.get("seed")!=seed or d.get("target_input_and_fourier_grid")!=128: raise ValueError("provenance mismatch")
        f=d["feasible_joint"]
        if not f["feasible"] or not f["outer_shell_preserved"]: raise AssertionError(f"seed {seed} failed screen")
        if f["accepted_steps"]+f["rejected_steps"]!=d["steps_per_active_arm"]: raise AssertionError("step count mismatch")
        rows.append(d)
    def stats(key):
        v=[float(r["feasible_joint"][key]) for r in rows]
        return {"mean":statistics.mean(v),"std_population":statistics.pstdev(v),"min":min(v),"max":max(v)}
    return {"schema":"W6_P20_NATIVE128_THREE_SEED_AGGREGATE_V1","seeds":[271,277,281],
      "independent_geometry_per_seed":True,"resolution":128,"input_and_internal_Fourier_grid":128,
      "steps_per_active_arm":rows[0]["steps_per_active_arm"],"learning_rate":rows[0]["learning_rate"],
      "aggregate":{"mass_reduction_fraction":stats("mass_reduction_fraction"),
        "model_cut_moment_relative_error":stats("model_cut_moment_relative_error"),
        "independent_hard_cut_relative_error":stats("independent_hard_cut_relative_error"),
        "normalized_material_9moment_l2":stats("normalized_material_9moment_l2"),
        "accepted_steps_total":sum(r["feasible_joint"]["accepted_steps"] for r in rows),
        "rejected_steps_total":sum(r["feasible_joint"]["rejected_steps"] for r in rows),
        "all_seeds_feasible":all(r["feasible_joint"]["feasible"] for r in rows),
        "all_shells_preserved":all(r["feasible_joint"]["outer_shell_preserved"] for r in rows)},
      "per_seed":[{"seed":r["seed"],"geometry_id":r["geometry_id"],
        "source_checkpoint_sha256":r["source_checkpoint_sha256"],"feasible_joint":r["feasible_joint"],
        "peak_process_ru_maxrss_kib":r["peak_process_ru_maxrss_kib"]} for r in rows],
      "claims":{"trained_PINO_native128":True,"DensiCrafter_native128":True,
        "independent_voxel_hard_cut":True,"Cherchi":False,"FEM":False,
        "millimeter_wall":False,"native_Newton":False,"512_cube":False}}

def main():
    p=argparse.ArgumentParser();p.add_argument("--input-dir",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True);a=p.parse_args()
    r=aggregate(a.input_dir);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True,allow_nan=False)+"\n")
    print(json.dumps(r["aggregate"],indent=2,sort_keys=True))
if __name__=="__main__": main()

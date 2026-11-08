import argparse,json,statistics
from pathlib import Path
EXPECTED=((271,883),(277,887),(281,991))
def aggregate(input_dir):
 root=Path(input_dir);rows=[]
 for ps,ts in EXPECTED:
  p=root/f"w6_p23_quadrann_pino{ps}_seed{ts}.json"
  if not p.is_file(): raise FileNotFoundError(p)
  d=json.loads(p.read_text())
  if d.get("pino_source_seed")!=ps or d.get("training_seed")!=ts: raise ValueError(f"seed provenance mismatch: {p}")
  if d.get("pino_parameters_frozen") is not True or d.get("zero_gate_exact_pino_parity") is not True: raise ValueError("PINO parity/frozen contract missing")
  b=d["baseline_pino"]["heldout"];q=d["quadrann_enhanced"]["heldout"]
  if b["negative_mass_fraction"]!=0 or q["negative_mass_fraction"]!=0: raise AssertionError("negative mass")
  rows.append(d)
 def stat(k):
  v=[float(d["improvement"][k]) for d in rows]
  return {"mean":statistics.mean(v),"std_population":statistics.pstdev(v),"min":min(v),"max":max(v)}
 rg=all(d["improvement"]["heldout_r_relative_l2_fraction"]>0 for d in rows)
 jg=all(d["improvement"]["heldout_J_relative_l2_fraction"]>0 for d in rows)
 repeat=rg and jg
 return {"schema":"W6_P23_QUADRANN_THREE_SOURCE_SEED_CONFIRMATION_V1",
  "pino_source_seeds":[271,277,281],"quadrann_training_seeds":[883,887,991],
  "upstream":"kesmarag/QuadrANN@111dd611aaeac1fb98c76385706b003ea8ef94be","license":"MIT",
  "primary_backbone":"P-CRAFT SpinPINO factorized F-FNO/U-FNO",
  "aggregate":{"heldout_r_relative_l2_fraction_improvement":stat("heldout_r_relative_l2_fraction"),
   "heldout_J_relative_l2_fraction_improvement":stat("heldout_J_relative_l2_fraction"),
   "all_three_improve_r":rg,"all_three_improve_J":jg,"repeatable_both_metric_gain":repeat},
  "per_seed":[{"pino_source_seed":d["pino_source_seed"],"training_seed":d["training_seed"],
   "source_checkpoint_sha256":d["pino_source_checkpoint_sha256"],
   "baseline_heldout":d["baseline_pino"]["heldout"],"quadrann_heldout":d["quadrann_enhanced"]["heldout"],
   "relative_improvement":d["improvement"],"gate":d["quadrann_gate_selected"],
   "best_validation_step":d["best_validation_step"],"training_seconds":d["training_seconds"]} for d in rows],
  "decision":"RETAIN_AS_REPEATABLE_OPTIONAL_AUXILIARY" if repeat else "KEEP_OPTIONAL_NO_PROMOTION",
  "claims":{"PINO_remains_primary":True,"QuadrANN_optional":True,"production_default":False,
   "Newton_admitted":False,"Cherchi_admitted":False}}
def main():
 p=argparse.ArgumentParser();p.add_argument("--input-dir",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 d=aggregate(a.input_dir);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(d,indent=2,sort_keys=True,allow_nan=False)+"\n")
 print(json.dumps(d["aggregate"],indent=2,sort_keys=True))
if __name__=="__main__":main()

"""The audit must never promote untrained weights to W2/native proof."""
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from research.NeuralMoments.models.deeponet.m6_budget_audit import run_audit


def test_small_audit_schema_counts_cost_and_fallback():
    x=run_audit(seeds=(7,),heights=(0.25,),w2_manifest={
        "schema":"w2-cherchi-teacher-v1-pre-w0", "status":"ADAPTER_SMOKE_ONLY",
        "native_teacher_runs":0,"training_samples":0})
    assert x["schema"]=="W5_M6_ANALYTIC_P0_BUDGET_AUDIT_V1"
    assert x["w2_gate"]["teacher_training_admissible"] is False
    assert x["environment"]["native_cherchi_executions"]==0
    assert x["design"]["model_weights"]=="RANDOM_UNTRAINED_ONLY"
    assert x["design"]["candidate_commit_performed"] is False
    assert len(x["cases"])==6
    assert {k:v["cases"] for k,v in x["summary"].items()}=={
        "exact_analytic_prediction":1,"controlled_noise":1,
        "reversed_derivative":1,"zero_derivative":1,
        "random_untrained_deeponet":1,"random_untrained_geometry_mlp":1}
    for record in x["cases"]:
        assert record["result"]["truth_calls"]<=4
        assert record["result"]["native_cherchi_calls"]==0
        assert record["result"]["requires_external_commit"]
        assert record["result"]["loss_after"]<=record["result"]["loss_before"]+1e-12
    # Audits are serializable and carry no tensors or network secrets.
    json.dumps(x, allow_nan=False)

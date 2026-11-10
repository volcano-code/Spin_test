"""P26.0: audit measured PINO + UQNO + exact-fallback wall time.

Consumes paired measured timings; never fabricates Cherchi or PINO latency.
Every sample includes an exact-reference timing for a fair exact-only baseline.
"""
from __future__ import annotations
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

ALLOWED_EXACT_BACKENDS = {"cherchi", "voxel_hardcut"}

def _positive_ms(row, key):
    value = float(row[key])
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{key} must be finite and non-negative")
    return value

def _percentile(values, q):
    ordered = sorted(float(v) for v in values)
    index = min(len(ordered)-1, max(0, math.ceil(q*len(ordered))-1))
    return ordered[index]

def _summarize(rows):
    if not rows:
        raise ValueError("cannot summarize an empty timing group")
    hybrid, exact_reference, pino_only = [], [], []
    fallback_count = 0
    for row in rows:
        pino_ms = _positive_ms(row, "pino_ms")
        uqno_ms = _positive_ms(row, "uqno_ms")
        exact_ref_ms = _positive_ms(row, "exact_reference_ms")
        if row.get("fallback_used"):
            fallback_count += 1
            exact_ms = _positive_ms(row, "exact_ms")
        else:
            exact_ms = 0.0
        hybrid.append(pino_ms + uqno_ms + exact_ms)
        exact_reference.append(exact_ref_ms)
        pino_only.append(pino_ms)
    mean_hybrid = statistics.fmean(hybrid)
    mean_exact = statistics.fmean(exact_reference)
    return {
        "sample_count": len(rows),
        "fallback_count": fallback_count,
        "fallback_fraction": fallback_count / len(rows),
        "mean_pino_ms": statistics.fmean(pino_only),
        "mean_total_pipeline_ms": mean_hybrid,
        "p50_total_pipeline_ms": _percentile(hybrid, .50),
        "p95_total_pipeline_ms": _percentile(hybrid, .95),
        "mean_exact_reference_ms": mean_exact,
        "mean_pino_only_ms": statistics.fmean(pino_only),
        "speedup_vs_exact_only": mean_exact / mean_hybrid if mean_hybrid > 0 else None,
        "decision": "MEASURED_COST_ONLY_NOT_PRODUCTION_ADMISSION",
    }

def audit(rows):
    if not rows:
        raise ValueError("timing ledger is empty")
    groups, seen = defaultdict(list), set()
    for row in rows:
        sample_id = str(row.get("sample_id", "")).strip()
        if not sample_id or sample_id in seen:
            raise ValueError("sample_id must be non-empty and unique")
        seen.add(sample_id)
        backend = row.get("exact_backend")
        provenance = str(row.get("exact_provenance", "")).strip()
        if backend not in ALLOWED_EXACT_BACKENDS or not provenance:
            raise ValueError("every sample requires explicit exact backend and provenance")
        groups[backend].append(row)
    return {
        "schema": "W6_P26_RUNTIME_COST_AUDIT_V1",
        "sample_count": len(rows),
        "backend_groups": {name: _summarize(group) for name, group in sorted(groups.items())},
        "claims": {
            "paired_measured_wall_time_only": True,
            "PINO_is_primary": True,
            "Cherchi_claim_requires_backend_tag_and_provenance": True,
            "production_gate_approved": False,
        },
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text().splitlines() if line.strip()]
    result = audit(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()

"""P26.0: audit measured PINO + UQNO + exact-fallback wall time.

This module deliberately consumes measured per-query timings. It does not
invent model latency or simulate a Cherchi backend. Exact backend provenance
must be explicit for every fallback sample.
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
    if not values:
        return None
    ordered = sorted(float(v) for v in values)
    index = min(len(ordered)-1, max(0, math.ceil(q*len(ordered))-1))
    return ordered[index]


def _summarize(rows):
    if not rows:
        raise ValueError("cannot summarize an empty timing group")
    total = []
    exact_only = []
    pino_only = []
    fallback_count = 0
    for row in rows:
        pino_ms = _positive_ms(row, "pino_ms")
        uqno_ms = _positive_ms(row, "uqno_ms")
        exact_ms = _positive_ms(row, "exact_ms") if row.get("fallback_used") else 0.0
        if row.get("fallback_used"):
            fallback_count += 1
            backend = row.get("exact_backend")
            provenance = str(row.get("exact_provenance", "")).strip()
            if backend not in ALLOWED_EXACT_BACKENDS or not provenance:
                raise ValueError("fallback sample requires explicit exact backend and provenance")
        total.append(pino_ms + uqno_ms + exact_ms)
        exact_only.append(exact_ms if row.get("fallback_used") else None)
        pino_only.append(pino_ms)
    exact_samples = [x for x in exact_only if x is not None]
    mean_total = statistics.fmean(total)
    mean_exact = statistics.fmean(exact_samples) if exact_samples else None
    return {
        "sample_count": len(rows),
        "fallback_count": fallback_count,
        "fallback_fraction": fallback_count / len(rows),
        "mean_pino_ms": statistics.fmean(pino_only),
        "mean_total_pipeline_ms": mean_total,
        "p50_total_pipeline_ms": _percentile(total, .50),
        "p95_total_pipeline_ms": _percentile(total, .95),
        "mean_exact_fallback_ms_when_used": mean_exact,
        "mean_pino_only_ms": statistics.fmean(pino_only),
        "speedup_vs_exact_only": (
            mean_exact / mean_total if mean_exact is not None and mean_total > 0 else None
        ),
        "decision": "MEASURED_COST_ONLY_NOT_PRODUCTION_ADMISSION",
    }


def audit(rows):
    if not rows:
        raise ValueError("timing ledger is empty")
    groups = defaultdict(list)
    seen = set()
    for row in rows:
        sample_id = str(row.get("sample_id", "")).strip()
        if not sample_id or sample_id in seen:
            raise ValueError("sample_id must be non-empty and unique")
        seen.add(sample_id)
        backend = row.get("exact_backend", "none")
        if row.get("fallback_used"):
            if backend not in ALLOWED_EXACT_BACKENDS:
                raise ValueError(f"unsupported or mislabeled exact backend: {backend}")
            groups[backend].append(row)
        else:
            groups["no_fallback"].append(row)
    return {
        "schema": "W6_P26_RUNTIME_COST_AUDIT_V1",
        "sample_count": len(rows),
        "backend_groups": {
            backend: _summarize(group) for backend, group in sorted(groups.items())
        },
        "claims": {
            "measured_wall_time_only": True,
            "PINO_is_primary": True,
            "Cherchi_claim_requires_backend_tag_and_provenance": True,
            "production_gate_approved": False,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True,
                        help="JSONL with measured pino_ms, uqno_ms, fallback_used and exact_ms/provenance")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [json.loads(line) for line in args.input.read_text().splitlines() if line.strip()]
    result = audit(rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

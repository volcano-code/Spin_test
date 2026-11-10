"""Validate the planned P29 generation task manifest; does not claim assets exist."""
from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path

EXPECTED = {
    "trellis_v1": 30,
    "trellis2": 20,
    "procedural_cad": 20,
    "public_cad": 20,
    "adversarial_topology": 10,
}


def validate(document):
    if document.get("schema") != "W6_P29_1_GENERATION_TASKS_V1":
        raise ValueError("unsupported generation task schema")
    if document.get("status") != "planned_not_generated":
        raise ValueError("task manifest must explicitly remain planned_not_generated")
    tasks = document.get("tasks")
    if not isinstance(tasks, list) or len(tasks) != 100:
        raise ValueError("expected exactly 100 planned candidates")
    ids = [x.get("task_id") for x in tasks]
    if len(set(ids)) != len(ids) or any(not x for x in ids):
        raise ValueError("task_id values must be unique and non-empty")
    counts = Counter(x.get("source_type") for x in tasks)
    if dict(counts) != EXPECTED:
        raise ValueError(f"source count mismatch: {dict(counts)}")
    for task in tasks:
        for key in ("lineage_id", "generation_brief", "candidate_class",
                    "geometry_focus", "expected_topology"):
            if not task.get(key):
                raise ValueError(f"{task.get('task_id')}: missing {key}")
        if task.get("status") != "planned":
            raise ValueError(f"{task['task_id']}: unexpected status")
        if task.get("physical_label_status") != "pending":
            raise ValueError(f"{task['task_id']}: physical labels must remain pending")
        if task.get("source_type") in {"trellis_v1", "trellis2"}:
            gen = task.get("generator", {})
            if gen.get("seed") is None:
                raise ValueError(f"{task['task_id']}: missing deterministic seed")
        if task.get("source_type") == "adversarial_topology":
            if task.get("intended_track") != "robustness_ood":
                raise ValueError(f"{task['task_id']}: adversarial sample must be OOD")
    return {
        "schema": "W6_P29_1_TASK_MANIFEST_VALIDATION_V1",
        "candidate_count": len(tasks),
        "source_counts": dict(counts),
        "unique_lineages": len({x["lineage_id"] for x in tasks}),
        "status": "VALID_PLAN_ONLY_NOT_GENERATED",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    result = validate(json.loads(a.input.read_text()))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

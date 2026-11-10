"""P29.0 CPU-side validator for TRELLIS/CAD/procedural geometry manifests.

This validates provenance and declared geometry-audit fields. It does not
replace mesh-level inspection (self-intersection, winding, watertightness),
which must be measured by the local mesh audit tool and recorded in the
manifest. No physical truth is inferred from a rendered mesh.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

SOURCE_TYPES = {
    "trellis_v1", "trellis2", "procedural_cad", "public_cad",
    "adversarial_topology", "analytic_control",
}
TRACKS = {"supervised_solid", "robustness_ood"}
TOPOLOGIES = {
    "closed_manifold", "multi_component_closed", "open_surface",
    "non_manifold", "self_intersecting", "near_zero_thickness", "unknown",
}
LABEL_STATES = {"pending", "cherchi", "analytic_control", "voxel_only"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _finite_positive(value, name):
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be numeric")
    if not math.isfinite(x) or x <= 0:
        raise ValueError(f"{name} must be finite and positive")
    return x


def _vector3(value, name, *, positive=False):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name} must be a length-3 list")
    vals = [float(x) for x in value]
    if not all(math.isfinite(x) for x in vals):
        raise ValueError(f"{name} contains non-finite values")
    if positive and any(x <= 0 for x in vals):
        raise ValueError(f"{name} must contain only positive values")
    return vals


def validate_record(row):
    errors = []
    required = (
        "asset_id", "lineage_id", "source_type", "raw_asset_path",
        "raw_asset_sha256", "units", "bbox_extent", "transform_4x4",
        "topology_class", "watertight", "winding_consistent",
        "self_intersections", "connected_components", "volume",
        "density_kg_m3", "intended_track", "license", "label_status",
    )
    for key in required:
        if key not in row:
            errors.append(f"missing:{key}")
    if errors:
        return errors

    if not str(row["asset_id"]).strip():
        errors.append("empty:asset_id")
    if not str(row["lineage_id"]).strip():
        errors.append("empty:lineage_id")
    if row["source_type"] not in SOURCE_TYPES:
        errors.append("invalid:source_type")
    if row["intended_track"] not in TRACKS:
        errors.append("invalid:intended_track")
    if row["topology_class"] not in TOPOLOGIES:
        errors.append("invalid:topology_class")
    if row["label_status"] not in LABEL_STATES:
        errors.append("invalid:label_status")
    if row["units"] not in {"mm", "cm", "m"}:
        errors.append("invalid:units")
    if not str(row["raw_asset_path"]).strip():
        errors.append("empty:raw_asset_path")
    if not SHA256_RE.fullmatch(str(row["raw_asset_sha256"])):
        errors.append("invalid:raw_asset_sha256")
    if not str(row["license"]).strip():
        errors.append("missing:license_or_restriction_record")

    for key in ("watertight", "winding_consistent", "self_intersections"):
        if not isinstance(row[key], bool):
            errors.append(f"invalid:boolean:{key}")
    try:
        _vector3(row["bbox_extent"], "bbox_extent", positive=True)
    except (TypeError, ValueError) as exc:
        errors.append(f"invalid:{exc}")
    try:
        _finite_positive(row["volume"], "volume")
    except ValueError as exc:
        errors.append(f"invalid:{exc}")
    try:
        _finite_positive(row["density_kg_m3"], "density_kg_m3")
    except ValueError as exc:
        errors.append(f"invalid:{exc}")
    try:
        components = int(row["connected_components"])
        if components < 1:
            errors.append("invalid:connected_components")
    except (TypeError, ValueError):
        errors.append("invalid:connected_components")

    transform = row["transform_4x4"]
    if (not isinstance(transform, list) or len(transform) != 4
            or any(not isinstance(line, list) or len(line) != 4 for line in transform)):
        errors.append("invalid:transform_4x4_shape")
    else:
        try:
            flat = [float(x) for line in transform for x in line]
            if not all(math.isfinite(x) for x in flat):
                errors.append("invalid:transform_4x4_nonfinite")
        except (TypeError, ValueError):
            errors.append("invalid:transform_4x4_numeric")

    # A supervised mass-moment solid must have a valid, positively oriented,
    # non-self-intersecting closed volume. Open/non-manifold assets stay OOD.
    if row["intended_track"] == "supervised_solid":
        if row["topology_class"] not in {"closed_manifold", "multi_component_closed"}:
            errors.append("solid_track_requires_closed_topology")
        if row["watertight"] is not True:
            errors.append("solid_track_requires_watertight")
        if row["winding_consistent"] is not True:
            errors.append("solid_track_requires_consistent_winding")
        if row["self_intersections"] is not False:
            errors.append("solid_track_rejects_self_intersections")
        if row["label_status"] == "voxel_only":
            errors.append("solid_track_requires_continuous_teacher_or_control_label")
    elif row["intended_track"] == "robustness_ood" and row["label_status"] == "cherchi":
        errors.append("ood_track_cannot_claim_solid_cherchi_label_without_surface_contract")

    if row["source_type"] in {"trellis_v1", "trellis2"}:
        for key in ("generator_version", "checkpoint_id", "generation_seed"):
            if key not in row or row[key] in (None, ""):
                errors.append(f"missing_generation_provenance:{key}")
    if row["source_type"] == "public_cad" and not row.get("source_url"):
        errors.append("missing:source_url")
    if row.get("repair_applied") is True:
        if not row.get("repair_tool") or not row.get("repair_version"):
            errors.append("repair_requires_tool_and_version")
        if not row.get("derived_asset_sha256") or not SHA256_RE.fullmatch(
            str(row["derived_asset_sha256"])
        ):
            errors.append("repair_requires_derived_asset_sha256")

    return errors


def validate_manifest(rows):
    if not rows:
        raise ValueError("manifest is empty")
    accepted, rejected = [], []
    seen_assets = set()
    lineage_sources = defaultdict(set)
    for index, row in enumerate(rows):
        errors = validate_record(row)
        asset_id = str(row.get("asset_id", ""))
        if asset_id in seen_assets:
            errors.append("duplicate:asset_id")
        seen_assets.add(asset_id)
        if row.get("lineage_id") and row.get("source_type"):
            lineage_sources[row["lineage_id"]].add(row["source_type"])
        item = {"line": index + 1, "asset_id": asset_id, "lineage_id": row.get("lineage_id"), "errors": errors}
        (rejected if errors else accepted).append(item)
    return {
        "schema": "W6_P29_GEOMETRY_MANIFEST_AUDIT_V1",
        "candidate_count": len(rows),
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "source_counts": dict(Counter(str(x.get("source_type", "missing")) for x in rows)),
        "track_counts": dict(Counter(str(x.get("intended_track", "missing")) for x in rows)),
        "lineage_count": len(lineage_sources),
        "accepted": accepted,
        "rejected": rejected,
        "claims": {
            "mesh_geometry_was_recomputed_here": False,
            "physical_labels_were_generated_here": False,
            "accepted_means_manifest_contract_only": True,
        },
    }


def read_jsonl(path):
    rows = []
    for line_no, line in enumerate(Path(path).read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at line {line_no}: {exc}")
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = validate_manifest(read_jsonl(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({k: result[k] for k in (
        "candidate_count", "accepted_count", "rejected_count",
        "source_counts", "track_counts",
    )}, indent=2))


if __name__ == "__main__":
    main()

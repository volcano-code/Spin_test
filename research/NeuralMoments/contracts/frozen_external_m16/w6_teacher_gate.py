"""Fail-closed W2 teacher readiness gate; never substitute analytic labels.

W2 pinned branch 14b1d2d5... currently publishes a pre-W0 adapter manifest
with zero native teacher runs. This module intentionally cannot authorize an
unreviewed schema merely because it reports a positive sample count.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

KNOWN_PRE_W0_SCHEMA = "w2-cherchi-teacher-v1-pre-w0"


class TeacherUnavailable(RuntimeError):
    pass


def inspect_teacher_manifest(manifest: Mapping) -> dict:
    if not isinstance(manifest, Mapping):
        raise TypeError("W2 manifest must be a mapping")
    schema = manifest.get("schema")
    status = manifest.get("status")
    samples = manifest.get("training_samples")
    native_runs = manifest.get("native_teacher_runs")
    blocks = []
    if schema == KNOWN_PRE_W0_SCHEMA:
        blocks.append("pre-W0 adapter schema is not a frozen, real Cherchi label contract")
    else:
        blocks.append("W2 schema is not pinned/independently validated against W0")
    if status != "NATIVE_VERIFIED":
        blocks.append("manifest has no independently accepted NATIVE_VERIFIED status")
    if not isinstance(native_runs,int) or isinstance(native_runs,bool) or native_runs <= 0:
        blocks.append("native_teacher_runs is missing or zero")
    if not isinstance(samples,int) or isinstance(samples,bool) or samples <= 0:
        blocks.append("training_samples is missing or zero")
    if manifest.get("pending_dependency"):
        blocks.append("manifest declares a pending upstream dependency")
    return {"admissible":False,"schema":schema,"status":status,
            "native_teacher_runs":native_runs,"training_samples":samples,
            "blockers":blocks,
            "policy":"NO_TRAINING_UNTIL_W0_W2_FROZEN_RECORD_VALIDATOR_AND_INDEPENDENT_SEAL"}


def require_native_teacher(manifest: Mapping) -> None:
    gate = inspect_teacher_manifest(manifest)
    raise TeacherUnavailable("W2 real-teacher ingestion blocked: " + "; ".join(gate["blockers"]))


def read_manifest(path: str | Path) -> dict:
    with open(path,encoding="utf-8") as stream:
        data = json.load(stream)
    return inspect_teacher_manifest(data)

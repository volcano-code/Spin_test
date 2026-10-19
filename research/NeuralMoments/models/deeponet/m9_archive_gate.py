"""Fail-closed, metadata-only gate for W2 historical H8e native archives.

The W2 25-point records are real *historical* Cherchi material measurements,
independently offline verified by W0/W2. This gate NEVER turns them into
network training data or smooth 10x10 derivative truth; no archive ZIP is read
and no real material integrals are recomputed in W5.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

W2_SOURCE_COMMIT = "bd87b26a926e260a4f3dd4df6b96ca561a49f6eb"
# Identity pinned to W2 Git blob; no unverified digest aliases.
W2_MANIFEST_EXPECTED_SHA = "b1a126d94eb5bfb0fc57ff59cd5250ce0a3b3171"
W2_ORIGINAL_FAILED_WORKFLOW = 39121571756
W2_ORIGINAL_ARTIFACT_SHA256 = "14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38"
W2_CLASSIFIER_WORKFLOW = 39122997405


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(content)).encode() + b"\0" + content).hexdigest()


def inspect_historical_manifest(manifest_path: str | Path) -> dict:
    """Verify published bytes before interpreting the *claimed* archive metadata.

    A correct manifest says what W2 independently reported, not that W5 read
    the 25 original material ZIP members or newly ran the Cherchi code.
    """
    path = Path(manifest_path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("W2 manifest missing/symlink")
    raw = path.read_bytes()
    if git_blob_sha(raw) != W2_MANIFEST_EXPECTED_SHA:
        raise ValueError("W2 manifest diverges from pinned published Git blob")
    m = json.loads(raw, parse_constant=lambda x: (_ for _ in ()).throw(ValueError("invalid JSON constant")))
    history = m.get("previously_recorded_native_evidence")
    if (m.get("schema") != "w2-cherchi-teacher-v2-pre-w0"
            or m.get("native_teacher_runs") != 0
            or m.get("training_samples") != 0 or not isinstance(history, dict)
            or history.get("original_native_evaluations") != 25
            or history.get("archived_samples_offline_independently_reverified") != 25
            or history.get("upstream_github_actions_run") != W2_ORIGINAL_FAILED_WORKFLOW
            or history.get("upstream_workflow_conclusion") != "failure"
            or history.get("archive_zip_sha256") != W2_ORIGINAL_ARTIFACT_SHA256
            or history.get("independent_classifier_run") != W2_CLASSIFIER_WORKFLOW
            or history.get("full_81_points") is not False
            or history.get("certified_smooth_neighborhood") is not False
            or history.get("training_admitted") is not False
            or history.get("newton_converged") is not False
            or history.get("new_native_evaluations") != 0
            or history.get("archived_topology_hash_drift_sample_indices") != list(range(17,25))):
        raise ValueError("W2 historical/native derivative gate cannot pass")
    return {
        "read_only_manifest_blob_checked":True,
        "original_native_archive_evaluations":25,
        "offline_independently_reverified_mass_records":25,
        "original_workflow_status":"failure",
        "topology_hash_drift_indices":list(range(17,25)),
        "certified_smooth_J_training_labels":0,
        "moment_training_labels_admitted":0,
        "new_native_cherchi_runs_in_w5":0,
        "historical_H8e_moments_accuracy_newly_remeasured_in_w5":False,
        "training_allowed":False,
        "independent_native_geometry_certified":False,
        "source":"W2 manifest evidence only; not raw ZIP contents or independent new proof",
        "underlying_workflow_run":W2_ORIGINAL_FAILED_WORKFLOW,
    }

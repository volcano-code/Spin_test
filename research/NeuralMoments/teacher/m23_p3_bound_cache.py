"""New W2 rebuild cache, NOT recovered historical common.py.

Bind outputs to ordered operands, code, backend, serializer and experiment.
An intact cache is a provenance check, never a solid/Jacobian certificate.
Only standard-library Python is required. No native executable is launched.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any

SCHEMA = "W2_NEW_REBUILD_BOUND_CACHE_V1"
KINDS = {"SYNTHETIC_MOCK_ONLY", "NATIVE_UNADMITTED"}
OPS = {"union": 2, "intersection": 2, "difference": 2, "copy": 1}
SHA_FIELDS = (
    "source_manifest_sha256", "source_audit_sha256", "builder_source_sha256",
    "adapter_sha256", "backend_sha256",
)
CONTEXT_FIELDS = {
    "experiment_id", "evidence_kind", "node_id", "operation", "serializer_id",
    "coordinate_policy", "operand_sha256", *SHA_FIELDS,
}


class CacheRejected(ValueError):
    """A cache must not be reused; preserve it for diagnosis."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def _unique_pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise CacheRejected("DUPLICATE_JSON_KEY:" + key)
        value[key] = item
    return value


def strict_json(data: bytes) -> Any:
    def reject_constant(value):
        raise CacheRejected("NONFINITE_JSON:" + value)
    try:
        return json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs,
                          parse_constant=reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CacheRejected("INVALID_RECEIPT_JSON") from exc


def _sha(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_context(context: dict) -> dict:
    if not isinstance(context, dict) or set(context) != CONTEXT_FIELDS:
        raise CacheRejected("CONTEXT_FIELDS_MISMATCH")
    for field in ("experiment_id", "node_id"):
        if not isinstance(context[field], str) or not re.fullmatch(
                r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", context[field]):
            raise CacheRejected("INVALID_SAFE_ID:" + field)
    if context["evidence_kind"] not in KINDS:
        raise CacheRejected("EVIDENCE_KIND_NOT_ADMITTED")
    if context["operation"] not in OPS:
        raise CacheRejected("INVALID_OPERATION")
    for field in ("serializer_id", "coordinate_policy"):
        if not isinstance(context[field], str) or not context[field].strip():
            raise CacheRejected("MISSING_POLICY:" + field)
    for field in SHA_FIELDS:
        if not _sha(context[field]):
            raise CacheRejected("INVALID_SHA256:" + field)
    operands = context["operand_sha256"]
    if not isinstance(operands, list) or len(operands) != OPS[context["operation"]]:
        raise CacheRejected("OPERAND_ARITY_MISMATCH")
    if not all(_sha(value) for value in operands):
        raise CacheRejected("INVALID_OPERAND_SHA256")
    # Detach from mutable caller dictionaries; do not normalize rational data.
    return strict_json(canonical(context))


def _directory(path: Path) -> None:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError as exc:
        raise CacheRejected("DIRECTORY_MISSING") from exc
    if not stat.S_ISDIR(mode):
        raise CacheRejected("SYMLINK_OR_NON_DIRECTORY")


def _regular_bytes(path: Path) -> bytes:
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError as exc:
        raise CacheRejected("INCOMPLETE_OR_UNREADABLE_CACHE:" + path.name) from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise CacheRejected("NONREGULAR_CACHE_FILE:" + path.name)
        with os.fdopen(fd, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(fd)


def _exclusive_write(path: Path, data: bytes) -> None:
    # Never overwrite a historical output, receipt, or partially written node.
    with path.open("xb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def _sync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _node_path(root: Path, context: dict, *, create: bool) -> Path:
    root = Path(root)
    if create:
        root.mkdir(parents=True, exist_ok=True)
    _directory(root)
    experiment = root / context["experiment_id"]
    if create:
        experiment.mkdir(exist_ok=True)
    if experiment.is_symlink():
        raise CacheRejected("SYMLINK_EXPERIMENT_DIRECTORY")
    if experiment.exists():
        _directory(experiment)
    return experiment / context["node_id"]


def store(root: Path, context: dict, output_bytes: bytes) -> dict:
    """Store a NEW node. The receipt is the last, exclusive commit marker.

    A crash can leave a partial directory. Such a directory is never silently
    reused or repaired. Use a new experiment/node after preserving evidence.
    """
    ctx = validate_context(context)
    if not isinstance(output_bytes, bytes) or not output_bytes:
        raise CacheRejected("NONEMPTY_BYTES_REQUIRED")
    node = _node_path(root, ctx, create=True)
    try:
        node.mkdir()
    except FileExistsError as exc:
        raise CacheRejected("REFUSE_EXISTING_NODE") from exc
    _sync_dir(node.parent)
    receipt = {
        "schema": SCHEMA, "context": ctx,
        "context_sha256": digest(canonical(ctx)),
        "output_sha256": digest(output_bytes), "output_size_bytes": len(output_bytes),
        "status": "COMMITTED_UNADMITTED",
        "historical_bytes_recovered": False,
        "solid_certified": False, "J_D": None, "training_admitted": False,
    }
    _exclusive_write(node / "output.bin", output_bytes)
    _exclusive_write(node / ".receipt.pending", canonical(receipt))
    # Hard link creates a complete receipt without replacing an existing one.
    os.link(node / ".receipt.pending", node / "receipt.json")
    _sync_dir(node)
    (node / ".receipt.pending").unlink()
    _sync_dir(node)
    return receipt


def load(root: Path, expected_context: dict) -> bytes | None:
    """Return verified bytes, or None for a missing node; reject partial/stale nodes.

    This assumes the caller independently derives the expected context from
    its current frozen inputs. A receipt is not a digital signature.
    """
    ctx = validate_context(expected_context)
    root = Path(root)
    if not root.exists() and not root.is_symlink():
        return None
    node = _node_path(root, ctx, create=False)
    if node.is_symlink():
        raise CacheRejected("SYMLINK_NODE_DIRECTORY")
    if not node.exists():
        return None
    _directory(node)
    receipt = strict_json(_regular_bytes(node / "receipt.json"))
    expected_keys = {
        "schema", "context", "context_sha256", "output_sha256", "output_size_bytes",
        "status", "historical_bytes_recovered", "solid_certified", "J_D",
        "training_admitted",
    }
    if not isinstance(receipt, dict) or set(receipt) != expected_keys:
        raise CacheRejected("RECEIPT_FIELDS_MISMATCH")
    if receipt["schema"] != SCHEMA or receipt["status"] != "COMMITTED_UNADMITTED":
        raise CacheRejected("RECEIPT_SCHEMA_OR_STATUS_MISMATCH")
    if validate_context(receipt["context"]) != ctx:
        raise CacheRejected("CACHE_CONTEXT_MISMATCH")
    if receipt["context_sha256"] != digest(canonical(ctx)):
        raise CacheRejected("CONTEXT_DIGEST_MISMATCH")
    if (receipt["historical_bytes_recovered"] is not False or
            receipt["solid_certified"] is not False or
            receipt["training_admitted"] is not False or receipt["J_D"] is not None):
        raise CacheRejected("UNSUPPORTED_ADMISSION_CLAIM")
    output = _regular_bytes(node / "output.bin")
    if (type(receipt["output_size_bytes"]) is not int or
            receipt["output_size_bytes"] != len(output) or
            receipt["output_sha256"] != digest(output)):
        raise CacheRejected("OUTPUT_BYTES_MISMATCH")
    return output

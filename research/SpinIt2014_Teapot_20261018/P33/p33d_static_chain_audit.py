#!/usr/bin/env python3
"""P33-D static consistency audit for the W4 P30B local native-pilot chain.

Reads source only. Does not inspect host resources, run Docker, import native
modules, read owner receipts, create a lock, or invoke Cherchi.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
P30 = ROOT / "research/SpinIt2014_Teapot_20261018/P30"
WRAPPER = P30 / "p30b_run_approved_native_pilot.sh"
AUTHORITY = P30 / "p30b_authority.py"
SAMPLER = P30 / "p30b_native_sampler.py"
SEED = P30 / "p30_neighborhood_preflight.py"


def need(ok, code):
    if not ok:
        raise ValueError(code)


def quoted_constant(source: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]",
                      source, re.MULTILINE)
    need(match is not None, "MISSING_CONSTANT:" + name)
    return match.group(1)


def audit(root: Path = ROOT):
    p30 = root / "research/SpinIt2014_Teapot_20261018/P30"
    wrapper = (p30 / "p30b_run_approved_native_pilot.sh").read_text()
    authority = (p30 / "p30b_authority.py").read_text()
    sampler = (p30 / "p30b_native_sampler.py").read_text()
    seed = (p30 / "p30_neighborhood_preflight.py").read_text()

    # All pinned artifacts must agree between the preflight implementation
    # and the shell wrapper. The archive's internal run root and the local
    # host's P27 prepared run directory are deliberately distinct identifiers.
    plan_sha = quoted_constant(authority, "P30_PRIVATE_PLAN_SHA")
    archive_sha = quoted_constant(seed, "ARCHIVE_SHA")
    manifest_sha = quoted_constant(seed, "MANIFEST_SHA")
    p27_lock_sha = quoted_constant(seed, "LOCK_SHA")
    core_sha = quoted_constant(sampler, "CORE_SHA")
    archive_run = quoted_constant(seed, "RUN")
    host_run_match = re.search(r'^P27_RUN_REL="([^"]+)"$', wrapper, re.MULTILINE)
    need(host_run_match is not None, "MISSING_HOST_P27_RUN_REL")
    host_run = host_run_match.group(1)
    need(host_run != archive_run,
         "P27_ARCHIVE_ROOT_AND_HOST_RUN_DIR_EXPECTED_TO_BE_SEPARATE")
    for value, code in (
        (plan_sha, "PLAN_SHA_NOT_PINNED_IN_WRAPPER"),
        (archive_sha, "ARCHIVE_SHA_NOT_PINNED_IN_WRAPPER"),
    ):
        need(value in wrapper, code)
    need(f'test "$(git -C "$CORE" rev-parse HEAD)" = "{core_sha}"' in wrapper,
         "CORE_COMMIT_PIN_MISMATCH")
    need(f'test "$(sha256sum "$LOCK" | awk \'{{print $1}}\')" = "$P30B_EXTERNAL_LOCK_SHA256"' in wrapper,
         "EXTERNAL_LOCK_SHA_CHECK_MISSING")
    need(f'test "$(sha256sum "$PLAN" | awk \'{{print $1}}\')" = "{plan_sha}"' in wrapper,
         "PLAN_SHA_CHECK_MISMATCH")
    need(f'test "$(sha256sum "$ARCHIVE" | awk \'{{print $1}}\')" = "{archive_sha}"' in wrapper,
         "ARCHIVE_SHA_CHECK_MISMATCH")

    # Verify exact owner receipt names are enforced in both Python authority
    # and the local host wrapper; no W4-created substitute is accepted.
    w0 = quoted_constant(authority, "W0_REL")
    w2 = quoted_constant(authority, "W2_REL")
    need(w0 in wrapper and w2 in wrapper, "OWNER_RECEIPT_PATH_NOT_ENFORCED")
    need(quoted_constant(authority, "W0_BRANCH") in authority and
         quoted_constant(authority, "W2_BRANCH") in authority,
         "OWNER_BRANCH_IDENTITY_MISSING")

    # Resource and runtime gates must be consistent across host and child.
    need("--memory=24g --memory-swap=24g" in wrapper,
         "DOCKER_24G_SWAP_ZERO_ENVELOPE_MISSING")
    need("resources[\"cgroup\"][\"memory.max\"] == str(ADDRESS_BYTES)" in sampler and
         "resources[\"cgroup\"][\"memory.swap.max\"] == \"0\"" in sampler and
         "resources[\"host_swap_bytes\"] == 0" in sampler,
         "CHILD_RESOURCE_GATES_MISSING")
    need("verify_modules(a.p27_run_dir)" in sampler and
         "native-build/core/python" in sampler and
         "native-build/cherchi/python" in sampler,
         "NATIVE_MODULE_PATH_OR_HASH_GATE_MISSING")
    need("P27_RUN_REL" in wrapper and
         f'/output/$P27_RUN_REL/native-build/core/python' in wrapper and
         f'/output/$P27_RUN_REL/native-build/cherchi/python' in wrapper,
         "HOST_PYTHONPATH_DOES_NOT_MATCH_PINNED_P27_RUN")
    need("p27_run_dir / LOCK_NAME" in sampler and
         "p27_run_dir / PINS_NAME" in sampler,
         "P27_LOCK_OR_SIX_PINS_NOT_REVALIDATED")
    need("seed.verify_archive(a.archive)" in sampler and
         "seed.plan(archive,step=plan[\"step_radians\"])" in sampler,
         "P27_ARCHIVE_AND_PLAN_NOT_RECONCILED")

    # Fail-closed scientific states remain false in authority and sampler.
    for token in ("Newton_accepted=False", "training_admissible=False",
                  "Faster_optimization_executed=False",
                  "MuJoCo_optimized_before_after_executed=False"):
        need(token in authority and token in sampler,
             "SCIENTIFIC_RELEASE_FLAG_NOT_CLOSED:" + token)
    need("P30_MAX_SECONDS = 3600" in sampler and
         "POINT_MAX_SECONDS = 900" in sampler and
         "N_PILOT = 12" in sampler,
         "PILOT_TIME_OR_POINT_BUDGET_CHANGED")

    return {
        "schema": "W4_P33D_P30B_STATIC_CHAIN_AUDIT_V1",
        "status": "STATIC_SOURCE_CONSISTENCY_PASS_NOT_RUNTIME_ADMISSION",
        "pinned": {
            "p30_private_plan_sha256": plan_sha,
            "p27_archive_sha256": archive_sha,
            "p27_manifest_sha256": manifest_sha,
            "p27_lock_sha256": p27_lock_sha,
            "core_commit": core_sha,
            "archive_internal_run_root": archive_run,
            "host_prepared_p27_run_directory": host_run,
            "w0_receipt_path": w0,
            "w2_receipt_path": w2,
        },
        "resource_envelope": {
            "docker_memory": "24g",
            "docker_memory_swap_total": "24g",
            "required_host_swap_bytes": 0,
            "required_cgroup_swap_max": "0",
        },
        "pilot": {"maximum_points": 12, "max_seconds": 3600,
                  "per_point_max_seconds": 900},
        "runtime_observed": False,
        "owner_receipts_observed": False,
        "external_lock_registered": False,
        "native_calls": 0,
        "scientific_admission": False,
        "Newton_accepted": False,
        "training_admissible": False,
        "MuJoCo_optimized_before_after_executed": False,
    }


def main():
    print(json.dumps(audit(), sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()

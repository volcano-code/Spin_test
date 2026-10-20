# W0 M12 — independent, fail-closed W3 four-side evidence custody

**Only write to** `research/neuralmoments-w0-contract-20261019` under
`research/NeuralMoments/contracts/` and `research/ParallelLaunch/`.
Frozen production ancestor: `0bcc187b3005478baa586a6d6f450e73811ca342`.

## Verified input at this milestone

- W3 Stage10 observed HEAD `324256786bc189abbbb93452ed2627cfe0b28a13`.
- W3 Stage10 original input JSON Git blob `8a352efca5f7f88dda24c359b7d5225f10f9cf66`.
- W3 Stage10 original execution JSON Git blob `254e93076d6fbec0a60632cee4c4731945f579d4`.
- W3 input gate source Git blob `5c7d71bb83cd195dea47d1c01400bc312fbbff65`.
- W3 source verifier Git blob `375fc1f3f04e110563ab53281200d99041cf12cd`.
- H8f frozen Actions workflow Git blob `a6dda4d04998f1244ce0a7f80991d6198c037cdb`.
- Original H8f run `39123384402` **failure**, authentic source artifact
  `12135528290` SHA-256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`.

Stage10 confirmed input readiness only, **zero** new real Cherchi evaluations and **zero**
new material packets. Its recorded build/run preflights both failed (exit 2),
with a 4 GiB effective memory limit, no complete pinned W3 checkout and no native
extensions. The M12 executable independently checks both actual W3 JSON blobs,
including the exact four q[7] proxy sample values, and returns **exit 3**:
`BLOCKED_MISSING_FOUR_NEW_CHERCHI_SIDE_MATERIALS`.

```bash
python -m research.NeuralMoments.contracts.w3_custody_m12 --mode stage10 \
  --output /new/path/w0_m12_readiness.json
# exit code 3 is EXPECTED, not a native success
```

## Independent pre-run lock (before executing any native Cherchi)

The **reviewer**, not the W3 producer, must create a byte-immutable JSON outside
all W3 writable output and independently register its SHA-256 BEFORE W3 starts.
The JSON must have exactly these fields:

```json
{
  "schema": "W0_M12_EXTERNALLY_PINNED_PRE_NATIVE_SOURCE_LOCK_V1",
  "frozen_w3_head_sha": "324256786bc189abbbb93452ed2627cfe0b28a13",
  "source_verifier_git_blob": "375fc1f3f04e110563ab53281200d99041cf12cd",
  "source_workflow_git_blob": "a6dda4d04998f1244ce0a7f80991d6198c037cdb",
  "source_input_gate_git_blob": "5c7d71bb83cd195dea47d1c01400bc312fbbff65",
  "source_stage10_evidence_git_blob": "254e93076d6fbec0a60632cee4c4731945f579d4",
  "historical_artifact_sha256": "99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9",
  "precommitted_native_binary_sha256": {
    "core": "<64hex from actual pinned binary BEFORE native execution>",
    "boolean": "<64hex from actual pinned binary BEFORE native execution>",
    "arithmetic": "<64hex from actual pinned binary BEFORE native execution>"
  }
}
```

**Do not use those bracketed placeholders as hashes.** A new W3 source commit
requires separate code review and a new explicit allowlisted W3 HEAD; the
current pinned Stage10 cannot silently validate an arbitrary later branch.
An internally self-generated hash is not independent pre-execution proof.

## Post-run collection (by an independent reviewer, after producer exit)

Only on a native host with the four **genuine** Cherchi/GMP packets, freeze all
13 of the M11-prescribed output files. The M12 capture checks source/binary
identity, the original H8f artifact hash, every required ordinary file (no
symlink or mid-read changes), bounded gzip decoding, run/audit/log semantics,
material byte hashes and pointwise coefficient shape. It rejects extra
unreviewed `side-*` packet files. On any failure it does **not** emit a success
receipt.

```bash
python -m research.NeuralMoments.contracts.w3_custody_m12 --mode capture \
  --pre-run-lock /reviewer/pre_run_lock.json \
  --external-pre-run-sha256 <HASH_REGISTERED_BEFORE_THE_RUN> \
  --w3-folder /read-only/copy/of/producer/four-native-points \
  --historical-archive /reviewer/verified/artifact-12135528290.zip \
  --output /reviewer/new/W0_M11_INDEPENDENT_FILE_DIGEST_RECEIPT_V1.json
```

The reviewer receipt MUST be held separately from W3 and made read-only to the
producer. A deterministic SHA plus JSON is **file integrity**, not proof of
cryptographic native runtime origin. Keep launch logs, CI and independently
collected build identities separately.

## Read-only acceptance replay (distinct operation)

Once all real files exist and the independent receipt is frozen, use:

```bash
python -m research.NeuralMoments.contracts.w3_custody_m12 --mode review \
  --pre-run-lock /reviewer/pre_run_lock.json \
  --external-pre-run-sha256 <HASH_REGISTERED_BEFORE_THE_RUN> \
  --w3-folder /read-only/copy/of/producer/four-native-points \
  --postrun-receipt /reviewer/frozen/W0_M11_INDEPENDENT_FILE_DIGEST_RECEIPT_V1.json \
  --historical-archive /reviewer/verified/artifact-12135528290.zip \
  --output /reviewer/new/w0_m12_review.json
```

This calls the **existing W0 M11** exact surface/Jacobian/independent moment
reviewer, not just string/status checking. A synthetic internally consistent
receipt should fail this actual geometric replay. Even a genuine positive
finite-four-side review **must keep** `newton_admitted=false`,
`training_admissible=false`, and `smooth_neighborhood_proven=false` because
four finite points cannot prove a continuous differentiable parameter stratum,
full F/D/cavity geometry partition, or accepted Newton terminal.

## Actually executed local tests

Using installed Python 3.13.5 and the genuine archived H8e + H8f original
GitHub ZIP attachments: **178/178 pytest passed** across M8–M12 in 28.60 s.
This includes 41 M12 cases (real Stage10 blob comparison; synthetic receipt
negative cases), and reruns 137 M8–M11 cases. The production W3 four-side
native job is **not** executed here; actual observed new data remain **0/4**.
CI status for the new W0 commit must be independently checked, not inferred.

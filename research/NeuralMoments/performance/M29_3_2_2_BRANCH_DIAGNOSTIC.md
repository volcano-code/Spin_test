# W1 M29.3.2.2 — discrete branch-component diagnostic

## Why this exists

The completed M29.3.2 run contains 72 fresh native evaluations. Operation, source surface type and cap count stayed fixed, but 46 topology hashes differ from the M9 base. Existing receipts do not persist all branch-hash components separately, so the cause cannot be inferred from the old hashes alone.

## Diagnostic experiment

This runner performs 13 fresh calls:
- one base-q candidate evaluation, checked against the saved M9 candidate result;
- +/- perturbations for tangent directions 6, 7, 8 at h=1e-5 and h=1e-6.

Each call uses a fresh evaluator, real Cherchi Boolean, same-call material validation, exact rational boundary audit and independent Fraction ten-moment check. It is serial, has a 24 GiB process address-space cap, and refuses to start below 6 GiB available memory or 1 GiB free disk space.

## Fingerprint components

The runner recomputes the exact production SOURCE_FEATURE_BRANCH_V2 fingerprint and separately records:
- ordered source-face list hash;
- orientation-preserving source-face-set hash;
- orientation-insensitive source-face-set hash;
- source-normal-edge hash;
- construction signature hash;
- output feature-triangle hash;
- operation, surface type and cap count.

Geometry hash is recorded but is deliberately excluded from branch equality because coordinates are expected to move continuously under parameter perturbations.

## Expected interpretation

The component mismatch table identifies which discrete inputs to the production feature hash change relative to the base. Pair summaries also show whether plus and minus sides agree with each other. This distinguishes a source-face change, feature-edge change, construction correspondence change, output feature-triangulation change, or a change in more than one component.

## Limits

The diagnostic does not relax the production branch policy, does not change the Cherchi evaluator, and does not certify a smooth neighborhood or Newton. A component hash match is necessary evidence for same-branch comparison under this policy, but it is not by itself a full neighborhood proof.

## Local execution

```bash
REPO="/data/xvxinyao1/Spin_test-W1/Spin_test-w1"
EXP="/data/xvxinyao1/Spin_test-W1/experiments"
PERF="$REPO/research/NeuralMoments/performance"
H8C="$EXP/archives/h8c-reference-39118951636.zip"
CORE="$REPO/build/w1-m13-core/python"
CHERCHI="$REPO/build/w1-m13-cherchi/python"
SYSTEM_LIB="/usr/lib/x86_64-linux-gnu/libstdc++.so.6.0.33"
M9RUN="$HOME/w1-m29-m9-fixed-20261108-181458"
OUT="$HOME/w1-m29-3-2-2-branch-diagnostic-$(date +%Y%m%d-%H%M%S)"

env LD_PRELOAD="$SYSTEM_LIB" \
  PYTHONPATH="$CORE:$CHERCHI:$REPO/python:$PERF" \
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python3 "$PERF/m29_3_2_2_branch_diagnostic.py" \
    --root "$REPO" --archive "$H8C" --m9-run "$M9RUN" \
    --output "$OUT" --steps 1e-5,1e-6 --directions 6,7,8
```

The expected work is 13 fresh native evaluations, not a replay of all 72 samples. It is still a real local compute job and should only be started when the machine has sufficient memory and disk headroom.

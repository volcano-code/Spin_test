# W1 M29.3.2 — fresh-native tangent-space Jacobian finite differences

## Purpose

Independently test the M9 production 10x10 moment Jacobian at the frozen H8c q after removing the scale-gauge direction identified in M29.3.1. This is a local derivative check at one q, not a neighborhood certificate, Newton solve, or speed claim.

## Method

- Load the passing M9 A/B/B/A report and use its candidate Jacobian and frozen q.
- Construct the same 10x9 orthonormal tangent basis as the M29.3.1 host check:
  `A=[q,I10]`, `Q,R=qr(A)`, `B=Q[:,1:]`.
- Compare `J_t=J B` against fresh central differences:
  `(F(normalize(q+h b_j))-F(normalize(q-h b_j)))/(2h)`.
- Step sizes: 1e-3, 1e-4, 1e-5, 1e-6; nine directions; 72 fresh function evaluations in candidate mode.
- Each sample constructs a fresh evaluator and invokes source motion, real Cherchi Boolean, same-call material validation, exact rational boundary audit, and independent Fraction ten-moment integration. No M9 material cache is reused.
- Every perturbation records geometry hash, feature-topology hash, operation, source surface type/cap count, source-edge signature, and construction-point signature. A finite-difference column is accepted only when both sides preserve the frozen base topology hash and each other.
- Full mesh packets are not copied to the output. A compact JSONL receipt is flushed after every sample.

## Numerical review thresholds

The runner reports both global relative Frobenius error and per-column relative errors. Default diagnostic thresholds are 1e-4 global and 1e-3 maximum per column. These are explicit engineering review thresholds for this experiment, not a published theorem or formal derivative-admission standard. All four step sizes must remain on the same feature branch for the runner to return the within-tolerance status.

## Resource and safety contract

- Serial execution; no parallel Cherchi calls.
- Requires at least 6 GiB MemAvailable and 1 GiB free on the output filesystem.
- Reuses pinned H8c archive, production source, and native module identities.
- 24 GiB process address-space cap and zero-swap policy inherited from M5.
- Maximum wall time defaults to 3600 seconds.
- On any failed sample, writes failure.json and exits nonzero; it never converts a failed run into a pass.
- The output directory must not already exist.

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
OUT="$HOME/w1-m29-3-2-fd-$(date +%Y%m%d-%H%M%S)"

env LD_PRELOAD="$SYSTEM_LIB" \
  PYTHONPATH="$CORE:$CHERCHI:$REPO/python:$PERF" \
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  python3 "$PERF/m29_3_2_jacobian_fd.py" \
    --root "$REPO" --archive "$H8C" --m9-run "$M9RUN" \
    --output "$OUT" --mode candidate \
    --steps 1e-3,1e-4,1e-5,1e-6 --max-seconds 3600
```

## Interpretation limits

A successful run supports local Jacobian agreement only at the frozen H8c point and only over the tested perturbations that remain in the same feature branch. It does not establish a connected smooth neighborhood, Newton convergence, terminal material acceptance, W0/W2 admission, or complete solver speedup. Those remain separate gates.

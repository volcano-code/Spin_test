# W6 M9 — bounded conservative SO(3) transport: actual experimental results

Date: 2026-11-07. Branch: research/neuralmoments-w6-pcraft-20261019.

## Source and reproducibility

- Implementation: \`mass_transport.py\`, paired experiment \`mass_transport_sweep.py\`,
  tests \`tests/test_m9_mass_transport.py\`; production PINO trunk unchanged.
- First implementation commit:
  https://github.com/volcano-code/Spin_test/commit/0cb9a45c2c65dd4c17e978320f548772b9c60b7e
- Diagnostic fix and strict-input regression:
  https://github.com/volcano-code/Spin_test/commit/edf4d2d40b0df5b0995e926060d10d8083a26f5b
  https://github.com/volcano-code/Spin_test/commit/a4fa3a3e4e3d92e8d16f2bd310dd0da9333f5e4a
- M9 three-seed cloud CI job (successful):
  https://github.com/volcano-code/Spin_test/actions/runs/42340430908
- Evidence artifact: \`spin-pino-m9-mass-transport\` / \`w6_m9_mass_transport.json\`.
  The downloaded JSON SHA-256 is
  \`0618c030bda48544ddeb1ada1966d6258be28601207d66ac27ef00a42d58d7c3\`.
- M9 contract tests: 7 passed locally; the added CI M9 job also succeeded.
  Overall workflow completion must be checked separately.
- Exact original M7e baseline reproduction for r/J:
  0.3712313473 / 0.4495181044 on the held-out rotated ellipsoids.

## Matched accuracy comparison (lower is better)

Freeze the same 3 trained PINO logistic-atom checkpoints (seeds 131,137,139),
same fit/validation split (boxes+spheres) and held-out ellipsoid family,
120 steps / seed; identical 48 transformed analytic P0 test queries and
coefficient/moment/Jacobian transforms. The input resampling scheme is the
only intentional model-facing difference.

| Metric | Original trilinear pull | M9 bounded conservative splat | Change |
|---|---:|---:|---:|
| r relative L2 | 0.37123135 | 0.11506282 | -69.005% |
| J relative L2 | 0.44951810 | 0.22057962 | -50.930% |
| r MAE | 0.02162862 | 0.00865936 | -59.963% |
| J MAE | 0.01183003 | 0.00655270 | -44.610% |
| Mean sampled material-mass relative error | 0.29911321 | 1.14e-7 | much lower |
| Mean discrete ten-moment covariance relative L2 | 0.29993984 | 0.02384264 | lower |
| Candidate rejected / fallback | n/a | 0 / 48 | all representable |

Per-seed r/J relative L2 (baseline -> candidate):
- 131: 0.371788/0.459157 -> 0.107029/0.229584
- 137: 0.376319/0.447175 -> 0.122198/0.221587
- 139: 0.365587/0.442223 -> 0.115961/0.210568

These are impressive restricted P0 representation improvements, NOT
Cherchi teachers, native quadric full-Newton acceleration or validated CAD.

## Cost and limitations

| Mean CPU cost | Original | M9 |
|---|---:|---:|
| Preprocess per rotated test sample | 0.000329 s | 0.006002 s |
| Inference per 16-sample seed batch | 0.009438 s | 0.008926 s |
| Approx. sequential preprocess + inference per 16-sample seed | 0.01469 s | 0.10495 s |

M9 input preprocessing was approximately 18.3x slower; the quoted
sequential combined cost was approximately 7.1x slower. The new method is
an **accuracy win, speed failure** in this setup. CPU timing is an exploratory
benchmark on a small CI runner, not a native/full-system wall-clock claim.

Additional local geometry-only microbenchmark (single synthetic ellipsoid,
angle 0.37 around Z, independent CPU host):
- Grid 8^3: baseline sampled mass error 21.04%, M9 ~0; M9 ten-moment
  covariance relative error 2.03%.
- 16^3: 9.73%, ~0, 0.502%.
- 32^3: 4.68%, ~0, 0.150%.
- 64^3: 2.33%, ~0, 0.0603%.

Key limits: discrete voxel-node mass is not continuum volume; the first
and second moments are only audited, not enforced. Occupied samples outside
the fixed domain cause fail-closed rejection. The projection includes 58
float64 bisection iterations, so a naive 512^3 path is inappropriate.
Low-resolution synthetic task, not arbitrary CAD/SDF or 512^3 proof.

## Decision and next experiment

1. Keep M9 as an **opt-in, source-pinned precision candidate**. Do NOT
   replace the production PINO encoder input or assert runtime gain.
2. Proceed to M9b/M10: per-geometry and per-rotation cache, compact splat
   support, sparse/parallel (or GPU) projection and cost accounting across
   multiple coefficients for one fixed geometry. Preserve default legacy
   behavior and fail-closed semantics.
3. Evaluate larger 16^3/32^3 analytic geometry families and adversarial
   boundary-touching cases; only compare on identical label budget and
   recorded timing. Hold out a new geometry family/rotation distribution.
4. Integrate W0 contract and W2 formally admitted teachers only when
   source provenance, derivative gates, and actual native execution
   receipts permit. No such admission yet.
5. Do not label this mathematical projection as a novel numerical method;
   research contribution would require validated physics-aware integration
   and superior full optimization behavior vs strong baselines.

Claims:
- W2/Cherchi supervision: NO
- Certified full 10x10 native derivative for arbitrary CAD: NO
- Verified Newton/Spin-it Faster acceleration: NO
- Verified 512^3 GPU scale: NO

# W6 M10 — optimization-decision fidelity, analytic P0, independent confirmations

**Write scope:** `volcano-code/Spin_test`, only branch `research/neuralmoments-w6-pcraft-20261019`, under `research/NeuralMoments/models/pcraft_ufno/`. **Parent:** W6 M9 commit `42d9a3b10df7d12d97a7db6e076d2306b8f0c6ae`. Frozen Spin/Cherchi source remains `0bcc187b3005478baa586a6d6f450e73811ca342` and P-CRAFT source remains `volcano-code/test@24eda3e9b3f87ba16251a9025761986d6cfe3079`.

## Research question

On W5 M13's new genuinely matched 4-channel centered-cell P0 input, the source-pinned W6 M7 had **lower r/J MAE**, but only **74.17%** one-step analytic candidate acceptance (versus W5 DeepONet **85.83%**). This milestone separates raw moment, Jacobian and goal-gradient errors rather than mistaking mean r/J prediction accuracy for useful decisions. This is NOT a 10D arbitrary-quadric Newton solver or real native Cherchi experiment.

## Pinned read-only dependencies

- W6 original M7 `m7_realizable.py`, blob `a0e45b278de050329bed60cf5cb2b27e2fdd3c64`, original W6 M7 commit `9d1758ea1ef527577b835f2b6bcfc5f0439d933d`. All W6 predecessor modules are unchanged in GitHub.
- W5 M13 observed `33363d833d0623627afb2a7d5eff5dde5c46dffc`. The four-channel depthwise spatial encoder was transcribed from W5 `m8_voxel_models.py` blob `317bcf1c3965326ee56b5948b80b01bbd052b592`; its original DeepONet head was already archived in W6 `w5_snapshot` as blob `7aa363769c0baf9f843d50e268164e761b566977`. W6's new `m10_w5_readonly.py` is an **independent composition** matching those operations/parameters, NOT a claim that this new file has W5's original Git blob SHA. It does not write W5.
- W2 current observed M13 has **0 independently admitted training/J labels**, historical 81 H8f candidates all excluded. No archived W2 material is read, fitted or evaluated here; current W0/W2 native full material/smooth derivative and Newton terminal gates remain blocked.

## Implemented files

- `m10_w5_readonly.py`: source-matched, 13,939-real-parameter W5 voxel DeepONet comparator. W6 M7 baseline and W6 directional training arm each have 13,448 real trainable parameters (difference <5%). All use the SAME freshly constructed 4-channel centered-cell voxels, controls, r/J references, geometry split and batch schedules. No family ID or exact primitive parameters enter the neural geometry encoder.
- `m10_decision.py`: chain rule `dc/dh` for W0 native unit `c(h)`; same regularized and trust-clipped 1D Gauss–Newton formula as W5 M13 (`damping=.01`, `trust=.12`), plus model-only predicted backtracking, special positive vertical-slice mass-monotonicity guard and charged true-oracle backtracking. **Only the latter** uses independent analytic poststep r during candidate selection. All strategies share goal `r_truth(h+.12)` as the prescribed objective; its analytic construction and retrospective candidate truth auditing are accounted separately, not hidden as model inference.
- `m10_experiment.py`: fresh training with 20 boxes + 20 spheres (8 entire geometries validation-only), 2 controls per geometry, then 20 unseen ellipsoids × 2 independent height controls. Six seeds in two precommitted groups: `[67,71,73]` and `[79,83,89]`. Adam lr=.003, batch8, validation-only early stop, maximum 100 steps, `MSE(r)+.5 MSE(Jc)` for all. Extra W6 arm adds `2.0 MSE((Jc-Jtruth) dc/dh)` **using the same existing analytic J labels**, therefore **no extra supervised teacher calls**. No heldout-ground-truth feedback into training, early stop or oracle-free policies.
- `test_m10.py`: 22 independent checks of W0 chain rule and analytic derivatives, trust/damping limits, exact W5 GN formula, oracle query accounting, no-oracle separation, byte-stable model capacity, source input family identities, replay consistency and tiny end-to-end optimization.
- `m10_three_seed_cpu.json.gz`, `m10_confirmatory_seed79_83_89.json.gz`: complete machine-readable three-model, per-seed training, heldout r/J/directional and every policy's outcomes (including failure case identities), with CPU phase timing.
- `m10_summary.json`: six-seed aggregate, error-source counterfactual attribution, charged selection oracle/surrogate budgets and an **exploratory** geometry-cluster bootstrap, 120 independent geometry groups (two controls/group), seed `20261020`, 5,000 replicates. Reported CI is not a native-material or publication-grade statistical claim.

## Actual local execution and reproduction

Python 3.13.5, PyTorch 2.10.0+cpu, NumPy 2.3.5; **one CPU thread**, no native build/CUDA/archived Cherchi J or remote GitHub CI. Run from the repository root:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m unittest \
  research.NeuralMoments.models.pcraft_ufno.test_m4 \
  research.NeuralMoments.models.pcraft_ufno.test_m5 \
  research.NeuralMoments.models.pcraft_ufno.test_m6 \
  research.NeuralMoments.models.pcraft_ufno.test_m7 \
  research.NeuralMoments.models.pcraft_ufno.test_m8 \
  research.NeuralMoments.models.pcraft_ufno.test_m9 \
  research.NeuralMoments.models.pcraft_ufno.test_m10 -v

python -m research.NeuralMoments.models.pcraft_ufno.m10_experiment \
  --seeds 67,71,73 --steps 100 --per-family 20 \
  --output research/NeuralMoments/models/pcraft_ufno/m10_three_seed_cpu.json
python -m research.NeuralMoments.models.pcraft_ufno.m10_experiment \
  --seeds 79,83,89 --steps 100 --per-family 20 \
  --output research/NeuralMoments/models/pcraft_ufno/m10_confirmatory_seed79_83_89.json
```

**158/158 tests passed**, 22 new + 136 old M4–M9, in 2.933 seconds; all newly authored Python modules compiled. The local test mirror uses M4–M9 sources recovered from prior source bundles with their code/test blob SHA checked, plus re-implemented old M2 analytic/support helpers. Its old M3 training tensors at seeds 19/23/29 reproduce the published exact SHA-256. This is **not** an original Git checkout CI or production CAD build. The W5 comparator's first three-seed metrics also replay W5 M13's published `r_MAE=0.02012684`, `J_MAE=0.01425239`, and 1D acceptance `85.8333%` within numerical rounding, validating source/protocol matching.

### Six-seed findings (240 heldout candidate cases per model)

| Metric | W6 M7 | W6 M7 + directional J supervision | W5 voxel DeepONet |
|---|---:|---:|---:|
| r MAE ↓ | 0.009520 | **0.009174** | 0.020444 |
| J MAE ↓ | 0.006348 | **0.006231** | 0.014148 |
| `dr/dh` MAE ↓ | 0.019112 | **0.018747** | 0.033927 |
| GN candidate acceptance ↑ | 74.17% | 76.67% | **78.33%** |
| Goal-gradient sign errors ↓ | 25.83% | 23.33% | **21.67%** |
| Candidate acceptance when **only current true r is substituted**, using model J (offline diagnostic) | 100% | 100% | 100% |
| Candidate acceptance when **only true J is substituted**, using predicted r (offline diagnostic) | 75.83% | 77.08% | 78.33% |

**Conclusion:** For this strictly one-dimensional positive-cut/known-goal analytic test, moment error drives almost all wrong **goal-gradient signs**, even when the mean moment MAE is small. Retrospectively substituting true r with estimated J repairs the candidate acceptance in every tested case, while substituting true J with estimated r does not. Neither substitution is available for free in production, and the conclusion must not be generalized to arbitrary 10D quadrics or unknown native material/derivative branches.

The directional J loss helps W6 acceptance by **+2.50 percentage points** (six-seed mean, same supervised r/J labels, no new oracle calls) and recovers six previously rejected test cases without introducing a new rejection in these particular data. A geometry-cluster bootstrap yields **[+0.42, +5.00] percentage points**, conditional on this synthetic family and six seeds. It remains **1.67 points below W5** in the six-seed mean, and the corresponding bootstrap W6-versus-W5 difference interval includes zero; do NOT assert a significant winner on real CAD.

### Candidate policy and query-budget accounting

| Policy | W6 base accepted | W6 directional accepted | Additional per-case *selection* calls |
|---|---:|---:|---|
| GN as in W5 M13 | 74.17% | 76.67% | 0 native/analytic oracle; no additional warm head |
| Surrogate-only predicted-backtrack | 74.17% | 76.67% | **+1 cached surrogate moment call**, 0 external oracle; no improvement |
| Monotone-mass-sign guard (vertical cut only) | **71.25%** | **73.75%** | 0 external oracle; **degraded** outcomes |
| True-oracle checked backtrack | 83.33% | 84.17% | **~1.78 / 1.70 analytic material queries per candidate** for selection; *not an acceleration result* |

All policies use the same goal shape/target and all outcome comparisons are evaluated against independent analytic truth *after* selection. For the checked policy, actual oracle calls used in selection are separately charged; offline auditing and the supplied goal label are not silently included as inference operations. These relative budgets are mathematical oracle-call counts; no certified native Cherchi runtime is implied. A true oracle backtrack on real CAD can easily cost more than it saves.

**Known policy failures:** The model-only backtrack typically accepts its first proposal and achieves no acceptance improvement; the sign prior may hurt because a biased *predicted* current mass can point the wrong way. Oracle-checked backtrack helps because it pays for real evaluations. No zero-oracle, generally useful policy has yet been proven beyond the small W6 training loss improvement.

### Source, performance, and honesty gates

- Each model encodes geometry once and reuses cached z for candidate c changes; uncompiled CPU encode, r and 10×10 J timing medians are in both full JSON reports and `m10_summary.json`. The W6 10×10 J is its **surrogate** derivative, NOT smooth native Cherchi J.
- The original W6 M7 nonnegative **atomic** moment structure and tangent `Jc` remain unchanged. The experiment uses a goal constructed from analytic truth: this explicitly simplifies the 1D optimization, and the oracle substitutions are not deployable prediction methods.
- Inputs here are analytic center-sampled voxels. They are not source-signed CAD volume fractions, exact Boolean materials, thin walls or real mesh families. W2 M13 still has zero independently admitted `(r,J)` training records and 81 historical excluded H8f candidates. No cross-window branch modifications, real Cherchi native evaluations, GPU/VRAM verification, arbitrary 10D Newton/KKT convergence, speedup claims, or fake CI.

## Next priority after M10

Focus on **geometry-conditioned moment-bias calibration** and **trustworthy current-state cached r** (count any authentic oracle query needed to obtain it), then independent same-source 8³/16³/24³ voxel-cell/integral M11 tests with no privileged analytic shape descriptors. Only after actual W0/W2 certified material labels and derivative categories become admissible can this proxy be tested against full native optimizer decisions and terminal results. Do not simply add more spectral-network candidates without solving the accuracy-to-decision gap.

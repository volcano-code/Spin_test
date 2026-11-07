# W6 M10b — Three-arm held-out analytic training and 32^3 confirmation

Date: 2026-11-07
Branch: `research/neuralmoments-w6-pcraft-20261019`
Main backbone: pinned P-CRAFT factorized-FNO/U-FNO Spin-PINO.
Status: **completed analytic CPU comparisons; sparse multiscale NOT promoted**.

## Source and real cloud execution

Implementation: `m10b_train.py`; three-way feature-ablation extension of
`m10_sparse_detail.py`; tests `tests/test_m10b_train.py`.
Immutable source/validation commits:
- M10b three-arm code: `0226582d176126fd5fbd7907f462c8cd3a882457`
- Confirmatory 32^3 protocol/CI: `8e6fc5be31fc72a6e4cbca565f89e7e81c8f394f`.

Real GitHub Actions:
- **16^3, 60 steps, 3 seeds:** https://github.com/volcano-code/Spin_test/actions/runs/42353625702
  (success, 11 tests passed, 0 failures).
  Artifact: `w6-m10b-three-arm-analytic-p0/w6_m10b_three_arm_analytic_p0.json`.
  JSON SHA-256: `63bc5d23f30c02881b219eec4a1c7de6d9b61a170d3873827e397ed000709f98`.
- **32^3, 180 steps, 3 seeds:** https://github.com/volcano-code/Spin_test/actions/runs/42353827145
  (success, 5 tests passed, 0 failures).
  Artifact: `w6-m10b-confirmatory-32-180/w6_m10b_confirmatory_32_180.json`.
  JSON SHA-256: `462a97b619b0512c8348b6b726d7eda5de92ce6709968d32e6ef787f0007577b`.

Both jobs used Linux CPU, one Torch thread, Python 3.10 and PyTorch 2.5.1.
No GPU, W2 native labels or exact Cherchi optimization was used.

## Frozen arms and fair scope
1. `pino`: unchanged P-CRAFT PINO trunk and support-masked
   quadrature/moment head; **9,608 trainable parameters**.
2. `moments_only`: same trunk, positive bounded reweighting conditioned
   on input-side *discrete full-material* raw ten moments plus their
   fine-versus-coarse differences; no within-bin geometric details.
3. `sparse_multiscale`: identical modules and allocated **12,745**
   parameters as (2) but adds mass-weighted spatial bin/offset detail.
   The moment-only arm has fewer *active* feature parameters despite
   matching total allocated parameters. Do NOT claim equal effective
   model capacity or FLOPs.

All arms share initial PINO weights, geometry-disjoint split IDs,
native coefficient query order, fit label budget, optimizer steps,
Adam/validation-only checkpoint selection; analytical label source:
`ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI`.
Fit/validation = different boxes/spheres; test = entire ellipsoid family,
not included in fit or model selection.
The source 16^3 and 32^3 datasets are distinct; each arm within a run
has identical source/cut labels and data SHA-256.

## Pilot: 16^3 source, 8^3 PINO, 60 updates/seed/arm

Per seed: 12 fit geometries (24 fit queries), 4 validation geometries
(8 queries), and 5 held-out ellipsoid geometries (10 queries).

| Arm | r relative L2 mean, lower better | J relative L2 mean | r MAE mean | J MAE mean | mean training s | mean test encode s |
|---|---:|---:|---:|---:|---:|---:|
| PINO | 0.1367005954 | 0.2247336755 | 0.0083365043 | 0.0049952259 | 0.7735 | 0.01323 |
| PINO+moment summary | 0.1075532784 | 0.1587622613 | 0.0072521248 | 0.0041472864 | 0.9003 | 0.01858 |
| PINO+multiscale | 0.1013801098 | 0.1551336497 | 0.0069663953 | 0.0041050346 | 0.9842 | 0.02050 |

Multiscale average r/J relative error -25.84%/-30.97% vs PINO;
-5.74%/-2.29% vs fine-moment-summary arm.
But seed 131 r worsened **0.10963 -> 0.12663** vs PINO.
The auxiliary arms selected step 60 for all seeds, an indication the
pilot budget may have been restrictive. No default promotion.

Per-seed held-out r/J relative L2:
- 131: PINO 0.109630/0.136916; summary 0.143584/0.131654;
  multiscale 0.126628/0.129312.
- 137: PINO 0.198378/0.368392; summary 0.086065/0.190554;
  multiscale 0.085658/0.183259.
- 139: PINO 0.102094/0.168893; summary 0.093011/0.154079;
  multiscale 0.091855/0.152830.

## Independent larger follow-up: 32^3 source, 8^3 PINO, 180 updates

Per seed: 18 fit geometries (36 fit queries), 6 validation geometries
(12 queries), and 8 held-out ellipsoids (16 queries).

| Arm | r relative L2 mean | J relative L2 mean | r MAE mean | J MAE mean | mean training s | mean test encode s |
|---|---:|---:|---:|---:|---:|---:|
| PINO | 0.1180210188 | **0.1749962072** | **0.0083223496** | **0.0042637792** | **2.1914** | **0.02060** |
| PINO+moment summary | **0.1159244925** | 0.1830903093 | 0.0083450979 | 0.0045773059 | 2.6405 | 0.02864 |
| PINO+multiscale | 0.1182710032 | 0.1855030656 | 0.0086246142 | 0.0046339547 | 3.3224 | 0.03799 |

Compared with PINO, 32^3 multiscale is **0.21% worse in r**
and **6.00% worse in J** on the held-out ellipsoids. Compared
with summary it is **2.02% worse in r** and **1.32% worse in J**.
Test encoding costs +84% vs the PINO baseline in this small CPU setup.
Seed 139 has particularly clear deterioration:
PINO r/J = 0.117218/0.159044;
multiscale r/J = 0.135896/0.183951.

Per-seed held-out r/J relative L2:
- 131: PINO 0.116902/0.154616; summary 0.111141/0.153982;
  multiscale 0.109972/0.154333.
- 137: PINO 0.119943/0.211328; summary 0.112675/0.216034;
  multiscale 0.108945/0.218225.
- 139: PINO 0.117218/0.159044; summary 0.123958/0.179256;
  multiscale 0.135896/0.183951.

WARNING: the second run simultaneously changed source resolution,
number of geometry instances, and training steps. Comparing run-16
to run-32 does NOT identify a single-factor resolution or budget effect.
Within each run, however, all arms used precisely matched data/steps.

## Final M10b decision — experiment completed, promotion FAILED

- **P-CRAFT PINO stays the only production/default backbone.**
- M10 sparse multiscale remains opt-in research code with
  zero-gate default; no trained high-resolution weights are promoted.
- The 16^3 pilot's average improvement does not survive stronger
  32^3 analytic testing. Preserving negative results prevents false
  attribution of gains to new geometry detail.
- Fine full-material ten-moment metadata is a privileged geometry
  summary of the input, not a cut-specific Cherchi teacher. It helps
  in some small settings but cannot certify `r_D(c)` or
  `J_D(c)` for general CAD.
- Current local sparse pooling is *coefficient-agnostic*. A more
  physically aligned hypothesis is **cut-conditioned local boundary
  interaction**, comparing it with pre-registered controls on a NEW
  held-out geometry/rotation split. Do not tune repeatedly on the
  ellipsoid set just used for model selection.
- Separate **physics/teacher gates**: W0/W2 admitted Cherchi records,
  differentiable event-neighborhood validation, actual native Newton
  speed and Heart/Teapot/Noodles full endpoint remain missing.
- Separate **scale gate**: sparse 512^3 coordinate-domain input exists,
  but no 512^3 full-resolution spectral network, pretrained fVDB CUDA
  backend, true 512^3 GPU gradient benchmark, or memory proof.
- Next step cloud-available: build and test cut-aware *sparse sampling*
  interfaces and a new geometry-disjoint control family. Local-only:
  official CUDA fVDB and high-resolution end-to-end GPU/Spin testing.

This report preserves all three per-seed results, including negative
outcomes, and should not be summarized as 'M10b model wins'.

# W6 P13b — 32³/64³ high-input-resolution density optimization + 128³ CPU gradient

Date: 2026-11-08. W6-only research branch. **P-CRAFT factorized U-FNO/F-FNO remains the only main neural operator**; DensiCrafter is its differentiable material-design module.

Source / test / CI commit: `d36484c79b5a1c1c4000e6486ad7cdaaacbf522f`.
Independent GitHub Actions run:
https://github.com/volcano-code/Spin_test/actions/runs/42391394923
Result: SUCCESS; **11 Python tests passed, 0 failed**. Full artifact:
`w6-p13b-32-64-ablation-128-smoke`, with
`w6_p13b_32_64_four_arm.json` and `w6_p13b_128_smoke.json`.
Artifact ZIP SHA256:
`2b50327630363f892fea81dc7c48a9d842f83577423390d7724f9b33db7f2332`.

## What is different from P13a

- 8³/16³ were only a gradient-safety prototype. P13b actually tests
  **32³ and 64³** density optimization, each with 12 Adam updates, common
  random seed/PINO weights and 2-voxel exact protected shell.
- Four conditions: DensiCrafter-only (mass/CoM/contact/height),
  PINO moment preservation alone, a soft weighted joint objective,
  and a joint objective with independent hard-feasibility filter,
  step shrinkage and rollback.
- Unlike P13a, verify the **10 true cell-centered, discrete HARD-cut**
  raw material moments independently of the PINO model. Cross terms
  obey native `2yz,2xz,2xy` coefficients and undoubled raw moment
  output. Also check full-material normalized nonmass nine moments.
- Reproducibility tests construct two different subcell densities
  with identical 8³ pooled PINO inputs and distinguishable discrete
  cut-moment truth: source resolution alone cannot fix spectral aliasing.

## Measured 32³ (12 optimizer updates each)

| Arm | Discrete mass saving | Model r relative change | Independent discrete cut r relative change | Normalized nonmass 9-moment L2 change | Predeclared constraints passed |
|---|---:|---:|---:|---:|---|
| DensiCrafter alone | 30.70% | 60.99% | 28.48% | 0.09013 | no |
| PINO-only moment keep | 0% | 0% | 0% | 0 | yes, trivial no-op |
| Soft weighted coupled | 30.19% | **0.87%** | **27.89%** | 0.08838 | no |
| Backtracking constrained | **4.84%** | 1.49% | **4.48%** | 0.01029 | yes (5 accepted, 7 rejected) |

## Measured 64³ (12 optimizer updates each)

| Arm | Discrete mass saving | Model r relative change | Independent discrete cut r relative change | Normalized nonmass 9-moment L2 change | Predeclared constraints passed |
|---|---:|---:|---:|---:|---|
| DensiCrafter alone | 42.48% | 60.62% | 40.43% | 0.08751 | no |
| PINO-only moment keep | 0% | 0% | 0% | 0 | yes, trivial no-op |
| Soft weighted coupled | 42.36% | **0.77%** | **40.32%** | 0.08699 | no |
| Backtracking constrained | **4.56%** | **0.19%** | **4.49%** | 0.00427 | yes (4 accepted, 8 rejected) |

Hard-check tolerances were **predeclared**:
model cut-r relative L2 <= 0.045; independent discrete
hard-cut r relative L2 <= 0.045; normalized full nonmass 9-moment
absolute L2 <= 0.04. The filter does not certify true
continuum CAD, stress, physical inertial preservation to tight
engineering tolerances, or native Newton derivatives.

## Actual 128³ CPU test
One 128³ density-PINO forward+backward **passed**, with
2,097,152 source voxels and nonzero finite full-density gradient.
Runtime: **0.3582 s** in its own GitHub Actions process.
Process peak RSS: **642,912 KiB ~= 628 MiB**.
This is only one probe, not a trained 128³ high-resolution operator,
not a GPU peak VRAM measure and not a repeated benchmark.

## Architecture warning (critical)

At every tested resolution this experiment used
`pino.encoder.grid_size = 8`. Any higher-resolution geometric
input was adaptively pooled to **8³** before the P-CRAFT Fourier
trunk. The PINO head also samples only a fixed 4³ quadrature node
set. Hence strong failures can hide behind very low PINO surrogate
error; the soft-weighted 64³ experiment shows **0.77% model change**
while independently integrated material moments changed **40.32%**.
This cannot be called a 64³ neural operator or an accurate Spin
optimization. A high-resolution internal Fourier/sparse multiscale
path must be tested before claiming 512³ readiness.

## Next requirements

1. Cloud CPU: separate P-CRAFT internal operator grids (16³,32³;
   64³ if feasible), true forward+backward and peak RAM, independent
   moment aliasing; do not conflate input grid with Fourier grid.
2. Fit the PINO surrogate against independent geometry/cut data at
   those resolutions, not just initialize random PINO weights.
3. Replace soft-only objective selection with independently verified
   constraints and a manufacturable unit-aware wall thickness.
4. Local 4090 and independent fVDB toolchain: genuine sparse
   256³/512³ native CUDA stress and material occupancy sweep.
5. Only formally admitted W0/W2 Cherchi geometry/J receipts can
   establish real CAD accuracy and Newton derivative safety.
6. TRELLIS/MuJoCo, actual toolpath/print and full physical strength
   still require their own native tests.

This is a **useful negative physical-fidelity result and positive
high-input-density integration test**, not high-resolution end-to-end
Spin-it Faster success.

## Independent cloud CPU proof: true P-CRAFT internal Fourier grid 16³/32³/64³/128³

This experiment is a NEW capacity gate, independent of the 32/64
density-optimization run above. It executes one true P-CRAFT
factorized-U-FNO full forward+backward and material-density
autograd per independent CPU process, with fixed small model
configuration: width=4, modes=2, n_layers=2, 4³ quadrature nodes.
**There is NO trained high-resolution teacher or 512³ network here.**

- Source pin: `4ab7c849f895b1b07743db19dbf0e1afe5a9a2f7`.
- GitHub Actions 64-input / 8,16,32,64 real Fourier, plus 128-input
  / 32 Fourier: https://github.com/volcano-code/Spin_test/actions/runs/42391852853
  **SUCCESS; 2 explicit aliasing and physics contract tests passed.**
  ZIP SHA256: `d038dd256afc59c7f2cf04e6b29961d701d23fdf6b2bcf5300690e7ae9106095`.
- Source pin for separate actual 128³ Fourier test:
  `387ebd2ef441a19f4427c904248f7478991404ce`.
  https://github.com/volcano-code/Spin_test/actions/runs/42392034359
  **SUCCESS; native 128³ Fourier/Densi density forward+backward**.
  ZIP SHA256: `afe7849bfc1bb5f109fd133401563f8a40f43c7835ed81e9f77a5007ff03f4e2`.

| Source density input | PINO internal Fourier grid | One CPU forward+backward | Maximum process RSS | Distinguishes the constructed fine source at preprocess? |
|---|---|---:|---:|---|
| 64³ | 8³ | 0.0554 s | 396.6 MiB | No (max diff=0) |
| 64³ | 16³ | 0.0569 s | 400.5 MiB | Yes (max diff=0.30) |
| 64³ | 32³ | 0.0785 s | 411.8 MiB | Yes (max diff=0.30) |
| **64³** | **64³ actual Fourier** | **0.4714 s** | **483.3 MiB** | Yes (max diff=0.30) |
| 128³ | 32³ | 0.4677 s | 854.0 MiB | Yes (max diff=0.30) |
| **128³** | **128³ actual Fourier** | **4.4957 s** | **1,313.2 MiB / 1.28 GiB** | Yes (max diff=0.30) |

The independent hard-cut moment difference of the paired density
inputs is 0.0819168 on 64³, and 0.0789809 on 128³. The pairs have
identical 8³ pooled density averages but distinct high-frequency
content, proving loss of information at the *encoder*'s 8³
preprocessing stage, and retained content for grid>=16.
This does not prove the entire trained ten-moment model has
general CAD accuracy at any grid. Even 128³ still uses only 4³
fixed quadrature nodes.

**New conclusion:** The existing GitHub CPU environment can handle
an actual one-step 128³ P-CRAFT F-FNO/U-FNO and differentiable
DensiCrafter density field at the narrowest tested model width.
It is incorrect to call cloud PINO hard-limited to 8³ or 16³.
It remains incorrect to claim 128³ multi-epoch training,
a feasible high-resolution printable solution, or any 512³
CUDA/float32 VRAM capacity. Physical fidelity and efficient memory
scale remain blocking tasks.

The same two-cell protected wall has different physical thickness
across 32³ and 64³ source grids. Their raw mass reductions must
not be treated as a controlled same-wall-thickness resolution study.
The independent discrete cut moment is cell-centered, not a
Cherchi-certified continuous CAD/Boolean integral. The P13b
feasibility threshold 4.5% is an exploratory test gate, not a
manufacturing-accuracy or native Newton guarantee.

## Updated cloud vs local recommendation

- **Cloud now:** 32³/64³ multi-objective optimization and narrow
  128³ original PINO forward/backward have both been demonstrated.
  Next train/fine-tune PINO on truly independent 32/64/128 source
  cut labels, implement per-resolution physical wall units, and
  test mass/CoM/inertia preservation via independent quadrature.
- **Local GPU:** match official fVDB/CUDA/PyTorch versions in a separate
  environment and perform 256³/512³ sparse density and PINO feature
  training, with peak VRAM, throughput, occupancy percentages and
  cut-moment fidelity; preserve PINO as sole main neural backbone.
- **Native W0/W2/Cherchi:** only admitted true derivative neighborhoods
  may authorize Newton and full Heart/Teapot/Noodles Spin speedups.

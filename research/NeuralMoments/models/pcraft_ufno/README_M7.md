# W6 M7 — bounded atomic material moments + native tangent derivative

**Branch:** `research/neuralmoments-w6-pcraft-20261019` in `volcano-code/Spin_test`.
**Exclusive write scope:** `research/NeuralMoments/models/pcraft_ufno/`.
**Frozen source:** `0bcc187b3005478baa586a6d6f450e73811ca342`.
**Pre-M7 W6 HEAD:** `27d51678cf741233c7a2e6c54c78d9a4667bec00`.
**Read-only W0 observed:** `64fa50ca171bc8e964edc5ded5e0b967cbbdb0a8`.
**Read-only W2 observed:** `36eb96a0abac1e1b6620264ac79b83f3345bbcb4`.

## Why another architecture?

M5/M6 convex one-homogeneous potential had exactly symmetric/PSD
`Jq=Jc B^-1`, but that alone did **not** guarantee a valid nonnegative
material measure; an all-empty probe could produce negative mass. M6
added a reject/strict-state gate but did not make generic cut predictions
structurally realizable.

**M7 implements the stronger, carefully limited condition of
realizability as a nonnegative *discrete atomic measure* on a known
quadrature grid.** For each input D (`rho`, occupancy, SDF, inner boundary),
learn a geometry-only correction `g_k= sigmoid(head(z_D))` and sample the
supplied nonnegative density and occupancy at fixed Gauss nodes:

`w_k(D) = positive_quadrature_volume_k * rho_k * occupancy_k * g_k`,

`r_i(D,c) = sum_k w_k(D) sigmoid((Bc)·m_k / (tau ||c||)) m_{ki}`.

Here `m=(1,x,y,z,xx,yy,zz,yz,xz,xy)` are **undoubled** raw monomials,
`c=(const,x,y,z,xx,yy,zz,yz,xz,xy)` are **native symmetric-matrix entries**,
and `B=diag(1,1,1,1,1,1,1,2,2,2)` supplies the polynomial factors of 2.
Each `alpha_k` lies in `[0,1]`; the ten moments are *literally moments* of a
nonnegative bounded atomic measure supported inside `[-1,1]^3`. This implies
nonnegative mass, the PSD covariance condition and axis-aligned support
moment inequalities, subject to floating-point tolerances. A learned network
cannot create material where the sampled density or occupancy is exactly 0.
No field decoder or repeated geometry encoding is required for multiple `c`.

### Derivative semantics — important limitation

The analytical `Jc=dr/dc` is the exact derivative of this *smooth surrogate*.
The normalized temperature `tau||c||` ensures positive projective scale
invariance, and `Jc c≈0`, but it also means **ambient `Jc B^-1` is not
symmetric** in general. It must NOT be passed to W0 as a smooth-continuum
symmetric ambient native Hessian. M7 supplies a native orthonormal 10x9
basis `V` perpendicular to c, and `Jt=Jc V` for tangent-mode reporting.
If `n=B^-1 c` and `P=I-n n^T/(n^T n)` in polynomial-q space, then
`P (Jc B^-1) P` is a symmetric PSD tangent Gram under this architecture.
This is a **model property**, not true native Cherchi derivative validity.

Strict all-empty/all-full quadric signs on the bounded cube are resolved with
the M6 exact-binary-rational interval classifier and return `r=0` or the
full cached atomic measure respectively, and `J=0`. Other cuts retain the
nonnegative atomic estimator. The existing fixed material remains a
separate constant `r_F`: `r_total=r_F+r_D`, `J_total=J_D`.

### Explicit exclusions

- This is a *quadrature-atomic* existence guarantee, **not** a 3D Boolean
  material region certificate, exact original CAD volume integrator, wall
  thickness proof, manufacturability validation or a learned exact Cherchi solver.
- Discrete positive atomic masses may not equal the moments of the true
  continuous retained object. Interpolated occupancy is a sample-based proxy.
- W2 M9 historical **81** physical candidate points are kept in `excluded`,
  all derivative labels are withheld and `training_samples=0`. They have
  **not** been used for training/validation/holdout here.
- Actual real native optimization, convergence, Newton terminal, and GPU
  memory/speed have not been measured; previous failed native preflight is not
  rewritten or hidden. W5's 9D voxel statistics remain a lossy representation
  of the same raw voxel source, so architectural information parity is absent.

## Code / tests

- `m7_realizable.py`: material-masked Gauss weights, exact smooth native Jc,
  projective tangent Jacobian and exact strict-sign safe inference.
- `m7_teacher_gate.py`: read-only, fail-closed check against W2 v2 with 81
  excluded archived candidates; forged verified status or positive counts do
  not unlock training.
- `m7_experiment.py`: deterministic M3/M4-matched P0 experiment with early
  stop by distinct geometry IDs and independent held-out ellipsoid families.
- `test_m7.py`: 25 new tests for geometry cache, weight support,
  finite-difference Jc (including tangent directions), Gram PSD, projective
  scaling, full/empty, invalid data, fixed material accounting and W2 gate.

From repository root in Python 3.13, torch 2.10.0 CPU (NumPy installed):

```bash
python -m unittest \
  research.NeuralMoments.models.pcraft_ufno.test_m7 \
  research.NeuralMoments.models.pcraft_ufno.test_m4 \
  research.NeuralMoments.models.pcraft_ufno.test_m5 \
  research.NeuralMoments.models.pcraft_ufno.test_m6 -v
python -m research.NeuralMoments.models.pcraft_ufno.m7_experiment \
  --seeds 19,23,29 --steps 400 --per-family 20 --repeats 5 \
  --output research/NeuralMoments/models/pcraft_ufno/m7_fair_400_three_seed_cpu.json
python -m research.NeuralMoments.models.pcraft_ufno.m7_experiment \
  --seeds 31,37,41 --steps 400 --per-family 20 --repeats 5 \
  --models lite_m7_tau012,lite_m6_gauss025,w5_deeponet \
  --output research/NeuralMoments/models/pcraft_ufno/m7_confirmatory_400_cpu.json
```

The two committed full JSON reports are gzip compressed, contain exact
per-seed losses/selection steps/CPU times, and can be decompressed with
`gzip -dc ...json.gz` without modifying earlier evidence. The local smoke
returned **87/87 passed** in `m7_all_tests_cpu.log`: 25 M7 plus 62 unchanged
M4–M6 regressions. Remote GitHub CI was **not** run. CPU was single-thread,
no GPU or native build used. Local files were reconstructed from W6 archives;
M4/M5/M6 code blobs were verified SHA-identical to the W6 GitHub sources,
but the local `analytic_cut.py` is a *semantic mirror*, not the exact GitHub
blob. Frozen train dataset digests match existing M3 for 19/23/29:
`7b65ebbb...`, `d36d707c...`, `25eece48...`.

## Real CPU experiment — same analytic teacher/query budget

Frozen 40 train geometries (20 boxes, 20 spheres, two physical cuts each),
8 geometry-ID held-out for validation (16 labels), 32 used for fits (64
labels), 20 unseen ellipsoid geometries for test (40 labels); Adam 0.003,
batch 8, max 400 steps, validation score `r_mae+0.25*J_mae`, patience 5.
Each model starts from a matched seed and sees equal label/query budgets.
M7 and M6 Gauss have **13,448 real trainable parameters** each. DeepONet
has 13,674 real parameters (~1.68% more), but less spatial information.

| Seeds 19/23/29, analytic P0 | r MAE ↓ | J MAE ↓ | necessary-condition pass ↑ |
|---|---:|---:|---:|
| M7 temperature 0.12 | 0.02390 | **0.01028** | **100%** |
| M7 temperature 0.25 | 0.02541 | 0.01326 | **100%** |
| M6 Gauss potential 0.25 | 0.02099 | 0.01798 | 31.7% |
| W5 DeepONet | **0.01562** | 0.01530 | 50.0% |

The 0.12 setting was then retained and evaluated on **new seeds
31/37/41** (separate validation/test geometry identities, not used in the
above fitting):

| Seeds 31/37/41 | r MAE ↓ | J MAE ↓ | necessary-condition pass ↑ |
|---|---:|---:|---:|
| M7 temperature 0.12 | 0.02515 | **0.01061** | **100%** |
| M6 Gauss potential 0.25 | 0.02383 | 0.01961 | 35.0% |
| W5 DeepONet | **0.01589** | 0.01389 | 48.3% |

M7 offers a better *analytic P0 J MAE* and 100% discrete-moment necessary
condition pass on these cases, but sacrifices r accuracy relative to W5.
A necessary-condition pass is not a proof of CAD material validity for
W5/M6; M7's stronger construction-level statement is **only** for its
atomic measure, not the input solid. Do not infer real-Cherchi generalization
or native solver speedup. CPU cold/warm timings are in the JSON; they are
hardware-local not reproducible speedup ratios.

## Next required gates (blocked by W2)

1. Independently authenticate original/F/D/retained exact geometry, one native
   Cherchi material evaluation, frozen coordinate/density identities and
   independently re-integrated r_F/r_D with signed provenance.
2. Freeze smooth branch/J-coordinate admission or explicitly use W0 tangent
   basis where actually verified. H8 point60 historical feature changes do
   not support an ambient derivative claim or train split admission.
3. Compare M7 to W5/M6 on **real sealed** held-out CAD families and
   independent Newton optimizer outcome, then GPU/swap-safe timing and 0–2
   *physically constrained* oracle-query adaptation. Unconstrained residual
   fitting risks destroying the atom-realizability guarantee.

# P30.0 — In-trunk material-measure mixing: implemented, NOT promoted

Base: `49655d19bc0471b38b1c3764b822ecdd38894ffd` on the W6 branch only.

## What changed, and what did not

Entry point: `material_core.MaterialAwareSpinPINO`.

This replaces the encoder's block update, not the primary P-CRAFT spectral
operator. The five U-shaped stages now compute

`GELU(IN(F_axis(h) + W_local(h) + tanh(gamma_stage)*R_material(h,D)))`.

The learned partition is generated from the CURRENT trunk feature and eight
material/coordinate descriptors. Slice tokens use positive material measure
`m = rho * occupancy`, not unweighted grid-point counts. Token interactions
include a slice-mass prior. Unsliced increments are support-limited and
projected to zero material-weighted channel mean. Material products and
boundary indicators are computed BEFORE multiscale pooling.

This incorporates the slicing idea of Transolver/Transolver++, positive
measure aggregation from numerical quadrature, and Spin's material support
requirements. No official GINO/QuadrANN/Transolver model is called by the new
core. No claim of first-in-literature novelty or official reproduction is
made. The local occupancy-contrast descriptor is NOT a curvature/thickness
certificate or an exact SDF.

Sources of ideas (not additional imported code):
- https://arxiv.org/abs/2402.02366
- https://arxiv.org/abs/2502.02414

The original P-CRAFT-derived spectral/local operators, U topology, positive
logistic moment head, and analytic coefficient Jacobian are inherited.
The existing `SpinPINO` class and all old checkpoints are left unchanged.
This isolated research entry point is deliberate: negative ablation results
must not silently become the default operator.

## Mathematical scope

With learned partition `A_ik >= 0, sum_k A_ik=1`, slice mass is
`M_k=sum_i A_ik*m_i*dV`; a slice token is its material-weighted feature mean.
The returned increment is `mask_i*(R_i-mu)` with
`mu=sum_i m_i*mask_i*R_i / sum_i m_i*mask_i`.
Thus `sum_i m_i*delta_i=0`, within floating-point tolerance, and delta is zero
at zero material support. This is a LATENT-increment property. It does NOT
prove exact conservation of physical output moments after normalization,
nonlinearities, pooling and the learned head.

The encoder is independent of c. Geometry weights remain cacheable for fixed
D and model parameters; changing rho invalidates the cache. Existing logistic
r and J are still generated from one expression. Only logistic_atom is
admitted by this new research entry point; the smooth_hinge branch is not
certified by these tests. Native Cherchi J and Newton admission remain absent.

## Real execution evidence

Local assistant CPU container: Python 3.13.5, Torch 2.10.0+cpu, NumPy as recorded
in `p30_evidence.json`; one compute thread. No user's 5090 was accessed.
Seven original source files were materialized from connector-read text and
verified against their exact Git blob hashes (recorded in the evidence).
This was not a full repository checkout/test suite and not GitHub Actions CI.

19 mechanism/integration tests passed. They cover zero-gate bitwise baseline
identity, old strict checkpoint loading, material-before-pooling, zero vacuum
response, material-mean-zero increments, active in-trunk effects, density and
internal parameter gradients, nonnegative weights, cached/full-query identity,
logistic Jacobian vs autodiff and finite differences, complement/projective/
radial identities, and checkpoint recomputation outputs/gradients.

The same complete fixed-budget study was run twice. All nine learned state
hashes and all reported error metrics matched exactly; wall times need not.

## Controlled pilot (no test-selected hyperparameters)

24 training geometries, 12 disjoint same-family test geometries, 4 additional
unseen ribbed geometries. Training families: ellipsoid, perforated block,
hollow shell. Four coefficient queries per geometry. Input 16^3, trunk 8^3,
8^3 fixed quadrature points; width 4; 60 optimizer updates per run.

Three seeds: 301, 307, 311. Three arms share the exact baseline initial state
and mini-batch sequence. Uniform and material internal arms additionally
share their initial mixing tensors and have identical parameter counts.
The original baseline has fewer parameters, explicitly disclosed below.

Reference: an independently coded dense cell-centered LOGISTIC SOFT-CUT
integral and derivative at the same temperature. It is neither a hard-cut
continuum derivative nor W2/Cherchi truth. The implicit-field input channel is
a proxy, not an exact signed-distance field. No TRELLIS assets are used.

| Arm | Real parameters | Test r rel-L2 | Test J rel-L2 | OOD r rel-L2 | OOD J rel-L2 |
|---|---:|---:|---:|---:|---:|
| Original PINO | 21,752 | 0.07225410 | 0.09623190 | 0.20305831 | 0.24311226 |
| Uniform in-trunk control | 24,257 | 0.07336798 | 0.09743847 | 0.20586223 | 0.24566791 |
| Material in-trunk core | 24,257 | 0.07231234 | 0.09631774 | 0.20296954 | 0.24302736 |

These are mean per-query relative L2 errors averaged over three seeds.
They are not componentwise error guarantees. The material arm beats the
same-parameter uniform control slightly but DOES NOT improve same-family
accuracy over the original PINO. OOD differences are tiny and not evidence of
statistical superiority. Mean CPU training wall times were approximately
0.960 / 1.799 / 1.892 seconds for these tiny runs; these are not inference or
Spin speedups. More parameters and work are not justified by this pilot.

## Independent limitation diagnostic: fixed nodes can miss material

Input: one occupied voxel at index (3,3,3) of a 32^3 grid; positive constant
cut; the current 8^3 point-sampled head.

- Independent dense soft mass: 0.0002440819662.
- Original PINO predicted mass: 0.
- New material-core predicted mass: 0.

This does not prove the cause of every pilot error. It DOES exhibit a
structural support blind spot which no encoder can fix while all sampled
rho/occupancy values are zero. The next task is material-covering stratified
quadrature / cell moment aggregation, with explicit r and J consistency,
rather than merely adding more geometry networks.

## Decision and next gate

`DO_NOT_PROMOTE_DEFAULT_NO_GAIN_OVER_BASELINE`.

Implementation and model-internal correctness: passed the listed CPU tests.
Accuracy/cost improvement: NOT demonstrated. Larger dataset/GPU experiments,
real upstream side-branch comparisons, teacher labels and full CI remain open.

Next controlled comparison should separate material-covering quadrature from
in-trunk mixing (2x2 ablation), and include tiny components/thin walls. Do not
silently substitute a new sampling rule and attribute its gain to attention.
No cached P25 UQ calibration may be reused for a changed predictor without
fresh error collection/calibration. Separate derivative reliability remains
unimplemented. TRELLIS generation work is independent of these CPU tasks.

## Reproduce from repository root

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m unittest discover \
  -s research/NeuralMoments/models/pcraft_ufno/spin_pino/tests \
  -p test_material_core.py -v
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 python -m \
  research.NeuralMoments.models.pcraft_ufno.spin_pino.p30_pilot \
  --output /tmp/w6-p30-pilot
```

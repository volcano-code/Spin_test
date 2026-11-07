# W6 M9 — bounded discrete-mass conservative SO(3) rotation

Status: experimental candidate; do not promote to default without same-data
r/J improvements and cost evidence. P-CRAFT Spin-PINO remains the backbone.

## Why this approach
M7e/M7f demonstrated that independently interpolating rho and occupancy at
8^3 can change the total sampled product rho*occupancy by about 30% under
arbitrary SO(3); a 5% gate rejected every extra orbit view. Such input
corruption is not cured by simply asking for more views or more loss terms.

M9 rotates occupied **voxel-center samples** by a forward trilinear
mass-and-occupancy splat, then performs two bounded simplex projections:
(1) redistribute occupancy on reached target nodes so 0<=occ<=1 and its
discrete sum equals its pre-rotation value; (2) redistribute material mass on
the same support so 0<=rho*occ<=occ and its discrete sum equals the original
rho*occ sum. The density is the ratio of projected material to occupancy.
Auxiliary signed-proxy/boundary channels still use the old pull interpolation.
Out-of-domain occupied source samples and infeasible capacity are rejected
(fail-closed). Identity rotation leaves the four-channel tensor bit-exact.

## Independent tests and study
- Identity/cube/generic rotation, bounded channels, sums and invalid inputs.
- Ten discrete NODE-QUADRATURE moment covariance residuals are audited,
  not enforced. Mass conservation alone cannot imply correct inertia.
- Frozen 3 seeds 131/137/139, 120-step fit, 8^3 input, 16 held-out
  ellipsoid test queries per seed, exact analytic continuum rotation labels.
- Compare the same trained PINO model on either legacy trilinear-pull input
  or M9 conservative-splat input. All failed M9 samples explicitly fall back
  to legacy input, with rejection counts recorded.
- Record independent pre-processing and inference wall-clock costs, model
  parameter counts, r/J relative L2 and ten-moment sampled covariance.
- Do not tune, retrain, or select configurations using held-out labels.

**Limitations:** sampled-grid mass is not continuum/CAD mass. The method is
nonlocal across voxels and the bounded projection adds substantial cost.
It may worsen r/J predictions from a model trained on legacy inputs,
and may be unsafe for material touching the domain boundary. Do not
claim native Cherchi, Newton, real-model, 512^3 or printer certification.

## Reproduce
python -m pytest -q research/NeuralMoments/models/pcraft_ufno/spin_pino/tests/test_m9_mass_transport.py

OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m research.NeuralMoments.models.pcraft_ufno.spin_pino.mass_transport_sweep \
  --seeds 131,137,139 --steps 120 --output /tmp/w6_m9_mass_transport.json

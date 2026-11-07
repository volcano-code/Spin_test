# W6 M10 — sparse multiscale feature side branch, PINO remains primary

Date: 2026-11-07. Branch research/neuralmoments-w6-pcraft-20261019.
Source baseline: b0a6329f0ff48469ba5317cd78f9cd1e1f96bda4.
All edits restricted to W6's pcraft_ufno/spin_pino subtree and a W6 CI file.

## Why M10
M9b can accept source indices from a 512^3 coordinate domain but the
PINO trunk still pools the material into a small dense grid. M10 is an
opt-in, additional **sparse feature path**, which sees original voxel
coordinates and their subcell offsets even if the dense coarse PINO input
is exactly identical. It does not replace the P-CRAFT U-shaped F-FNO.

## Architecture
- P-CRAFT SpinPINO is still responsible for support-masked nonnegative
  quadrature atoms, moment_from_weights and jacobian_from_weights.
- SparseMultiscaleDetail groups valid source voxels by sparse bins at
  declared levels (e.g. 16,32,64 for 512 input), and aggregates
  density*occupancy-weighted positions and second-order local offsets.
  torch.unique/index_add avoids dense level^3 or 512^3 allocations.
- Independently measured fine-grid cell-centered ten moments and their
  coarse-grid discrepancies are geometry descriptors, NOT teacher labels.
- A bounded learned correction multiplies the PINO quadrature by a positive
  factor. A zero-initialized gate is **bit-exact PINO-only** on first use;
  an active gate can make geometries with identical coarse grids different.
- PINO moment and derivative heads are preserved, so trained corrections
  must not introduce atoms beyond the original support. These are
  model-internal algebraic guarantees, NOT true CAD derivative admission.

## Cloud CPU gates
1. Zero-gate r/J must exactly match the original PINO.
2. Two 32^3 sparse geometries with identical coarse 8^3 inputs but
   distinct within-cell locations must produce distinguishable features
   when gate is enabled; report actual numerical change, not accuracy.
3. 512^3 source coordinate sparse smoke: 4096 records, 16/32/64 bins,
   no dense 512^3 grid or FFT, 10x10 Jacobian finite.
4. Reject invalid levels and bad/duplicate material records.
5. No degradation of M9b source-bound caches and original M9 tests.
6. Push source, logs, benchmark JSON and status, and avoid promotion to
   default without multi-seed trained accuracy and runtime evidence.

## Explicit exclusions
This is NOT the original fVDB/PhysicsNeMo FIGConvNet code or a 512^3 GPU
operator; full fVDB CUDA build is a separate task requiring compatible
local driver/toolchain. This M10 module is a PyTorch proof of the
spatial-detail integration port. Training data do not yet include W2
formally admitted Cherchi teachers. 512^3 generic dense CAD operation and
complete Spin Newton acceleration remain unverified.

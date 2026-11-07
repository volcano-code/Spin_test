# W6 M9b — cached fixed-geometry queries + sparse-512 input bridge (CPU evidence)

Date: 2026-11-07. W6-only branch `research/neuralmoments-w6-pcraft-20261019`.
Parent result: W6 M9, 2026-11-07 (accuracy gain, runtime regression).
Source commits:
- `c01d9a2737c65232d1ea6da9d2f40e8c25552421`: opt-in, exact-byte source and model state caches + sparse material bridge.
- `3823b94f30935b7912da29daddffed4a54e1016a`: scalar-tensor hash fix, source-bound/LRU/gradient tests, isolated CI and benchmark.
- `774fb89a66b3966ed2aeae834fc3740f6ea21e98`: 512-index sparse-to-*reduced*-PINO ten-moment/Jacobian forward validation.

## Verified GitHub Actions
Latest independent M9b run:
https://github.com/volcano-code/Spin_test/actions/runs/42345628225
All steps successful; 16 tests passed, 0 failed in 1.70 s.
The tests include original M9 transport regression tests.
Artifact: `w6-m9b-cache-sparse-evidence/w6_m9b_cache_sparse.json`
Source artifact JSON SHA-256:
`01ad01481442aa86a63b75673e694bb4f454975b639b7d38927649455b629cf2`

### Six **repeated coefficient queries** on one unchanged 8^3 geometry and R
All neural weights are RANDOM / untrained; this is a CPU compute and
data-equality check, not a fitted-accuracy metric.

| Condition | Total time for six queries |
| --- | ---: |
| Recompute M9 transport and PINO encoding for every c | 47.9068 ms |
| M9b exact-source rotation+PINO geometry caches | 12.2812 ms |
| Measured CPU time ratio | 3.9008x |
| Rotation cache | 5 hits / 1 miss |
| PINO latent cache | 5 hits / 1 miss |
| Max absolute r and J difference | 0.0 |

The previous CI run 42345431734 recorded 43.798 ms / 12.177 ms
(3.5968x); timing varies with the CI worker. Neither number establishes
end-to-end native optimization speed or benefit for one-off rotations.

### 512^3 SOURCE COORDINATE DOMAIN: sparse/reduced pipeline ONLY
The synthetic input contains exactly 4,096 active material voxel records
at declared 512^3 cell-centered coordinates, NOT a full 512^3 tensor and
NOT a realistic occupancy stress test. Joint mass/occupancy coarsening
produces a [1,4,16,16,16] tensor, retaining the original-resolution
ten-moment diagnostic ledger independently. A RANDOM SpinPINO with
internal grid size 8 then processes that reduced tensor and returns
finite r[1,10] and J[1,10,10].

| Measured quantity | Result |
| --- | ---: |
| Input records (indices + four material channels) | 4,096 |
| Raw sparse input storage (not peak RAM) | 196,608 bytes |
| Reduced four-channel tensor | 65,536 bytes |
| Sparse-to-reduced-grid CPU step | 1.63235 ms |
| Reduced PINO r/J CPU forward | 3.13029 ms |
| Discrete total mass relative error | 0.0 |
| Fine-to-coarse ten-moment relative drift | 0.00233332 |
| Actual 512^3 full-resolution FFT | NO |
| fVDB official source/CUDA integration | NO |
| 512^3 GPU neural training | NO |
| Native Cherchi/Spin optimization admission | NO |

The sparse interface preserves the **total cell-centered material mass**.
It does not constrain the other nine moments, and it does not preserve
spatial detail lost by downsampling. The diagnostic moment drift is
nonzero even in this extremely sparse test. Its input contract rejects
duplicate indices, nonzero unknown SDF/boundary proxies and negative/
invalid material values instead of fabricating them.

## Adoption decision
- Accept the opt-in M9b source-bound cache as a verified optimization for
  **repeated identical geometry+R with changing native coefficient c**.
- Do NOT replace the default M9 geometry path based only on this microbenchmark.
  Hash/model-state verification also has a real, workload-dependent cost.
- Accept the 512^3 sparse material-only ingestion contract as an
  independently tested API slice, **not** 512^3 PINO support.
- Production PINO continues using the P-CRAFT factorized F-FNO U-shaped
  trunk and task-specific ten-moment head; original M9 accuracy and
  numerical reference results remain unchanged.
- Required next milestone: truly multi-resolution geometry feature path
  that *retains* 512^3 boundary detail without dense 512^3 FFT; pinned
  fVDB official source CUDA prototype and optional PhysicsNeMo FIGConv
  features must compete as subordinate adapters against the same PINO
  trunk, with matched data, material truth, costs and license receipts.
- Official fVDB 0.6 installation matrix (2026 documentation) specifies
  PyTorch 2.13 and CUDA 13.0/13.2. W6 CPU CI is pinned at Torch 2.5.1;
  therefore do NOT install fVDB 0.6 into the existing W6 CI. Build
  a separate local GPU environment and verify toolchain/driver before
  attempting to reuse original CUDA fVDB code.
  Source: https://github.com/openvdb/fvdb-core/blob/main/docs/installation.rst

No neural-model accuracy improvement, full 512^3 learning, arbitrary
CAD/H9 derivative certification, Newton admission or full Spin/Faster
speedup is claimed in this M9b artifact.

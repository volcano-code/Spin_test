# W6 M13 — same-source indexed mesh and conservative voxel-cell material moments

Repository: `volcano-code/Spin_test`; write ONLY `research/neuralmoments-w6-pcraft-20261019` under `research/NeuralMoments/models/pcraft_ufno/`. Parent: `bfa8d0c767fc3cb69216db6a8a2801e200b43365`; frozen original Spin: `0bcc187b3005478baa586a6d6f450e73811ca342`.

## Why M13 is scientifically different from M9

M9 received analytic ideal primitive center/axis specifications to build capacity; the old M7 geometry input was just a coarsely sampled 4-channel volume. This introduced **privileged side information** unavailable to the learned W6/W5 networks. M13 eliminates that difference: the **only preprocessing geometry** is the submitted indexed `(vertices, faces, density)` mesh. The mesh-derived *same* 4-channel `D` is used for both W6 M7 and the read-only source-pinned W5 4-channel DeepONet. The mathematical truth label is obtained from a **separately computed planar clipping and integration of this exact indexed triangulated surface**, not the source analytic primitive that generated it. No source-label channel, ideal axes/center, prior target r/J, or cut-side labels enter the encoder.

This is still a **synthetic P0 experiment using numerically triangulated convex box/sphere/ellipsoid meshes**, not original author CAD, not GMP rational or Cherchi Boolean proof, not arbitrary 10-parameter quadratic cut.

## Four new implementation modules

- `m13_mesh_source.py`: SHA-bound `FrozenTriMesh` verifies finite coordinates in `[-1,1]^3`, distinct nondegenerate indexed faces, reversed edge-pair closure, positive signed volume; an explicit *not certified CAD* disclaimer remains. The deterministic 3D solid-angle winding test computes sampled material, with all intersecting triangle-AABB cells treated as unresolved. Returns 4-channel `[intrinsic rho, cell occupancy fraction, zero SDF placeholder, boundary_uncertainty]` at 8³/16³. For boundary cells, sample 1³/2³/3³ subcells to estimate occupancy, **but** use `[0,1]` conditional conservative bounds, not sample outcomes as proof. Every source/voxel byte identity is independently pinned.
- `m13_cell_integrals.py`: strict float32 frozen **center-cell** D bind; integrate all ten *undoubled* raw moments of the declared piecewise-constant voxel proxy exactly for positive unit vertical native `c`. Compute local continuous 10×10 `Jc` via boundary Gram `Jq = Jc B^-1` with B diagonal `1,1,1,1,1,1,1,2,2,2`; check symmetry, PSD, radial identity, FD. Reject oblique, quadratic, negative or nonunit native c. When the plane hits a voxel layer boundary, publish r but withhold derivative. Strict full/empty outside grid: return J zero. Fixed F is NOT added and variable D is not conflated with total r. Mesh bounds combined with the exact planar cell occupancy g yield Fréchet mass bounds `max(0,lo+g−1) ≤ intersection_fraction ≤ min(hi,g)`. This is conditional on a legal embedded closed mesh and does NOT prove source CAD geometry.
- `m13_mesh_cut.py`: independently compute numerical ten-moment source-mesh labels via oriented surface triangles clipped by an interior vertical plane, plus a convex-cap triangulation. A positive degree-5 Dunavant triangular rule integrates the degree-4 surface Gram, yielding the **numerical** local true mesh `Jc` for smooth vertex-event-free vertical P0. Reject nonconvex/multi-component inputs and withhold J at mesh-vertex events. This is a new P0 mathematical reference, **not** W2 native Cherchi teacher labels.
- `m13_experiment.py`: randomized mesh-generation-only source setup, with boxes/spheres in fitting/validation and held-out ellipsoid **indexed meshes**. Separate labels (computed only from mesh), SHA-auditable dataset IDs, parameter-matched W5 vs W6 training, 8³ vs 16³ representation, single CPU-thread timing, and complete per-seed raw results.

## Locally executed evidence and sample sizes

Python `3.13.5`, PyTorch `2.10.0+cpu`, NumPy `2.3.5`, single CPU thread, CUDA/GPU hours 0. Source mesh generation uses `trimesh` only to construct deterministic indexed test inputs. Three **fresh seeds 131,137,139**. Representation: **27 independent meshes** (box/sphere/ellipsoid; 3 of each per seed), two independent cut controls per mesh = **54 test cuts**. Neural experiment per seed: 10 training boxes + 10 spheres, 2 controls/mesh = 40 labels; 4 complete meshes / 8 labels reserved for validation, 16 fit meshes /32 fitting labels. Holdout **6 new ellipsoid meshes** /12 novel controls per seed. 80 maximum steps, Adam .003/batch8, full source r+0.5J loss, validation-only checkpoint; identical seeds, minibatch schedule, four-channel D, label source and geometry-family split. W6 13,448 and W5 13,939 real parameters (~3.65% mismatch). No historical FEM checkpoint used.

### Source mesh vs same-voxel proxy numerical error (lower is better)

| Input source strategy | mean full-mesh mass relative error | mean cut r MAE | mean cut Jc MAE | mean conditional cut-mass bracket width relative to mesh truth | bracket coverage | mesh rasterization ms/mesh |
|---|---:|---:|---:|---:|---:|---:|
| cells16_sub2 | 1.662% | 0.004332 | 0.002179 | 126.3% | 54/54 | 357.3 |
| cells8_sub1 | 4.692% | 0.012512 | 0.006976 | 219.1% | 54/54 | 25.6 |
| cells8_sub3 | 1.955% | 0.006401 | 0.003839 | 219.1% | 54/54 | 142.4 |

**Important:** 54/54 *conditional* interval coverage is not geometric/CAD certification. Bracket widths of approximately 219% on n8 and 126% on n16 are **too loose** for proof of precision. The improved estimates come with substantial rasterization time (8³ 3³ ~142ms, 16³ 2³ ~357ms per mesh, single CPU thread), and no actual end-to-end Faster acceleration is demonstrated.

### Actually trained matched models, same mesh-derived source

| New-seed model | r MAE ↓ | Jc MAE ↓ | Real trainable DOFs |
|---|---:|---:|---:|
| W6 M7 Realizable U-FNO | 0.00997222 | 0.00559021 | 13,448 |
| W5 4-channel Voxel DeepONet | 0.04108642 | 0.01654326 | 13,939 |

W6 wins these **three small held-out mesh-family P0 CPU tests**, but results do not establish superiority on independent CAD, general quadratic boundaries, real W2/Faster, or converged 10D Newton. Numbers should not be pooled with earlier M9 privileged-geometry data or W5 M13's distinct center-cell input/labels without disclosing changed conditions.

### Reproduction

```sh
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m unittest \
 research.NeuralMoments.models.pcraft_ufno.test_m4 \
 research.NeuralMoments.models.pcraft_ufno.test_m5 \
 research.NeuralMoments.models.pcraft_ufno.test_m6 \
 research.NeuralMoments.models.pcraft_ufno.test_m7 \
 research.NeuralMoments.models.pcraft_ufno.test_m8 \
 research.NeuralMoments.models.pcraft_ufno.test_m9 \
 research.NeuralMoments.models.pcraft_ufno.test_m10 \
 research.NeuralMoments.models.pcraft_ufno.test_m11 \
 research.NeuralMoments.models.pcraft_ufno.test_m11_merge \
 research.NeuralMoments.models.pcraft_ufno.test_m12 \
 research.NeuralMoments.models.pcraft_ufno.test_m12_audit \
 research.NeuralMoments.models.pcraft_ufno.test_m13 \
 research.NeuralMoments.models.pcraft_ufno.test_m13_mesh_cut -v

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
python -m research.NeuralMoments.models.pcraft_ufno.m13_experiment \
  --seeds 131,137,139 --per-family-train 10 --per-family-test 6 \
  --representation-per-family 3 --steps 80 \
  --output /tmp/m13_three_seed_mesh_cpu.json
```

Actual local regression: **272 tests collected, 271 passed, 1 skipped, 0 failed**, in 13.7s. The skip is a previously unfinished M10 three-seed freeze fixture; not a M13 test. **52/52 new M13 tests passed**; `compileall` successful. A first full experiment tool wrapper timed out, but its complete raw JSON was written and subsequently independently parsed and checked for all three seeds/27 representation meshes/6 trained model runs. Full stdout and complete original JSON are retained, not reconstructed. No GitHub Actions result is claimed for M13.

Upstream source audit: ten of eleven selected old W6 M4–M12 local source/test files match their exact Git blob IDs. The locally reconstructed M2 `analytic_cut.py` differs from the original remote blob; old regression is explicitly local mirror, **not a bit-identical remote checkout**. This module is not used as M13 oracle.

## Dependency release gate and next work

W2 current read-only observed head `1093a115cde928122de6aee98233fec8b18e5774` still reports 0 new native teacher evaluations and 0 formally admitted training samples; its 81 historical H8f archived cases are excluded. The original heavy P-CRAFT/FEM weights are not reproduced. W0 contract migration and W5 W2-v2 migration are separate owners' responsibilities. Never convert these P0 mesh tests into a claim of validated Cherchi material, native smooth Jacobian, CAD embedding, topology validity, terminal Newton, GPU VRAM or end-to-end Faster speedup.

**M14 recommendation:** same-source native-GPU profiling and warm/cold encoding amortization, plus a budget calculator including 100–400ms mesh-to-voxel preprocessing, oracle-query cost, few-shot adaptation and certified fallback. Formal original CAD/quadric solver validation remains blocked by W0/W2.

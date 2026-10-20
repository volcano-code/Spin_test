# W5 M12 — source-bound analytic saturation for the cone-valued cached moment model

**Only writable destination:** `volcano-code/Spin_test` branch
`research/neuralmoments-w5-deeponet-20261019`. Parent reviewed:
`2c413afca5944fe5db708dc5bfadd256013deeed`; common frozen native source
`0bcc187b3005478baa586a6d6f450e73811ca342`.
Changed only W5-owned `research/NeuralMoments/models/deeponet/` and independent
`tests/python/test_w5_m12_*.py`. **No modifications to W0/W2/W6/main**, and
no merges or replacements of original failed native workflow evidence.

## Scientific motivation and what was actually changed

M11's `ConeIntegrableMoment` has a convex, degree-one homogeneous potential,
nonnegative **atomic** ten-moments, and a symmetric PSD corrected surrogate
`Jq=Jc B^-1` only on smooth fixed-node activation strata. However, when all
nodes are active, the norm component reweights their masses, so even a strictly
FULL polynomial region can produce biased full material moments and nonzero
`J`. M11 already documented this negative result.

`m12_saturation.py` is a **post-inference safety envelope, not a newly
trained fifth architecture**:

1. Bind a real **self-generated analytic primitive specification** (axis-
   aligned box, sphere, or ellipsoid) to its exact four-channel, 8³ sampled
   voxel serialization and SHA256. Reject mismatched voxel bytes, unknown
   geometry, outside-world bounds, malformed coordinates, or altered cache.
   Cache the W6 source-pinned geometry encoder **once**, plus one independent
   analytic closed-form full raw ten-moment reference.
2. Interpret the exact *binary-float* W0 native coefficients
   `c=[a,bx,by,bz,Axx,Ayy,Azz,Ayz,Axz,Axy]` as `q=Bc` with
   `B=diag(1,1,1,1,1,1,1,2,2,2)`. Using rational-arithmetic interval bounds
   over the **analytic geometry's documented containment box**, certify a
   strictly positive or strictly negative polynomial sign without guessing
   at boundary contact.
3. When strictly EMPTY: return `r_D=0`, `J_D=0`. When strictly FULL: return the
   **independently derived continuum analytic full moments** (not the
   approximate learned Gauss node full measure) and `J_D=0`. Both are exact
   open-neighborhood mathematical derivatives for this **fixed analytic D**.
   Their source must not be described as learned model prediction.
4. In all other cases return the *unchanged M11* nonnegative surrogate mass
   moments and its local Jacobian **only when its fixed-node derivative regime
   is smooth**. At nodal sign switches report `Jc=None` and require external
   fallback. None of these flags permits real W0/W2 derivative training or
   an actual geometry commit.

The unknown-CAD path deliberately **does not support arbitrary external
`r_full` assertions**. Without independently certified full D material and a
verified bound, the wrapper is not authorized for real CAD. An 8³ occupancy
sample, matching analytical mesh statistics or SHA alone cannot certify
geometric equality to the actual original CAD or its Boolean F/D partition.

## Newly executed training and comparison

Reconstructed and hash-checked the existing M11 W5 source, the pre-existing
W6 M4/M5/M6 read-only source, and existing tests. **159/159 pre-M12 regression
cases passed**. The new M12 full run is **185 tests passed, 42 subtests passed**
(0 failures/0 skips); `m12_test_log.txt` has the exact console output.

Three **new** seeds **53,59,61**, four trained baseline architectures, all on
identical M8 four-channel analytic continuum P0. For each seed: 20 box+20 sphere
geometries with two native cuts per geometry, validation by 8 whole geometry
IDs, and 20 completely held-out ellipsoid geometries with two cuts each.
Adam, LR .003, batch 8, up to 100 iterations, same derivative objective
`MSE(r)+0.5 MSE(Jc)` and validation-selected early stopping. No real W2,
GPU, Cherchi or CAD-solver data are used.

| Model | Interior heldout r MAE | Interior Jc MAE | Analytic 1D guarded decision acceptance |
|---|---:|---:|---:|
| Four-channel DeepONet | **0.02108** | **0.01479** | 53.3% |
| M10 positive-atomic .12 | 0.04103 | 0.02158 | **76.7%** |
| W6 Gauss convex .04 | 0.04688 | 0.02575 | 44.2% |
| M11 cone-integrable .25 (M12 wrapper uses SAME trained weights) | 0.04595 | 0.02301 | 65.8% |

The M12 wrapper leaves all 120 held-out **interior** cut queries numerically
identical to M11 in both r and available J (`max_abs_difference=0`).

### Strict all-full/all-empty *out-of-cut* replay

Across the same 60 unseen ellipsoid geometries, four independent native-c
queries per geometry (positive and negative constant, plus tilted quadratic
with all three doubled native cross terms), **240 strict-sign queries**:

| Raw M12 target | Original trained M11 | M12 analytic source-bound bypass |
|---|---:|---:|
| FULL ten-moment MAE | **0.10767** | **0.0** |
| EMPTY ten-moment MAE | 0.0 | 0.0 |
| Maximum FULL `abs(Jc)` across seeds (mean of per-seed maxima) | 0.06354 | **0.0** |
| Maximum EMPTY `abs(Jc)` | 0.0 | 0.0 |

A separate independent analytic full-volume formula was evaluated **once
per geometric specification** (**60** source-reference evaluations total),
and geometry encoded once per shape (**60** source-bound encodes) for the
saturation replay. This is important cost accounting: the improvement comes
from a trusted analytical geometry oracle and strict sign contract, **not from
better learned network weights or teacher-query-free inference**. One M12
saturation batch of 80 queries, including the 20 analytic source bindings,
took 58–63 ms wall on this CPU; this is not an apples-to-apples model-only
latency comparison with baseline full forward or native Cherchi.

`m12_merge.py` reads all three full raw seed files and refuses duplicated
seeds, duplicate dataset identities, mismatched protocols, invented native
teacher counts, or forged zero saturation errors. It recomputes mean, sample
SD, source SHA-256, and retains all per-seed material. Source file SHA
identities are included in `m12_seed53_59_61_full.json`.

## Reproduction (source-pinned, CPU)

```bash
export PYTHONPATH=.
export W5_M12_READONLY_W6_ROOT=/path/to/unmodified/readonly_W6
# Existing historical W5 tests also require pinned W0/W2 paths as in M10/M11.
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  python -m pytest -q tests/python/test_w5_*.py
for seed in 53 59 61; do
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    python -m research.NeuralMoments.models.deeponet.m12_experiment \
       --w6-root "$W5_M12_READONLY_W6_ROOT" --seed "$seed" \
       --steps 100 --per-family 20 \
       --output "research/NeuralMoments/models/deeponet/m12_seed${seed}.json"
done
python -m research.NeuralMoments.models.deeponet.m12_merge \
  research/NeuralMoments/models/deeponet/m12_seed53.json \
  research/NeuralMoments/models/deeponet/m12_seed59.json \
  research/NeuralMoments/models/deeponet/m12_seed61.json \
  --output research/NeuralMoments/models/deeponet/m12_seed53_59_61_full.json
```

PyTorch `2.10.0+cpu`, NumPy `2.3.5`, Python `3.13.5`, pytest `9.0.2`, CPU
single-thread. Native/CUDA computations in W5 M12: **0**. Runtime and memory
are local-only, no native Faster-vs-network speedup is claimed.

## Dependency read-only status and scientific limits

- Latest reviewed W6 `research/neuralmoments-w6-pcraft-20261019` at
  `9d1758ea1ef527577b835f2b6bcfc5f0439d933d` includes an independently
  developed M7 realizable atomic model. This M12 experiment did **not**
  retrain W6 M7 or compare it on these new seeds. Executable W6 dependencies
  for M12 remain the older unmodified source-pinned M4/M5/M6
  (`m4_lite_model.py` blob `853ea92054e5895abe06d33092615a0be4b58772`,
   `m5_potential.py` blob `b5f976af0b2ef0621fd3f557ea93ae08a48ba99a`,
   `m6_gauss_potential.py` blob `85d0ead6ee0dec9fc3212750e849310230d7878a`,
   `m6_moment_guard.py` blob `9a9f0ae8cd1066c7e401529541387052faf264af`).
- Read-only W0 latest `d0a1b136b61b7c809311278c6c5051b62469d29a`
  confirms a real H8f/W3 four-side native replay blocker; zero new valid
  side materials, no certified continuous derivative or Newton solve.
- Read-only W2 latest `33a2ce05e005227bf69f260efa992b7553e91112`
  (`teacher_manifest.json` blob `c093d1fbab925e6075cd3fbe577d7f088f46d6c0`)
  still has `training_samples=0`, `native_teacher_runs=0`; 81 historical H8f
  material packets remain excluded because of construction point 60 and
  missing independent smooth-neighborhood proof. Original failed H8f
  GitHub Actions run `39123384402` remains **failure**. No W2-native
  supervision or self-asserted native gradient is used in M12.
- This is an **analytic source-gated case-specific correctness repair**.
  It does not produce a generally physically correct smooth native Jacobian
  inside a cutting boundary, a certificate of actual arbitrary 3D CAD
  material, an exact 10D Faster optimizer or demonstrable production speedup.
  The exact sign certificate is only for the known analytic support box and
  strict sign; contacts/unknown source remain undecided and must not silently
  promote ambient J. W5's fresh seeds do not remove P0/8³ domain shift.

## Next decision

Retain the strict gate as a non-native safety protocol. Compare genuinely
continuous-support/trilinear-cell analytical moment/Jacobian integration against
W6 M7 realizable head on matched novel geometry families, and admit real CAD
only through W0/W2 independently sealed source, region and differentiable
stratum contracts. Native costs, solver decisions and true material errors
must be measured only when an authentic Cherchi runner is available.

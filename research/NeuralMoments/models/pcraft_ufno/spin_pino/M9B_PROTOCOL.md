# W6 M9b: Source-bound geometry caching and 512^3 sparse ingestion

Date: 2026-11-07. Owner: W6 only. Base: d6cbb45e5b917b395cfc4435d5c66c7fd13559d9.
Primary trunk remains P-CRAFT factorized-FNO/U-FNO Spin-PINO. Default
training and inference paths are unchanged; M9b is opt-in and exploratory.

## 1. Two distinct caches
- SourceBoundRotationCache: exact byte-keyed geometry+R bounded M9 transport,
  LRU eviction, immutable internal entry, no gradients, input size cap.
- PinnedPINOQueryCache: one PINO geometry encoding reused across many *different*
  coefficient vectors c. Pin the entire model state including buffers; reject
  model mutation, train() and any autograd-enabled request.
- Both include value bytes in cache identity, so the same geometry ID with
  changed material cannot silently reuse a stale result.
- The 58-bisection M9 projection remains on the **cold** path. A repeated
  same-geometry/same-rotation query may skip it. Different rotations are misses.
  This does NOT speed unique one-off rotations automatically.
- An exact 10x10 Jacobian **of the neural head** is evaluated per query;
  physical/native Cherchi derivative certification remains excluded.

## 2. First sparse ingestion slice, not fVDB integration
- sparse_bridge.sparse_to_pino_grid takes unique (batch,i,j,k) int64 indices
  and [rho,occupancy,0,0] sampled values from a declared resolution, including
  512^3, without allocating the full high-resolution volume.
- It sums **rho*occupancy** and occupancy separately into 16^3 bins, then
  defines coarse density conditionally so coarse rho*occupancy preserves the
  discrete *total mass*. This avoids the invalid mean(rho)*mean(occupancy).
- Source voxel-center first and second moments are independently accumulated
  in float64, retained next to the coarse 16^3 approximation, with all ten
  components and drift metadata. The coarse PINO input by itself does **not**
  preserve high-frequency details or higher moments.
- Sparse records represent all nonzero material cells and all omitted entries
  are zero material. Ambiguous duplicate voxels, invalid source range,
  missing material and nonzero sparse SDF/boundary values are rejected.
- Separate smoke runs the existing SpinPINO ten-moment/Jacobian head on the
  reduced sparse bridge input. It tests shape/finite contract ONLY, with
  RANDOM weights and the encoder still downsampling to 8^3.
- No fVDB, CUDA kernel, full-resolution spectral operator, native Cherchi
  teacher, 512^3 GPU training, or native Spin end-to-end acceleration is claimed.

## 3. Reproducible cloud acceptance
Run:
```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m pytest -q \
 research/NeuralMoments/models/pcraft_ufno/spin_pino/tests/test_m9b_cache_sparse.py \
 research/NeuralMoments/models/pcraft_ufno/spin_pino/tests/test_m9_mass_transport.py

OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
python -m research.NeuralMoments.models.pcraft_ufno.spin_pino.m9b_benchmark \
 --queries 6 --source-resolution 512 --sparse-records 4096 \
 --output /tmp/w6_m9b_cache_sparse.json
```

Promotion requires same checksum results, cache hits on repeated coefficient
queries, fail-closed mutation and source checks, no dense 512^3 allocation,
and measured overall latency on the actual workload. Benchmark accuracy is
**not** a replacement for M9 P0 analytic held-out accuracy validation.

## 4. Next gates
- Integrate a provenance-pinned fVDB CUDA backend only after license and
  environment smoke; compare sparse memory, geometry throughput and fidelity
  against this torch-only interface.
- Add multiscale spatial detail into the PINO trunk *without* silently
  compressing 512^3 into 16^3. Demonstrate 32/64/128/512 scales on local GPU.
- W0/W2 teacher admission plus true Cherchi/Newton are separate hard gates.

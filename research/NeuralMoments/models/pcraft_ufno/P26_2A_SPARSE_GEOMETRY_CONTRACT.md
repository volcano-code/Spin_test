# W6 P26.2a — Sparse voxel geometry interchange contract

## Purpose

Establish a backend-neutral sparse representation before attempting a
pinned fVDB integration. This is a data contract only; it does not import,
build or claim to integrate fVDB.

## Representation

SparseGeometryBatch stores:
- `coords: int64 [N,4]` as (batch,x,y,z);
- `values: float [N,4]` as density, occupancy, normalized SDF,
  internal boundary;
- explicit batch size and 3D spatial shape.

Coordinates must be in bounds, unique, and on the same device as values.
Values must be finite. Empty batch members are supported.

## Implemented operations

- `from_dense`: extract occupied voxel coordinates and preserve
  all four channel values at those coordinates.
- `to_dense`: small-test/debug reconstruction only.
- `active_counts`: per-batch active voxel counts.
- `occupancy_fraction`: global active fraction.
- `to(device,dtype)`: device/dtype transfer.

## Required tests

- Dense → sparse → dense occupancy and active-value round-trip.
- Empty batch member preservation.
- Duplicate coordinate rejection.
- Out-of-bounds coordinate rejection.
- Invalid channel-count rejection.

CI: https://github.com/volcano-code/Spin_test/actions/workflows/w6-p26-2a-sparse-geometry-contract.yml

## Next fVDB adapter gate

The next implementation must use the pinned official source:
`openvdb/fvdb-core@b263e7d5bcc2fef155d57c4aa14c5f76f8b9356c`
(Apache-2.0). It must prove round-trip coordinate/value fidelity and
variable active-density behavior. It must not densify the full 512^3 grid.

The existing W6 CPU CI uses PyTorch 2.5.1. The candidate fVDB package matrix
requires a separate compatible CUDA/PyTorch environment. Do not change the
existing W6 environment to force an installation.

## Non-claims

This contract is not an fVDB build, GPU benchmark, sparse spectral PINO,
512^3 result, Cherchi integration, or end-to-end speed result.


## P26.2a CI result

The sparse interchange contract workflow completed successfully with 5 tests
passing (dense/sparse round-trip, empty batch member, duplicate coordinates,
out-of-bounds coordinates, invalid channel count):
https://github.com/volcano-code/Spin_test/actions/runs/42627685849

This confirms the backend-neutral data contract only. It does not validate
fVDB APIs or GPU behavior.

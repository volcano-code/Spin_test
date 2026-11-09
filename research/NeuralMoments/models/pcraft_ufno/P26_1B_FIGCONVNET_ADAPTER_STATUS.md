# W6 P26.1b — FIGConvNet point-cloud adapter status

## Implemented

- `FIGConvNetPointEncoder` wraps an injected official FIGConvUNet module.
- Occupied voxel centers are deterministically sampled to a fixed point count.
- Four canonical geometry channels (density, occupancy, normalized SDF,
  internal boundary) are passed as point features.
- Point coordinates are normalized to the configured FIGConvNet AABB
  (default [0,1]^3, matching the official model defaults).
- Point outputs are pooled by mean and max, then projected to the SpinPINO
  geometry plugin feature dimension.
- A lazy builder constructs the official `physicsnemo.models.figconvnet.figconvunet.FIGConvUNet`
  from a separately installed PhysicsNeMo environment.
- No silent fallback to a locally invented FIGConvNet implementation occurs.

## Source pin

- Upstream: NVIDIA/physicsnemo
- Commit: 22bb35ec6e700c2f8d6088ddbf88af12b157e5f2
- Source: physicsnemo/models/figconvnet/figconvunet.py
- Source blob: c19b160f72ea8918f14c1bc69007fc05afd54472
- License: Apache-2.0; preserve notices and audit bundled dependencies.

## Tests

The P26.1 CPU contract workflow passed 10 tests covering:
- zero-gated identity of the PINO function;
- plugin/gate gradient flow;
- deterministic occupied-voxel sampling;
- point-feature output shape and finiteness;
- empty geometry rejection;
- default/custom AABB normalization;
- plugin shape and duplicate attachment checks.

Run: https://github.com/volcano-code/Spin_test/actions/runs/42627450181

The adapter tests use a test double. The official PhysicsNeMo FIGConvUNet
package itself has not yet been installed or executed in this CPU CI.

## Current integration classification

| Item | Status |
|---|---|
| PINO plugin port | Implemented and CPU-tested |
| FIGConvNet point-cloud adapter | Implemented and CPU-tested against a test double |
| Official FIGConvUNet lazy builder | Implemented; not instantiated in this CI |
| Official PhysicsNeMo dependency/Warp install | Not done |
| Official FIGConvNet GPU forward/backward | Not done |
| Matched GINO vs FIGConvNet ablation | Not done |
| 256^3/512^3 performance | Not done |

## Promotion gate

Before claiming FIGConvNet integrated:
1. Install the exact audited PhysicsNeMo source in an isolated compatible
   environment; do not modify the Torch 2.5.1 W6 CI environment.
2. Verify the Warp and point-grid kernels work on the selected GPU.
3. Run real FIGConvUNet forward/backward on representative 3D point clouds.
4. Compare against GINO and PINO-only with matched geometry IDs, parameter
   budget, training steps and teacher labels.
5. Report ten-moment/Jacobian error, independent hard-cut error, runtime,
   memory, and failure/OOD rates.

PINO remains the only primary neural-operator backbone. FIGConvNet is an
optional geometry feature plugin and challenger, not a replacement.

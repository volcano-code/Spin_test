# W6 P26.1 — PINO-first external geometry plugin port

## Scope

P26.1 creates a stable residual feature port for one optional external
geometry encoder. It does not vendor, build or claim to integrate FIGConvNet.
The P-CRAFT PINO F-FNO/U-FNO trunk and ten-moment/Jacobian heads remain the
only primary operator.

## Source and license pin for the selected challenger

- Project: NVIDIA PhysicsNeMo.
- Upstream commit: 22bb35ec6e700c2f8d6088ddbf88af12b157e5f2.
- FIGConvNet source: physicsnemo/models/figconvnet/figconvunet.py
- Source blob: c19b160f72ea8918f14c1bc69007fc05afd54472.
- License recorded in candidate audit: Apache-2.0; preserve notices and
  audit bundled dependencies before source reuse.
- Candidate status before P26.1: NOT_INTEGRATED.

fVDB remains a separate sparse-voxel backend candidate and is not part of
this geometry feature plugin.

## Implemented interface

SpinPINO.attach_geometry_plugin(plugin, input_dim=K) accepts a torch module
that consumes canonical geometry [B,4,X,Y,Z] and returns a global feature
tensor [B,K]. The adapter projects that tensor to the existing PINO encoder
feature dimension and adds it through a scalar residual gate initialized
to zero.

At gate zero, the function is exactly PINO-only. The plugin cannot replace
the F-FNO/U-FNO trunk, ten-moment head, or analytic Jacobian implementation.
Only one external geometry plugin may be attached at a time.

The contract rejects wrong output shapes and nonfinite features.

## Tests and promotion gate

- Exact PINO output identity with a newly attached zero-gated plugin.
- Gradient flow into plugin parameters and the scalar gate after opening.
- Shape validation.
- Duplicate attachment rejection.

CI: https://github.com/volcano-code/Spin_test/actions/workflows/w6-p26-1-geometry-plugin-port.yml

This interface test is not FIGConvNet integration. The next stage must
implement a separately pinned FIGConvNet point-cloud adapter, verify its
input sampling and feature normalization, and compare it against the
existing GINO adapter under matched geometry splits, parameter budget,
teacher labels, and runtime measurements. FIGConvNet is a challenger, not
an automatic default.

## Cloud/local boundary

Cloud can validate this interface and small CPU geometry adapters. Full
PhysicsNeMo FIGConvNet training, point-cloud scale tests and 256^3/512^3
memory/throughput measurements require a compatible local GPU environment.
Do not upgrade the existing Torch 2.5.1 W6 CI in place.

## Explicit non-claims

No FIGConvNet model weights trained, no full FIGConvNet source integrated,
no fVDB backend integrated, no 512^3 GPU result, no Cherchi certification,
no FEM/FEA or end-to-end Spin-it speed claim.

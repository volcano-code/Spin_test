# W6 P21: train the original MIT QuadrANN as an optional geometry-aware proposal around P-CRAFT PINO

## Source and role
- Upstream: kesmarag/QuadrANN commit 111dd611aaeac1fb98c76385706b003ea8ef94be.
- License: MIT, retained at p0_integration/third_party/QUADRANN_LICENSE.
- Reuse the original upstream QuadrANN GNN core unchanged. The upstream
  example script is not imported because it starts training/plotting on import.
- P-CRAFT SpinPINO remains the sole moment and analytic coefficient-Jacobian
  backbone. QuadrANN proposes geometry-conditioned positive weights only.
- The QuadrANN proposal is independent of c. The same geometry proposal
  is therefore used for all cut queries and does not alter d r/d c semantics.
- The gate starts at zero, guaranteeing exact pure-PINO parity. Only the
  original QuadrANN GNN parameters and its scalar residual gate are trained;
  all P14 PINO weights are frozen.

## Training
- P14 trained native-64 seed-271 PINO checkpoint, strict load.
- New analytic P0 dataset seed 883; fit/validation boxes+spheres, held-out
  ellipsoid family. 16 geometries per training family, 8 held-out ellipsoids,
  four coefficient queries per geometry, 64^3 input.
- Original QuadrANN on material point clouds, max 128 sampled material sites,
  upstream positional encoding, kNN message passing, global context and
  positive softmax weights.
- Gaussian kernel maps learned material-site weights onto the fixed 512
  P-CRAFT quadrature nodes. PINO's own support/density weights remain the
  multiplicative base; QuadrANN cannot create support outside the PINO support.
- Optimize standardized ten-moment and analytic P0 Jacobian errors for
  60 updates, batch 4, Adam lr=1e-3. Validation chooses checkpoint.
- Compare pure PINO, zero-gate parity, and trained QuadrANN-enhanced PINO
  on held-out ellipsoid geometries. Report both r and J error.

## Acceptance and scientific limits
The adapter is promoted only if held-out r and J both improve without
negative weights, support violations, or material increase in runtime.
If it does not improve, keep its gate at zero and retain it as a rejected
or diagnostic candidate. J remains a diagnostic model Jacobian; it is not
W0/W2/Cherchi-certified and cannot authorize native Newton.
Labels are analytic P0 only, not Cherchi/CAD or stress/FEA data.

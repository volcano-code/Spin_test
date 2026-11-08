# W6 P22: train original NeuralOperator GINO as optional geometry residual around P-CRAFT PINO

- Upstream: neuraloperator/neuraloperator commit a6648eeeb60fe0837f2d7d021517a945a159a0c8; MIT license retained.
- P14 trained seed-271 PINO remains the sole moment/Jacobian trunk and is frozen.
- GINO encodes a deterministic 64-point cloud of geometry plus four material/SDF/boundary features. Its latent code drives a zero-initialized residual gate on PINO quadrature-node weights.
- Positive PINO support/density weights remain the multiplicative base; GINO cannot create support outside the PINO support.
- Geometry-only GINO correction is independent of cut coefficients c; the PINO analytic coefficient Jacobian remains consistent.
- Train only GINO encoder, node correction and scalar gate. The unused GINO moment head is excluded.
- Analytic P0 training seed 887; fit/validation boxes+spheres; held-out ellipsoid family; 64^3 source grid; 40 updates, batch 2, Adam lr 5e-4.
- Compare pure PINO and GINO-enhanced PINO on held-out ellipsoids. Promote only if both ten-moment and Jacobian errors improve; otherwise keep gate zero.
- No W2/Cherchi, CAD event certification, native Newton, FEM or 512^3 claims.

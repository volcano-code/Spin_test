# W6 P23: three-source-seed confirmation of original MIT QuadrANN around P-CRAFT PINO

P21 showed a promising single-seed held-out gain. P23 tests repeatability
across three independently trained P14 PINO source checkpoints and three
independent QuadrANN/data initialization seeds.

- P14 source PINO seeds: 271, 277, 281 (native 64^3 trained checkpoints).
- QuadrANN training/data seeds: 883, 887, 991.
- Strict source checkpoint identity and SHA256 recorded per run.
- 60 updates, batch 4, Adam lr=1e-3.
- Fit/validation use boxes+spheres; held-out test uses the entire ellipsoid
  geometry family, disjoint by geometry ID.
- Original MIT QuadrANN GNN core unchanged; up to 128 material support points.
- P-CRAFT PINO frozen and remains the sole ten-moment/Jacobian backbone.
- Zero gate exact parity; train only QuadrANN weights and scalar gate.
- QuadrANN proposal is geometry-only and independent of cut coefficient c.
- Compare pure PINO and enhanced PINO on the same held-out ellipsoids for
  each source seed. Report both moment and Jacobian relative L2.

Promotion rule: all three runs must improve both held-out moment and
Jacobian errors and preserve nonnegative mass. Even then QuadrANN remains
optional until native 128^3 and W0/W2 Cherchi derivative validation.
Mixed or negative results are retained and not promoted.

Labels are analytic P0, not Cherchi, CAD topology certification,
Newton admission, FEM/FEA or manufacturing certification.

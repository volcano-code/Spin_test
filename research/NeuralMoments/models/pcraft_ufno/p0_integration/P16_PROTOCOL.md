# W6 P16: warm-start native 128³ PINO from the trained 64³ P14 checkpoint

P16 reuses the three-seed, 40-step trained 64³ P14 checkpoint artifact.
It does not replace PINO and does not copy any model from GINO.

## Locked experiment
- Download prior P14 Actions artifact `w6-p14-native-PINO-grid-64`
  from workflow run 42450889982 using actions:read permission.
- Strictly load seed-271 64³ model weights into the identical-width,
  identical-mode, identical-layer, identical-quadrature native 128³ PINO.
  No shape interpolation, no missing/unexpected keys. Coordinate grid
  is nonpersistent and recomputed at target 128³.
- Verify geometry IDs across 64³ and 128³ fit/validation/ellipsoid test
  splits match exactly (8 boxes + 8 spheres train pool, 6 heldout
  ellipsoids, 2 c queries each).
- Record zero-shot 64-trained model performance when evaluated at 128³.
- Fine-tune ALL PINO weights at 128³ for 8 updates, batch=1, chunked
  eval=1, activation checkpointing enabled and full SpinPINOLoss.
- Use conservative learning rate 2e-4 for warm-start; the first P16
  run at default 1.5e-3 is retained as a high-LR exploratory comparison.
- Groupwise exact cube fit augmentation; separate SO(3) rotated test.
- Report validation-selected final model, independent voxel hard cut
  comparison and peak CPU RSS.
- Single seed is an initial transfer pilot only; not a generalization
  claim. If useful, repeat all three seeds and longer budget.

## Provenance limits
P14 weights were trained on analytic P0 continuum box/sphere labels
and ellipsoid holdout. This is a resolution transfer study, not
Cherchi/W2 teacher training, not arbitrary CAD, not certified Newton.

# W6 P16 — Native 64³ to 128³ PINO transfer (partial verified result)

Date: 2026-11-08. W6 research branch.
High-learning-rate transfer run:
https://github.com/volcano-code/Spin_test/actions/runs/42453678302
Status: SUCCESS; 1 strict cross-grid state-transfer test passed and
one native 128³ warm-start/fine-tune experiment completed.

## Source model and strict transfer
- Source: P14 native 64³ trained P-CRAFT SpinPINO, seed 271.
- Source checkpoint SHA-256:
  `6e6662a00bde1f3686f9f86629b8b98646d079e72296591c116cc783628ce531`.
- Source ZIP: P14 64 artifact SHA-256
  `597ef4c2725b958976998d3912242b2a9e13953b4de193fcb408cc70ad08bf75`.
- Strictly loaded all 75 model tensors/parameters into an identical
  width=8, modes=4, n_layers=4 PINO with native 128³ Fourier grid.
  No shape interpolation or dropped weights.
- 512 quadrature atoms, all PINO parameters fine-tuned, GINO/QuadrANN/UQNO off.
- Same geometry IDs across source64 and target128; 12 fit samples,
  4 validation samples, 12 held-out ellipsoid samples, 2 coefficient
  queries per geometry.
- One seed, 8 fine-tune steps, batch=1, evaluation chunk=1,
  activation checkpointing enabled.
- P0 analytic continuum labels only; not W2/Cherchi.

## Measured high-LR run (1.5e-3)

| Metric | 64-trained checkpoint evaluated directly at 128 | After 8-step 128 fine-tuning |
|---|---:|---:|
| Held-out ellipsoid r relative L2 | **0.095621** | 0.096245 |
| Held-out ellipsoid J relative L2 | **0.192026** | 0.194287 |
| Validation r relative L2 | 0.246995 | 0.239015 |
| Validation J relative L2 | 0.302125 | 0.297065 |
| SO(3)-rotated held-out r relative L2 | — | 0.115383 |
| SO(3)-rotated held-out J relative L2 | — | 0.213712 |
| Independent voxel hard-cut vs continuum r relative L2 | — | 0.021427 |

- Fine-tune optimizer time: 268.91 s; wall time: 717.16 s.
- Peak process RSS: 7,612,280 KiB (about 7.26 GiB).
- Validation selected step 1/8. The high LR did **not** improve
  held-out r/J; it slightly worsened both. Do not use the high-LR
  fine-tuned checkpoint as a promoted model.
- The important result is **zero-shot transfer**: the 64³ trained
  weights can be strictly loaded and evaluated on the true 128³
  Fourier grid, with r/J errors close to the original 64³ model
  (0.094538/0.201146). This is a resolution-transfer result, not
  evidence that 128 fine-tuning has helped yet.

## Low-LR confirmation and checkpoint preservation

A separate conservative fine-tuning run at learning rate 2e-4 is
running. The original P16 artifact path omitted its saved .pt file;
the P16 script has now been corrected to save the 128³ checkpoint
at the exact workflow artifact path and to record the source
checkpoint SHA-256. The corrected run will be used as the durable
P16 transfer artifact. Do not promote the high-LR checkpoint.

## Limits

- This is one seed and the same geometry-ID distribution used to
  train the 64³ source checkpoint; the 128 fine-tune uses those
  training geometries, with a disjoint held-out ellipsoid family.
- No W2/Cherchi teacher, arbitrary quadric/event derivative,
  continuous CAD certification, Newton admission, 512³ training,
  or full Spin-it Faster speedup is established.
- The high-RSS 128³ CPU run is near the hosted runner's practical
  memory budget. The 128³ CPU path is feasible but expensive.

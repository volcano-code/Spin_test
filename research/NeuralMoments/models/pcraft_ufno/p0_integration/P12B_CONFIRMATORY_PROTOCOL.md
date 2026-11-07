# W6 P12b: independent exact-cube SO(3) held-out confirmation

Precommitted prior to P12b CI: source code `p12_train.py` from W6 P12.
P12 one-seed class tests and 3-seed aggregate were successfully completed
under https://github.com/volcano-code/Spin_test/actions/runs/42373752345 .
The initial 8^3 P0 data showed an apparent mean QuadrANN advantage but
a seed selected training step zero, preventing a confident learning claim.

## Locked configuration
- New seeds: **211,223,227**, not used for selecting the initial P12 result.
- P-CRAFT PINO same primary U-FNO trunk, same checkpoint per seed.
- 80 shared PINO pretrain updates; each arm then receives exactly 36
  identical fit observation updates. Arms: PINO-head finetune, original
  GINO residual, material-conditioned original QuadrANN proposal.
- Fit/validation: box and sphere geometry identities drawn anew, 14
  examples per family split by the frozen dataset generator. Entire
  ellipsoid family remains unseen in training or validation.
- Exact signed-permutation SO(3) cube rotation applied ONCE to every
  held-out ellipsoid. Keep ONLY transformed test samples. Analytical
  P0 r and 10x10 J and native coefficient vector transformed by
  exact geometry/coordinate rules (not arbitrary trilinear interpolation).
- Every arm trained for the same label/optimizer UPDATE budget but
  allocated parameters/FLOPs remain unequal; no default promotion
  based on a tiny CPU study.
- **Crucial**: after validation selects a checkpoint, report the
  untrained initial adapter's heldout errors under the SAME test
  distribution alongside the chosen checkpoint. This isolates whether
  a result is actually trained rather than a lucky random gate.
- UQNO original scale head trained 48 fit-only updates, independent
  box/sphere validation IDs for group conformal alpha=.25, held-out
  rotated ellipsoid coverage and precommitted 0.05 radius threshold.
- Source distribution remains synthetic continuum vertical-plane
  cuts transformed by exact cube rotations. Real general quadrics,
  CAD derivatives, W0/W2 Cherchi admitted labels, 512^3 GPU training
  and native Newton use remain UNVERIFIED.

Promotion beyond experimental adapter requires a larger new held-out
shape AND cut distribution, matched model capacity and speed, real
Cherchi teacher admission and end-to-end Newton fallback/latency.

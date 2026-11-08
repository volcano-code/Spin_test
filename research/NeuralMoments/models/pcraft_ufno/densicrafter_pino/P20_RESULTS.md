# W6 P20 — Three-seed native 128³ P-CRAFT PINO × DensiCrafter confirmation

Date: 2026-11-08.
Run: https://github.com/volcano-code/Spin_test/actions/runs/42459811708
Source commit: `40a9a7f03144560fed35494beeaf18c5ad460f13`.
All three native-128 seed design jobs: **SUCCESS**. The original
aggregate-only job failed because its lightweight runner did not install
PyTorch while invoking the package via `python -m`; the three experiment
jobs and their artifacts were successful. A recovery workflow now
aggregates the archived JSONs by direct script invocation, which needs
only the Python standard library.

## Fixed experiment

- P14 trained 64³ P-CRAFT SpinPINO checkpoints, seeds 271, 277, 281;
  each strictly loaded into the same P-CRAFT architecture at native 128³
  input and internal Fourier grid.
- Width 8, modes 4, four U-FNO layers, 512 positive quadrature atoms.
- Freeze every PINO parameter; optimize only DensiCrafter density logits.
- Three independently seeded analytic P0 sphere geometries.
- Four-cell protected shell; same normalized thickness as P18's
  two-cell shell at 64³.
- Four arms: Densi-only, PINO-only, soft joint, feasible joint.
- Six Adam updates per active arm, learning rate 0.06.
- Resolution-aware DensiCrafter contact weighting.
- Independent cell-centered hard-cut ten-moment and normalized
  full-material nine-moment checks.
- Predeclared tolerances: PINO cut-r <=2%, independent hard-cut r <=2%,
  normalized full-material nine-moment L2 <=2%.

## Per-seed feasible-joint results

| P14 seed | Mass reduction | PINO cut-r relative change | Independent hard-cut r change | Normalized material 9-moment L2 | Accepted/rejected |
|---|---:|---:|---:|---:|---:|
| 271 | 0.227568% | 0.010670% | 0.272167% | 0.013818% | 6/0 |
| 277 | 0.211819% | 0.011485% | 0.294213% | 0.012381% | 6/0 |
| 281 | 0.173320% | 0.076741% | 0.146189% | 0.007706% | 6/0 |
| **Mean** | **0.204236%** | **0.032966%** | **0.237523%** | **0.011302%** | **18/0** |

Mass-reduction mean population standard deviation: 0.022786%.
All three geometries passed all predeclared 2% screens; all protected
shells remained exact. Peak process RSS was approximately 2.30 GiB
per seed.

## Evidence artifacts and checksums

- Seed 271 artifact ID 13609457779; SHA256
  `1845affcced11e68f9beadbd7aa89126c24bb3da22e98805f648efa0c983fe6f`.
- Seed 277 artifact ID 13608614765; SHA256
  `831e47b5bde804558d3f79df73cf31702a300011af6700b11ea8bf9273c5b667`.
- Seed 281 artifact ID 13608564978; SHA256
  `982ad8c73e163fda5c1573f1c6997570c428f51144de3c6a406579f9ca91d8bc`.

## Interpretation and limits

P20 establishes repeatability of the trained P-CRAFT PINO + DensiCrafter
128³ integration over three trained checkpoints and three independent
synthetic geometries. Mean mass reduction is about 0.204%, larger than
P19's three-step pilot but still modest. It is not yet a converged or
competitive lightweighting result.

The hard-cut reference is cell-centered voxel quadrature, not continuous
Cherchi integration. The nine-moment metric is normalized shape/inertia
proxy, not preservation of absolute inertia after removing mass.
Four voxels are not a physical millimeter wall. These runs do not
establish stress/FEM/FEA, printability, CAD topology certification,
Newton admission, or 512³ training.

## Recovery

The three experiment jobs all completed successfully. The aggregate
job failed only because the aggregation job lacked torch and imported
the package using `python -m`. The recovery workflow downloads the
same immutable artifacts and runs `p20_aggregate.py` directly, avoiding
package initialization and requiring no PyTorch installation.


## Aggregate recovery completed

The three seed design jobs were all successful. The original aggregate job failed only because it invoked the package with `python -m` without installing torch. Recovery run https://github.com/volcano-code/Spin_test/actions/runs/42461359386 completed successfully by invoking the standard-library-only aggregation script directly. Recovered aggregate artifact ID: 13609238721; ZIP SHA256: `67dff51406fdfc3b25387902ac3f731c17458e0965d661a01f71ed2d13c0fb67`. Aggregate reports all three seeds feasible, all 18/18 accepted updates, and zero rejected updates.

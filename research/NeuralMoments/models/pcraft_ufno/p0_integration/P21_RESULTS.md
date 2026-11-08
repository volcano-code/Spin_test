# W6 P21 — Original MIT QuadrANN trained as an optional proposal around P-CRAFT PINO

Run: https://github.com/volcano-code/Spin_test/actions/runs/42460223133
Result: SUCCESS; 8 tests passed; 60-step QuadrANN training completed.
Artifact ID: 13609353468; ZIP SHA256: 7002b627b44c8d16edb3e41cb32b65609342d4a59158ae07e8f0c5dc9260b864.
JSON SHA256: bb6da8355882b9408fe8da00a1914492b3fd9f78e43b9960de06cf96c278dc23.

## Provenance and architecture

- Upstream source: kesmarag/QuadrANN commit 111dd611aaeac1fb98c76385706b003ea8ef94be; MIT license preserved.
- The original QuadrANN GNN core is reused unchanged. The upstream example script is not imported because it trains/plots on import.
- P14 trained seed-271 P-CRAFT SpinPINO checkpoint, strict loaded; source checkpoint SHA256 6e6662a00bde1f3686f9f86629b8b98646d079e72296591c116cc783628ce531.
- P-CRAFT PINO remains the only moment/Jacobian backbone. All 75,040 PINO parameters are frozen.
- Only 4,066 QuadrANN/gate parameters are trained. QuadrANN gate starts at zero and ends at 0.0328168.
- Geometry-conditioned proposal is independent of cut coefficients c. The positive learned proposal reweights fixed PINO quadrature nodes; PINO still evaluates the cut and its analytic coefficient Jacobian.
- Training data: analytic P0 boxes/spheres; held-out entire ellipsoid geometry family. Training seed 883, 60 updates, batch 4, Adam lr 0.001. Validation selected step 60.
- Labels are exact analytic P0 continuum labels for strictly interior vertical-plane cuts; not W2/Cherchi.

## Held-out ellipsoid results

| Metric | Pure P-CRAFT PINO | PINO + trained QuadrANN | Relative improvement |
|---|---:|---:|---:|
| Ten raw moments relative L2 | 0.108610 | **0.077162** | **28.95%** |
| Jacobian relative L2 | 0.205412 | **0.173038** | **15.76%** |

Validation r/J relative L2 improved from 0.216100/0.260620 to 0.204872/0.245179. Negative predicted mass fraction remained zero. The selected QuadrANN gate was nonzero, so the improvement is not a zero-gate parity artifact.

## Interpretation and promotion status

This is a promising first result: the original geometry-aware QuadrANN proposal improved both held-out moment and Jacobian errors while preserving the P-CRAFT moment potential and c-independent proposal semantics. It is a genuine trained auxiliary module, not just an upstream import/smoke test.

However, this is one P14 source seed and one QuadrANN training seed. It is not yet multi-seed evidence, does not establish robustness across CAD topology or arbitrary quadrics, and does not certify continuous Cherchi derivatives. Keep the QuadrANN gate optional and do not make it the production default until three-seed confirmation and independent CAD/teacher validation.

No native Newton admission, W0/W2/Cherchi supervision, FEM/FEA, printability or 512^3 claim is made.
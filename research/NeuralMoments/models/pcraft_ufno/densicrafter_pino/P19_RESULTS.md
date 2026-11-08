# W6 P19 — native 128^3 trained P-CRAFT PINO × DensiCrafter

Run: https://github.com/volcano-code/Spin_test/actions/runs/42456853635
Result: success; 5 tests passed; four-arm native 128^3 material design completed.
Artifact ID: 13607729820; ZIP SHA256: 4a68f6ac5c39545d1c549d7271dc567f42fb06b197db5d85c460b21b390c28f4.

Source is the P14 seed-271 trained 64^3 PINO checkpoint, strictly loaded into the same architecture with both input and internal Fourier grid at 128^3. All 75,040 PINO parameters are frozen; only DensiCrafter density logits are trainable. Four-voxel protected shell, 104,599 interior design cells, 512 quadrature atoms, 3 updates per active arm, Adam lr 0.03.

DensiCrafter bottom-contact exponential decay is measured in equivalent 64-grid voxels. It exactly matches the original formula at 64^3 and preserves the same physical decay at 128^3.

| Feasible-joint metric | Result |
|---|---:|
| Mass reduction | 0.011162% |
| PINO cut-r relative change | 0.013962% |
| Independent hard-cut r relative change | 0.015087% |
| Normalized full-material nine-moment L2 | 0.003573% |
| Accepted / rejected steps | 3 / 0 |
| Protected shell | exact |
| Peak process RSS | 2,404,324 KiB (~2.29 GiB) |

This proves the trained PINO and DensiCrafter pipeline runs at true 128^3 and passes independent voxel-level screening. The 0.011% mass reduction is very small and the budget is only three steps; this is an integration proof, not yet useful lightweighting. The hard-cut reference is cell-centered voxel quadrature, not continuous Cherchi. No FEM/FEA, stress, printability, millimeter wall or Newton certification is claimed. P20 now repeats the test across three seeds with six updates per active arm.

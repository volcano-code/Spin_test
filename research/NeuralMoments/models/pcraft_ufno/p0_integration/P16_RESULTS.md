# W6 P16 — trained 64^3 PINO transferred to native 128^3

Run: https://github.com/volcano-code/Spin_test/actions/runs/42455011782
Artifact ID: 13608207276; ZIP SHA256: 22d31408a2898485e140e2bb6e9209e3bd754ab73b8b65a91a71a6ee74512099.

Strictly loaded all 75 state_dict entries from P14 seed-271 64^3 P-CRAFT SpinPINO into the same architecture configured at a true 128^3 input and Fourier grid. No learned weight interpolation or dropped keys. Width 8, modes 4, four U-FNO layers, 75,040 parameters and 512 quadrature atoms.

Conservative fine-tuning: 8 updates, batch 1, evaluation chunk 1, activation checkpointing, learning rate 2e-4. All PINO weights trainable. The source checkpoint SHA256 is 6e6662a00bde1f3686f9f86629b8b98646d079e72296591c116cc783628ce531.

| Metric | Zero-shot transfer | After fine-tuning |
|---|---:|---:|
| Validation r relative L2 | 0.246995 | 0.245621 |
| Validation J relative L2 | 0.302125 | 0.301251 |
| Held-out ellipsoid r relative L2 | 0.095621 | 0.095497 |
| Held-out ellipsoid J relative L2 | 0.192026 | 0.191952 |
| Rotated held-out r relative L2 | — | 0.115461 |
| Rotated held-out J relative L2 | — | 0.216332 |

Validation selected step 1/8. Held-out improvements are tiny (about 0.13% for r and 0.04% for J relative error), so this is not a meaningful accuracy breakthrough. Zero-shot transfer remains the preferred simple reference unless later multi-seed studies show robust gains. Optimizer time 504.01 s; wall time 1296.93 s; peak RSS 7,728,252 KiB (~7.37 GiB). Analytic P0 labels only; not W2/Cherchi, not Newton-admitted.

# W4 P30 tangent preflight — planning only

Source: frozen P27 formal M6 archive, SHA-256 `6827a0951ce8201e4bea5585ba4e2b485b4652c830604b06592e5a0146583e89`.
External P27 manifest: `3a9b6b21d1d1185e00d1ef25a1bfc625d4696f554c3ab4a7719f5d85ca109773`.
Native coefficient SHA-256: `57ac958304df37ebfd36bc1dddeb32c81a113ed5440f65d959f4b45f2a12e6ca`.
Same-call Jacobian (100 float64) SHA-256: `26cf3b5dd53d45a4b80f14319b39d28fa9ef7b8d8be3a915189e90ba077a08a5`.

The JSON contains 9 deterministic tangent vectors to actual frozen c. For each direction the four **unexecuted** planned points are +h, -h, +h/2, -h/2, h=0.002 rad. The first 12 form a 3-direction diagnostic pilot; remaining 24 extend to 9 dimensions. These are research *proposals*, not W0-authorized settings. All feature-branch, numerical tolerance and physical owner approvals remain null. Zero new native calls were performed.

Run after placing original private archive locally:

```bash
python3 p30_neighborhood_preflight.py --archive /path/to/P27_FORMAL_M6_EVIDENCE.tar.gz --output P30_NEW_UNEXECUTED_TANGENT_PLAN.json
python3 -m unittest -v test_p30_neighborhood_preflight.py
```

Local run with original private archive completed (preflight and 11 pure regression tests). GitHub CI tests 11 pure regressions and the W0 numeric-gate semantics with **synthetic data**, not real perturbations.

Before real native sample collection, W0 must accept or correct the physics, scale, tip/shaft and per-case tolerance, and W2 must accept a separate base feature-branch fingerprint for genuine same-call output. A captured one-point J and 36 planned coefficients cannot prove smoothness or Newton readiness.

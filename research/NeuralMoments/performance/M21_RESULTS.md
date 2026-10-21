# W1 V2 M21 — source-pinned exact Fraction auditor speed candidate

**Branch:** `research/neuralmoments-w1-native-20261019`
**Writable scope:** `research/NeuralMoments/performance/` only
**Status:** reproducible source-pinned *independent Python Fraction verifier* candidate, **NOT** Cherchi/Faster production admission.

## Genuine input and exact code change

The baseline is the repository's byte-identical frozen `verify_h8_exact_moments.py`, Git blob `79ca86064b2b2d990ab5b42b202e3339b6356509`. The test candidate `m21_independent_verifier_candidate.py` differs only by adding `BalancedFractionSum` and replacing the ten left-fold `Fraction +=` reductions with exact binary carry-tree additions; the original parser, per-face validation, determinant, tetrahedral ten-moment formula, CLI/API shape, and output semantics remain unchanged. Candidate Git blob `7a7230f72d9736279b95d9c966c995e3b056327a` and SHA-256 `900cd721a3a448e8807e5a5276831a2cc0ed32f7ec5c03e2c5ed42401aa967e8`.

Real frozen H8e native archive SHA-256: `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`, with 8,455 vertices / 16,910 triangles per point. For each saved material the same immutable exact rational coordinates were parsed and the complete ten-moment verification was run A-B-B-A on one local Python host. We did **not** perform a new Boolean, native Jacobian or Newton solve.

| Archived H8e point | Original median (s) | Drop-in candidate median (s) | Isolated original/candidate |
|---|---:|---:|---:|
| 0 | 2.864411 | 1.978388 | 1.448x |
| 8 | 2.835331 | 1.908964 | 1.485x |
| 17 | 3.095065 | 1.961500 | 1.578x |

**Median of paired point medians:** old **2.864411 s**, candidate **1.961500 s**, an observed **1.460x** isolated verifier speedup. All **30/30 exact Fraction values** and their archived native binary64 projections matched; there is no numerical tolerance. The fully measured raw four-timing-per-point evidence and genuine material gzip SHAs are in `evidence/m21-dropin-real-3point.json`.

Prior pre-drop-in pilot using the same balanced arithmetic yielded 1.553x over points 0/8/17; it is a **separate run/implementation** and must not be combined with the drop-in figures. An initial four-point run with point 24 **timed out without a complete four-point receipt**; do not represent it as completed. The true frozen H8e original 8/24 feature-hash changes remain a failed historical scientific gate.

## Actually executed regressions and scope

`test_m21_dropin.py`: **10/10 passed**, testing pinned original Git blob, exact rational parsing including binary tokens/invalid tokens, signed tetrahedron, zero determinant, invalid face index/types, large denominators, original-versus-candidate Fraction equality on authentic H8e point 0, and evidence scope. Additional experimental benchmark-runner regressions **15/15 passed locally**, source/test code and full logs in the downloadable M21 archive. The strict W1 M9 material/Jacobian parity and W0 derivative admission have NOT been changed.

**Not measured or admitted:** new real Cherchi Boolean calls = 0, optimized native ABBA = 0, full Faster/Newton solver speedup = null. A 1.460x audit-only improvement should **never** be reported as 1.460x faster Boolean or full solver; it is only a candidate for optional future W1 profiling/validator integration. The real M19/M20 cloud profile is still blocked by CI owner activation issue #3.

## Reproduce

From the real W1 checkout, with the archived authentic H8e ZIP restored and SHA-authenticated, compare `research/Heart_v1_20261017/Heart_H8_Asymmetric_CAD_20261018/source/verify_h8_exact_moments.py` to `research/NeuralMoments/performance/m21_independent_verifier_candidate.py` on the same archived exact-rational vertices and face indices. Both expose `independent_ten_raw_moments(vertices,faces)`, and both return identical tuples of ten `fractions.Fraction` values. Then run:

```bash
export W1_M21_H8E_ARCHIVE=/path/to/h8e-25point-39121571756.zip
python -m unittest discover -s research/NeuralMoments/performance -p test_m21_dropin.py -v
```

Do not merge into shared production without W0 review, original compiler/source pin, formal independent verification and real same-host W1 native ABBA. This commit edits only W1-owned research files.

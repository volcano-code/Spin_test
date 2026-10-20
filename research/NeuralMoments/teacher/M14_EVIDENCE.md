# W2-M14 — projective identity handoff remains fail-closed (2026-10-20)

**Branch**: `research/neuralmoments-w2-teacher-20261019`  
**Only write path**: `research/NeuralMoments/teacher/`  
**Frozen source**: `0bcc187b3005478baa586a6d6f450e73811ca342`

## Verified source observations
- W2 M13 report: historical H8f source Actions run 39123384402, outcome **failure**. SHA-pinned M13 full report `2de535d1243802eba1826870001e7d7dc8c34ba8f6d911e933bc201da14ee8fc` (conversation artifact, not checked into Git).
- 81 distinct primitive integer positive-ray identities; 17/81 original native-c vectors satisfy the W0 norm rule, 64/81 do not. Original float c and same-call material SHA are not rewritten.
- W0 `w2_teacher_gate.py` still accepts only v1: Git blob `b42ec6d9b389675123250d79f9cc9efb1b658c07`. This **does not** establish W0 v2/projective acceptance.
- W3 latest Stage11 evidence blob `342b5e6968ba029c2af389de8de4a394543f422e`: no new native Cherchi side points, no admitted Newton, and no final Heart OBJ.
- Historical point60 remains feature-change / not a certified smooth neighborhood. There are 0 admitted Jacobian labels.

## M14 code
`m14_algebraic_handoff.py` independently verifies the frozen M13 full SHA, raw binary64 rational tokens, the `q=Bc` mapping, exact positive rational scale times primitive signed integer c, probe flags, 81 unique rays and non-release assertions. When W0/W3 external documents are supplied it checks their independent Git blobs and current W3 no-native/no-Newton status. Without them it records `observed=false`. It never rewrites the raw c or publishes a Jacobian.

`test_m14_algebraic_handoff.py` includes 16 tests. Tests with the real 381 KB M13 report require environment variable `W2_M13_FULL_REPORT`. This full report is **not committed** in source; original proof is pinned by SHA.

## Execution and scope disclosure
A locally implemented reference version of the M14 algorithm was **actually executed** against the original M13 full report: 81/81 exact reconstructions and 17/64 categorization passed. Its **19** local unit tests passed in 0.039 seconds. This local reference differs in function names/layout from the newly committed compact production module; the exact committed M14 tests **have not been run by GitHub Actions**, and no byte-identical checkout-based test evidence is claimed here. Commit SHA and changes are recorded on the W2 branch.

CLI from complete W2 checkout:
```bash
export W2_M13_FULL_REPORT=/path/to/M13_H8F_81_PROJECTIVE_HANDOFF.json
python -m unittest discover -s research/NeuralMoments/teacher -p test_m14_algebraic_handoff.py -v
python research/NeuralMoments/teacher/m14_algebraic_handoff.py \
  --m13 "$W2_M13_FULL_REPORT" --output /new/path/M14_HANDOFF_RESULT.json
```

## Non-admission
This is a **proposal and evidence transport for W0**, not a W0-approved v2 validator, online Cherchi run, numerical Jacobian derivative oracle, original-CAD proof, or continuous neighborhood certificate. W3 must independently produce and verify new sided native points. W2 must still independently demonstrate one fresh native Cherchi teacher for Frozen Heart and Noodles V7 on a compatible research host. **Training admission remains zero.**

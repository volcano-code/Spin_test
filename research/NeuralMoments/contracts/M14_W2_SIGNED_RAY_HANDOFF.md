# W0 M14 — archived native c and W2 M12 exact positive rays

**Status: HISTORICAL DIAGNOSTIC ONLY; NOT TEACHER/TRAINING RELEASE.** 2026-10-20.

W0 branch: `research/neuralmoments-w0-contract-20261019`. Frozen historical production source: `0bcc187b3005478baa586a6d6f450e73811ca342`. W0-only file scope: `research/NeuralMoments/contracts/` and `research/ParallelLaunch/`.

## Two different objects MUST NOT be conflated

- **Archived native c**: ten original binary64 components, including signed zero and all unnormalized finite-difference offsets. Bind their source `.json` and same-call material `.json.gz` SHA256, before any mathematical reinterpretation. This is the only c that was actually passed to Cherchi. Its native r and J, if archived, belong to exactly those source bytes.
- **Signed exact algebraic ray**: for a nonzero c, choose index p of the first component of maximum absolute magnitude; let `a = |c[p]| > 0`. Interpret each saved binary64 component exactly as a rational number and form `t_i = Q(c_i)/Q(a)`. SHA256 hash JSON array `["num/den", ...]`. The pivot scale is **positive**, so `c` and `-c` are different retained-halfspace rays. This only certifies an exact real polynomial zero-set identity under positive scaling, not identical floating Cherchi topology, source vertices, actual native J, material, or Newton terminal.
- **W0 unit c display**: if `abs(||c||₂-1)<=1e-12` keep c unchanged. Otherwise `c/||c||` is a rounded `float64` *display*, not a new source evaluation; the exact rational ray of this display is generally different. For the real 81 points exactly 17/81 display rays equal source rays; **0/64 nonunit** displays do.
- **Polynomial monomial q** is `B*c`, where `Bdiag=(1,1,1,1,1,1,1,2,2,2)`; it is not W2's legacy `q` name for native c. Preserve `c[7]=3e-6`, `q[7]=6e-6` for H8f point 60.

## Pinned remote / original evidence

- Historical H8f GitHub Actions run `39123384402`: failure, not promoted. Exact artifact `12135528290`, ZIP SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`.
- W2 M12 authoritative JSON: `research/NeuralMoments/teacher/M12_H8F_81_PROJECTIVE_RAYS.json` at observed W2 head `4b1301c6b478437f29836e78be0b773b9d145787`. Git blob `2d4cf4aae1368e22e760803d9bfe49479125ac4b`, full raw JSON SHA256 `255769c4401a89449ef864bf0ef72ec99403d0085b5eb04891512dfe2daab473`.
- W0 source independently computes 81 rows `[i, SHA256(canonical original float c), SHA256(signed ray tokens), original gzip SHA256, unit-c bool, binary64 display same exact Q ray bool]`. Its compact canonical array Git blob SHA1 **must** equal `051a9bb7149ff63af92d7018019165face426f52`, calculated independently from the exact W2 Git blob. This covers all 81 original c AND material gzip identities rather than just comparing summary counts.
- W2 M12 original JSON was inspected and all 81 original c, exact rational tokens, material digests, q mapping and unit flags were compared against W0 M13 source rows via the GitHub connector. The local reproducibility test does not need a duplicate 192KB W2 JSON because the 81-row aggregate is pinned; optional `--w2-m12-ledger` additionally requires the *full exact* original W2 JSON bytes and verifies every row.

## Reproduction

```bash
cd /path/to/Spin_test # checked out on W0 branch
export W0_M14_REAL_ZIP=/path/to/authentic-h8f-artifact-12135528290.zip
python -m pytest -q research/NeuralMoments/contracts/test_w2_ray_compatibility_m14.py
python -m research.NeuralMoments.contracts.w2_ray_compatibility_m14 \
  --original-h8f-zip "$W0_M14_REAL_ZIP" \
  --output /new/path/w0_m14_archived_ray_evidence.json
# When the exact original W2 file has been separately downloaded:
python -m research.NeuralMoments.contracts.w2_ray_compatibility_m14 \
  --original-h8f-zip "$W0_M14_REAL_ZIP" \
  --w2-m12-ledger /path/to/exact-W2-M12-81-ledger.json \
  --output /another/new/path/w0_m14_full_w2_byte_review.json
```

All exported M14 objects conform to `schema_archived_ray_m14.json` (read-only diagnostic only), require `training_admissible=false`, `derivative_J_D=null`, `newton_admitted=false`, and explicitly preserve the original H8f failure. **Existing** `schema_v1.json`, `validate_contract_v1.py`, and the original `MomentContractV1` unit-c requirement remain UNCHANGED.

## Other-window dependency

W3 Stage 12 head `d69a9c91bf3a9359cf2a480fc22fec8bc8393ca3`: `H9_STAGE12_EXECUTION_EVIDENCE.json` Git blob `23a593a3c902d493e7acb72a163b2d37db394c97`, read-only. Early captured `unverified-*` packets are not four qualified side materials. W3 still has 0 new native samples, 0 accepted Newton, 0 final Heart. W0 M12 Stage10 source/binary locks cannot silently be reused after W3 Stage11/12 code changes. Re-freeze source, build, and binary identities before any **future** W3 native run; then independently audit all four new materials through W0 M11/M12.

No W0-side mathematical gate, exact-rational ray equality or W2 label envelope can authorize W5/W6 training, full material partition, smooth neighborhood or Newton acceptance. These are separately witnessed future steps, not a threshold tweak.

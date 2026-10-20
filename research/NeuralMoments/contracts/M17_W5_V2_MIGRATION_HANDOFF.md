# W0 M17 — W5 v2 native-teacher consumer migration contract

**Branch:** `research/neuralmoments-w0-contract-20261019`; only W0 files and the previously authorized `.github/workflows/w0-contract-ci.yml` are changed. This is a **reference implementation and an adversarial executable review**, NOT a W5 branch change or a real Cherchi teacher release.

## Actual observed incompatibility

The byte-pinned W2 v2 manifest (`41e7c4dc65a029a3cc7ce746c694bc8a03cdad70`) has `native_teacher_runs=0`, `training_samples=0`, and all **81 H8f historical candidates in `excluded`**, all Jacobians unapproved. The source-linked original H8f Actions run `39123384402` remains **failure** (81 native samples and 30 finite differences, with point-60 symbolic constructor change). W2 v2 uses `payload.native_c` for the **saved** symmetric-entry native coefficients, legacy `payload.q` is an alias of the native coefficients, and `payload.polynomial_q=Bc`, with the last three entries doubled.

The original W5 `contract_gate.py` at Git blob `14b2ab225a032188fe16570414ef321af9a81e00` is **v1-only**, and its structural `check_w0_contract` tests `abs(||c||₂−1) <= 1e-9`, whereas W0's actual `validate_contract_v1.py` (blob `fe5f71e7cb2b6c6ad45f48c49ab4042f797a113e`) uses **1e-12**. The M17 executable regression runs both real source functions on exactly the same non-unit dummy W0 record (`c=[1+4e-10,0,…,0]`); **W5 accepts structurally, W0 rejects**. This is not proof that W5 ever ingested or trained on that record; the W5 importer also has other independent safeguards.

## W5-owned migration acceptance criteria

1. On the **W5 branch**, introduce an explicitly versioned v2 ingestion path, keeping v1 parsing separate. Reject unknown future versions rather than mass-replacing a schema string.
2. Require the saved `native_c` binary64 vector and legacy `q` alias to agree **exactly**, enforce `polynomial_q=Bc` in correct native order, and preserve the original same-call material SHA, raw coefficient and native Jacobian identity. A display-normalized coefficient never replaces the raw native input.
3. Match W0's `1e-12` native unit-norm rule for serialized `MomentContractV1`. Nonunit H8f stencil points must remain in a **diagnostic-only** raw-c/projective-ray archive (M13–M14), never silently re-normalize their `r_D` or `J_D`.
4. Validate independently frozen geometry/model/native IDs and enforce `fixed_r` added only once. A self-attested SHA, `native_cherchi=true` field, `topology_status=VALID` or `NATIVE_VERIFIED` string **never proves** full exact material or a continuous derivative neighborhood.
5. The 81 historical candidates remain `excluded`; no `train/val/test`, no usable teacher `J_D`, no formal Newton terminal or physical certification. W5's analytic P0 benchmark is separate from independently sealed Cherchi truth.
6. W5 must run this W0 M17 test suite against **its real modified source** and return its own test SHA and commit. Then W0 may update its frozen expected Git blob and accept the new *structural* interface, without automatically authorizing training.

## Run and meaning

```
python -m pytest -q research/NeuralMoments/contracts/test_consumer_v2_preview_m17.py
python -m research.NeuralMoments.contracts.consumer_v2_preview_m17 --output /new/path/m17_runtime_diff.json
```

The W0 CI job invokes these alongside M16 source-pinned checks and uploads the JSON discrepancy. Exit zero means the **expected existing incompatibility was reproduced and labels remained blocked**, not that v2 has been implemented in W5 or that any native material was certified. The adapter `archived_v2_preview` accepts only source/geometry pinned **excluded v2 diagnostic** envelopes and always returns `training_admitted=false` with no training targets. Positive successful fixtures in tests are explicitly synthetic.

No W3 four-side certified native packets or independently sealed accepted Newton terminal were supplied at this milestone; these remain scientific dependencies. Do not modify old failed CI or another window's branch.

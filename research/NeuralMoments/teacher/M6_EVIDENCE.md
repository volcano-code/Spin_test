# W2 M6 | Frozen Native-C, same-call seal, independent ten-moment budget

Repository: `volcano-code/Spin_test`
Write branch: `research/neuralmoments-w2-teacher-20261019`
Write scope: `research/NeuralMoments/teacher/` only.
Previous reference: `M5_EVIDENCE.md` (preserved, not overwritten).

## Actual execution (2026-10-19)

- Environment: Python 3.13.5, NumPy installed, compiled `make_it_stand` / `_cherchi_core_boolean` absent.
- GitHub checkout: `git ls-remote https://github.com/volcano-code/Spin_test.git` failed with `Could not resolve host: github.com`. Local copies of **exact source blobs** from the W2 branch were used and verified against GitHub connector blob SHAs.
- Command (local mirror of `research/NeuralMoments/teacher/`):
  `python -m unittest discover -s . -p 'test_*.py' -v`
- Result: **45 tests run, 45 passed, 0 failed (0.038–0.043 seconds)**. Includes mathematical exact box reference, ten-moment error budget, native-C cross term factor B, same-call attachment validation (unit-test double), input mutation, source pinning, atomic writes, anti-tamper reload and mock exclusion.
- Raw local stdout available as a conversation artifact (`unittest_m6.log`). This is NOT a GitHub Actions result.

**Actual one-shot runner preflight** (test-only deliberately incomplete input):
```text
python run_native_smoke.py --spec mock_preflight_v2_spec.json --output mock_preflight_v2_failure.json
exit code: 2
status: FAILED_PREFLIGHT
error: ModuleNotFoundError: No module named 'make_it_stand'
native_cherchi_verified: false
training_admitted: false
```
The new failure record was written to disk and re-read. No real Cherchi evaluation or H8/Heart/Noodles model was executed. Production native teacher samples: **0**. Admitted training samples: **0**.

## M6 correctness changes

1. **W0 coefficient identity alignment.** W0's branch supplies `MomentContractV1` JSON schema (Git blob `52c2cfa54567d7dc2164c4b9eb56e8385c0ee1dc`). W0 native symmetric-matrix coefficients are **c** with order `CONST,X,Y,Z,XX,YY,ZZ,YZ,XZ,XY`, and polynomial coefficients are `q=Bc`, `Bdiag=(1,1,1,1,1,1,1,2,2,2)`. The new W2 label stores explicit `native_c` and `polynomial_q`. Historical pre-W0 `payload.q` is a native-c alias only. New labels use `w2-cherchi-teacher-v2-pre-w0` and are intentionally not claimed to be full W0 records.
2. **Producer same-call proof.** Authenticated in-process Cherchi must supply a serialized material attachment through `evaluator.material(c)` and verify it using its own `validate_same_call_material`. We cross-check its coefficients, total/variable ten moments, 10×10 Jacobian, geometry/topology/backend/evaluation-map identities. A hash of the validated material attachment is included.
3. **Independent exact reference.** The same-call rational boundary is integrated independently via signed tetrahedra. Actual native path MUST supply ten explicit, per-case **absolute moment error tolerances** before evaluating. Reports include all component errors and normalized-to-budget errors. This numerical consistency test alone does not certify embedded material, exact Boolean set, 3D printability or derivative neighborhood.
4. **Frozen file identities.** Preflight rejects changed model bytes, mutated native-c coefficients, an ambiguous `q` field, missing/invalid module SHA and absent ten-moment budgets. During a native call the model and native binary bytes are hashed again. Frozen request/settings/spec SHA commitments are added to the geometry metadata, while `model_to_request_geometry_verified` remains **false** until a separate trusted source-model correspondence proof exists.
5. **Persistence.** Complete labels/failure preflight records are fsynced and linked into place exclusively; existing reports are never overwritten, even when a retry fails. Records are reloaded and checked against the expected frozen model, module and native-c identities. Process RSS high-water is measured but is **not** labelled per-call peak memory.
6. **Derivative safety.** The presence of a W0 JSON schema is **not** the trusted W0 local-neighborhood verifier. W2 keeps `J_D=null`, derivative `UNKNOWN`, split `excluded` for successful pre-W0 physical-moment packets. H8 point60 branch-change/unknown and open Teapot boundary are not admitted.

## One actual Cherchi run on the compiled research host

Do not invent sample meshes or model results. Reuse a **previously validated, frozen closed input** and the actual registered native-c vector. Export the already validated request/solver controls and freeze all provenance **before** executing Cherchi:

```python
from dataclasses import asdict
from pathlib import Path
import json
from make_it_stand import spin
from research.NeuralMoments.teacher.native_cherchi_teacher import digest
from research.NeuralMoments.teacher.cherchi_single_request import sha256_file
from research.NeuralMoments.teacher.run_native_smoke import FROZEN_SOURCE_SHA

model = Path(frozen_model_path)               # independently verified source model
native = Path(spin._native_module().__file__)  # actual compiled binary used in this run
c = [float(x) for x in verified_native_c]      # native symmetric-entry c, NOT polynomial q
budget = list(predeclared_ten_abs_error_budget) # case-specific, in target-frame moment units
spec = {
    "schema": "w2-one-cherchi-request-v2",
    "source_sha": FROZEN_SOURCE_SHA,
    "model_path": str(model.resolve()),
    "expected_model_sha256": sha256_file(model),
    "expected_native_module_sha256": sha256_file(native),
    "request": asdict(validated_faster_request),
    "evaluator_settings": asdict(validated_evaluator_settings),
    "native_c": c,
    "expected_native_c_sha256": digest(c),
    "reference_absolute_tolerances": budget,
    "geometry": {"model_id": known_validated_model_id},
    "frame": {"name": "INPUT_NORMALIZED_TARGET_V1"},
    "normalization": known_normalization,
}
Path("w2-frozen-v2-spec.json").write_text(json.dumps(spec, allow_nan=False))
```

Then from repository root (ensuring the package import is available in `PYTHONPATH`):

```bash
PYTHONPATH=python:. timeout --signal=TERM --kill-after=10s 60m \
  python research/NeuralMoments/teacher/run_native_smoke.py \
  --spec w2-frozen-v2-spec.json \
  --output w2-native-once.json
```

Run **serially**, respecting the agreed 24GiB/swap0 host resource protocol; no shared heavy Cherchi jobs with W1/W3. On failure a failed preflight or failed same-call label remains as immutable evidence. This M6 tool does not create formal training truth on its own.

## Remaining real acceptance

- Install/build compatible Spin/Cherchi modules in the research host (no local compiled module in this sandbox).
- Run one already authenticated closed Heart/Noodles material with exactly the frozen `native_c`.
- Confirm true geometry region/non-self-intersection status using a separate independent native exact material proof, in addition to these ten-moment checks.
- Publish real per-component `r_D` errors, total `r_F+r_D`, stage runtimes, and process RSS high-water, retaining every failed run.
- Integrate an independently verifiable W0 signed/frozen neighborhood decision before exposing true `J_D` training labels.

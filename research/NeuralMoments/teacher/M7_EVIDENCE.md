# W2 M7 | Frozen OBJ-to-request identity gate

Branch: `research/neuralmoments-w2-teacher-20261019`
Exclusive scope: `research/NeuralMoments/teacher/`
Source revision pinned by W2: `0bcc187b3005478baa586a6d6f450e73811ca342`
Predecessor: `M6_EVIDENCE.md` (left intact).

## Executed 2026-10-19

Environment: Python 3.13.5 / NumPy; compiled project Python package `make_it_stand` and `_cherchi_core_boolean` **not available**. The container cannot clone from GitHub: `Could not resolve host: github.com`. The GitHub connector can fetch and update repository files.

After verifying M6's six source/test Git blobs against the connector, M7 was developed in a separate local test mirror. The three newly changed files were fetched again from W2 and their Git object hashes checked byte-for-byte against the tested mirror:

- `frozen_model_binding.py`: `036554096c2cdeacb93455ca3b51d4a9abf08efe`
- `run_native_smoke.py`: `58031d76c9aecf5700071c9b02a712114855e95c`
- `test_frozen_model_binding.py`: `861da6c0db1662209cb0bca67e3e070f0b8b5e44`

Command:
```bash
cd /mnt/data/w2_m7
python -m unittest discover -s . -p 'test_*.py' -v
```
**61 tests executed, 61 passed, 0 failed (0.068 seconds).** Fifteen of the new cases exercise ordered OBJ correspondence, physical-to-normalized coordinates, wrong transforms, open/duplicate/wrong-winding faces, unsupported polygon faces, relative indices, NaN vertices, frozen spec gating and malformed face indices. These tests are on fixture data; they are NOT real Cherchi evaluations or GitHub CI.

Executed an additional end-to-end CLI preflight using a *deliberately synthetic* v3 specification and a small indexed closed box OBJ. The OBJ-to-request correspondence gate passed before the attempted native import. The command returned **exit code 2**, with this persisted failure evidence:
```text
schema: w2-native-smoke-preflight-v2
status: FAILED_PREFLIGHT
phase: NATIVE_SETUP_OR_EVALUATION
error: ModuleNotFoundError: No module named 'make_it_stand'
training_admitted: false
native_cherchi_verified: false
```
It **did not** call a Cherchi native evaluator. Real native teacher samples: **0**; formally admitted training samples: **0**. There are no real native moment errors, compute timings, or memory readings to report.

## New source/model correspondence contract

New file `frozen_model_binding.py` independently parses frozen indexed OBJ triangles. For a version-3 single-request specification it requires:

1. `model_geometry_binding.mode` is exactly `OBJ_IS_INPUT_NORMALIZED_OUTER_V1` **or** `OBJ_PHYSICAL_TO_INPUT_NORMALIZED_OUTER_V1`.
2. The source OBJ bytes match the supplied `expected_model_sha256`.
3. Every normalized **binary64 vertex**, indexed triangle, face ordering and winding matches `request.outer_vertices` and `request.outer_faces`, without indexing repair or tolerance-based reinterpretation.
4. In physical-source mode, the locked map `(OBJ_vertices - normalization.origin) / normalization.L` matches the same arrays, and `request.original_units_per_normalized_unit == normalization.L`.
5. Every directed triangle edge is paired with exactly one oppositely oriented edge; duplicate triangles, open edges, nonmanifold edges and unsupported OBJ geometry are rejected.

The returned proof carries the mesh file SHA, both native array byte SHAs, vertex/face counts, binding mode and explicit limitations. Binding is repeated before and after native work to help detect file replacement.

**This is a strict representation check, not an exact self-intersection or embedding proof.** An originally distinct CAD/OBJ with identical bytes/geometry cannot establish independent source provenance. Matching the outer mesh does not by itself certify the design/fixed partition or any W0 smooth-neighborhood derivative. The native Cherchi source and final Boolean material still require their independent exact audits.

## Versioning and branch safety

- `w2-one-cherchi-request-v3` is required for a real native attempt and includes `model_geometry_binding`.
- M6 version `v2` is still parseable for preserving historic preflight/mock evidence, but now **cannot launch a native Cherchi evaluation**.
- On preflight failure, a report is saved with exclusive/atomic no-overwrite semantics; no fabricated teacher label is added to the manifest.
- All changes belong to the W2 branch's exclusive teacher directory; no shared core, other W branches or historic artifacts are modified.
- H8 point60 continues `branch-change/unknown`; unclosed Teapot is not admitted; only separately valid frozen Heart/Noodles can be promoted after native reference comparison.

## Next real experimental step

On the user's research machine, where the compatible native Spin/Cherchi modules and **actual frozen** Heart/Noodles geometry are installed, export one `SpinItFasterRequest`, its actual native-C ten coefficients, predeclared ten independent reference tolerances, and an indexed OBJ in the *same* order as the request's outer mesh.

Use an explicit v3 `model_geometry_binding`; for original physical OBJ, set `OBJ_PHYSICAL_TO_INPUT_NORMALIZED_OUTER_V1` and carry the locked `normalization.origin` and `normalization.L`. Run one request only, serially:

```bash
PYTHONPATH=python:. timeout --signal=TERM --kill-after=10s 60m \
  python research/NeuralMoments/teacher/run_native_smoke.py \
  --spec w2-frozen-v3-heart-or-noodles.json \
  --output w2-native-real-once.json
```

Do not run multiple concurrent Cherchi jobs. Enforce the existing research-host 24GiB/swap0 and maximum-60-minute policies. Log actual per-stage timing, Linux process-lifetime RSS high water (not per-call peak), independent exact ten-moment errors, fixed/variable separation and negative cases. Retain all failures. Neither the new OBJ binding nor the W0 schema alone permits derivative `J_D` to train until the independently validated `MomentContractV1` neighborhood rule is integrated.

# W2 M5 — independent ten-moment audit and one-call native runner

Branch: `research/neuralmoments-w2-teacher-20261019` only.
Scope: `research/NeuralMoments/teacher/` only.
No changes to shared core, other W branches, stored model data or existing failed reports.

## Actual execution (2026-10-19)

Command on a Python 3.13.5 / NumPy 2.3.5 analysis environment:

```bash
python -m unittest discover -s research/NeuralMoments/teacher -p 'test_*.py' -v
```

The same W2 source files and unit tests were placed in a local mirror (direct checkout was blocked because github.com DNS resolution failed). Their Git blob hashes were checked against GitHub connector `fetch_file` results. **31/31 locally executed tests passed**, in approximately 0.02 seconds. This is not a GitHub Actions result and not a real Cherchi result.

- Independent closed oriented 2×3×4 box, density=2.0: exact raw ten moments `[48,48,72,96,64,144,256,144,96,72]`.
- Independent exact vs box analytic reference: **maximum absolute error = 0** (mathematical reference, not native Cherchi accuracy).
- Rejected open/wrong-winding/negative-orientation/degenerate/duplicate faces and altered cross moment.
- Rejected tampered or incorrectly reloaded identities; verified mock double-count rejection, failure-label reload and conservative derivative handling.
- Reference uses exact rational tetrahedron integration. **Oriented closure alone does not certify non-self-intersection, embedding, valid Boolean material or a smooth derivative neighborhood.**

## Real-native attempt and blocker

A single CLI preflight was actually run, using a **test-only incomplete JSON request**. It wrote a `w2-native-smoke-preflight-v1` failure record with:

```text
status: FAILED_PREFLIGHT
error: ModuleNotFoundError: No module named 'make_it_stand'
```

The environment does not contain the project's compiled Spin/Cherchi extension, and direct Git clone is DNS-blocked. No production native Cherchi geometry evaluation has been performed; **native teacher samples = 0, admitted training samples = 0**. Do not reinterpret preflight failure as a geometric/material failure. No H8 point60, Frozen Heart, Noodles V7 or open Teapot case was used as training truth.

## Run one real native evaluation on a machine with the compiled project

Prepare a frozen JSON spec with:

- `schema = "w2-one-cherchi-request-v1"`
- `model_path`: path to the frozen source/model file (SHA256 bound; caller must separately establish that it corresponds to the request geometry)
- `request`: a JSON serialization of a valid `SpinItFasterRequest`, including its actual `design_vertices`, `design_faces`, `outer_vertices`, `outer_faces`, material density, optional solver settings
- `evaluator_settings`: a JSON serialization of the exact `SpinEvaluatorConfig` for the frozen run, including derivative method
- `q`: **ten coefficients**, in native matrix-entry order, not swapped cross terms
- `geometry`, `frame`: explicit frozen geometry/frame metadata
- Optional `normalization`, `design_vertices_physical`, `rational_arithmetic_backend` as required by that frozen case
- **No** caller-supplied `derivative_contract` may assert W0 admission.

Example export from an existing already validated Python request (do not fabricate a fresh test model):

```python
from dataclasses import asdict
import json
spec = {
    "schema": "w2-one-cherchi-request-v1",
    "model_path": str(frozen_model_path),
    "request": asdict(request),
    "evaluator_settings": asdict(evaluator_settings),
    "q": list(frozen_quadric_q),
    "geometry": dict(model_id=known_model_id),
    "frame": dict(name="actual_target_frame"),
    "normalization": known_normalization,
}
with open("frozen-w2-single.json", "x") as f:
    json.dump(spec, f, allow_nan=False)
```

From the `Spin_test` repository root, with Python native build installed and `PYTHONPATH=python`:

```bash
PYTHONPATH=python timeout --signal=TERM --kill-after=10s 60m \
  python research/NeuralMoments/teacher/run_native_smoke.py \
  --spec frozen-w2-single.json \
  --output w2-single-label.json
```

Only **one** evaluator call is issued; it does not launch a Newton solve or a batch. Run serially and within the agreed 24GiB/swap0 resource profile. The caller is responsible for enforcing the memory/swap policy on the host. Files are created exclusively and existing evidence is never overwritten.

For an authenticated native call the wrapper compares the returned variable moments against its **same-call exact rational retained boundary** using the separate tetrahedron reference. `r_F` remains separate, so `r_total=r_F+r_D` and `J_total=J_D` are never double-counted. Every result/failure that reaches the wrapper is sealed and reloaded; pre-import/setup failures are recorded separately as `FAILED_PREFLIGHT`.

**W0 constraint:** the formal `MomentContractV1` verifier is not yet integrated. Even a successful native run is a pre-W0 label with `J_D=null`, derivative `UNKNOWN`, split `excluded`, and no training admission. The raw source map may have produced an internal Jacobian, but this is not a validated derivative truth.

## Remaining acceptance

1. Run a frozen closed Heart/Noodles sample using the actual compiled native modules (not this analysis container).
2. Independently certify exact Boolean region validity and verify ten moments from the retained boundary; report observed per-component numeric errors.
3. Preserve wall/stage timing and Linux **process lifetime RSS high-water mark** (not falsely claim per-call peak memory).
4. Add a trusted W0 signed/verified derivative-neighborhood evidence path before admitting `J_D` or publishing a formal teacher training split.
5. Keep H8 point60 as branch-change/unknown and open Teapot invalid as a volume teacher.

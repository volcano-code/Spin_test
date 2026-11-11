# W1 M29: missing M9 baseline path recovery

## User-reported blocker

The M29.3.2.2 invocation with output name `w1-m29-3-2-2-branch-diagnostic-20261111-133232` stopped at `Path(m9_run).resolve(strict=True)` because `/home/lin/w1-m29-m9-fixed-20261108-181458` could not be resolved. This is before native preflight, output directory creation, and the first new Cherchi evaluation. No new branch-diagnostic native evaluations ran in this failed invocation. The trace does not establish whether the original report was moved, deleted, archived, or made inaccessible by a changed mount or broken symbolic link.

Do not make an empty replacement directory, change strict path validation to hide the error, substitute the H8c input archive for an M9 output report, or reconstruct a passing report from chat summaries. Preserve the old failure log and prior evidence.

## Added read-only recovery tool

`m29_locate_m9_baseline.py` searches bounded, explicitly supplied directory trees for `baseline-performance.json` or `m9-baseline-performance.json`. It accepts candidates only when known M9 schema, H8c input digest, frozen production source, three native binary digests, ABBA order, material/geometry digests, and finite numerical field checks match. It reports SHA-256 of the candidate file. This is an identity-filtering aid, NOT independent material authentication or proof of execution. The original baseline report file hash was not provided, so an exact forensic file-identity claim is not possible here.

The tool does not import NumPy or native extensions, mutate any discovered file, extract archives, select one of multiple candidates, create a replacement report, or start a new experiment. Archive names containing `m9` are listed only as uninspected leads. A limited search with no match is not proof of deletion. Depth cutoffs, time/directory limits, inaccessible paths, and skipped directory classes are included in its output.

Example, from the user's local W1 checkout:

```bash
PERF=/data/xvxinyao1/Spin_test-W1/Spin_test-w1/research/NeuralMoments/performance
python3 "$PERF/m29_locate_m9_baseline.py" \
  --root /data/xvxinyao1/Spin_test-W1 \
  --root "$HOME" \
  --root /data/xvxinyao1 \
  --max-depth 8 --max-seconds 60 --max-directories 20000
```

Exit 0 means matching report candidates were found; exit 2 means none matched within the scoped search. Neither result automatically runs M29.3.2.2. A candidate named `m9-baseline-performance.json` is not directly accepted by the current runner, which opens `baseline-performance.json` in the `--m9-run` directory. Preserve the candidate and inspect it before any controlled copying/renaming.

Once the original report is located and checked, use its actual parent directory for `--m9-run`. Keep new diagnostic outputs/logs on the user's `/data` filesystem rather than `/home`: the provided snapshot shows only 3.8 GB free on `/home`, versus 58 GB on `/data`. Do not delete or move existing evidence as part of this repair. A new output directory must not already exist.

## Tests actually run in this assistant's working container

Interpreter: Python 3.13.5. Command:

```bash
python -m unittest -v test_m29_locate_m9_baseline.py
```

Result: 11 tests ran; all passed. They cover valid identity, wrong material, wrong binary identity, missing/nonfinite Jacobian, rejection of M5/FD summaries, moved report lookup without mutation, multiple candidates, missing/depth-limited roots, uninspected archive listing, directory limits, and renamed report filenames. Tests use synthetic fixtures only; they do not establish that the user's local report has been recovered.

SHA-256 of tested source: `8ea3a3b1ec9f3858eeea33dd8056bbda0c1b66f062461d9a5b1f27c3e462867d`.
SHA-256 of test source: `171403074897ec15a1ede6a6fe481bd8c4174b834ea413ce400487a7ca71ed06`.
SHA-256 of captured unittest log: `b32174f6b4369b5859f0d54c94f16c0d80c36206f4331af461720fa2c1d9d5ba`.

## Status

The production evaluator, branch policy, finite-difference tolerances, and historical experiment data are unchanged. The M9 baseline's current host location is unresolved. Native evaluations in this recovery development: 0. Full nine-direction derivative admission, smooth-neighborhood admission, Newton convergence, and full-solver speedup remain unverified. Only the W1 performance subtree and W1 branch were changed.

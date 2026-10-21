# W2-M17 — Frozen Noodles V7 source recovery and fresh Heart preflight

Date: 2026-10-21. Only `research/neuralmoments-w2-teacher-20261019` branch, only `research/NeuralMoments/teacher/`. No mutation of main, W0, W3, compiled common core, historical failures, or original models.

## 1. What actually ran

**Frozen Heart.** Re-ran the M16 original H8f archive preflight from the verified bundle against the real `h8f_81_real.zip` (SHA256 `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`) using `--execute-native`. **Exit code 2**, `BLOCKED_BEFORE_NATIVE_CALL`; persisted local evidence SHA256 `0af26402b70ac74ab638a3d90efe87779bd13cf74d4e5d8f6fc9def068dd5683`. This runner checked the real immutable Heart input again and refused native execution because cgroup memory limit was 4 GiB (minimum 24 GiB), complete W2 Git checkout, three externally SHA-pinned compiled native modules, and a separate predeclared ten-moment Cherchi error budget were missing. **No Cherchi native evaluation was launched.**

**Noodles V7.** Examined the actual `Spin_test/main` source manifest `research/Noodles_v7_20261017/frozen-parts-v7c/manifest.json` (Git blob `f476a8c3e87bd30ef186b24442f641c2602c32ec`), original Python generator, source audit, 96-operation CSG construction receipt `1e824c72d5ee13cc484bbf60a0be9b79be86d787` and old Newton request. The manifest specifies **94 parts / 93 fixed parts**. Its **94 mesh sources and actual post-CSG F/D/A rational packets were not all committed to the accessible Git tree**; a recipe and SHA receipts are not equivalent to the missing files.

**Actual source reconstruction (not mock):** used NumPy/trimesh and the frozen v7 geometry recipe to regenerate THREE primitive source meshes: `outer-ellipsoid`, `hub-fixed`, `pin-fixed`. Re-serialized all in model units and in SI coordinates, using the generator's exact 17-digit OBJ writer. All **six generated OBJ SHA256s** match the frozen original main manifest. The exact meshes have **642/1280**, **50/96** and **530/1056** vertices/triangles respectively, with oriented closed topology and positive volume. The other **91 parts are not yet verified**. These three are upstream input primitives, not an admitted exact CSG material.

## 2. Code and tests

- `m17_core_sha_reconstruction.py` implements bit-for-bit regeneration of the three original parts and strict SHA gates for all 94 original source part pairs and for all six historical rational CSG output packets when supplied separately. Missing F/D/A files are **not** forged, downloaded from guessed locations, or silently replaced with CGAL approximations.
- `test_m17_core_sha_reconstruction.py` is byte-identical to the locally **executed 9-test suite**; **9/9 PASS** (0.064 s). Tests confirm all six real source-file SHA values and counts, topology, no overwrite, injected hash drift, fake manifest and fake CSG receipt rejection. Git blobs: source `bf170cae1d2f6b13a5c2005a507b7f317524da8c`, tests `dc6d60d153a0dff0513e3e049ce047180f3be3c8`.
- Also ran an expanded **19/19 PASS** local recovery test suite on the same true regenerated source geometry, including generator identity checks and negative source/csg failure records; expanded implementation remains a separate *local* supplementary artifact, not claimed to be byte-identical to the compact committed module.
- Compact evidence in `M17_NOODLES_AND_HEART_RECOVERY_RESULT.json`. Native evaluations=0, training admitted=0, `J_D=null`.

## 3. How to reproduce

From a W2 checkout with Python/NumPy/trimesh:

```bash
python -m unittest discover -s research/NeuralMoments/teacher -p test_m17_core_sha_reconstruction.py -v
PYTHONPATH=research/NeuralMoments/teacher python - <<'PY'
from pathlib import Path
from m17_core_sha_reconstruction import reproduce
print(reproduce(Path('/tmp/w2-m17-new-frozen-core')))
PY
```

For a **separately obtained, byte-identical** original `Spin_test/main` full source bundle, use `inspect_full_source(source_parts_dir, manifest)` and require all 188 model/SI SHA matches (94 source parts). For historical exact rational Boolean outputs, use `inspect_csg(original_csg_dir, construction.json)` and require all six independently pinned packet SHAs. Neither check alone constitutes a fresh Cherchi call or certifies binary64 F/D/A partition. Do not use the optimized final V7 OBJ as source F/D geometry.

Once an authenticated complete source request exists, execute **one** new Noodles teacher call under the existing W2 preflight (at least 24 GiB effective memory, swap=0, original immutable compiled modules and source commit SHA, independent ten-moment oracle, single serial job ≤60 minutes). W0 derivative neighborhood and W3 point60 remain independent scientific gates; `train/val/test` admission remains zero.

## 4. Next milestone

M18 should prioritize actual remaining 91-source re-generation from the pinned `noodles_paper_geometry_v7.py` and dependencies, followed by recovering or reproducibly rebuilding all source F/D/A exact CSG packets and verifying the full frozen native request; separately perform a fresh Heart native teacher run on qualified hardware. The V7 photo-guided geometry is not original paper CAD. Historic V7 Newton convergence on the old binary does not authenticate a fresh teacher evaluation in this environment.

**M17 status: PARTIAL_RECOVERY_3_OF_94_NO_NEW_NATIVE_TEACHER**.

# W4 M22 — W0 M21 native/SI frame contract integrated into P30-B

**Result:** M22 software integration PASS; real P30-B pilot remains BLOCKED.  
**W4 branch HEAD:** `c16c0dcb6c4d50ec4039ae6aa62103099026132c`  
**M22 frame/CI receipt commit:** `65e0aea8886b707d95fc52d4a2883fb5e63b4982`  
**W0 M21 source HEAD:** `cd72c04631a672408aaf576ab1b98747625f9468`  
**W0 M21 tested implementation:** `e1b765c46bfce0ece47e0f691d8131f1b50c9b1d`

## What changed

- Vendored exact W0 M21 source modules under `P30/w0_m21_reference/`; each module is runtime-verified by Git blob SHA-1 and SHA-256. No runtime import from the W0 branch.
- Added `p30b_moment_frame.py` to load the frozen P20 request and frame report, derive the frame/affine identity, and build a separate view from the same-call native material.
- Updated P30-B authority to require W0 and W2 to agree on the exact frame metadata, including normalization, native density, affine identity, W0 source bundle and legacy normalization fields.
- Updated the sampler to preserve `MATERIAL_SAME_CALL.json` in native target coordinates and write a separately verifiable `MOMENT_FRAME_VIEW.json`. Every receipt, BEGIN, RUN_STATE, attempt and completion binds the frame and transform identities. Resume re-derives the view from the native source material.
- Updated the local Docker wrapper to accept `P30B_MOMENT_COORDINATE_FRAME`, defaulting to native mode.

## Coordinate contract

Native P20 Cherchi capture is always `INPUT_NORMALIZED_TARGET_V1` at native material density 1.0.

| Mode | L normalization | density normalization | r/J treatment |
|---|---:|---:|---|
| Native (default) | 1.0 | 1.0 | Preserve raw10 and Jc unchanged |
| Conditional SI | 0.06429 m | 1200 kg/m³ | Affine-pushforward all ten raw moments and all ten Jc output columns |

The SI values remain conditional conversions of an unapproved physical proposal. They are not an approval of the physical scale, material, support or printability. Coefficient vector c and tangent directions remain in native coefficient coordinates. The represented-tip translation residual is retained.

## Actual CI evidence

[GitHub Actions #42472917746](https://github.com/volcano-code/Spin_test/actions/runs/42472917746), head `65e0aea8886b707d95fc52d4a2883fb5e63b4982`, conclusion success.

- 20/20 P30-B sampler and append-only recovery unittests passed.
- 17/17 P30-B frame/transform pytest cases passed.
- 0 skipped.
- The workflow inspected actual W0/W2 branch checkouts and confirmed that both independent Teapot pilot authorization files are absent.
- Readiness returned the expected `BLOCKED_WAITING_INDEPENDENT_W0_W2_APPROVAL`.
- New Cherchi native calls: 0; genuine Teapot tangent samples: 0/12.
- No native 24-GiB pilot was run in CI.

Artifact: `W4-P30B-M22-native-SI-frame-37-regression-evidence`, ID `13614346750`, 7,262 bytes. The workflow's artifact metadata is the authoritative artifact identifier; do not substitute the similarly named P30 tangent-preflight artifact.

## Scientific state

All remain false: W0 physical case approval, W2 Teapot Teacher approval, P30-B real native authorization, continuous smoothness, Newton acceptance, training admission, physical strength/printability. M22 is an interface/math/software milestone only.

## Next work

1. W0 physical case remains BLOCKED until authoritative CAD or owner-defined new design, measured scale, material/fill, tip/contact/support, shaft/load and D strength requirements are supplied.
2. W2 must independently review the same Teapot source/Boolean/feature branch and Jc; Heart/Noodles evidence is not substitutable.
3. Once both owners publish compatible tracked diagnostic-only receipts and an independent lock is registered, W4 may run the 12-point pilot on the qualified local host.
4. Finite diagnostic points do not certify a continuous smooth neighborhood, Newton terminal or training readiness.

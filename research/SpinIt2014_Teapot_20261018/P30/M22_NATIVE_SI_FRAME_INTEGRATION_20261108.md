# W4 M22 — integrate W0 M21 native/SI mass-moment and Jacobian frame contract

**Scope:** W4-only implementation and software verification.  
**Scientific state:** W0 physical case remains BLOCKED; W2 Teapot approval absent; real Cherchi tangent samples remain 0/12.  
**No P30-B native worker was started.**

## 1. Frozen W0 M21 reference implementation

W4 vendors an exact, read-only copy of the W0 M21 source modules under `P30/w0_m21_reference/`; P30-B does not import from a W0 runtime checkout or depend on W0's branch being present.

| Source module | W0 Git blob SHA-1 |
|---|---|
| `teapot_moment_frame_m21.py` | `f38b135b9d61a214e2c8b4240654dcfd8a57fb47` |
| `moment_coordinates.py` | `7f844fadc02b8f02c8560b5180e29bac78332ab4` |
| `tangent_neighborhood.py` | `4fbfd52a787f3cbbc4228b1c1bbdab01638ed57f` |

Source branch HEAD at M22: `cd72c04631a672408aaf576ab1b98747625f9468`; implementation/test commit: `e1b765c46bfce0ece47e0f691d8131f1b50c9b1d`.

At runtime, `p30b_moment_frame.py` recomputes each vendored Git blob identity and SHA-256, the W0 source-bundle SHA-256, and the P20-derived frame/affine identities. A changed vendor file, frame contract, affine translation or density ratio is rejected before a sample can be accepted.

## 2. Exact P20 source inputs

- P20 request SHA-256: `a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9`
- P20 exact frame/physics report SHA-256: `eaba6b60753fcb2141be425081897a8e891821349c166f5daff143d3ce9ea5fc`

These are read directly from the frozen W4 P1 checkout. The M21 contract builder rejects changed bytes, duplicate JSON keys, altered exact frame values and mismatched coordinate assumptions.

## 3. Two explicit and non-interchangeable r/J modes

The native Cherchi capture is **always** preserved as `INPUT_NORMALIZED_TARGET_V1`. The command-line selection determines the separate, auditable moment view stored alongside it.

### Native mode (default)

```text
moment_coordinate_frame = INPUT_NORMALIZED_TARGET_V1
normalization_L = 1.0
normalization_R = 1.0
native_material_density = 1.0
coordinate_transform_applied = false
```

The raw ten moments and 10x10 Jc are unchanged. This is the default and is the only mode that should be used unless W0/W2 independently approve another mode.

### Conditional SI mode

```text
moment_coordinate_frame = P19_PROPOSED_SI_Z_UP
normalization_L = 0.06429 m
normalization_R = 1200 kg/m^3
native_material_density = 1.0
coordinate_transform_applied = true
```

For every sample, the same M21 affine pushforward is applied to the complete ten-entry raw-moment vector and to **each of the ten output columns of Jc**. The coefficient vector c and tangent directions remain in native coefficient coordinates. The exact represented-tip translation residual is retained.

The SI values are a **conditional coordinate representation** based on the still-unapproved P20 physical proposal. Transforming r/J into this representation does not approve 0.025 m/reference, 1200 kg/m³, physical support, material, printability or strength.

## 4. Evidence layout and resume contract

Each real point retains:
- `MATERIAL_SAME_CALL.json`: original same-call Cherchi material record in native target frame;
- `MOMENT_FRAME_VIEW.json`: independently recomputable native or conditional-SI view;
- `SAMPLE_RECEIPT.json`: selected frame, L/R, native density, transform flag, affine identity SHA, frame-contract SHA, W0 commit/blob/SHA provenance, native r/J hashes, view r/J hashes, and view file SHA;
- `ATTEMPT_RESULT.json` and `BEGIN.json`: same frame identity, lock and coefficient binding.

The batch `RUN_STATE.json` and `PILOT_COMPLETION.json` also bind the selected frame and identities. Resume re-derives the view from the native same-call material record and pinned W0 helper; it never trusts a stored SI matrix or skips a partially written/tampered point.

CLI selection:
- default: `--moment-coordinate-frame INPUT_NORMALIZED_TARGET_V1`
- conditional SI: `--moment-coordinate-frame P19_PROPOSED_SI_Z_UP`

The local wrapper exposes the same selection via `P30B_MOMENT_COORDINATE_FRAME`. The selected mode must exactly match both independently issued W0 and W2 approvals and the externally registered P30-B lock.

## 5. New approval fields required from W0 and W2

In addition to the previously pinned P20/P27/P30 identities, **both** tracked owner receipts must include:

- `moment_coordinate_frame`;
- `normalization_L` and `normalization_R` (must match the chosen mode);
- `native_material_density`;
- `frame_contract_sha256`;
- `affine_transform_identity_sha256`;
- `w0_m21_source_commit`;
- `w0_m21_source_bundle_sha256`;
- `w0_m21_source_files` with each Git blob SHA-1, SHA-256 and byte count;
- legacy `length_ref` and `density_ref`, exactly equal to `normalization_L/R`.

W0 and W2 must agree byte-for-byte on the selected frame metadata. W2's receipt must additionally bind the exact W0 authorization file SHA-256. A mismatch blocks lock creation and all native workers.

The W0 frame-bound audit helper also requires a W0 case-specific numerical budget receipt. No default tolerance is invented. A numerical tangent pass remains finite-sample diagnostic evidence only; it does not certify a continuous smooth neighborhood, Newton terminal, training or physical strength.

## 6. CI and actual result

GitHub Actions: [W4 P30B M22 frame integration CI](https://github.com/volcano-code/Spin_test/actions/runs/42472734377)

- 20/20 unittest sampler/append-only resume regressions passed;
- 17/17 pytest M21 frame/transform regressions passed;
- zero skipped;
- actual W0/W2 checkouts found no P30-B owner authorization and returned the expected fail-closed BLOCKED readiness;
- local wrapper syntax and 24 GiB/zero-swap policy checks passed;
- no native modules were loaded, no Cherchi call occurred, and no Teapot point was sampled.

CI artifact: `W4-P30B-M22-native-SI-frame-37-regression-evidence`, artifact ID `13614450510`, SHA-256 `8447285b685a38deb45caf0e86e0caff1c29f1c204070f66b2ab589cd2199398`.

## 7. Still blocked / next dependencies

1. W0 must retain its BLOCKED physical decision until authoritative CAD or a formally owner-defined new Spinning Top, measured scale, material/fill, tip/contact/support, shaft/load and D strength requirements are available.
2. W0's eventual diagnostic authorization must include the new M21 frame/source fields and a justified case-specific error budget; it must not set Newton/training true.
3. W2 must independently review the same Teapot base feature/source/Boolean and Jc, and bind the same M21 frame metadata plus W0 authorization SHA.
4. Only after both tracked receipts and an independently registered frame-bound P30-B lock may W4 execute the 12-point pilot on the qualified local host.

**M22 software integration is complete. P30-B remains unauthorized; 0/12 real native points.**

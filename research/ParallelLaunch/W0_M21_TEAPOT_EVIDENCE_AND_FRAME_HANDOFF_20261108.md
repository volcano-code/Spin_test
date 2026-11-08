# W0 M21 — Teapot source evidence binding and native/SI moment-frame contract

**State:** `SOURCE_BINDING_AND_FRAME_CONTRACT_PASS_PHYSICAL_CASE_STILL_BLOCKED`  
**Tested W0 commit:** `e1b765c46bfce0ece47e0f691d8131f1b50c9b1d`  
**Final M21 CI:** [run #42463041196](https://github.com/volcano-code/Spin_test/actions/runs/42463041196) — **203 passed, 7 parameterized subtests passed**, workflow steps all success.  
**Machine-readable report:** [W0_M21_TEAPOT_EVIDENCE_AND_FRAME_REPORT_20261108.json](../NeuralMoments/contracts/W0_M21_TEAPOT_EVIDENCE_AND_FRAME_REPORT_20261108.json).

## 1. Direct source-byte audit (not hand-entered digest comparison)

W0 CI now fetches the reviewed W4 branch head `aca53abf0d31329264fe1f028b2aff2175165ba3`, archives the actual P1 files, and recomputes SHA-256 from their bytes. It verifies **10 W4 source files**:

- P20 request;
- P19 material manifest;
- P19 canonical source report;
- P20 exact frame/physics report;
- M/F/D/S OBJ files;
- P20 native factory;
- P20 exact physical contract.

The audit cross-checks P20 request paths and SHA values against P19's manifest, P19 report and P20 frame report; checks M/F/D/S byte identities, saved-mesh mass/COM/inertia facts, shaft-accounting and approval flags; then compares every derived fact against the frozen W0 review evidence. A drift in the source bytes, cross-report references or review JSON fails CI.

The P20 frame report also pins the Core source commit `58fd12c1306c1c01679a19172e276eef0cb30542`. W0 CI now archives and directly re-hashes all **10 Core source files** named by that report, including `faster_material.py`, `spin_problem.py` and `cherchi_inprocess.py`. It separately hashes the W4 P20 factory and physical-contract files. This directly binds the code paths used to construct the native request, integrate moments and capture the Jacobian.

This is source integrity and code-provenance evidence. It is **not** a new native Cherchi execution, a fresh P19 mesh reintegration, an independent native set-predicate replay or a physical certificate. The P20 report itself says its source bytes were observed but the whole Core commit tree was not verified by that earlier report; M21 independently checks the exact listed source files at the pinned commit.

## 2. Corrected native-target versus SI coordinate contract

The M21 source audit establishes the P20 request facts:

- `fixed_density = 1`, `design_density = 1`;
- P20 physical replay density reference = 1;
- native coefficient frame = `INPUT_NORMALIZED_TARGET_V1`;
- exact Core normalization length = 2.5716 P19 reference units per target-normalized unit;
- original-per-native density scale = 1;
- target axes = identity for this frozen P20 case.

The Cherchi in-process evaluator integrates `variable_raw_moments` using the normalized target-frame geometry and the request's normalized material density. The same call produces `moment_jacobian` in that same frame. Therefore the valid **native-frame numerical audit normalization** is:

```text
moment_coordinate_frame = INPUT_NORMALIZED_TARGET_V1
length_ref = 1
density_ref = 1
```

Do not compare these native r/J values directly using SI scales 0.06429 m and 1200 kg/m³.

### Optional conditional SI representation

If an SI-coordinate audit is needed, transform **every raw-moment vector and every column of Jc** by the same affine pushforward before comparing derivatives. For this frozen P20 case:

```text
x_SI = s * (L * A_target * x_target + tip_reference)
s = 0.025 m/reference
L = 2.5716
A_target = I
A_SI = s * L * A_target = 0.06429 * I
t_SI = s * represented_tip_reference
density_ratio = 1200
```

The represented tip residual is retained, not rounded to zero. The M21 frame report records the corresponding translation:

- X: `-8.205519964092365e-20 m`
- Y: `0`
- Z: `1.0129829261402906e-18 m`

The conditional SI audit normalization is then:

```text
moment_coordinate_frame = P19_PROPOSED_SI_Z_UP
length_ref = 0.06429 m
density_ref = 1200 kg/m^3
```

M21 implements `transform_raw10_native_to_si`, `transform_jacobian_native_to_si` (column-wise output pushforward), and `audit_tangent_neighborhood_in_frame`. It rejects mismatched frame/normalization pairs. The coefficient vector c and tangent directions remain in their native coefficient coordinates; only the ten output moments and Jc rows are transformed.

The synthetic analytic-cap tests exercise both paths and the feature-branch veto. They are mathematical software tests, not Teapot samples.

**Important:** the 0.025 m/reference and 1200 kg/m³ remain unapproved physical proposals. Correctly transforming the current native r/J into a conditional SI representation does not validate the real object's scale, density, material, support or contact physics.

## 3. CI outcome and preserved scientific status

The final run #42463041196:

- 203 pytest cases passed and 7 parameterized subtests passed;
- direct W4 source binding: 10/10 source files checked;
- pinned Core source binding: 10/10 source files checked;
- native/SI frame contract CLI succeeded;
- live W2 change was detected and recorded as requiring independent review;
- W0 P30 physical audit still returned the expected `BLOCKED_PHYSICAL_CASE_NOT_OWNER_APPROVED`.

No new Cherchi call was made. Real Teapot tangent samples remain 0/12. No W0 physical approval, W2 Teacher approval, continuous smoothness certificate, Newton acceptance, training admission, strength certificate or printability certificate was created.

## 4. What W0 still needs to do

### A. Physical case (hard blocker)

1. Obtain authoritative Teapot CAD/dimensioned drawing, including body, shaft, actual tip/contact patch and bearing/support geometry; or explicitly redefine P19 as a new owner-designed Spinning Top rather than author CAD.
2. Obtain owner-approved measured dimensions and metres-per-reference-unit.
3. Obtain material identity/density and solid/hollow/shell/infill/porosity/fill/manufacturing specification.
4. Define the spin axis, shaft/bearing interface, support reactions, gravity, friction, contact boundary and load/torque/speed envelope.
5. Define D removal constraints, global minimum wall, load paths, material allowables, load cases, safety factor and strength/printability acceptance.
6. Define objective tolerances for mass, COM, full inertia and spin stability.

### B. Private evidence custody

Obtain the original `P27_FORMAL_M6_EVIDENCE.tar.gz` (including the original P27 lock) and `P30_UNEXECUTED_TANGENT_PLAN.json` in W0's review workspace. Recompute their raw SHA-256 locally; public receipts alone are corroboration, not a direct re-hash.

### C. W2 Teapot-specific review

W2 must issue its own review of the same Teapot's base feature branch, material/source/Boolean identity, ten moments and same-call Jc. The current W2 manifest's one native diagnostic is a Heart case; training samples remain zero. Heart/Noodles evidence cannot be relabelled as Teapot.

### D. Only after A–C

1. W0 sets a case-specific numerical noise/error budget; no arbitrary universal 1% or (10^{-8}) threshold.
2. W0 and W2 issue independent, source-bound diagnostic-only receipts.
3. W0 reviews the separately registered P30-B lock.
4. W4 runs at most 12 real Cherchi diagnostic points on the qualified host.
5. W0/W2 review the actual r/J samples and feature-branch identities. A finite set of samples is not a continuous smooth-neighborhood proof.
6. Only after a separate derivative-neighborhood argument and Newton terminal evidence can any optimization/training gate be reconsidered.

## 5. Next cross-window handoff

W4 must consume the M21 explicit frame contract in its own branch. W0 will not modify W4. The W4 handoff must ensure every P30-B sample receipt identifies `moment_coordinate_frame`, `normalization_L`, `normalization_R`, native density and transform provenance; it must never pair native r/J with SI normalization.

W0's P30-B physical decision remains **BLOCKED**. M21 improves evidence custody and mathematical coordinate correctness; it does not remove the missing real-world physical inputs.

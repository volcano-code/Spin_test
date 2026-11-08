# W0 P30-B Teapot physical-case review — BLOCKED

**Decision:** \`BLOCKED_PHYSICAL_CASE_NOT_OWNER_APPROVED\`  
**W0 branch / review-start HEAD:** \`research/neuralmoments-w0-contract-20261019\` / \`5bab2eb2616df306906a6887a273f68acfa49320\`  
**W4 branch HEAD observed:** \`aca53abf0d31329264fe1f028b2aff2175165ba3\`  
**Task:** [Issue #5](https://github.com/volcano-code/Spin_test/issues/5). The issue body and both comments were read.

No \`P30_TEAPOT_DIAGNOSTIC_AUTHORIZATION.json\` is created. No P30-B native sample was run. No W4, W2, main, or other-window branch was modified.

## 1. Frozen evidence identity

Directly fetched from the public W4 branch and independently SHA-256 re-hashed:

| File | Git blob | Recomputed SHA-256 | Result |
|---|---|---|---|
| \`P1/P20_native_request.json\` | \`f3bca7bef1f207cb5b857848c9588543fb7e5a9c\` | \`a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9\` | Match |
| \`P1/P19_material_case/manifest.json\` | \`65ab0ffd0d0b43b3b9153f1de44fc04bd0859e00\` | \`c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6\` | Match |
| \`M_native.obj\` | \`e2651b8a2efcc89fee3e69f9ebb78ddffb8f942e\` | \`0b59fd6f41079ab507af3e31673f94472b0d6f849df981b52c1ea667994ad704\` | Match |
| \`F_native.obj\` | \`180c3ade7c939008b90fa1aaabe82653047b2e6c\` | \`5c5db73792bd8d6566a954e6d0eef6d22e248a7ad2f8a7a8d8e6d4f2ad9d86a8\` | Match |
| \`D_native.obj\` | \`9820f3d73d15a4cdd0c504a0264f934aefd40df1\` | \`d64a3163c886cb06ade6f366e8ff5e475934816343a5be429b55c5832951b073\` | Match |
| \`shaft-reference.obj\` | \`9fe9f78257c7a90970095f6bb54c5148198a33d1\` | \`65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0\` | Match |

P27/P28/P30 frozen hashes were cross-checked against the public receipts and review documents:

- P27 formal manifest: \`3a9b6b21d1d1185e00d1ef25a1bfc625d4696f554c3ab4a7719f5d85ca109773\`.
- P27 precommitted lock: \`451d8b46cd047325b0b3e2d406f9e89dd0252cece677f5f310ca5abe3c8089a4\`.
- P30 private full plan: \`fc2d9a1b3c372513cdf3d6ba41e74812a12761e67f6b6fa82c0a66982351bacc\`.
- Base native c: \`57ac958304df37ebfd36bc1dddeb32c81a113ed5440f65d959f4b45f2a12e6ca\`.
- Same-call 100-entry Jc: \`26cf3b5dd53d45a4b80f14319b39d28fa9ef7b8d8be3a915189e90ba077a08a5\`.

**Re-hash limitation:** P28 reports 37/37 formal manifest files matched, 0 failed, and confirms the same-call J bytes. P27's exact lock is inside the private formal archive; the private P30 full plan is explicitly not uploaded to public GitHub. W0 therefore corroborates those two hashes from P27/P28/P30 receipts but cannot claim a fresh byte-for-byte re-hash of the unavailable private files. P28 is a cloud standalone replay, not the original P21 verifier: \`official_p21_replay_verify_executed=false\`, \`independent_native_set_predicates_reexecuted=false\`, \`independent_runtime_attestation=false\`, \`scientific_admission=false\`.

## 2. Physical case facts

P19 is explicitly \`P19_EXACT_SAVED_SOLID_AND_COMPLETE_ORIGINAL_SHAFT_PASS_NOT_ADMITTED\`; its case is \`P13_RECONSTRUCTED_REFERENCE_UNIFORM_SOLID_PROPOSAL\`, not an owner-approved Teapot CAD. \`original_author_CAD=false\`; physical parameters and printability are not approved.

### Scale, density and dimensions

- \`0.025 m/reference\` is proposed, not approved.
- \`1200 kg/m³\` is an assumed uniform solid, not a printed-material certificate; fill, shell, porosity and material are unspecified.
- P20 says \`native_length_scale_is_bbox_L_not_SI_0025=true\`. Its exact frame has \`length_original_per_normalized=2.5716\` reference units. Under the unapproved proposal this conditionally maps to \`2.5716 × 0.025 = 0.06429 m\`.
- Saved M bbox under that proposal is **64.29 × 40.00 × 42.75 mm**. These are saved mesh dimensions, not independently measured real-object dimensions or author CAD.

### Conditional mass, COM and full inertia

The following are saved-mesh diagnostics only under the proposed scale/density. Full symmetric inertia tensors about each region's own COM (kg·m²) are preserved in \`contracts/P30_TEAPOT_PHYSICAL_REVIEW_BLOCKED_20261108.json\`.

| Region | Mass (kg) | COM (m) |
|---|---:|---|
| M | 0.031118997336943656 | (0.000209100, 0.0000000329, 0.016317787) |
| F | 0.030623879229415785 | (0.000212481, 0.0000000334, 0.016310799) |
| D | 0.0004951181075278711 | (~0, ~0, 0.016750000) |
| S | 0.00034522876294318855 | (~0, ~0, 0.022256850) |

\`M = F + D\` holds for saved-mesh mass. **S is already contained in F; it must not be added a second time.** P19 exact saved-mesh checks say full original S is in F and separated from D. D is a closed saved surface and the exact M/F/D partition is consistent. These are geometric and arithmetic results, not strength or printability certification.

### Shaft, D, tip and support

- P19 uses a **9/8 radial shaft-envelope** and **7° XY rotation**; original shaft-reference bytes are preserved. This is a reconstruction/envelope operation, not proof that the result is the author's actual shaft CAD, bearing journal or tip.
- P19 reports the complete saved shaft contained in F and separated from D. The P19 registered shaft/design gap is 1/500 reference unit (conditionally 0.05 mm). A separate 1/32 reference-unit (conditionally 0.78125 mm) wall probe is explicitly local, not a global minimum-wall certificate.
- D's saved bounds are approximately 9.997 × 9.997 × 9.446 mm. No owner-specified load path, minimum global wall, material strength, connection constraints, FEM/experimental strength or safety factor is provided. D is geometrically partitioned, but legal deletion/structural adequacy is not approved.
- P20 requests tip \`(0,0,0)\`, axis \`+Z\`, and has \`support_points=[]\`. The exact represented-tip residual is nonzero but tiny: about \`4.0652e-17\` reference units, conditionally \`1.0163e-18 m\`. This is likely numerical frame residual, but no owner-approved physical tolerance exists. More importantly, there is no authentic tip contact patch, bearing, ground/support geometry, friction or reaction constraints. Axis plus nominal point does not define a physical spinning support problem.
- P12's 15 cm / 1240 kg/m³ / 0.25 kg historical diagnostic is a different case and is not mixed into this P19/P20 review.

## 3. P30-B tolerance decision

W0 \`tangent_neighborhood.py\` normalizes ten moments with \`[density_ref·L³, density_ref·L⁴ (3 first moments), density_ref·L⁵ (6 second moments)]\`, compares Richardson \`(4D(h/2)-D(h))/3\` with \`Jc·v\`, and separately records step-halving change. Every ±h and ±h/2 sample must carry the same feature-branch SHA as the base; a branch mismatch vetoes the numerical derivative. Even a numerical pass explicitly does not prove a continuous smooth neighborhood or training eligibility.

Conditional candidates from the unapproved proposal would be \`length_ref=0.06429 m\` (bbox L) and \`density_ref=1200 kg/m³\`. They are **not authorized**. W4's \`h=0.002 rad\` is a geodesic step on the 10-D unit native-coefficient sphere, not a rigid-body rotation; the receipt says it is not preapproved and 0 genuine tangent samples exist. No authentic base feature-branch SHA, measured numerical noise, geometry uncertainty, material uncertainty or owner-defined Jacobian error budget is available. Therefore no defensible numeric \`max_normalized_jacobian_error\` can be set, and none of \`length_ref\`, \`density_ref\`, \`h\`, or error budget is approved.

The proposed 12-point pattern (directions \`[0,1,2]\`, four samples ±h/±h/2 each) is a software plan only. Finite-difference agreement, sampled branch stability, continuous smooth-neighborhood proof and Newton terminal certification remain four distinct levels.

## 4. Decision and minimum unblocking inputs

**P30-B 12-point pilot: NOT APPROVED.** W0 physical approval=false; W2 teacher approval=false; continuous smoothness=false; Newton=false; training=false; physical/printability/strength validation=false. No authorization JSON is created.

Provide the following exact items for a fresh review:

1. Authoritative Teapot/spinning-top CAD assembly (STEP/Parasolid/native CAD) including body, real shaft, tip/contact and bearings; or an owner-signed dimensioned drawing with datums and SHA-256. Confirm the target object identity.
2. Owner-approved measured dimensions/metres-per-reference-unit, material identity and density certificate; specify solid/hollow/shell/infill/porosity/fill and manufacturing process. Explicitly approve or replace 0.025 m/reference and 1200 kg/m³.
3. Actual tip radius/shape/contact patch, support/bearing/ground geometry, spin axis, gravity, friction, support reactions and boundary conditions.
4. Authoritative shaft CAD/material, bearing interfaces and load/torque/spin-speed envelope; confirm whether 9/8 + 7° is intended physical design or merely reconstruction.
5. D removal requirements, global minimum wall, connections/load-bearing zones, material modulus/yield/allowables, load cases, safety factor and a validated strength/printability acceptance method.
6. Owner acceptance tolerances for mass, COM, full inertia, spin duration/precession/stability and an identical-condition before/after simulation protocol.
7. Private evidence bytes for direct W0 re-hash: \`P27_FORMAL_M6_EVIDENCE.tar.gz\` (containing the P27 manifest and preregistered lock) and \`P30_UNEXECUTED_TANGENT_PLAN.json\` (expected SHA-256 \`fc2d9a1b3c372513cdf3d6ba41e74812a12761e67f6b6fa82c0a66982351bacc\`).

After physical inputs, W0 can derive a case-specific error budget. W2 must separately approve its authentic feature-branch/teacher side. Only after both tracked owner reviews and a fresh preregistered lock may W4 run the 12 native diagnostic points.

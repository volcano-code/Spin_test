# W4 P32-B — MuJoCo scenario contract and readiness report
Date: 2026-11-09
Branch: research/neuralmoments-w4-teapot-p1-20261019

## Work completed in this milestone
Created `P32B_MUJOCO_SCENARIO_CONTRACT_20261109.json` and fetched it back from GitHub for deterministic structural checks. Eight checks passed:
1. schema identity;
2. case B identity and no historical CAD claim;
3. provisional SI mapping remains explicitly unapproved;
4. candidate mass is positive;
5. candidate inertia has 3x3 shape;
6. no tip contact radius was invented;
7. no spin speed was invented;
8. every physical/scientific admission gate remains false.

## Conditional rigid-body candidate
The pinned P20 report's exact-affine algebraic replay provides the following F-only candidate under the user's provisional 0.025 m/reference and 1200 kg/m^3 mapping:
- mass: 0.030623879229415785 kg;
- COM: [0.00021248054445209633, 3.3427826229945706e-8, 0.01631079864337299] m;
- inertia about COM (kg m^2):
  `[[3.880413266512508e-6, -2.558349495841274e-11, -5.4331174909324105e-9], [-2.558349495841274e-11, 4.393412127153277e-6, -2.228648075359519e-12], [-5.4331174909324105e-9, -2.228648075359519e-12, 5.452774958403695e-6]]`.
All displayed values are preserved exactly from the P20 report's floating-point projection. They are candidate algebraic values, not an observed native Cherchi result or measured printed-part inertia. They are not sufficient to launch a scientifically valid physical simulation without owner-approved geometry/contact/material inputs.

## MuJoCo protocol now specified
- Z-up world and gravity -9.80665 m/s² as a scene convention.
- Separate visual mesh from collision/contact proxy; do not assume the concave teapot visual mesh is a valid contact primitive.
- Two contact alternatives remain open: ideal point-tip diagnostic, or a redesigned finite-radius/flat pad requiring new mesh hashes and a new preregistration.
- No contact radius, friction, contact stiffness/damping, elastic modulus, yield strength, print process or spin speed is invented.
- Baseline and optimized cases must use paired initial pose, angular velocity, contact model, integrator, timestep and solver tolerances.
- Required outputs include tilt, fall time, spin decay, angular momentum, contact impulses/forces, COM height, energy drift, solver residual and wall-clock.
- Required sensitivity includes timestep refinement, contact/friction sweeps, initial-spin sweep and small tilt perturbations.

## Why a real MuJoCo run is not launched yet
The P20 source has `support_points=[]`; the shaft terminates at a point apex. The actual contact pad/support, contact parameters and material structural properties are undefined. P20's physical replay is an exact affine algebraic replay, not a native core execution or a validated physical solid. W0/W2 owner receipts are still missing. Running MuJoCo with arbitrary values now would produce an illustrative animation, not a valid physical result, so no simulation is claimed.

## Gap to the original W4 target
Original target: a new Utah-Teapot-inspired spinning top; Cherchi exact rational material/moment pipeline; valid F/D/S partition; three objective Spin-It optimization (inertia, lower COM, mass); and MuJoCo before/after physical comparison.

| Workstream | Current evidence | Remaining blocker |
|---|---|---|
| Teapot design identity | Case B frozen in P31 decision | Physical design dimensions/material still provisional |
| Mesh topology | Closed edge-incidence and orientation screen; P32 custom SAT screen found zero nonincident self hits | Independent robust kernel certificate still required |
| F/D relationship | Exact triangle boundary correspondence and signed-volume residual ~3.34e-17 | Robust solid set equality/containment proof |
| Shaft S | 3,584 sample classification and SAT contacts localized to apex/top cap | Robust S-in-F and contact/fusion proof; no-double-counting owner sign-off |
| Physical dimensions/mass | Conditional bbox 64.29x40.00x42.75 mm; F mass 30.624 g | Actual material, print settings, uncertainty, loads and strength |
| Support/contact | Tip and candidate alternatives documented | W0 must freeze point vs finite pad, support plane and friction/contact |
| Cherchi native teacher | Software gate and 37 regression tests previously passed | W0/W2 tracked receipts, independent lock, local native 12-point run |
| Derivative validity | P30B journal/frame/branch machinery prepared | Real Jc, same-call provenance, neighborhood checks, independent error budget |
| Three-objective optimization | Objective plan exists in broader Spin-It pipeline | No Teapot optimization admitted or run |
| MuJoCo | Paired scenario and metric contract prepared | Approved collision/contact, material and load case; run baseline and optimized cases |
| Final validation | No final evidence | Convergence, sensitivity, structural/printability and reproducibility package |

## Estimated completion, carefully scoped
- W4 software/contract preparation: substantial progress; P20/P30B/M22 and P31/P32 records exist.
- Physical entity validation: partial only; no robust solid certificate or owner approval.
- Cherchi scientific evidence: not admitted; genuine P30B samples 0/12.
- Optimization: 0 Teapot optimization runs admitted.
- MuJoCo paired physical validation: 0 baseline/optimized comparison runs.
- End-to-end original W4 target: **not complete**. The project is past initial design/contract setup, but the decisive native, optimization and physical validation stages remain ahead. Do not present a single percentage as if all workstreams were equally weighted.

## Next steps
1. W0 independently certifies M/F/D/S geometry, shaft semantics, contact geometry, material and load envelope; issue a diagnostic-only receipt if justified.
2. W2 independently certifies the same Teapot feature branch and Cherchi source/Boolean/integration/derivative provenance; issue its separate receipt.
3. W4 verifies both receipts and obtains an independently registered P30B lock.
4. Run local Cherchi 12-point diagnostic only after the gates pass.
5. After derivative/branch validation, request separate optimization admission and execute the three objectives with strong independent checks.
6. Run paired MuJoCo baseline/optimized experiments with timestep/contact sensitivity and publish video plus raw metrics.

# W4 P13 | Reference spindle and shaft-excluded Cherchi design domain

**Research status:** Reconstructed-2014-Teapot dimensional shaft proposal; W0 scientific approval NOT granted. This is distinct from the P12 15-cm/PLA proposal and prior 0.25-kg MuJoCo illustrations.

## Why this is needed

P11 successfully proved native Cherchi subtraction and ten moments, but its trial carveable sphere intersects the fixed center spindle. It is invalid to claim the trial D is safe to carve while the physical contact shaft is fixed.

P13 independently rereads actual P9/P11 native Cherchi M/F/D, reusing frozen parameters already in the reconstructed Teapot source:

- experiments/teapot_spin2014/teapot.py, Git blob a80974d062c7fef2fe1852df677477e82a5adb54: rounded shaft profile
- experiments/teapot_spin2014/prepare.py, Git blob fde050a83b2e39b9a92dab5e46616e1f37a9f4ff: Y-up to Z-up, scale 0.4, shift z+0.15
- 0.025 m per reconstructed-model unit and uniform solid density 1200 kg/m³ are PRIOR RECONSTRUCTION DEFAULTS, not original paper parameters or W0-approved truth.

Pinned original native M/F/D and P11 report SHA-256:

- M: 154cdfc9ec94b6885a95e596c36ac1382dd2d36ed99e19d0b36c2b9de80b6df4
- F: 22593c5ab3b5f6ee786f2d17ce15f3beae16fcb09589dce2314d1615b3f115ba
- D: 4cc61b54939fe9c9acdfe9e956af24f2a411d6016acd83fd32d46722749a99b9
- P11 native audit: 798ee3092487a4797a427e9a36dad11791f21835b897235c25f4b6518aee404f

## Actual P13 preflight results from real saved material

| Diagnostic | Measured |
|---|---:|
| M mass (before shaft union) | 0.031017469 kg |
| shaft mass (standalone, before union) | 0.000345229 kg |
| P11 trial D mass (before shaft exclusion) | 0.000607057 kg |
| round-tip lowest height | 0 m |
| shaft top height | 0.04275 m |
| teapot body bottom height | 0.00375 m |
| M/F/D reconstructed-frame raw-ten maximum error | 1.56e-16 |

DO NOT ADD the standalone M and shaft masses to claim a physical total: they overlap and must undergo native union. The P12 15cm/1240 kg/m³ source corresponds to DIFFERENT scaling and cannot be mixed with this candidate.

The deterministic witness (x,y,z)=(0.03,0,0.67) lies inside BOTH the reference shaft and P11 trial D; independent signed-solid-angle windings were ~+1.0 for both. Thus the old carveable D HAS POSITIVE-VOLUME INTERSECTION with the proposed fixed rod. Its rejection is a scientific gate, not a cosmetic warning.

Required true material program:

O = native_CHERCHI_UNION(M, shaft)
D_safe = native_CHERCHI_SUBTRACTION(D, shaft)
F_safe = native_CHERCHI_SUBTRACTION(O, D_safe)
independently require r(O) = r(F_safe) + r(D_safe) for ALL 10 ordinary raw moments.

## Real deliverables

p13_reconstructed_shaft_domain.py checks source SHA and P11 native provenance, generates four CLOSED reference-frame M/F/D/shaft OBJ candidates and p13-preflight.json, verifies proper affine ten moments and translated COM, demonstrates D/shaft positive overlap, and explicitly denies W0/Faster/MuJoCo claims. The optional native mode invokes the three original pinned Cherchi CLI Booleans, never CGAL/OpenSCAD fallback, independently tests surface legality and ten moments, and stores the complete failure receipt if geometry is rejected.

test_p13_reconstructed_shaft_domain.py passed 11 actual local tests including source-tamper, fake W0 approval, proper frame and cross moments, spindle tip, file identities, and D/shaft overlap. The cloud job uses the immutable actual P11 success artifact from Run 39403411538. The native work remains serial in the user-authorized W4 Actions workflow and may fail honestly.

Scientific denial flags always remain FALSE:
W0_physical_case_admitted; W0_spindle_approved; W0_fixed_F_design_D_admitted; printability_certified; faster_optimization_performed; real_optimized_MuJoCo_validated.

A pointlike tip is NOT a printability certificate, and this is NOT a Spin-It Faster optimized object. W0 must approve the final shaft, tip, shell, removable domain, metric units, density and optimized objectives. Only then may P14 start genuine three-goal optimization and same-conditions MuJoCo before/after testing.

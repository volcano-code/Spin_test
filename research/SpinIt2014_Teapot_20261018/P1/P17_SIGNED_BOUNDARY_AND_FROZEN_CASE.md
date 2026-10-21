# W4 P17 — corrected signed boundary identity and frozen physical case

## Outcome

P17 fixes the interpretation of P16's nonzero triangle-counter residual. All
three real P14 material partitions, both before and after P15 micro-welding,
satisfy an **exact saved-binary64 oriented triangle-chain identity**. No mesh
vertices or faces are changed by P17. The preselected `rotate_1p5` candidate is
now a durable, self-contained material packet in `P17_material_case/`, with
source receipts, numerical geometry checks, exact moments and one physical
case proposal. It remains **not admitted by W0/W2 and not optimized**.

The source branch parent is `7b22a3f910970951d96c1278d10a3d2945d518d2`.
Authentic source artifacts are P14 run
[39462578208](https://github.com/volcano-code/Spin_test/actions/runs/39462578208)
and P15 run
[39555122736](https://github.com/volcano-code/Spin_test/actions/runs/39555122736).
Pinned Cherchi upstream remains `7bd6c2697695f555f9a15d7e154e084d841316f0`.

## 1. A representation issue, not a material boundary gap

P16's `oriented_counter` identifies cyclic permutations but treats an opposite
orientation as a different positive key. That is an orientation-preserving
triangle multiset, rather than the complete oriented simplex algebra:

`[a,b,c] = [b,c,a] = [c,a,b] = -[a,c,b]`.

An internal cavity contributes reversed D triangles to F. In the legacy
`M - F - D` comparison these produce two uncancelled orientation keys per
design face. P17 retains signed integer multiplicities when canonicalizing all
six permutations; reversing a face multiplies its coefficient by -1.

| Actual source case | native saved signed residual | P15 saved signed residual | reproduced legacy residual | reverse pairs |
|---|---:|---:|---:|---:|
| rotate_1p5 | 0 | 0 | 1280 | 640 |
| translate_y_008 | 0 | 0 | 1248 | 624 |
| translate_xy_012_m008 | 0 | 0 | 1248 | 624 |

This proves `boundary(M_saved) = boundary(F_saved) + boundary(D_saved)`
exactly at the saved binary64 coordinates, face by face. No coplanar tolerance,
common refinement, fresh Boolean, remeshing or new retained-material assembly
is needed. Independent vertex-sorting/permutation-parity replay reproduced all
six zero residuals using a different implementation of the orientation rule.

Historical P16 files are retained unchanged. Its separate exact integration
result **still holds**: the native outer and the repaired outer differ by
`+4.424138952620733e-21` reference-volume units. P17 does not claim that the
micro-weld preserves the original implicit Cherchi solid exactly.

## 2. A concrete material packet, with unchanged source bytes

The selected case follows P15's already declared `rotate_1p5`; it was not chosen
by an optimization objective. Packet materials are:

| Material | Source | SHA-256 |
|---|---|---|
| M, repaired whole body including spindle | P15 repaired outer | `4c2e4d480d1041f4817128a8b4b61675d80a699e448e7a5a253311c1805a3aa2` |
| F, retained trial material | P15 repaired F | `47c08ee597d5666069416985e0dc8900d204481c590b73596f90daccd2b068d1` |
| D, experimental carveable region | actual P14 Cherchi D-minus-shaft | `1d4a0673e9297d95adfb5722158ba1d859a83099046d01116a2b363cb3cb386b` |

The packet also retains original native outer/F, D hypothesis, spindle,
same-call F/D execution receipts and the immutable P14/P15 reports. Input
reports, negative historical outcomes, source/output identities and native
operand relationships are authenticated before any candidate is copied.

Saving this selected material in Git removes the selected-case verifier's
dependency on expiring Actions archives. Rebuilding *all six* historical
certificates still needs the original full archives. The packet verifier
recomputes the selected material; it authenticates the all-six report against
its fixed independently reproduced SHA and does not pretend to rerun the
other two candidate materials when their OBJ files are absent.

The independent numerical preflight adds vertex-link circularity to closed
edge incidence, checks every cross M/D AABB pair without excluding shared
indices, tests all 320 D vertices inside M and confirms separate shaft-core
and off-axis removable witnesses. M, F and D have 1, 2 and 1 closed boundary
components respectively; F's second component is the interior cavity surface.
The numerical cavity-to-exterior sphere-distance bound is approximately
`0.008077094884 m` under this proposal.

These remain finite-floating checks. Incident triangle contacts and exact
embedded-solid legality are not fully certified. The clearance bound concerns
this cavity and exterior; it is not a whole-object wall-strength or printability
certificate. Correct boundary algebra alone is not used to set those flags.

## 3. One physical proposal for all three materials

P17 freezes the existing P13 reconstructed-reference assumptions:

- length scale `0.025 m/reference unit`;
- assumed uniform solid density `1200 kg/m^3`;
- coordinates already Z-up, spin axis `+Z`, tip `(0,0,0)`;
- whole-object height `42.75 mm` including the spindle.

These are explicit reconstruction assumptions, not original-author CAD or
material measurements and not W0 approval. The earlier 15-cm/1240-kg/m^3 and
250-g diagnostic configurations are not mixed into this case.

| Saved material | Mass (g) | COM z (mm) | central Izz (kg m^2) |
|---|---:|---:|---:|
| M | 31.0976346832 | 16.3074010823 | 5.45849862223e-6 |
| F | 30.5719754929 | 16.2997909693 | 5.45263237550e-6 |
| D | 0.525659190356 | 16.7500000000 | 5.84283614452e-9 |

All ten ordinary, undoubled moments are integrated from the reread saved
meshes as exact rational values. SI conversion uses rho*s^3, rho*s^4 and
rho*s^5. Full origin/COM inertia tensors and principal moments are included.
No inertia tensor is edited, and overlapping body/shaft masses are not added.

Removing all trial D would remove 1.690351037% of this material and lower its
COM by only 0.007610113 mm. These are trial-partition properties, **not a
Faster optimization or measured improvement in spin stability**.

## 4. Reproduction and review

From a checkout of this W4 branch:

```bash
python -m pip install numpy==2.3.5 scipy==1.17.0 trimesh==4.12.2 networkx==3.7
P1=research/SpinIt2014_Teapot_20261018/P1
python "$P1/p17_material_candidate.py" verify --packet "$P1/P17_material_case"
```

The selected packet verification is self-contained. To regenerate the packet
and execute the full actual-source tests, expand the two authentic source
Actions archives and set:

```bash
export W4_P17_P14_ROOT=/path/to/p14/research/SpinIt2014_Teapot_20261018/P1
export W4_P17_P15_ROOT=/path/to/p15
python -m unittest discover -v -s "$P1" -p 'test_p17*.py'
python "$P1/p17_material_candidate.py" build \
  --p14-root "$W4_P17_P14_ROOT" --p15-root "$W4_P17_P15_ROOT" \
  --out /path/to/a/new/p17-material-case
```

Build refuses an existing output directory. Verification checks a complete
relative-file inventory, source-derived hashes, same-call native receipts,
strict boolean flags and all regenerated selected-case reports. Parent-path
symlinks, mismatched candidates, forged approval, report/CSV changes and
updated self-reported hashes do not bypass the frozen source checks.
Only the LAPACK-derived principal-inertia projections permit a 1e-12 relative
replay tolerance; exact fraction fields and the other physical fields remain
strict. Numerical geometry reports allow bounded floating replay variation.

Actual local test execution is recorded in `P17_LOCAL_TEST_RECEIPT.txt`.
The added independent `p17-signed-boundary-and-material-case` Actions job
rebuilds from the original archives, runs all P17 tests with no skips and
verifies both the committed packet and the freshly rebuilt packet. Its actual
remote status must be read separately; this document does not make an
unexecuted CI claim. Existing failing P13/P14 jobs remain unchanged.

## 5. Exact handoff boundary and next acceptance

P17 can hand off the concrete candidate and its stronger saved-boundary
certificate to W0/W2. It cannot approve those other windows' contracts.

The next acceptance must settle:

1. Acceptance of this explicitly repaired, source-deviating baseline and its
   repair budget, or replacement by a separately certified native implicit
   construction. No strict identity to the pre-weld source is claimed.
2. Full embedded-solid validation, protected spindle/outer-shell geometry and
   an authorized removable design domain, including the appropriate wall and
   contact constraints.
3. W0's approval of one metric/density/axis/tip case, plus the corresponding
   W2 exact material/teacher interface requirements.
4. Only after those prerequisites: actual Faster optimization of the three
   registered objectives and same-condition MuJoCo videos from the saved
   before/after optimized materials.

P17 performed zero new native Boolean calls, zero optimization runs and zero
new MuJoCo runs. It delivered an exact boundary-algebra correction and a
reusable, independently checked material/physical proposal, while preserving
all original scientific limitations.

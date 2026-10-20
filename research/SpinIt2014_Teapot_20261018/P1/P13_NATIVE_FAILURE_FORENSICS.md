# W4 P13 negative native material geometry — independent forensic milestone

Source: real [GitHub Actions run 39446111126](https://github.com/volcano-code/Spin_test/actions/runs/39446111126), failed Cherchi stage. The same run's MuJoCo and P12 physical preflight jobs succeeded independently.

Native pinned Cherchi reference `7bd6c2697695f555f9a15d7e154e084d841316f0` called `union` on source M + shaft, then `subtraction` on trial design D - shaft. Actual saved artifacts were downloaded under GitHub artifact ID `12276067191` and independently analyzed using NumPy/Trimesh (no CGAL solver and no repair).

| Saved real native output | indexed vertices | triangles | non-two incidence edges | small triangles (area <= 1e-14) | watertight | valid volume |
|---|---:|---:|---:|---:|---|---|
| `p13-outer-cherchi-union.obj` | 3793 | 7586 | 0 | 28 | yes | yes |
| `p13-D-shaft-excluded.obj` | 324 | 806 | **162 (all incidence 3)** | **8** | **no** | **no** |

The P13 subtraction **process returned 0**, but its output is *not a legal removable material*. The saved signed-tetrahedral surface integral 0.02813245057578 cannot be treated as a true physical volume because the boundary is nonmanifold. Original D is watertight (162 vertices, 320 faces); the shaft is watertight (258 vertices, 512 faces). Their overlap is already independently confirmed. The problem is the native Boolean output near the shaft/domain boundary, not missing W0 approval alone.

New `p13_native_failure_forensics.py` independently computes exact indexed edge-incidence multiplicities, degenerate triangles, witness coordinates, mass-sign diagnostics and provenance, writing a structured FAIL report. It never performs repairs or renames failures as successes. New negative-regression suite checks a valid tetrahedron, a native-return-0 nonmanifold sample, SHA tampering and unsuccessful native exit. Optional fifth regression audits the actual saved P13 output when staged.

The W4 authorized Actions workflow now runs the forensic step `if: always()` after the P13 native attempt so that genuine failed OBJ/JSON is retained even when upstream subtraction fails. W4 does not modify `main`, any other research window, original P0/P1, previously archived run artifacts, or the current scientific admission flags.

**Next scientific investigation:** determine whether the shaft profile and D-sphere intersection creates coincident/near-degenerate features, and test narrow, source-tracked geometric clearance variants using genuine Cherchi alone. Any successful variant must be checked for geometric deviation, true material additivity and W0 tip/shell authority before proceeding to Faster optimization. This milestone does not claim a new valid P13 F/D or any optimization result.

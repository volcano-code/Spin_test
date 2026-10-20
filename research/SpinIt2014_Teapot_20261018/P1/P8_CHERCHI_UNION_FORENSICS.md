# W4 P8 — Cherchi-only real native forensics, no CGAL repair

## Confirmed P7 failure from original GitHub Actions

Source frozen P0 SHA-256: `1b5396fedd74b577e32cef41146582c2f2e1a050d5b4915193c0ac1ad4187ed4`.
Source frozen P1 SHA-256: `3b13a006976093f86b733cd1a00c57d70a66e2fc8dca1c4a157bb18f93a7db47`.
Original Cherchi reference revision: `7bd6c2697695f555f9a15d7e154e084d841316f0`. P7 native executable SHA-256: `ad8f4e012fff474f96c059532ac32290fbf4a969c07d5462e08879466c6a66fb`.

P7 actual GitHub Actions [run 39280601698](https://github.com/volcano-code/Spin_test/actions/runs/39280601698) ended FAILURE. The original C++ Cherchi reference executable compiled and an actual 3-way `UNION` returned process code **0**, wall approximately 0.0355 s. The subsequent Python check threw `ModuleNotFoundError: No module named 'networkx'`. This is a missing audit dependency, not proof that Cherchi geometry is acceptable.

Downloaded the original native artifact **12199484757**, extracted `cherchi-variadic-union-p7.obj` (SHA-256 `e4ba6b8a5cfc4bb49259befaece9b3e1914ac5b3d67808b651c413343527dcb2`) and independently analyzed *the actual original file* using NumPy/Trimesh and no mesh repair:

| Property | Actual P7 Cherchi output |
|---|---:|
| indexed vertices | 3,344 |
| indexed triangles | 6,754 |
| exact edge incidence = 2 | 10,029 |
| edge incidence = 3 | **68** |
| connected components by input indices | **3** |
| winding consistency | true |
| watertight | **false** |
| Trimesh `is_volume` | **false** |
| naive signed surface tetrahedron integral | 27.013292438061995 |

Triply incident edge coordinates are concentrated at x approx 1.8973..1.9581, y approx 0.6661..1.4417, z approx -0.4885..0.4885, close to spout/body intersection. Thus the 3-way result is **not** admissible as the legal Teapot original material. Do not use its mass integral as physical volume. Previous CGAL P2 is an independent *comparison only*, not input or fallback to P8.

## P8 action

`p8_cherchi_union_forensics.py` executes the pinned *real native Cherchi* CLI in isolated serial calls:

- all-three `body+spout+handle`
- `body+handle`
- `body+spout`
- `spout+handle`
- reversed-three order
- sequential `(body+handle)+spout`, or `(body+spout)+handle`, **only when first result is independently admissible**.

For every file it records original source SHA, native return code, candidate OBJ SHA, incidence histogram, bad-edge witnesses, oriented watertight/index connectivity, vertex-fan issues, and (only after topology passes) nonincident floating SAT triangle contact checks. To accept a whole-body candidate it also requires a physically necessary union-volume range `max(V_i) <= V_union <= sum(V_i)` within 1e-6 (original P1 components alone are individually closed and positive), plus a separate ten-raw-moment comparison using Trimesh mass properties. Every validation explicitly excludes exact rational CAD proof, W0 physical F/D, W2 teacher, true optimization and MuJoCo-before/after validation.

`test_p8_cherchi_union_forensics.py` includes analytic tetrahedron, three-face incidence corruption, open-boundary rejection, independent connected-components accounting, and a fake native executable that returns 0 but produces no OBJ. The optional actual P7 archived OBJ regression only executes when the matching archive path is supplied; absence is recorded as skip, not PASS. The previous P7 test remains unmodified; P8 augments the original CI with `networkx>=3,<4`, logs the historical-style 3-input P7 result even on failure, then runs the above independent pairwise/order study.

Workflow: only `.github/workflows/w4-teapot-mujoco.yml` on W4 branch may change. No main/other W windows, source P0/P1 or historical run artifacts are altered. Native trials are serial with <=90-second command cap and <=2 native compile workers; on failure all archived OBJ/JSON/stdout evidence is uploaded and the step fails. **No green geometry claim without a real passing P8 output.**

## Next decision

If an ordering produces a verified single closed Cherchi union, use that output as a **numerical initial geometry candidate**, then independently recover/verify exact rational boundary and construct a W0-approved, non-overlapping fixed F/removable D material partition. If no ordering passes, isolate the spout intersection feature; do not repair by swapping to CGAL while calling it Cherchi.

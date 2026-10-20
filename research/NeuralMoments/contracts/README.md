# MomentContractV1 — W0 mathematical interface

Frozen source: `0bcc187b3005478baa586a6d6f450e73811ca342`.
Only W0's `research/NeuralMoments/contracts/` and
`research/ParallelLaunch/` are writable by this window.

## Source inspection and exact native meanings

- `src/spin/QuadricCoefficients.cpp` (frozen blob
  `ae831afe9191f67fb2659f112d1b85a8e2b61581`):
  `c=[a,bx,by,bz,Axx,Ayy,Azz,Ayz,Axz,Axy]`,
  `beta(x)=a+b·x+x^T A x`. The final three terms in the
  *polynomial* are `2*Ayz*yz+2*Axz*xz+2*Axy*xy`;
  the solver's native c stores matrix entries, not doubled monomial
  coefficients. The same blob is on frozen source and W0 branch.
- `python/make_it_stand/verification/spin_common.py` (blob
  `56c908c138c24fd5b90444bfc508904dead71c61`):
  `r=[M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY]`.
  All cross-moment products are ordinary, *not doubled*.
- `python/make_it_stand/verification/faster_material.py` (blob
  `a3c56a395e98e5c19d5924d1568b4e800e94b4d9`):
  independently integrated design material moments and an immutable
  prepared fixed moment contribution enter the external-moment bridge;
  ambient `moment_jacobian` is `dr_variable/dc_native`, while
  supported tangent mode provides a 10×k directional Jacobian together
  with the native 10×k basis. Do not fabricate ambient columns.

Set `B=diag(1,1,1,1,1,1,1,2,2,2)`; monomial coefficient vector
`q=B c`. For smooth full-ambient continuous retained-halfspace
moment maps only, `Jq=Jc B^-1` may be a symmetric boundary Gram
matrix. `Jc` **must not** be checked for symmetry directly. Tangent,
discrete, contact, topology-changing or undefined derivatives **do not**
meet the full smooth Hessian hypothesis without additional proof.

Unit-norm `c` is part of native serialization, and the saved normalized
vector's bit pattern must not be renormalized. Multiplication by a
strictly positive scalar preserves the represented signed halfspace;
negating c exchanges positive and negative halves and **is not an
allowed projective identification**. Retained side is explicit in
serialized contracts.

## Geometry, frames, and physical moments

A contract binds independent original/F/D geometry SHA-256 identities,
coordinate frame, material density, positive scale, and fixed-moment
cache. `r_total(c)=r_F+r_D(c)` and `J_total=J_D`;
no fixed F recomputation per c and no double addition.

For `x'=Ax+t` and density ratio `rho'/rho`, define
`w=abs(det A)*(rho'/rho)`, with original mass M, first moment L and
symmetric ordinary second moment Q:

- `M'=w M`
- `L'=w(AL+M t)`
- `Q'=w[AQA^T+(AL)t^T+t(AL)^T+M tt^T]`

These are raw mass moments, **not** central covariance or inertia
moments. Original-frame normalizations use `rho_ref*L_ref^3`,
`rho_ref*L_ref^4`, `rho_ref*L_ref^5` for M/L/Q errors.
**No universal 1% error threshold** is defined. Schema validation,
analytic P0 samples or a network prediction do **not** prove valid
geometry, correct Boolean material, derivatives or solver convergence.

## Testing and evidence

```bash
python -m pytest -q research/NeuralMoments/contracts/test_contract_v1.py
```

The committed `test_contract_v1.py` checks the native cross-term
factor 2, C++-equivalent polynomial formula, projective sign,
box quadrature, rotated ellipsoid, density and normalized scale,
quadric pullback, analytic P0 sphere-cap quadrature, analytic Jacobian
finite difference, and conditional `Jc B^-1` symmetry.

W0's isolated extended local working suite returned **15 passed**
with an independently compiled C++ formula sentinel; this is
not a claim that the exact committed GitHub test suite was run, nor
that native production Eigen/Cherchi/CAD code was compiled.
Actual W2 sealed real-mesh `r,J`, geometry and source hashes,
failure states and Newton terminal checks are still required.

## M2 semantic gate and W2 pre-release handoff

Run the full W0 local-only suite with:

```bash
python research/NeuralMoments/contracts/run_contract_smoke.py
# or: python -m pytest -q research/NeuralMoments/contracts
```

`validate_contract_v1.validate_record` strictly checks frozen SHA identities,
native unit coefficient c, explicit positive-only projective equivalence,
density/frame, the ten undoubled moment coordinates, one-time fixed F addition,
finite Jacobian shape, and native tangent basis orthonormality/orthogonality.
It rejects ambiguous derivative flags and does **not** assert that Jc itself
is symmetric. The JSON Schema is the structural interchange document;
use the semantic validator as an additional gate, not as a substitute for
independent material certification.

`w2_teacher_gate.inspect_w2_label` reads W2's
`w2-cherchi-teacher-v1-pre-w0` sealed-envelope semantics *without changing
or importing W2 source*. W2's legacy field named `q` contains the native
matrix-entry coefficient vector, equal to W0's **c**, **not** W0's doubled
monomial `q=Bc`. The bridge binds the expected native c, source/module
identities and frozen geometry hash externally, recomputes W2 envelope hashes,
separates cached r_F and variable r_D, and exposes only **candidate** Jc/Jq.
No SHA, boolean status or locally asserted `native_cherchi=True` proves
correct original CAD/Boolean geometry; training admission always returns
false until independent native re-evaluation and derivative-neighborhood proof.

On 2026-10-19 the tested local mirror with Git blob SHAs identical to the
published Python source achieved **57 passed**. GitHub combined statuses
and PR-triggered workflow listings for the runner commit were empty: **there
is no claimed green CI**, and no production Eigen/Cherchi solver was run.
See `research/ParallelLaunch/W0_M2_EVIDENCE_20261019.md`.

## M3 source-compiled quadric and exact signed-shell P0

The executable probe `native_quadric_probe.cpp` is linked against the **unmodified actual frozen production** `src/spin/QuadricCoefficients.cpp` and exact header. `test_native_quadric_cpp.py` computes their Git blob SHA-1 before compiling, and passes the repository's actual `include/` path plus a real Eigen header directory to one g++ process. The unrelated slicer hash function is stubbed **for linking only**; no production hash claims are made. If Eigen is not available, that pytest is explicitly **SKIPPED**, not passed.

`exact_box_material_probe.py` independently uses signed tetrahedra over two exact-rational watertight boxes. An inward-oriented inner boundary defines the fixed shell F and its independent inner D, with different physical densities; ten ordinary raw moments are compared to *independent separable rational monomial integrals*. A transformed mesh is reintegrated to check rotation, scale, shear, reflection/winding and translation. The integrator's elementary edge checks are **not** a certificate of arbitrary Boolean nesting, embedding, geometry or Cherchi source identity.

```bash
python -m pytest -q research/NeuralMoments/contracts/test_native_quadric_cpp.py research/NeuralMoments/contracts/test_exact_box_material_probe.py
# Full W0 suite (old 57 + new cases):
python research/NeuralMoments/contracts/run_contract_smoke.py
```

Measured in the isolated 2026-10-19 environment: **9 new tests passed in 11.85s**, native C++ value/gradient/matrix maximal error `2.22e-16`, pullback `6.66e-16`. Prior M2 57 tests were not rerun in this isolated mirror, so an aggregate 66-test PASS is **not** claimed. W2 teacher manifest still advertises 0 native teacher samples; only 5.8GiB RAM and no Cherchi native module are available here. See `research/ParallelLaunch/W0_M3_EVIDENCE_20261019.md` for exact limitations.


## M4 live native teacher replay and W2 handoff

W0 `native_teacher_replay.py` integrates ten undoubled raw moments with exact rational signed tetrahedra, confirms indexed boundary topology, physical/target rational coordinate maps and geometry/source SHA bindings, and checks fixed+design accounting against a same-call Cherchi material attachment. All arithmetic-only results deliberately return `training_admissible=False`; no geometric embedding or smooth derivative is inferred from a hash or local mock.

When an authorized native runtime is present, `audit_live_native_once(evaluator,problem,c,pins)` permits **only** the authentic frozen `InProcessCherchiEvaluator` and a locked `SpinArtifactProblem`, with externally pinned six SHA identities. It obtains `evaluator.material(c)` from that single source+Boolean call, compares independent fixed moments, native `MeshSnapshot.from_rationals` physical region and exact design subset, then records pointwise Jacobian and native stage timings. Training still requires an independent derivative neighborhood, terminal Newton and final full-material seal.

Run offline: `python -m pytest -q research/NeuralMoments/contracts/test_native_teacher_replay.py research/NeuralMoments/contracts/test_live_native_teacher_cli.py`. Native CLI details: `research/NeuralMoments/contracts/M4_NATIVE_HANDOFF.md`. Local result `43 passed in 0.07s`; real native CLI status `BLOCKED_INSUFFICIENT_PHYSICAL_RAM`, not a green native proof. See `contract_smoke_m4.json` and `research/ParallelLaunch/W0_M4_EVIDENCE_20261019.md`.


## M5 independently pinned W2 reference, native bridge and branch diagnostic

The exact read-only `w2_reference_snapshot.py` matches the active W2 `independent_reference.py` Git blob `d734398292e1fdaf839db3413c537de2474df3e1` and SHA256 `3238fb14d4cbf85d7754551689fa40cbb08653bf3a9bf631faf16138f9c6bea9`. `cross_oracle_gate.py` **recomputes** W0/W2 r10 over the same rational indexed mesh and compares every exact component, including fixed F + design D; ordinary cross products are never doubled. Closed/nonmanifold/shapes are numeric checks, **not** a legal Boolean/embedded solid certificate.

`tangent_neighborhood.py` validates unit native coefficient c, an orthonormal tangent basis, the base feature branch hash, four geodesic ±h and ±h/2 samples per tangent direction, and finite-difference Richardson comparison with Jc@v on predeclared dimensional scales. A changed feature branch at even one sample excludes derivative truth; same hashes are only sampled evidence, not continuous smoothness proof. No automatic model training clearance is granted.

`native_m5_bridge.py` may call the authentic pinned M4 native single-request evaluator once on a true native host, then reads the already saved same-call material and crosschecks a second pinned W2 exact-moment oracle. `live_native_m5_cli.py` enforces Linux resource preflight, max one W0-M5 native CLI process lock and 3600s parent/worker timeout. **It does not coordinate a global lock with W1/W2 native jobs**; users must serialize them externally. It returns training_admissible=false until independently certified full material partition and derivative neighborhood plus Newton terminal review.

Local (no native) command: `python -m pytest -q research/NeuralMoments/contracts/test_*.py` (93 pass); native prerequisites and exact invocation are in `M5_NATIVE_HANDOFF.md`. See `W0_M5_EVIDENCE_20261019.md` and `contract_smoke_m5.json`.


## M6 native full exact material partition

`full_partition_m6.py` reuses the genuine source-bound one-call M4/M5 native audit, then calls the **opposite-side Cherchi Boolean once** using `evaluator.material(c)`'s identical frozen source; it does **not** reconstruct a new source or solve Newton. It builds independently validated exact material-region handles for original/F/D/retained/cavity and calls the native `check_exact_material_partition` for all three required decompositions. The complement's exact normalized target coordinates are inverted into physical rational coordinates using the **actual inverse** of the binary64 frame matrix, never its approximate transpose. Ten raw moments for retained+cavity must equal design as exact rationals. Native predicate facts, timing and RSS process HWM are stored, and `training_admissible=false` is mandatory.

`live_native_m6_cli.py` admits only precommitted SHA pins and a trusted real evaluator factory on a 20+GiB RAM/swap0 node, shares W0 M5's in-process serialization lock, times out after 60 minutes and **never overwrites an existing evidence file**. Cross-window native jobs must still be scheduled serially. Run `python -m pytest -q research/NeuralMoments/contracts/test_*.py` for local W0-only checks; M4/M5/M6 mirror result `142 passed in 0.27s` is not a Cherchi runtime certificate. This local host blocked actual native preflight at 5.81 GiB, exit 3.

See `M6_NATIVE_HANDOFF.md`, `contract_smoke_m6.json`, and `research/ParallelLaunch/W0_M6_EVIDENCE_20261019.md`. Further independent Newton terminal and continuous derivative-neighborhood proof remain required for any real W2 teacher/training promotion.


## M7 externally pinned terminal journal and KKT review

New W0-only `terminal_archive_m7.py` is a **read-only reviewer** for immutable actual `solve_cherchi_inprocess_and_seal_faster` production archives. It demands exact independently frozen SHA256 for **every** `MAP_SAVED` evaluation file, all essential saved terminal/material/complement/result/complete/event records, final accepted native c, source and geometry identity, exact rational ten-moment reintegration, and correct Jc→solver Jacobian chain rule. A missing, unreferenced, mutated or reordered nonterminal material is denied. Archive file pins must be committed by an independent collector **after writer close, before review**; model/build/source pins must be separately fixed **before execution**. No existing archive or failed record is overwritten.

`original_stationarity_m7.py` provides separately tested original-mode numerical KKT via complex step and correct native coefficient B mapping; `live_original_objective_m7.py` can run only with installed production `faster_material.py` and original objective contract whose **SHA256 are externally pinned**. `m7_evidence_chain.py` binds one M6 exact partition record to the same terminal c/source/retained geometry but does **not** grant authenticity to self-asserted native flags. `live_terminal_m7_cli.py` never launches Newton; production-dependent options return a typed blocked status in an environment without native modules.

```bash
python -m pytest -q research/NeuralMoments/contracts/test_*.py
PYTHONPATH=python python -m research.NeuralMoments.contracts.live_terminal_m7_cli --archive /immutable/native-run --pins /externally-frozen/terminal-pins.json --output /new/m7-review.json
```

The measured isolated **M4–M7** mirror was **222 passed in 0.55 seconds** including five extra multi-evaluation journal tests; earlier M1–M3 tests were not rerun in this mirror. Only synthetic archives were numerically checked here, and both real verifier/original KKT modes correctly returned `BLOCKED_PRODUCTION_VERIFIER_UNAVAILABLE` (exit3). This is **NOT** a claim of real Cherchi convergence, a valid full material partition, geometric/printability approval or a smooth derivative-neighborhood certificate. **`training_admissible=false` always.** See `M7_TERMINAL_HANDOFF.md`, `contract_smoke_m7.json` and `research/ParallelLaunch/W0_M7_EVIDENCE_20261019.md`.


## M8 actual archived H8e Cherchi data (not a Newton convergence claim)

W0 `real_h8e_archive_m8.py` verifies authentic downloaded H8e 25-point native and classifier ZIP artifacts (GitHub Actions run IDs `39121571756` failure and `39122997405` success). It binds the artifact ZIP hashes, frozen request and report hashes, each gzip snapshot SHA, native coefficient/source/geometry identity and independently recomputes all ten mass moments by exact rational signed tetrahedra. It also checks 25 indexed mesh edge closures, fixed material target frame and nine 5-point numerical Jacobian stencils. This is a **real historical Cherchi** offline audit, not a new native run.

The observed 25 real snapshots all match binary64 raw moments (`max_abs_error=0.0`); fixed-frame maximum discrepancy `2.22e-16`; nine reconstructed derivative checks maximum normalized `2.60e-10`; native run was **failure** because raw topology hashes drifted in eight perturbation points. A later successful 24/24 exact symbolic patch classification is *finite point only*, and cannot prove continuous smoothness. Thus full Newton terminal/represented-set partition/differentiability remain unverified and `training_admissible=false`. See `M8_REAL_H8E_ARCHIVE_HANDOFF.md`, `contract_smoke_m8.json`, `research/ParallelLaunch/W0_M8_EVIDENCE_20261019.md`.


## M9: real 81-point exact Cherchi archived replay and point 60 (not smooth/ Newton)

`real_h8f_81_m9.py` re-reads original **failed** GitHub Actions run `39123384402` artifact `12135528290`, strictly checks GitHub SHA256 ZIP/source/report/request and every 81 material identity, independent oriented closure, all ten raw mass moments per point from exact rational archived geometry (`--exact-mode all --workers 4`), 30 independently reconstructed five-point stencils and the preserved false certification flags. The 81×10 real moments match binary64 exact projections (max abs error 0) and finite differences show max normalized 9.45e-10, but this is not original/CAD physics or Newton convergence. A mathematical LPI-order normalization leaves exactly point 60 (2 source features removed/2 added, 17 signed source triangles replaced, 5 vertex identity positions changed) as a nontrivial **finite sampled combinatorial event**. It does not prove an open smooth neighborhood or a changed exact Boolean represented solid. `training_admissible=false`, `certified_smooth_neighborhood=false`, `newton_converged=false` always. See `M9_REAL_H8F_81_HANDOFF.md` and `W0_M9_EVIDENCE_20261019.md`.


## M10: W3 surrogate versus real native endpoint cross-window gate

`h9_event_admission_m10.py` opens the original SHA-pinned H8f failed 81-point archive; independently re-evaluates exact binary64→Fraction signed edge determinants (59 positive/60 negative), original source/design interior nearest-line parameters, native Jc two-point secant (max difference 6.11608878342898e-10) and unchanged symbolic triangle identities except point60. An external W3 certificate is admitted only with immutable Git Blob SHA `213d0d7f7bfec6ffa293cfd735556d8b10316601`, signed exact native endpoint fractions and explicit **zero** between-endpoint real native evaluations. The precision root belongs to a conditional fixed-normal surrogate and must never be called a certified real root; `newton_admitted=false` and `training_admissible=false` always. M8+M9+M10 locally observed 71/71 pytest PASS using actual original ZIPs. See `M10_H9_W3_EVENT_HANDOFF.md` and `W0_M10_EVIDENCE_20261020.md`.


## M11 independently sealed W3 four-real-native-side packet handoff

M11 `w3_four_side_replay_m11.py` accepts only an externally postrun-frozen **13-file SHA256 receipt** plus *prerun* three native-binary SHA256 identities and the original SHA-pinned H8f 81-point archive. It independently reintegrates all ten undoubled raw moments, checks original quadric c (except the frozen c[7] side sample), source/geometry SHA, exact sided edge signs, Jc column 7 from each same-call material, and both left/right finite sample derivative secants. All four side samples must genuinely exist; stale Stage9 reports return code 3.

M11's read-only W3 Stage9 observation reports **0 new Cherchi calls / 0 new packets**; local M8–M11 mirror tests **137 passed** and Stage9 preflight exits **3 BLOCKED_MISSING_FOUR_NEW_CHERCHI_SIDE_MATERIALS**. Synthetic four-side test fixtures exercise negative and metadata-positive code paths only. Under no condition does M11 infer a continuous derivative neighborhood or release Newton/teacher labels: `newton_admitted=false`, `training_admissible=false`. See `M11_W3_FOUR_SIDE_HANDOFF.md`, `contract_smoke_m11.json`, `research/ParallelLaunch/W0_M11_EVIDENCE_20261020.md`.

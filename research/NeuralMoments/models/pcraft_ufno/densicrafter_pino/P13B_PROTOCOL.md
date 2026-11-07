# W6 P13b: Higher resolution DensiCrafter × PINO material optimization

## Motivation and accuracy boundary
P13a's 8^3/16^3 CPU checks are solely gradient-integration smoke.
This follow-up actually runs **32^3 and 64^3** four-arm optimization and
a **128^3 one forward+backward** smoke on GitHub Actions CPU.

**Crucial**: PINOFeatureEncoder._prepare_geometry adaptive-avg-pools
inputs larger than its configured grid. The experiment uses a frozen
P-CRAFT U-FNO at grid_size=8; this is **not 32/64/128^3 Fourier resolution**.
A source-grid aliasing test constructs different subcell material fields
with identical 8^3 pooled inputs but different true discrete cut moments.
Do not generalize performance to 512^3 / complex CAD.

## Four controlled arms
Same initial material/shell/PINO weights, one seed, identical optimizer
step count and Adam LR; PINO weights are frozen for this CPU design
experiment (not a trained physical teacher).
1. DensiCrafter-only: mass/CoM/contact/height objective, no PINO moment.
2. PINO-only: preserve original model cut moments, without reducing mass.
3. Weighted coupled: mass/CoM/contact plus soft PINO moment error.
4. Feasible joint: same weighted loss, but backtracking and rollback
   ensure *predeclared tolerances* on PINO cut moment error, an
   **independent physical voxel-center hard-cut ten-moment integral**,
   and the normalized nine non-mass full material moments.

Independent checks are required because lowering a soft weighted
PINO objective DOES NOT guarantee an actual CAD cut shape.
Raw material mass is deliberately reduced; normalizing the other
nine moments is a practical shape/inertia-proxy constraint, NOT a proof
of preserved absolute inertia / structural strength.
A 2-voxel outer shell is fixed to protect a minimum **sampled wall**
of two voxels, not an arbitrary manufacturable minimum wall thickness
in mm or STL mesh fidelity. All current inputs are synthetic cubes.

A "hard feasible" optimizer uses sampled-model and independent discrete
cut checks, not Cherchi and no real Newton derivative admission. It may
reject all steps and yield zero mass saving; never call failed
optimizations successful. Report accepted/rejected step counts.

## Cloud gates
- Python tests of 2-cell shell, W0 raw 10 moment cross factors,
  independent cut truth, aliasing, mathematical feasible checks,
  density autograd at 32^3.
- GitHub CPU 32^3 + 64^3 four-arm gradient optimization, 12 updates
  each, with independent moments + time + peak process RSS.
- 128^3 **only one** density/PINO forward+backward and memory report.
  A passing input-gradient run is not 128^3 full spectral operator.
- Preserve existing P13a 21 tests on same branch.

## Local high-resolution gate
True 256^3/512^3 requires actual sparse architecture (official fVDB
CUDA independent env), GPU memory/profile and per-shape material budget.
For PINO to retain local detail we need a validated multiscale/sparse
feature injection, not just higher input geometry. Full Cherchi
teacher and CAD native r/J + event-safe Newton remain W0/W2 gates.

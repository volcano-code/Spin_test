# W6 M7f — SO(3) orbit finite-grid mass gate: confirmatory negative result

Date: 2026-11-06. Source W6 commit: `92506938baffd11d52ce1a727bdfb578bc6085a6`.
Workflow: https://github.com/volcano-code/Spin_test/actions/runs/42234640205
Artifact: `spin-pino-m7e-orbit-ensemble` from that run.
Task labels: `ANALYTIC_CONTINUUM_P0_NOT_W2_CHERCHI`, seeds 131/137/139,
matched rotated held-out ellipsoids, 120-step analytic training.
Gate: prespecified sampled `sum(rho*occupancy)` relative drift <= 0.05
for every additional view and every sample in the evaluation batch.

| Requested views | Ungated r relative L2 | Ungated J relative L2 | Gated r relative L2 | Gated J relative L2 | Mean accepted | Mean rejected | Gated CPU time (s) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.37123135 | 0.44951810 | 0.37123135 | 0.44951810 | 1 | 0 | 0.00001539 |
| 2 | 0.41987793 | 0.49270917 | 0.37123140 | 0.44951813 | 1 | 1 | 0.00981554 |
| 4 | 0.44482612 | 0.51429371 | 0.37123140 | 0.44951813 | 1 | 3 | 0.01130658 |

The initial random-SO(3) test input has mean sampled material-mass
interpolation discrepancy 0.29911, varying across the three seeds:
0.29845, 0.29740, and 0.30148. This is a **discrete grid measure**
and not physical material loss. For all three seeds, the 5% gate
rejected all additional views. Hence the gate prevents M7e's observed
view-averaging regression by reverting to direct PINO inference.
It **does not improve the 1-view accuracy**, and it adds rotation
resampling work merely to reject additional views.

## Decision
- DO NOT promote orbit averaging or this gate as a new default.
- Retain the gate as an opt-in negative-control/fail-closed study.
- Next experiment: rotation-aware, mass-conservative geometric
  representation, preserving the P-CRAFT/PINO Fourier backbone and
  the physical moment head. Evaluate occupancy-mass leakage, r/J
  rotational generalization, accuracy/cost, and unchanged identity
  predictions before considering a new promotion.
- A performance or physics claim requires true native Cherchi and
  actual Spin optimization evidence; the current P0 labels cannot
  grant it.

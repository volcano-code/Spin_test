# W6 M7f: precommitted discrete-mass drift gate for SO(3) orbit inference

## Context / provenance
The M7e three-seed GitHub Actions run 42217536334 on analytic P0 labels
found that increasing inference views 1 -> 2 -> 4 worsened both held-out
raw ten-moment and 10x10 Jacobian relative L2. The initial arbitrary SO(3)
input resampling already lost approximately 30% of sampled rho*occupancy mass.
M7f does **not** relabel that drift as a geometric mass loss; it is a numerical
input-representation discrepancy on a finite grid.

## Hypothesis (not claimed as solved)
An opt-in, precommitted 5% relative sampled-material-mass drift bound
can reject corrupted additional orbit views while retaining the original
P-CRAFT PINO direct inference and differentiable moment/Jacobian head.

The gate compares sum(rho*occupancy) before and after each **additional**
rotation, on the same finite voxel grid. The identity view cannot be rejected.
For a batched prediction, a view is rejected for the entire batch if *any*
sample violates the gate, avoiding sample-specific batch-shape changes.
Invalid or zero reference sampled mass causes fail-closed ValueError.
The model's existing ungated behavior remains the default.

## Same-data comparison
The existing M7e orbit CI experiment now emits both original and gated
1/2/4-view conditions with the exact same trained models and held-out
random-SO(3) samples; three seeds 131/137/139 and 120 training steps.
Threshold 0.05 was set before inspecting the gated results. It is an
engineering guard, not a validated universal physical tolerance.
Report per-condition r/J relative L2, accepted/rejected views, and CPU
inference wall time. Extra view resampling for screening costs time even if
the model call is avoided.

## Boundaries / promotion
This filter can at best avoid a harmful orbit average. Merely returning to
single-view accuracy is NOT a positive generalization gain and is NOT a
novel physics operator. Do not promote orbit averaging to default unless
held-out improvements are reproducible and favorable in end-to-end cost.
No W2/Cherchi supervision, certified Jacobian, arbitrary CAD, or native
Newton optimizer admission is implied.

All files in this milestone are under the W6-only
research/NeuralMoments/models/pcraft_ufno/spin_pino/ subtree.

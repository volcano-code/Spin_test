# W6 M12 — Validation-only value of information for 0/1/2 analytic moment anchors

**Repository:** `volcano-code/Spin_test`, **sole writable branch** `research/neuralmoments-w6-pcraft-20261019`, **sole changed subtree** `research/NeuralMoments/models/pcraft_ufno/`.

**Frozen previous W6 parent:** `028dc5951744a1a8d8348750874fe33f2d57a6ff` (M11). **Native source:** `0bcc187b3005478baa586a6d6f450e73811ca342`. **Reference P-CRAFT:** `volcano-code/test@24eda3e9b3f87ba16251a9025761986d6cfe3079`. This is an **analytic P0 smoke and offline decision-policy study**, NOT native/Cherchi training, an exact CAD material certificate, GPU benchmark, or full 10D solver.

## A. Scientific question / failure disclosure

W6 M11 found that 0/1/2 independently paid *analytic* moment observations can correct a Gauss–Newton **decision residual**, but a correction that helps one signed target may hurt the opposite direction. M11 cannot promote the corrected vector as a physical material moment. M12 asks whether a **geometry-level value-of-information policy can choose K = 0,1,2 without seeing withheld current/target truth**, and whether the *physically bounded* M8 atom adaptation has the same decision benefit as a freely corrected residual.

**New results do not establish a general native speedup.** Selecting K=2 for every geometry has higher analytic acceptance than the learned VOI heuristic; its price is more reference calls. The chosen scalar price **0.2** is an abstract per-reference-query per-target penalty, *not* measured Cherchi time or an empirical cost calibration. Tiny utility differences are inconclusive. The M8 bounded-weight comparison is often less beneficial for optimization acceptance, despite preserving nonnegative sampled atomic representation.

## B. Implemented files and exact source semantics

- `m12_value_policy.py`: computes exact mass of the **declared center-cell piecewise-constant proxy**, not of underlying CAD; creates observable risk from **only** raw 4-channel `D`, cached proxy/model r/J, externally supplied task `goal_r`, and current 1D vertical native c/h. No oracle `r_true`, `J_true`, post-step acceptance, or test label is passed into this function. Calibrates two ordered score thresholds on disjoint new *development* boxes/spheres, optimizing `acceptance - lambda * (analytic r-only anchor calls / requested target count)`. A frozen policy chooses 0/1/2 for each entire geometry before any target-geometry support query.
- `m12_experiment.py`: freezes preexisting M10 training for source-pinned W6 M7 (`13448` real parameters) and W5 4-channel voxel DeepONet (`13939` parameters), exactly the same source tensors, optimizer, batch schedule and heldout family policy. Evaluates M11 **decision-only** r-anchor correction and the distinct M8 **nonnegative bounded-atomic weight fit** under separately charged K=0/1/2 oracle r budgets. All alternatives are scored with independent analytic truth **after** candidate selection. No new native W2 labels are read or promoted.
- `m12_audit.py`: replays per-geometry test cases, control direction balance, oracle purchase budget, per-model seed aggregates, development/test SHA isolation, false W2 counts, baseline/corrected acceptance and risk inference surcharge. Altered test outcomes and budgets fail closed.
- `test_m12.py`, `test_m12_audit.py`: 31 new adversarial/smoke tests. New 100-step 3-seed CPU experiments, full results, summary, source/checkpoint receipts, and complete regression log. The unabridged per-geometry/per-case report is committed as `m12_full_three_new_seeds.json.gz` (gzip, deterministic mtime=0), with separate lightweight per-seed receipts.

**Only vertical positive signed W0 native c(h)**, half-space beta>=0, with undoubled native moments, and surrogate Jacobian dr/dc_native. Goal moments in this experiment are synthesized by an **independent analytic oracle** to define each task; that goal construction also has a cost. The goal oracle and poststep/diagnostic truth are *not* charged to the incremental **selection** budget, and this distinction is documented explicitly. A true native optimizer would have different initial/goal/verification costs.

## C. Reproducible training / independent evaluation

CPU, PyTorch `2.10.0+cpu`, NumPy `2.3.5`, Python `3.13.5`, one thread, deterministic algorithms. New seeds **107, 109, 113** (not reused as M10/M11 test/selection seeds).

Each seed: train on 20 boxes + 20 spheres, two c queries each (80 analytic r/J labels). Existing M10 whole-geometry checkpoint validation holds out 8 of the 40 geometries, retaining 64 fitting cases. VOI threshold fitting uses **8 other new box/sphere geometries** (different geometry SHA identities; 64 mixed-goal decision examples), never the checkpoint validation or unseen ellipsoid test labels. Test is 20 *different* ellipsoids × eight *distinct* target queries, **four h+0.12 and four h−0.12 per geometry**. Across three seeds and both model families this gives **120 model/geometry evaluations, 960 candidate decisions**. Every K strategy on every geometry is computed as a *separate offline counterfactual experiment*; deployed per-policy K counts are modeled independently.

From repository root:

```bash
OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python -m unittest \
    research.NeuralMoments.models.pcraft_ufno.test_m4 \
    research.NeuralMoments.models.pcraft_ufno.test_m5 \
    research.NeuralMoments.models.pcraft_ufno.test_m6 \
    research.NeuralMoments.models.pcraft_ufno.test_m7 \
    research.NeuralMoments.models.pcraft_ufno.test_m8 \
    research.NeuralMoments.models.pcraft_ufno.test_m9 \
    research.NeuralMoments.models.pcraft_ufno.test_m10 \
    research.NeuralMoments.models.pcraft_ufno.test_m11 \
    research.NeuralMoments.models.pcraft_ufno.test_m11_merge \
    research.NeuralMoments.models.pcraft_ufno.test_m12 \
    research.NeuralMoments.models.pcraft_ufno.test_m12_audit -v

OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  python -m research.NeuralMoments.models.pcraft_ufno.m12_experiment \
    --seeds 107,109,113 --steps 100 --per-family 20 --target-count 8 \
    --oracle-price .2 --output /tmp/w6_m12_full.json

python -m research.NeuralMoments.models.pcraft_ufno.m12_audit \
  --input /tmp/w6_m12_full.json --output /tmp/w6_m12_replay_receipt.json
```

**Actually executed in local mirror:** 220 unittest cases, **219 passed, 1 skipped, 0 failed** (exit 0; `m12_full_tests_local.log`); the new **31/31 passed** (21+10), including 10 tamper/ledger assertions. Three 100-step model-training seeds and independent mixed-target evaluation ran successfully. Strict replay returned `PASS_NOT_NATIVE` for all six model×seed runs and all 960 offline candidate outcomes; see `m12_replay_audit.json`. GitHub Actions on this exact W6 commit has NOT been confirmed.

Historical mirrored code verification: 12 key M4–M11 Python modules were checked **byte-identical to existing Git blob SHAs**. Three pre-M4 helpers (`analytic_cut.py`, `fixed_moments.py`, `teacher_gate.py`) were reconstructed locally to match frozen documented semantics and their own original Git blob SHAs do **not** match; the M4 dataset SHA regression passed. This means **our local run is not a byte-identical full remote W6 checkout**, and an unchanged checkout CI remains desirable. No old remote files are replaced in this commit. Full source receipt in `m12_source_receipt.json`.

## D. Measured heldout mixed-direction performance

Values are means of three seeds; 20 ellipsoid geometries ×8 targets/seed; four positive and four negative targets per geometry. K queries are r-only analytic observations *per geometry*, amortized over eight targets. `K=0/1/2` are fixed policies; **VOI** thresholds are fit on distinct development geometries, never ellipsoid labels.

| Model / policy | Candidate acceptance ↑ | r-only online references / target ↓ | mean positive target acceptance ↑ | mean negative target acceptance ↑ |
|---|---:|---:|---:|---:|
| W6 M7 K=0 | 87.08% | 0 | 74.58% | 99.58% |
| W6 M7 K=1 | 94.79% | 0.125 | 92.08% | 97.50% |
| W6 M7 K=2 | **99.79%** | 0.250 | 100.00% | 99.58% |
| W6 M7 validation VOI | 97.92% | **0.1521** | 96.67% | 99.17% |
| W5 DeepONet K=0 | 77.71% | 0 | 77.92% | 77.50% |
| W5 DeepONet K=1 | 92.92% | 0.125 | 92.08% | 93.75% |
| W5 DeepONet K=2 | **95.21%** | 0.250 | 93.75% | 96.67% |
| W5 DeepONet validation VOI | 94.38% | **0.1958** | 92.92% | 95.83% |

W6's learned VOI chooses K per test geometry: **10×K0, 27×K1, 23×K2** (60 geometries in three seeds), compared to 60×K2 for the fixed 2-query policy. The corresponding *selection* queries are 73 (VOI) versus 120 (fixed K2); **the offline benchmarking process executes more oracle calls** because it also evaluates all comparison policies and true poststeps. For W5, VOI chooses 7×K0, 12×K1, 41×K2.

With the *predeclared arbitrary* price lambda=.2, mean abstract objective `acceptance - .2 * selection_calls_per_target` is **0.94875 for W6 VOI**, versus **0.94792 for fixed K2**. This ~0.00083 difference is **not statistically convincing**. A 1,500-draw exploratory seed/geometry bootstrap finds a VOI-minus-K2 utility interval approximately **[-0.0248,+0.0158]**. VOI acceptance itself is lower than K2. This is a qualified budget-saving behavior, not a demonstrated general superiority.

The VOI computation itself costs an extra *batched* eight surrogate `r/J` predictions plus nine proxy-volume mass evaluations per geometry; on this one-thread CPU that took approximately **2.23ms/geometry (W6), 2.75ms/geometry (W5)**. It cannot be treated as a zero-cost policy. The cheaper proxy itself models piecewise-constant center-cell `rho*occupancy`, not true CAD geometry.

**Physicality ablation:** When W6 M7 uses the M8 **bounded nonnegative atom-weight adaptation** instead of M11's decision-residual bias, heldout acceptance is **87.08% (K0), 88.13% (K1), 87.50% (K2), 87.50% (VOI K mix)**. It retains the sampled atomic nonnegative construction, but it does **not** replicate the very large decision-only improvement. Consequently the calibration vector used for M11's high acceptance **must not be exported as a material-moment prediction**.

## E. Remaining limits / next scientific gate

1. VOI threshold behavior changes across seeds; model selection uses just 8 development geometries per seed. New K choices may collapse to fixed K1/K2. More families / geometry splits are required; do not claim a universal VOI policy.
2. The risk proxy is an explicitly *new cellwise* interpretation of D and does not recover subvoxel information. M9 privileged analytic anti-alias input remains an unfair source for real deployment.
3. Original `ANALYTIC_P0` oracle is **not Cherchi**; 0 W2 native training labels, 0 native calls, no verified derivative neighborhood, exact mesh partition, Newton/KKT or source-owned CAD proof. W2 excluded historical H8f candidates remain unused.
4. No measured actual Cherchi cost, no end-to-end total runtime saving, no CUDA peak VRAM or full 10D optimization test. Production `admitted_for_real_optimizer` remains false.
5. **M13:** same-source mesh/center-cell geometry and conservative integration under nonvertical cuts, including source digest and discretization error. **M14:** measured GPU cold/hot/cache cost, failure fallback, checkpoint provenance; later native teacher A/B only after W0/W2 admission.

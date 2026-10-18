# W6 M2 — W0-aligned P0 physical-cut training smoke (2026-10-19)

## Reproduction

Branch: research/neuralmoments-w6-pcraft-20261019
Only path modified: research/NeuralMoments/models/pcraft_ufno/
Frozen baseline: 0bcc187b3005478baa586a6d6f450e73811ca342

From the repository root (Python 3.13.5, PyTorch 2.10.0+cpu, NumPy, single CPU thread):

    python -m unittest research.NeuralMoments.models.pcraft_ufno.test_stage2 -v
    python -m research.NeuralMoments.models.pcraft_ufno.experiment_stage2 --seed 19 --steps 12 --per-family 20 --repetitions 7 --output research/NeuralMoments/models/pcraft_ufno/stage2_analytic_cpu.json

Executed: 11/11 local tests passed, 1.005s, exit 0. Full test log is test_stage2.log; numerical evidence is stage2_analytic_cpu.json. Earlier W6 model.py and adaptation.py were reproduced byte-for-byte locally and independently checked with Git blob SHAs 994aad8d6094e0a1343b2b3c9c1bf91be8da4bdf and 9f07b7a3955c68cfb7ac4c7cd70e1340e20ce333 respectively. New scripts were also compared against their locally calculated Git blob SHAs. This is NOT GitHub CI.

## Dependency audit (read only)

W0 published mathematical contract at fbf3f3a3916d504baef0557ed9979525ec63b7b6:
native c = (const,x,y,z,xx,yy,zz,yz,xz,xy);
raw r = (M,LX,LY,LZ,QXX,QYY,QZZ,QYZ,QXZ,QXY);
monomial q = Bc, B = diag(1 seven times, 2 three times).
For smooth continuous full ambient cuts, Jq = Jc B^-1 can be symmetric, but raw Jc generally is NOT. Our signed retained side is beta_c(x)>=0, with positive scale equivalence only. The W0 schema itself is not yet imported into W6 or production-certified.

W2 branch 14b1d2d5da4e258d125e664b5665ef84f7ebbb4e has only pre-W0 adapter smoke, manifest native_teacher_runs=0, training_samples=0. The new teacher_gate.py rejects unreviewed or unsupported teacher data. No real Cherchi runs, labels, training, or native material certificates were used.

W5 branch 8efd22864dc61b4782e1e2f8c0b177db3a15fff5 reports DeepONet 13,674 parameters and geometry MLP 13,482. Existing W5 synthetic experiment uses POLYNOMIAL DENSITY control c, not Spin physical CUT control c. It is scientifically invalid to compare published W5 r/J errors numerically with the W6 physical-cut results; both must be re-trained on an identical oracle dataset and input parity policy. No cross-model speedup or accuracy superiority is claimed.

## Implementation

- analytic_cut.py: independent exact continuum P0 vertical-cut truth for closed boxes, spheres and axis-aligned ellipsoids, returning unit signed native c[10], undoubled r_D[10] and full 10x10 J_D. Analytic solid truth, NOT voxel mass quadrature; geometry is sampled into a 4-channel 8^3 tensor, SDF/inner boundary channels imputed as zero rather than misreported.
- fixed_moments.py: cached fixed contribution r_total = r_D + r_F, J_total = J_D, never recompute fixed F or differentiate it.
- experiment_stage2.py: seeded 12-step CPU paired ablations (value-only vs value+0.5 derivative J MSE+0.05 continuum Jq asymmetry MSE); constrained symmetry loss is ONLY valid for smooth full ambient continuum labels, never blindly for tangent or discrete W2 records.
- teacher_gate.py: fail-closed validation barrier until W0/W2 signed native teacher agreement.
- test_stage2.py: 11 unit and integration tests: W0 cross-term twice, sphere cap and ellipsoid analytic, plane parameter finite difference, full-ambient Jq symmetry, native J asymmetry, projective radial null, cached F, deterministic geometry family split and synthetic tiny training/adaptation.

## Experiment protocol and real numbers

Seed 19, 40 distinct train geometries (20 boxes + 20 spheres), 2 cuts each = 80 train labels. Hold out 20 unique ellipsoids and 2 cuts each = 40 test labels (no family or geometry SHA leakage). PyTorch model width=4, modes=3, latent=24, head width=40, 13,982 trainable real DOFs, batch 8, Adam lr=0.003, 12 CPU steps, 8^3 input, no FEM checkpoint or GPU. GPU hours = 0.

| Metric (analytic held-out ellipsoids) | Moment-only | Derivative + W0 smooth Jq |
|---|---:|---:|
| raw r MAE | 0.0663465 | 0.0668731 |
| raw J MAE | 0.0254248 | 0.0231718 |
| J relative L2 | 0.978830 | 0.950962 |
| directional derivative MAE | 0.0191638 | 0.0144869 |
| max predicted Jq asymmetry | 0.0377130 | 0.0515644 |
| W0-normalized component r MAE | 0.00568924 | 0.00571766 |

The derivative-enhanced arm has slightly worse r and worse Jq asymmetry. These are 12-step smoke numbers, NOT convergence, physics validation or a universal 1% guarantee.

Held-out ellipsoid analytic oracle support queries (r MAE, 0/1/2):
moment-only = 0.053695 / 0.048842 / 0.005596;
derivative+Jq = 0.053694 / 0.047970 / 0.005624.
Supports are counted as teacher queries; the latter 1/2-query numbers are NOT zero-shot.

Derivative-arm CPU median of 7: encoder 2.082ms; warm cached head 0.0756ms; warm cached 10x10 Jacobian 0.8325ms; cold encode+head 2.338ms. Process-wide CPU peak RSS ~338568 KiB (NOT model-specific/phase memory). CUDA VRAM and latency NOT measured.

## Blockers and next

W2 has no independently verified real Cherchi (r,J) labels. W0 contract schema has not been imported or validated on real CAD. W5 must be rerun with matching physical-cut c and balanced input features; previous results do not compare. Current W6 network does not converge within 12 steps, and the smooth-Jq penalty has no demonstrated structural benefit on held-out examples. Further work: W0 record schema/parity checks; supervised W2 sealed train/holdout integration once ready; W5 matched-input, matched-teacher, matched-query head-to-head; longer multi-seed training and independent decision error, GPU cold/warm/peak VRAM measurements when hardware is available. Do not infer Faster/Cherchi speedup or exact material proof from P0 analytic smoke.

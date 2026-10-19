# W5 M3: Closed triangle mesh inputs and W0-native analytic decision audit

W5-only extension on `research/neuralmoments-w5-deeponet-20261019`. Verified read-only W0 head `bfedacd3a1f4e10d30f1258331260380739d243c` and W2 head `ab93ccd6b894978311773b0f8a8b6b9c40d696ab`. Common frozen source: `0bcc187b3005478baa586a6d6f450e73811ca342`.

`mesh_features.py` computes 24 dimensionless geometry inputs from an outward-oriented closed **triangular** OBJ, integrates ten undoubled *input-solid* mass moments through oriented tetrahedra, applies explicit W0 physical frame scales, retains exact OBJ-byte SHA256, and rejects open, unoriented, nonmanifold, unreferenced and nonpositive-volume meshes. It does **not** prove absence of self-intersection, CAD topology, Boolean carving, nested shells or derivative validity; the mesh moments are never passed off as variable material `r_D(c)` truth.

Instantiate either existing W5 model with `geometry_dim=24`. Use `cached_mesh_geometry(model, mesh_features)` once and then `model.moment(z_D,c)` or `model.jacobian(z_D,c)` for multiple c queries.

`native_p0.py` implements a standalone **perfect** sphere-cap analytic oracle in native W0 `c` coordinates, with `q=Bc`, `B=diag(1,...,1,2,2,2)`. It checks the smooth-continuum full Jc and a **one-dimensional cut-height** damped Newton decision; no genuine Cherchi or general 10D optimizer certification. The analytic sphere oracle is deliberately NOT combined with the demo cube mesh to compute model accuracy. Untrained model runs only check cached input, output, Jacobian shape and CPU timing. The separately perturbed P0 oracle measures sensitivity of the decision.

Run from the repository root:

```bash
python -m pytest -q tests/python/test_w5_deeponet_smoke.py tests/python/test_w5_m2_contract_and_gate.py tests/python/test_w5_m3_mesh_and_p0.py
python -m research.NeuralMoments.models.deeponet.m3_audit --seed 101 --repeats 21 > research/NeuralMoments/models/deeponet/m3_mesh_p0_cpu.json
```

Tracked evidence: `m3_test_log.txt`, `m3_mesh_p0_cpu.json`. W2 manifest still declares `native_teacher_runs=0`, `training_samples=0`: **no** W2-native training, per-CAD error rate, production speedup or GPU runtime. Real native fitting requires separately approved W2 CAD/F/D identities, verified same-call Cherchi r/J derivative strata, W0 full semantic contract, and geometry-family heldout labels. W0 and W2 branches were not changed or merged.

# W0 M9: independently replayed real H8f 81-point Cherchi evidence

This procedure is read-only, limited to W0 scope. It neither reruns the native kernel
nor modifies GitHub Actions historical failures or other branches.

## Archived source and status, frozen externally

- GitHub Actions run: `39123384402`, **completed / failure** (2026-10-18).
- Repository code commit used in original native job: `0bcc187b3005478baa586a6d6f450e73811ca342`.
- Original artifact: `12135528290`, `heart-h8f-all81-real-jacobian-proof-or-failure`.
- ZIP SHA-256: `99a050f4604109e0323c0110a029aa5d7601d729d755e6956ad48ed8c77ccda9`.
- Embedded original `report.json` SHA-256: `28e5a641da153b08a7f15f4abb87336c797f1e85b6f2742fc025274c231f53c5`.
- Embedded original `h8f-81-exact-construction-classification.json` SHA-256: `f82801aa26d3f4228b8cb68f08abab5ef45458cc2368703e9187e0745662d6c5`.
- Frozen request SHA-256: `1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`.

GitHub report deliberately has `completed_samples=81` **and** `complete_eighty_one_samples=false`. The first is the finite evaluation count; the second preserves the **unmet strict scientific gate**, not missing files. This distinction is a tested invariant.

## Re-run on archived, actual data

Download the original attachment from [workflow run 39123384402](https://github.com/volcano-code/Spin_test/actions/runs/39123384402). The code checks the downloaded ZIP against the **fixed GitHub SHA**, not a hash supplied by the same report.

From the Spin_test checkout (with NumPy and pytest):

```bash
export W0_M9_REAL_ZIP=/path/to/original-heart-h8f-artifact.zip
python -m pytest -q research/NeuralMoments/contracts/test_real_h8f_81_m9.py

# Quick 81 point packet, closure, source feature and 30-stencil recheck
python -m research.NeuralMoments.contracts.real_h8f_81_m9 \
  --archive "$W0_M9_REAL_ZIP" --output /new/path/m9-fast.json --exact-mode none

# Full independent exact rational moments for 81 *actual* saved Cherchi materials
python -m research.NeuralMoments.contracts.real_h8f_81_m9 \
  --archive "$W0_M9_REAL_ZIP" --output /new/path/m9-full.json \
  --exact-mode all --workers 4
```

The full exact mode uses only **previously saved** materials and `Fraction` signed tetrahedra. It checks 810 density-weighted raw moments against the real archive (floating projection equality), and checks indexed oriented closure, material/source SHA and W0 fixed-frame accounting. No new Cherchi Boolean or Newton solve takes place. Recomputed numeric finite differences cover all 30 five-point stencils and all 10 literal coefficient columns.

## Genuine point 60 witness: discrete construction changes

- Baseline point 0 and point 59 (native `c[7]=+1.5e-6`) have the same **normalized LPI construction signatures and oriented signature-triangles**.
- Point 60 (`c[7]=+3.0e-6`) changes exactly output vertex positions `[8043, 8044, 8045, 8046, 8047]`. Changes are not explained by LPI line endpoint ordering or plane-triangle vertex ordering.
- Comparing signature multisets rather than incidental output indices, two unique LPI construction features disappear and two different features appear.
- Comparing oriented triangle *source-feature* multisets (cyclic rotation allowed, winding reversal forbidden), 17 triangles disappear and 17 new triangles appear. Source triangle faces remain byte-identical; the raw output `variable_faces` has 434 differing rows, most reflecting incidental vertex reindexing.
- Original raw `SOURCE_FEATURE_BRANCH_V2` hash changes at 17 of 80 perturbed points; independent normalized exact construction classification is 79 `STABLE_NOT_CERTIFIED` and 1 `FEATURE_CHANGE` (point 60). All 30 numeric stencils pass, while 9 contain raw hash changes.

**Scientific limit:** the two sampled c-values bracket *observed different discrete representations*. They do **not** locate a continuous event root, certify an open smooth neighborhood, prove a change in exact represented Boolean solid, or show that Newton converges. Historical CI failure, `qualified_branch_neighborhood=false`, `certified_smooth_neighborhood=false`, `formal_newton_converged=false`, `training_admissible=false` remain unchanged.

## Next gate

1. Have W3 independently inspect the true local two-source-face construction and edge event, with native exact admissibility/one-sided derivative probes. W0 observes W3 only; do not modify W3.
2. Re-run a fresh, source-frozen native probe at justified bracketing points if a real certified interval is needed; preserve all original artifact/CI identities.
3. Only with a separately authenticated continuous-stratum proof and an **actual completed and independently sealed Newton solver run** can later review W5/W6 teacher training promotion. An 81-point FD audit, however accurate, never creates a converged Newton endpoint.

# W0 M15 — coordination and CI integration handoff

This is a **W0-owned contract gate**, not an active GitHub Actions workflow or teacher publisher. Historical H8f Actions run 39123384402 was a failure. W2's archival 81 records (17 unit c / 64 nonunit c) remain excluded. W3 still lacks four independently certified same-call native side materials; no accepted Heart Newton step or terminal OBJ is proved.

Run a lightweight regression from repository root:
```bash
python -m pytest -q research/NeuralMoments/contracts/test_contract_v1.py research/NeuralMoments/contracts/test_validate_contract_v1.py research/NeuralMoments/contracts/test_w2_teacher_gate.py research/NeuralMoments/contracts/test_cross_window_release_m15.py
python -m research.NeuralMoments.contracts.cross_window_release_m15 --snapshot research/NeuralMoments/contracts/m15_observation.json --output /new/path/m15_gate_result.json
# Gate exit code 3 is an EXPECTED denial, NOT a CI failure when separately interpreted.
```

The branch SHAs in m15_observation.json are a read-only historical observation, not a permanently current catalog or CI status. A future collector must re-fetch branch SHA and verify source files before a new report. No label can be released by this gate, even if upstream flags claim success. W5/W6 analytic P0 work is not authenticated Cherchi training.

`M15_CI_WORKFLOW_TEMPLATE.yml` is a template only. No write to `.github/workflows/` is authorized in W0; activating it requires a separate approved integration change. Native jobs retain 24 GiB/swap0, <=4 compile parallelism, <=60 minute per-job constraints.

# W0 M8 — replay one genuine archived H8e 25-point Cherchi run

Scope: `research/NeuralMoments/contracts/`, `research/ParallelLaunch/` ONLY; historical frozen core `0bcc187b3005478baa586a6d6f450e73811ca342` not edited.

## Exact source provenance (original GitHub Actions records are immutable inputs)

- **Native job**: https://github.com/volcano-code/Spin_test/actions/runs/39121571756, status **failure**, source commit `fd7459f7bf10344269d3b9b3ada39d3e81edde48`, artifact ID `12134772056`, `heart-h8e-25point-real-jacobian-proof-or-failure`, ZIP SHA256 `14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38`.
- **Offline classification job**: https://github.com/volcano-code/Spin_test/actions/runs/39122997405, status **success**, source commit `c743f35424c52790e29708d331299fa33b00b29b`, artifact ID `12134499573`, ZIP SHA256 `e17d90a8195637358d19e61fda3d8e1946cb33540f26190cead6723e7a36ef16`.
- Native report SHA256 `7937da1e76a73612d71bc0d4352c292c2549655c770d024a06548eb8e8096d0f`; frozen prepared request SHA256 `1d2b06063c5b2c7010fcb2764518c05c9707f013d6914bc4e20298f8516e061c`. The downstream classifier explicitly binds both source digests.

The two ZIPs were fetched in W0 M8 using the GitHub connector's Actions artifact download, not synthesized or modified. The 21.7MB native ZIP has 25 complete `point-###-material.json.gz` and matching metadata, plus source request and original report. The tiny independent classifier ZIP contains the original finite-point classification JSON. The helper refuses a ZIP unless its SHA matches the frozen GitHub metadata. Do not rename or substitute an archive silently.

## Replay locally (Python/NumPy, no Cherchi native build required)

```bash
PYTHONPATH=. python -m research.NeuralMoments.contracts.real_h8e_archive_m8 \
  --native-archive /path/to/h8e-25point-native-source-failure.zip \
  --classification-archive /path/to/h8e-25point-exact-classification.zip \
  --output /new/path/w0_m8_reaudit.json

W0_M8_NATIVE_ARCHIVE=/path/to/h8e-25point-native-source-failure.zip \
W0_M8_CLASSIFICATION_ARCHIVE=/path/to/h8e-25point-exact-classification.zip \
  python -m pytest -q research/NeuralMoments/contracts/test_real_h8e_archive_m8.py
```

Outputs are created exclusively and never overwrite native run logs, old failed CI or other branches. Without the optional downloaded source ZIPs, the one actual-archive identity test SKIPS explicitly; synthetic math tests still execute but can never claim a full 25-point genuine replay.

## Executed W0 M8 result

- 25/25 real archived same-call material packets bound to unique SHA256; 25/25 indexed triangle boundary edge orientations checked (8455 vertices and 16910 faces each).
- 25/25 independent `Fraction`-exact signed tetrahedral raw 10-moment reintegrations on the actual retained target-frame rational boundary; **binary64 max absolute difference 0** against original and independent numbers. Fixed-shell target-frame sum difference max `2.22e-16`.
- Nine independent five-point finite differences match the original numerical report, maximum normalized error `2.6019151368622826e-10`; 3/9 have different original source feature hashes and 8 perturbed points contain source hash drift. The separate successful construction classification has 24/24 stable symbolic patch identities **NOT CERTIFIED** as continuous geometry.
- Replay wall time `76.19 s`. Fifteen local regression tests pass in `0.09 s`. This is **NOT** a full M1–M7 suite rerun and **NOT** a native Newton run.

## SCIENTIFIC LIMITS: DO NOT PROMOTE

The original native workflow intentionally exited **failure** for strict hash drift. Later exact finite-point construction classification does not certify an open smooth derivative neighborhood. Actual Newton optimality, complete independently sealed original/F/D/retained/cavity material, printability, 81-point ten-column Jacobian, author CAD and training admission remain **false / unverified**. W5/W6 real label release is blocked until authenticated full native solve and separate derivative-neighborhood and physical seal.


# W6 candidate library — license and provenance audit

Audit date: 2026-11-06. This is an engineering provenance checklist, not legal advice.

## Direct-reuse candidates with a verified root license

| Project | License found | Pinned license blob |
|---|---|---|
| NeuralOperator | MIT | 5637378e3734ad545887a7e782f1cf22e4ced42f |
| Transolver++ | MIT | 83787cb894a379be3f9babe7e701d5e7d338ec9f |
| Neural-Solver-Library | MIT | ee43be6e2f4082018ca353fc961328c2f3a7a0dc |
| NVIDIA PhysicsNeMo | Apache-2.0 | 82676a5d11201bc4b7dedfa819fb37b2abe81d08 |
| QuadrANN | MIT | e3bf69af5a25254481a9ad7a6035d91ae2097e80 |
| fVDB | Apache-2.0 | d9a10c0d8e868ebf8da0b3dc95bb0be634c34bfe |
| NVIDIA Kaolin | Apache-2.0 | cbfdef8c5a017e609616abb90cc040b61f99ac00 |
| PyTorch Geometric | MIT | 1f622cff1ea1df457a7a99aff1e2b875e112604d |
| e3nn | MIT | 3a7f6259353b96a5b0da5a4393d0bd2706686123 |
| TorchOpt | Apache-2.0 | 185e0144f4e84f24d2e3750d7647f2a61d278731 |
| PyTorch3D | BSD-style | c55382ff0992d90ae5ecb2cd9ac624ccd20bda4d |

## Custom permissive license

Algoim uses a custom BSD-style license with source/binary redistribution conditions and an additional enhancement-grant clause. Preserve the full copyright notice, conditions and disclaimer; do not relabel it as MIT or standard BSD-3-Clause.

Pinned license blob: 8c2302650552febe4ecaff957db0445ba28b6235.

## Copyleft isolation

torchquad's root LICENSE is GPL-3.0. It may be useful as an independent integration benchmark, but do not copy or link its implementation into the W6 core without a separate compatibility decision. Prefer a separate environment/process for comparison and review distribution consequences.

Pinned license blob: f288702d2fa16d3cdf0035b15a9fcbc552cd88e7.

## No root license found / permission required

The following repositories were inspected but no root LICENSE file was found at the audited commit:
- volcano-code/test (internal P-CRAFT source archive);
- camlab-ethz/GAOT;
- Shizheng-Wen/GAOT-3D;
- QibangLiu/GINOT;
- pengwei07/PhysGTO;
- sung-won-kim/EqGINO;
- SuikaSibyl/nqr.

UNOP's README shows an MIT badge, but no root LICENSE file was found. Treat it as permission-pending until the actual license text and scope are verified.

Do not copy source files, pretrained weights, data or shaders from these repositories into W6 until an explicit license/permission review is complete. Public accessibility alone is not a reuse license.

## Paper/repository watchlist

- Active operator learning with predictive uncertainty quantification (JCP 2026): paper identified; no code repository verified in this audit.
- Transolver-3: announced in the Transolver README; a separate official code repository was not verified.
- Opt-RNO: the expected repository path from the previous candidate list did not resolve; exact project identity/source remains unverified.

## File-level provenance

catalog.json records upstream commit SHAs and selected source Git blob SHAs. For every later import:
1. keep the original upstream URL and commit;
2. retain license and third-party notices;
3. record any local modifications as a patch, not an untraceable copy;
4. add the import and test receipt to the W6 branch;
5. re-audit if the upstream commit changes.
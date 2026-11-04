# W1 M25: four-point saved Cherchi material exact-moment replay (2026-11-04)

**Scope:** W1 performance branch only. Original user-provided \`material-evidence.zip\` has SHA-256 \`0c0962173694415b07578bae4375b9702251d0078b5c3a20935836e96d938976\`; input bytes remain outside this commit.

## Actually executed (local, not CI)

- Four previously acquired Cherchi Boolean output packets: 117/difference control, 4/intersection candidate, 116/difference candidate, 123/difference strictly empty.
- Standalone Python \`fractions.Fraction\` signed-tetra integral, original exact-rational physical-space vertices, 10 moments; additionally check three independent coordinate-axis divergence identities.
- Separately compiled C++17/GMP signed-tetra integrator \`m25_independent_gmp_tetra.cpp\` on all three nonempty real materials. All **3 × 10** rational results exactly match Python; the empty packet was *not* passed to a positive-mass integrator. Full canonical exact ten-moment values are in the user-delivered M25 archive, not this repository commit.
- Python fail-closed packet validator and 18 no-native synthetic/negative tests: 18/18 passed locally. Independent design-boundary audit was present in input; do **not** mislabel it as post-Boolean output self-intersection certification.

| Evaluation | Operator | Exact volume (float display, rho=1) | Result |
|---|---|---:|---|
| 117 | difference | 5809.272270251298 | closed positive, 10/10 exact matching |
| 4 | intersection | 7638.767584325569 | closed positive candidate, 10/10 matching |
| 116 | difference | 5809.396912303254 | closed positive candidate, 10/10 matching |
| 123 | difference | 0 | all four geometry arrays empty, **NOT** positive-mass-solver admissible |

Design volume ≈ 17185.70323640518. The canonical exact fraction serialization uses \`0xNUM/0xDEN\` to preserve enormous exact rational values without loosening Python's decimal-integer conversion guard.

## Scientific limits (deliberately fail closed)

The independent GMP helper is **not** the original production Cherchi \`.so\` integral. The input does not include same-call native production ten moments or full 10×10 Jacobian; exact production equality, full material topology/self-intersection proof, smooth-neighborhood derivative admission, convergence, W0/W2 certification and four converged A/B/B/A full-Newton speedup remain **unverified**. \`full_solver_speedup=null\`. No source geometry/solver behavior changed.

## Next

Capture authoritative production Cherchi same-input ten moments, independent post-Boolean self-intersection and source-velocity/10×10 Jacobian evidence for 117/4/116; classify 123 as empty without inferring derivative zero or smoothness; after formal approval, run sealed end-to-end converged A/B/B/A under original W1 resource and numerical contracts. Do not report paper speed from isolated stage timings.

Standalone build: \`g++ -std=c++17 -O2 -Wall -Wextra m25_independent_gmp_tetra.cpp -o m25_gmp -lgmpxx -lgmp\`.

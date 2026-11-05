# W1 M27 — adversarial regression expansion for exact post-Boolean surface audit

**Date:** 2026-11-05  
**Repository:** volcano-code/Spin_test  
**Branch:** research/neuralmoments-w1-native-20261019  
**Parent:** M26 03ea3c7d4a9df9608247bd2b7aab12dfff2c7f34  
**Write scope:** research/NeuralMoments/performance/ only.

## Purpose

M26 added an independent exact GMP triangle-intersection checker and replayed four already-saved Cherchi Boolean output packets. Before using that checker as a gate for later material-semantic work, extend its adversarial tests around cases likely to be mishandled by a broad-phase floating AABB plus exact narrow-phase predicate.

## Changes

Added test_m27_intersection_adversarial.py; production C++ predicates, the original M26 tests and solver code are untouched. Four new regression cases were added:

1. **Legal coplanar adjacency:** a closed square pyramid whose two coplanar base triangles share only their diagonal must pass.
2. **Illegal coplanar area overlap:** two closed tetrahedral shells with distinct vertex IDs and overlapping coplanar base triangles must fail with POST_BOOLEAN_SELF_INTERSECTION.
3. **Illegal geometric point contact:** two shells touching at one exact coordinate but using distinct topological vertex IDs must fail; geometric contact cannot be hidden by separate indices.
4. **Sub-ULP rational separation:** two shells separated by exactly 2^-80 at coordinate magnitude 2 must pass. The outward-rounded binary64 AABBs may conservatively overlap, but the exact GMP predicate must not report a false intersection.

## Execution evidence

Built the unchanged C++ checker in the cloud execution container using GCC 14.2, installed GMP headers/libraries and Boost.Geometry headers:

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Wno-deprecated-declarations m26_exact_intersection.cpp -o m26_exact_intersection -lgmpxx -lgmp
python -m unittest -v test_m26_exact_intersection.py test_m27_intersection_adversarial.py
```

Result: **18/18 tests passed**, 0 failures, 0 skips. The original 14 M26 tests remain green; the four new cases each exercised the intended pass/fail classification. The source checker hash remains 2536f7783ff6552ac930c294879e69b8430fc8e527873859b3ec1187d39c6ea0; this milestone changes test coverage, not production geometry behavior.

## Scientific limits

This is a synthetic/adversarial regression expansion. It does not execute Cherchi, regenerate Boolean outputs, or prove that saved Boolean output meshes represent the correct input intersection/difference domains. It does not certify production ten-moment equality, the full 10x10 Jacobian, a smooth derivative neighborhood, Newton convergence, W0/W2 admission, or full-solver A/B/B/A acceleration. full_solver_speedup remains **null**.

## Next decisive work

M28 should move from surface self-intersection to **input/output material set semantics**: authenticate the original operand boundaries and the saved Boolean output packets, then independently classify whether each output is the correct intersection/difference of those operands. The original material-evidence.zip is not tracked in this branch; real-data M28 must use the exact original archive and verify its SHA rather than reconstructing or substituting geometry. Cloud-side parser, exact predicates and synthetic fixtures are feasible; production Cherchi, full native Jacobian and Newton evidence still require the user's pinned Ubuntu native environment.

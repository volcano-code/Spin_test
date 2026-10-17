# Heart P0/P3 initial isolated checkpoint (2026-10-17)

Base: `upstream-spin-it-strict-computational-v2@a17ff49cd8a1e6e8b388bc591410bda56d67c28a`.
This branch changes only the **independent offline radial cap checker**. The original Spin repository, Spin_test/main, and Noodles V7 remain unchanged.

## Confirmed finding
The old reference code signed the cap axis using `axis @ point`, while the production C++ code uses `axis @ (point - center)`. It also always picked the largest eigenvalue; native C++ picks index 2 only when the middle eigenvalue is negative and otherwise index 0. Correcting both avoids false failures in shifted and one-negative-eigenvalue quadrics. Five-point derivatives now use the same center-relative convention.

## Tests and limits
The accompanying **isolated downloadable patch** includes a 9-test pytest suite and captured output `9 passed`. This GitHub commit contains the updated checker and this report, not the complete independent test suite. The 9-test outcome was from the isolated patch environment; it is not GitHub CI evidence.
No fresh native C++ build or Cherchi material result has been obtained here. Source-only `eval60` replay requires the historical `heart-source-failure-replay-job-03/stdout.log` containing actual rejected vertices, faces and loops, plus frozen request/runtime receipts, which are not present in the published branch. This checkpoint cannot be called a Heart solve, shape export, or dynamics result.

Next: reproduce old failure using genuine captured source operands, native rebuild, 81-point source-velocity and same-call material derivatives, then original seed0/1 Newton.

# W1 M28.3.7 exact-integer AABB hardening

Date: 2026-11-06  
Branch: `research/neuralmoments-w1-native-20261019`  
Base HEAD: `1fb0831c083eeae8b164dac183dce4da3b344db6`

## Change

The original M28.3.7 C++ checker formed its broad-phase AABBs by converting GMP integers through `mpz_class::get_d()`. Although the conversion is monotone, the broad phase does not need floating-point arithmetic at all.

The attached patch changes:
- `Box` from six doubles to six GMP integers;
- per-axis min/max to exact `std::min/std::max` over GMP integers;
- closed AABB overlap comparisons to exact integer comparisons;
- call sites to remove the obsolete dummy argument.

This patch is the exact source change used for the local recompile and replay. Apply it with `git apply m28_3_7_exact_integer_aabb.patch`.

## Verification

Build:
```bash
g++ -std=c++17 -O1 -DNDEBUG m28_3_7_exact_pair_sat.cpp -lgmpxx -lgmp -o m28_3_7_exact_pair_sat
```

Results after applying the patch:
- Eval 4: 1,163,975 AABB candidates; 416 exact positive-dimensional cut pairs.
- Eval 116: 77,779 AABB candidates; 578 exact positive-dimensional cut pairs.
- Eval 117: 25,373 AABB candidates; 580 exact positive-dimensional cut pairs.
- Eval 123: 6,560 AABB candidates; zero exact contacts.
- Total: 1,273,687 AABB candidates; 1,574 exact cut pairs.
- Pair sets exactly equal the frozen M28.3.5 pair index: zero missing and zero extra pairs.
- Unit tests: 9/9 passed, including 160 seeded random triangle-pair comparisons against the exact Fraction reference.

This is a post-review hardening of the saved-packet M28.3.7 audit. It does not add a new Cherchi Boolean call, production moments, Jacobian, Newton run, or production admission.

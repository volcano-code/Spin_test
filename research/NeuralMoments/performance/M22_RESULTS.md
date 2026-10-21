# W1 V2 M22 — full Faster solver entrypoint candidate (NOT native-admitted)

**Branch:** research/neuralmoments-w1-native-20261019. **Write scope:** research/NeuralMoments/performance/ only.
**Original evaluator/solver source Git blob:** f9fa539f699df8baf8b8d30729048269a26ecb3c.
**M8 exact-frame source Git blob:** d85ea23f6db394d13ec7410ec487ec40ab981eb2.

## Actual development

- m22_solver_runtime_candidate.py creates a new function object with the **identical code object** of the frozen production solve_cherchi_inprocess_and_seal_faster entrypoint. Its private globals bind an isolated InProcessCherchiEvaluator subclass; shared production globals are not patched.
- That subclass uses an exact Fraction-token LRU cache limited to **one native evaluator call** (cleared on success or exception) and the source-pinned M8 exact target-frame identity-axes specialization. Arbitrary affine frames use original Fraction matrix arithmetic.
- The solver's original Boolean, source motion, Jacobian calculation, material verification, Newton accept/reject, terminal-region seal, and durability paths are not rewritten or bypassed. W0 and W2 have **not** admitted this candidate.

## Actually observed

- Local unit/negative tests **13/13 passed**, including solver bytecode identity, original-vs-candidate mock accept/reject trace, offset and rotated frame exact parity, cache lifetime and exception cleanup, frozen dependency hash and source mismatch rejection.
- Independently opened the genuine archived H8e 25-point Actions ZIP (SHA256 14de425c18ac8b4704424976983d7130923432cd67a20f314e65c7f48f85ad38). On archived points **0, 8, 17**, replayed all 8,455 vertices each using old/candidate/candidate/old exact coordinate maps. Verified **25,365/25,365** rational target coordinates and **76,095/76,095** binary64 displayed components bit-for-bit against actual saved Cherchi materials; source packet gzip SHA, geometry, topology and original exact boundary flags were checked.
- Archive numerator/denominator strings were binary 0b tokens; the first local attempt using Python Fraction(string) failed. Corrected to the unmodified M8 exact binary-token parser and reran the three-point replay successfully. No first-attempt success was claimed.
- Original-vs-specialized coordinate-only replay times are in evidence/m22-real-target-3point-summary.json. This subpath timing is **not** a new Boolean/solver runtime, and cannot be extrapolated to a Faster performance speedup.

## Outstanding hard gates

**Fresh native W1 candidate Boolean calls: 0. Full original-vs-candidate Newton solves: 0. Full-solver speedup: NULL.**
The local host is limited to 4 GiB cgroup and lacks the three compiled production modules; W1 Actions workflow activation remains blocked under issue #3. This commit changes NO production src/, bindings/, main, or other W branches. The complete old/new run must be done in separate native processes under 24 GiB/swap0/<=4 compile workers/<=60 min per heavy job with M11/M14 and W0/W2 independent scientific gates.

## Genuine native-host use

```python
from make_it_stand.verification.cherchi_inprocess import InProcessCherchiEvaluator, solve_cherchi_inprocess_and_seal_faster
from m22_solver_runtime_candidate import make_candidate_solver
candidate_solver, candidate_cls = make_candidate_solver(InProcessCherchiEvaluator, solve_cherchi_inprocess_and_seal_faster)
# Pass exactly the same frozen SpinArtifactProblem, evaluator/solver parameters
# and distinct immutable output directories to original and candidate solvers.
# candidate_solver(problem, evaluator_settings=..., solver_settings=..., output_directory=...)
```

Re-run local unit checks with: python -m unittest test_m22_solver_runtime_candidate -v.
Re-run the real archived target replay with m22_real_h8_target_replay.py --archive <real-h8e.zip> --output <new-absent-path.json> --points 0,8,17.

**M22 verdict: executable candidate integration is implemented and local checks pass, but original W1 V2 core acceptance (real native speed, Newton and full terminal equivalence) remains incomplete.**

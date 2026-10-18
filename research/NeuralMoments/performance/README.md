# W1 M1 — Faster native performance audit

Scope: only `research/NeuralMoments/performance/`, branch `research/neuralmoments-w1-native-20261019`. Frozen source: `0bcc187b3005478baa586a6d6f450e73811ca342`.

First executable milestone: immutable Git blob verification of the existing Noodles/Heart historical timing reports, mutually exclusive timing-scope audit, explicit absent V7/H8 replay inputs, and a simple fail-closed sequential `StageClock` usable when real native runs are available. No production source/bindings or ABI changed.

Run:
```bash
python -m unittest discover -s research/NeuralMoments/performance -p 'test_native_profile.py' -v
python research/NeuralMoments/performance/native_profile.py --root . --output /tmp/w1-audit-01
```
Emits `baseline-performance.json` and `before_after.json`; both explicitly refuse claims of fresh native measurements or speedup when inputs/binaries and same-run old/new parity are unavailable.

Critical exclusions: the missing `research/Noodles_v7_20261017/V7_STAGE_STATUS.json` cannot be substituted with another run's 569.56s. Historical Heart is not a completed native solve. The repo already contains a GMP `PreparedBoundary` implementation; no duplicate or new ABI is introduced. Native mathematical parity, same-call material and exact rational boundary verification, full old/new run, ABI experiments and paper comparison remain blocked on real replay input/toolchain and W0/W2 approval.

Resources for subsequent native runs: serial jobs, <=24 GiB, swap=0, <=3600s per job, <=4 compile workers.

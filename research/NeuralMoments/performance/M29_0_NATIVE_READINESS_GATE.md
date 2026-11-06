# W1 M29.0 — consolidated native numerical campaign gate

Date: 2026-11-06  
Branch: research/neuralmoments-w1-native-20261019  
Scope: read-only preflight orchestration.

M28.3.7 closes the saved-Boolean boundary audit for the four frozen packets. The remaining W1 gates are production Cherchi ten-moment equality, the complete 10x10 Jacobian and smooth-branch reliability, real Newton convergence, and full original/candidate A/B/B/A timing.

The branch already has three independent native checks: M13 pinned source/build preflight, M19 real H8e profiler preflight, and M23 full Faster Newton ABBA preflight. This milestone adds m29_native_campaign_gate.py to call those existing preflight functions and combine their results.

The gate:
- checks the frozen H8c and H8e archive identities through the existing M13/M19/M23 implementations;
- checks M13 source/build readiness, M19 H8e profiling readiness and M23 full-solver readiness;
- requires all three expected native modules to be uniquely present;
- requires the module SHA-256 maps reported by M19 and M23 to match;
- writes the component preflight JSON files and one consolidated readiness receipt into a new output directory, refusing overwrite.

M13 is invoked with allow_source_fetch=True only to report NEEDS_PINNED_FETCH as a status. The gate itself does not fetch sources, compile extensions, invoke Cherchi, evaluate moments or run Newton.

## Tests

9/9 unit tests passed: all gates green; each M13/M19/M23 blocker propagates; H8c/H8e hash mismatches fail; missing native module and module SHA drift fail; and a green readiness result never implies production admission, Jacobian certification or speedup.

## Local/cloud assessment

The gate and tests were developed in the cloud. A real readiness run requires the full W1 checkout, the frozen H8c and H8e archives, and the three pinned native extensions on the Ubuntu host. Run M13 preflight first; if ready, perform its pinned build-only stage; then run M29.0. Only a green M29.0 receipt should precede M19 profiling and M23 full Newton ABBA.

The native host must meet the existing limits: at least 6 GiB address-space ceiling, swap=0, at most 4 build workers, at most 24 GiB native job cap, and at most 3600 seconds per heavy stage.

## Scientific status

M28 saved Boolean boundary semantics are certified only for the four frozen packets (4, 116, 117, 123), conditional on the frozen evidence chain. Production-native ten-moment equality, the full 10x10 Jacobian, smooth-neighborhood certification, converged Newton and complete solver speedup remain unverified. production_admitted=false; full_solver_speedup=null.

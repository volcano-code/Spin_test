# P25 — fixed-W0 native full-partition diagnostic

**Result:** TEST_ONLY native audit returned successfully. This is not formal M6 admission.

- GitHub Actions: [Run 42178859911](https://github.com/volcano-code/Spin_test/actions/runs/42178859911)
- Evidence artifact: [W4-P25-P22-fixed-W0-8GiB-test-only](https://github.com/volcano-code/Spin_test/actions/runs/42178859911/artifacts/13483998978)
- Artifact ZIP SHA-256: `7438c73725225a32500ac8ba2a07956c1a3de7fd54d8f9beb59255733d10511f`
- W4 revision executed: `343f5d7e8913efc56c9393ef49f25d7d97064198`
- W0 fixed revision: `5bab2eb2616df306906a6887a273f68acfa49320`
- Core revision: `58fd12c1306c1c01679a19172e276eef0cb30542`

## Actual native execution

| Operation | Observed calls |
|---|---:|
| Cherchi source generation | 1 |
| Cherchi Boolean | 2 |
| Derivative | 1 |
| Integration | 2 |

The unchanged W0 audit returned
`REAL_EXACT_FULL_PARTITION_VERIFIED_DERIVATIVE_AND_TERMINAL_PENDING`.
The three exact represented-set partitions all passed:

| Partition | Digest | Result |
|---|---|---|
| M = F + D | `81ca886b90fbc9d93529374d83fbee5fd672fdc95114d6907a2a5883ca8a5866` | Complete; no overlap, missing or excess content |
| D = R + C | `65ade0d9a7e5e7c8f3a1abb7a3333e107c760751927bcd8fa3b035e2cca3c5a4` | Complete; no overlap, missing or excess content |
| M = F + R + C | `6fadc907a35a19f6a2f421e1d7df1657d1d580d2e5c208a803ab992c644677a8` | Complete; no overlap, missing or excess content |

Additional exact checks passed:
- retained material plus cavity equals the design region in all ten raw moments;
- fixed plus retained density-weighted moments are verified;
- M4 same-call native execution, native region proof and mathematical replay passed;
- W2 independent exact R10 reference matched all ten values, with maximum absolute error 0.

The exact represented-set predicate backend is CGAL Nef/GMP as an **independent set checker**. Cherchi remains the geometry/evaluation path: the run recorded one Cherchi source and two Cherchi Boolean calls. CGAL was not substituted as the Cherchi construction backend.

## Resource and admission boundary

The actual container was limited to 8 GiB with `memory.swap.max=0`; its cgroup memory peak was 421,068,800 bytes and OOM/OOM-kill counters remained zero. The shared GitHub host itself reported 15.61 GiB physical RAM and 3 GiB host swap. Therefore the formal P20 resource gate was not met.

Consequently all of the following remain false:
- formal M6 executed/passed;
- W0 owner and physical-case admission;
- W2 teacher/training admission;
- smooth derivative-neighborhood certification;
- Newton terminal certification;
- training admission and physical validation.

The M5 record also explicitly leaves the independent W2 material-partition proof and independent Cherchi Boolean proof false, despite exact ten-moment parity. This is not a training or scientific release.

## Next work

1. Refresh P20/P21 fixed-W0 source identities to commit `5bab2eb2616df306906a6887a273f68acfa49320` (P26).
2. Run the refreshed P20/P21 regression suite.
3. Rebuild and independently register new six-pin identities on a host satisfying the unchanged formal resource gate.
4. Execute formal M6, then pursue derivative-neighborhood and Newton certification before optimization and MuJoCo comparison.

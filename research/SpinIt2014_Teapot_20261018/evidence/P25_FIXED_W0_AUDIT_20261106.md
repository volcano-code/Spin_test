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

## P26 follow-on — source identity refresh passed

P26 refreshed the formal P20/P21 identity chain to the fixed W0 commit `5bab2eb2616df306906a6887a273f68acfa49320`:

- P20 request SHA-256: `a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9`
- P20 factory SHA-256: `bebab47452b61da7af3faa9e202f0ca44d3e1e36d18f171c90c50517b83047f4`
- P20 launcher SHA-256: `ab63fc9b9c87307335d9bbe15f72a1ae62fec664ccfd0de8a5be50f136bcaca2`
- P21 replay SHA-256: `ad22805aed5e0a2e4057b9fadc9e96d77c734f37aed99d7efb6ee066fece4310`
- P21 replay verifier's W0/request/launcher pins were also refreshed.

[ P26 GitHub Actions — 146 regression tests ](https://github.com/volcano-code/Spin_test/actions/runs/42180376807) completed successfully: P20 74/74 and P21 72/72, with no skips. The exact W0 source blobs and all 77 frozen Core Python source blobs also matched.

## Next work

1. Obtain a host with at least 20 GiB physical and effective memory and zero host swap; the current standard GitHub runner does not qualify.
2. Rebuild or verify the actual native modules on that host and independently register a fresh six-pin record. P25 self-observed pins are TEST_ONLY and cannot be promoted.
3. Run the refreshed P21 preflight/register/execute path and obtain formal M6 evidence.
4. Obtain W0 owner/physical approval and W2 independent material-partition, Cherchi Boolean and derivative-neighborhood certification.
5. Only then proceed to Newton optimization, three-objective ablations, physical validation and optimized-before/after MuJoCo comparison.

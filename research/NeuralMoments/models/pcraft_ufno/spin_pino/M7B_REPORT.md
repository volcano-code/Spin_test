# Spin-PINO M7b fair SO(3) comparison

Workflow: [42211797282](https://github.com/volcano-code/Spin_test/actions/runs/42211797282)
Code commit: `6ca6cdc73413c86a1a6a23d571749818c62912e0`
Artifact ID: `13498609643`

Three training conditions were evaluated on the same deterministic Haar-SO(3) held-out transforms. Only rotated test samples contribute to the rotated metric.

| Training condition | r relative L2, unrotated | J relative L2, unrotated | r relative L2, SO(3) | J relative L2, SO(3) |
|---|---:|---:|---:|---:|
| No augmentation | 0.206020 | 0.314656 | 0.371231 | 0.449518 |
| Cube augmentation | 0.205555 | 0.314324 | 0.370718 | 0.449004 |
| SO(3) augmentation | 0.205568 | 0.314284 | 0.370660 | 0.448910 |

Voxel diagnostics: mean occupied voxel centers outside target cube 0%; mean soft occupancy mass ratio 0.999466; 16 rotated test samples per seed.

Conclusion: augmentation alone provides negligible benefit; arbitrary orientation generalization remains weak. Next experiment is paired SO(3)-covariance consistency loss.

Labels are analytic continuum P0 vertical-plane cuts, not W2/Cherchi. No Newton admission or real Spin end-to-end claim.

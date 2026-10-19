# W4 Cloud MuJoCo first-run failure and physics-preserving remediation

Scope: W4 branch `research/neuralmoments-w4-teapot-p1-20261019`; P1-owned files and explicitly authorized `.github/workflows/w4-teapot-mujoco.yml` only.

## Run 39237705418 (HEAD dc3ff80f8413bf066f9bdaacc052d0a33517d54d)

- GitHub-hosted `ubuntu-24.04` installed OpenSCAD 2021.01, Python 3.13.16, MuJoCo **3.3.7**, NumPy 2.5.4, Trimesh 4.12.2. Native installation/import PASSED.
- Pinned P2 z-up OBJ SHA256 matched `d3289193185192ebca4d63fc813bd77d96810051089c672e887accdf3205b331`; the code progressed to the XML digest comparison.
- Rebuilt MJCF SHA256 `4b8ffd649ae5829a84d042fc69fa17fa4a4248dde83c9b092877c22a72ab8596`, different from frozen `b830a76a8d25d689b109f15b60ab171cbac8d8aecea5a310b15ed36f1b6ffd61`. The literal difference is restricted to eigendecomposition serialized values of the `<inertial>` quaternion/diaginertia.
- Independently reconstructed physical center-of-mass tensors agree within `2.168404344971009e-19 kg*m^2`; mass, COM and every other XML attribute are unchanged.
- Existing `p4_prepare_scene.py` deliberately failed `RECREATED_MJCF_SHA_MISMATCH`, so no MuJoCo dynamics or MP4 was run in this job. The failure is retained at [first run](https://github.com/volcano-code/Spin_test/actions/runs/39237705418).
- The failed run still uploaded artifact `12179203073` containing real XML and manifest for independent comparison; no video was in that artifact.

## Corrective implementation

New `p5_cloud_scene_bootstrap.py` regenerates P0/P1-pinned P2 geometry, accepts **only** the frozen z-up OBJ SHA256, validates new scene/manifest, and compares all MJCF structure byte-exact after substituting only the two inertial eigenbasis fields. It independently reconstructs the full inertia tensor from the quaternion/principal moments and compares it with the frozen reference at `atol=1e-11 kg*m^2`; total mass and COM have independent absolute tolerances (`1e-13`, `1e-12` respectively). Generated XML gets its own SHA256 in a separate certificate. All non-inertia fields remain byte-identical at the XML-tree level, so gravity, contact geometry and scale cannot be silently changed.

The workflow now writes generated MJCF to distinct `p5-cloud-mujoco-scene` rather than overwriting the frozen `p3-mujoco-diagnostic` input. New `test_p5_cloud_scene_bootstrap.py` checks successful P2 reproducibility, allowable minor eigen-serialization change, rejection of tampered mass/inertia, and rejection of altered gravity. **5 local tests passed** using Python 3.13.5. It was also exercised on downloaded CI XML from the failed cloud run and accepted only a `2.17e-19` inertial-tensor difference.

## Scientific boundary

This continues to use the CGAL-made P2 **diagnostic proxy** for MuJoCo integration testing. It is not Cherchi Teapot geometry, not a before/after comparison and not optimization success. Actual MuJoCo dynamics/MP4 must be separately verified by the next GitHub Actions job; this note documents only the first-run failure and corrected bootstrapping procedure.

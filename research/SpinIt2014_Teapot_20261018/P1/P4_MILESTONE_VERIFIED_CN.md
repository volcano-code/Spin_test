# W4 P4 | Teapot MuJoCo video pipeline and evidence

**Status: static scene PASS; actual MuJoCo runtime BLOCKED; SciPy reference executed.**

This is an independently committed W4-only task. The source is a public Utah Teapot mesh, not the author's original CAD. OpenSCAD/CGAL P2 is a **diagnostic geometry proxy**, not Cherchi geometry. No Figure 9 optimization, W0-authorized F/D, genuine W2 Cherchi teacher, or MuJoCo dynamics result is claimed.

## Actual stage facts (2026-10-19)

- New p4_prepare_scene.py regenerates the proxy and MJCF from the immutable P0/P1 source. Y-up to Z-up P2 asset SHA256: d3289193185192ebca4d63fc813bd77d96810051089c672e887accdf3205b331. MJCF SHA256: b830a76a8d25d689b109f15b60ab171cbac8d8aecea5a310b15ed36f1b6ffd61. Both matched a fresh OpenSCAD regeneration.
- New p4_mujoco_verified_video.py (versioned beside the existing P4 script, without overwriting its previous work) checks mesh/manifest/XML identities, mass, inertia, free joint, gravity and simplified contact spheres. Its actual run path imports official MuJoCo, executes mj_step and Renderer, encodes H.264 with ffmpeg, and will archive video, three trajectories and engine metadata **only on success**. No synthetic or SciPy fallback.
- Actual tests: python -m unittest -v test_p4_video_pipeline -> 11 tests PASS (5.532 seconds). See p4_local_unittest.log.
- Explicit MuJoCo run attempted -> exit code 2: MUJOCO_RUNTIME_UNAVAILABLE_NO_ACTUAL_SIMULATION_OR_VIDEO. MuJoCo could not be installed in this environment due PyPI DNS failure. No actual MuJoCo video or CSV was generated.
- Actual SciPy DOP853 fixed-pivot reference ran 2.8 physical seconds, with 0/30/60 rad/s: peak tilts 177.1276 / 34.6659 / 9.7222 degrees; final tilts 31.5235 / 4.2262 / 5.1341 degrees. This reference does NOT model friction/contact. Its recorded H.264 MP4 is 1440x810, 169 frames, 30 FPS, 5.6333 seconds slowed playback; SHA256 280216a3cb50904fda6fc1012b7b622dcaf7fd5b250e0a1515a80c66e2669ef6. Large MP4/CSV files are supplied in the downloadable P4 stage archive, NOT as Git blobs.
- The MJCF uses *assumed diagnostic* height 0.15 m, mass 0.25 kg, virtual tip radius 2 mm, friction 0.9 and contact body sphere. The free-body dynamics and collision sphere are not physically certified design outputs.

## Reproduce from a clean Git checkout

Ubuntu install prerequisites:

    sudo apt-get install openscad ffmpeg libegl1 libgl1 fonts-noto-cjk
    python -m pip install 'numpy>=2,<3' 'scipy>=1.15,<2' 'trimesh>=4,<5' 'opencv-python-headless>=4,<5' 'mujoco==3.3.7' pillow
    export MUJOCO_GL=egl

From repository root, materialize the diagnostic scene and execute real native physics:

    P1=research/SpinIt2014_Teapot_20261018/P1
    python "$P1/p4_prepare_scene.py" --output "$P1/p3-mujoco-diagnostic"
    python "$P1/p4_mujoco_verified_video.py" --xml "$P1/p3-mujoco-diagnostic/teapot_spinning.xml" --preflight-only
    python "$P1/p4_mujoco_verified_video.py" --xml "$P1/p3-mujoco-diagnostic/teapot_spinning.xml" --out "$P1/p4-actual-mujoco" --duration 2.8 --fps 24
    python -m unittest discover -v -s "$P1" -p 'test_p4_video_pipeline.py'

Actual MuJoCo success, and only actual success, should create p4-actual-mujoco/mujoco_teapot_comparison.mp4, three mujoco_RATE_rad_s.csv files, and mujoco_video_results.json with REAL_MUJOCO_ENGINE_AND_VIDEO_EXECUTED.

To reproduce the SciPy **non-MuJoCo** reference in a scene-equipped checkout:

    python "$P1/w4_fixed_pivot_reference.py" --asset "$P1/p3-mujoco-diagnostic/assets/teapot_visual_z_up.obj" --manifest "$P1/p3-mujoco-diagnostic/simulation-manifest.json" --out "$P1/p4-reference" --duration 2.8
    python "$P1/render_fixed_pivot_video.py" --asset "$P1/p3-mujoco-diagnostic/assets/teapot_visual_z_up.obj" --manifest "$P1/p3-mujoco-diagnostic/simulation-manifest.json" --csv "$P1/p4-reference/reference_trajectories.csv" --summary "$P1/p4-reference/reference_summary.json" --out "$P1/p4-reference/w4_teapot_fixed_pivot_comparison.mp4" --poster "$P1/p4-reference/reference_poster.png" --fps 30

## Remaining scientific gates

W4 can only modify P1 paths in its own branch. Public Cherchi C++ UNION dispatch remains unresolved in its owning window, and the exact pinned external native sources are absent. Before claiming a full Cherchi Teapot simulation, require source-sealed native Cherchi boolean, independent exact certificate of the saved material, W0 Teapot-specific scale/density/spin axis/tip/F-D, W2 authenticated real moments/Jacobians, physically justified collision geometry, actual MuJoCo contact trajectories and videos, and same-condition before/after ablations.

**Never promote CGAL diagnostic geometry or a fixed-pivot SciPy animation to Cherchi + MuJoCo proof.**

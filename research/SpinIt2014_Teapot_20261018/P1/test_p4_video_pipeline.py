"""W4 P4 actual executed static provenance + independent dynamic/video checks.

No test accepts static MJCF or SciPy results as evidence of actual MuJoCo.
"""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import cv2
import numpy as np
from p4_mujoco_verified_video import P2_Z_SHA256, preflight, run, _encode_mp4, sha
from w4_fixed_pivot_reference import simulate
from p4_prepare_scene import materialize_scene

HERE=Path(__file__).resolve().parent
SCENE=HERE/'p3-mujoco-diagnostic'/'teapot_spinning.xml'
ASSET=SCENE.parent/'assets'/'teapot_visual_z_up.obj'
SUMMARY=HERE/'p4-reference'/'reference_summary.json'
TRAJECTORY=HERE/'p4-reference'/'reference_trajectories.csv'
VIDEO=HERE/'p4-reference'/'w4_teapot_fixed_pivot_comparison.mp4'

class W4P4Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Git checkout intentionally excludes generated OBJ/STL/video and can
        # reconstruct the proxy with pinned sources if OpenSCAD is installed.
        global SCENE, ASSET
        if not (SCENE.parent/'simulation-manifest.json').is_file() or not ASSET.is_file():
            if shutil.which('openscad') is None:
                raise unittest.SkipTest('OpenSCAD required to regenerate proxy only; NOT MuJoCo')
            cls._generated_scene = tempfile.TemporaryDirectory(prefix='w4-clean-checkout-')
            cls.addClassCleanup(cls._generated_scene.cleanup)
            SCENE = Path(cls._generated_scene.name)/'teapot_spinning.xml'
            ASSET = SCENE.parent/'assets'/'teapot_visual_z_up.obj'
            materialize_scene(SCENE.parent)

    def test_rebuilt_pinned_scene_produces_same_xml_sha(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt=materialize_scene(Path(tmp)/'scene',cached_mesh=ASSET)
            self.assertEqual(receipt['status'],'SCENE_STATIC_BOOTSTRAP_ONLY')
            self.assertEqual(receipt['asset_sha256'],P2_Z_SHA256)
            self.assertEqual(receipt['mjcf_sha256'],sha(SCENE))
            self.assertFalse(receipt['mujoco_engine_invoked'])

    def test_scene_pins_source_mass_inertia_and_simulation_status(self):
        result=preflight(SCENE)
        self.assertEqual(result['preflight'],'STATIC_SOURCE_AND_SCENE_PASS_MUJOCO_NOT_EXECUTED')
        self.assertEqual(result['visual_mesh_sha256'],P2_Z_SHA256)
        self.assertEqual((result['mesh_vertices'],result['mesh_faces']),(3328,6656))
        self.assertAlmostEqual(result['mass_kg'],.25)
        self.assertAlmostEqual(result['com_body_m'][2],.05961113826578046,places=12)
        self.assertEqual(result['contact'],'VIRTUAL_TIP_AND_APPROX_BODY_SPHERES_NOT_TRUE_CAD')

    def test_tampered_xml_rejected_before_mujoco(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            shutil.copytree(SCENE.parent,base/'scene')
            xml=base/'scene'/'teapot_spinning.xml'
            xml.write_text(xml.read_text()+'\n<!-- malicious content -->\n')
            with self.assertRaisesRegex(ValueError,'MJCF_SHA256_MISMATCH'):
                preflight(xml)

    def test_tampered_visual_mesh_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            scene=Path(td)/'scene';shutil.copytree(SCENE.parent,scene)
            path=scene/'assets'/'teapot_visual_z_up.obj'
            path.write_bytes(path.read_bytes()+b'\n# tamper\n')
            with self.assertRaisesRegex(ValueError,'VISUAL_MESH_SHA256_MISMATCH'):
                preflight(scene/SCENE.name)

    def test_missing_joint_rejected_even_after_resigning_xml(self):
        with tempfile.TemporaryDirectory() as td:
            scene=Path(td)/'scene';shutil.copytree(SCENE.parent,scene)
            xml=scene/SCENE.name
            tree=ET.parse(xml)
            body=tree.getroot().find('worldbody/body')
            body.remove(body.find('freejoint'))
            tree.write(xml,encoding='unicode',xml_declaration=True)
            manifest=scene/'simulation-manifest.json'
            obj=json.loads(manifest.read_text())
            obj['mjcf_sha256']=sha(xml)
            manifest.write_text(json.dumps(obj))
            with self.assertRaisesRegex(ValueError,'MISSING_FREEJOINT'):
                preflight(xml)

    def test_no_false_cherchi_or_simulation_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            scene=Path(td)/'scene';shutil.copytree(SCENE.parent,scene)
            manifest=scene/'simulation-manifest.json'
            record=json.loads(manifest.read_text())
            record['claims_cherchi_geometry']=True
            record['claims_mujoco_dynamics_run']=True
            manifest.write_text(json.dumps(record))
            with self.assertRaisesRegex(ValueError,'DIAGNOSTIC_MESH_FALSELY_PROMOTED'):
                preflight(scene/SCENE.name)

    def test_missing_runtime_cannot_emit_video_or_trajectories(self):
        if importlib.util.find_spec('mujoco') is not None:
            self.skipTest('MuJoCo is now installed; use actual runtime test instead')
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(RuntimeError,'MUJOCO_RUNTIME_UNAVAILABLE_NO_ACTUAL_SIMULATION_OR_VIDEO'):
                run(SCENE,Path(td)/'actual-run',duration=.08)
            self.assertFalse((Path(td)/'actual-run'/'mujoco_video_results.json').exists())
            self.assertFalse((Path(td)/'actual-run'/'mujoco_teapot_comparison.mp4').exists())

    def test_wrong_spin_sweep_fails_before_real_runtime(self):
        with self.assertRaisesRegex(ValueError,'THREE_CANONICAL_SPIN_RATES_REQUIRED'):
            run(SCENE,Path('/tmp/no-output-w4'),spins=(0.,20.,40.))

    def test_scipy_reference_replay_is_not_mujoco(self):
        meta=json.loads(SUMMARY.read_text())
        self.assertTrue(meta['not_mujoco'])
        self.assertTrue(meta['not_cherchi'])
        self.assertEqual(meta['geometry'],'CGAL_DIAGNOSTIC_PROXY')
        self.assertEqual(sha(ASSET),meta['asset_sha256'])
        if TRAJECTORY.exists():
            self.assertEqual(sha(TRAJECTORY),meta['trajectory_sha256'])
        rows,results,payload=simulate(SCENE.parent/'simulation-manifest.json',ASSET,total=2.8)
        self.assertEqual(len(rows),423)
        for observed,archived in zip(results,meta['results']):
            self.assertAlmostEqual(observed['spin_rad_s'],archived['spin_rad_s'])
            for key in ('max_tilt_deg','final_tilt_deg','mean_last_quarter_tilt_deg'):
                self.assertAlmostEqual(observed[key],archived[key],places=6)
            self.assertLess(observed['peak_relative_energy_error'],2e-10)

    def test_reference_video_codec_dimensions_and_truth_label(self):
        if not VIDEO.exists():self.skipTest('MP4 is distributed in the stage ZIP, not the Git source tree')
        info=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0',
            '-show_entries','stream=codec_name,width,height,nb_frames,r_frame_rate',
            '-of','json',str(VIDEO)],text=True))['streams'][0]
        self.assertEqual(info['codec_name'],'h264')
        self.assertEqual((info['width'],info['height']),(1440,810))
        self.assertEqual(info['r_frame_rate'],'30/1')
        self.assertEqual(int(info['nb_frames']),169)
        cap=cv2.VideoCapture(str(VIDEO))
        okay,frame=cap.read();cap.release()
        self.assertTrue(okay)
        self.assertEqual(frame.shape,(810,1440,3))
        self.assertGreater(frame.std(),9)

    def test_ffmpeg_codec_smoke_is_not_mujoco_simulation(self):
        with tempfile.TemporaryDirectory() as td:
            rng=np.random.default_rng(42)
            frames=[rng.integers(0,256,(48,96,3),dtype=np.uint8) for _ in range(5)]
            target=Path(td)/'codec-smoke.mp4'
            info=_encode_mp4(frames,target,fps=10,width=96,height=48)
            self.assertEqual(info['codec_name'],'h264')
            self.assertTrue(target.stat().st_size>2000)
            self.assertFalse((Path(td)/'mujoco_video_results.json').exists())


if __name__=='__main__':unittest.main()

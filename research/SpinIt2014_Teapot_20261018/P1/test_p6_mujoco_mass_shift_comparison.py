"""Numerical physical-moment and provenance guards for optional P6 cloud A/B."""
import json
import os
import shutil
from pathlib import Path
import tempfile
import unittest
import numpy as np
from p6_mujoco_mass_shift_comparison import make_counterfactual,tensor_of_inertial
from p4_mujoco_verified_video import sha
from xml.etree import ElementTree as ET

HERE=Path(__file__).resolve().parent
SCENE=Path(os.environ.get('W4_P6_TEST_SCENE_XML',str(HERE/'p3-mujoco-diagnostic'/'teapot_spinning.xml')))

class MassShiftPhysicalControls(unittest.TestCase):
    def test_mass_conservation_and_complete_inertia(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);shutil.copy2(SCENE,p/'teapot_spinning.xml')
            shutil.copy2(SCENE.parent/'simulation-manifest.json',p/'simulation-manifest.json')
            (p/'assets').mkdir()
            shutil.copy2(SCENE.parent/'assets'/'teapot_visual_z_up.obj',p/'assets/teapot_visual_z_up.obj')
            variant,receipt=make_counterfactual(p/'teapot_spinning.xml')
            self.assertAlmostEqual(receipt['original_com_m'][2]-receipt['counterfactual_com_m'][2],.012,places=12)
            self.assertTrue(receipt['identical_collision_geometry'])
            self.assertFalse(receipt['real_mujoco_started'])
            self.assertIn('NOT_CHERCHI',receipt['scientific_claim'])
            orig=ET.parse(p/'teapot_spinning.xml').getroot().find('worldbody/body/inertial')
            new=ET.parse(variant).getroot().find('worldbody/body/inertial')
            m0,c0,I0=tensor_of_inertial(orig);m1,c1,I1=tensor_of_inertial(new)
            self.assertEqual(m0,m1)
            self.assertTrue(np.min(np.linalg.eigvalsh(I1))>0)
            self.assertLess(np.max(np.abs(I1-I0)),2e-4)
            self.assertEqual(receipt['visual_mesh_sha256'],sha(p/'assets/teapot_visual_z_up.obj'))

    def test_false_proxy_provenance_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);shutil.copy2(SCENE,p/'teapot_spinning.xml')
            manifest=json.loads((SCENE.parent/'simulation-manifest.json').read_text())
            manifest['claims_cherchi_geometry']=True
            (p/'simulation-manifest.json').write_text(json.dumps(manifest))
            (p/'assets').mkdir()
            shutil.copy2(SCENE.parent/'assets'/'teapot_visual_z_up.obj',p/'assets/teapot_visual_z_up.obj')
            with self.assertRaisesRegex(ValueError,'FALSELY_PROMOTED'):
                make_counterfactual(p/'teapot_spinning.xml')

if __name__=='__main__':unittest.main()

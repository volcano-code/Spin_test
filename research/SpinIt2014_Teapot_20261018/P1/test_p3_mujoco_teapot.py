"""Physical-moment and provenance tests; MuJoCo dynamics only when installed."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation
import trimesh
from p3_mujoco_teapot import (digest, inertial_from_mesh, prepare_model,
                               geometry_origin_contract,run_simulation,P2_Z_SHA256)

HERE=Path(__file__).resolve().parent
REAL=HERE/'p2-output'/'p2-teapot-cgal-union-z-up.obj'


class TeapotMuJoCoContract(unittest.TestCase):
    def test_exact_p2_mesh_identity(self):
        self.assertTrue(REAL.is_file())
        self.assertEqual(digest(REAL),P2_Z_SHA256)
        proof=geometry_origin_contract(REAL,'diagnostic-cgal')
        self.assertFalse(proof['authoritative_cherchi'])
        self.assertFalse(proof['physical_case_authorized'])

    def test_cgal_cannot_masquerade_as_cherchi(self):
        with self.assertRaisesRegex(ValueError,'CHERCHI_NATIVE_CERT_AND_W0_PHYSICAL_CASE_REQUIRED'):
            geometry_origin_contract(REAL,'cherchi-certified')
        with tempfile.TemporaryDirectory() as tmp:
            fake=Path(tmp)/'fake-cert.json'
            fake.write_text(json.dumps(dict(schema='w4-teapot-cherchi-certified-v1',
                                             native_backend='openscad-cgal-nef',
                                             mesh_sha256=digest(REAL),exact_boundary_certified=True,
                                             independent_geometry_certified=True)))
            case=Path(tmp)/'physical-case.json'
            case.write_text(json.dumps(dict(schema='W4TeapotPhysicalCaseV1',
                                            mesh_sha256=digest(REAL),W0_physical_case_authorized=True,
                                            fixed_F_sha256='a'*64,design_D_sha256='b'*64)))
            with self.assertRaisesRegex(ValueError,'CHERCHI_INDEPENDENT_CERT_REQUIRED'):
                geometry_origin_contract(REAL,'cherchi-certified',fake,case)

    def test_inertial_tensor_rotated_and_scaled(self):
        mesh=trimesh.load_mesh(REAL,process=False)
        p=inertial_from_mesh(mesh,0.15,0.25)
        self.assertAlmostEqual(p['physical_mass_kg'],0.25)
        self.assertAlmostEqual(p['mesh_height_m'],0.15)
        self.assertLess(p['roundtrip_inertia_max_abs_error'],1e-14)
        self.assertTrue(all(x>0 for x in p['diagonal_inertia_kg_m2']))
        quat=p['quat_wxyz']
        R=Rotation.from_quat([quat[1],quat[2],quat[3],quat[0]]).as_matrix()
        expected=R@np.diag(p['diagonal_inertia_kg_m2'])@R.T
        np.testing.assert_allclose(expected,p['inertia_com_kg_m2'],atol=1e-14)
        self.assertAlmostEqual(np.linalg.det(R),1,places=12)
        self.assertAlmostEqual(p['com_m'][2],0.05961113826578046,places=9)

    def test_xml_scene_provenance_tip_and_inertia(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=prepare_model(REAL,tmp,source_kind='diagnostic-cgal',height_m=.15,mass_kg=.25)
            model=ET.parse(Path(tmp)/'teapot_spinning.xml').getroot()
            self.assertEqual(model.tag,'mujoco')
            self.assertEqual(model.find('worldbody/body/freejoint').attrib['name'],'teapot_free')
            self.assertEqual(model.find('worldbody/geom').attrib['type'],'plane')
            inertial=model.find('worldbody/body/inertial')
            self.assertAlmostEqual(float(inertial.attrib['mass']),.25)
            self.assertEqual(len(inertial.attrib['diaginertia'].split()),3)
            self.assertEqual(len(inertial.attrib['quat'].split()),4)
            self.assertEqual(model.find('worldbody/body/geom[@name="virtual_tip_contact"]').attrib['size'],'0.002')
            self.assertEqual(model.find('worldbody/body/geom[@name="teapot_mesh_visual"]').attrib['contype'],'0')
            self.assertEqual(r['status'],'MJCF_GENERATED_RUNTIME_NOT_YET_EXECUTED')
            self.assertEqual(r['mjcf_sha256'],digest(Path(tmp)/'teapot_spinning.xml'))
            self.assertFalse(r['claims_mujoco_dynamics_run'])
            self.assertFalse(r['claims_cherchi_geometry'])
            self.assertEqual(r['mesh_asset_sha256'],P2_Z_SHA256)
            self.assertTrue((Path(tmp)/'assets'/'teapot_visual_z_up.obj').exists())

    def test_requires_explicit_physical_parameters(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'DIAGNOSTIC_DIMENSIONS_MUST_BE_EXPLICIT'):
                prepare_model(REAL,tmp,source_kind='diagnostic-cgal')
            with self.assertRaisesRegex(ValueError,'PHYSICAL_SIZE_OR_MASS_INVALID'):
                prepare_model(REAL,tmp,source_kind='diagnostic-cgal',height_m=0,mass_kg=0.25)
            modified=Path(tmp)/'invalid.obj'
            modified.write_bytes(REAL.read_bytes()+b'\n# tamper\n')
            with self.assertRaisesRegex(ValueError,'DIAGNOSTIC_CGAL_MESH_SHA_MISMATCH'):
                prepare_model(modified,tmp,source_kind='diagnostic-cgal',height_m=0.15,mass_kg=.25)

    @unittest.skipIf(importlib.util.find_spec('mujoco') is not None,'MuJoCo runtime available')
    def test_no_runtime_must_explicitly_fail(self):
        with self.assertRaisesRegex(RuntimeError,'MUJOCO_RUNTIME_UNAVAILABLE'):
            run_simulation(HERE/'p3-mujoco-diagnostic'/'teapot_spinning.xml',Path('/tmp/w4-no-runtime'))

    @unittest.skipUnless(importlib.util.find_spec('mujoco') is not None,'MuJoCo package unavailable in this container')
    def test_actual_mujoco_dynamics(self):
        with tempfile.TemporaryDirectory() as tmp:
            prepare_model(REAL,tmp,source_kind='diagnostic-cgal',height_m=.15,mass_kg=.25)
            result=run_simulation(Path(tmp)/'teapot_spinning.xml',Path(tmp)/'runs',
                                  duration=.08,spin_rates=(0.,30.),sample_every=5)
            self.assertEqual(result['status'],'ACTUAL_MUJOCO_ENGINE_EXECUTED')
            self.assertEqual(len(result['runs']),2)
            self.assertTrue((Path(tmp)/'runs'/'mujoco-run.json').exists())
            self.assertTrue((Path(tmp)/'runs'/'teapot_spin_30rad_s.csv').exists())


if __name__=='__main__':unittest.main()

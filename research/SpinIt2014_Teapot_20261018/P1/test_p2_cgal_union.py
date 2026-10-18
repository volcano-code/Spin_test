"""P2 regressions: malicious input, native union, honest optimization gate."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import numpy as np
import trimesh

from p2_cgal_union import (P0_SHA256, P1_SHA256, Y_TO_Z,
                           independent_tetra_moments, trimesh_oracle,
                           source_check, prepare, geometry_gate)
from p2_self_intersection import check_nonincident_triangle_contacts

HERE=Path(__file__).resolve().parent
SOURCE=Path(os.environ.get('W4_SOURCE_OBJ',HERE.parent/'input/teapot-public-original.obj'))
CANDIDATE=Path(os.environ.get('W4_P1_CANDIDATE_OBJ',HERE/'teapot-topology-candidate-p1.obj'))
OUTPUT=Path(os.environ.get('W4_P2_OUTPUT',HERE/'p2-output'))


class TestP2Native(unittest.TestCase):
    def test_pins_do_not_accept_modified_source_or_p1(self):
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),P0_SHA256)
        self.assertEqual(hashlib.sha256(CANDIDATE.read_bytes()).hexdigest(),P1_SHA256)
        source_check(SOURCE,CANDIDATE)
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/'source.obj'
            src.write_bytes(SOURCE.read_bytes()+b'\n# tamper\n')
            with self.assertRaisesRegex(ValueError,'P0_SOURCE_SHA256_MISMATCH'):
                source_check(src,CANDIDATE)
            p1=Path(tmp)/'candidate.obj'
            p1.write_bytes(CANDIDATE.read_bytes()+b'\n# tamper\n')
            with self.assertRaisesRegex(ValueError,'P1_CANDIDATE_SHA256_MISMATCH'):
                source_check(SOURCE,p1)

    def test_sat_rejects_crossing_and_coplanar_overlaps(self):
        a=[[0,0,0],[1,0,0],[0,1,0]]
        crossed=[[.25,.25,-1],[.25,.25,1],[.75,.25,0]]
        distant=[[4,0,0],[5,0,0],[4,1,0]]
        coplanar=[[.2,.2,0],[.8,.2,0],[.2,.8,0]]
        for second,detect in [(crossed,True),(distant,False),(coplanar,True)]:
            v=np.asarray(a+second,float)
            f=np.asarray([[0,1,2],[3,4,5]])
            result=check_nonincident_triangle_contacts(v,f)
            self.assertEqual(bool(result['witnesses']),detect)
            self.assertTrue(result['exhaustive'])

    def test_tetra_moments_oracle_and_proper_rotation(self):
        vertices=np.asarray([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],float)
        faces=np.asarray([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
        m=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
        r=independent_tetra_moments(m)
        r2=trimesh_oracle(m)
        self.assertAlmostEqual(r[0],1/6,places=14)
        np.testing.assert_allclose(r[1]/r[0],[.25,.25,.25],atol=1e-14)
        for a,b in zip(r,r2): np.testing.assert_allclose(a,b,atol=1e-13)
        self.assertAlmostEqual(np.linalg.det(Y_TO_Z),1)
        z=trimesh.Trimesh(vertices=vertices@Y_TO_Z.T,faces=faces,process=False)
        mass,first,Q,_=independent_tetra_moments(z)
        self.assertAlmostEqual(mass,r[0])
        np.testing.assert_allclose(first,Y_TO_Z@r[1],atol=1e-14)
        np.testing.assert_allclose(Q,Y_TO_Z@r[2]@Y_TO_Z.T,atol=1e-14)

    def test_current_p1_must_fail_nonincident_gate(self):
        mesh=trimesh.load(CANDIDATE,force='mesh',process=True)
        contact=check_nonincident_triangle_contacts(mesh.vertices,mesh.faces,max_witnesses=4)
        self.assertGreater(len(contact['witnesses']),0)
        state,passed=geometry_gate(mesh)
        self.assertFalse(passed)
        self.assertEqual(state['components'],3)

    def test_saved_artifact_independent_audit(self):
        # A clean Git checkout contains only the pinned audit, not bulky OBJ/STL.
        # Rebuild natively in temporary storage before independently reloading.
        with tempfile.TemporaryDirectory() as tmp:
            if (OUTPUT/'p2-teapot-cgal-union-y-up.obj').is_file():
                target = OUTPUT
            else:
                if not shutil.which('openscad'):
                    self.skipTest('native OpenSCAD required to materialize clean checkout artifacts')
                target = Path(tmp)
                prepare(SOURCE,CANDIDATE,target,timeout=120)
            r=prepare(SOURCE,CANDIDATE,target,verify_existing=True)
        self.assertEqual(r['output']['y_up']['vertices'],3328)
        self.assertEqual(r['output']['y_up']['faces'],6656)
        self.assertEqual(r['output']['y_up']['components'],1)
        self.assertEqual(r['output']['y_up']['euler_characteristic'],0)
        self.assertTrue(r['output']['y_up']['trimesh_is_volume'])
        self.assertEqual(r['output']['y_up']['boundary_or_nonmanifold_edges'],0)
        self.assertEqual(r['output']['y_up']['nonincident_triangle_contacts']['witnesses'],[])
        self.assertEqual(r['output']['y_up']['nonincident_triangle_contacts']['evaluated_nonincident_aabb_pairs'],7236)
        self.assertLess(max(r['independent_mass_audit']['max_abs_oracle_error'].values()),1e-8)
        self.assertLess(r['independent_mass_audit']['max_abs_proper_rotation_transform_error'],1e-8)
        self.assertFalse(r['acceptance']['optimization_ready'])

    @unittest.skipUnless(shutil.which('openscad'), 'native OpenSCAD unavailable')
    def test_native_reproducibility_and_fail_closed_optimization(self):
        old_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as temp:
            r=prepare(SOURCE,CANDIDATE,temp,timeout=120)
            self.assertEqual(r['native']['returncode'],0)
            self.assertTrue(r['native']['native_simple_yes'])
            self.assertEqual(r['native']['native_reported_volumes'],2)
            self.assertEqual(r['output']['y_up']['components'],1)
            self.assertEqual(r['output']['y_up']['nonincident_triangle_contacts']['witnesses'],[])
            baseline=json.loads((OUTPUT/'p2-cgal-union-audit.json').read_text())
            for key in ('y_up_obj_sha256','z_up_obj_sha256','binary_stl_sha256'):
                self.assertEqual(r['output'][key],baseline['output'][key],key)
            with self.assertRaisesRegex(RuntimeError,'OPTIMIZATION_BLOCKED'):
                prepare(SOURCE,CANDIDATE,Path(temp)/'negative',require_optimization_ready=True)
        self.assertEqual(old_sha,hashlib.sha256(SOURCE.read_bytes()).hexdigest())


if __name__=='__main__':
    unittest.main()

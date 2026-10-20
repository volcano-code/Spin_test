"""W4 P10/P11 input identity, topology, exact-decimal and native-abort tests.

This suite is run AFTER P9 on the W4 cloud branch with real Cherchi material.
Missing real P9 input is an explicit skip, never a claimed native success.
"""
from pathlib import Path
from fractions import Fraction
import os,tempfile,unittest
import numpy as np
import trimesh
from p10_cherchi_material_baseline import (certify,exact_decimal_ten,
    independently_check_topology,P9_SHA,sha)
from p11_cherchi_partition_feasibility import (
    sphere_clearance,signed_winding,triangle_moments,
    edge_certificate,trial_partition,CENTER_YUP)

HERE=Path(__file__).resolve().parent
P0=HERE.parent/'input'/'teapot-public-original.obj'
P1=HERE/'teapot-topology-candidate-p1.obj'
REAL=Path(os.environ.get('W4_REAL_P9_OBJ',
     str(HERE/'p9-cherchi-handle-variants'/'cherchi-body-spout-handle-03.obj')))
JOURNAL=Path(os.environ.get('W4_REAL_P9_JOURNAL',
     str(HERE/'p9-cherchi-handle-variants'/'p9-source-deviation-sweep.json')))

class TestCherchiP10P11(unittest.TestCase):
    def test_real_p9_numerical_and_exact_decimal_moment_certificate(self):
        if not REAL.exists() or not JOURNAL.exists():
            self.skipTest('real P9 native artifact not staged; cannot infer PASS')
        with tempfile.TemporaryDirectory() as td:
            result=certify(REAL,P0,P1,JOURNAL,td)
            self.assertEqual(result['status'],'NUMERIC_CLOSED_DECIMAL_EXACT_MOMENTS_ONLY')
            self.assertFalse(result['native_exact_set_identity_certified'])
            self.assertFalse(result['W0_tip_axis_scale_density_F_D_approved'])
            self.assertFalse(result['SpinIt_optimization_performed'])
            self.assertLess(result['max_abs_error_vs_P9_production_ten'],1e-10)
            self.assertEqual(result['source_obj_sha256'],P9_SHA)
            self.assertTrue((Path(td)/'p10-numeric-source-seal.json').exists())
            self.assertEqual(len(result['exact_saved_OBJ_decimal_raw_ten']),10)

    def test_exact_analytic_tetrahedron(self):
        vv=[tuple(Fraction(x) for x in p) for p in
             ((0,0,0),(1,0,0),(0,1,0),(0,0,1))]
        faces=[(0,2,1),(0,1,3),(0,3,2),(1,2,3)]
        ms=exact_decimal_ten(vv,faces)
        self.assertEqual(ms[0],Fraction(1,6))
        self.assertEqual(ms[1],Fraction(1,24))
        self.assertEqual(ms[4],Fraction(1,60))
        self.assertEqual(ms[7],Fraction(1,120))

    def test_closed_and_nonmanifold_negative_gate(self):
        v=np.asarray([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],float)
        f=np.asarray([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
        self.assertTrue(independently_check_topology(
            trimesh.Trimesh(vertices=v,faces=f,process=False))['one_component_closed_preflight'])
        for faces in (f[:-1],np.vstack((f,f[0]))):
            self.assertFalse(independently_check_topology(
                trimesh.Trimesh(vertices=v,faces=faces,process=False))['one_component_closed_preflight'])

    def test_tampered_actual_p9_refused(self):
        if not REAL.is_file() or not JOURNAL.is_file():
            self.skipTest('P9 actual candidate missing')
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'changed.obj'
            p.write_bytes(REAL.read_bytes()+b'\n# forged trailing comment\n')
            with self.assertRaisesRegex(ValueError,'PINNED_REAL_CHERCHI'):
                certify(p,P0,P1,JOURNAL,td)

    def test_exploratory_cavity_inside_real_mesh(self):
        if not REAL.is_file():self.skipTest('P9 actual candidate missing')
        m=trimesh.load_mesh(REAL,process=False)
        d=sphere_clearance(m)
        self.assertTrue(d['independent_float_containment_pass'])
        self.assertAlmostEqual(d['numeric_surface_winding_number'],1,places=10)
        self.assertGreater(d['minimum_spherical_cavity_surface_clearance'],.79)
        with self.assertRaisesRegex(ValueError,'TRIAL_D_NOT_PROVEN'):
            sphere_clearance(m,center=(5,5,5),radius=.5)

    def test_analytic_D_volume_and_raw_ten(self):
        d=trimesh.creation.icosphere(subdivisions=2,radius=.5)
        d.apply_translation(CENTER_YUP)
        self.assertTrue(edge_certificate(d)['numeric_surface_gate'])
        m=triangle_moments(d)
        self.assertAlmostEqual(m[0],d.volume,places=12)
        self.assertAlmostEqual(m[2]/m[0],1.3,places=12)

    def test_no_native_CGAL_substitution(self):
        if not REAL.is_file():self.skipTest('P9 material is absent')
        with self.assertRaisesRegex(ValueError,'CHERCHI_NATIVE_BINARY_REQUIRED'):
            trial_partition(REAL,'/none/w4_cherchi_reference_native','/tmp/w4-missing-native')

if __name__=='__main__':
    unittest.main()

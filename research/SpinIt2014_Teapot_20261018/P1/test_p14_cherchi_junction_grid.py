"""W4 P14: regression anchored to the REAL native Cherchi P13 failed OBJ.

A passing unit suite is NOT evidence that a modified D is an accepted design.
The cloud job must execute actual native Cherchi calls separately.
"""
from __future__ import annotations
import json,os,tempfile,unittest
from pathlib import Path
import numpy as np
import trimesh
from p14_cherchi_junction_grid import (PIN,CASES,load_pinned,geometry,variant,
                                       raw_ten,native_call,write_obj,digest)

ARCHIVE=Path(os.environ.get('W4_P14_NATIVE_ARCHIVE_DIR',
                           'research/SpinIt2014_Teapot_20261018/P1/p14-source-archive'))

class RealCherchiAxisJunction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ARCHIVE.exists():raise unittest.SkipTest('real pinned P13 native artifact not staged')
        cls.files=load_pinned(ARCHIVE)

    def test_real_native_failure_162_edges_on_spindle(self):
        r=geometry(self.files['failed'])
        self.assertEqual(r['vertices'],324)
        self.assertEqual(r['triangles'],806)
        self.assertEqual(r['edge_incidence_histogram']['3'],162)
        self.assertEqual(r['non_two_incident_edges'],162)
        self.assertEqual(r['low_area_triangles'],8)
        self.assertFalse(r['strict_numeric_preflight'])
        self.assertFalse(r['watertight'])
        self.assertLess(r['nonmanifold_locus']['max_distance_to_shaft_radius'],.0004)

    def test_original_archived_geometry_provenance_unmodified(self):
        self.assertEqual({key:digest(path) for key,path in self.files.items()},
                         {key:pin[1] for key,pin in PIN.items()})
        for name in ('D','shaft','outer'):
            m=trimesh.load_mesh(self.files[name],process=False)
            self.assertTrue(m.is_volume,name)
        outer=geometry(self.files['outer'])
        self.assertEqual(outer['non_two_incident_edges'],0)
        self.assertEqual(outer['low_area_triangles'],28)

    def test_zero_shift_identity_and_reloaded_geometry(self):
        src=trimesh.load_mesh(self.files['D'],process=False)
        m,properties=variant(src,CASES[0])
        np.testing.assert_array_equal(m.vertices,src.vertices)
        self.assertEqual(properties['max_vertex_displacement'],0)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'D.obj';write_obj(p,m)
            again=trimesh.load_mesh(p,process=False)
            self.assertTrue(again.is_volume)
            self.assertAlmostEqual(again.volume,src.volume,places=12)

    def test_all_11_hypotheses_are_bounded_and_mass_consistent(self):
        source=trimesh.load_mesh(self.files['D'],process=False)
        orig=np.asarray(source.vertices).copy()
        self.assertEqual(len(CASES),11)
        for case in CASES:
            mesh,desc=variant(source,case)
            self.assertTrue(mesh.is_volume)
            self.assertTrue(desc['physical_scale_NOT_W0_authorized'])
            self.assertAlmostEqual(mesh.volume/source.volume,float(case[4])**3,places=10)
        np.testing.assert_array_equal(source.vertices,orig)

    def test_unapproved_offsets_are_rejected(self):
        source=trimesh.load_mesh(self.files['D'],process=False)
        for spec in (('far',.031,0,0,1),('spin',0,0,16,1),
                     ('scale',0,0,0,1.03),('nan',float('nan'),0,0,1)):
            with self.assertRaisesRegex(ValueError,'OUT_OF_BOUNDS'):
                variant(source,spec)

    def test_native_process_exit_zero_without_mesh_is_negative(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);bin=p/'w4_cherchi_reference_native'
            bin.write_text('#!/bin/sh\nexit 0\n');bin.chmod(0o755)
            output=p/'missing.obj'
            res=native_call(bin,'subtraction',
                 [self.files['D'],self.files['shaft']],output,5)
            self.assertEqual(res['returncode'],0)
            self.assertFalse(res['output_exists'])
            self.assertFalse(output.exists())
            self.assertTrue(Path(str(output)+'.native.json').is_file())

    def test_actual_sha_mutation_cannot_fake_a_new_admissible_source(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            for k,(name,_) in PIN.items():(p/name).write_bytes(self.files[k].read_bytes())
            target=p/PIN['shaft'][0]
            target.write_bytes(target.read_bytes()+b'\n# fake\n')
            with self.assertRaisesRegex(ValueError,'SHA_MISMATCH_shaft'):
                load_pinned(p)

    def test_analytic_tetrahedron_raw_ten_formula(self):
        v=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],dtype=float)
        f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype=int)
        m=trimesh.Trimesh(vertices=v,faces=f,process=False)
        r=raw_ten(m)
        self.assertAlmostEqual(r[0],1/6,places=14)
        np.testing.assert_allclose(r[1:4],[1/24]*3,atol=1e-15)
        self.assertAlmostEqual(r[4],1/60,places=14)
        self.assertAlmostEqual(r[7],1/120,places=14)
        with tempfile.TemporaryDirectory() as d:
            o=Path(d)/'tetra.obj';write_obj(o,m)
            self.assertTrue(geometry(o)['strict_numeric_preflight'])

if __name__=='__main__':unittest.main()

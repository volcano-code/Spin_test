"""W4 P1 independent source-based preflight and negative-gate regression."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
import trimesh

from p1_geometry import (SOURCE_SHA256, read_obj, boundary_loops, vertex_fans,
                         closed_surface_checks, signed_volume_and_moments,
                         _tri_overlap, prepare)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(os.environ.get('W4_SOURCE_OBJ',
    ROOT/'input'/'teapot-public-original.obj'))


class TopologyFixtures(unittest.TestCase):
    def test_tetra_positive_and_closed(self):
        v = np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        f = np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
        self.assertTrue(closed_surface_checks(v,f)['topologically_closed'])
        volume, first, _, cm, _=signed_volume_and_moments(v,f)
        self.assertAlmostEqual(volume,1/6,places=12)
        np.testing.assert_allclose(cm,[.25]*3,atol=1e-14)
        self.assertEqual(boundary_loops(f)[1],0)
        open_f=f[:-1]
        self.assertEqual(sorted(map(len,boundary_loops(open_f)[0])),[3])
        self.assertFalse(closed_surface_checks(v,open_f)['topologically_closed'])

    def test_bad_orientations_and_contact_sat(self):
        v=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        bad=np.array([[0,1,2],[0,1,3]])
        with self.assertRaisesRegex(ValueError,'INCONSISTENT_WINDING'):
            boundary_loops(bad)
        a=np.array([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.]])
        b=np.array([[2.,0.,0.],[3.,0.,0.],[2.,1.,0.]])
        c=np.array([[.2,.2,-1.],[.2,.2,1.],[.8,.8,0.]])
        self.assertFalse(_tri_overlap(a,b))
        self.assertTrue(_tri_overlap(a,c))

    def test_pin_source_sha(self):
        self.assertTrue(SOURCE.is_file(),str(SOURCE))
        original=SOURCE.read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(),SOURCE_SHA256)
        with tempfile.TemporaryDirectory() as tmp:
            tampered=Path(tmp)/'tampered.obj'
            tampered.write_bytes(original+b'\n# modified\n')
            with self.assertRaisesRegex(ValueError,'SOURCE_SHA256_MISMATCH'):
                prepare(tampered,Path(tmp)/'rejected')

    def test_real_teapot_repair_and_independent_reload(self):
        with tempfile.TemporaryDirectory() as tmp:
            before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
            report=prepare(SOURCE,Path(tmp))
            self.assertEqual(report['input']['vertices'],3644)
            self.assertEqual(report['input']['faces'],6320)
            self.assertEqual(report['input']['geometric_vertices'],3241)
            self.assertEqual(report['input']['open_edges'],160)
            self.assertEqual(report['input']['boundary_loop_lengths'],[20,20,20,20,40,40])
            self.assertEqual(len(report['input']['bowtie_vertices']),1)
            self.assertEqual(report['input']['bowtie_vertices'][0]['coordinate'],[-2.,.9,0.])
            self.assertEqual(report['candidate']['vertices'],3246)
            self.assertEqual(report['candidate']['faces'],6480)
            self.assertEqual(report['candidate']['connected_components']['count'],3)
            self.assertEqual(report['candidate']['connected_components']['euler_characteristic'],6)
            self.assertGreater(report['candidate']['pseudovolume_delta'],0)
            self.assertTrue(report['candidate']['pseudovolume_comparison_is_nonphysical'])
            rows=(Path(tmp)/'p1-diagnostic-moments.csv').read_text().strip().splitlines()
            self.assertEqual(len(rows),11)
            self.assertTrue(all('NOT_AUTHORIZED_GEOMETRY' in r for r in rows[1:]))
            self.assertEqual(report['repairs']['joined_lid_and_body_rims']['added_triangles'],80)
            self.assertTrue(report['candidate']['closed_checks']['topologically_closed'])
            self.assertTrue(report['candidate']['conservative_suspected_triangle_contacts']['witness_face_pairs'])
            self.assertFalse(report['geometry_legal'])
            self.assertFalse(report['physical_moments_authoritative'])
            self.assertFalse(report['optimized'])
            self.assertEqual(report['coordinate_plan']['fixed_F'],'NOT_GENERATED')
            self.assertEqual(report['coordinate_plan']['removable_D'],'NOT_GENERATED')
            self.assertEqual(len(report['optimization_ablation_registry']),3)
            out=Path(tmp)/'teapot-topology-candidate-p1.obj'
            self.assertEqual(hashlib.sha256(out.read_bytes()).hexdigest(),
                             report['candidate']['candidate_obj_sha256'])
            v,f=read_obj(out)
            self.assertTrue(closed_surface_checks(v,f)['topologically_closed'])
            mesh=trimesh.load(out,force='mesh',process=False)
            self.assertTrue(mesh.is_watertight)
            self.assertTrue(mesh.is_winding_consistent)
            self.assertAlmostEqual(mesh.volume,report['candidate']['diagnostic_signed_volume'],places=9)
            np.testing.assert_allclose(mesh.center_mass,report['candidate']['diagnostic_centroid'],atol=1e-8)
            self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),before)
            with self.assertRaisesRegex(RuntimeError,'CERTIFICATION_BLOCKED'):
                prepare(SOURCE,Path(tmp)/'negative-gate',require_certified=True)


if __name__=='__main__':
    unittest.main()

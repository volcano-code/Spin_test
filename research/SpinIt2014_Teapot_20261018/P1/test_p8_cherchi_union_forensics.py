"""P8 genuine Cherchi-only forensic gates: independent topology and fail-closed.

No native success or optimizer result may be inferred from synthetic fixtures.
"""
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
import trimesh

from p8_cherchi_union_forensics import (inspect_obj,indexed_components,
                                        run_case,WHOLE_TEAPOT_CASES)
from p7_cherchi_native_union import write_obj,sha


def tetra(shift=(0.,0.,0.)):
    v=np.asarray([[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])+np.asarray(shift)
    f=np.asarray([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype=np.int64)
    return v,f


class IndependentP8Topology(unittest.TestCase):
    def test_complete_tetra_closed_and_connected(self):
        v,f=tetra()
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'valid.obj'
            write_obj(out,trimesh.Trimesh(vertices=v,faces=f,process=False))
            saved,report=inspect_obj(out)
            self.assertEqual(report['index_components'],1)
            self.assertEqual(report['non_two_incidence_edges'],0)
            self.assertTrue(report['independent_numeric_geometry_pass'])
            self.assertAlmostEqual(saved.volume,1/6,places=12)
            self.assertTrue(report['conservative_float_contacts']['exhaustive'])

    def test_three_incident_faces_rejected(self):
        v,f=tetra()
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'bad.obj'
            write_obj(out,trimesh.Trimesh(vertices=v,faces=np.vstack([f,f[0]]),process=False))
            _,report=inspect_obj(out)
            self.assertGreater(report['non_two_incidence_edges'],0)
            self.assertFalse(report['independent_numeric_geometry_pass'])
            self.assertGreater(len(report['bad_edge_witnesses']),0)
            self.assertEqual(report['conservative_float_contacts']['status'],'NOT_RUN_TOPOLOGY_FIRST')

    def test_nonmanifold_hole_fails_closed(self):
        v,f=tetra()
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'open.obj'
            # P7's writer intentionally rejects incomplete source meshes;
            # first serialize a valid tetra, then mutate the saved OBJ as an
            # adversarial output fixture (not as a legal input).
            write_obj(out,trimesh.Trimesh(vertices=v,faces=f,process=False))
            lines=out.read_text().splitlines()
            face_positions=[i for i,line in enumerate(lines) if line.startswith('f ')]
            self.assertEqual(len(face_positions),4)
            del lines[face_positions[-1]]
            out.write_text('\n'.join(lines)+'\n')
            _,report=inspect_obj(out)
            self.assertFalse(report['watertight'])
            self.assertGreater(report['non_two_incidence_edges'],0)

    def test_independent_index_components(self):
        v,f=tetra()
        self.assertEqual(indexed_components(len(v),f),[4])
        v2,f2=tetra((5.,0,0))
        self.assertEqual(indexed_components(8,np.vstack([f,f2+4])),[4,4])

    def test_missing_native_output_not_success(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            fake=d/'w4_cherchi_reference_native'
            fake.write_text('#!/bin/sh\nexit 0\n');fake.chmod(0o755)
            v,f=tetra();a=d/'a.obj';b=d/'b.obj'
            write_obj(a,trimesh.Trimesh(vertices=v,faces=f,process=False))
            write_obj(b,trimesh.Trimesh(vertices=v+np.array([.1,0,0]),faces=f,process=False))
            record,out=run_case('fake',[a,b],fake,d,10)
            self.assertEqual(record['native_exit_code'],0)
            self.assertEqual(record['geometry_status'],'NATIVE_FAILED')
            self.assertFalse(out.exists())

    def test_pairwise_only_result_never_promoted_as_complete_teapot(self):
        self.assertEqual(WHOLE_TEAPOT_CASES,
            frozenset({'all-three','all-reversed',
                       'body-handle-then-spout','body-spout-then-handle'}))
        self.assertNotIn('body-plus-handle',WHOLE_TEAPOT_CASES)
        self.assertNotIn('body-plus-spout',WHOLE_TEAPOT_CASES)
        self.assertNotIn('spout-plus-handle',WHOLE_TEAPOT_CASES)

    @unittest.skipUnless(os.environ.get('W4_P7_FAILED_REAL_OBJ'),
                         'real archived native failure OBJ not supplied')
    def test_actual_p7_invalid_surface_is_not_promoted(self):
        path=Path(os.environ['W4_P7_FAILED_REAL_OBJ'])
        _,report=inspect_obj(path)
        self.assertEqual(report['vertices'],3344)
        self.assertEqual(report['faces'],6754)
        self.assertEqual(report['non_two_incidence_edges'],68)
        self.assertEqual(report['index_components'],3)
        self.assertFalse(report['independent_numeric_geometry_pass'])


if __name__=='__main__':
    unittest.main()

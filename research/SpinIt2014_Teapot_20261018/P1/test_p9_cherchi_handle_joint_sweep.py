"""P9 controlled tiny handle shift: tests are not native Cherchi proof."""
from pathlib import Path
import unittest
import numpy as np
import trimesh

from p7_cherchi_native_union import validate_input
from p9_cherchi_handle_joint_sweep import translated_handle,SHIFTS,MAX_SHIFT_ABS

HERE=Path(__file__).resolve().parent
P0=HERE.parent/'input'/'teapot-public-original.obj'
P1=HERE/'teapot-topology-candidate-p1.obj'


class HandleShiftGates(unittest.TestCase):
    def test_original_label_and_topology(self):
        body,spout,handle=validate_input(P0,P1)
        self.assertEqual((len(body.faces),len(spout.faces),len(handle.faces)),(4800,840,840))
        self.assertGreater(spout.bounds[0,0],0)
        self.assertLess(handle.bounds[1,0],0)
        self.assertTrue(handle.is_volume)

    def test_zero_shift_byte_equal_vertices(self):
        handle=validate_input(P0,P1)[2]
        result,error=translated_handle(handle,0)
        self.assertEqual(error,0)
        np.testing.assert_array_equal(result.vertices,handle.vertices)
        np.testing.assert_array_equal(result.faces,handle.faces)

    def test_handle_only_moves_along_declared_axis_and_preserves_volume(self):
        mesh=validate_input(P0,P1)[2]
        original=np.asarray(mesh.vertices)
        for shift in (.0005,.002,.005,.01,-.002):
            candidate,error=translated_handle(mesh,shift)
            delta=np.asarray(candidate.vertices)-original
            np.testing.assert_allclose(delta[:,0],shift,atol=2e-15)
            np.testing.assert_array_equal(delta[:,1:],np.zeros_like(delta[:,1:]))
            np.testing.assert_array_equal(candidate.faces,mesh.faces)
            self.assertTrue(candidate.is_volume)
            self.assertAlmostEqual(candidate.volume,mesh.volume,places=12)
            self.assertLessEqual(error,abs(shift)+1e-12)
        np.testing.assert_array_equal(mesh.vertices,original)

    def test_invalid_shift_is_rejected(self):
        mesh=validate_input(P0,P1)[2]
        with self.assertRaisesRegex(ValueError,'HANDLE_SHIFT_EXCEEDS'):
            translated_handle(mesh,MAX_SHIFT_ABS+.0001)
        for shift in (float('nan'),float('inf')):
            with self.assertRaisesRegex(ValueError,'HANDLE_SHIFT_EXCEEDS'):
                translated_handle(mesh,shift)

    def test_sweep_is_explicit_and_bounded(self):
        self.assertIn(0.,SHIFTS)
        self.assertTrue(any(x>0 for x in SHIFTS))
        self.assertTrue(any(x<0 for x in SHIFTS))
        self.assertEqual(len(SHIFTS),len(set(SHIFTS)))
        self.assertTrue(all(abs(x)<=MAX_SHIFT_ABS for x in SHIFTS))


if __name__=='__main__':unittest.main()

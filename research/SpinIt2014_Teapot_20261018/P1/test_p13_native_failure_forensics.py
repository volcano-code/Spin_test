"""W4 P13 authentic-surface nonmanifold/degeneracy diagnostics."""
from pathlib import Path
import json,os,tempfile,unittest
import numpy as np
import trimesh
from p13_native_failure_forensics import audit,sha256


class NativeShaftSurfaceGate(unittest.TestCase):
    def _file(self,folder,faces=None):
        v=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],dtype=float)
        f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype=int)
        p=Path(folder)/'tetra.obj'
        trimesh.Trimesh(vertices=v,faces=f if faces is None else faces,process=False).export(p)
        return p,f

    def test_one_closed_tetra(self):
        with tempfile.TemporaryDirectory() as d:
            path,_=self._file(d)
            result=audit(path)
            self.assertEqual(result['non_two_incident_edges'],0)
            self.assertEqual(result['status'],'NUMERIC_CLOSED_SURFACE')
            self.assertFalse(result['W0_design_authorized'])

    def test_zero_native_exit_not_topological_certificate(self):
        with tempfile.TemporaryDirectory() as d:
            path,faces=self._file(d)
            self._file(d,np.vstack([faces,faces[0]]))
            record=Path(d)/'native.json'
            record.write_text(json.dumps({'exit':0,'sha256':sha256(path)}))
            result=audit(path,record)
            self.assertGreater(result['non_two_incident_edges'],0)
            self.assertFalse(result['watertight'])
            self.assertEqual(result['status'],'REJECTED_NONMANIFOLD_OR_DEGENERATE_NATIVE_OUTPUT')

    def test_changed_native_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path,_=self._file(d)
            log=Path(d)/'native.json'
            log.write_text(json.dumps({'exit':0,'sha256':'0'*64}))
            with self.assertRaisesRegex(ValueError,'RECEIPT_SHA_MISMATCH'):
                audit(path,log)

    def test_nonzero_native_exit_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path,_=self._file(d)
            log=Path(d)/'native.json';log.write_text(json.dumps({'exit':5}))
            with self.assertRaisesRegex(ValueError,'NATIVE_PROCESS_FAILED'):
                audit(path,log)

    @unittest.skipUnless(os.environ.get('W4_P13_INVALID_NATIVE_OBJ'),
                         'historical P13 native result not mounted')
    def test_actual_saved_native_failure(self):
        obj=Path(os.environ['W4_P13_INVALID_NATIVE_OBJ'])
        native=Path(os.environ['W4_P13_INVALID_NATIVE_RECEIPT'])
        result=audit(obj,native)
        self.assertEqual(result['non_two_incident_edges'],162)
        self.assertEqual(result['low_area_triangles'],8)
        self.assertEqual(result['vertices'],324)
        self.assertEqual(result['triangles'],806)
        self.assertEqual(result['status'],'REJECTED_NONMANIFOLD_OR_DEGENERATE_NATIVE_OUTPUT')


if __name__=='__main__':
    unittest.main()

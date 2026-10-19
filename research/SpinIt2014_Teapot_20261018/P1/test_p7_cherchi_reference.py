"""W4 P7 input, no-fallback and independent integration-moment regressions."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
import trimesh
from p7_cherchi_native_union import (P0_SHA,P1_SHA,validate_input,native_identity,
    write_obj,check_native_output,moments_crosscheck,run_native,sha)

HERE=Path(__file__).resolve().parent
P0=HERE.parent/'input'/'teapot-public-original.obj'
P1=HERE/'teapot-topology-candidate-p1.obj'

class P7CherchiReferenceTests(unittest.TestCase):
    def test_pinned_mesh_components(self):
        self.assertEqual(sha(P0),P0_SHA)
        self.assertEqual(sha(P1),P1_SHA)
        parts=validate_input(P0,P1)
        self.assertEqual([len(p.faces) for p in parts],[4800,840,840])
        self.assertTrue(all(p.is_volume for p in parts))

    def test_tampered_source_rejected_before_native(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'modified.obj'
            p.write_bytes(P1.read_bytes()+b'\n# mutated\n')
            with self.assertRaisesRegex(ValueError,'PINNED_P0_OR_P1_SHA_MISMATCH'):
                validate_input(P0,p)

    def test_no_native_means_no_cgal_fallback(self):
        with self.assertRaisesRegex(ValueError,'NATIVE_CHERCHI_REFERENCE_BINARY_REQUIRED'):
            run_native(P0,P1,'/none/w4_cherchi_reference_native','/none/source',
                       '/tmp/forbidden-w4-p7',timeout=10)

    def test_rejects_wrong_binary_basename(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'cgal-not-cherchi';p.write_text('#!/bin/sh\nexit 0\n');p.chmod(0o755)
            with self.assertRaisesRegex(ValueError,'UNEXPECTED_CHERCHI_REFERENCE_BINARY_NAME'):
                native_identity(p,Path(d))

    def test_closed_tetra_oracle(self):
        v=np.asarray([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],dtype=float)
        f=np.asarray([[0,2,1],[0,1,3],[0,3,2],[1,2,3]])
        mesh=trimesh.Trimesh(vertices=v,faces=f,process=False)
        with tempfile.TemporaryDirectory() as d:
            target=Path(d)/'valid.obj';write_obj(target,mesh)
            got,state=check_native_output(target)
            self.assertTrue(state['float_independent_preflight_pass'])
            moments=moments_crosscheck(got)
            self.assertAlmostEqual(moments['unit_density_raw_ten'][0],1/6)
            self.assertLess(moments['max_abs_independent_tetra_vs_trimesh'],1e-12)
            f_bad=f[:-1];broken=trimesh.Trimesh(vertices=v,faces=f_bad,process=False)
            target=Path(d)/'notclosed.obj'
            target.write_text('\n'.join(line for line in (Path(d)/'valid.obj').read_text().splitlines() if not line.startswith('f ') or line != 'f 2 3 4')+'\n')
            with self.assertRaisesRegex(ValueError,'CHERCHI_NATIVE_OUTPUT_FAILED_INDEPENDENT_FLOAT_GATE'):
                check_native_output(target)

    def test_unsupported_timeout_denied(self):
        with self.assertRaisesRegex(ValueError,'PER_CALL_TIMEOUT_OUT_OF_BOUNDS'):
            run_native(P0,P1,'/none','/none','/tmp/none',timeout=3601)

if __name__=='__main__':unittest.main()

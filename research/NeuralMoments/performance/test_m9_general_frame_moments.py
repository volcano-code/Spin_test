"""Regression tests for M9's general proper-orthonormal target-frame transform."""
import ast, math, unittest
from pathlib import Path
SOURCE=Path(__file__).with_name("m9_native_abba_gate.py")
def load_transform():
    tree=ast.parse(SOURCE.read_text())
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="model_to_target_identity_ten")
    ns={"math":math};exec(compile(ast.Module(body=[node],type_ignores=[]),str(SOURCE),"exec"),ns)
    return ns[node.name]
transform=load_transform()
class GeneralFrameMomentTests(unittest.TestCase):
    def test_identity_axes_zero_origin_is_identity(self):
        m=[2.,3.,5.,7.,11.,13.,17.,19.,23.,29.]
        self.assertEqual(transform(m,[0.,0.,0.],[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]),m)
    def test_identity_axes_translation_matches_legacy_formula(self):
        m=[2.,3.,5.,7.,11.,13.,17.,19.,23.,29.];x,y,z=.5,-1.,2.
        got=transform(m,[x,y,z],[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
        M,Lx,Ly,Lz,xx,yy,zz,yz,xz,xy=m
        exp=[M,Lx-x*M,Ly-y*M,Lz-z*M,xx-2*x*Lx+x*x*M,
             yy-2*y*Ly+y*y*M,zz-2*z*Lz+z*z*M,
             yz-y*Lz-z*Ly+y*z*M,xz-x*Lz-z*Lx+x*z*M,xy-x*Ly-y*Lx+x*y*M]
        for a,b in zip(got,exp):self.assertAlmostEqual(a,b,places=12)
    def test_90_degree_z_rotation(self):
        m=[1.,2.,3.,4.,5.,6.,7.,8.,9.,10.]
        axes=[[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]]
        got=transform(m,[0.,0.,0.],axes)
        exp=[1.,3.,-2.,4.,6.,5.,7.,-9.,8.,-10.]
        for a,b in zip(got,exp):self.assertAlmostEqual(a,b,places=12)
    def test_translation_then_rotation(self):
        m=[1.,2.,3.,4.,5.,6.,7.,8.,9.,10.]
        axes=[[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]]
        got=transform(m,[1.,2.,3.],axes)
        centered=[1.,1.,1.]
        self.assertEqual(got[:4],[1.,centered[1],-centered[0],centered[2]])
    def test_rejects_nonorthonormal_axes(self):
        with self.assertRaisesRegex(ValueError,"NOT_ORTHONORMAL"):
            transform([1.]*10,[0.]*3,[[1.,0.,0.],[0.,2.,0.],[0.,0.,1.]])
    def test_rejects_reflection(self):
        with self.assertRaisesRegex(ValueError,"NOT_PROPER_ROTATION"):
            transform([1.]*10,[0.]*3,[[-1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
    def test_rejects_nonfinite_moments(self):
        m=[1.]*10;m[4]=float("nan")
        with self.assertRaisesRegex(ValueError,"MALFORMED_H8_FRAME"):
            transform(m,[0.]*3,[[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]])
if __name__=="__main__":unittest.main()

import unittest
import numpy as np
from m29_3_2_fd_math import tangent_basis,retract_unit,central_difference,compare_jacobians

class TangentFDErrorTests(unittest.TestCase):
    def setUp(self):
        self.q=np.array([.37,-.158,0.,-.761,.294,.294,.294,0.,0.,0.],dtype=float)
        self.q/=np.linalg.norm(self.q)

    def test_tangent_basis_shape_and_orthogonality(self):
        q,b=tangent_basis(self.q)
        self.assertEqual(b.shape,(10,9))
        self.assertLess(np.linalg.norm(b.T@q),1e-12)
        self.assertLess(np.linalg.norm(b.T@b-np.eye(9)),1e-12)

    def test_retraction_returns_unit_vector(self):
        q,b=tangent_basis(self.q)
        p=retract_unit(q,1e-4*b[:,3])
        self.assertAlmostEqual(np.linalg.norm(p),1.0,places=14)

    def test_retraction_plus_minus_are_distinct(self):
        q,b=tangent_basis(self.q)
        p=retract_unit(q,1e-4*b[:,0])
        m=retract_unit(q,-1e-4*b[:,0])
        self.assertGreater(np.linalg.norm(p-m),1e-5)

    def test_central_difference(self):
        h=1e-4
        p=np.arange(10,dtype=float)+1
        m=np.arange(10,dtype=float)-1
        np.testing.assert_allclose(central_difference(p,m,h),np.full(10,1/h))

    def test_compare_jacobians_zero_error(self):
        a=np.arange(90,dtype=float).reshape(10,9)
        r=compare_jacobians(a,a.copy())
        self.assertEqual(r["global_relative_frobenius_error"],0.0)
        self.assertEqual(r["max_column_relative_error"],0.0)

    def test_reject_bad_q(self):
        with self.assertRaises(ValueError): tangent_basis(np.zeros(10))
        with self.assertRaises(ValueError): tangent_basis(np.ones(9))

    def test_reject_bad_step_and_values(self):
        with self.assertRaises(ValueError): central_difference(np.ones(10),np.ones(10),0)
        with self.assertRaises(ValueError): central_difference(np.ones(9),np.ones(9),1e-4)

if __name__=="__main__": unittest.main()

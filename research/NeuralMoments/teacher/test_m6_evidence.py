"""Unit-test doubles only; patching native identity never proves real Cherchi."""
from fractions import Fraction
import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import numpy as np

from native_cherchi_teacher import native_c_to_polynomial_q, verify
from cherchi_single_request import evaluate_one, audit_same_call_attachment, sha256_file
from independent_reference import compare_predeclared_budget
from test_independent_reference import V, F, EXPECTED


class SyntheticMaterialProducer:
    """Fixture simulating the existing same-call producer's public API."""
    context_identity='synthetic-context'
    def __init__(self):
        from types import SimpleNamespace
        self.request=SimpleNamespace(material_density=2.0)
        self.fixed=np.array([7.0]+[0.0]*9)
        self.stage_seconds={}
        self.last=None
        self.attachment=None
        self.calls=0
        self.corrupt_attachment=False
        self.corrupt_moments=False
        self.on_call=None
    def __call__(self,native_c):
        self.calls+=1
        if self.on_call is not None: self.on_call()
        variable=np.array(EXPECTED,dtype=float)
        if self.corrupt_moments: variable[8]+=1.0
        mapped=dict(variable_raw_moments=variable,
           raw_moments=variable+self.fixed,
           moment_jacobian=np.zeros((10,10)), derivative_defined=True,
           geometry_hash='g',topology_hash='t',evaluation_map_identity=self.context_identity,
           boolean_backend_identity='synthetic-backend',derivative_identity='synthetic-derivative')
        self.last=dict(geometry_hash='g',topology_hash='t',
                       exact_vertices=tuple(tuple(Fraction(i) for i in row) for row in V),
                       faces=np.array(F,dtype=np.int64))
        self.attachment=dict(
            quadric_coefficients=tuple(native_c),
            raw_moments=mapped['raw_moments'].tolist(),
            variable_raw_moments=mapped['variable_raw_moments'].tolist(),
            moment_jacobian=mapped['moment_jacobian'].tolist(),
            material_proof={'kind':'synthetic'},
            variable_rational_vertices=[['0/1','0/1','0/1']],
            **{key:mapped[key] for key in ('derivative_defined','geometry_hash',
                'topology_hash','evaluation_map_identity','boolean_backend_identity',
                'derivative_identity')})
        return mapped
    def material(self,native_c):
        material=copy.deepcopy(self.attachment)
        if self.corrupt_attachment:
            material['variable_raw_moments'][8]+=1
        return material
    def validate_same_call_material(self,material,native_c,request):
        if request is not self.request or tuple(native_c)!=tuple(self.attachment['quadric_coefficients']):
            raise ValueError('WRONG_REQUEST_OR_NATIVE_C')
        # Simulate incumbent evaluator's frozen serialized packet validator.
        if material!=self.attachment:
            raise ValueError('SAME_CALL_MATERIAL_MISMATCH')


class TestM6SourceAndMaterialProof(unittest.TestCase):
    def setUp(self):
        self.tmp=TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.model=Path(self.tmp.name)/'model.obj';self.model.write_bytes(b'test only geometry')
        self.module=Path(self.tmp.name)/'module.so';self.module.write_bytes(b'test only binary')
        self.native_c=[1.0]+[0.0]*9
    def evaluate_fixture(self,producer):
        with patch('cherchi_single_request._authenticated_native',return_value=True):
            return evaluate_one(producer,self.native_c,
                model_path=self.model,native_module_path=self.module,
                geometry={'kind':'test only synthetic'},density=2.0,frame={'kind':'identity'},
                reference_absolute_tolerances=[1e-9]*10,split='train')
    def test_analytic_reference_plus_same_call_attachment(self):
        producer=SyntheticMaterialProducer()
        result=self.evaluate_fixture(producer)
        body=verify(result,expected_q=self.native_c,
                    expected_model_sha256=sha256_file(self.model),
                    expected_native_module_sha256=sha256_file(self.module))
        self.assertEqual(producer.calls,1)
        self.assertEqual(body['r_D'],list(map(float,EXPECTED)))
        self.assertEqual(body['r_F'][0],7.0)
        self.assertEqual(body['exact_proof']['independent_ten_moment_audit']['comparison']['maximum_absolute_error'],0)
        self.assertEqual(len(body['exact_proof']['same_call_attachment']['serialized_material_sha256']),64)
        self.assertIsNone(body['J_D'])
        self.assertEqual(body['split'],'excluded')
        self.assertIn('w2_independent_reference_seconds',body['stage_seconds'])
    def test_same_call_attachment_tampering_fails(self):
        producer=SyntheticMaterialProducer();producer.corrupt_attachment=True
        body=self.evaluate_fixture(producer)['payload']
        self.assertEqual(body['topology_status'],'FAILED')
        self.assertIn('SAME_CALL_MATERIAL_MISMATCH',body['failure_reason'])
        self.assertIsNone(body['r_D'])
    def test_numeric_material_reference_mismatch_fails(self):
        producer=SyntheticMaterialProducer();producer.corrupt_moments=True
        body=self.evaluate_fixture(producer)['payload']
        self.assertIn('INDEPENDENT_TEN_MOMENT_MISMATCH',body['failure_reason'])
        self.assertEqual(body['split'],'excluded')
    def test_file_mutated_during_call_fails(self):
        producer=SyntheticMaterialProducer()
        producer.on_call=lambda: self.module.write_bytes(b'test only binary CHANGED')
        body=self.evaluate_fixture(producer)['payload']
        self.assertIn('FROZEN_MODEL_OR_NATIVE_MODULE_CHANGED_DURING_CALL',body['failure_reason'])
    def test_missing_budget_fails_before_material_admission(self):
        producer=SyntheticMaterialProducer()
        with patch('cherchi_single_request._authenticated_native',return_value=True):
            record=evaluate_one(producer,self.native_c,model_path=self.model,
               native_module_path=self.module,geometry={},density=2.0,frame={})
        self.assertIn('PREDECLARED_TEN_MOMENT_ERROR_BUDGET_REQUIRED',record['payload']['failure_reason'])
        self.assertEqual(record['payload']['split'],'excluded')
    def test_negative_or_wrong_budget(self):
        with self.assertRaisesRegex(ValueError,'BUDGET_NONPOSITIVE'):
            compare_predeclared_budget(EXPECTED,EXPECTED,[-1]+[1.0]*9)
        report=compare_predeclared_budget(EXPECTED,[*EXPECTED[:8],EXPECTED[8]+1,*EXPECTED[9:]],
                                          [0.25]*10)
        self.assertFalse(report['within_tolerance'])
        self.assertEqual(report['maximum_normalized_error'],4.0)
    def test_w0_polynomial_vs_native_cross_terms(self):
        c=[1.0,0,0,0,0,0,0,1.5,-2,3]
        q=native_c_to_polynomial_q(c)
        self.assertEqual(q[:7],list(map(float,c[:7])))
        self.assertEqual(q[7:],[3,-4,6])


if __name__=='__main__':unittest.main()

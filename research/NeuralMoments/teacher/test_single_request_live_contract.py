import tempfile
import unittest
from pathlib import Path
from fractions import Fraction
import numpy as np
from native_cherchi_teacher import save, load
from independent_reference import integrate_exact_boundary
from cherchi_single_request import evaluate_one, sha256_file, audit_same_call_exact_boundary
from test_independent_reference import V,F,EXPECTED

class Mock:
    context_identity="fake-evaluation-map"
    fixed=np.array([7.0]+[0.0]*9)
    stage_seconds={}
    def __call__(self,q):
        self.stage_seconds['source']=0.001
        variable=np.array([3.0]+[0.0]*9)
        return dict(variable_raw_moments=variable,raw_moments=variable+self.fixed,
             derivative_defined=True,moment_jacobian=np.zeros((10,10)),
             geometry_hash="bound-g",topology_hash="bound-t",
             evaluation_map_identity=self.context_identity)

class TestSingleRequest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.model=Path(self.tmp.name)/'model.obj';self.model.write_bytes(b'mock closed model')
        self.native=Path(self.tmp.name)/'native.so';self.native.write_bytes(b'mock native bytes')
        self.q=[0.0]*10
    def run_one(self,evaluator=None,contract=None,split='excluded'):
        return evaluate_one(evaluator if evaluator is not None else Mock(),self.q,
           model_path=self.model,native_module_path=self.native,
           geometry={'kind':'fixture-only'},density=2,frame={'target':'identity'},
           derivative_contract=contract,split=split)
    def test_mock_retains_physical_moments_but_excludes_derivative(self):
        record=self.run_one(contract={'schema':'MomentContractV1','verified_neighborhood':True},split='train')
        p=record['payload']
        self.assertEqual(p['r_D'][0],3)
        self.assertEqual(p['r_F'][0],7)
        self.assertIsNone(p['J_D'])
        self.assertEqual(p['derivative_status'],'UNKNOWN')
        self.assertEqual(p['split'],'excluded')
        self.assertFalse(p['exact_proof']['native_cherchi'])
        self.assertEqual(p['exact_proof']['derivative_admission_reason'],'W0_VERIFIER_NOT_INTEGRATED')
    def test_failure_logged_and_reloaded(self):
        class Broken(Mock):
            def __call__(self,q): raise ValueError('native failed')
        record=self.run_one(Broken())
        self.assertEqual(record['payload']['topology_status'],'FAILED')
        self.assertIn('native failed',record['payload']['failure_reason'])
        path=Path(self.tmp.name)/'record.json';save(path,record)
        p=load(path,expected_q=self.q,expected_model_sha256=sha256_file(self.model),
               expected_native_module_sha256=sha256_file(self.native))
        self.assertEqual(p['derivative_status'],'INVALID')
    def test_independent_same_call_audit(self):
        from types import SimpleNamespace
        reference,proof=integrate_exact_boundary(V,F,2)
        producer=SimpleNamespace(last={'geometry_hash':'g','topology_hash':'t',
                'exact_vertices':[[Fraction(x) for x in row] for row in V],
                'faces':np.asarray(F,dtype=int)},
                request=SimpleNamespace(material_density=2))
        output={'geometry_hash':'g','topology_hash':'t',
                'variable_raw_moments':np.array(list(map(float,reference)))}
        checked=audit_same_call_exact_boundary(producer,output,2)
        self.assertEqual(checked['comparison']['maximum_absolute_error'],0)
        output['variable_raw_moments'][8]+=1
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_TEN_MOMENT_MISMATCH'):
            audit_same_call_exact_boundary(producer,output,2)
    def test_reject_stale_topology(self):
        from types import SimpleNamespace
        producer=SimpleNamespace(last={'geometry_hash':'g','topology_hash':'t'},
                                 request=SimpleNamespace(material_density=2))
        with self.assertRaisesRegex(ValueError,'STALE_OR_WRONG_BRANCH'):
            audit_same_call_exact_boundary(producer,{'geometry_hash':'g','topology_hash':'different'},2)
    def test_double_count_fails(self):
        class Double(Mock):
            def __call__(self,q):
                x=super().__call__(q);x['raw_moments']=x['variable_raw_moments'];return x
        record=self.run_one(Double())
        self.assertIn('DOUBLE_COUNT',record['payload']['failure_reason'])
        self.assertIsNone(record['payload']['r_D'])
    def test_resource_metadata_is_not_seconds(self):
        p=self.run_one()['payload']
        self.assertNotIn('w2_rss_process_hwm_before_bytes',p['stage_seconds'])
        self.assertFalse(p['exact_proof']['memory_measurement']['is_per_call_peak'])
        self.assertGreaterEqual(p['peak_rss_bytes'],0)

if __name__=='__main__':unittest.main()

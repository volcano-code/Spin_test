import json
import tempfile
import unittest
from pathlib import Path
from run_native_smoke import parse_spec,run

class TestNativeSmokePreflight(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.home=Path(self.tmp.name)
        self.model=self.home/'mock.obj';self.model.write_text('v 0 0 0\n')
        self.spec=self.home/'single.json'
        self.doc={'schema':'w2-one-cherchi-request-v1','model_path':str(self.model),
          'request':{},'evaluator_settings':{},'q':[0]*10,
          'geometry':{'kind':'test_only'},'frame':{'kind':'identity'}}
        self.dump()
    def dump(self):self.spec.write_text(json.dumps(self.doc))
    def test_preflight_parse(self):
        self.assertEqual(parse_spec(self.spec)['q'],[0.0]*10)
    def test_wrong_length_rejected(self):
        self.doc['q']=[0]*9;self.dump()
        with self.assertRaisesRegex(ValueError,'TEN_COMPONENTS_REQUIRED'): parse_spec(self.spec)
    def test_spec_forged_contract_rejected(self):
        self.doc['derivative_contract']={'verified_neighborhood':True};self.dump()
        with self.assertRaisesRegex(ValueError,'W0_DERIVATIVE'): parse_spec(self.spec)
    def test_preflight_failure_recorded_no_native(self):
        # Failure cause is intentionally environment-specific; no native claim.
        path=self.home/'failure.json'
        result=run(self.spec,path)
        self.assertEqual(result['status'],'FAILED_PREFLIGHT')
        self.assertFalse(result['training_admitted'])
        self.assertEqual(json.loads(path.read_text())['status'],'FAILED_PREFLIGHT')
        with self.assertRaisesRegex(FileExistsError,'REFUSE_OVERWRITE_EXISTING_EVIDENCE'):
            run(self.spec,path)

if __name__=='__main__':unittest.main()

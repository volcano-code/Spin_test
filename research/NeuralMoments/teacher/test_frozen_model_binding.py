"""Small exact-correspondence smoke; these OBJ fixtures are not Cherchi truth."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from frozen_model_binding import validate_model_binding
from native_cherchi_teacher import digest
from cherchi_single_request import sha256_file
from run_native_smoke import FROZEN_SOURCE_SHA, parse_spec, run
from test_independent_reference import V, F


def obj_text(v, f):
    return ('\n'.join('v '+ ' '.join(str(x) for x in row) for row in v)+ '\n'
            + '\n'.join('f '+ ' '.join(str(x+1) for x in row) for row in f)+'\n')


class TestFrozenObjCorrespondence(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.model=self.root/'closed.obj'
        self.model.write_text(obj_text(V,F),encoding='utf-8')
        self.request={'outer_vertices':V,'outer_faces':F,
                      'original_units_per_normalized_unit':1.0}
        self.spec=self.root/'spec.json'

    def check(self, binding=None, request=None, normalization=None):
        return validate_model_binding(self.model, request or self.request,
            binding or {'mode':'OBJ_IS_INPUT_NORMALIZED_OUTER_V1'}, normalization)

    def test_exact_ordered_geometry_matches(self):
        proof=self.check()
        self.assertEqual(proof['status'],'EXACT_BINARY64_ORDERED_OUTER_MESH_MATCH')
        self.assertEqual(proof['face_count'],12)
        self.assertEqual(proof['model_file_sha256'],sha256_file(self.model))

    def test_coordinate_mismatch_fail_closed(self):
        request=copy.deepcopy(self.request)
        request['outer_vertices'][0][0]=0.25
        with self.assertRaisesRegex(ValueError,'OUTER_VERTEX_BYTES_MISMATCH'):
            self.check(request=request)

    def test_stored_face_order_mismatch_fail_closed(self):
        request=copy.deepcopy(self.request)
        request['outer_faces'][0],request['outer_faces'][1] = request['outer_faces'][1],request['outer_faces'][0]
        with self.assertRaisesRegex(ValueError,'OUTER_FACE_BYTES_MISMATCH'):
            self.check(request=request)

    def test_closed_topology_required(self):
        self.model.write_text(obj_text(V,F[:-1]),encoding='utf-8')
        request=copy.deepcopy(self.request)
        request['outer_faces']=F[:-1]
        with self.assertRaisesRegex(ValueError,'OPEN_NONMANIFOLD'):
            self.check(request=request)

    def test_face_winding_rejected(self):
        bad=copy.deepcopy(F)
        bad[0]=bad[0][::-1]
        self.model.write_text(obj_text(V,bad),encoding='utf-8')
        request=copy.deepcopy(self.request)
        request['outer_faces']=bad
        with self.assertRaisesRegex(ValueError,'OPEN_NONMANIFOLD'):
            self.check(request=request)

    def test_duplicate_triangles_rejected(self):
        faces=F+[F[0]]
        self.model.write_text(obj_text(V,faces),encoding='utf-8')
        request=copy.deepcopy(self.request)
        request['outer_faces']=faces
        with self.assertRaisesRegex(ValueError,'OBJ_DUPLICATE_TRIANGLE'):
            self.check(request=request)

    def test_physical_to_normalized_exact_transform(self):
        origin=np.array([12.,-6.,3.])
        L=4.0
        original=np.asarray(V,dtype=float)
        physical=original*L+origin
        self.model.write_text(obj_text(physical,F),encoding='utf-8')
        request=copy.deepcopy(self.request)
        request['original_units_per_normalized_unit']=L
        proof=self.check({'mode':'OBJ_PHYSICAL_TO_INPUT_NORMALIZED_OUTER_V1'},
                         request=request,normalization={'origin':origin.tolist(),'L':L})
        self.assertEqual(proof['vertex_count'],8)
        self.assertEqual(proof['mode'],'OBJ_PHYSICAL_TO_INPUT_NORMALIZED_OUTER_V1')

    def test_wrong_affine_scale_rejected(self):
        request=copy.deepcopy(self.request)
        with self.assertRaisesRegex(ValueError,'REQUEST_NORMALIZATION_LENGTH_MISMATCH'):
            self.check({'mode':'OBJ_PHYSICAL_TO_INPUT_NORMALIZED_OUTER_V1'},
                       request=request,normalization={'origin':[0,0,0],'L':2})

    def test_unverified_mode_rejected(self):
        with self.assertRaisesRegex(ValueError,'MODEL_BINDING_MODE_REQUIRED'):
            self.check(binding={'mode':'OBJ_IS_INPUT_NORMALIZED_OUTER_V1','claim':'trusted'})

    def test_open_teapot_face_rejected_before_native(self):
        quad='v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf 1 2 3 4\n'
        self.model.write_text(quad,encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'OBJ_NOT_TRIANGULATED'):
            self.check()

    def test_relative_index_rejected(self):
        txt=obj_text(V,F).replace('f 1 3 2','f -8 -6 -7',1)
        self.model.write_text(txt,encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'OBJ_RELATIVE_OR_INVALID_FACE_INDEX'):
            self.check()

    def test_nonfinite_coordinate_rejected(self):
        txt=obj_text(V,F).replace('v 0 0 0','v nan 0 0',1)
        self.model.write_text(txt,encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'OBJ_NONFINITE_VERTEX'):
            self.check()

    def test_v3_spec_parses_to_verified_geometry_proof(self):
        doc={'schema':'w2-one-cherchi-request-v3',
             'source_sha':FROZEN_SOURCE_SHA,'model_path':str(self.model),
             'expected_model_sha256':sha256_file(self.model),
             'expected_native_module_sha256':'a'*64,
             'request':self.request,'evaluator_settings':{},
             'native_c':[1.0]+[0.0]*9,
             'expected_native_c_sha256':digest([1.0]+[0.0]*9),
             'reference_absolute_tolerances':[1e-10]*10,
             'model_geometry_binding':{'mode':'OBJ_IS_INPUT_NORMALIZED_OUTER_V1'},
             'geometry':{'kind':'fixture-not-cherchi'},
             'frame':{'kind':'identity'}}
        self.spec.write_text(json.dumps(doc),encoding='utf-8')
        parsed=parse_spec(self.spec)
        self.assertEqual(parsed['_verified_model_binding']['status'],
                         'EXACT_BINARY64_ORDERED_OUTER_MESH_MATCH')
        # Compiled project absent: preflight must fail, never synthesize truth.
        output=self.root/'failure-record.json'
        result=run(self.spec,output)
        self.assertEqual(result['status'],'FAILED_PREFLIGHT')
        self.assertIn('No module named',result['error'])
        self.assertFalse(result['training_admitted'])
        self.assertEqual(json.loads(output.read_text())['status'],'FAILED_PREFLIGHT')

    def test_v3_requires_explicit_binding(self):
        doc={'schema':'w2-one-cherchi-request-v3',
             'source_sha':FROZEN_SOURCE_SHA,'model_path':str(self.model),
             'expected_model_sha256':sha256_file(self.model),
             'expected_native_module_sha256':'a'*64,
             'request':self.request,'evaluator_settings':{},
             'native_c':[1.0]+[0.0]*9,
             'expected_native_c_sha256':digest([1.0]+[0.0]*9),
             'reference_absolute_tolerances':[1e-10]*10,
             'geometry':{},'frame':{}}
        self.spec.write_text(json.dumps(doc))
        with self.assertRaisesRegex(ValueError,'MODEL_BINDING_MODE_REQUIRED'):
            parse_spec(self.spec)

    def test_v2_deprecated_preflight_only(self):
        # Historical V2 can be parsed and reported, but cannot invoke native.
        doc={'schema':'w2-one-cherchi-request-v2',
             'source_sha':FROZEN_SOURCE_SHA,'model_path':str(self.model),
             'expected_model_sha256':sha256_file(self.model),
             'expected_native_module_sha256':'a'*64,
             'request':self.request,'evaluator_settings':{},
             'native_c':[1.0]+[0.0]*9,
             'expected_native_c_sha256':digest([1.0]+[0.0]*9),
             'reference_absolute_tolerances':[1e-10]*10,
             'geometry':{},'frame':{}}
        self.spec.write_text(json.dumps(doc))
        parsed=parse_spec(self.spec)
        self.assertNotIn('_verified_model_binding',parsed)
        output=self.root/'v2-blocked.json'
        status=run(self.spec,output)
        self.assertEqual(status['status'],'FAILED_PREFLIGHT')
        self.assertIn('NATIVE_REQUIRES_V3',status['error'])

if __name__=='__main__':unittest.main()

class TestRequestIndexTypeSafety(unittest.TestCase):
    def test_float_or_boolean_face_indices_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            model=Path(tmp)/'closed.obj'
            model.write_text(obj_text(V,F),encoding='utf-8')
            for value in (0.0,True):
                request={'outer_vertices':V,'outer_faces':copy.deepcopy(F)}
                request['outer_faces'][0][0]=value
                with self.assertRaisesRegex(ValueError,'INTEGER_INDICES_REQUIRED'):
                    validate_model_binding(model,request,
                        {'mode':'OBJ_IS_INPUT_NORMALIZED_OUTER_V1'})

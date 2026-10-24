"""M19 fresh-native, cross-build authority checks (NO new Cherchi execution)."""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
import types
import sys
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
import m19_real_h8e_profiler as p

LOCAL_SHA = dict(
    _make_it_stand='579128457145c22f6192df8bf7b75603f5cfc5b3c719008d39ef9e3fb40ae0bf',
    _cherchi_core_boolean='d6c2da58e4396c7ad279fb10457dd365783ba6f056983acf1353a73ce63e3351',
    _cherchi_rational_moments='ed05436e2796b190ddebb024f67318e2e88bdc46d96b01e9d7db71a6af080dca',
)
ARCHIVED_H8C=Path(os.environ.get('W1_M19_CROSSBUILD_H8C','/mnt/data/h8c-reference-39118951636.zip'))
ARCHIVED_H8E=Path(os.environ.get('W1_M19_CROSSBUILD_H8E','/mnt/data/h8e-25point-39121571756.zip'))


def original_formula(raw,origin,axes):
    vec=np.asarray(raw,dtype=np.float64)
    origin=np.asarray(origin,dtype=np.float64)
    axes=np.asarray(axes,dtype=np.float64)
    m=vec[0];first=vec[1:4]
    second=np.array([[vec[4],vec[9],vec[8]], [vec[9],vec[5],vec[7]],
                    [vec[8],vec[7],vec[6]]])
    shifted=second-np.outer(origin,first)-np.outer(first,origin)+m*np.outer(origin,origin)
    rot=axes.T
    target_first=rot@(first-m*origin)
    target_second=rot@shifted@rot.T
    return np.array([m,*target_first,target_second[0,0],target_second[1,1],
        target_second[2,2],target_second[1,2],target_second[0,2],target_second[0,1]])


class TestM25DifferentBinary(unittest.TestCase):
    def setUp(self):
        if not ARCHIVED_H8C.is_file():
            self.skipTest('genuine SHA256-pinned H8c archive not on testing host')
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.input=p.prepare_h8c_inputs(ARCHIVED_H8C,self.tmp.name)
        self.auth=p.cross_build_reference_authority(self.input,LOCAL_SHA)

    def test_archive_real_sha_and_expected_distinct_ELFs(self):
        self.assertEqual(self.auth['mode'],'FRESH_NATIVE_DIFFERENT_ELF_BINARY_SAME_PINNED_SOURCE')
        self.assertEqual(self.auth['archived_binary_sha256']['_make_it_stand'],
            'ad0c4fe3527954c611743dbbccb384cc1521909e8a39d68c3b7554b3a3919d40')
        self.assertEqual(self.auth['archived_binary_sha256']['_cherchi_core_boolean'],
            '3cc8bf789168752f8b921c160ca9937cdf0f61c845d3088760811b9e5a4596b7')
        self.assertNotEqual(self.auth['archived_binary_sha256']['_make_it_stand'],LOCAL_SHA['_make_it_stand'])
        self.assertFalse(self.auth['same_binary_as_archived'])
        self.assertFalse(self.auth['archived_jacobian_admitted'])
        self.assertIsNone(self.auth['cross_build_full_material_sha_identical'])

    def test_suppressing_provenance_forbidden(self):
        for bad in (dict(),{'_make_it_stand':'x'},dict(LOCAL_SHA,bogus='x')):
            with self.assertRaisesRegex(ValueError,'BINARY_PROVENANCE_INCOMPLETE'):
                p.cross_build_reference_authority(self.input,bad)

    def test_same_historical_binaries_must_use_default_strict(self):
        original=dict(LOCAL_SHA,
            _make_it_stand=self.auth['archived_binary_sha256']['_make_it_stand'],
            _cherchi_core_boolean=self.auth['archived_binary_sha256']['_cherchi_core_boolean'])
        with self.assertRaisesRegex(ValueError,'USE_STRICT_MODE'):
            p.cross_build_reference_authority(self.input,original)

    def test_tampering_reference_or_certificate_rejected(self):
        originals=dict(self.input)
        for name in (p.REFERENCE_MEMBER,p.CERT_MEMBER,p.REQUEST_MEMBER):
            src=originals[name]
            data=json.loads(src.read_text())
            data['schema']='FAKE' if 'schema' in data else 'FAKE'
            modified=Path(self.tmp.name)/(name.split('/')[-1]+'-bad.json')
            modified.write_text(json.dumps(data))
            self.input[name]=modified
            with self.assertRaisesRegex(ValueError,'ARCHIVED_AUTHORITY_INVALID'):
                p.cross_build_reference_authority(self.input,LOCAL_SHA)
            self.input[name]=src

    def test_unchanged_frozen_script(self):
        code=Path(p.H8E_SOURCE_REL)
        if code.exists():
            self.assertEqual(p.git_blob(code.read_bytes()),p.H8E_SOURCE_BLOB)
        self.assertEqual(p.run_native.__defaults__,None)
        self.assertEqual(p.run_native.__kwdefaults__['baseline_mode'],'strict')

    def test_real_h8e_first_point_moment_and_mesh_identity(self):
        if not ARCHIVED_H8E.is_file():
            self.skipTest('genuine 25-point H8e archive unavailable')
        with ZipFile(ARCHIVED_H8E) as z:
            point=json.loads(z.read('artifacts/h8e-jacobian-cols0-4-8/point-000.json'))
        req_json=json.loads(self.input[p.REQUEST_MEMBER].read_text())['request']
        req=types.SimpleNamespace(target_origin=req_json['target_origin'],
                                   target_axes=req_json['target_axes'])
        # The test substitutes only the frozen H8e pure-function origin frame;
        # no Boolean, source provenance or native solver is mocked as success.
        m=types.ModuleType('probe_h8_native_cherchi')
        m.initial_ellipsoid_q=lambda origin:np.asarray(self.auth['archived_q'])
        with patch.dict(sys.modules,{'probe_h8_native_cherchi':m}):
            result=p.cross_build_first_point_audit(
                self.auth,point,req,types.SimpleNamespace(model_to_target_raw_ten_moments=original_formula))
        self.assertEqual(result['status'],'PASS_HISTORICAL_TEN_MOMENT_ANCHOR_ONLY')
        self.assertLessEqual(result['max_abs_model_to_target_ten_error'],1e-10)
        self.assertEqual(result['first_point_vertex_count'],8455)
        self.assertEqual(result['first_point_triangle_count'],16910)
        self.assertFalse(result['historical_binary_sha_parity'])

    def test_changed_geometry_or_ten_moment_fails(self):
        if not ARCHIVED_H8E.is_file():self.skipTest('genuine H8e archive unavailable')
        with ZipFile(ARCHIVED_H8E) as z:
            point=json.loads(z.read('artifacts/h8e-jacobian-cols0-4-8/point-000.json'))
        req_json=json.loads(self.input[p.REQUEST_MEMBER].read_text())['request']
        req=types.SimpleNamespace(target_origin=req_json['target_origin'],target_axes=req_json['target_axes'])
        m=types.ModuleType('probe_h8_native_cherchi')
        m.initial_ellipsoid_q=lambda origin:np.asarray(self.auth['archived_q'])
        module=types.SimpleNamespace(model_to_target_raw_ten_moments=original_formula)
        with patch.dict(sys.modules,{'probe_h8_native_cherchi':m}):
            for altered,regex in (
                (dict(point,vertex_count=8_454),'MESH_COUNT_DIFFERENCE'),
                (dict(point,triangle_count=16_909),'MESH_COUNT_DIFFERENCE'),
                (dict(point,independent_variable_raw_moments=[9.]*10),'TEN_MOMENT_DIFFERENCE')
            ):
                with self.assertRaisesRegex(ValueError,regex):
                    p.cross_build_first_point_audit(self.auth,altered,req,module)
            broken=dict(self.auth,archived_q=[1.]*10)
            with self.assertRaisesRegex(ValueError,'REFERENCE_Q_OR_TEN_INVALID'):
                p.cross_build_first_point_audit(broken,point,req,module)


if __name__=='__main__': unittest.main()

"""M11 tests: mock receipts are intentionally NOT native Cherchi measurements."""
from __future__ import annotations

from copy import deepcopy
import gzip
from hashlib import sha256
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from m10_native_host_runner import archive_identity, NATIVE
from m11_native_evidence_gate import (ARCHIVE_SHA, REQUEST_SHA, SOURCE_BLOB,
    AUDIT_TRUE, MAX_MATERIAL_BYTES, _ledger, _load, _module_receipt, verify)
from m11_native_host_runner import run
from m9_native_abba_gate import certify_abba, ORDER, CHERCHI_ID


def write_json(path, value):
    Path(path).write_text(json.dumps(value,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


class SyntheticReceipt(unittest.TestCase):
    """Exercise integrity gates on synthetic artifacts, never claim real native."""
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='w1-m11-synthetic-')
        cls.root = Path(cls.temp.name)
        cls.m5,cls.m9 = cls.root/'m5',cls.root/'m9'
        cls.m5.mkdir();cls.m9.mkdir()
        module_inventory = {}
        for name in NATIVE:
            path=cls.root/(name+'.fake-test-ELF')
            path.write_bytes(b'M11_SYNTHETIC_NOT_AN_ELF_'+name.encode())
            raw=path.read_bytes()
            module_inventory[name]=dict(status='FOUND',path=str(path),
                                        sha256=sha256(raw).hexdigest(),bytes=len(raw))
        cls.modules=module_inventory
        checks={key:dict(status='PASS',details={'non_native_unit_test':True})
                for key in ('git','source','archive','memory','swap_disabled','native_abi_import')}
        checks['archive']['details']['zip_sha256']=ARCHIVE_SHA
        checks['native_modules']=dict(status='PASS',modules=module_inventory)
        cls.pref=dict(schema='w1-m10-native-host-preflight-v1',
                      state='READY_FOR_REAL_NATIVE_ABBA',checks=checks,blockers=[],
                      synthetic_unit_fixture_only=True)
        cls.pref_path=cls.root/'preflight.json';write_json(cls.pref_path,cls.pref)

        cls.q=[1.]+[0.]*9
        cls.ten=[1.]+[0.]*9
        cls.jac=[[1. if i==j else 0. for j in range(10)] for i in range(10)]
        cls.flags={k:True for k in AUDIT_TRUE}
        cls.backend=CHERCHI_ID+'synthetic-not-native'
        def ident(x):return sha256(json.dumps(x,sort_keys=True,separators=(',',':'),
                                        allow_nan=False).encode()).hexdigest()
        cls.faces=[[0,1,2]]*16910
        cls.vertices=[['0/1','0/1','0/1']]*8455
        source_vertices=[[0.,0.,0.],[1.,0.,0.],[0.,1.,0.],[0.,0.,1.]]
        source_faces=[[0,2,1],[0,1,3],[0,3,2],[1,2,3]]
        source_identity=ident(dict(vertices=source_vertices,faces=source_faces,coefficients=cls.q))
        geometry_identity=ident(dict(vertices=cls.vertices,faces=cls.faces))
        cls.material=dict(quadric_coefficients=cls.q,geometry_hash=geometry_identity,
            topology_hash='synthetic-topology',quadric_source_identity=source_identity,
            quadric_source_vertices=source_vertices,quadric_source_faces=source_faces,
            boolean_backend_identity=cls.backend,variable_raw_moments=cls.ten,
            moment_jacobian=cls.jac,raw_moments=cls.ten,
            variable_rational_vertices=cls.vertices,
            variable_faces=cls.faces,
            material_proof={'schema':'cherchi-same-call-material-v1',
                'exact_vertices':cls.vertices,
                'construction_records':[{}]*8455,
                'resolved_construction_records':[{}]*8455})
        cls.raw=json.dumps(cls.material,sort_keys=True,allow_nan=False).encode()
        cls.raw_sha=sha256(cls.raw).hexdigest()
        with gzip.open(cls.m5/'same-call-material.json.gz','wb') as f:f.write(cls.raw)
        def ledger(total=400, *, m5=False):
            audits = (
                'audit:same_call_material', 'audit:native_exact_rational_boundary',
                'audit:independent_fraction_ten',
                'audit:complete_material_snapshot' if m5 else
                'audit:exact_material_serialization')
            names = ['native:boolean', *audits]
            rows = [dict(name=name, status='PASS', inclusive_ns=50 if idx==0 else 5,
                         exclusive_ns=50 if idx==0 else 5)
                    for idx, name in enumerate(names)]
            total_exclusive=sum(row['exclusive_ns'] for row in rows)
            return dict(wall_ns=total, exclusive_ns=total_exclusive,
                        unattributed_ns=total-total_exclusive, all_returned=True,
                        exclusive_stages=rows,
                        stage_exclusive_totals_ns={row['name']:row['exclusive_ns'] for row in rows})
        cls.ledger=ledger
        cls.m5_report=dict(schema='w1-m5-native-h8-instrumented-sample-v1',
            scope='FRESH_H8_RECONSTRUCTED_SINGLE_Q_NOT_FULL_SOLVER',
            fresh_boolean_calls=1,full_solver_measured=False,paper_speed_qualified=False,
            input_request_sha256=REQUEST_SHA,archive_sha256=ARCHIVE_SHA,
            source_git_blob=SOURCE_BLOB,
            native_binary_sha256=module_inventory['_make_it_stand']['sha256'],
            cherchi_binary_sha256=module_inventory['_cherchi_core_boolean']['sha256'],
            gmp_binary_sha256=module_inventory['_cherchi_rational_moments']['sha256'],
            material_vertices=8455,material_faces=16910,ten_moment_max_scaled_error=0.,
            all_boundary_proof_flags=cls.flags,jacobian_shape=[10,10],q=cls.q,
            profiler=ledger(m5=True),sample_and_validation_wall_ns=200,geometry_hash=cls.material['geometry_hash'],
            topology_hash=cls.material['topology_hash'])
        write_json(cls.m5/'baseline-performance.json',cls.m5_report)
        cls.rows=[]
        for i,mode in enumerate(ORDER):
            row=dict(iteration=i,mode=mode,
                native_sha256=module_inventory['_make_it_stand']['sha256'],
                cherchi_sha256=module_inventory['_cherchi_core_boolean']['sha256'],
                gmp_sha256=module_inventory['_cherchi_rational_moments']['sha256'],
                setup_ns=12,eval_wall_ns=100,complete_validation_ns=200,
                material_sha256=cls.raw_sha,geometry_hash=cls.material['geometry_hash'],
                topology_hash=cls.material['topology_hash'],
                source_identity=cls.material['quadric_source_identity'],
                backend_identity=cls.backend,q=cls.q,ten=cls.ten,jacobian=cls.jac,
                vertices=8455,faces=16910,boundary_flags=cls.flags,
                same_call_passed=True,exact_geometry_audit_passed=True,
                independent_ten_max_scaled_error=0.,historical_ten_max_abs_error=0.,
                stage_ledger=ledger(200))
            cls.rows.append(row)
            write_json(cls.m9/f'point-{i:03d}-{mode}.json',row)
            with gzip.open(cls.m9/f'point-{i:03d}-{mode}.json.gz','wb') as f:f.write(cls.raw)
        cls.m9_report=dict(schema='w1-m9-native-h8c-abba-v1',
            scope='FOUR_REAL_H8C_SINGLE_Q_CHERCHI_MATERIALS_NOT_FULL_NEWTON',
            native_cherchi_calls=4,real_newton_solves=0,full_solver_speedup=None,
            paper_speed_qualified=False,archive_sha256=ARCHIVE_SHA,
            request_sha256=REQUEST_SHA,production_source_blob=SOURCE_BLOB,
            order=ORDER,module_binary_sha256=dict(
                native_sha256=module_inventory['_make_it_stand']['sha256'],
                cherchi_sha256=module_inventory['_cherchi_core_boolean']['sha256'],
                gmp_sha256=module_inventory['_cherchi_rational_moments']['sha256']),
            parity_and_timing=certify_abba(cls.rows),
            candidate_parser_caches_by_call=[{'misses':1},{'misses':1}],
            measurements=cls.rows)
        write_json(cls.m9/'baseline-performance.json',cls.m9_report)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def verify(self):return verify(self.pref_path,self.m5,self.m9)

    def edit(self,path,change,pattern):
        path=Path(path);raw=path.read_bytes();data=json.loads(raw);change(data)
        write_json(path,data)
        try:
            with self.assertRaisesRegex(ValueError,pattern):self.verify()
        finally:path.write_bytes(raw)

    def test_synthetic_reference_receipt_passes_integrity_only(self):
        result=self.verify()
        self.assertEqual(result['complete_native_ledger_rows'],5)
        self.assertEqual(result['reproduced_abba_single_q_ratio'],1.0)
        self.assertFalse(result['fresh_native_execution_independently_proven_by_receipt_alone'])
        self.assertIsNone(result['full_solver_speedup'])

    def test_reject_blocked_preflight(self):
        self.edit(self.pref_path,lambda x:x.update(state='BLOCKED'),
                  'M11_REAL_M10_PREFLIGHT_REQUIRED')

    def test_reject_drifted_original_module_binary(self):
        p=Path(self.modules['_make_it_stand']['path']);raw=p.read_bytes()
        p.write_bytes(raw+b'evil')
        try:
            with self.assertRaisesRegex(ValueError,'M11_MODULE_BINARY_MISMATCH'):
                self.verify()
        finally:p.write_bytes(raw)

    def test_reject_invalid_timer_sum(self):
        self.edit(self.m5/'baseline-performance.json',
                  lambda x:x['profiler'].update(unattributed_ns=1),'M11_LEDGER_DOES_NOT_CLOSE')

    def test_reject_missing_boolean_stage(self):
        self.edit(self.m5/'baseline-performance.json',
                  lambda x:x['profiler']['exclusive_stages'][0].update(name='native:source'),
                  'M11_NO_MEASURED_CHERCHI_BOOLEAN')

    def test_reject_source_construction_internal_digest(self):
        path=self.m9/'point-000-original.json.gz';raw=path.read_bytes()
        invalid=deepcopy(self.material);invalid['quadric_source_vertices'][0][0]=123.
        with gzip.open(path,'wb') as z:z.write(json.dumps(invalid).encode())
        try:
            with self.assertRaisesRegex(ValueError,'M11_M9_SERIALIZED_PACKET_SHA_DRIFT'):
                self.verify()
        finally:path.write_bytes(raw)

    def test_reject_unsourced_history_material(self):
        path=self.m9/'point-001-candidate.json.gz';raw=path.read_bytes()
        with gzip.open(path,'wb') as z:z.write(self.raw+b' ')
        try:
            with self.assertRaisesRegex(ValueError,'M11_M9_SERIALIZED_PACKET_SHA_DRIFT'):
                self.verify()
        finally:path.write_bytes(raw)

    def test_reject_changed_jacobian_and_archived_snapshot(self):
        self.edit(self.m9/'baseline-performance.json',
                  lambda x:x['measurements'][0]['jacobian'][0].__setitem__(0,2.),
                  'M9_ABBA_SCIENTIFIC_OUTPUT_DRIFT|M11_M9_REPORTED_ABBA_RATIO_DRIFT')

    def test_reject_per_point_report_tamper(self):
        self.edit(self.m9/'point-002-candidate.json',
                  lambda x:x.update(eval_wall_ns=1),'M11_M9_POINT_REPORT_MUTATION')

    def test_reject_m5_m9_cross_run_drift(self):
        path=self.m5/'same-call-material.json.gz';raw=path.read_bytes()
        invalid=deepcopy(self.material);invalid['moment_jacobian'][0][0]=2.
        with gzip.open(path,'wb') as z:z.write(json.dumps(invalid).encode())
        try:
            with self.assertRaisesRegex(ValueError,'M11_M5_M9_COMPLETE_MATERIAL_BYTES_NOT_EQUAL'):
                self.verify()
        finally:path.write_bytes(raw)

    def test_json_duplicate_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'dup.json';p.write_text('{"a":1,"a":2}')
            with self.assertRaisesRegex(ValueError,'M11_DUPLICATE_JSON_KEY'):_load(p)

    def test_m10_blocked_native_environment_never_launches_m11(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);archive=Path(os.environ.get('W1_M8_H8C_ARCHIVE',
                        '/mnt/data/h8c-reference-39118951636.zip'))
            with patch('m11_native_host_runner.m10.execute') as native_execute:
                result=run(root,archive,root/'output')
            native_execute.assert_not_called()
            self.assertEqual(result['state'],'BLOCKED')
            self.assertTrue((root/'output/failure.json').exists())
            self.assertFalse((root/'output/m11-native-validation-summary.json').exists())

    def test_m11_refuses_subsequent_false_success_after_m10_zero(self):
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/'result';ready=dict(state='READY_FOR_REAL_NATIVE_ABBA')
            mock_result=dict(schema='w1-m10-fresh-native-evaluation-complete-v1',
                scope='M5_SINGLE_Q_PLUS_M9_ABBA_NOT_FULL_NEWTON',fresh_boolean_calls=5,
                full_solver_speedup=None,paper_speed_qualified=False,
                jobs=[dict(stage='m5',returncode=0),dict(stage='m9',returncode=0)])
            with patch('m11_native_host_runner.m10.preflight',return_value=ready),\
                 patch('m11_native_host_runner.m10.execute',return_value=mock_result),\
                 patch('m11_native_host_runner.verify',side_effect=ValueError('M11_UNLINKED_MATERIAL')):
                with self.assertRaisesRegex(ValueError,'M11_UNLINKED_MATERIAL'):
                    run(Path(td),Path(td)/'archive.zip',output)
            self.assertEqual(json.loads((output/'failure.json').read_text())['status'],'FAILED_CLOSED')
            self.assertFalse((output/'m11-native-validation-summary.json').exists())

    def test_actual_immutable_h8c_archive_not_fake(self):
        p=Path(os.environ.get('W1_M8_H8C_ARCHIVE',
                 '/mnt/data/h8c-reference-39118951636.zip'))
        if not p.is_file():self.fail('real H8c source artifact is mandatory for M11 smoke')
        anchored=archive_identity(p)
        self.assertEqual(anchored['zip_sha256'],ARCHIVE_SHA)
        self.assertEqual(anchored['historical_material_vertices'],8455)
        self.assertFalse(anchored.get('is_original_author_cad',False))


if __name__=='__main__':unittest.main()

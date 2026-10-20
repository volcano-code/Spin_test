"""Stage15: integrity of partial native packets; all fixture runs are NOT native calls."""
from __future__ import annotations
import gzip
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SOURCE = Path(__file__).resolve().parents[1] / 'source'
sys.path.insert(0, str(SOURCE))
from h9_capture_inventory import inventory, inspect_side, sha_bytes
from h9_frozen_input_gate import validate_pair
from h9_same_call_capture import BACKEND, capture_same_call, promote_after_full_audit
import run_h9_native_serial as runner

ARCHIVE = os.environ.get('H9_EVIDENCE_ZIP')
CERT = os.environ.get('H9_CROSSING_CERTIFICATE')


def synthetic_packet(q):
    """Explicit in-memory structural fixture: NOT computed by Cherchi."""
    return {'quadric_coefficients':q, 'boolean_backend_identity':BACKEND+'inprocess',
            'material_proof':{'schema':'cherchi-same-call-material-v1'},
            'variable_faces':[[0,1,2],[0,3,1],[0,2,3],[1,3,2]],
            'variable_rational_vertices':[['0','0','0'],['1','0','0'],['0','1','0'],['0','0','1']]}


@unittest.skipUnless(ARCHIVE and CERT,'requires original GitHub Actions ZIP and exact stage4 certificate')
class H9Stage15ForensicInventory(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frozen = validate_pair(ARCHIVE,CERT)
        with zipfile.ZipFile(ARCHIVE) as z:
            cls.q0 = json.loads(z.read('artifacts/h8f-all81-points/report.json'))['target_q']
        cls.plan=cls.frozen['four_new_native_probe_plan']

    def new_fixture(self,root,index=0):
        p=self.plan[index]
        q=self.q0.copy();q[7]=p['c7']
        proof=capture_same_call(root,index=index,side=p['side'],coefficients=q,
                                material=synthetic_packet(q),backend_identity=BACKEND+'inprocess')
        return proof,p,q

    def test_absent_native_directory_is_not_claimed_as_execution(self):
        with tempfile.TemporaryDirectory() as td:
            a=inventory(ARCHIVE,CERT,Path(td)/'missing')
            self.assertEqual(a['status'],'NO_NATIVE_SIDE_DIRECTORY')
            self.assertEqual(a['new_cherchi_calls_verified_by_this_inventory'],0)
            self.assertFalse(a['newton_admitted'])

    def test_unverified_structural_packet_never_becomes_admitted(self):
        with tempfile.TemporaryDirectory() as td:
            self.new_fixture(Path(td))
            a=inventory(ARCHIVE,CERT,td)
            self.assertEqual(a['status'],'REVIEW_NOT_A_FRESH_CHERCHI_EXECUTION')
            self.assertEqual(a['unverified_complete_checkpoints'],1)
            self.assertEqual(a['promoted_complete_structural_pairs'],0)
            self.assertEqual(a['side_records'][0]['state'],'COMPLETE_UNVERIFIED_CHECKPOINT_NOT_QUALIFIED')
            self.assertEqual(a['new_cherchi_calls_verified_by_this_inventory'],0)

    def test_promoted_pair_is_structural_only_not_runtime_attestation(self):
        with tempfile.TemporaryDirectory() as td:
            proof,p,q=self.new_fixture(Path(td))
            meta={'index':0,'side':p['side'],'q':q,'c7':p['c7'],
                  'material_sha256':proof['archive_sha256'],
                  'native_geometry_valid':True,'newton_admitted':False,
                  'actual_accepted_step':False}
            promote_after_full_audit(td,proof,meta)  # synthetic *storage* fixture only
            a=inventory(ARCHIVE,CERT,td)
            self.assertEqual(a['promoted_complete_structural_pairs'],1)
            self.assertEqual(a['side_records'][0]['state'],
                             'COMPLETE_PROMOTED_PAIR_STRUCTURAL_ONLY_NOT_NATIVE_ATTESTED')
            self.assertEqual(a['new_cherchi_calls_verified_by_this_inventory'],0)

    def test_changed_unverified_packet_sha_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            self.new_fixture(Path(td))
            raw=Path(td)/'unverified-00-left-coarse.json.gz'
            with gzip.open(raw,'rt',encoding='utf8') as stream:
                payload=json.load(stream)
            payload['material_proof']['tampered']=True
            with gzip.open(raw,'wt',encoding='utf8') as stream:
                json.dump(payload,stream)
            a=inventory(ARCHIVE,CERT,td)
            self.assertEqual(a['status'],'REJECTED_ONE_OR_MORE_UNTRUSTED_CHECKPOINTS')
            self.assertIn('SHA_DRIFT',a['side_records'][0]['reason'])

    def test_genuine_historical_sample59_must_not_be_relabelled_as_new_sample0(self):
        with tempfile.TemporaryDirectory() as td,zipfile.ZipFile(ARCHIVE) as z:
            m=json.loads(gzip.decompress(z.read('artifacts/h8f-all81-points/point-059-material.json.gz')))
            q=m['quadric_coefficients']
            capture_same_call(td,index=0,side='left-coarse',coefficients=q,
                              material=m,backend_identity=m['boolean_backend_identity'])
            a=inventory(ARCHIVE,CERT,td)
            self.assertEqual(a['status'],'REJECTED_ONE_OR_MORE_UNTRUSTED_CHECKPOINTS')
            self.assertIn('IDENTITY_OR_SHA_DRIFT',a['side_records'][0]['reason'])
            self.assertEqual(a['new_cherchi_calls_verified_by_this_inventory'],0)

    def test_missing_forensic_metadata_never_counts_as_complete(self):
        with tempfile.TemporaryDirectory() as td:
            self.new_fixture(Path(td))
            (Path(td)/'unverified-00-left-coarse.json').unlink()
            a=inventory(ARCHIVE,CERT,td)
            self.assertEqual(a['side_records'][0]['state'],
                             'PARTIAL_UNVERIFIED_CHECKPOINT_NOT_QUALIFIED')
            self.assertEqual(a['unverified_complete_checkpoints'],0)

    def test_source_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            self.new_fixture(Path(td))
            raw=Path(td)/'unverified-00-left-coarse.json.gz'
            foreign=Path(td)/'foreign.gz';foreign.write_bytes(raw.read_bytes())
            raw.unlink();raw.symlink_to(foreign)
            a=inventory(ARCHIVE,CERT,td)
            self.assertEqual(a['status'],'REJECTED_ONE_OR_MORE_UNTRUSTED_CHECKPOINTS')
            self.assertIn('NONREGULAR_OR_SYMLINK_CHECKPOINT',a['side_records'][0]['reason'])

    def test_certificate_tamper_before_packet_inspection(self):
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'bad.json'
            data=json.loads(Path(CERT).read_text());data['newton_admitted']=True
            bad.write_text(json.dumps(data))
            with self.assertRaises(Exception):
                inventory(ARCHIVE,bad,td)

    def test_failed_probe_runs_inventory_and_preserves_original_failure(self):
        with tempfile.TemporaryDirectory() as td:
            output=Path(td)/'run'
            state={'status':'READY_TO_ATTEMPT_REAL_CHERCHI','blockers':[]}
            with patch.object(runner,'preflight',return_value=state),\
                 patch.object(runner,'capped_exec',return_value=17):
                code=runner.run_once(ARCHIVE,CERT,output)
            self.assertEqual(code,17)
            saved=json.loads((output/'run_status.json').read_text())
            self.assertEqual(saved['probe_exit_code'],17)
            self.assertEqual(saved['forensic_inventory_status'],'NO_NATIVE_SIDE_DIRECTORY')
            self.assertFalse(saved['newton_admitted'])
            self.assertEqual(saved['new_native_calls_verified'],0)
            self.assertTrue((output/'forensic-inventory.json').is_file())


if __name__=='__main__':unittest.main()

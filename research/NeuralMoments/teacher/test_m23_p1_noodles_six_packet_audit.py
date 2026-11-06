import json
import tempfile
import unittest
from pathlib import Path

from m23_p1_noodles_six_packet_audit import (
    PACKETS, SOURCE_MANIFEST_SHA, BACKEND_SHA, CHAIN_RELATIONS, audit
)

class TestM23P1(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.snapshot = {
            "frozen-inputs/author-rational/construction.json": json.dumps({
                "schema":"noodles-v7-exact-cgal-input-construction",
                "status":"EXACT_INPUT_CONSTRUCTED_NOT_OPTIMIZED",
                "manifest_sha":SOURCE_MANIFEST_SHA,"backend_sha":BACKEND_SHA,
                "csg_executed_current_process":96,
                "outputs":{k:{"sha":v[0],"faces":v[1]} for k,v in PACKETS.items()}
            }),
            "frozen-inputs/author-rational/exact-chain-summary.json": json.dumps({
                "all_three_chains_verified":True,"does_not_prove_native_solid_validity":True,
                "results":[{"name":k,"success":True,"nonzero_support_planes":0,
                    "exact_zero_area_triangles":0,"inputs":v} for k,v in CHAIN_RELATIONS.items()]
            }),
            "V7_STAGE_STATUS.json": json.dumps({
                "classification":"PAPER_PHOTO_GUIDED_RECONSTRUCTED_METHOD_VALIDATION_NOT_AUTHOR_CAD"
            }),
            "frozen-parts-v7c/manifest.json": json.dumps({"spec":{"author_original":False}})
        }
        self.snap=self.root/"snapshot.json"
        self.dag=self.root/"dag.json"
        self.pre=self.root/"pre.json"
        self.snap.write_text(json.dumps(self.snapshot))
        self.dag.write_text(json.dumps({
            "source_manifest_sha256":SOURCE_MANIFEST_SHA,"historical_backend_sha256":BACKEND_SHA,
            "expected_exact_backend_operations":96,"fixed_union_operations":92,"final_CSG_operations":4,
            "input_parts_total":94,"fixed_source_parts":93,
            "expected_historical_outputs":{k:{"sha256":v[0],"triangles":v[1]} for k,v in PACKETS.items()}
        }))
        self.pre.write_text(json.dumps({"historic_6_outputs_expected":[
            {"name":k,"sha256":v[0],"faces":v[1]} for k,v in PACKETS.items()
        ]}))

    def tearDown(self): self.tmp.cleanup()

    def run_audit(self):
        # The audit pins the actual historical snapshot SHA, so patch only the
        # constant in a test-local module clone for synthetic fixtures.
        import m23_p1_noodles_six_packet_audit as mod
        old=mod.SNAPSHOT_SHA256
        import hashlib
        mod.SNAPSHOT_SHA256=hashlib.sha256(self.snap.read_bytes()).hexdigest()
        try: return mod.audit(self.snap,self.dag,self.pre)
        finally: mod.SNAPSHOT_SHA256=old

    def test_six_identities_and_three_chain_receipts_match(self):
        r=self.run_audit()
        self.assertEqual(r["packet_count"],6)
        self.assertEqual(r["chain_relation_count"],3)
        self.assertFalse(r["raw_packet_payloads_in_snapshot"])
        self.assertFalse(r["native_solid_validity_proven_by_chain"])

    def test_packet_sha_mismatch_fails(self):
        d=json.loads(self.dag.read_text())
        d["expected_historical_outputs"]["fixed"]["sha256"]="0"*64
        self.dag.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,"DAG_PACKET_IDENTITY_MISMATCH"):
            self.run_audit()

    def test_chain_failure_fails(self):
        s=json.loads(self.snap.read_text())
        c=json.loads(s["frozen-inputs/author-rational/exact-chain-summary.json"])
        c["results"][0]["success"]=False
        s["frozen-inputs/author-rational/exact-chain-summary.json"]=json.dumps(c)
        self.snap.write_text(json.dumps(s))
        with self.assertRaisesRegex(ValueError,"CHAIN_RELATION_NOT_PASSED"):
            self.run_audit()

    def test_wrong_backend_fails(self):
        s=json.loads(self.snap.read_text())
        c=json.loads(s["frozen-inputs/author-rational/construction.json"])
        c["backend_sha"]="0"*64
        s["frozen-inputs/author-rational/construction.json"]=json.dumps(c)
        self.snap.write_text(json.dumps(s))
        with self.assertRaisesRegex(ValueError,"CGAL_BACKEND_IDENTITY"):
            self.run_audit()

    def test_missing_packet_name_fails(self):
        s=json.loads(self.snap.read_text())
        c=json.loads(s["frozen-inputs/author-rational/construction.json"])
        del c["outputs"]["initial"]
        s["frozen-inputs/author-rational/construction.json"]=json.dumps(c)
        self.snap.write_text(json.dumps(s))
        with self.assertRaisesRegex(ValueError,"SIX_PACKET_SET"):
            self.run_audit()

if __name__=="__main__": unittest.main(verbosity=2)

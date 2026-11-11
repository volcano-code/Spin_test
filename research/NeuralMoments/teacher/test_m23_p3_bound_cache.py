import copy
import json
from pathlib import Path
import tempfile
import unittest

from m23_p3_bound_cache import CacheRejected, canonical, digest, load, store


def context():
    return {
        "experiment_id": "synthetic-fixture", "evidence_kind": "SYNTHETIC_MOCK_ONLY",
        "node_id": "design", "operation": "difference", "serializer_id": "TEST_JSON_V1",
        "coordinate_policy": "TEST_ONLY",
        "source_manifest_sha256": "1" * 64, "source_audit_sha256": "2" * 64,
        "builder_source_sha256": "3" * 64, "adapter_sha256": "4" * 64,
        "backend_sha256": "5" * 64, "operand_sha256": ["6" * 64, "7" * 64],
    }


class BoundCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "cache"
        self.ctx = context()
        self.payload = b'{"fixture":"NOT_A_REAL_BOOLEAN_SOLID"}\n'

    def write(self):
        return store(self.root, self.ctx, self.payload)

    def node(self):
        return self.root / self.ctx["experiment_id"] / self.ctx["node_id"]

    def modify_receipt(self, edit):
        path = self.node() / "receipt.json"
        receipt = json.loads(path.read_text())
        edit(receipt)
        path.write_bytes(canonical(receipt))

    def test_roundtrip_and_unadmitted(self):
        rec = self.write()
        self.assertEqual(load(self.root, self.ctx), self.payload)
        self.assertIs(rec["training_admitted"], False)
        self.assertIsNone(rec["J_D"])

    def test_missing_node_is_not_a_hit(self):
        self.assertIsNone(load(self.root, self.ctx))

    def test_missing_receipt_rejected(self):
        self.write(); (self.node() / "receipt.json").unlink()
        with self.assertRaises(CacheRejected): load(self.root, self.ctx)

    def test_missing_payload_rejected(self):
        self.write(); (self.node() / "output.bin").unlink()
        with self.assertRaises(CacheRejected): load(self.root, self.ctx)

    def test_modified_payload_rejected(self):
        self.write(); (self.node() / "output.bin").write_bytes(b"different bytes")
        with self.assertRaisesRegex(CacheRejected, "OUTPUT_BYTES_MISMATCH"):
            load(self.root, self.ctx)

    def test_backend_change_rejected(self):
        self.write(); changed = copy.deepcopy(self.ctx); changed["backend_sha256"] = "f" * 64
        with self.assertRaisesRegex(CacheRejected, "CONTEXT_MISMATCH"):
            load(self.root, changed)

    def test_ordered_operands_swap_rejected(self):
        self.write(); changed = copy.deepcopy(self.ctx); changed["operand_sha256"].reverse()
        with self.assertRaises(CacheRejected): load(self.root, changed)

    def test_operand_content_change_rejected(self):
        self.write(); changed = copy.deepcopy(self.ctx); changed["operand_sha256"][0] = "a" * 64
        with self.assertRaises(CacheRejected): load(self.root, changed)

    def test_operation_change_rejected(self):
        self.write(); changed = copy.deepcopy(self.ctx); changed["operation"] = "union"
        with self.assertRaises(CacheRejected): load(self.root, changed)

    def test_each_source_and_policy_change_rejected(self):
        self.write()
        for field in ("source_manifest_sha256", "source_audit_sha256", "builder_source_sha256",
                      "adapter_sha256", "serializer_id", "coordinate_policy", "evidence_kind"):
            with self.subTest(field=field):
                changed = copy.deepcopy(self.ctx)
                changed[field] = ("e" * 64 if field.endswith("sha256") else
                                  "NATIVE_UNADMITTED" if field == "evidence_kind" else "CHANGED")
                with self.assertRaises(CacheRejected): load(self.root, changed)

    def test_no_overwrite(self):
        self.write()
        with self.assertRaisesRegex(CacheRejected, "REFUSE_EXISTING_NODE"):
            store(self.root, self.ctx, b"replacement")
        self.assertEqual(load(self.root, self.ctx), self.payload)

    def test_path_traversal_rejected(self):
        for field in ("node_id", "experiment_id"):
            with self.subTest(field=field):
                c = copy.deepcopy(self.ctx); c[field] = "../outside"
                with self.assertRaises(CacheRejected): store(self.root, c, self.payload)

    def test_symlink_output_rejected(self):
        self.write(); out = self.node() / "output.bin"; out.unlink()
        target = Path(self.tmp.name) / "target"; target.write_bytes(self.payload)
        out.symlink_to(target)
        with self.assertRaises(CacheRejected): load(self.root, self.ctx)

    def test_duplicate_json_keys_rejected(self):
        self.write(); path = self.node() / "receipt.json"
        path.write_bytes(path.read_bytes().rstrip()[:-1] + b',"schema":"duplicate"}')
        with self.assertRaisesRegex(CacheRejected, "DUPLICATE_JSON_KEY"):
            load(self.root, self.ctx)

    def test_admission_claim_rejected(self):
        self.write(); self.modify_receipt(lambda r: r.update(training_admitted=True))
        with self.assertRaisesRegex(CacheRejected, "UNSUPPORTED_ADMISSION_CLAIM"):
            load(self.root, self.ctx)

    def test_corrupt_context_digest_rejected(self):
        self.write(); self.modify_receipt(lambda r: r.update(context_sha256="0" * 64))
        with self.assertRaises(CacheRejected): load(self.root, self.ctx)

    def test_boolean_length_is_not_an_integer_count(self):
        self.payload = b"x"; self.write()
        self.modify_receipt(lambda r: r.update(output_size_bytes=True))
        with self.assertRaises(CacheRejected): load(self.root, self.ctx)

    def test_copy_node_also_requires_receipt(self):
        self.ctx["operation"] = "copy"; self.ctx["operand_sha256"] = ["6" * 64]
        self.ctx["node_id"] = "envelope"; self.write()
        self.assertEqual(load(self.root, self.ctx), self.payload)
        (self.node() / "receipt.json").unlink()
        with self.assertRaises(CacheRejected): load(self.root, self.ctx)

    def test_partial_directory_not_repaired(self):
        self.node().mkdir(parents=True)
        (self.node() / ".receipt.pending").write_text("unfinished")
        with self.assertRaises(CacheRejected): store(self.root, self.ctx, self.payload)
        with self.assertRaises(CacheRejected): load(self.root, self.ctx)

    def test_invalid_operation_arity(self):
        self.ctx["operand_sha256"] = ["6" * 64]
        with self.assertRaises(CacheRejected): store(self.root, self.ctx, self.payload)

    def test_experiment_namespace_isolated(self):
        self.write(); c = copy.deepcopy(self.ctx); c["experiment_id"] = "other-experiment"
        self.assertIsNone(load(self.root, c))

    def test_native_context_still_never_admits_training(self):
        self.ctx["evidence_kind"] = "NATIVE_UNADMITTED"
        self.assertIs(self.write()["training_admitted"], False)


if __name__ == "__main__":
    unittest.main()

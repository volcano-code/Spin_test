"""Actual original 94 Noodles v7 source parts, 188 SHA/size identities, no CSG."""
import json,hashlib,unittest,tempfile
from pathlib import Path
from unittest.mock import patch
import m18_noodles_full_source as m

class ActualFull94(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory()
  cls.path=Path(cls.tmp.name)/'real-reconstructed-parts'
  cls.ledger=m.regenerate(cls.path)
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def test_94(self):self.assertEqual(len(self.ledger),94)
 def test_188_and_sha(self):
  self.assertEqual(sum(len(list(self.path.glob('*-'+t+'.obj'))) for t in ('model','si')),188)
  for name,record in self.ledger.items():
   with self.subTest(name=name):
    self.assertEqual(m.sha(self.path/record['model_obj']),record['model_sha256'])
    self.assertEqual(m.sha(self.path/record['si_obj']),record['si_sha256'])
 def test_all_188_against_independent_original_corpus_digest(self):
  self.assertEqual(m.corpus_identity_sha(self.ledger),m.FULL_FROZEN_188_SHA_AND_94_COUNTS_DIGEST)
 def test_79_tubes_and_12_ribs(self):
  self.assertEqual(len([x for x in self.ledger if x.startswith('tube-')]),79)
  self.assertEqual(len([x for x in self.ledger if x.startswith('rib-')]),12)
 def test_93_fixed_one_envelope(self):
  self.assertEqual(len([x for x in self.ledger if x.endswith('-fixed')]),93)
  self.assertIn('outer-ellipsoid',self.ledger)
 def test_94_positive_single_closed_oriented_sources(self):
  for name,v in self.ledger.items():
   with self.subTest(name=name):
    self.assertTrue(v['watertight'] and v['winding_consistent'] and v['signed_volume']>0)
    self.assertEqual(v['components'],1)
 def test_original_frozen_seven_samples(self):
  for name,(model,si) in m.PREDECLARED_SAMPLES.items():
   self.assertEqual(self.ledger[name]['model_sha256'],model)
   self.assertEqual(self.ledger[name]['si_sha256'],si)
 def test_original_core_three_sources(self):
  for name,(model,si,nv,nf) in m.core.PINNED.items():
   x=self.ledger[name]
   self.assertEqual((x['model_sha256'],x['si_sha256'],x['vertices'],x['faces']),(model,si,nv,nf))
 def test_ledger_hash_changes_on_tamper(self):
  rows={n:dict(v) for n,v in self.ledger.items()}
  rows['tube-042-fixed']['si_sha256']='0'*64
  self.assertNotEqual(m.corpus_identity_sha(rows),m.FULL_FROZEN_188_SHA_AND_94_COUNTS_DIGEST)
 def test_wrong_original_manifest_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'manifest.json';p.write_text('{"parts":{}}')
   with self.assertRaisesRegex(ValueError,'HISTORICAL_MANIFEST_GIT_BLOB_CHANGED'):
    m.validate_against_original_manifest(self.ledger,p)
 def test_refuse_overwrite_original_reconstruction(self):
  with self.assertRaises(FileExistsError):m.regenerate(self.path)
 def test_no_native_or_csg_can_be_inferred_from_sha(self):
  self.assertTrue(len(self.ledger)==94)
  self.assertFalse(any('exact_boolean' in v or 'J_D' in v for v in self.ledger.values()))
 def test_188_digest_guard_not_swappable(self):
  self.assertNotEqual(m.FULL_FROZEN_188_SHA_AND_94_COUNTS_DIGEST,'0'*64)
 def test_frozen_generator_source_identity_list(self):
  self.assertEqual(m.FROZEN_GENERATOR_BLOBS['manifest'],'f476a8c3e87bd30ef186b24442f641c2602c32ec')
  self.assertEqual(m.FROZEN_GENERATOR_BLOBS['v7'],'73f78e76100139184318131eb7cff9816384bc7c')
 def test_wrong_receipt_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'construction.json';p.write_text('{}')
   with self.assertRaisesRegex(ValueError,'UNPINNED_CSG_RECEIPT'):
    m.core.inspect_csg(d,p)
 def test_absent_csg_packets_unavailable(self):
  for name in m.core.CSG_HASHES:
   self.assertFalse((self.path/(name+'-rational.json')).exists())

if __name__=='__main__':unittest.main()

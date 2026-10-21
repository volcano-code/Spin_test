"""Optional genuine upstream-generator integration (never a Cherchi call).

Set W2_M18_PINNED_SOURCE_SNAPSHOT to a folder containing the original W2 V7
upstream source/generator/*.py and frozen-parts-v7c/manifest.json. This source
snapshot must be independently byte-pinned to the GitHub main blobs.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,tempfile,unittest
import m18_noodles_full_source as m
import m17_core_sha_reconstruction as core

ROOT = Path(os.environ.get('W2_M18_PINNED_SOURCE_SNAPSHOT','/absent/w2-original-snapshot'))

class PinnedOriginalGenerator(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  source=ROOT/'source/generator/noodles_paper_geometry_v7.py'
  if not source.is_file():raise unittest.SkipTest('REAL_PINNED_ORIGINAL_GENERATOR_SNAPSHOT_NOT_SUPPLIED')
  for name,filename in (
      ('v7','noodles_paper_geometry_v7.py'),('v5','noodles_dense_v5_input.py'),
      ('v3','noodles_dense_v3_input.py'),('tube','noodles_input.py')):
   p=ROOT/'source/generator'/filename
   if not p.is_file() or core.blob(p)!=m.FROZEN_GENERATOR_BLOBS[name]:
    raise AssertionError('UNPINNED_UPSTREAM_GENERATOR:'+filename)
  cls.hist=ROOT/'frozen-parts-v7c/manifest.json'
  if core.blob(cls.hist)!=m.FROZEN_GENERATOR_BLOBS['manifest']:
   raise AssertionError('UNPINNED_HISTORY_SOURCE_MANIFEST')
  cls.tmp=tempfile.TemporaryDirectory()
  cls.out=Path(cls.tmp.name)/'upstream-original-execution'
  cmd=[sys.executable,str(source),'--output',str(cls.out)]
  env=dict(os.environ,PYTHONPATH=str(ROOT/'source/generator'))
  proc=subprocess.run(cmd,env=env,capture_output=True,text=True,timeout=90)
  if proc.returncode!=0:raise AssertionError('ORIGINAL_GENERATOR_FAILED:'+proc.stderr[-700:])
  cls.generated=json.loads((cls.out/'manifest.json').read_text())
 @classmethod
 def tearDownClass(cls):
  if hasattr(cls,'tmp'):cls.tmp.cleanup()
 def test_original_manifest_byte_identical(self):
  self.assertEqual((self.out/'manifest.json').read_bytes(),self.hist.read_bytes())
 def test_complete_94_replay_original_main_188_SHA(self):
  records={n:{'model_sha256':meta['sha256_model'],'si_sha256':meta['sha256_si'],
     'vertices':meta['audit']['vertices'],'faces':meta['audit']['triangles']}
    for n,meta in self.generated['parts'].items()}
  self.assertEqual(m.corpus_identity_sha(records),m.FULL_FROZEN_188_SHA_AND_94_COUNTS_DIGEST)
  self.assertEqual(m.validate_against_original_manifest(records,self.hist)['obj_hashes_verified'],188)
  for n,meta in self.generated['parts'].items():
   self.assertEqual(m.sha(self.out/meta['model_obj']),meta['sha256_model'])
   self.assertEqual(m.sha(self.out/meta['si_obj']),meta['sha256_si'])
 def test_historical_CSG_receipt_is_not_concrete_material(self):
  receipt=ROOT/'frozen-inputs/author-rational/construction.json'
  self.assertEqual(core.blob(receipt),core.ORIGINAL_CSG_BLOB)
  obj=json.loads(receipt.read_text())
  self.assertEqual(obj['manifest_sha'],m.sha(self.hist))
  self.assertEqual(obj['csg_executed_current_process'],96)
  checked=core.inspect_csg(self.out,receipt)
  self.assertFalse(checked['all_historical_CSG_PACKETS_present'] if 'all_historical_CSG_PACKETS_present' in checked else checked['all_historical_CSG_packets_present'])
  self.assertEqual(len(checked['missing_packets']),6)

if __name__=='__main__':unittest.main()

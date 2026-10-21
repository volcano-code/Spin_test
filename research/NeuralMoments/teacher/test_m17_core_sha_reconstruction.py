"""Exact frozen OBJ hashes from real Noodles source manifest; negative checks."""
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
import m17_core_sha_reconstruction as r

class M17Reproduce(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory()
  cls.folder=Path(cls.temp.name)
  cls.result=r.reproduce(cls.folder/'core')
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_3_parts(self):self.assertEqual(len(self.result),3)
 def test_6_original_sha(self):
  for name,(model,si,_,__) in r.PINNED.items():
   with self.subTest(name=name):
    self.assertEqual(r.sha(self.folder/'core'/(name+'-model.obj')),model)
    self.assertEqual(r.sha(self.folder/'core'/(name+'-si.obj')),si)
 def test_original_topology(self):
  for name,m in r.parts().items():
   self.assertTrue(m.is_watertight and m.is_winding_consistent and m.volume>0)
 def test_94_not_declared(self):self.assertEqual(len(self.result),3)
 def test_csg_not_called(self):self.assertEqual(len(r.CSG_HASHES),6)
 def test_hash_mismatch(self):
  with tempfile.TemporaryDirectory() as d:
   p=dict(r.PINNED);p['hub-fixed']=('0'*64,*r.PINNED['hub-fixed'][1:])
   with patch.object(r,'PINNED',p):
    with self.assertRaisesRegex(ValueError,'SOURCE_SHA_MISMATCH'):r.reproduce(Path(d)/'bad')
 def test_existing_folder_no_overwrite(self):
  with self.assertRaises(FileExistsError):r.reproduce(self.folder/'core')
 def test_fake_manifest_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   fake=Path(d)/'manifest.json';fake.write_text('{}')
   with self.assertRaisesRegex(ValueError,'UNPINNED_94_PART_MANIFEST'):r.inspect_full_source(d,fake)
 def test_fake_csg_blocked(self):
  with tempfile.TemporaryDirectory() as d:
   fake=Path(d)/'construction.json';fake.write_text('{}')
   with self.assertRaisesRegex(ValueError,'UNPINNED_CSG_RECEIPT'):r.inspect_csg(d,fake)

if __name__=='__main__':unittest.main()

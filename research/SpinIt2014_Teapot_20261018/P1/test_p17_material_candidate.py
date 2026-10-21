"""Regression tests for real packet custody and non-upgrading review claims."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np
import trimesh

from p17_material_candidate import (DENIED, MATERIAL_FILES, build_packet,
    validate_packet_files, verify_packet, vertex_link_audit, cross_surface_scan)


class NumericGeometryTests(unittest.TestCase):
    def test_pinched_vertex_rejected_despite_closed_edges(self):
        a=trimesh.creation.icosphere(subdivisions=0)
        b=a.copy();b.vertices+=np.array([4.,0.,0.])
        # Identify exactly one indexed vertex of otherwise disjoint closed meshes.
        vertices=np.vstack((a.vertices,b.vertices[1:]))
        remap=np.arange(len(b.vertices))+len(a.vertices)-1;remap[0]=0
        faces=np.vstack((a.faces,remap[b.faces]))
        pinched=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
        self.assertTrue(pinched.is_watertight)
        self.assertEqual(vertex_link_audit(pinched)['non_circular_vertex_links'],[0])

    def test_cross_scan_distinguishes_nested_and_crossing_surfaces(self):
        outer=trimesh.creation.box(extents=[2,2,2])
        inner=trimesh.creation.box(extents=[.5,.5,.5])
        self.assertEqual(cross_surface_scan(outer,inner)['witnesses'],[])
        inner.vertices+=np.array([1.,0.,0.])
        self.assertTrue(cross_surface_scan(outer,inner)['witnesses'])


class RealCandidatePacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p14=os.environ.get('W4_P17_P14_ROOT');p15=os.environ.get('W4_P17_P15_ROOT')
        if not p14 or not p15:
            raise unittest.SkipTest('Authentic P14/P15 archives required; CI forbids skips')
        cls.temp=tempfile.TemporaryDirectory(prefix='w4-p17-test-')
        cls.base=Path(cls.temp.name)
        cls.packet=cls.base/'authentic-packet'
        cls.p14=Path(p14);cls.p15=Path(p15)
        cls.manifest=build_packet(cls.p14,cls.p15,cls.packet)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def copy_packet(self):
        target=self.base/self._testMethodName
        shutil.copytree(self.packet,target)
        return target

    def rehash(self,packet,rel):
        path=packet/'manifest.json';data=json.loads(path.read_text())
        data['files_sha256'][rel]=hashlib.sha256((packet/rel).read_bytes()).hexdigest()
        path.write_text(json.dumps(data))

    def test_real_packet_replays_and_preserves_denials(self):
        result=verify_packet(self.packet)
        self.assertTrue(result['recomputed_geometry_and_physics'])
        for key in DENIED:
            self.assertIs(result[key],False)
            self.assertIs(self.manifest[key],False)
        self.assertTrue(self.manifest['selected_material_bytes_unchanged_from_P14_P15'])
        report=json.loads((self.packet/'all-six-boundary-certificates.json').read_text())
        self.assertEqual(len(report['cases']),6)
        self.assertTrue(all(c['certificate']['signed_triangle_residual_terms']==0
                            for c in report['cases']))
        self.assertEqual([c['certificate']['legacy_cyclic_multiset_residual_terms']
                          for c in report['cases']],[1280,1280,1248,1248,1248,1248])
        repair=json.loads((self.packet/'repair-budget-and-limitations.json').read_text())
        self.assertFalse(repair['exact_signed_volume_difference_native_minus_repaired']['is_zero'])
        self.assertEqual(repair['current_milestone_new_native_Boolean_calls'],0)

    def test_existing_outputs_never_overwritten(self):
        before=(self.packet/'manifest.json').read_bytes()
        with self.assertRaises(FileExistsError):
            build_packet(self.p14,self.p15,self.packet)
        self.assertEqual(before,(self.packet/'manifest.json').read_bytes())

    def test_material_tamper_rejected_even_after_manifest_rehash(self):
        p=self.copy_packet();rel=MATERIAL_FILES['M']
        (p/rel).write_bytes((p/rel).read_bytes()+b'\n# tampered\n')
        with self.assertRaisesRegex(ValueError,'PACKAGE_FILE_SHA'):
            validate_packet_files(p)
        self.rehash(p,rel)
        with self.assertRaisesRegex(ValueError,'SOURCE_DERIVED_HASH'):
            validate_packet_files(p)

    def test_wrong_candidate_D_rejected_even_when_rehashed(self):
        p=self.copy_packet();rel=MATERIAL_FILES['D']
        source=self.p14/'p14-cherchi-junction-study/translate_y_008/D_minus_shaft_cherchi.obj'
        shutil.copyfile(source,p/rel);self.rehash(p,rel)
        with self.assertRaisesRegex(ValueError,'SOURCE_DERIVED_HASH'):
            validate_packet_files(p)

    def test_boolean_and_forged_approval_rejected(self):
        for value in (True,0,None,'false'):
            with self.subTest(value=value):
                p=self.base/(self._testMethodName+'-'+str(type(value).__name__))
                shutil.copytree(self.packet,p)
                data=json.loads((p/'manifest.json').read_text())
                data['W0_physical_tip_or_FD_approved']=value
                (p/'manifest.json').write_text(json.dumps(data))
                with self.assertRaisesRegex(ValueError,'PREMATURE'):
                    validate_packet_files(p)

    def test_changed_scale_rejected_even_when_rehashed(self):
        p=self.copy_packet();rel='physical-case-proposal.json'
        data=json.loads((p/rel).read_text());data['scale_m_per_unit']=.15/3.15
        (p/rel).write_text(json.dumps(data));self.rehash(p,rel)
        with self.assertRaisesRegex(ValueError,'PHYSICAL_PROPOSAL_CHANGED'):
            validate_packet_files(p)

    def test_native_receipt_change_rejected_even_when_rehashed(self):
        p=self.copy_packet();rel='source/D-native-receipt.json'
        data=json.loads((p/rel).read_text());data['op']='union'
        (p/rel).write_text(json.dumps(data));self.rehash(p,rel)
        with self.assertRaisesRegex(ValueError,'SAME_CALL_RECEIPT_CHANGED'):
            validate_packet_files(p)

    def test_source_report_and_unsafe_path_rejected(self):
        p=self.copy_packet();rel='source/p15-report.json'
        (p/rel).write_bytes((p/rel).read_bytes()+b'\n');self.rehash(p,rel)
        with self.assertRaisesRegex(ValueError,'FROZEN_SOURCE_REPORT_CHANGED'):
            validate_packet_files(p)
        manifest=json.loads((self.packet/'manifest.json').read_text())
        manifest['files_sha256']['../outside']='0'*64
        (p/'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            validate_packet_files(p)


if __name__=='__main__': unittest.main()

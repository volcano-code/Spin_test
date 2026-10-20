"""W4 P13 tests: genuine saved Cherchi materials, shaft proposal, fail-closed gates."""
from pathlib import Path
import json
import tempfile
import unittest
import numpy as np
import trimesh
from p13_reconstructed_shaft_domain import (
    SHA, UNAPPROVED, SHIFT_PROOF, REF_SCALE, DENSITY_KG_M3,
    METERS_PER_REF_MODEL_UNIT, digest, round_spindle, prepare,
    verify_preflight, reference_transform, solid_angle_winding, native_raw_si
)
from p12_physical_case import raw_ten

HERE=Path(__file__).resolve().parent
INPUT_DIR=Path(__import__('os').environ.get('W4_P13_REAL_INPUT_DIR',str(HERE/'p12-real-input')))
FILES={
 'M':INPUT_DIR/'P10_Cherchi_Original_Yup.obj',
 'F':INPUT_DIR/'P11_F_Trial_Cherchi_Real_Subtraction.obj',
 'D':INPUT_DIR/'P11_D_Trial_Interior_Sphere.obj'
}
P11=INPUT_DIR/'P11_real_Cherchi_subtraction_audit.json'

class P13ReconstructedReferenceCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='w4_p13_test_')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.out=Path(cls.tmp.name)
        cls.report=prepare(FILES,P11,cls.out)

    def test_real_ch_erchi_identity_not_mock(self):
        for k,path in FILES.items():
            self.assertEqual(digest(path),SHA[k])
        self.assertEqual(digest(P11),SHA['P11'])
        self.assertEqual(self.report['source_real_Cherchi_M_F_D_sha256'],
                         {k:digest(path) for k,path in FILES.items()})

    def test_source_files_untouched_after_generation(self):
        # The setUpClass creation already ran; rehash original immutable bytes.
        self.assertEqual({k:digest(v) for k,v in FILES.items()},
                         {k:SHA[k] for k in FILES})

    def test_reference_shaft_true_closed_tip_and_pin(self):
        rod=round_spindle()
        self.assertEqual((len(rod.vertices),len(rod.faces)),(258,512))
        self.assertTrue(rod.is_volume)
        self.assertAlmostEqual(rod.bounds[0,2],0,places=12)
        self.assertAlmostEqual(rod.bounds[1,2],1.71,places=12)
        self.assertAlmostEqual(rod.volume,.018412200690303387,places=12)
        self.assertEqual(self.report['frozen_reconstruction_code_git_blobs']['teapot'],
                         'a80974d062c7fef2fe1852df677477e82a5adb54')

    def test_reference_proper_transform_and_bottom_clearance(self):
        src=trimesh.load_mesh(FILES['M'],process=False)
        m=reference_transform(src)
        self.assertTrue(m.is_volume)
        self.assertAlmostEqual(m.volume,src.volume*REF_SCALE**3,places=10)
        self.assertAlmostEqual(m.bounds[0,2],.15,places=12)
        self.assertAlmostEqual(self.report['teapot_bottom_height_m'],.00375)
        self.assertAlmostEqual(self.report['shaft_max_height_m'],.04275)
        self.assertAlmostEqual(self.report['shaft_min_tip_height_m'],0)

    def test_mass_is_different_from_previous_mujoco_and_P12_cases(self):
        self.assertAlmostEqual(self.report['mass_M_kg'],.031017469002406838,places=11)
        self.assertAlmostEqual(self.report['mass_shaft_kg'],.0003452287629431886,places=12)
        self.assertAlmostEqual(self.report['staged']['D']['proposed_mass_kg'],.000607056704168177,places=12)
        self.assertTrue(self.report['previous_15cm_P12_case_is_distinct'])
        self.assertTrue(self.report['old_0_25kg_MuJoCo_demonstration_is_distinct'])
        self.assertGreater(self.report['incompatible_P12_15cm_PLA_solid_mass_kg']/self.report['mass_M_kg'],100)

    def test_undoubled_ten_mass_moments_remain_additive_after_affine(self):
        r={k:raw_ten(trimesh.load_mesh(self.out/f'p13-{k.lower()}-reference.obj',process=False))
           for k in ('M','F','D')}
        self.assertLess(float(np.max(np.abs(r['M']-r['F']-r['D']))),1e-12)
        self.assertLess(self.report['M_F_D_ref_raw_ten_max_residual'],1e-12)
        physical={k:native_raw_si(trimesh.load_mesh(self.out/f'p13-{k.lower()}-reference.obj',process=False))
                  for k in ('M','F','D')}
        self.assertLess(float(np.max(np.abs(physical['M']-physical['F']-physical['D']))),1e-12)
        self.assertAlmostEqual(physical['M'][0],self.report['mass_M_kg'],places=12)
        self.assertAlmostEqual(METERS_PER_REF_MODEL_UNIT,.025)
        self.assertEqual(DENSITY_KG_M3,1200)

    def test_existing_D_positively_overlaps_mandatory_shaft(self):
        d=trimesh.load_mesh(self.out/'p13-d-reference.obj',process=False)
        rod=trimesh.load_mesh(self.out/'p13-shaft-reference.obj',process=False)
        self.assertAlmostEqual(solid_angle_winding(d,SHIFT_PROOF),1.,places=10)
        self.assertAlmostEqual(solid_angle_winding(rod,SHIFT_PROOF),1.,places=10)
        self.assertTrue(self.report['old_P11_D_not_compatible_with_new_fixed_shaft'])
        self.assertTrue(self.report['require_D_minus_shaft_before_optimization'])

    def test_prohibit_W0_or_optimizer_promotion(self):
        self.assertFalse(any(self.report[key] is not False for key in UNAPPROVED))
        self.assertFalse(self.report['native_Cherchi_reference_union_completed'])
        j=json.loads((self.out/'p13-preflight.json').read_text())
        j['W0_fixed_F_design_D_admitted']=True
        with tempfile.TemporaryDirectory() as dest:
            tampered=Path(dest)/'tampered.json'
            tampered.write_text(json.dumps(j))
            with self.assertRaisesRegex(ValueError,'PREMATURE_APPROVAL'):
                verify_preflight(tampered,self.out)

    def test_staged_mesh_sha_tamper_fails_closed(self):
        with tempfile.TemporaryDirectory() as dest:
            dest=Path(dest)
            for key in ('M','F','D','shaft'):
                p=self.out/f'p13-{key.lower()}-reference.obj'
                (dest/p.name).write_bytes(p.read_bytes())
            candidate=dest/'p13-shaft-reference.obj'
            candidate.write_bytes(candidate.read_bytes()+b'\n# mutated\n')
            with self.assertRaisesRegex(ValueError,'STAGED_MESH_TAMPER_shaft'):
                verify_preflight(self.out/'p13-preflight.json',dest)

    def test_reject_fake_native_material_P11_report(self):
        with tempfile.TemporaryDirectory() as dest:
            bad=Path(dest)/'bad.json'
            bad.write_bytes(P11.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'P11_REPORT_HASH_MISMATCH'):
                prepare(FILES,bad,Path(dest)/'forbidden')

    def test_reject_forged_real_Cherchi_source(self):
        with tempfile.TemporaryDirectory() as dest:
            bad=Path(dest)/'changed.obj'
            bad.write_bytes(FILES['M'].read_bytes()+b'\n# unverified change\n')
            with self.assertRaisesRegex(ValueError,'M_HASH_MISMATCH'):
                prepare({**FILES,'M':bad},P11,Path(dest)/'forbidden')

    def test_failed_native_cli_logs_are_preserved(self):
        from p13_reconstructed_shaft_domain import _native
        with tempfile.TemporaryDirectory() as td:
            d=Path(td)
            fake=d/'fake-native';fake.write_text('#!/bin/sh\nexit 0\n');fake.chmod(0o755)
            out=d/'not-produced.obj'
            with self.assertRaisesRegex(RuntimeError,'CHERCHI_NATIVE_UNION_NOT_COMPLETED'):
                _native(fake,'union',
                        [self.out/'p13-m-reference.obj',
                         self.out/'p13-shaft-reference.obj'],out,5)
            record=json.loads((d/'not-produced.native-call.json').read_text())
            self.assertEqual(record['exit'],0)
            self.assertFalse(record['native_output_exists'])
            self.assertFalse(out.exists())

if __name__=='__main__': unittest.main()

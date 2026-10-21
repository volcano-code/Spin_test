"""Independent adversarial review of the committed, real P17 material packet.

The mutations preserve the manifest's self-consistent hashes. Acceptance must
therefore depend on frozen provenance, mandatory evidence, and actual replay,
not on an attacker-controlled checksum list. All mutations use temporary copies.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from p17_material_candidate import validate_packet_files, verify_packet


class IndependentPacketReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path(os.environ.get(
            'W4_P17_PACKET', str(Path(__file__).parent / 'P17_material_case')))
        if not (cls.source / 'manifest.json').is_file():
            raise AssertionError('The committed authentic P17 packet is required; no skipped review')
        validate_packet_files(cls.source)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='w4-p17-independent-review-')
        self.root = Path(self.temp.name)
        self.packet = self.root / 'packet'
        shutil.copytree(self.source, self.packet)

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self):
        return json.loads((self.packet / 'manifest.json').read_text())

    def save_manifest(self, value):
        (self.packet / 'manifest.json').write_text(json.dumps(value), encoding='utf-8')

    def change_json_and_rehash(self, relative, change):
        path = self.packet / relative
        value = json.loads(path.read_text())
        change(value)
        path.write_text(json.dumps(value), encoding='utf-8')
        self.rehash(relative)

    def rehash(self, relative):
        manifest = self.manifest()
        manifest['files_sha256'][relative] = hashlib.sha256(
            (self.packet / relative).read_bytes()).hexdigest()
        self.save_manifest(manifest)

    def test_material_mapping_cannot_redirect_downstream_consumers(self):
        manifest = self.manifest()
        manifest['materials'] = {
            'M': '../../unrelated.obj',
            'F': 'source/native-F.obj',
            'D': 'material/M_repaired_outer.obj',
        }
        self.save_manifest(manifest)
        with self.assertRaises(ValueError):
            validate_packet_files(self.packet)

    def test_native_commit_and_archive_runs_are_pinned_independently(self):
        for key, replacement in (
                ('native_cherchi_commit', '0' * 40),
                ('source_P14_run', 1),
                ('source_P15_run', 1)):
            with self.subTest(field=key):
                manifest = json.loads((self.source / 'manifest.json').read_text())
                manifest[key] = replacement
                self.save_manifest(manifest)
                with self.assertRaises(ValueError):
                    validate_packet_files(self.packet)

    def test_evidence_cannot_be_removed_with_its_manifest_entry(self):
        manifest = self.manifest()
        for relative in ('numeric-geometry-preflight.json',
                         'repair-budget-and-limitations.json',
                         'all-six-boundary-certificates.json', 'physical-table.csv'):
            (self.packet / relative).unlink()
            del manifest['files_sha256'][relative]
        self.save_manifest(manifest)
        with self.assertRaises(ValueError):
            validate_packet_files(self.packet)

    def test_material_directory_symlink_cannot_externalize_packet(self):
        outside = self.root / 'outside-material'
        shutil.move(str(self.packet / 'material'), outside)
        (self.packet / 'material').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            validate_packet_files(self.packet)

    def test_numeric_claim_cannot_be_promoted_after_rehash(self):
        self.change_json_and_rehash(
            'numeric-geometry-preflight.json',
            lambda j: j.update(full_exact_solid_partition_certified=True))
        with self.assertRaises(ValueError):
            verify_packet(self.packet)

    def test_numeric_report_boolean_is_not_integer_zero(self):
        self.change_json_and_rehash(
            'numeric-geometry-preflight.json',
            lambda j: j.update(full_exact_solid_partition_certified=0))
        with self.assertRaises(ValueError):
            verify_packet(self.packet)

    def test_microweld_exact_nonidentity_cannot_be_erased(self):
        def forge(value):
            value['exact_signed_volume_difference_native_minus_repaired'] = {
                'numerator': '0', 'denominator': '1',
                'decimal_projection': 0.0, 'is_zero': True,
            }
        self.change_json_and_rehash('repair-budget-and-limitations.json', forge)
        with self.assertRaises(ValueError):
            verify_packet(self.packet)

    def test_published_csv_must_match_recomputed_physics(self):
        relative = 'physical-table.csv'
        (self.packet / relative).write_text('material,mass_kg\nM,999\n', encoding='utf-8')
        self.rehash(relative)
        with self.assertRaises(ValueError):
            verify_packet(self.packet)

    def test_all_six_evidence_cannot_be_replaced_by_self_consistent_digest(self):
        def forge(value):
            value['cases'][0]['certificate']['signed_triangle_residual_terms'] = 999
        self.change_json_and_rehash('all-six-boundary-certificates.json', forge)
        with self.assertRaises(ValueError):
            verify_packet(self.packet)

    def test_selected_boundary_denial_keeps_boolean_type(self):
        def forge(value):
            value['scientific_flags']['W2_teacher_training_allowed'] = 0
        self.change_json_and_rehash('selected-boundary-certificate.json', forge)
        with self.assertRaises(ValueError):
            verify_packet(self.packet)

    def test_physical_denial_keeps_boolean_type(self):
        self.change_json_and_rehash(
            'physical-properties.json', lambda j: j.update(W2_teacher_training_allowed=0))
        with self.assertRaises(ValueError):
            verify_packet(self.packet)

    def test_exact_moment_fact_keeps_boolean_type(self):
        self.change_json_and_rehash(
            'exact-ten-moment-partition.json',
            lambda j: j.update(saved_binary64_raw_ten_additivity_exact=1))
        with self.assertRaises(ValueError):
            verify_packet(self.packet)

    def test_lapack_eigenvalue_last_bit_is_allowed(self):
        def roundoff(value):
            eigenvalues = value['materials']['M']['principal_inertia_kg_m2']
            eigenvalues[0] = math.nextafter(eigenvalues[0], math.inf)
        self.change_json_and_rehash('physical-properties.json', roundoff)
        result = verify_packet(self.packet)
        self.assertTrue(result['recomputed_geometry_and_physics'])
        self.assertIs(result['W0_physical_tip_or_FD_approved'], False)

    def test_exact_fraction_projected_mass_is_not_given_lapack_tolerance(self):
        def changed_mass(value):
            material = value['materials']['M']
            material['mass_kg'] = math.nextafter(material['mass_kg'], math.inf)
        self.change_json_and_rehash('physical-properties.json', changed_mass)
        with self.assertRaises(ValueError):
            verify_packet(self.packet)


if __name__ == '__main__':
    unittest.main()

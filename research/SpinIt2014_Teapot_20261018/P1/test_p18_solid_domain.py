"""Integration of exact saved-solid proof with a real protected-shaft failure."""
from copy import deepcopy
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from p18_solid_domain import (audit_packet,check_report_replay,integer_lift,
    P17_MANIFEST_SHA256,P17_COMMIT)


class P18RealProofIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base=Path(__file__).parent
        cls.packet=Path(os.environ.get('W4_P18_CASE_ROOT',base/'P17_material_case'))
        cls.replayed=audit_packet(cls.packet)
        cls.saved=json.loads((base/'P18_EXACT_SOLID_AND_SHAFT_REPORT.json').read_text())

    def test_real_committed_proof_replays_completely(self):
        result=check_report_replay(self.saved,self.replayed)
        self.assertEqual(result['status'],'P18_EXACT_PROOF_REPLAY_MATCH')
        self.assertIs(result['scientific_admission'],False)

    def test_real_saved_solids_partition_but_original_shaft_protection_fails(self):
        report=self.replayed
        self.assertEqual(report['source_P17_commit'],P17_COMMIT)
        self.assertEqual(hashlib.sha256((self.packet/'manifest.json').read_bytes()).hexdigest(),P17_MANIFEST_SHA256)
        self.assertIs(report['saved_repaired_solid_partition_certified'],True)
        self.assertIs(report['fixed_and_design_have_no_positive_volume_overlap'],True)
        self.assertIs(report['positive_volume_design_shaft_overlap_proved'],True)
        self.assertIs(report['shaft_excluded_from_design_domain'],False)
        self.assertIs(report['optimization_admitted'],False)
        self.assertEqual(report['shaft_domain_audit']['strict_intruding_face_count'],283)
        self.assertEqual(report['shaft_domain_audit']['strict_intruding_vertex_count'],74)
        self.assertEqual(report['shaft_domain_audit']['design_triangles_exactly_processed'],640)
        self.assertTrue(all(flag is False for flag in report['scientific_flags'].values()))

    def test_all_saved_surface_adjacent_candidates_are_accounted_for(self):
        for name,report in self.replayed['exact_surface_audits'].items():
            with self.subTest(name=name):
                coverage=report['coverage']
                self.assertEqual(coverage['adjacent_candidates_excluded'],0)
                self.assertEqual(coverage['aabb_candidate_pairs'],
                    coverage['exact_noncoplanar_shared_edge_theorem_checks']+
                    coverage['exact_triangle_intersection_checks'])
                self.assertEqual(report['forbidden_intersection_pair_count'],0)
                self.assertIs(report['exact_embedded_closed_oriented_2manifold'],True)

    def test_gap_and_core_are_proofs_with_different_scopes(self):
        report=self.replayed
        gap=report['cavity_ball_and_clearance_certificate']['cavity_to_outer_clearance_lower_bound_reference']
        self.assertEqual(Fraction(int(gap['numerator']),int(gap['denominator'])),Fraction(161541897,500000000))
        self.assertIs(report['conservative_axis_core_excluded_from_design_domain'],True)
        self.assertIs(report['scientific_flags']['full_original_shaft_contained_in_fixed_material'],False)
        self.assertIs(report['scientific_flags']['printability_or_strength_certified'],False)

    def test_promoting_scientific_or_shaft_flags_is_rejected(self):
        for field in ('optimization_admitted','training_admitted','shaft_excluded_from_design_domain'):
            changed=deepcopy(self.saved)
            changed[field]=True
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'DIFFERS'):
                check_report_replay(changed,self.replayed)
        changed=deepcopy(self.saved)
        changed['positive_volume_design_shaft_overlap_proved']=False
        with self.assertRaisesRegex(ValueError,'DIFFERS'):
            check_report_replay(changed,self.replayed)

    def test_boolean_integer_substitution_and_missing_evidence_are_rejected(self):
        for field in ('saved_repaired_solid_partition_certified','optimization_admitted'):
            changed=deepcopy(self.saved)
            changed[field]=int(changed[field])
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'DIFFERS'):
                check_report_replay(changed,self.replayed)
        changed=deepcopy(self.saved)
        del changed['shaft_domain_audit']['strict_intrusion_witnesses']
        with self.assertRaisesRegex(ValueError,'DIFFERS'):
            check_report_replay(changed,self.replayed)

    def test_only_runtime_timings_are_excluded_from_replay_comparison(self):
        changed=deepcopy(self.saved)
        changed['audit_elapsed_seconds']=12345.5
        changed['exact_surface_audits']['D']['elapsed_seconds']=2.5
        check_report_replay(changed,self.replayed)
        changed['cavity_ball_and_clearance_certificate']['cavity_to_outer_clearance_lower_bound_reference']['numerator']='0'
        with self.assertRaisesRegex(ValueError,'DIFFERS'):
            check_report_replay(changed,self.replayed)

    def test_changed_source_manifest_rejected_before_missing_material_can_be_used(self):
        with tempfile.TemporaryDirectory() as temp:
            packet=Path(temp)
            source=json.loads((self.packet/'manifest.json').read_text())
            source['saved_binary64_oriented_boundary_identity_certified']=False
            (packet/'manifest.json').write_text(json.dumps(source))
            with self.assertRaisesRegex(ValueError,'IMMUTABLE_P17_MANIFEST'):
                audit_packet(packet)

    def test_arbitrary_rational_queries_are_lifted_without_rounding(self):
        points=((Fraction(1,3),Fraction(1,7),Fraction(1,11)),
                (Fraction(2,5),Fraction(1,2**90),Fraction(-3,17)))
        lifted,scale=integer_lift(points)
        self.assertEqual(tuple(tuple(Fraction(x,scale) for x in p) for p in lifted),points)


if __name__=='__main__':
    unittest.main()

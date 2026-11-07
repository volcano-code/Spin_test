"""Synthetic contract tests for the W3 M21.5B derived JSON auditor.

These fixtures do NOT represent genuine Cherchi native samples.
"""
import copy
from fractions import Fraction as F
import json
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import w3_m21_5b_audit as verifier


def token(f):
    f=F(f)
    return str(f.numerator)+'/'+str(f.denominator)


def fixture():
    c7 = [F(0), F(1, 2), F(0), F(1, 2), F(1, 4), F(1, 4)]
    samples=[]
    for stem,x in zip(verifier.STEMS,c7):
        rows=[]
        for name, (edge, face) in verifier.CASES.items():
            rows.append(dict(label=name, design_edge=list(edge), source_plane=list(face),
                d='-2/1',d_prime='0/1',d_prime_normal='0/1',d_prime_line='0/1',
                numerator=token(-2*x),numerator_prime='-2/1',
                numerator_prime_normal='0/1',numerator_prime_anchor_minus_line='-2/1',
                t=token(x),t_prime='1/1',t_prime_numerator='1/1',t_prime_denominator='0/1',
                t_prime_normal_net='0/1',t_prime_plane_anchor='1/1',t_prime_line_motion='0/1',
                abs_d='2/1',abs_d_prime_over_d='0/1',abs_t_prime='1/1',
                incidence_squared='1/4',incidence_approx=0.5,
                position=[token(x),'0/1','0/1'],velocity=['1/1','0/1','0/1'],
                speed_squared='1/1',speed_approx=1.0,reference_position_velocity_exact_match=True))
        samples.append(dict(stem=stem,c7=token(x),material_sha256='a'*64,
                            attachment_sha256='b'*64,constructions=rows))
    intervals=[]
    for side, label, a,b in verifier.INTERVALS:
        h=c7[b]-c7[a]
        intervals.append(dict(side=side,interval=label,from_stem=verifier.STEMS[a],
                              to_stem=verifier.STEMS[b],features={name:dict(
                delta_c7=token(h),position_secant=['1/1','0/1','0/1'],
                endpoint_average_velocity=['1/1','0/1','0/1'],
                signed_residual=['0/1','0/1','0/1'],
                max_abs_residual='0/1',residual_norm_approx=0.0,
                relative_residual_approx=0.0) for name in verifier.LABELS}))
    return dict(schema='heart-h9-m21-3-selected-lpi-motion-v1',
        status='SIX_SAVED_PACKETS_THREE_LPI_DIAGNOSTIC_ONLY',
        native_core_sha256='c'*64,precision_ledger_sha256='d'*64,
        worker_report_sha256='e'*64,script_sha256='f'*64,
        new_boolean_calls_this_run=0,new_native_source_calls_this_run=0,
        newton_admitted=False,root_cause_determined=False,
        continuous_neighborhood_certified=False,asymptotic_order_certified=False,
        final_heart_obj_produced=False,runtime_origin_cryptographically_attested=False,
        samples=samples,same_side_interval_lpi_secants=intervals)


class OfflineAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'fixture.json'

    def check(self, obj):
        self.path.write_text(json.dumps(obj))
        return verifier.audit(self.path)

    def test_synthetic_linear_matches_all_exact_identities(self):
        result=self.check(fixture())
        self.assertEqual(result['counts']['LPI_rows_exactly_rechecked'],18)
        self.assertEqual(result['counts']['interval_feature_exactly_rechecked'],18)
        self.assertEqual(result['counts']['full_vs_two_halves_curvature_identities'],6)
        self.assertFalse(result['limits']['newton_admitted'])

    def test_tampered_tprime_is_rejected(self):
        data=fixture()
        data['samples'][0]['constructions'][0]['t_prime']='2/1'
        with self.assertRaisesRegex(ValueError,'LPI_QUOTIENT_RULE'):
            self.check(data)

    def test_tampered_interval_residual_is_rejected(self):
        data=fixture()
        data['same_side_interval_lpi_secants'][0]['features']['Repeated']['signed_residual'][0]='1/1'
        with self.assertRaisesRegex(ValueError,'EXACT_INTERVAL_RESIDUAL_IDENTITY'):
            self.check(data)

    def test_newton_promotion_is_rejected(self):
        data=fixture()
        data['newton_admitted']=True
        with self.assertRaisesRegex(ValueError,'SCIENTIFIC_SCOPE_FLAGS_INCONSISTENT'):
            self.check(data)

    def test_wrong_stem_order_is_rejected(self):
        data=fixture()
        data['samples'][0],data['samples'][1]=data['samples'][1],data['samples'][0]
        with self.assertRaisesRegex(ValueError,'SAMPLE_SET_OR_ORDER'):
            self.check(data)


if __name__=='__main__':unittest.main()

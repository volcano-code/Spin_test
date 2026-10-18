"""Standalone W5 M2 cross-contract and W2 fail-closed admission regression.

Mock W2 sealed envelopes here are TEST FIXTURES and are never native truth.
The real W2 pre-W0 manifest currently advertises zero verified samples.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

import numpy as np

from research.NeuralMoments.models.deeponet.contract_gate import (
    AdmissionError, B_DIAG, NATIVE_C_ORDER, RAW_R_ORDER, W0_SCHEMA,
    W0_SOURCE_SHA, W2_ORDER, W2_SCHEMA, admit_w2_record,
    audit_family_split, canonical, check_w0_contract, coefficient_to_monomial,
    digest, file_sha256, native_jacobian_to_monomial, native_polynomial,
    normalized_component_error, raw_pushforward, strict_json,
)
from research.NeuralMoments.models.deeponet.m2_audit import (
    check_w2_readiness, run_multiseed,
)


def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _w0_fixture() -> dict:
    c = [-1/math.sqrt(26), 0, 0, 5/math.sqrt(26)] + [0]*6
    zero = [0.]*10
    return {
        "schema":W0_SCHEMA, "source_sha":W0_SOURCE_SHA,
        "geometry":{"original_sha256":"1"*64,"fixed_F_sha256":"2"*64,"design_D_sha256":"3"*64,
                    "frame":{"kind":"INPUT_NORMALIZED_TARGET_V1",
                             "length_original_per_normalized":2.0,
                             "density_original_per_normalized":3.0,"origin_original":[.2,-.3,.4]},
                    "density":3.,"fixed_r_computed_once":True},
        "coefficients":{"c":c,"order":NATIVE_C_ORDER,"positive_scale_equivalent":True,
                        "negative_sign_equivalent":False,"retained_side":"BETA_POSITIVE",
                        "cross_mapping":"q=Bc;Bdiag=1,1,1,1,1,1,1,2,2,2"},
        "moments":{"order":RAW_R_ORDER,"fixed_r":zero,"variable_r":None,"total_r":None,
                   "status":"ANALYTIC_ONLY","independent_geometry_evidence":False},
        "jacobian":{"type":"UNAVAILABLE","derivative_defined":False,"values":None,
                    "native_tangent_basis":None,
                    "hessian_rule":"ONLY_IF_SMOOTH_AMBIENT_CHECK_Jc_B_INVERSE"},
        "error":{"truth_kind":"ANALYTIC_P0","length_ref":1,"density_ref":1,
                 "metric":"ABSOLUTE_PER_COMPONENT_DIVIDED_BY_RHO_L3_L4_L5",
                 "threshold_policy":"PER_CASE_PREDECLARED_NO_UNIVERSAL_1_PERCENT",
                 "certifies_proof":False},
    }


class W0BridgeUnitTests(unittest.TestCase):
    def test_native_offdiagonal_coefficients_have_factor_two(self):
        c=[.2,.1,.3,-.4,2.,3.,4.,5.,6.,7.]
        xyz=[.3,-.2,.5]
        x,y,z=xyz
        expected=c[0]+c[1]*x+c[2]*y+c[3]*z+c[4]*x*x+c[5]*y*y+c[6]*z*z+2*c[7]*y*z+2*c[8]*x*z+2*c[9]*x*y
        self.assertAlmostEqual(native_polynomial(c,xyz),expected,places=13)
        np.testing.assert_allclose(coefficient_to_monomial(c),np.array(c)*B_DIAG)
        self.assertNotAlmostEqual(native_polynomial(c,xyz),-expected)

    def test_hessian_rule_is_conditioned_on_smooth_ambient(self):
        J=np.diag(B_DIAG).tolist()
        H=native_jacobian_to_monomial(J,smooth_full_ambient=True)
        np.testing.assert_allclose(H,np.eye(10))
        with self.assertRaises(AdmissionError):
            native_jacobian_to_monomial(J,smooth_full_ambient=False)
        self.assertNotAlmostEqual(np.linalg.norm(np.array(J)-np.array(J).T)+1,0)

    def test_physical_raw_pushforward_matches_gaussian_quadrature(self):
        # Analytic centered unit box of half extent 1 and rho=1.
        base=[8.,0.,0.,0.,8/3,8/3,8/3,0.,0.,0.]
        theta=.43
        R=np.array([[math.cos(theta),-math.sin(theta),0],
                    [math.sin(theta),math.cos(theta),0],[0,0,1.]])
        A=R@np.diag([1.4,.7,1.1]); t=np.array([.2,-.4,.6]); density=2.5
        expected=raw_pushforward(base,A,t,density_ratio=density)
        roots,weights=np.polynomial.legendre.leggauss(3)
        direct=np.zeros(10)
        for i,x in enumerate(roots):
            for j,y in enumerate(roots):
                for k,z in enumerate(roots):
                    px,py,pz=A@np.array([x,y,z])+t
                    direct += density*abs(np.linalg.det(A))*weights[i]*weights[j]*weights[k] * np.array([1,px,py,pz,px*px,py*py,pz*pz,py*pz,px*pz,px*py])
        np.testing.assert_allclose(expected,direct,atol=2e-13,rtol=1e-13)
        np.testing.assert_allclose(raw_pushforward(base,np.eye(3),[0.,0.,0.]),base)
        with self.assertRaises(AdmissionError):
            raw_pushforward(base,[[0]*3 for _ in range(3)],[0,0,0])

    def test_normalized_error_component_scales(self):
        pred=[8,16,16,16]+[32]*6
        np.testing.assert_allclose(normalized_component_error(pred,[0]*10,length_ref=2,density_ref=1),np.ones(10))
        with self.assertRaises(AdmissionError):
            normalized_component_error(pred,[0]*10,length_ref=0,density_ref=1)

    def test_w0_sample_accepted_and_tampering_rejected(self):
        valid=_w0_fixture()
        result=check_w0_contract(valid)
        self.assertEqual(result["j_type"],"UNAVAILABLE")
        variants=[
            ("bad_source",lambda x:x.update(source_sha="f"*40)),
            ("bad_order",lambda x:x["moments"].update(order="WRONG")),
            ("cross_term_swap",lambda x:x["coefficients"].update(cross_mapping="q=c")),
            ("missing_geometry_identity",lambda x:x["geometry"].update(design_D_sha256=None)),
            ("bad_side",lambda x:x["coefficients"].update(negative_sign_equivalent=True)),
            ("not_normalized",lambda x:x["coefficients"].update(c=[0]*10)),
            ("lost_fixed_cache",lambda x:x["geometry"].update(fixed_r_computed_once=False)),
            ("bad_derivative",lambda x:x["jacobian"].update(derivative_defined=True)),
        ]
        for name,change in variants:
            with self.subTest(name=name):
                x=copy.deepcopy(valid);change(x)
                with self.assertRaises(AdmissionError):check_w0_contract(x)
        x=copy.deepcopy(valid)
        x["moments"].update(variable_r=[1]*10,total_r=[1]*10,status="NATIVE_VERIFIED")
        self.assertTrue(np.array_equal(check_w0_contract(x)["r_variable"],np.ones(10)))
        x["moments"]["total_r"][0]=2
        with self.assertRaises(AdmissionError):check_w0_contract(x)

    def test_tangent_not_promoted_into_ambient(self):
        x=_w0_fixture()
        x["jacobian"].update(type="TANGENT_10XK",derivative_defined=True,
                             values=[[1,2]]*10,native_tangent_basis=[[1,2]]*10)
        self.assertEqual(check_w0_contract(x)["j_type"],"TANGENT_10XK")
        x["jacobian"]["native_tangent_basis"]=None
        with self.assertRaises(AdmissionError):check_w0_contract(x)


class W2GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.model=self.root/"model.stl";self.model.write_bytes(b"W5-test-model-not-a-native-CAD")
        self.native=self.root/"native.so";self.native.write_bytes(b"W5-test-native-placeholder-no-solver")
        self.filename=self.root/"record.json"
        self.c=_w0_fixture()["coefficients"]["c"]
        self.geometry={"family":"closed_heart_test_only", "original_sha256":"1"*64,
                       "fixed_F_sha256":"2"*64,"design_D_sha256":"3"*64}
        self.frame=_w0_fixture()["geometry"]["frame"]
        self.p={"schema":W2_SCHEMA,"order":W2_ORDER,
                "coefficient_convention":"NATIVE_MATRIX_ENTRY_Q10",
                "model_sha256":_digest_file(self.model),
                "native_module_sha256":_digest_file(self.native),
                "geometry":self.geometry,"density":3.,"frame":self.frame,
                "q":self.c,"r_D":[3.]+[0.]*9,"J_D":np.eye(10).tolist(),
                "r_F":[2.]+[0.]*9,"topology_status":"VALID",
                "derivative_status":"VALID","derivative_contract":{"verified_neighborhood":True},
                "stage_seconds":{"w2_total_wall_seconds":1.25},"peak_rss_bytes":51200,
                "exact_proof":{"kind":"cherchi_same_call_discrete_map","native_cherchi":True,
                    "geometry_hash":"test-geometry-hash","topology_hash":"test-topology-hash",
                    "evaluation_map_identity":"test-evaluation-map-identity",
                    "boolean_backend_identity":"test-backend-fake-evidence",
                    "derivative_identity":"test-derivative-identity"},
                "split":"train","failure_reason":None,
                "total_policy":"r_total=r_F+r_D;J_total=J_D;fixed_never_in_r_D"}

    def write(self,*,payload=None):
        p=copy.deepcopy(self.p if payload is None else payload)
        record={"payload":p,"payload_sha256":digest(p),"identity":{
            "q_sha256":digest(p["q"]),"geometry_sha256":digest(p["geometry"]),
            "model_sha256":p["model_sha256"],"native_module_sha256":p["native_module_sha256"]}}
        self.filename.write_text(canonical(record)+"\n",encoding="utf-8")
        return _digest_file(self.filename)

    def admit(self,**kw):
        options=dict(expected_c_native=self.c,model_path=self.model,native_module_path=self.native,
                     approved_file_sha256=[_digest_file(self.filename)],
                     expected_design_sha256=self.geometry["design_D_sha256"],
                     expected_w0_original_sha256=self.geometry["original_sha256"],
                     expected_w0_fixed_sha256=self.geometry["fixed_F_sha256"])
        options.update(kw)
        return admit_w2_record(self.filename,**options)

    def test_explicit_approval_and_complete_fake_fixture_path(self):
        self.write()
        with self.assertRaisesRegex(AdmissionError,"approved"):
            self.admit(approved_file_sha256=[])
        # This artificially approved record ONLY exercises parser/gate code;
        # it is NOT a claim of native Cherchi runtime or label authenticity.
        candidate=self.admit()
        self.assertEqual(candidate["r_total"][0],5)
        self.assertEqual(candidate["J_native"].shape,(10,10))
        self.assertTrue(candidate["status"].startswith("CANDIDATE_"))
        self.assertEqual(candidate["record_sha256"],_digest_file(self.filename))
        with self.assertRaises(AdmissionError):self.admit(expected_design_sha256="9"*64)
        self.model.write_bytes(b"replaced model")
        with self.assertRaises(AdmissionError):self.admit()

    def test_reject_modified_envelope_even_if_old_hash_approved(self):
        sha=self.write()
        record=json.loads(self.filename.read_text())
        record["payload"]["J_D"][7][9]+=0.25
        self.filename.write_text(canonical(record),encoding="utf-8")
        with self.assertRaisesRegex(AdmissionError,"not independently approved"):
            self.admit(approved_file_sha256=[sha])
        with self.assertRaises(AdmissionError):self.admit()
        self.filename.write_text('{"payload": 1, "payload": 2}',encoding="utf-8")
        with self.assertRaisesRegex(AdmissionError,"duplicate"):
            strict_json(self.filename)

    def test_w2_pre_w0_mock_and_missing_certificates_fail(self):
        cases=[
            ("mock backend", lambda p:p["exact_proof"].update(boolean_backend_identity="mock")),
            ("analytic not native",lambda p:p["exact_proof"].update(native_cherchi=False)),
            ("unknown derivative",lambda p:p.update(derivative_status="UNKNOWN",J_D=None)),
            ("no neighborhood",lambda p:p.update(derivative_contract=None)),
            ("excluded",lambda p:p.update(split="excluded")),
            ("failed",lambda p:p.update(failure_reason="native failed")),
            ("frame mismatch",lambda p:p["frame"].update(kind="physical")),
            ("coefficient order",lambda p:p.update(order=list(reversed(W2_ORDER)))),
            ("unexpected payload key",lambda p:p.update(unapproved_field="injected")),
            ("geometry family missing",lambda p:p["geometry"].pop("family")),
            ("too-short Jacobian",lambda p:p.update(J_D=[[0]*9]*10)),
            ("native SHA mismatch",lambda p:p.update(native_module_sha256="a"*64)),
        ]
        for name,mutation in cases:
            with self.subTest(case=name):
                p=copy.deepcopy(self.p);mutation(p)
                self.write(payload=p)
                with self.assertRaises(AdmissionError):self.admit()

    def test_query_mismatch_sign_not_identified(self):
        self.write()
        with self.assertRaises(AdmissionError):
            self.admit(expected_c_native=[-x for x in self.c])
        with self.assertRaises(AdmissionError):
            self.admit(expected_c_native=[2*x for x in self.c])

    def test_material_identity_and_family_split_leakage(self):
        self.write();row=self.admit()
        other=copy.deepcopy(row);other["split"]="test";other["record_sha256"]="f"*64
        with self.assertRaises(AdmissionError):audit_family_split([row,other])
        separate=copy.deepcopy(other)
        separate["family"]="ellipsoid_test_only"
        separate["geometry"]={"family":"ellipsoid_test_only", "original_sha256":"4"*64,
                              "fixed_F_sha256":"5"*64,"design_D_sha256":"6"*64}
        data=audit_family_split([row,separate])
        self.assertEqual(data["by_split"]["test"],1)
        self.assertFalse(data["leakage"])
        separate["geometry"]["fixed_F_sha256"]=row["geometry"]["fixed_F_sha256"]
        with self.assertRaises(AdmissionError):audit_family_split([row,separate])

    def test_manifest_declares_zero_and_never_opens_gate(self):
        path=self.root/"manifest.json"
        path.write_text(json.dumps({"schema":W2_SCHEMA,"status":"ADAPTER_SMOKE_ONLY",
                                    "native_teacher_runs":0,"training_samples":0}),encoding="utf-8")
        gate=check_w2_readiness(path)
        self.assertFalse(gate["ready"])
        self.assertEqual(gate["training_samples_declared"],0)
        self.assertFalse(check_w2_readiness(None)["ready"])
        with self.assertRaises(ValueError):
            check_w2_readiness(self.model)


class MultiSeedAuditTests(unittest.TestCase):
    def test_two_seed_real_cpu_analytic_trial(self):
        report=run_multiseed(seeds=(2,5),steps=1,per_family=2,repeats=1)
        self.assertEqual(report["status"],"MULTISEED_ANALYTIC_ONLY_NATIVE_TRAINING_BLOCKED")
        self.assertFalse(report["w2_admission"]["ready"])
        self.assertEqual(report["gpu_seconds"],0.0)
        for family in ("deeponet","geometry_mlp"):
            m=report["models"][family]
            self.assertEqual(set(m),{"residual_only","derivative_enhanced"})
            for arm in m.values():
                self.assertGreater(arm["parameters"],0)
                self.assertGreater(arm["heldout"]["J_mae"]["mean"],0)
                self.assertEqual(set(arm["oracle_adaptation"]),{"0","1","2","4","8"})
                self.assertEqual(len(arm["heldout"]["r_mae"]["per_seed"]),2)


if __name__=="__main__":
    unittest.main()

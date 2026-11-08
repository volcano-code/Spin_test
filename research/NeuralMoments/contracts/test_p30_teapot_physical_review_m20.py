import copy
import json
import unittest
from pathlib import Path
from p30_teapot_physical_review_m20 import audit_case, ReviewRejected

BASE={
 "w0_baseline":"5bab2eb2616df306906a6887a273f68acfa49320",
 "p20_request_sha256":"a324bbe85c9ee57a67221eb86420c505efc4d065d60d84cf92d66e4d95dac1b9",
 "p19_manifest_sha256":"c6bd67f872f344da46c1f774f8b68c28a2ecfa4c5a5c000d9e6bf5229e3412d6",
 "p27_manifest_sha256":"3a9b6b21d1d1185e00d1ef25a1bfc625d4696f554c3ab4a7719f5d85ca109773",
 "p27_lock_sha256":"451d8b46cd047325b0b3e2d406f9e89dd0252cece677f5f310ca5abe3c8089a4",
 "p30_private_plan_sha256":"fc2d9a1b3c372513cdf3d6ba41e74812a12761e67f6b6fa82c0a66982351bacc",
 "base_native_c_sha256":"57ac958304df37ebfd36bc1dddeb32c81a113ed5440f65d959f4b45f2a12e6ca",
 "same_call_jacobian_sha256":"26cf3b5dd53d45a4b80f14319b39d28fa9ef7b8d8be3a915189e90ba077a08a5",
 "obj_sha256":{"M":"0b59fd6f41079ab507af3e31673f94472b0d6f849df981b52c1ea667994ad704","F":"5c5db73792bd8d6566a954e6d0eef6d22e248a7ad2f8a7a8d8e6d4f2ad9d86a8","D":"d64a3163c886cb06ade6f366e8ff5e475934816343a5be429b55c5832951b073","S":"65d794715d580ebab231716669e25d79fea7f353da35c96d4a54f1779dc7e9f0"},
 "scale_m_per_reference":0.025,"density_kg_m3":1200,"density_model":"ASSUMED_UNIFORM_SOLID_NOT_PRINTED_MATERIAL_CERTIFICATE",
 "bounds_m":[[-0.029950000000000004,-0.020000000000000004,0.0],[0.03434,0.020000000000000004,0.04275]],
 "length_original_per_normalized":2.5716,"frame_length_is_bbox_L":True,
 "mass_kg":{"M":0.031118997336943656,"F":0.030623879229415785,"D":0.0004951181075278711,"S":0.00034522876294318855},
 "center_of_mass_m":{"M":[0.00020909987752647146,3.289597355222163e-8,0.016317786546683703],"F":[0.00021248054445209633,3.3427826229945706e-8,0.01631079864337299],"D":[-1.711702442325252e-20,-1.3743671140548967e-21,0.01675],"S":[-3.4344921238481775e-20,1.200157052966431e-20,0.02225685012784948]},
 "full_inertia_com_kg_m2":{"M":[[3.885498172690457e-6,-2.5588491967436944e-11,-5.387647354106609e-9],[-2.5588491967436944e-11,4.398518998111973e-6,-2.221494630622323e-12],[-5.387647354106609e-9,-2.221494630622323e-12,5.458550461413813e-6]],"F":[[3.880413266512508e-6,-2.558349495841274e-11,-5.4331174909324105e-9],[-2.558349495841274e-11,4.393412127153277e-6,-2.228648075359519e-12],[-5.4331174909324105e-9,-2.228648075359519e-12,5.452774958403695e-6]],"D":[[4.990918533352237e-9,-1.5362550681184515e-15,-1.3937853903056407e-26],[-1.5362550681184515e-15,4.990885387534517e-9,1.2436366283654635e-26],[-1.3937853903056407e-26,1.2436366283654635e-26,5.753505082465374e-9]],"S":[[4.863130801577518e-8,-1.8069096482697272e-27,1.8185087685803964e-27],[-1.8069096482697272e-27,4.863130801577518e-8,-9.740921051163033e-29],[1.8185087682697272e-27,-9.740921051163033e-29,3.805802570293026e-10]]},
 "shaft_included_in_fixed":True,"shaft_added_separately_to_total":False,
 "radial_envelope_scale":"9/8","xy_rotation_degrees":7,"original_shaft_bytes_preserved":True,
 "original_author_cad":False,"physical_parameters_approved":False,"support_points":[],
 "target_tip_reference":[0,0,0],"represented_tip_exactly_equals_requested":False,
 "p19_complete_shaft_in_fixed":True,"p19_design_shaft_separation":True,
 "global_printability_or_strength_proved":False,"native_implicit_region_equality_proved":False
}

class TeapotPhysicalReview(unittest.TestCase):
 def test_actual_evidence_is_blocked_not_authorized(self):
  r=audit_case(BASE)
  self.assertEqual(r["decision"],"BLOCKED_PHYSICAL_CASE_NOT_OWNER_APPROVED")
  self.assertFalse(r["p30b"]["diagnostic_pilot_authorized"])
  self.assertFalse(r["newton_authorized"])
  self.assertFalse(r["training_authorized"])
  self.assertFalse(r["continuous_smooth_neighborhood_certified"])
  self.assertEqual(r["p30b"]["maximum_real_native_points"],12)
  self.assertIsNone(r["p30b"]["max_normalized_jacobian_error"])

 def test_mass_partition_and_shaft_not_double_counted(self):
  r=audit_case(BASE)
  self.assertAlmostEqual(r["physical_case"]["proposed_uniform_solid_mass_kg"],
                         r["physical_case"]["fixed_mass_kg"]+r["physical_case"]["design_mass_kg"],places=15)
  self.assertTrue(r["physical_case"]["S_already_in_F"])
  self.assertFalse(r["physical_case"]["global_strength_printability"])

 def test_wrong_scale_rejected(self):
  x=copy.deepcopy(BASE);x["scale_m_per_reference"]=0.15
  with self.assertRaisesRegex(ReviewRejected,"PROPOSED_SCALE_CHANGED"):audit_case(x)

 def test_wrong_density_rejected(self):
  x=copy.deepcopy(BASE);x["density_kg_m3"]=1240
  with self.assertRaisesRegex(ReviewRejected,"PROPOSED_DENSITY_CHANGED"):audit_case(x)

 def test_density_must_be_solid_assumption(self):
  x=copy.deepcopy(BASE);x["density_model"]="PRINTED_MATERIAL_CERTIFIED"
  with self.assertRaisesRegex(ReviewRejected,"DENSITY_MODEL_NOT_EXPLICIT"):audit_case(x)

 def test_tip_mismatch_is_not_silently_accepted(self):
  x=copy.deepcopy(BASE);x["represented_tip_exactly_equals_requested"]=True
  with self.assertRaisesRegex(ReviewRejected,"TIP_FRAME_FACT_CHANGED"):audit_case(x)

 def test_support_geometry_required_and_empty_is_blocker_not_approval(self):
  r=audit_case(BASE)
  self.assertEqual(r["physical_case"]["support_points"],[])
  self.assertIn("SUPPORT_POINTS_EMPTY_AND_NO_SUPPORT_OR_REACTION_CONSTRAINTS",r["blockers"])

 def test_shaft_envelope_and_rotation_are_reconstruction_not_cad(self):
  r=audit_case(BASE)
  self.assertEqual(r["physical_case"]["shaft_envelope_radial_scale"],"9/8")
  self.assertEqual(r["physical_case"]["shaft_envelope_xy_rotation_degrees"],7)
  self.assertIn("9_OVER_8_RADIAL_SHAFT_ENVELOPE_AND_7_DEG_ROTATION_ARE_RECONSTRUCTION_RULES_NOT_AUTHOR_CAD",r["blockers"])

 def test_shaft_double_count_rejected(self):
  x=copy.deepcopy(BASE);x["shaft_added_separately_to_total"]=True
  with self.assertRaisesRegex(ReviewRejected,"SHA_DOUBLE_COUNT_RISK"):audit_case(x)

 def test_mfd_identities_rejected_on_drift(self):
  x=copy.deepcopy(BASE);x["obj_sha256"]["D"]="0"*64
  with self.assertRaisesRegex(ReviewRejected,"P19_OBJ_IDENTITY_MISMATCH"):audit_case(x)

 def test_partition_mass_error_rejected(self):
  x=copy.deepcopy(BASE);x["mass_kg"]["D"]+=0.01
  with self.assertRaisesRegex(ReviewRejected,"M_NOT_EQUAL_F_PLUS_D"):audit_case(x)

 def test_no_global_strength_inference(self):
  x=copy.deepcopy(BASE);x["global_printability_or_strength_proved"]=True
  with self.assertRaisesRegex(ReviewRejected,"UNSUPPORTED_STRENGTH_CLAIM"):audit_case(x)

 def test_w0_w2_p27_p30_hashes_pinned(self):
  for key in ("p20_request_sha256","p19_manifest_sha256","p27_manifest_sha256","p27_lock_sha256","p30_private_plan_sha256","base_native_c_sha256","same_call_jacobian_sha256"):
   x=copy.deepcopy(BASE);x[key]="f"*64
   with self.subTest(key=key),self.assertRaises(ReviewRejected):audit_case(x)

 def test_unit_transform_is_conditional_and_not_authorized(self):
  r=audit_case(BASE)
  self.assertEqual(r["physical_case"]["conditional_normalized_frame_length_m"],0.06429)
  self.assertEqual(r["physical_case"]["conditional_length_ref_candidate_m"],0.06429)
  self.assertEqual(r["physical_case"]["conditional_density_ref_candidate_kg_m3"],1200)
  self.assertTrue(r["physical_case"]["conditional_units_are_not_approved"])
  self.assertIsNone(r["p30b"]["length_ref"])
  self.assertIsNone(r["p30b"]["density_ref"])

 def test_pilot_step_and_error_budget_remain_unapproved(self):
  r=audit_case(BASE)
  self.assertEqual(r["p30b"]["proposed_h_radians"],0.002)
  self.assertFalse(r["p30b"]["h_approved"])
  self.assertIsNone(r["p30b"]["max_normalized_jacobian_error"])
  self.assertIn("NO_MEASURED_CASE_SPECIFIC_NOISE_OR_ERROR_BUDGET",r["p30b"]["tolerance_reason"])

 def test_no_authorization_artifact_is_created_by_review(self):
  r=audit_case(BASE)
  self.assertNotEqual(r["decision"],"APPROVED_FOR_DIAGNOSTIC_PILOT_ONLY")
  self.assertFalse(r["p30b"]["diagnostic_pilot_authorized"])

 def test_full_inertia_tensor_is_retained_and_positive(self):
  r=audit_case(BASE)
  self.assertEqual(set(r["physical_case"]["full_inertia_com_kg_m2"]),{"M","F","D","S"})
  x=copy.deepcopy(BASE);x["full_inertia_com_kg_m2"]["D"][0][0]=-1
  with self.assertRaisesRegex(ReviewRejected,"INERTIA_NOT_POSITIVE_DEFINITE:D"):audit_case(x)

if __name__=="__main__":unittest.main()

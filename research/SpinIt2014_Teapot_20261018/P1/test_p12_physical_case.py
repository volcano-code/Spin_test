"""Independent P12 regression on archived real Cherchi F/D; no W0 authorization."""
from __future__ import annotations
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from p12_physical_case import (SHA,MOMENT_ORDER,YUP_TO_ZUP,raw_ten,
                                ten_to_matrices,transform_ten_physical,
                                si_properties,evaluate,digest)
import trimesh

HERE=Path(__file__).resolve().parent
REAL=Path(__import__('os').environ.get('W4_P12_REAL_INPUT_DIR',str(HERE.parent/'w4_p12_real')))
INPUT={
    'M':REAL/'P10_Cherchi_Original_Yup.obj',
    'F':REAL/'P11_F_Trial_Cherchi_Real_Subtraction.obj',
    'D':REAL/'P11_D_Trial_Interior_Sphere.obj',
}
REPORT=REAL/'P11_real_Cherchi_subtraction_audit.json'
CASE=HERE/'p12_teapot_proposed_case.json'

class P12PhysicalPreflight(unittest.TestCase):
    def test_archived_real_Cherchi_source_ID_and_raw_partition(self):
        self.assertEqual({k:digest(v) for k,v in INPUT.items()},{k:SHA[k] for k in INPUT})
        self.assertEqual(digest(REPORT),SHA['P11'])
        mesh={k:trimesh.load_mesh(v,process=False) for k,v in INPUT.items()}
        r={k:raw_ten(x) for k,x in mesh.items()}
        self.assertLess(np.max(abs(r['M']-r['F']-r['D'])),1e-10)
        self.assertEqual(MOMENT_ORDER,['M','LX','LY','LZ','QXX','QYY','QZZ','QYZ','QXZ','QXY'])

    def test_SI_mass_scale_density_invariants(self):
        m=trimesh.load_mesh(INPUT['M'],process=False)
        r=raw_ten(m);s=.15/3.15
        mass,L,Q=transform_ten_physical(r,s,1240)
        self.assertAlmostEqual(mass,3.4608988916769654,places=10)
        self.assertAlmostEqual(L[2]/mass,m.center_mass[1]*s,places=12)
        self.assertTrue(np.allclose(Q,Q.T))
        self.assertAlmostEqual(transform_ten_physical(r,2*s,1240)[0],8*mass,places=9)
        self.assertAlmostEqual(transform_ten_physical(r,s,620)[0],mass/2,places=9)
        self.assertAlmostEqual(np.linalg.det(YUP_TO_ZUP),1)
        with self.assertRaisesRegex(ValueError,'PHYSICAL_SCALE_DENSITY_INVALID'):
            transform_ten_physical(r,-1,1240)

    def test_physical_inertia_and_axis(self):
        m=trimesh.load_mesh(INPUT['M'],process=False)
        p=si_properties(raw_ten(m),.15/3.15,1240)
        I=np.array(p['inertia_com_kg_m2']);self.assertTrue(np.allclose(I,I.T))
        self.assertTrue(all(v>0 for v in p['principal_inertia_kg_m2']))
        self.assertAlmostEqual(I[2,2],p['inertia_about_trial_z_at_com_kg_m2'],places=12)
        self.assertTrue(np.isfinite(p['nearest_principal_axis_angle_to_trial_z_deg']))

    def test_real_FD_candidate_report_is_not_optimization(self):
        with tempfile.TemporaryDirectory() as td:
            o=evaluate(INPUT,REPORT,CASE,Path(td)/'report.json')
            self.assertEqual(o['status'],'DIAGNOSTIC_PHYSICAL_CASE_ONLY')
            self.assertLess(o['SI_additivity_max_abs'],1e-12)
            self.assertFalse(o['W0_contract_approval'])
            self.assertFalse(o['actual_optimized_geometry_available'])
            self.assertFalse(o['P12_final_SpinIt_Faster_optimization_performed'])
            self.assertGreater(o['assumed_solid_mass_divided_by_old_demo_mass'],13)
            self.assertGreater(o['minimum_inner_cavity_to_original_outer_surface_lower_bound_m'],.03)
            self.assertAlmostEqual(o['material']['D']['mass_kg'],o['material_relative_effects']['mass_reduction_kg'],places=12)
            self.assertTrue((Path(td)/'report.json').is_file())

    def test_reject_tampered_real_M(self):
        with tempfile.TemporaryDirectory() as td:
            m=Path(td)/'tampered.obj';m.write_bytes(INPUT['M'].read_bytes()+b'\n# tampered\n')
            with self.assertRaisesRegex(ValueError,'FROZEN_REAL_CHERCHI_M_SHA256_MISMATCH'):
                evaluate({**INPUT,'M':m},REPORT,CASE,Path(td)/'forbidden.json')

    def test_reject_promoted_W0_approval(self):
        with tempfile.TemporaryDirectory() as td:
            case=json.loads(CASE.read_text());case['W0_design_F_D_authorized']=True
            p=Path(td)/'fake-case.json';p.write_text(json.dumps(case))
            with self.assertRaisesRegex(ValueError,'FORBIDDEN_PREMATURE_PHYSICAL_AUTHORIZATION'):
                evaluate(INPUT,REPORT,p,Path(td)/'forbidden.json')

    def test_reject_fake_material_record(self):
        with tempfile.TemporaryDirectory() as td:
            bad=Path(td)/'fake-native.json';bad.write_bytes(REPORT.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'FROZEN_REAL_CHERCHI_P11_SHA256_MISMATCH'):
                evaluate(INPUT,bad,CASE,Path(td)/'forbidden.json')

    def test_reject_invalid_virtual_tip(self):
        with tempfile.TemporaryDirectory() as td:
            case=json.loads(CASE.read_text())
            case['diagnostic_assumptions']['tip_contact']='CERTIFIED_REAL_TIP'
            p=Path(td)/'fake.json';p.write_text(json.dumps(case))
            with self.assertRaisesRegex(ValueError,'TIP_OR_AXIS_NOT_EXPLICIT_PROVISIONAL'):
                evaluate(INPUT,REPORT,p,Path(td)/'forbidden.json')

if __name__=='__main__':unittest.main()

"""W4 P15 actual P14 archive regression and fail-closed source identity tests."""
from __future__ import annotations
import json,os,tempfile,unittest
from pathlib import Path
import numpy as np
import trimesh
from p15_inherited_sliver_repair import (AREA,BOUND,MESH_COUNT,CASES,digest,load,
  edge_incidence,sliver_signatures,weld_inherited,study,raw_ten,
  independent_contact_scan,oriented_triangle,valid_native_case)

ROOT=Path(os.environ.get('W4_P15_P14_DIR',
  'research/SpinIt2014_Teapot_20261018/P1/p14-cherchi-junction-study'))
OUTER=ROOT.parent/'p13-native-Cherchi-domain/p13-outer-cherchi-union.obj'

class P15SourceGates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not ROOT.is_dir() or not OUTER.is_file():
            raise unittest.SkipTest('real P14 native artifact was not mounted')
        cls.report=json.loads((ROOT/'p14-junction-native-study.json').read_text())

    def test_true_negative_native_study_remains_negative(self):
        self.assertEqual(self.report['status'],'COMPLETED_NEGATIVE_NATIVE_JUNCTION_STUDY')
        self.assertIsNone(self.report['admissible_candidate'])
        self.assertEqual(self.report['real_D_native_trials'],11)
        self.assertFalse(self.report['W0_approved'])
        self.assertEqual(digest(OUTER),self.report['source_sha256']['outer'])

    def test_inherited_exactly_twenty_eight_tiny_face_signatures(self):
        outer=load(OUTER)
        ids,slivers=sliver_signatures(outer)
        self.assertEqual(len(ids),MESH_COUNT)
        self.assertEqual(len(slivers),MESH_COUNT)
        for name in CASES:
            F=load(ROOT/name/'F_retained_cherchi.obj')
            candidate_ids,cs=sliver_signatures(F)
            self.assertEqual(len(candidate_ids),MESH_COUNT)
            self.assertEqual(cs,slivers)
            self.assertEqual(edge_incidence(F),0)

    def test_original_and_all_three_F_weld_only_known_pairs(self):
        sources=[OUTER]+[ROOT/name/'F_retained_cherchi.obj' for name in CASES]
        for path in sources:
            original=load(path);before=digest(path)
            cleaned,meta=weld_inherited(original)
            self.assertEqual(meta['merged_near_vertex_pairs'],14)
            self.assertEqual(meta['removed_exact_sliver_faces'],28)
            self.assertEqual(meta['non_two_incidence_edges'],0)
            self.assertEqual(meta['remaining_small_triangles'],0)
            self.assertLess(meta['maximum_vertex_representative_displacement'],BOUND)
            self.assertLess(meta['material_raw_ten_change_max_abs'],1e-11)
            self.assertTrue(cleaned.is_volume)
            self.assertEqual(digest(path),before)

    def test_full_real_P14_material_additivity_and_float_contact_scans(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=study(ROOT,tmp)
            self.assertEqual(result['status'],'FLOAT64_MICROWELD_CANDIDATE_AVAILABLE_NOT_EXACT_CHERCHI')
            self.assertEqual(result['selected'],'rotate_1p5')
            self.assertEqual(len(result['cases']),3)
            for entry in result['cases']:
                self.assertEqual(entry['status'],'FLOAT_MESH_POSTPROCESS_CONDITIONAL_PASS_NOT_NATIVE_EXACT')
                self.assertTrue(entry['all_slivers_from_outer'])
                self.assertLess(entry['max_abs_full_raw_ten_material_additivity_residual'],1e-12)
                self.assertTrue(entry['F_independent_contact_scan']['exhaustive'])
                self.assertEqual(entry['F_independent_contact_scan']['witnesses'],[])
                self.assertTrue(entry['D_independent_contact_scan']['exhaustive'])
                self.assertEqual(entry['D_independent_contact_scan']['witnesses'],[])
                saved=Path(tmp)/entry['name']/'F_numeric_microweld.obj'
                self.assertEqual(digest(saved),entry['F_postprocessed_sha256'])
                self.assertTrue(load(saved).is_volume)
            for flag in ('original_CAD_shape_certified','exact_Cherchi_implicit_geometry_certified',
                         'W0_physical_tip_or_FD_approved','SpinIt_Faster_optimization_executed'):
                self.assertFalse(result[flag])

    def test_fabricated_native_sha_rejected(self):
        case=next(c for c in self.report['cases'] if c['name']=='rotate_1p5')
        altered=json.loads(json.dumps(case))
        altered['F_native']['output_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'NATIVE_BINARY_MATERIAL_PROVENANCE_MISMATCH'):
            valid_native_case(altered,ROOT,OUTER)

    def test_winding_reversal_is_not_inherited_sliver(self):
        parent=load(OUTER)
        tiny=np.flatnonzero(parent.area_faces<=AREA)[0]
        before=oriented_triangle(parent,parent.faces[tiny]); flipped=parent.faces[tiny,[0,2,1]]
        self.assertNotEqual(oriented_triangle(parent,flipped),before)

    def test_weld_limit_does_not_allow_uncontrolled_remeshing(self):
        parent=load(OUTER)
        with self.assertRaisesRegex(ValueError,'UNAUTHORIZED_VERTEX_MOVEMENT_LIMIT'):
            weld_inherited(parent,tol=1e-6)
        with self.assertRaisesRegex(ValueError,'UNEXPECTED_SOURCE_SLIVER_FACE_COUNT'):
            wedge=trimesh.creation.box()
            weld_inherited(wedge)

    def test_analytic_tetrahedral_ten_raw_moments_and_negative_contact(self):
        v=np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]],float)
        f=np.array([[0,2,1],[0,1,3],[0,3,2],[1,2,3]],dtype=int)
        tetra=trimesh.Trimesh(vertices=v,faces=f,process=False)
        moments=raw_ten(tetra)
        self.assertAlmostEqual(moments[0],1/6,places=12)
        self.assertAlmostEqual(moments[7],1/120,places=12)
        self.assertEqual(independent_contact_scan(tetra)['witnesses'],[])
        self.assertEqual(edge_incidence(tetra),0)

if __name__=='__main__':unittest.main()

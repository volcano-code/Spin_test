"""Model-independent solver code is untouched; test photo-guided INPUT only."""
import json,hashlib,sys,unittest
from pathlib import Path
import numpy as np,trimesh
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'source'))
import noodles_paper_geometry_v7 as v7

class NoodlesV7InputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((HERE/'source_parts_v7c/manifest.json').read_text())
    def test_79_strands(self):
        self.assertEqual(sum(name.startswith('tube-') for name in self.manifest['parts']),79)
    def test_11_rows_and_axial_rib(self):
        self.assertEqual(sum(name.startswith('rib-row') for name in self.manifest['parts']),11)
        self.assertIn('rib-axial-fixed',self.manifest['parts'])
    def test_all_strands_intersect_own_connector_by_conservative_radii(self):
        rows=v7.old.tube_layout()
        levels=sorted(set(round(row['z_model'],12) for row in rows))
        ribs=v7.rib_centerlines()
        for i,row in enumerate(rows):
            k=min(range(len(levels)),key=lambda j:abs(levels[j]-row['z_model']))
            midpoint=v7.centerline(i)[v7.SPEC['tube_samples']//2]
            rib=ribs[f'rib-row-{k:02d}-fixed']
            self.assertGreaterEqual(midpoint[1],rib[:,1].min())
            self.assertLessEqual(midpoint[1],rib[:,1].max())
            self.assertLess(abs(midpoint[2]-rib[0,2]),v7.SPEC['tube_radius_model']+v7.SPEC['rib_radius_model'])
    def test_row_ribs_reach_axial_and_hub(self):
        ribs=v7.rib_centerlines();spine=ribs['rib-axial-fixed']
        for name,rib in ribs.items():
            if name.startswith('rib-row'):
                self.assertLess(rib[:,1].min(),0)
                self.assertGreater(rib[:,1].max(),0)
                self.assertGreater(rib[0,2],spine[:,2].min())
                self.assertLess(rib[0,2],spine[:,2].max())
        self.assertLess(spine[:,2].min(),.9)
        self.assertGreater(spine[:,2].max(),.9)
    def test_design_envelope_is_not_fixed(self):
        rec=self.manifest['construction']
        self.assertEqual(rec['design_envelope'],'outer-ellipsoid')
        self.assertNotIn('outer-ellipsoid',rec['fixed_parts'])
        self.assertFalse(rec['permanent_ellipsoid_shell'])
    def test_all_input_source_files_match_manifest(self):
        for name,data in self.manifest['parts'].items():
            p=HERE/'source_parts_v7c'/data['model_obj']
            self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),data['sha256_model'])
    def test_native_audit_is_exactly_bound_to_source_hashes(self):
        audit=json.loads((HERE/'source-v7c-native-audit.json').read_text())
        self.assertTrue(audit['full_source_parts_passed'])
        self.assertEqual(audit['native_passed'],94)
        checks={x['part']:x for x in audit['results']}
        for part,data in self.manifest['parts'].items():
            row=checks[part+'-model.obj'];self.assertTrue(row['passed'])
            self.assertEqual(row['sha256'],data['sha256_model'])
    def test_no_optimisation_claim(self):
        self.assertEqual(self.manifest['optimization_invocations'],0)
        self.assertIn('NOT_OPTIMIZED',self.manifest['status']) if 'NOT_OPTIMIZED' in self.manifest['status'] else self.assertIn('NOT_RUN',self.manifest['status'])
        self.assertFalse(self.manifest['spec']['paper_cad_available'])
    def test_fluted_knob_and_slim_envelope(self):
        p=trimesh.load(HERE/'source_parts_v7c/pin-fixed-model.obj',force='mesh',process=False)
        vv=p.vertices
        upper=vv[(vv[:,2]>1.61)&(vv[:,2]<1.81)]
        radius=np.linalg.norm(upper[:,:2],axis=1)
        self.assertGreater(np.max(radius)-np.min(radius),.004)
        self.assertEqual(v7.SPEC['ellipsoid_radii_model'][-1],.42)

if __name__=='__main__':unittest.main(verbosity=2)

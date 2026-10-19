"""M7 source-pinned W6 interoperability and historical-evidence guardrails.

External W6 tests require a separate read-only W6 worktree or exact-byte mirror;
they are never satisfied by code secretly vendored in the W5 branch.
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import numpy as np
import torch

from research.NeuralMoments.models.deeponet.m7_cross_framework import (
    UntrustedW6Source, W6_FILES, git_blob_sha, load_pinned_w6,
    run_comparison, shared_voxel,
)
from research.NeuralMoments.models.deeponet.m7_evidence_audit import (
    inspect_snapshot,
)

ROOT=Path(__file__).resolve().parents[2]
SNAPSHOT=ROOT / 'research/NeuralMoments/models/deeponet/m7_w6_published_400step_snapshot.json'
EXTERNAL=os.environ.get('W5_M7_READONLY_W6_ROOT')


class W6HistoricalEvidenceTests(unittest.TestCase):
    def test_real_source_provenance_and_limits(self):
        a=inspect_snapshot(SNAPSHOT)
        self.assertFalse(a['representation_parity'])
        self.assertFalse(a['this_turn_retrained_W6'])
        self.assertFalse(a['verified_native_CAD_accuracy'])
        self.assertEqual(a['model_count'],6)
        self.assertLess(a['capacity_max_over_min'],1.05)
        self.assertEqual(a['source_git_blob_sha1'],'2e0d186933cf4f8579b1e012e74df714f5ae2bbc')

    def test_known_tradeoff_not_single_winner(self):
        a=inspect_snapshot(SNAPSHOT)
        self.assertEqual(a['best_r_mae'],'w5_deeponet')
        self.assertEqual(a['best_J_mae'],'w5_deeponet')
        self.assertEqual(a['fastest_archived_cached_J'],'w6_convex_potential4')
        self.assertIn('w6_convex_potential6',a['pareto_nondominated_models'])
        self.assertGreater(a['convex6_cached_J_speed_ratio_vs_deeponet'],4)

    def test_rejects_false_native_training(self):
        source=json.loads(SNAPSHOT.read_text())
        source['data']['teacher_real_native_runs']=1
        self._reject(source)

    def test_rejects_false_input_parity(self):
        source=json.loads(SNAPSHOT.read_text())
        source['data']['representation_parity']=True
        self._reject(source)

    def test_rejects_leaked_geometries(self):
        source=json.loads(SNAPSHOT.read_text())
        source['data']['dataset_sha256_per_seed'][1]['heldout']=source['data']['dataset_sha256_per_seed'][1]['train']
        self._reject(source)

    def test_rejects_unpinned_report(self):
        source=json.loads(SNAPSHOT.read_text())
        source['origin']['source_git_blob_sha1']='0'*40
        self._reject(source)

    def test_rejects_unmatched_parameters(self):
        source=json.loads(SNAPSHOT.read_text())
        source['data']['models']['w6_lite_bottleneck']['real_parameters']=99999
        self._reject(source)

    def _reject(self, source):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'bad.json'
            p.write_text(json.dumps(source),encoding='utf-8')
            with self.assertRaises(ValueError):inspect_snapshot(p)

    def test_unknown_external_worktree_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(UntrustedW6Source):load_pinned_w6(d)

    def test_github_blob_algorithm(self):
        # Known Git: `git hash-object` of a one-line blob.
        self.assertEqual(git_blob_sha(b'test\n'), '9daeafb9864cf43055ae93beb0afd6c7d144bfa4')


@unittest.skipUnless(EXTERNAL, 'W6 read-only worktree unavailable; set W5_M7_READONLY_W6_ROOT')
class W6ExactSourceIntegrationTests(unittest.TestCase):
    def test_verified_real_w6_files(self):
        base=Path(EXTERNAL)/'research/NeuralMoments/models/pcraft_ufno'
        for name,expected in W6_FILES.items():
            self.assertEqual(git_blob_sha((base/name).read_bytes()), expected)
        a,b=load_pinned_w6(EXTERNAL)
        self.assertTrue(hasattr(a,'LiteUFNOMoment'))
        self.assertTrue(hasattr(b,'ConvexPotentialMoment'))

    def test_single_geometry_repeat_control_and_limited_capacity(self):
        r=run_comparison(w6_root=EXTERNAL,seed=19,repeats=3)
        self.assertEqual(len(r['results']),5)
        self.assertLess(r['capacity_max_over_min'],1.05)
        self.assertEqual(r['cherchi_native_evaluations'],0)
        self.assertFalse(r['accuracy_comparison_allowed'])
        self.assertFalse(r['same_geometry_input_information'])
        self.assertFalse(r['training_applied'])
        for name,metrics in r['results'].items():
            self.assertEqual(metrics['r_shape'],[1,10],name)
            self.assertEqual(metrics['Jc_shape'],[1,10,10],name)
            self.assertGreater(metrics['warm_jacobian_ms'],0)
        convex=r['results']['w6_convex_potential6']
        self.assertLess(convex['jacobian_q_max_asymmetry'],1e-5)
        self.assertGreater(convex['jacobian_q_min_symmetric_eigenvalue'],-1e-5)
        self.assertLess(convex['radial_null_max_abs'],1e-5)
        self.assertLess(convex['positive_scale_r_max_abs_difference'],1e-5)

    def test_w6_potential_gradient_is_raw_moment_not_dphi_dc(self):
        torch.set_num_threads(1)
        _,m5=load_pinned_w6(EXTERNAL)
        torch.manual_seed(5)
        model=m5.ConvexPotentialMoment(points_per_axis=6,hidden=32).eval()
        geom=shared_voxel(5)
        with torch.no_grad():z=model.encode_geometry(geom)
        c=torch.randn(1,10).float();c/=c.norm(dim=-1,keepdim=True);c.requires_grad_()
        scalar=model.potential(z,c).sum()
        grad_c=torch.autograd.grad(scalar,c)[0]
        prediction=model.moment(z,c)
        B=torch.tensor([1.]*7+[2.]*3)
        torch.testing.assert_close(grad_c/B,prediction,atol=4e-5,rtol=1e-5)

    def test_w6_tamper_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            dest=Path(d)/'research/NeuralMoments/models/pcraft_ufno'
            dest.mkdir(parents=True)
            src=Path(EXTERNAL)/'research/NeuralMoments/models/pcraft_ufno'
            for f in W6_FILES:shutil.copy2(src/f,dest/f)
            with (dest/'m5_potential.py').open('a') as o:o.write('\n# injected\n')
            with self.assertRaises(UntrustedW6Source):load_pinned_w6(d)


if __name__=='__main__':unittest.main()

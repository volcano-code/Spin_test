"""Live-run regression: preserve mesh identity, forbid altered MJCF physics.

The CI and local eigensolvers returned different but equivalent diagonalizations.
"""
from __future__ import annotations
from pathlib import Path
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from p5_cloud_scene_bootstrap import certificate, FROZEN_XML, run


class CloudSceneBootstrap(unittest.TestCase):
    def test_pinned_regeneration(self):
        with tempfile.TemporaryDirectory() as td:
            evidence=run(Path(td)/'scene')
            self.assertEqual(evidence['status'],'PINNED_P2_DIAGNOSTIC_RECONSTRUCTED')
            self.assertEqual(evidence['source_closed_triangle_count'],6656)
            self.assertLessEqual(evidence['numeric_cross_version_approval']['inertia_tensor_max_absolute_diff'],1e-11)
            self.assertFalse(evidence['mujoCo_engine_executed'])

    def _mutate(self, attribute, value):
        d=tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        xml=Path(d.name)/'teapot.xml'
        root=ET.parse(FROZEN_XML)
        if attribute=='gravity':root.getroot().find('option').set('gravity',value)
        else:root.getroot().find('worldbody/body/inertial').set(attribute,value)
        root.write(xml,encoding='unicode',xml_declaration=True)
        return xml

    def test_equivalent_cross_version_numeric_serialization(self):
        # Perturb the final decimal of a 0.8e-3 inertia eigenvalue. This is
        # non-identity at the byte level but physically identical at 1e-11.
        doc=ET.parse(FROZEN_XML)
        e=doc.getroot().find('worldbody/body/inertial')
        inertia=e.get('diaginertia').split()
        inertia[0]=str(float(inertia[0])*(1+5e-14))
        other=self._mutate('diaginertia',' '.join(inertia))
        certificate(other)

    def test_wrong_mass_rejected(self):
        with self.assertRaisesRegex(ValueError,'MATERIAL_MASS_COM_OR_INERTIA_CHANGED'):
            certificate(self._mutate('mass','0.3'))

    def test_wrong_gravity_rejected(self):
        with self.assertRaisesRegex(ValueError,'MJCF_NON_INERTIAL_STRUCTURE_MISMATCH'):
            certificate(self._mutate('gravity','0 0 -3.71'))

    def test_wrong_inertia_rejected(self):
        with self.assertRaisesRegex(ValueError,'MATERIAL_MASS_COM_OR_INERTIA_CHANGED'):
            certificate(self._mutate('diaginertia','0.0008 0.0012 0.004'))


if __name__=='__main__': unittest.main()

#!/usr/bin/env python3
"""P5: rebuild pinned diagnostic Teapot on Linux across floating eigensolvers.

Only the tiny eigendecomposition serialization of the inertia MJCF fields may
vary. Recheck the source mesh byte hash, all structural XML attributes, and the
full inertial tensor independently; do not silently waive a scientific check.
This diagnostic P2 geometry is NOT a Cherchi optimized solid.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial.transform import Rotation

from p2_cgal_union import prepare as build_p2
from p3_mujoco_teapot import prepare_model, digest, P2_Z_SHA256
from p4_mujoco_verified_video import preflight

HERE=Path(__file__).resolve().parent
P0=HERE.parent/'input'/'teapot-public-original.obj'
P1=HERE/'teapot-topology-candidate-p1.obj'
FROZEN_XML=HERE/'p3-mujoco-diagnostic'/'teapot_spinning.xml'
FROZEN_XML_SHA='b830a76a8d25d689b109f15b60ab171cbac8d8aecea5a310b15ed36f1b6ffd61'


def inertial_tensor(elem):
    mass=float(elem.attrib['mass'])
    values=np.array([float(x) for x in elem.attrib['diaginertia'].split()])
    xyzw=np.array([float(x) for x in elem.attrib['quat'].split()])
    if values.shape!=(3,) or xyzw.shape!=(4,) or mass<=0 or np.any(values<=0):
        raise ValueError('BAD_INERTIAL_FIELD')
    q=np.array([xyzw[1],xyzw[2],xyzw[3],xyzw[0]])
    R=Rotation.from_quat(q).as_matrix()
    return mass,np.array([float(x) for x in elem.attrib['pos'].split()]),R@np.diag(values)@R.T


def certificate(xml, baseline=FROZEN_XML):
    baseline=Path(baseline)
    if digest(baseline)!=FROZEN_XML_SHA:
        raise ValueError('FROZEN_XML_CORRUPTED')
    original=ET.parse(baseline).getroot()
    candidate=ET.parse(xml).getroot()
    old_i=original.find('worldbody/body/inertial')
    new_i=candidate.find('worldbody/body/inertial')
    if old_i is None or new_i is None:
        raise ValueError('INERTIAL_NOT_PRESENT')
    a_mass,a_com,a_inertia=inertial_tensor(old_i)
    b_mass,b_com,b_inertia=inertial_tensor(new_i)
    if (abs(a_mass-b_mass)>1e-13 or not np.allclose(a_com,b_com,atol=1e-12,rtol=0) or
       not np.allclose(a_inertia,b_inertia,atol=1e-11,rtol=0)):
        raise ValueError('MATERIAL_MASS_COM_OR_INERTIA_CHANGED')
    # All tags, hierarchy and ALL attributes other than inertial diagonalization
    # must remain exact. Eigenvector bases may legitimately differ by sign.
    a=deepcopy(original);b=deepcopy(candidate)
    for root in (a,b):
        inertial=root.find('worldbody/body/inertial')
        inertial.set('quat','INERTIA_EIGENVECTORS_VERIFIED_BY_RECONSTRUCTION')
        inertial.set('diaginertia','PRINCIPAL_MOMENTS_VERIFIED_BY_TENSOR')
    if ET.tostring(a,encoding='unicode')!=ET.tostring(b,encoding='unicode'):
        raise ValueError('MJCF_NON_INERTIAL_STRUCTURE_MISMATCH')
    return dict(frozen_xml_sha256=FROZEN_XML_SHA,
                generated_xml_sha256=digest(xml),
                xml_byte_identical=digest(xml)==FROZEN_XML_SHA,
                non_inertial_xml_exact=True,
                mass_absolute_diff=abs(a_mass-b_mass),
                com_max_absolute_diff=float(np.max(np.abs(a_com-b_com))),
                inertia_tensor_max_absolute_diff=float(np.max(np.abs(a_inertia-b_inertia))),
                inertia_tolerance_kg_m2=1e-11)


def run(output):
    output=Path(output)
    output.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='w4-p2-source-') as temp:
        p2=Path(temp)
        p2data=build_p2(P0,P1,p2)
        mesh=p2/'p2-teapot-cgal-union-z-up.obj'
        if digest(mesh)!=P2_Z_SHA256:
            raise ValueError('PINNED_Z_MESH_CHANGED')
        scene=prepare_model(mesh,output,source_kind='diagnostic-cgal',height_m=.15,mass_kg=.25)
    independent=preflight(output/'teapot_spinning.xml')
    audit=certificate(output/'teapot_spinning.xml')
    evidence=dict(schema='W4P5CloudSceneV1',status='PINNED_P2_DIAGNOSTIC_RECONSTRUCTED',
                  geometry_provenance='CGAL_PROXY_NOT_CHERCHI',
                  original_sha256=p2data['source']['P0_sha256'],
                  source_closed_triangle_count=p2data['output']['z_up']['faces'],
                  visual_mesh_sha256=digest(output/'assets'/'teapot_visual_z_up.obj'),
                  scene_preflight=independent,mujoCo_engine_executed=False,
                  numeric_cross_version_approval=audit)
    (output/'p5-scene-certificate.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return evidence


if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    print(json.dumps(run(args.output),indent=2))

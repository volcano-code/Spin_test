#!/usr/bin/env python3
"""Bootstrap diagnostic MuJoCo scene from immutable source in a clean checkout.

Does NOT use Cherchi, and does NOT execute MuJoCo. A fail-closed preparation
step so tests/video never rely on a missing untracked proxy OBJ file.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import tempfile
from p2_cgal_union import prepare as create_p2_proxy
from p3_mujoco_teapot import P2_Z_SHA256, prepare_model, digest

BASE=Path(__file__).resolve().parent
ORIGINAL=BASE.parent/'input'/'teapot-public-original.obj'
CANDIDATE=BASE/'teapot-topology-candidate-p1.obj'
MJCF_SHA='b830a76a8d25d689b109f15b60ab171cbac8d8aecea5a310b15ed36f1b6ffd61'


def materialize_scene(output, *, cached_mesh=None):
    """Regenerate P2 CGAL *diagnostic* proxy then an exact-sha MJCF scene."""
    output=Path(output)
    if cached_mesh is not None:
        zmesh=Path(cached_mesh)
        if digest(zmesh)!=P2_Z_SHA256:
            raise ValueError('CACHED_PROXY_MESH_NOT_PINNED')
        proof='PINNED_EXISTING_P2_PROXY'
        report=None
        # Preexisting file is used ONLY after its exact SHA256 is verified.
        built=prepare_model(zmesh,output,source_kind='diagnostic-cgal',height_m=.15,mass_kg=.25)
    else:
        with tempfile.TemporaryDirectory(prefix='w4-cgal-diagnostic-') as td:
            proxy=Path(td)
            report=create_p2_proxy(ORIGINAL,CANDIDATE,proxy)
            zmesh=proxy/'p2-teapot-cgal-union-z-up.obj'
            if digest(zmesh)!=P2_Z_SHA256:
                raise ValueError('REGENERATED_PROXY_SHA_MISMATCH')
            built=prepare_model(zmesh,output,source_kind='diagnostic-cgal',height_m=.15,mass_kg=.25)
        proof='REGENERATED_P2_CGAL_DIAGNOSTIC'
    xml=output/'teapot_spinning.xml'
    if digest(xml)!=MJCF_SHA or built['mesh_asset_sha256']!=P2_Z_SHA256:
        raise ValueError('RECREATED_MJCF_SHA_MISMATCH')
    return dict(status='SCENE_STATIC_BOOTSTRAP_ONLY',source=proof,
                geometry_kind='CGAL_DIAGNOSTIC_NOT_CHERCHI',
                mujoco_engine_invoked=False,mjcf_sha256=digest(xml),
                asset_sha256=built['mesh_asset_sha256'])


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--output',type=Path,required=True)
    a.add_argument('--cached-mesh',type=Path)
    args=a.parse_args()
    print(json.dumps(materialize_scene(args.output,cached_mesh=args.cached_mesh),indent=2))

if __name__=='__main__':main()

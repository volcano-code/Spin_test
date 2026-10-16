"""Paper-oriented Noodles domain, not an optimized result.

E is a DESIGN ENVELOPE, not a permanently fixed shell.
F is the union of tube/hub/pin parts. All unions/differences must be
performed with the project's exact Boolean backend before optimization.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import noodles_dense_v5_input as old

SPEC = deepcopy(old.SPEC)
SPEC.update(schema='noodles-paper-domain-v6', classification='RECONSTRUCTED_METHOD_VALIDATION',
            author_original=False, permanent_ellipsoid_shell=False,
            domain_contract='E=outer-ellipsoid; S=union(fixed_parts); F=S; D=E\\S',
            legacy_inner_ellipsoid_role='NOT_USED_FOR_FIXED_SHELL')

def components():
    parts = old.components()
    parts.pop('inner-ellipsoid-candidate', None)
    return parts

def construction_recipe():
    parts=components()
    names=['hub-fixed','pin-fixed'] + sorted(n for n in parts if n.startswith('tube-'))
    assert len(names)==len(set(names))
    return dict(fixed_parts=names, design_envelope='outer-ellipsoid',
                fixed_material_operation='UNION(ALL fixed_parts)',
                design_operation='DIFFERENCE(outer-ellipsoid, UNION(ALL fixed_parts))',
                complete_initial_material_operation='UNION(outer-ellipsoid, UNION(ALL fixed_parts))',
                permanent_ellipsoid_shell=False)

def prepare(directory):
    from noodles_input import mesh_audit, write_obj
    directory=Path(directory)
    directory.mkdir(parents=True,exist_ok=False)
    parts=components()
    entries={}
    for name, mesh in parts.items():
        audit=mesh_audit(mesh)
        if not audit['closed'] or not audit['winding_consistent'] or audit['components']!=1 or mesh.volume<=0:
            raise ValueError('INVALID_SOURCE_PART: '+name)
        model=directory/(name+'-model.obj')
        si=directory/(name+'-si.obj')
        write_obj(model,mesh)
        scaled=mesh.copy();scaled.vertices*=SPEC['model_unit_m'];write_obj(si,scaled)
        entries[name]=dict(model_obj=model.name,si_obj=si.name,audit=audit,
                          sha256={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in [('model',model),('si',si)]})
    manifest=dict(schema=SPEC['schema'],spec=SPEC,parts=entries,construction=construction_recipe(),
                  optimization_invocations=0,simulation_invocations=0,
                  status='SOURCE_PARTS_PREPARED_PENDING_EXACT_BOOLEAN_AND_OPTIMIZATION',
                  note='No optimization or printability claims; original v5 is unchanged')
    (directory/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False))
    return manifest

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--prepare',required=True)
    prepare(p.parse_args().prepare)
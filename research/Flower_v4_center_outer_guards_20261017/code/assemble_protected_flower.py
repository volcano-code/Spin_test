"""Assemble actual optimized Flower material and fixed central/outer rims.

Does not weld bearings or patch holes after optimization: the two fixed bands
were already part of the frozen input and solver's exact fixed material moments.
"""
from pathlib import Path
import argparse,json,hashlib
import trimesh
from flower_table_delivery import combined_obj

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def assemble(folder,out):
    folder,out=Path(folder),Path(out)
    report=json.loads((folder/'output-preparation.json').read_text())
    required=['design','retained','cavity','original-flower','fixed-middle-boundary-rim',
              *report['rotor_layers'],*report['clamp_layers']]
    required=list(dict.fromkeys(required))
    if report['full_material_gate']!='PENDING_EXACT_REGION_AUDIT':
        raise ValueError('Unexpected audit status; do not override checks')
    meshes={}
    for name in required:
        file=folder/(name+'.obj')
        if not file.is_file() or sha(file)!=report['files'][name]['sha256']:
            raise ValueError('GEOMETRY_SOURCE_MISMATCH '+name)
        mesh=trimesh.load(file,force='mesh',process=False,maintain_order=True)
        if not mesh.is_watertight or not mesh.is_winding_consistent or mesh.volume<=0:
            raise ValueError('INVALID_COMPONENT '+name)
        meshes[name]=mesh
    out.mkdir(parents=True,exist_ok=False)
    (out/'flower.mtl').write_text('newmtl grey\nKd 0.45 0.49 0.52\nnewmtl yellow\nKd 0.94 0.75 0.19\nnewmtl pink\nKd 0.88 0.39 0.61\n')
    rotor=['retained',*report['rotor_layers']]
    clamp=list(report['clamp_layers'])
    selections={
        'flower-middle-protected.obj':['retained','fixed-middle-boundary-rim'],
        'flower-rotor-protected.obj':rotor,
        'flower-assembly-protected.obj':rotor+clamp,
        'flower-cutaway-protected.obj':[x for x in rotor+clamp if x!='top'],
    }
    checks={}
    for filename,names in selections.items():
        checks[filename]=combined_obj(out/filename,names,meshes)
    # The GLB is an inspectable rendering preview, not a Boolean-welded solid.
    scene=trimesh.Scene()
    for name in rotor+clamp:
        scene.add_geometry(meshes[name],node_name=name,geom_name=name)
    scene.export(out/'flower-preview-protected.glb')
    summary={'schema':'flower-v4-protected-seed1-assembly-v1',
        'selected_seed':report['selected_seed'],'source_report_sha256':sha(folder/'output-preparation.json'),
        'assembly_files':checks,'glb_sha256':sha(out/'flower-preview-protected.glb'),
        'state':'ASSEMBLY_AND_RELOAD_ONLY_FULL_EXACT_GEOMETRY_AND_PHYSICS_PENDING',
        'disclaimer':'OBJ files retain independently moving pieces: do not weld bearings; selected flower material and fixed middle ring are separately preserved.'}
    (out/'assembly-check.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();s=assemble(a.source,a.output)
    print(json.dumps({k:{'faces':v['faces'],'parts':v['parts']} for k,v in s['assembly_files'].items()},indent=2))
